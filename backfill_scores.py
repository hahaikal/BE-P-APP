# backfill_scores.py

import os
import sys
from datetime import datetime, timedelta, timezone
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app.database import SessionLocal
from app import model, worker

def backfill_scores():
    logging.info("🚀 Memulai skrip 'Kerja Rodi' untuk mengisi skor...")
    db = SessionLocal()
    try:
        lookup_time = datetime.now(timezone.utc) - timedelta(minutes=110)
        matches_to_update = db.query(model.Match).filter(
            model.Match.commence_time < lookup_time,
            model.Match.result_home_score.is_(None)
        ).all()

        if not matches_to_update:
            logging.info("✅ Semua pertandingan yang relevan sudah memiliki skor. Tidak ada pekerjaan.")
            return

        logging.warning(f"🔥 Ditemukan {len(matches_to_update)} pertandingan yang skornya perlu diisi.")

        for match in matches_to_update:
            logging.info(f"Mengambil skor untuk match ID {match.id}: {match.home_team} vs {match.away_team}...")
            
            # Memanggil worker dengan DUA argumen yang dibutuhkan: api_id dan sport_key
            score_data = worker.fetch_score_for_match(match.api_id, match.sport_key)
            
            if score_data:
                home_score = next((s['score'] for s in score_data['scores'] if s['name'] == match.home_team), None)
                away_score = next((s['score'] for s in score_data['scores'] if s['name'] == match.away_team), None)

                if home_score is not None and away_score is not None:
                    match.result_home_score = int(home_score)
                    match.result_away_score = int(away_score)
                    db.commit()
                    logging.info(f"✅ Skor berhasil diisi untuk match ID {match.id}: {home_score}-{away_score}")
                else:
                    logging.warning(f"Data skor tidak lengkap dari API untuk match ID {match.id}.")
            else:
                logging.warning(f"Gagal mendapatkan data skor dari API untuk match ID {match.id}.")

    except Exception as e:
        logging.error(f"Terjadi kesalahan fatal selama proses backfill: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
        logging.info("🚀 Skrip 'Kerja Rodi' selesai.")

if __name__ == "__main__":
    backfill_scores()