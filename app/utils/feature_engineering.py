import pandas as pd
from typing import List, Dict, Any
from .. import model # Menggunakan model.OddsSnapshot

def process_odds_to_features(snapshots: List[model.OddsSnapshot]) -> Dict[str, Any]:
    """
    Mengubah 3 odds snapshot terakhir menjadi satu baris fitur untuk prediksi.
    Fungsi ini dirancang untuk dipanggil dari endpoint API.

    Args:
        snapshots (List[model.OddsSnapshot]): Daftar berisi 3 objek OddsSnapshot,
                                             diurutkan dari yang terbaru ke terlama.

    Returns:
        Dict[str, Any]: Dictionary yang berisi fitur-fitur yang telah dihitung.
    """
    if len(snapshots) < 3:
        return {}

    # Asumsi: snapshots[0] adalah T-5, snapshots[1] adalah T-20, snapshots[2] adalah T-60
    # Ini karena kita mengambil 3 terakhir dan diurutkan secara descending dari DB.
    try:
        raw_data = {
            "h_t60": snapshots[2].price_home, "d_t60": snapshots[2].price_draw, "a_t60": snapshots[2].price_away,
            "h_t20": snapshots[1].price_home, "d_t20": snapshots[1].price_draw, "a_t20": snapshots[1].price_away,
            "h_t5":  snapshots[0].price_home, "d_t5":  snapshots[0].price_draw, "a_t5":  snapshots[0].price_away,
        }
        df = pd.DataFrame([raw_data])
    except IndexError:
        return {}

    # 1. Hitung probabilitas implisit untuk setiap time bucket
    for t in [60, 20, 5]:
        h_col, d_col, a_col = f'h_t{t}', f'd_t{t}', f'a_t{t}'
        h_prob_col, d_prob_col, a_prob_col = f'h_prob_t{t}', f'd_prob_t{t}', f'a_prob_t{t}'
        
        prob_h = 1 / df[h_col]
        prob_d = 1 / df[d_col]
        prob_a = 1 / df[a_col]
        total_prob = prob_h + prob_d + prob_a
        
        df[h_prob_col] = prob_h / total_prob
        df[d_prob_col] = prob_d / total_prob
        df[a_prob_col] = prob_a / total_prob

    # 2. Hitung Pergerakan Odds (Delta) antara T-60 dan T-5
    df['delta_h_60_5'] = df['h_t5'] - df['h_t60']
    df['delta_d_60_5'] = df['d_t5'] - df['d_t60']
    df['delta_a_60_5'] = df['a_t5'] - df['a_t60']

    # 3. Hitung Pergerakan Probabilitas (Delta) antara T-60 dan T-5
    df['delta_prob_h_60_5'] = df['h_prob_t5'] - df['h_prob_t60']
    df['delta_prob_d_60_5'] = df['d_prob_t5'] - df['d_prob_t60']
    df['delta_prob_a_60_5'] = df['a_prob_t5'] - df['a_prob_t60']

    # 4. Hitung Volatilitas (standar deviasi dari odds)
    df['volatility_h'] = df[[f'h_t{t}' for t in [60, 20, 5]]].std(axis=1)
    df['volatility_d'] = df[[f'd_t{t}' for t in [60, 20, 5]]].std(axis=1)
    df['volatility_a'] = df[[f'a_t{t}' for t in [60, 20, 5]]].std(axis=1)
    
    # 5. Fitur Final: Odds dan Probabilitas terakhir (T-5) dianggap paling relevan
    df['final_odds_h'] = df['h_t5']
    df['final_odds_d'] = df['d_t5']
    df['final_odds_a'] = df['a_t5']
    df['final_prob_h'] = df['h_prob_t5']
    df['final_prob_d'] = df['d_prob_t5']
    df['final_prob_a'] = df['a_prob_t5']
    
    # Mengembalikan baris pertama dari DataFrame sebagai dictionary
    return df.to_dict(orient='records')[0]
