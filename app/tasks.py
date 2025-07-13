import os
import requests
import logging
from datetime import datetime, timedelta, timezone
from celery import Celery
from celery.schedules import crontab
import pytz

# Import modul lokal
from . import worker, crud, schemas, model
from .database import SessionLocal

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfigurasi Celery
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
BACKEND_URL = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
celery = Celery("tasks", broker=BROKER_URL, backend=BACKEND_URL)

# Daftar liga target
TARGET_LEAGUES = [
    'soccer_argentina_primera_division',
    'soccer_australia_aleague',
    'soccer_austria_bundesliga',
    'soccer_belgium_first_div',
    'soccer_chile_campeonato',
    'soccer_denmark_superliga',
    'soccer_england_efl_cup',
    'soccer_france_ligue_two',
    'soccer_italy_serie_b',
    'soccer_japan_j_league',
    'soccer_korea_kleague1',
    'soccer_mexico_ligamx',
    'soccer_netherlands_eredivisie',
    'soccer_poland_ekstraklasa',
    'soccer_spain_segunda_division',
    'soccer_germany_bundesliga2',
    'soccer_spl',
    'soccer_sweden_allsvenskan',
    'soccer_sweden_superettan',
    'soccer_switzerland_superleague',
    'soccer_turkey_super_league',
]

@celery.task(acks_late=True)
def record_odds_snapshot(match_db_id: int):
    """
    Task untuk mengambil dan merekam satu snapshot odds untuk sebuah pertandingan.
    Task ini sekarang cerdas dan tidak akan membuat data duplikat.
    """
    db = SessionLocal()
    try:
        match = db.query(model.Match).filter(model.Match.id == match_db_id).first()
        if not match:
            logger.error(f"Match dengan ID database {match_db_id} tidak ditemukan.")
            return

        five_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        recent_snapshot = db.query(model.OddsSnapshot).filter(
            model.OddsSnapshot.match_id == match_db_id,
            model.OddsSnapshot.timestamp >= five_minutes_ago
        ).first()

        if recent_snapshot:
            logger.warning(f"Snapshot untuk match_id {match_db_id} sudah ada dalam 5 menit terakhir. Melewatkan...")
            return

        logger.info(f"Mulai merekam odds untuk match: {match.home_team} vs {match.away_team} (api_id: {match.api_id})")

        match_odds_data = worker.fetch_odds_for_match(match.api_id, match.sport_key)

        if not match_odds_data or not match_odds_data.get("bookmakers"):
            logger.warning(f"Tidak ada data odds atau bookmakers ditemukan untuk match api_id: {match.api_id}")
            return

        bookmaker = match_odds_data["bookmakers"][0]
        market = next((m for m in bookmaker.get("markets", []) if m["key"] == "h2h"), None)

        if market and len(market.get("outcomes", [])) == 3:
            outcomes = market["outcomes"]
            price_home = next((o['price'] for o in outcomes if o['name'] == match.home_team), 0.0)
            price_away = next((o['price'] for o in outcomes if o['name'] == match.away_team), 0.0)
            price_draw = next((o['price'] for o in outcomes if o.get('name') == "Draw"), 0.0)

            snapshot_schema = schemas.OddsSnapshotCreate(
                bookmaker=bookmaker["key"],
                price_home=price_home,
                price_draw=price_draw,
                price_away=price_away
            )
            crud.create_odds_snapshot(db, odds_snapshot=snapshot_schema, match_id=match_db_id)
            logger.info(f"✅ Berhasil merekam odds untuk match_db_id: {match_db_id}")
        else:
            logger.warning(f"Market 'h2h' tidak ditemukan atau tidak lengkap untuk match api_id: {match.api_id}")

    except Exception as e:
        logger.error(f"Error tidak terduga saat merekam odds untuk match_id {match_db_id}: {e}", exc_info=True)
    finally:
        db.close()


@celery.task
def discover_new_matches():
    """
    Mencari pertandingan baru dari liga target.
    """
    logger.warning("Mulai mencari pertandingan baru...")
    db = SessionLocal()
    try:
        for league_key in TARGET_LEAGUES:
            try:
                logger.info(f"Memeriksa liga: {league_key}")
                api_url = f"{worker.ODDS_API_BASE_URL}/v4/sports/{league_key}/events"
                params = {"apiKey": worker.THE_ODDS_API_KEY, "dateFormat": "iso"}

                response = requests.get(api_url, params=params, timeout=30)
                response.raise_for_status()
                matches_data = response.json()

                if not matches_data:
                    logger.info(f"Tidak ada jadwal pertandingan ditemukan dari API untuk {league_key}.")
                    continue

                for match_data in matches_data:
                    existing_match = crud.get_match_by_api_id(db, api_id=match_data['id'])
                    if not existing_match:
                        commence_time_utc = datetime.fromisoformat(match_data['commence_time'].replace("Z", "+00:00"))
                        
                        logger.warning(f"Pertandingan baru ditemukan: {match_data['home_team']} vs {match_data['away_team']}")

                        new_match_schema = schemas.MatchCreate(
                            api_id=match_data['id'],
                            sport_key=match_data['sport_key'],
                            home_team=match_data['home_team'],
                            away_team=match_data['away_team'],
                            commence_time=commence_time_utc
                        )
                        new_match = crud.create_match(db, match=new_match_schema)

                        snapshot_times = [
                            new_match.commence_time - timedelta(minutes=60),
                            new_match.commence_time - timedelta(minutes=20),
                            new_match.commence_time - timedelta(minutes=5)
                        ]
                        for exec_time in snapshot_times:
                            if exec_time > datetime.now(timezone.utc):
                                record_odds_snapshot.apply_async(
                                    args=[new_match.id], # Hanya kirim satu argumen
                                    eta=exec_time
                                )
                                logger.info(f"Menjadwalkan snapshot untuk match_id {new_match.id} pada {exec_time.isoformat()}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Gagal menghubungi API untuk liga {league_key}: {e}")
            except Exception as e:
                logger.error(f"Terjadi kesalahan saat memproses liga {league_key}: {e}", exc_info=True)

    finally:
        db.close()
        logger.warning("Selesai mencari pertandingan baru.")


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Menjadwalkan task periodik.
    """
    sender.add_periodic_task(
        crontab(hour='*/2', minute='0'),
        discover_new_matches.s(),
        name='Cari pertandingan baru dari liga target setiap 2 jam'
    )