import pandas as pd
from fastapi import APIRouter, Request
from fastapi_cache.decorator import cache
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/matches",
    tags=["Matches"]
)

@router.get("/{match_id}/prediction")
@cache(expire=60)
async def get_match_prediction(match_id: int, request: Request):
    """
    Endpoint untuk mendapatkan prediksi spesifik untuk satu pertandingan.
    Hasilnya di-cache untuk mengurangi beban.
    """
    model = request.app.state.model
    encoder = request.app.state.encoder
    feature_columns = request.app.state.feature_columns

    # Membuat dummy features
    dummy_features_list = [[
        # Pivot (9)
        2.0, 2.1, 2.05, 3.0, 3.1, 3.05, 2.5, 2.6, 2.55,
        # Delta (2)
        -0.1, -0.05,
        # Volatility (1)
        0.05,
        # Implicit Probs (3)
        0.48, 0.29, 0.23
    ]]
    
    # 1. Buat DataFrame dengan nama kolom yang benar
    predict_df = pd.DataFrame(dummy_features_list, columns=feature_columns)

    # 2. Lakukan prediksi
    probabilities = model.predict_proba(predict_df)[0]
    
    # 3. Buat dictionary probabilitas secara aman menggunakan kelas dari model
    # model.classes_ berisi kelas yang dipelajari model, misal: [0, 1] yang merepresentasikan ['AWAY_WIN', 'DRAW']
    prob_dict = dict(zip(model.classes_, probabilities))
    
    # 4. Ambil nilai probabilitas dengan aman, beri nilai 0 jika tidak ada
    # encoder.classes_ berisi SEMUA kelas, misal: ['AWAY_WIN', 'DRAW', 'HOME_WIN']
    prediction_result = {}
    for i, class_name in enumerate(encoder.classes_):
        # i adalah indeks kelas asli (0, 1, 2)
        # class_name adalah nama kelas ('AWAY_WIN', 'DRAW', 'HOME_WIN')
        
        # Ambil probabilitas dari prob_dict menggunakan indeks kelas. Default ke 0.0 jika tidak ditemukan.
        prob = prob_dict.get(i, 0.0)
        
        if class_name == 'HOME_WIN':
            prediction_result["home_win_percentage"] = round(prob * 100, 2)
        elif class_name == 'DRAW':
            prediction_result["draw_percentage"] = round(prob * 100, 2)
        elif class_name == 'AWAY_WIN':
            prediction_result["away_win_percentage"] = round(prob * 100, 2)

    return prediction_result