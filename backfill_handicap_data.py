import os
import requests
import logging
from datetime import datetime, timedelta
import time

from app.database import SessionLocal
from app import crud, model, worker

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_backfill():
    """
    Skrip satu kali jalan untuk mengisi data handicap yang kosong
    pada odds_snapshots yang sudah ada.
    """
    logger.info("Memulai proses backfill data handicap...")
    db = SessionLocal()
    
    try:
        # 1. Ambil semua pertandingan dari database
        all_matches = db.query(model.Match).all()
        logger.info(f"Ditemukan {len(all_matches)} pertandingan untuk diproses.")
        
        for i, match in enumerate(all_matches):
            logger.info(f"[{i+1}/{len(all_matches)}] Memproses match: {match.home_team} vs {match.away_team} (ID: {match.id})")
            
            # 2. Cek apakah match ini sudah punya data handicap
            # Jika sudah ada, kita bisa melewatinya untuk efisiensi
            has_handicap_data = db.query(model.OddsSnapshot).filter(
                model.OddsSnapshot.match_id == match.id,
                model.OddsSnapshot.handicap_line.isnot(None)
            ).first()
            
            if has_handicap_data:
                logger.info(f"Match ID {match.id} sudah memiliki data handicap. Melewatkan.")
                continue

            # 3. Ambil data odds baru dari API, termasuk spreads
            # Kita hanya perlu satu panggilan per pertandingan
            match_odds_data = worker.fetch_odds_for_match(match.api_id, match.sport_key, markets="h2h,spreads")
            
            if not match_odds_data or not match_odds_data.get("bookmakers"):
                logger.warning(f"Tidak ada data odds dari API untuk match api_id: {match.api_id}. Melewatkan.")
                continue
            
            # Ambil data dari bookmaker pertama
            bookmaker = match_odds_data["bookmakers"][0]
            spreads_data = None
            for market in bookmaker.get("markets", []):
                if market.get("key") == "spreads":
                    spreads_data = market.get("outcomes")
                    break # Keluar dari loop setelah menemukan market spreads

            # 4. Jika data handicap (spreads) ditemukan, update semua snapshot untuk match ini
            if spreads_data and len(spreads_data) == 2:
                home_spread = next((s for s in spreads_data if s["name"] == match.home_team), None)
                away_spread = next((s for s in spreads_data if s["name"] == match.away_team), None)

                if home_spread and away_spread:
                    handicap_line = home_spread["point"]
                    handicap_price_home = home_spread["price"]
                    handicap_price_away = away_spread["price"]
                    
                    # Lakukan UPDATE pada semua snapshot milik match ini
                    updated_rows = db.query(model.OddsSnapshot).filter(
                        model.OddsSnapshot.match_id == match.id
                    ).update({
                        "handicap_line": handicap_line,
                        "handicap_price_home": handicap_price_home,
                        "handicap_price_away": handicap_price_away
                    })
                    db.commit()
                    logger.info(f"✅ Berhasil mem-backfill {updated_rows} snapshot untuk match ID {match.id} dengan handicap line: {handicap_line}")
                else:
                    logger.warning(f"Data spreads tidak lengkap untuk match ID {match.id}")
            else:
                logger.warning(f"Tidak ditemukan market 'spreads' untuk match ID {match.id}")

            # Beri jeda antar panggilan API agar tidak membebani server
            time.sleep(2) # Jeda 2 detik

    except Exception as e:
        logger.error(f"Terjadi error saat proses backfill: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
        logger.info("Proses backfill selesai.")

if __name__ == "__main__":
    run_backfill()

