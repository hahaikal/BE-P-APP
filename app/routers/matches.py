from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging
import pandas as pd
from datetime import datetime, time, timezone
import pytz

from .. import crud, schemas, auth
from ..database import get_db
from ..utils.feature_engineering import process_odds_to_features # Impor utilitas baru

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Matches & Predictions"],
    responses={404: {"description": "Not found"}},
)

# ... (Endpoint lain seperti read_matches, create_manual_match, dll. tetap sama) ...
@router.get("/", response_model=list[schemas.Match])
def read_matches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        matches = crud.get_matches(db, skip=skip, limit=limit)
        return matches
    except Exception as e:
        logger.error(f"Error reading matches: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/manual", response_model=schemas.Match, status_code=status.HTTP_201_CREATED)
def create_manual_match(match: schemas.ManualMatchCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(auth.get_current_user)):
    logger.info(f"Menerima permintaan manual untuk membuat pertandingan: {match.home_team} vs {match.away_team}")
    if not match.api_id:
        match.api_id = f"manual_{int(datetime.now().timestamp())}"
    return crud.create_match(db=db, match=match)

@router.post("/{match_id}/odds/manual", response_model=schemas.OddsSnapshot, status_code=status.HTTP_201_CREATED)
def create_manual_odds(match_id: int, odds_data: schemas.ManualOddsSnapshotCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(auth.get_current_user)):
    logger.info(f"Menerima permintaan manual untuk menambah odds ke match_id: {match_id} pada waktu {odds_data.snapshot_time}")
    db_match = crud.get_match_by_id(db, match_id=match_id)
    if db_match is None:
        raise HTTPException(status_code=404, detail="Match tidak ditemukan")
    try:
        local_tz = pytz.timezone(odds_data.snapshot_timezone)
        today_local = datetime.now(local_tz).date()
        time_input = datetime.strptime(odds_data.snapshot_time, '%H:%M').time()
        naive_datetime = datetime.combine(today_local, time_input)
        local_datetime = local_tz.localize(naive_datetime)
        utc_datetime = local_datetime.astimezone(timezone.utc)
        logger.info(f"Waktu input {odds_data.snapshot_time} {odds_data.snapshot_timezone} dikonversi ke {utc_datetime.isoformat()} UTC")
    except ValueError:
        raise HTTPException(status_code=400, detail="Format waktu tidak valid. Gunakan format 'HH:MM'.")
    except pytz.UnknownTimeZoneError:
        raise HTTPException(status_code=400, detail=f"Timezone tidak dikenal: {odds_data.snapshot_timezone}")
    return crud.create_odds_snapshot(db=db, odds_snapshot=odds_data, match_id=match_id, timestamp=utc_datetime)

@router.put("/{match_id}/score", response_model=schemas.Match)
def update_manual_score(match_id: int, scores: schemas.ScoreUpdate, db: Session = Depends(get_db), current_user: schemas.User = Depends(auth.get_current_user)):
    logger.info(f"Menerima permintaan manual untuk update skor match_id: {match_id}")
    updated_match = crud.update_match_scores(db, match_id=match_id, scores=scores)
    if updated_match is None:
        raise HTTPException(status_code=404, detail="Match tidak ditemukan")
    logger.info(f"✅ Skor berhasil diupdate untuk match {match_id}: {scores.result_home_score}-{scores.result_away_score}")
    return updated_match

@router.get("/{match_id}/prediction", response_model=schemas.PredictionOutput)
def get_match_prediction(match_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Memberikan prediksi hasil pertandingan menggunakan model yang sudah dilatih.
    """
    logger.info(f"Menerima permintaan prediksi untuk match_id: {match_id}")
    
    # 1. Periksa apakah model sudah dimuat
    model = request.app.state.model
    encoder = request.app.state.encoder
    feature_columns = request.app.state.feature_columns

    if not all([model, encoder, feature_columns]):
        logger.error("Model atau artefak lainnya tidak dimuat. Prediksi tidak tersedia.")
        raise HTTPException(status_code=503, detail="Prediction service is currently unavailable.")

    # 2. Ambil data pertandingan dan odds dari DB
    db_match = crud.get_match_by_id(db, match_id=match_id)
    if db_match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Ambil 3 snapshot odds terakhir
    snapshots = sorted(db_match.odds_snapshots, key=lambda s: s.timestamp, reverse=True)[:3]
    if not snapshots:
        raise HTTPException(status_code=400, detail="Not enough odds data to make a prediction.")

    # 3. Lakukan Feature Engineering
    features_dict = process_odds_to_features(snapshots)
    features_df = pd.DataFrame([features_dict])
    
    # Pastikan urutan kolom sesuai dengan saat training
    features_df = features_df.reindex(columns=feature_columns, fill_value=0)

    # 4. Lakukan Prediksi
    try:
        probabilities = model.predict_proba(features_df)[0]
        predicted_class_index = probabilities.argmax()
        predicted_outcome = encoder.inverse_transform([predicted_class_index])[0]
    except Exception as e:
        logger.error(f"Error saat prediksi untuk match_id {match_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not process prediction.")

    # 5. Format Hasil
    # Buat dictionary probabilitas sesuai dengan urutan kelas di encoder
    prob_dict = {encoder.classes_[i]: probabilities[i] for i in range(len(encoder.classes_))}

    prediction_result = {
        "match_id": match_id,
        "home_team": db_match.home_team,
        "away_team": db_match.away_team,
        "predicted_outcome": predicted_outcome,
        "probabilities": {
            "home_win": prob_dict.get("HOME_WIN", 0.0),
            "draw": prob_dict.get("DRAW", 0.0),
            "away_win": prob_dict.get("AWAY_WIN", 0.0)
        }
    }
    
    logger.info(f"Prediksi untuk match {match_id} berhasil: {predicted_outcome}")
    return prediction_result

@router.get("/status_overview", response_model=schemas.StatusOverview)
def get_status_overview(db: Session = Depends(get_db)):
    overview = crud.get_matches_status_overview(db)
    return overview

@router.delete("/{match_id}", status_code=status.HTTP_200_OK)
def delete_match(match_id: int, db: Session = Depends(get_db), current_user: schemas.User = Depends(auth.get_current_user)):
    deleted_match = crud.delete_match_by_id(db, match_id=match_id)
    if not deleted_match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return JSONResponse(
        content={"status": "success", "message": f"Match {match_id} and associated odds have been deleted."},
        status_code=200
    )
