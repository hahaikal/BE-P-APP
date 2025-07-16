import os
import requests
import logging

THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY")
ODDS_API_BASE_URL = "https://api.the-odds-api.com"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_odds_for_match(match_api_id: str, sport_key: str):
    """
    Mengambil data odds untuk satu pertandingan SPESIFIK.
    """
    logger.info(f"Mencoba mengambil odds untuk match_api_id: {match_api_id}")
    try:
        api_url = f"{ODDS_API_BASE_URL}/v4/sports/{sport_key}/odds"
        params = {
            "apiKey": THE_ODDS_API_KEY,
            "regions": "eu",
            "markets": "h2h",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
            "eventIds": match_api_id,
        }
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data:
            return data[0]
        logger.warning(f"Respons API kosong untuk odds match_api_id: {match_api_id}")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error saat mengambil odds untuk {match_api_id}: {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Error umum saat mengambil odds untuk {match_api_id}: {e}", exc_info=True)
        return None
