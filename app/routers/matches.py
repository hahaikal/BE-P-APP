from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from .. import crud, schemas
from ..database import get_db

# Configure logging
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


@router.get("/{match_id}/prediction", response_model=schemas.PredictionOutput)
def get_match_prediction(match_id: str, db: Session = Depends(get_db)):
    """
    Get prediction for a specific match.
    NOTE: This is a placeholder implementation.
    """
    db_match = crud.get_match_by_id(db, match_id=match_id)
    if db_match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    # --- Placeholder Logic ---
    # In a real scenario, you would fetch features, pass them to the model,
    # and get a real prediction.
    logger.info(f"Generating placeholder prediction for match_id: {match_id}")
    
    # Placeholder response
    prediction_result = {
        "match_id": match_id,
        "home_team": db_match.home_team,
        "away_team": db_match.away_team,
        "predicted_outcome": "HOME_WIN", # Placeholder
        "probabilities": {
            "home_win": 0.65,
            "draw": 0.20,
            "away_win": 0.15
        }
    }
    # --- End of Placeholder Logic ---

    return prediction_result
