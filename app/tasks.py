import os
import requests
import logging
from datetime import datetime, timedelta, timezone
from celery import Celery
from celery.schedules import crontab
import pytz

from . import worker, crud, schemas, model
from .database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
BACKEND_URL = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
celery = Celery("tasks", broker=BROKER_URL, backend=BACKEND_URL)

TARGET_LEAGUES = [
    'soccer_argentina_primera_division', 'soccer_australia_aleague', 'soccer_austria_bundesliga',
    'soccer_belgium_first_div', 'soccer_brazil_campeonato', 'soccer_brazil_serie_b',
    'soccer_chile_campeonato', 'soccer_china_superleague', 'soccer_denmark_superliga',
    'soccer_efl_champ', 'soccer_england_efl_cup', 'soccer_england_league1',
    'soccer_england_league2', 'soccer_epl', 'soccer_finland_veikkausliiga',
    'soccer_france_ligue_one', 'soccer_france_ligue_two', 'soccer_germany_bundesliga',
    'soccer_germany_bundesliga2', 'soccer_greece_super_league', 'soccer_italy_serie_a',
    'soccer_italy_serie_b', 'soccer_japan_j_league', 'soccer_korea_kleague1',
    'soccer_league_of_ireland', 'soccer_mexico_ligamx', 'soccer_netherlands_eredivisie',
    'soccer_norway_eliteserien', 'soccer_poland_ekstraklasa', 'soccer_portugal_primeira_liga',
    'soccer_spain_la_liga', 'soccer_spain_segunda_division', 'soccer_spl',
    'soccer_sweden_allsvenskan', 'soccer_sweden_superettan', 'soccer_switzerland_superleague',
    'soccer_turkey_super_league', 'soccer_usa_mls'
]

@celery.task(acks_late=True)
def record_odds_snapshot(match_db_id: int):
    db = SessionLocal()
    try:
        match = db.query(model.Match).filter(model.Match.id == match_db_id).first()
        if not match:
            logger.error(f"Match dengan ID database {match_db_id} tidak ditemukan.")
            return

        # Logika untuk mencegah duplikasi snapshot tetap sama
        five_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
        recent_snapshot = db.query(model.OddsSnapshot).filter(
            model.OddsSnapshot.match_id == match_db_id,
            model.OddsSnapshot.timestamp >= five_minutes_ago
        ).first()

        if recent_snapshot:
            logger.warning(f"Snapshot untuk match_id {match_db_id} sudah ada dalam 5 menit terakhir. Melewatkan...")
            return

        logger.info(f"Mulai merekam odds untuk match: {match.home_team} vs {match.away_team} (api_id: {match.api_id})")
        
        # --- PERBAIKAN KUNCI DI SINI ---
        # Secara eksplisit meminta market 'h2h' dan 'spreads'
        match_odds_data = worker.fetch_odds_for_match(match.api_id, match.sport_key, markets="h2h,spreads")

        if not match_odds_data or not match_odds_data.get("bookmakers"):
            logger.warning(f"Tidak ada data odds atau bookmakers ditemukan untuk match api_id: {match.api_id}")
            return

        bookmaker = match_odds_data["bookmakers"][0]
        
        # --- LOGIKA PARSING BARU UNTUK H2H & SPREADS ---
        h2h_data = None
        spreads_data = None

        for market in bookmaker.get("markets", []):
            if market.get("key") == "h2h":
                h2h_data = market.get("outcomes")
            elif market.get("key") == "spreads":
                spreads_data = market.get("outcomes")

        # Pastikan data H2H ada sebagai data dasar
        if h2h_data and len(h2h_data) == 3:
            price_home = next((o['price'] for o in h2h_data if o['name'] == match.home_team), 0.0)
            price_away = next((o['price'] for o in h2h_data if o['name'] == match.away_team), 0.0)
            price_draw = next((o['price'] for o in h2h_data if o.get('name') == "Draw"), 0.0)

            # Siapkan data untuk disimpan
            snapshot_data = {
                "bookmaker": bookmaker["key"],
                "price_home": price_home,
                "price_draw": price_draw,
                "price_away": price_away
            }

            # Jika data handicap (spreads) ditemukan, tambahkan ke data yang akan disimpan
            if spreads_data and len(spreads_data) == 2:
                home_spread = next((s for s in spreads_data if s["name"] == match.home_team), None)
                away_spread = next((s for s in spreads_data if s["name"] == match.away_team), None)
                if home_spread and away_spread:
                    snapshot_data["handicap_line"] = home_spread["point"]
                    snapshot_data["handicap_price_home"] = home_spread["price"]
                    snapshot_data["handicap_price_away"] = away_spread["price"]
                    logger.info(f"Data handicap ditemukan untuk match_id {match_db_id}.")

            snapshot_schema = schemas.OddsSnapshotCreate(**snapshot_data)
            crud.create_odds_snapshot(db, odds_snapshot=snapshot_schema, match_id=match_db_id)
            logger.info(f"✅ Berhasil merekam odds untuk match_db_id: {match_db_id}")
        else:
            logger.warning(f"Market 'h2h' tidak ditemukan atau tidak lengkap untuk match api_id: {match.api_id}")
            
    except Exception as e:
        logger.error(f"Error tidak terduga saat merekam odds untuk match_id {match_db_id}: {e}", exc_info=True)
    finally:
        db.close()

# ... (task discover_new_matches dan lainnya tidak perlu diubah) ...
@celery.task
def discover_new_matches():
    logger.warning("Mulai mencari pertandingan baru untuk HARI INI...")
    db = SessionLocal()
    today_utc = datetime.now(timezone.utc).date()
    
    try:
        for league_key in TARGET_LEAGUES:
            try:
                logger.info(f"Memeriksa liga: {league_key}")
                matches_data = worker.fetch_scheduled_matches_by_league(league_key)

                if not matches_data:
                    logger.info(f"Tidak ada jadwal pertandingan ditemukan dari API untuk {league_key}.")
                    continue

                for match_data in matches_data:
                    commence_time_utc = datetime.fromisoformat(match_data['commence_time'].replace("Z", "+00:00"))
                    
                    if commence_time_utc.date() == today_utc:
                        existing_match = crud.get_match_by_api_id(db, api_id=match_data['id'])
                        if not existing_match:
                            logger.warning(f"Pertandingan HARI INI ditemukan: {match_data['home_team']} vs {match_data['away_team']}")

                            new_match_schema = schemas.MatchCreate(
                                api_id=match_data['id'], sport_key=match_data['sport_key'],
                                sport_title=match_data.get('sport_title', league_key),
                                home_team=match_data['home_team'], away_team=match_data['away_team'],
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
                                    record_odds_snapshot.apply_async(args=[new_match.id], eta=exec_time)
                                    logger.info(f"Menjadwalkan snapshot untuk match_id {new_match.id} pada {exec_time.isoformat()}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Gagal menghubungi API untuk liga {league_key}: {e}")
            except Exception as e:
                logger.error(f"Terjadi kesalahan saat memproses liga {league_key}: {e}", exc_info=True)
    finally:
        db.close()
        logger.warning("Selesai mencari pertandingan baru.")


@celery.task
def fetch_and_update_daily_scores():
    """
    Mengambil data skor pertandingan kemarin dari semua liga target dan
    memperbaruinya di database.
    """
    logger.warning("Mulai tugas harian: Mengambil dan memperbarui skor pertandingan.")
    db = SessionLocal()
    try:
        for league_key in TARGET_LEAGUES:
            scores_data = worker.fetch_daily_scores_by_league(league_key)
            
            if not scores_data:
                logger.info(f"Tidak ada data skor ditemukan untuk liga {league_key}.")
                continue
            
            for score_item in scores_data:
                if not score_item.get('completed', False) or not score_item.get('scores'):
                    continue

                api_id = score_item['id']
                db_match = crud.get_match_by_api_id(db, api_id=api_id)

                if db_match:
                    home_score = next((s['score'] for s in score_item['scores'] if s['name'] == db_match.home_team), None)
                    away_score = next((s['score'] for s in score_item['scores'] if s['name'] == db_match.away_team), None)

                    if home_score is not None and away_score is not None:
                        score_update_schema = schemas.ScoreUpdate(
                            result_home_score=int(home_score),
                            result_away_score=int(away_score)
                        )
                        crud.update_match_scores(db, match_id=db_match.id, scores=score_update_schema)
                        logger.info(f"✅ Skor berhasil diupdate untuk match ID {db_match.id}: {home_score}-{away_score}")
                    else:
                        logger.warning(f"Data skor tidak lengkap untuk match api_id {api_id}.")
                else:
                    logger.info(f"Match dengan api_id {api_id} tidak ditemukan di DB, skor diabaikan.")
    finally:
        db.close()
        logger.warning("Selesai memperbarui skor harian.")


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Menjadwalkan semua task periodik.
    """
    sender.add_periodic_task(
        crontab(hour=4, minute=0),
        discover_new_matches.s(),
        name='Cari pertandingan untuk hari ini (sekali sehari)'
    )

    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        fetch_and_update_daily_scores.s(),
        name='Ambil dan perbarui skor pertandingan harian'
    )
