from sqlalchemy.orm import Session
from . import model, schemas

def get_match_by_id(db: Session, *, match_id: int) -> model.Match | None:
    """Mencari match berdasarkan ID primary key dari database."""
    return db.query(model.Match).filter(model.Match.id == match_id).first()

def get_match_by_api_id(db: Session, *, api_id: str) -> model.Match | None:
    """Mencari match berdasarkan ID dari API eksternal."""
    return db.query(model.Match).filter(model.Match.api_id == api_id).first()

def create_match(db: Session, *, match: schemas.MatchCreate | schemas.ManualMatchCreate) -> model.Match:
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

def update_match_scores(db: Session, match_id: int, scores: schemas.ScoreUpdate):
    """Memperbarui skor akhir untuk sebuah pertandingan."""
    db_match = db.query(model.Match).filter(model.Match.id == match_id).first()
    if db_match:
        db_match.result_home_score = scores.result_home_score
        db_match.result_away_score = scores.result_away_score
        db.commit()
        db.refresh(db_match)
    return db_match

def get_matches(db: Session, skip: int = 0, limit: int = 100):
    return db.query(model.Match).order_by(model.Match.commence_time.asc()).offset(skip).limit(limit).all()