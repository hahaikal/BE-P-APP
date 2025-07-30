import os
import requests
import logging
from datetime import datetime, timedelta

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfigurasi API
THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY")
ODDS_API_BASE_URL = "https://api.the-odds-api.com"

# --- PERBAIKAN DI SINI ---
# Menambahkan parameter 'markets' dengan nilai default 'h2h'
def fetch_odds_for_match(event_id: str, sport_key: str, regions: str = "eu", markets: str = "h2h"):
    """
    Mengambil data odds untuk satu event spesifik.
    """
    if not THE_ODDS_API_KEY:
        logger.error("THE_ODDS_API_KEY tidak diatur.")
        return None

    url = f"{ODDS_API_BASE_URL}/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": THE_ODDS_API_KEY,
        "regions": regions,
        "markets": markets, # Menggunakan parameter 'markets' yang diterima
        "eventIds": event_id,
        "oddsFormat": "decimal",
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data[0] if data else None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error saat mengambil odds untuk event {event_id}: {e}")
        return None

def fetch_scheduled_matches_by_league(league_key: str):
    """
    Mengambil jadwal pertandingan untuk satu liga.
    """
    if not THE_ODDS_API_KEY:
        logger.error("THE_ODDS_API_KEY tidak diatur.")
        return None
        
    url = f"{ODDS_API_BASE_URL}/v4/sports/{league_key}/events"
    params = {"apiKey": THE_ODDS_API_KEY, "dateFormat": "iso"}
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Gagal menghubungi API untuk jadwal liga {league_key}: {e}")
        return None

def fetch_daily_scores_by_league(league_key: str):
    """
    Mengambil data skor untuk satu liga pada hari kemarin.
    """
    if not THE_ODDS_API_KEY:
        logger.error("THE_ODDS_API_KEY tidak diatur.")
        return None
        
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y-%m-%d')
    
    url = f"{ODDS_API_BASE_URL}/v4/sports/{league_key}/scores"
    params = {"apiKey": THE_ODDS_API_KEY, "daysFrom": "1"}
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Gagal menghubungi API untuk skor liga {league_key}: {e}")
        return None
