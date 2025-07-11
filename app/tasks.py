import os
from celery import Celery
from celery.schedules import crontab
from datetime import datetime, timedelta
import pytz

from . import worker, crud, schemas
from .database import SessionLocal

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
BACKEND_URL = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery = Celery("tasks", broker=BROKER_URL, backend=BACKEND_URL)

@celery.task
def record_odds_snapshot(match_db_id: int, match_api_id: str):
    """
    Task untuk mengambil dan merekam satu snapshot odds untuk sebuah pertandingan.
    """
    print(f"Mulai merekam odds untuk match_db_id: {match_db_id}")
    db = SessionLocal()
    try:
        match_odds_data = worker.fetch_odds_for_match(match_api_id)
        
        if not match_odds_data or not match_odds_data.get("bookmakers"):
            print(f"Tidak ada data odds atau bookmakers ditemukan untuk match {match_api_id}")
            return

        bookmaker = match_odds_data["bookmakers"][0]
        market = next((m for m in bookmaker.get("markets", []) if m["key"] == "h2h"), None)

        if market and len(market["outcomes"]) == 3:
            outcomes = market["outcomes"]
            home_team_name = match_odds_data["home_team"]
            
            price_home = next((o['price'] for o in outcomes if o['name'] == home_team_name), 0)
            price_away = next((o['price'] for o in outcomes if o['name'] == match_odds_data["away_team"]), 0)
            price_draw = next((o['price'] for o in outcomes if o['name'] == "Draw"), 0)

            print(f"DEBUG: home_team_odds={price_home}, draw_odds={price_draw}, away_team_odds={price_away}")

            snapshot_schema = schemas.OddsSnapshotCreate(
                bookmaker=bookmaker["key"],
                price_home=price_home,
                price_draw=price_draw,
                price_away=price_away,
                timestamp=datetime.now(pytz.utc)
            )
            crud.create_odds_snapshot(db, odds_snapshot=snapshot_schema, match_id=match_db_id)
            print(f"Berhasil merekam odds untuk match_db_id: {match_db_id} dari bookmaker: {bookmaker['key']}")
        else:
            print(f"Market 'h2h' tidak ditemukan untuk match {match_api_id}")

    finally:
        db.close()

@celery.task
def discover_new_matches():
    """
    Task untuk mencari pertandingan baru, menyimpannya, dan menjadwalkan pengambilan odds.
    """
    print("Mulai mencari pertandingan baru...")
    db = SessionLocal()
    try:
        upcoming_matches = worker.fetch_upcoming_matches()
        
        for match_data in upcoming_matches:
            api_id = match_data.get("id")
            if not api_id:
                continue

            db_match = crud.get_match_by_api_id(db, api_id=api_id)
            
            if not db_match:
                print(f"Pertandingan baru ditemukan: {match_data['home_team']} vs {match_data['away_team']}")
                commence_time_utc = datetime.fromisoformat(match_data["commence_time"].replace("Z", "+00:00"))
                
                match_schema = schemas.MatchCreate(
                    api_id=api_id,
                    sport_key=match_data["sport_key"],
                    home_team=match_data["home_team"],
                    away_team=match_data["away_team"],
                    commence_time=commence_time_utc
                )
                new_db_match = crud.create_match(db, match=match_schema)

                kick_off_time = new_db_match.commence_time
                snapshot_times = [
                    kick_off_time - timedelta(minutes=60),
                    kick_off_time - timedelta(minutes=20),
                    kick_off_time - timedelta(minutes=5)
                ]

                for exec_time in snapshot_times:
                    if exec_time > datetime.now(pytz.utc):
                        record_odds_snapshot.apply_async(
                            args=[new_db_match.id, new_db_match.api_id],
                            eta=exec_time
                        )
                        print(f"Menjadwalkan snapshot untuk match_id {new_db_match.id} pada {exec_time.isoformat()}")
    finally:
        db.close()

@celery.on_after_configure.connect
@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(hour='*/2', minute='0'), 
        discover_new_matches.s(), 
        name='Cari pertandingan baru setiap 2 jam'
    )
