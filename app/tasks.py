import os
import requests
import logging
from datetime import datetime, timedelta, timezone
from celery import Celery
from celery.schedules import crontab
import pytz

from . import worker, crud, schemas, model
from .database import SessionLocal, get_db

logger = logging.getLogger(__name__)

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
BACKEND_URL = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
celery = Celery("tasks", broker=BROKER_URL, backend=BACKEND_URL)

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

@celery.task
def record_odds_snapshot(match_db_id: int, match_api_id: str):
    """
    Task untuk mengambil dan merekam satu snapshot odds untuk sebuah pertandingan.
    (Tidak ada perubahan di fungsi ini, sudah solid)
    """
    logger.info(f"Mulai merekam odds untuk match_db_id: {match_db_id}")
    db = SessionLocal()
    try:
        match_odds_data = worker.fetch_odds_for_match(match_api_id)
        if not match_odds_data or not match_odds_data.get("bookmakers"):
            logger.warning(f"Tidak ada data odds ditemukan untuk match {match_api_id}")
            return

        bookmaker = match_odds_data["bookmakers"][0]
        market = next((m for m in bookmaker.get("markets", []) if m["key"] == "h2h"), None)

        if market and len(market["outcomes"]) == 3:
            outcomes = market["outcomes"]
            price_home = next((o['price'] for o in outcomes if o['name'] == match_odds_data["home_team"]), 0.0)
            price_away = next((o['price'] for o in outcomes if o['name'] == match_odds_data["away_team"]), 0.0)
            price_draw = next((o['price'] for o in outcomes if o['name'] == "Draw"), 0.0)

            snapshot_schema = schemas.OddsSnapshotCreate(
                bookmaker=bookmaker["key"],
                price_home=price_home,
                price_draw=price_draw,
                price_away=price_away
            )
            crud.create_odds_snapshot(db, odds_snapshot=snapshot_schema, match_id=match_db_id)
            logger.info(f"Berhasil merekam odds untuk match_db_id: {match_db_id}")
        else:
            logger.warning(f"Market 'h2h' tidak ditemukan untuk match {match_api_id}")
    except Exception as e:
        logger.error(f"Error saat merekam odds untuk match_id {match_db_id}: {e}", exc_info=True)
    finally:
        db.close()


# ======================================================================
# TUGAS FINAL: Mengganti total isi fungsi discover_new_matches
# ======================================================================
@celery.task
def discover_new_matches():
    """
    Mencari pertandingan dari liga-liga target yang akan dimulai
    antara 1 jam dari sekarang hingga akhir hari ini.
    """
    logger.warning("Mulai mencari pertandingan baru dengan filter liga dan waktu...")
    db = SessionLocal()

    try:
        # 1. Tentukan rentang waktu (Time Window) dalam UTC
        now_utc = datetime.now(timezone.utc)
        start_time_utc = now_utc + timedelta(hours=1)
        end_time_utc = now_utc.replace(hour=23, minute=59, second=59, microsecond=0)

        # Konversi ke format ISO 8601 yang dibutuhkan API
        start_time_iso = start_time_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_time_iso = end_time_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

        logger.info(f"Mencari pertandingan dari {start_time_iso} hingga {end_time_iso}")

        # 2. Loop untuk setiap liga target
        for league_key in TARGET_LEAGUES:
            try:
                logger.info(f"Memeriksa liga: {league_key}")

                # 3. Panggil API dengan filter liga DAN waktu
                api_url = f"{worker.ODDS_API_BASE_URL}/v4/sports/{league_key}/scores"
                params = {
                    "apiKey": worker.THE_ODDS_API_KEY,
                    "commenceTimeFrom": start_time_iso,
                    "commenceTimeTo": end_time_iso
                }

                response = requests.get(api_url, timeout=30)
                response.raise_for_status()  # Akan error jika status bukan 2xx

                matches_data = response.json()

                if not matches_data:
                    logger.info(f"Tidak ada pertandingan untuk {league_key} dalam rentang waktu ini.")
                    continue  # Lanjut ke liga berikutnya

                # 4. Proses dan simpan pertandingan baru (menggunakan CRUD pattern)
                for match_data in matches_data:
                    existing_match = crud.get_match_by_api_id(db, api_id=match_data['id'])
                    if not existing_match:
                        logger.warning(f"Pertandingan baru ditemukan di {league_key}: {match_data['home_team']} vs {match_data['away_team']}")

                        commence_time_utc = datetime.fromisoformat(match_data["commence_time"].replace("Z", "+00:00"))
                        
                        new_match_schema = schemas.MatchCreate(
                            api_id=match_data['id'],
                            sport_key=match_data['sport_key'],
                            home_team=match_data['home_team'],
                            away_team=match_data['away_team'],
                            commence_time=commence_time_utc
                        )
                        new_match = crud.create_match(db, match=new_match_schema)

                        # Jadwalkan pengambilan odds untuk pertandingan baru (menggunakan logika yang sudah ada)
                        kick_off_time = new_match.commence_time
                        snapshot_times = [
                            kick_off_time - timedelta(minutes=60),
                            kick_off_time - timedelta(minutes=20),
                            kick_off_time - timedelta(minutes=5)
                        ]
                        for exec_time in snapshot_times:
                            if exec_time > datetime.now(pytz.utc):
                                record_odds_snapshot.apply_async(
                                    args=[new_match.id, new_match.api_id],
                                    eta=exec_time,
                                    acks_late=True
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
    (Tidak ada perubahan, tetap berjalan setiap 2 jam)
    """
    sender.add_periodic_task(
        crontab(hour='*/2', minute='0'),
        discover_new_matches.s(),
        name='Cari pertandingan baru dari liga target setiap 2 jam'
    )