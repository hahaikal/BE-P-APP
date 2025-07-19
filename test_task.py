import os
import sys

# --- Bagian Paling Penting ---
# Atur variabel lingkungan SEBELUM kita mengimpor aplikasi kita.
# Ini meniru cara kerja worker kita yang sebenarnya.
print("==> Mengatur alamat Broker Redis secara manual...")
os.environ['CELERY_BROKER_URL'] = 'redis://redis:6379/0'
os.environ['CELERY_RESULT_BACKEND'] = 'redis://redis:6379/0'
print("==> Alamat Broker diatur.")

# Sekarang baru kita import tugasnya
from app.tasks import record_odds_snapshot

def main():
    """
    Fungsi utama untuk mengirim tugas tes.
    """
    # Ambil ID pertandingan dari argumen command line
    if len(sys.argv) < 2:
        print("Error: Harap berikan ID pertandingan sebagai argumen.")
        print("Contoh: python test_task.py 190")
        return

    try:
        match_id_to_test = int(sys.argv[1])
    except ValueError:
        print(f"Error: '{sys.argv[1]}' bukan angka yang valid.")
        return

    print(f"==> Mengirim tugas 'record_odds_snapshot' untuk match_id: {match_id_to_test}")
    
    # Kirim tugas ke worker
    record_odds_snapshot.delay(match_id_to_test)
    
    print("==> Tugas berhasil dikirim! Silakan periksa log worker Anda dengan 'docker-compose logs -f worker'.")

if __name__ == "__main__":
    main()