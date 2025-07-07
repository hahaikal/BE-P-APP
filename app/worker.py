import requests # Ganti httpx dengan requests
import os
from dotenv import load_dotenv
import traceback

# Muat environment variables dari .env
load_dotenv()

THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY")
ODDS_API_BASE_URL = "https://api.the-odds-api.com"
SPORT = "soccer_epl"
REGIONS = "eu"
MARKETS = "h2h"
ODDS_FORMAT = "decimal"
DATE_FORMAT = "iso"

def fetch_upcoming_matches(): # Hapus async
    """
    Mengambil jadwal pertandingan yang akan datang dari The Odds API menggunakan requests.
    """
    if not THE_ODDS_API_KEY:
        print("Error: THE_ODDS_API_KEY tidak ditemukan.")
        return []

    url = f"{ODDS_API_BASE_URL}/v4/sports/{SPORT}/scores"
    params = {"apiKey": THE_ODDS_API_KEY, "daysFrom": "3"}
    
    try:
        # Gunakan requests.get dengan timeout
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status() # Akan raise exception untuk status code 4xx atau 5xx
        print("✅ Berhasil mengambil data jadwal pertandingan.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print("==================== TRACEBACK ERROR (requests) ====================")
        traceback.print_exc()
        print("====================================================================")
    return []


def fetch_odds_for_match(event_id: str): # Hapus async
    """
    Mengambil data odds untuk satu pertandingan spesifik menggunakan requests.
    """
    if not THE_ODDS_API_KEY:
        print("Error: THE_ODDS_API_KEY tidak ditemukan.")
        return None

    url = f"{ODDS_API_BASE_URL}/v4/sports/{SPORT}/events/{event_id}/odds"
    params = {
        "apiKey": THE_ODDS_API_KEY,
        "regions": REGIONS,
        "markets": MARKETS,
        "oddsFormat": ODDS_FORMAT,
        "dateFormat": DATE_FORMAT,
    }

    try:
        # Gunakan requests.get dengan timeout
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        print(f"✅ Berhasil mengambil data odds untuk event {event_id}.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"============== TRACEBACK ERROR (Odds for {event_id}) ==============")
        traceback.print_exc()
        print("==================================================================================")
    return None