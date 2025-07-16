from sqlalchemy.orm import Session
from datetime import datetime, timezone
from . import model, schemas

def get_match_by_id(db: Session, match_id: int):
    return db.query(model.Match).filter(model.Match.id == match_id).first()

def get_match_by_api_id(db: Session, api_id: str):
    return db.query(model.Match).filter(model.Match.api_id == api_id).first()

def get_matches(db: Session, skip: int = 0, limit: int = 100):
    return db.query(model.Match).offset(skip).limit(limit).all()

def create_match(db: Session, match: schemas.MatchCreate):
    db_match = model.Match(**match.dict())
    db.add(db_match)
    db.commit()
    db.refresh(db_match)
    return db_match

def create_odds_snapshot(db: Session, odds_snapshot: schemas.OddsSnapshotBase, match_id: int, timestamp: datetime | None = None):
    """
    Membuat odds snapshot. Jika timestamp tidak disediakan, gunakan waktu saat ini (UTC).
    """
    if timestamp is None:
        timestamp_to_save = datetime.now(timezone.utc)
    else:
        timestamp_to_save = timestamp

    db_snapshot = model.OddsSnapshot(
        **odds_snapshot.dict(),
        match_id=match_id,
        timestamp=timestamp_to_save 
    )
    db.add(db_snapshot)
    db.commit()
    db.refresh(db_snapshot)
    return db_snapshot

def update_match_scores(db: Session, match_id: int, scores: schemas.ScoreUpdate):
    db_match = db.query(model.Match).filter(model.Match.id == match_id).first()
    if db_match:
        db_match.result_home_score = scores.result_home_score
        db_match.result_away_score = scores.result_away_score
        db.commit()
        db.refresh(db_match)
    return db_match