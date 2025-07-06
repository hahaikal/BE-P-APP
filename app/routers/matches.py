import pandas as pd
from typing import List
from fastapi import APIRouter, Request, Depends
from fastapi_cache.decorator import cache
from sqlalchemy.orm import Session

# Import diubah menjadi absolut dari 'app'
from app import crud, schemas
from app.database import SessionLocal

router = APIRouter(
    prefix="/matches",
    tags=["Matches"]
)

# Dependency untuk mendapatkan sesi database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("", response_model=List[schemas.MatchSchema])
def read_all_matches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Endpoint baru untuk mengambil daftar semua pertandingan.
    """
    matches = crud.get_all_matches(db, skip=skip, limit=limit)
    
    response = []
    for match in matches:
        # Pydantic v2 menggunakan from_attributes, bukan from_orm
        match_data = schemas.MatchSchema.from_attributes(match)
        # Tambahkan data prediksi dummy untuk sementara
        match_data.prediction = schemas.PredictionSchema(
            home_win_percentage=0.0,
            draw_percentage=0.0,
            away_win_percentage=0.0
        )
        response.append(match_data)
        
    return response

@router.get("/{match_id}/prediction")
@cache(expire=60)
async def get_match_prediction(match_id: int, request: Request):
    """
    Endpoint untuk mendapatkan prediksi spesifik untuk satu pertandingan.
    (Kode di sini tetap sama seperti sebelumnya)
    """
    model = request.app.state.model
    encoder = request.app.state.encoder
    feature_columns = request.app.state.feature_columns

    dummy_features_list = [[
        2.0, 2.1, 2.05, 3.0, 3.1, 3.05, 2.5, 2.6, 2.55,
        -0.1, -0.05, 0.05, 0.48, 0.29, 0.23
    ]]
    
    predict_df = pd.DataFrame(dummy_features_list, columns=feature_columns)
    probabilities = model.predict_proba(predict_df)[0]
    prob_dict = dict(zip(model.classes_, probabilities))
    
    prediction_result = {}
    for i, class_name in enumerate(encoder.classes_):
        prob = prob_dict.get(i, 0.0)
        
        if class_name == 'HOME_WIN':
            prediction_result["home_win_percentage"] = round(prob * 100, 2)
        elif class_name == 'DRAW':
            prediction_result["draw_percentage"] = round(prob * 100, 2)
        elif class_name == 'AWAY_WIN':
            prediction_result["away_win_percentage"] = round(prob * 100, 2)

    return prediction_result