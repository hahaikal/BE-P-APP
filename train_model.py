import os
import pandas as pd
import numpy as np
import psycopg2
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score
import joblib
import mlflow
from dotenv import load_dotenv
from sqlalchemy import create_engine
import logging
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Muat environment variables
load_dotenv()

# --- PERBAIKAN: Validasi environment variables ---
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_HOST = "postgres"  # Nama service di docker-compose
DB_PORT = "5432"

if not all([DB_USER, DB_PASSWORD, DB_NAME]):
    logging.error("FATAL: Variabel lingkungan database (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB) tidak diatur. Pastikan file .env Anda ada dan sudah benar.")
    exit(1) # Keluar dari skrip jika variabel penting tidak ada

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Definisikan path artefak secara terpusat
ARTIFACTS_DIR = "/app/artifacts"
MODEL_PATH = os.path.join(ARTIFACTS_DIR, "trained_model.joblib")
ENCODER_PATH = os.path.join(ARTIFACTS_DIR, "label_encoder.joblib")
FEATURES_PATH = os.path.join(ARTIFACTS_DIR, "feature_columns.joblib")

def get_training_data(engine):
    """
    Mengambil dan memproses data training dari database dengan logika time bucketing.
    """
    logging.info("Mengambil data training dari database...")
    # Kueri ini mengambil snapshot yang paling dekat dengan T-60, T-20, dan T-5
    query = """
    WITH RankedSnapshots AS (
        SELECT
            m.id as match_id,
            m.home_team,
            m.away_team,
            -- Tentukan hasil pertandingan berdasarkan skor
            CASE
                WHEN m.result_home_score > m.result_away_score THEN 'HOME_WIN'
                WHEN m.result_home_score < m.result_away_score THEN 'AWAY_WIN'
                ELSE 'DRAW'
            END as result,
            s.price_home, s.price_draw, s.price_away,
            s.timestamp,
            m.commence_time,
            -- Beri peringkat pada setiap snapshot berdasarkan kedekatannya dengan target waktu
            ROW_NUMBER() OVER(PARTITION BY m.id ORDER BY ABS(EXTRACT(EPOCH FROM (m.commence_time - s.timestamp)) / 60 - 60)) as rn_60,
            ROW_NUMBER() OVER(PARTITION BY m.id ORDER BY ABS(EXTRACT(EPOCH FROM (m.commence_time - s.timestamp)) / 60 - 20)) as rn_20,
            ROW_NUMBER() OVER(PARTITION BY m.id ORDER BY ABS(EXTRACT(EPOCH FROM (m.commence_time - s.timestamp)) / 60 - 5)) as rn_5
        FROM matches m
        JOIN odds_snapshots s ON m.id = s.match_id
        WHERE m.result_home_score IS NOT NULL AND m.result_away_score IS NOT NULL
    ),
    PivotedData AS (
        -- Ambil snapshot terbaik untuk setiap bucket dan pivot datanya
        SELECT
            match_id,
            MAX(result) as result,
            MAX(CASE WHEN rn_60 = 1 THEN price_home END) as h_t60,
            MAX(CASE WHEN rn_60 = 1 THEN price_draw END) as d_t60,
            MAX(CASE WHEN rn_60 = 1 THEN price_away END) as a_t60,
            MAX(CASE WHEN rn_20 = 1 THEN price_home END) as h_t20,
            MAX(CASE WHEN rn_20 = 1 THEN price_draw END) as d_t20,
            MAX(CASE WHEN rn_20 = 1 THEN price_away END) as a_t20,
            MAX(CASE WHEN rn_5 = 1 THEN price_home END) as h_t5,
            MAX(CASE WHEN rn_5 = 1 THEN price_draw END) as d_t5,
            MAX(CASE WHEN rn_5 = 1 THEN price_away END) as a_t5
        FROM RankedSnapshots
        WHERE rn_60 = 1 OR rn_20 = 1 OR rn_5 = 1
        GROUP BY match_id
    )
    -- Pilih hanya data yang memiliki ketiga snapshot
    SELECT * FROM PivotedData WHERE h_t60 IS NOT NULL AND d_t60 IS NOT NULL AND a_t60 IS NOT NULL
                               AND h_t20 IS NOT NULL AND d_t20 IS NOT NULL AND a_t20 IS NOT NULL
                               AND h_t5 IS NOT NULL AND d_t5 IS NOT NULL AND a_t5 IS NOT NULL;
    """
    df = pd.read_sql(query, engine)
    logging.info(f"Ditemukan {len(df)} baris data training yang valid.")
    return df

def create_features_for_training(df: pd.DataFrame) -> pd.DataFrame:
    """
    Membuat fitur dari data mentah yang sudah di-pivot.
    """
    # 1. Hitung probabilitas implisit
    for t in [60, 20, 5]:
        prob_h = 1 / df[f'h_t{t}']
        prob_d = 1 / df[f'd_t{t}']
        prob_a = 1 / df[f'a_t{t}']
        total_prob = prob_h + prob_d + prob_a
        df[f'h_prob_t{t}'] = prob_h / total_prob
        df[f'd_prob_t{t}'] = prob_d / total_prob
        df[f'a_prob_t{t}'] = prob_a / total_prob

    # 2. Hitung delta odds & probabilitas
    df['delta_h_60_5'] = df['h_t5'] - df['h_t60']
    df['delta_d_60_5'] = df['d_t5'] - df['d_t60']
    df['delta_a_60_5'] = df['a_t5'] - df['a_t60']
    df['delta_prob_h_60_5'] = df['h_prob_t5'] - df['h_prob_t60']
    df['delta_prob_d_60_5'] = df['d_prob_t5'] - df['d_prob_t60']
    df['delta_prob_a_60_5'] = df['a_prob_t5'] - df['a_prob_t60']

    # 3. Hitung volatilitas
    df['volatility_h'] = df[[f'h_t{t}' for t in [60, 20, 5]]].std(axis=1)
    df['volatility_d'] = df[[f'd_t{t}' for t in [60, 20, 5]]].std(axis=1)
    df['volatility_a'] = df[[f'a_t{t}' for t in [60, 20, 5]]].std(axis=1)

    # 4. Fitur final
    df['final_odds_h'] = df['h_t5']
    df['final_odds_d'] = df['d_t5']
    df['final_odds_a'] = df['a_t5']
    df['final_prob_h'] = df['h_prob_t5']
    df['final_prob_d'] = df['d_prob_t5']
    df['final_prob_a'] = df['a_prob_t5']

    feature_columns = [
        'final_odds_h', 'final_odds_d', 'final_odds_a',
        'final_prob_h', 'final_prob_d', 'final_prob_a',
        'delta_h_60_5', 'delta_d_60_5', 'delta_a_60_5',
        'delta_prob_h_60_5', 'delta_prob_d_60_5', 'delta_prob_a_60_5',
        'volatility_h', 'volatility_d', 'volatility_a'
    ]
    return df, feature_columns

def main():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    
    # --- PERBAIKAN: Beri jeda sebelum koneksi DB ---
    logging.info("Menunggu database siap...")
    time.sleep(5) 
    
    engine = create_engine(DATABASE_URL)
    
    mlflow.set_experiment("P-APP Prediction Model v1")
    with mlflow.start_run(run_name="Training LogisticRegression"):
        
        # 1. Ambil & Proses Data
        raw_data = get_training_data(engine)
        if raw_data.empty:
            logging.error("Tidak ada data training yang ditemukan. Proses dihentikan.")
            return
            
        y = raw_data['result']
        X_raw = raw_data.drop(columns=['match_id', 'result'])
        X, feature_names = create_features_for_training(X_raw)
        
        logging.info(f"Feature engineering selesai. {len(feature_names)} fitur dibuat.")

        # 2. Encode Target
        encoder = LabelEncoder()
        y_encoded = encoder.fit_transform(y)
        
        # 3. Split Data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=0.25, random_state=42, stratify=y_encoded
        )
        
        # 4. Latih Model
        model = LogisticRegression(random_state=42, class_weight='balanced', max_iter=1000)
        model.fit(X_train, y_train)
        
        # 5. Evaluasi
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        logging.info(f"Akurasi model: {accuracy:.4f}")
        
        # 6. Log ke MLflow
        mlflow.log_param("model_type", "LogisticRegression")
        mlflow.log_metric("accuracy", accuracy)
        mlflow.sklearn.log_model(model, "model")
        
        # 7. Simpan Artefak
        joblib.dump(model, MODEL_PATH)
        joblib.dump(encoder, ENCODER_PATH)
        joblib.dump(feature_names, FEATURES_PATH)
        logging.info(f"Model dan artefak berhasil disimpan di {ARTIFACTS_DIR}")

if __name__ == "__main__":
    main()
