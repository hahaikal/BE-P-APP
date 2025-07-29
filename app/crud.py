from sqlalchemy.orm import Session, joinedload
from . import model, schemas # <-- Menghapus 'import auth'
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

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

def get_matches_status_overview(db: Session):
    all_matches = db.query(model.Match).options(
        joinedload(model.Match.odds_snapshots)
    ).all()

    overview = {
        "complete": [],
        "incomplete": [],
        "empty": []
    }

    for match in all_matches:
        has_score = match.result_home_score is not None
        odds_count = len(match.odds_snapshots)

        if odds_count >= 3 and has_score:
            overview["complete"].append(match)
        
        elif odds_count == 0:
            overview["empty"].append(match)
            
        else:
            overview["incomplete"].append(match)
            
    return overview

def delete_match_by_id(db: Session, match_id: int):
    db_match = db.query(model.Match).filter(model.Match.id == match_id).first()
    
    if db_match:
        db.delete(db_match)
        db.commit()
        return db_match
    
    return None

def get_user_by_username(db: Session, username: str):
    return db.query(model.User).filter(model.User.username == username).first()

# --- [MODIFIKASI] ---
# Fungsi ini sekarang menerima password yang sudah di-hash.
# Ini hanya digunakan oleh skrip CLI, bukan oleh API secara langsung.
def create_user(db: Session, user: schemas.UserCreate, hashed_password: str):
    db_user = model.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- [DIHAPUS] ---
# Fungsi authenticate_user dipindahkan sepenuhnya ke auth.py

def delete_odds_snapshot_by_id(db: Session, id: int):
    """
    Menghapus satu odds snapshot dari database berdasarkan ID-nya.
    """
    print(f"=== DEBUG DELETE START ===")
    print(f"Attempting to delete odds snapshot with ID: {id}")
    
    # Debug: Cek total records
    total_records = db.query(model.OddsSnapshot).count()
    print(f"Total odds snapshots in database: {total_records}")
    
    # Debug: Cek ID yang tersedia (ambil 10 terakhir)
    recent_ids = db.query(model.OddsSnapshot.id).order_by(model.OddsSnapshot.id.desc()).limit(10).all()
    print(f"Recent IDs: {[id[0] for id in recent_ids]}")
    
    # Debug: Query spesifik untuk ID yang diminta
    db_snapshot = db.query(model.OddsSnapshot).filter(model.OddsSnapshot.id == id).first()
    
    if db_snapshot:
        print(f"✅ FOUND: ID={db_snapshot.id}, bookmaker={db_snapshot.bookmaker}, match_id={db_snapshot.match_id}")
        print(f"   price_home={db_snapshot.price_home}, price_draw={db_snapshot.price_draw}, price_away={db_snapshot.price_away}")
        print(f"   timestamp={db_snapshot.timestamp}")
        
        # Debug: Cek match yang terkait
        match = db.query(model.Match).filter(model.Match.id == db_snapshot.match_id).first()
        if match:
            print(f"   Related match: {match.home_team} vs {match.away_team}")
        
        db.delete(db_snapshot)
        db.commit()
        print(f"✅ Successfully deleted odds snapshot ID: {id}")
        return db_snapshot
    else:
        print(f"❌ Odds snapshot with ID {id} not found in this session.")
        print(f"=== DEBUG DELETE END ===")
        
    return None
