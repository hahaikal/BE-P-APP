from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging
from datetime import datetime, time, timezone
import pytz

from .. import crud, schemas
from ..database import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["matches"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=list[schemas.Match])
def read_matches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve matches from the database.
    """
    try:
        matches = crud.get_matches(db, skip=skip, limit=limit)
        return matches
    except Exception as e:
        logger.error(f"Error reading matches: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/manual", response_model=schemas.Match, status_code=status.HTTP_201_CREATED)
def create_manual_match(match: schemas.ManualMatchCreate, db: Session = Depends(get_db)):
    """
    Endpoint untuk membuat data pertandingan baru secara manual.
    """
    logger.info(f"Menerima permintaan manual untuk membuat pertandingan: {match.home_team} vs {match.away_team}")
    
    if not match.api_id:
        match.api_id = f"manual_{int(datetime.now().timestamp())}"
        
    return crud.create_match(db=db, match=match)


@router.post("/{match_id}/odds/manual", response_model=schemas.OddsSnapshot, status_code=status.HTTP_201_CREATED)
def create_manual_odds(match_id: int, odds_data: schemas.ManualOddsSnapshotCreate, db: Session = Depends(get_db)):
    """
    Endpoint untuk menambahkan data odds snapshot ke pertandingan yang ada
    dengan waktu yang bisa ditentukan secara manual.
    """
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

    return crud.create_odds_snapshot(
        db=db, 
        odds_snapshot=odds_data, 
        match_id=match_id,
        timestamp=utc_datetime 
    )

@router.put("/{match_id}/score", response_model=schemas.Match)
def update_manual_score(match_id: int, scores: schemas.ScoreUpdate, db: Session = Depends(get_db)):
    """
    Endpoint untuk memasukkan/memperbarui skor pertandingan secara manual.
    """
    
    logger.info(f"Menerima permintaan manual untuk update skor match_id: {match_id}")
    updated_match = crud.update_match_scores(db, match_id=match_id, scores=scores)
    
    if updated_match is None:
        raise HTTPException(status_code=404, detail="Match tidak ditemukan")
    
    logger.info(f"✅ Skor berhasil diupdate untuk match {match_id}: {scores.result_home_score}-{scores.result_away_score}")
    return updated_match

@router.get("/{match_id}/prediction", response_model=schemas.PredictionOutput)
def get_match_prediction(match_id: int, db: Session = Depends(get_db)):
    """Get prediction for a specific match."""
    
    db_match = crud.get_match_by_id(db, match_id=match_id)
    
    if db_match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    
    prediction_result = {
        "match_id": match_id,
        "home_team": db_match.home_team,
        "away_team": db_match.away_team,
        "predicted_outcome": "HOME_WIN",
        "probabilities": {"home_win": 0.65, "draw": 0.20, "away_win": 0.15}
    }
    return prediction_result
