import os
import sys
import logging
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from sqlalchemy import func, or_

from app.database import SessionLocal
from app import model

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def cleanup_incomplete_historical_data():
    """
    Skrip mandiri untuk mencari dan menghapus data pertandingan historis
    (sebelum hari ini) yang tidak lengkap.
    """
    logging.info("🚀 Memulai skrip pembersihan data historis yang tidak lengkap...")
    db = SessionLocal()
    
    try:
        now_utc = datetime.now(timezone.utc)
        
        matches_to_delete = (
            db.query(model.Match)
            .outerjoin(model.OddsSnapshot)
            .filter(model.Match.commence_time < now_utc)
            .group_by(model.Match.id)
            .having(
                or_(
                    func.count(model.OddsSnapshot.id) < 3,
                    model.Match.result_home_score == None
                )
            )
            .all()
        )
        
        if not matches_to_delete:
            logging.info("✅ Tidak ada data pertandingan historis yang tidak lengkap. Database bersih!")
            return

        logging.warning(f"🔥 Ditemukan {len(matches_to_delete)} pertandingan tidak lengkap untuk dihapus.")
        
        deleted_count = 0
        for match in matches_to_delete:
            logging.info(f" -> Menghapus Match ID: {match.id} - {match.home_team} vs {match.away_team} (Jadwal: {match.commence_time})")
            db.delete(match)
            deleted_count += 1
        
        db.commit()
        
        logging.info(f"🧹 Pembersihan selesai. Total {deleted_count} pertandingan telah dihapus.")

    except Exception as e:
        logging.error(f"Terjadi kesalahan fatal selama proses pembersihan: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
        logging.info("🚀 Skrip pembersihan data selesai.")


if __name__ == "__main__":
    cleanup_incomplete_historical_data()
