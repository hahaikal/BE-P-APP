import pandas as pd
import numpy as np

def calculate_implied_probability(df: pd.DataFrame) -> pd.DataFrame:
    """Menghitung probabilitas implisit dari odds."""
    df['h_prob'] = 1 / df['h']
    df['d_prob'] = 1 / df['d']
    df['a_prob'] = 1 / df['a']
    
    # Normalisasi probabilitas agar jumlahnya 100%
    total_prob = df['h_prob'] + df['d_prob'] + df['a_prob']
    df['h_prob'] /= total_prob
    df['d_prob'] /= total_prob
    df['a_prob'] /= total_prob
    return df

def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Membangun fitur dari data odds yang sudah di-pivot.
    Fungsi ini dirancang untuk digunakan baik dalam training maupun prediction.

    Args:
        df (pd.DataFrame): DataFrame dengan kolom-kolom odds yang sudah di-pivot
                           (misal: h_t60, d_t60, a_t60, h_t20, d_t20, dst.).

    Returns:
        pd.DataFrame: DataFrame dengan fitur-fitur yang siap dimasukkan ke model.
    """
    # 1. Hitung probabilitas implisit untuk setiap time bucket
    for t in [60, 20, 5]:
        temp_df = pd.DataFrame({
            'h': df[f'h_t{t}'],
            'd': df[f'd_t{t}'],
            'a': df[f'a_t{t}']
        })
        temp_df = calculate_implied_probability(temp_df)
        df[f'h_prob_t{t}'] = temp_df['h_prob']
        df[f'd_prob_t{t}'] = temp_df['d_prob']
        df[f'a_prob_t{t}'] = temp_df['a_prob']

    # 2. Hitung Pergerakan Odds (Delta) antara T-60 dan T-5
    df['h_delta_60_5'] = df['h_t5'] - df['h_t60']
    df['d_delta_60_5'] = df['d_t5'] - df['d_t60']
    df['a_delta_60_5'] = df['a_t5'] - df['a_t60']

    # 3. Hitung Pergerakan Probabilitas (Delta) antara T-60 dan T-5
    df['h_prob_delta_60_5'] = df['h_prob_t5'] - df['h_prob_t60']
    df['d_prob_delta_60_5'] = df['d_prob_t5'] - df['d_prob_t60']
    df['a_prob_delta_60_5'] = df['a_prob_t5'] - df['a_prob_t60']

    # 4. Hitung Volatilitas (standar deviasi dari odds)
    df['h_volatility'] = df[[f'h_t{t}' for t in [60, 20, 5]]].std(axis=1)
    df['d_volatility'] = df[[f'd_t{t}' for t in [60, 20, 5]]].std(axis=1)
    df['a_volatility'] = df[[f'a_t{t}' for t in [60, 20, 5]]].std(axis=1)
    
    # 5. Hitung Volatilitas Probabilitas
    df['h_prob_volatility'] = df[[f'h_prob_t{t}' for t in [60, 20, 5]]].std(axis=1)
    df['d_prob_volatility'] = df[[f'd_prob_t{t}' for t in [60, 20, 5]]].std(axis=1)
    df['a_prob_volatility'] = df[[f'a_prob_t{t}' for t in [60, 20, 5]]].std(axis=1)

    # 6. Fitur Final: Odds dan Probabilitas terakhir (T-5) dianggap paling relevan
    df['final_h_odds'] = df['h_t5']
    df['final_d_odds'] = df['d_t5']
    df['final_a_odds'] = df['a_t5']
    df['final_h_prob'] = df['h_prob_t5']
    df['final_d_prob'] = df['d_prob_t5']
    df['final_a_prob'] = df['a_prob_t5']
    
    # Pilih kolom fitur yang akan digunakan oleh model
    feature_columns = [
        'final_h_odds', 'final_d_odds', 'final_a_odds',
        'final_h_prob', 'final_d_prob', 'final_a_prob',
        'h_delta_60_5', 'd_delta_60_5', 'a_delta_60_5',
        'h_prob_delta_60_5', 'd_prob_delta_60_5', 'a_prob_delta_60_5',
        'h_volatility', 'd_volatility', 'a_volatility',
        'h_prob_volatility', 'd_prob_volatility', 'a_prob_volatility'
    ]
    
    # Pastikan semua kolom ada, isi dengan 0 jika tidak ada (untuk keamanan)
    for col in feature_columns:
        if col not in df.columns:
            df[col] = 0
            
    return df[feature_columns]

