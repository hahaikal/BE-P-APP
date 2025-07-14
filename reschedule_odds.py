import os
import sys
from datetime import datetime, timedelta, timezone
import logging

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Mengatur sys.path untuk memastikan modul 'app' dapat ditemukan
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# --- [PERBAIKAN] ---
# Mengimpor 'celery' sesuai dengan nama variabel di tasks.py
from app.tasks import celery, record_odds_snapshot
from app.database import SessionLocal
from app import model

# --- [PERBAIKAN] ---
# Mengkonfigurasi ulang broker menggunakan variabel 'celery' yang benar
celery.conf.update(
    broker_url=os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0"),
    result_backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
)
# --------------------

def reschedule_missing_odds():
    """
    Skrip sekali jalan untuk mencari semua pertandingan di masa depan
    dan memastikan jadwal snapshot odds-nya ada di kalender (Redis).
    """
    logging.info("🚀 Memulai skrip penjadwalan ulang snapshot odds...")
    db = SessionLocal()
    try:
        # 1. Cari semua pertandingan yang akan datang
        future_matches = db.query(model.Match).filter(
            model.Match.commence_time > datetime.now(timezone.utc)
        ).all()

        if not future_matches:
            logging.info("Tidak ada pertandingan di masa depan yang perlu dijadwalkan.")
            return

        logging.warning(f"🔥 Ditemukan {len(future_matches)} pertandingan di masa depan. Memeriksa dan menjadwalkan ulang snapshot...")

        # 2. Untuk setiap pertandingan, jadwalkan ulang snapshot-nya
        for match in future_matches:
            logging.info(f"Memproses Match ID {match.id}: {match.home_team} vs {match.away_team}")
            
            snapshot_times = [
                match.commence_time - timedelta(minutes=60),
                match.commence_time - timedelta(minutes=20),
                match.commence_time - timedelta(minutes=5)
            ]

            for exec_time in snapshot_times:
                # Hanya jadwalkan jika waktu eksekusinya masih di masa depan
                if exec_time > datetime.now(timezone.utc):
                    record_odds_snapshot.apply_async(
                        args=[match.id],
                        eta=exec_time
                    )
                    logging.info(f"  -> ✅ Berhasil menjadwalkan snapshot pada {exec_time.isoformat()}")

    except Exception as e:
        logging.error(f"Terjadi kesalahan fatal selama proses penjadwalan ulang: {e}", exc_info=True)
    finally:
        db.close()
        logging.info("🚀 Skrip penjadwalan ulang selesai.")

if __name__ == "__main__":
    reschedule_missing_odds()