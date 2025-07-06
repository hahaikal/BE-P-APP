from sqlalchemy.orm import Session
from app import model

def get_all_matches(db: Session, skip: int = 0, limit: int = 100):
    """
    Mengambil semua data pertandingan dari database.
    """
    return db.query(model.Match).offset(skip).limit(limit).all()
