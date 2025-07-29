import pandas as pd
from datetime import timedelta
from typing import List
from .. import model # Menggunakan model SQLAlchemy

def select_time_bucketed_snapshots(snapshots: List[model.OddsSnapshot], match_time: pd.Timestamp) -> List[model.OddsSnapshot]:
    """
    Memilih hingga 3 snapshot yang paling mendekati T-60, T-20, dan T-5 menit.
    Ini memastikan kita mendapatkan data dari titik-titik waktu yang paling relevan.
    
    Args:
        snapshots: Daftar objek OddsSnapshot dari database.
        match_time: Waktu kick-off pertandingan.

    Returns:
        Daftar snapshot yang telah dipilih dan diurutkan.
    """
    if not snapshots:
        return []

    # Tentukan target waktu kita
    target_times = {
        "t_minus_60": match_time - timedelta(minutes=60),
        "t_minus_20": match_time - timedelta(minutes=20),
        "t_minus_5": match_time - timedelta(minutes=5),
    }

    selected_snapshots = {}
    for key, target_time in target_times.items():
        # Cari snapshot dengan selisih waktu absolut terkecil ke target
        best_snapshot = min(
            snapshots, 
            key=lambda s: abs(s.timestamp - target_time)
        )
        # Gunakan ID snapshot untuk memastikan keunikan jika satu snapshot paling dekat dengan beberapa target
        selected_snapshots[best_snapshot.id] = best_snapshot

    # Kembalikan daftar snapshot unik yang sudah diurutkan berdasarkan waktu
    return sorted(list(selected_snapshots.values()), key=lambda s: s.timestamp)


def process_odds_to_features(snapshots: List[model.OddsSnapshot]) -> dict:
    """
    Memproses daftar 1 hingga 3 snapshot odds menjadi fitur-fitur machine learning.
    Ini adalah inti dari feature engineering kita.

    Args:
        snapshots: Daftar 1-3 objek OddsSnapshot yang sudah dipilih.

    Returns:
        Sebuah dictionary yang berisi fitur-fitur yang siap dipakai model.
    """
    features = {}
    
    # Pastikan snapshot diurutkan berdasarkan waktu untuk konsistensi
    snapshots.sort(key=lambda s: s.timestamp)

    def safe_float(value):
        """Convert None or invalid values to 0.0"""
        if value is None or pd.isna(value):
            return 0.0
        return float(value)

    # Fungsi helper untuk menghitung probabilitas implisit dari odds
    def get_implied_prob(s):
        # Menghindari pembagian dengan nol jika odds tidak valid atau NaN
        price_home = safe_float(s.price_home)
        price_draw = safe_float(s.price_draw)
        price_away = safe_float(s.price_away)
        
        if price_home == 0 or price_draw == 0 or price_away == 0:
            return 0.0
        return (1/price_home) + (1/price_draw) + (1/price_away)

    # Fitur dari snapshot terbaru (s3)
    if len(snapshots) > 0:
        s_latest = snapshots[-1]
        features['h_odds_s3'] = safe_float(s_latest.price_home)
        features['d_odds_s3'] = safe_float(s_latest.price_draw)
        features['a_odds_s3'] = safe_float(s_latest.price_away)
        features['imp_prob_s3'] = get_implied_prob(s_latest)
    else:
        features['h_odds_s3'] = 0.0
        features['d_odds_s3'] = 0.0
        features['a_odds_s3'] = 0.0
        features['imp_prob_s3'] = 0.0

    # Fitur dari snapshot kedua terakhir (s2)
    if len(snapshots) > 1:
        s_mid = snapshots[-2]
        features['h_odds_s2'] = safe_float(s_mid.price_home)
        features['d_odds_s2'] = safe_float(s_mid.price_draw)
        features['a_odds_s2'] = safe_float(s_mid.price_away)
        features['imp_prob_s2'] = get_implied_prob(s_mid)
        
        # Fitur Delta: Pergerakan odds antara s2 dan s3
        features['delta_h_s3_s2'] = features['h_odds_s3'] - features['h_odds_s2']
        features['delta_d_s3_s2'] = features['d_odds_s3'] - features['d_odds_s2']
        features['delta_a_s3_s2'] = features['a_odds_s3'] - features['a_odds_s2']
    else:
        features['h_odds_s2'] = 0.0
        features['d_odds_s2'] = 0.0
        features['a_odds_s2'] = 0.0
        features['imp_prob_s2'] = 0.0
        features['delta_h_s3_s2'] = 0.0
        features['delta_d_s3_s2'] = 0.0
        features['delta_a_s3_s2'] = 0.0

    # Fitur dari snapshot paling awal (s1)
    if len(snapshots) > 2:
        s_first = snapshots[-3]
        features['h_odds_s1'] = safe_float(s_first.price_home)
        features['d_odds_s1'] = safe_float(s_first.price_draw)
        features['a_odds_s1'] = safe_float(s_first.price_away)
        features['imp_prob_s1'] = get_implied_prob(s_first)

        # Fitur Delta: Pergerakan odds antara s1 dan s2
        features['delta_h_s2_s1'] = features['h_odds_s2'] - features['h_odds_s1']
        features['delta_d_s2_s1'] = features['d_odds_s2'] - features['d_odds_s1']
        features['delta_a_s2_s1'] = features['a_odds_s2'] - features['a_odds_s1']

        # Fitur Volatilitas: Seberapa stabil pergerakan odds
        all_h_odds = [safe_float(s.price_home) for s in snapshots]
        all_d_odds = [safe_float(s.price_draw) for s in snapshots]
        all_a_odds = [safe_float(s.price_away) for s in snapshots]
        
        # Handle NaN in std() by using fillna(0.0) and checking for NaN
        vol_h = pd.Series(all_h_odds).std()
        vol_d = pd.Series(all_d_odds).std()
        vol_a = pd.Series(all_a_odds).std()
        
        features['volatility_h'] = 0.0 if pd.isna(vol_h) else vol_h
        features['volatility_d'] = 0.0 if pd.isna(vol_d) else vol_d
        features['volatility_a'] = 0.0 if pd.isna(vol_a) else vol_a
    else:
        features['h_odds_s1'] = 0.0
        features['d_odds_s1'] = 0.0
        features['a_odds_s1'] = 0.0
        features['imp_prob_s1'] = 0.0
        features['delta_h_s2_s1'] = 0.0
        features['delta_d_s2_s1'] = 0.0
        features['delta_a_s2_s1'] = 0.0
        features['volatility_h'] = 0.0
        features['volatility_d'] = 0.0
        features['volatility_a'] = 0.0

    return features

def get_target(match: model.Match) -> str:
    """
    Menentukan hasil akhir pertandingan (target variable) dari skor.
    """
    if match.result_home_score is None or match.result_away_score is None:
        return "UNKNOWN"
    if match.result_home_score > match.result_away_score:
        return "HOME_WIN"
    elif match.result_home_score < match.result_away_score:
        return "AWAY_WIN"
    else:
        return "DRAW"
