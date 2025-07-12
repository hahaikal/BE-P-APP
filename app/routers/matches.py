from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging
from datetime import datetime

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
def create_manual_odds(match_id: int, odds_snapshot: schemas.OddsSnapshotCreate, db: Session = Depends(get_db)):
    """
    Endpoint untuk menambahkan data odds snapshot ke pertandingan yang ada.
    """
    logger.info(f"Menerima permintaan manual untuk menambah odds ke match_id: {match_id}")
    db_match = crud.get_match_by_id(db, match_id=match_id)
    if db_match is None:
        raise HTTPException(status_code=404, detail="Match tidak ditemukan")
        
    return crud.create_odds_snapshot(db=db, odds_snapshot=odds_snapshot, match_id=match_id)


@router.get("/{match_id}/prediction", response_model=schemas.PredictionOutput)
def get_match_prediction(match_id: int, db: Session = Depends(get_db)):
    """
    Get prediction for a specific match.
    NOTE: This is a placeholder implementation.
    """
    db_match = crud.get_match_by_id(db, match_id=match_id)
    if db_match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    logger.info(f"Generating placeholder prediction for match_id: {match_id}")
    prediction_result = {
        "match_id": match_id,
        "home_team": db_match.home_team,
        "away_team": db_match.away_team,
        "predicted_outcome": "HOME_WIN",
        "probabilities": {
            "home_win": 0.65,
            "draw": 0.20,
            "away_win": 0.15
        }
    }
    return prediction_result