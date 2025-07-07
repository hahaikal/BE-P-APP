from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# Import dari modul lokal
from .. import crud, schemas
from ..database import get_db

# Definisikan router
router = APIRouter(
    tags=["Matches"] # Menambahkan tag untuk dokumentasi API
)

# Endpoint untuk mendapatkan semua pertandingan
@router.get("/matches", response_model=List[schemas.Match])
def read_matches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Mengambil daftar pertandingan dari database.
    """
    matches = crud.get_matches(db, skip=skip, limit=limit)
    return matches


@router.get("/matches/{match_id}/prediction", response_model=schemas.PredictionOutput) # <-- PERUBAHAN DI SINI
def get_match_prediction(match_id: int, db: Session = Depends(get_db)):
    """
    Mengambil prediksi untuk satu pertandingan.
    (Logika penuh akan diimplementasikan di Sprint 3)
    """
    # Placeholder logic
    match = db.query(schemas.Match).filter(schemas.Match.id == match_id).first() # Ini juga perlu diperbaiki
    if not match:
        # handle error
        pass
    
    return {
        "match_id": match_id,
        "home_team": match.home_team,
        "away_team": match.away_team,
        "prediction": "HOME_WIN",
        "probabilities": {"HOME_WIN": 0.55, "DRAW": 0.25, "AWAY_WIN": 0.20}
    }