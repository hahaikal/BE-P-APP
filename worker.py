import os
import time
from datetime import datetime, timedelta

from celery import Celery
from celery.schedules import crontab # Untuk penjadwalan periodik
from dotenv import load_dotenv

# Memuat environment variables
load_dotenv()

# Inisialisasi Celery
# Nama 'p_app_worker' adalah nama worker kita
# Broker menunjuk ke Redis
celery_app = Celery(
    "p_app_worker",
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL")
)

# Konfigurasi: Memberitahu Celery untuk otomatis mencari tasks
celery_app.autodiscover_tasks()

# --- DEFINISI TUGAS (TASKS) ---

@celery_app.task(name="fetch_all_upcoming_matches")
def fetch_all_upcoming_matches():
    """
    Subtask 2.2: Worker untuk mengambil data jadwal pertandingan.
    Tugas ini akan berjalan secara periodik (misal: setiap hari).
    """
    print("Mulai mengambil jadwal pertandingan dari The Odds API...")
    # --- LOGIKA UNTUK MENGAMBIL DATA DARI THE ODDS API ---
    # 1. Panggil The Odds API menggunakan API Key.
    # 2. Loop setiap pertandingan yang didapat.
    # 3. Simpan ke tabel 'matches' di database PostgreSQL.
    # 4. Untuk setiap match BARU, jadwalkan pengambilan odds.
    # --- (Simulasi untuk saat ini) ---
    
    # Misalkan kita mendapat 1 match baru dari API
    match_id_from_db = 1 # ID dari match yang baru disimpan
    kickoff_time = datetime.utcnow() + timedelta(minutes=70) # Kickoff 70 menit dari sekarang
    
    print(f"Menemukan pertandingan baru (ID: {match_id_from_db}). Menjadwalkan pengambilan odds...")
    
    # Subtask 2.3 (Kritis): Memicu pengambilan data odds pada interval spesifik
    # Kita gunakan 'eta' untuk menjadwalkan tugas pada waktu yang tepat di masa depan.
    fetch_odds_for_match.apply_async(args=[match_id_from_db], eta=kickoff_time - timedelta(minutes=60))
    fetch_odds_for_match.apply_async(args=[match_id_from_db], eta=kickoff_time - timedelta(minutes=20))
    fetch_odds_for_match.apply_async(args=[match_id_from_db], eta=kickoff_time - timedelta(minutes=5))
    
    print("Penjadwalan odds selesai.")
    return "Proses pengambilan jadwal selesai."


@celery_app.task(name="fetch_odds_for_match")
def fetch_odds_for_match(match_id: int):
    """
    Subtask 2.3: Mengambil snapshot odds untuk satu pertandingan
    dan menyimpannya ke tabel 'odds_snapshots'.
    """
    print(f"Mengambil snapshot odds untuk Match ID: {match_id} pada {datetime.utcnow()}")
    # --- LOGIKA UNTUK MENGAMBIL ODDS & MENYIMPAN KE DB ---
    # 1. Ambil data odds dari API untuk match_id.
    # 2. Simpan hasilnya ke tabel 'odds_snapshots' dengan foreign key ke match_id.
    # --- (Simulasi untuk saat ini) ---
    time.sleep(5) # Simulasi proses I/O
    print(f"Selesai menyimpan snapshot untuk Match ID: {match_id}")
    return f"Snapshot untuk match {match_id} berhasil disimpan."


# --- PENJADWALAN OTOMATIS (CELERY BEAT) ---

celery_app.conf.beat_schedule = {
    # Menjalankan tugas 'fetch_all_upcoming_matches' setiap hari pada jam 1 pagi
    'fetch-matches-daily': {
        'task': 'fetch_all_upcoming_matches',
        'schedule': crontab(hour=1, minute=0),
    },
}