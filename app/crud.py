from sqlalchemy.orm import Session
from . import model, schemas

def get_match_by_api_id(db: Session, *, api_id: str) -> model.Match | None:
    """Mencari match berdasarkan ID dari API eksternal."""
    return db.query(model.Match).filter(model.Match.api_id == api_id).first()

def create_match(db: Session, *, match: schemas.MatchCreate) -> model.Match:
    """Membuat match baru di database."""
    db_match = model.Match(**match.model_dump())
    db.add(db_match)
    db.commit()
    db.refresh(db_match)
    return db_match

def create_odds_snapshot(db: Session, *, odds_snapshot: schemas.OddsSnapshotCreate, match_id: int) -> model.OddsSnapshot:
    """Membuat odds snapshot baru yang terhubung dengan sebuah match."""
    db_odds_snapshot = model.OddsSnapshot(**odds_snapshot.model_dump(), match_id=match_id)
    db.add(db_odds_snapshot)
    db.commit()
    db.refresh(db_odds_snapshot)
    return db_odds_snapshot

# --- Fungsi yang sudah ada ---
def get_matches(db: Session, skip: int = 0, limit: int = 100):
    return db.query(model.Match).order_by(model.Match.commence_time.asc()).offset(skip).limit(limit).all()

def get_match_prediction(db: Session, match_id: int):
    # Logika ini akan diimplementasikan di Sprint 3
    return {"match_id": match_id, "prediction": "LOGIC_PENDING"}