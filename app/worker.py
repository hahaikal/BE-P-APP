import os
import requests
import logging

# Konfigurasi dasar
THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY")
ODDS_API_BASE_URL = "https://api.the-odds-api.com"

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fungsi ini tidak kita gunakan lagi untuk mencari pertandingan,
# tetapi biarkan saja untuk referensi atau penggunaan di masa depan.
def fetch_upcoming_matches():
    """
    Mengambil jadwal pertandingan yang akan datang dari The Odds API menggunakan requests.
    """
    if not THE_ODDS_API_KEY:
        logger.error("Error: THE_ODDS_API_KEY tidak ditemukan.")
        return []

    url = f"{ODDS_API_BASE_URL}/v4/sports/soccer_epl/scores"
    params = {"apiKey": THE_ODDS_API_KEY, "daysFrom": "3"}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        logger.info("✅ Berhasil mengambil data jadwal pertandingan.")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error saat mengambil jadwal pertandingan: {e}")
    return []


def fetch_odds_for_match(match_api_id: str, sport_key: str):
    """
    Mengambil data odds untuk satu pertandingan SPESIFIK menggunakan
    endpoint dan parameter yang BENAR.
    """
    logger.info(f"Mencoba mengambil odds untuk match_api_id: {match_api_id}")
    try:
        # ===== INI ADALAH PERBAIKAN UTAMA =====
        # Endpoint yang benar adalah /odds, BUKAN /events/{id}/odds
        api_url = f"{ODDS_API_BASE_URL}/v4/sports/{sport_key}/odds"

        # Event ID sekarang menjadi parameter, bukan bagian dari URL
        params = {
            "apiKey": THE_ODDS_API_KEY,
            "regions": "eu",
            "markets": "h2h",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
            "eventIds": match_api_id, # <-- Ini cara yang benar
        }
        # =======================================

        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        if data:
            # API mengembalikan list, jadi kita ambil elemen pertamanya
            return data[0]
        logger.warning(f"Respons API kosong untuk match_api_id: {match_api_id}")
        return None

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error saat mengambil odds untuk {match_api_id}: {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Error umum saat mengambil odds untuk {match_api_id}: {e}", exc_info=True)
        return None