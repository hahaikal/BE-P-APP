import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score
import joblib
import mlflow
from dotenv import load_dotenv
from sqlalchemy import create_engine
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_HOST = "postgres"
DB_PORT = "5432"

if not all([DB_USER, DB_PASSWORD, DB_NAME]):
    logging.error("FATAL: Variabel lingkungan database tidak diatur.")
    exit(1)

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

ARTIFACTS_DIR = "/app/artifacts"
MODEL_PATH = os.path.join(ARTIFACTS_DIR, "trained_model.joblib")
ENCODER_PATH = os.path.join(ARTIFACTS_DIR, "label_encoder.joblib")
FEATURES_PATH = os.path.join(ARTIFACTS_DIR, "feature_columns.joblib")

def get_training_data(engine):
    """
    Mengambil data training dari database, termasuk data H2H dan Handicap.
    """
    logging.info("Mengambil data training (H2H & Handicap) dari database...")
    query = """
    WITH RankedSnapshots AS (
        SELECT
            m.id as match_id,
            CASE
                WHEN m.result_home_score > m.result_away_score THEN 'HOME_WIN'
                WHEN m.result_home_score < m.result_away_score THEN 'AWAY_WIN'
                ELSE 'DRAW'
            END as result,
            s.price_home, s.price_draw, s.price_away,
            s.handicap_line, s.handicap_price_home, s.handicap_price_away,
            ROW_NUMBER() OVER(PARTITION BY m.id ORDER BY ABS(EXTRACT(EPOCH FROM (m.commence_time - s.timestamp)) / 60 - 60)) as rn_60,
            ROW_NUMBER() OVER(PARTITION BY m.id ORDER BY ABS(EXTRACT(EPOCH FROM (m.commence_time - s.timestamp)) / 60 - 20)) as rn_20,
            ROW_NUMBER() OVER(PARTITION BY m.id ORDER BY ABS(EXTRACT(EPOCH FROM (m.commence_time - s.timestamp)) / 60 - 5)) as rn_5
        FROM matches m
        JOIN odds_snapshots s ON m.id = s.match_id
        WHERE m.result_home_score IS NOT NULL AND m.result_away_score IS NOT NULL
    ),
    PivotedData AS (
        SELECT
            match_id,
            MAX(result) as result,
            MAX(CASE WHEN rn_60 = 1 THEN price_home END) as h2h_h_t60,
            MAX(CASE WHEN rn_60 = 1 THEN price_draw END) as h2h_d_t60,
            MAX(CASE WHEN rn_60 = 1 THEN price_away END) as h2h_a_t60,
            MAX(CASE WHEN rn_60 = 1 THEN handicap_line END) as hcap_line_t60,
            MAX(CASE WHEN rn_60 = 1 THEN handicap_price_home END) as hcap_h_t60,
            MAX(CASE WHEN rn_60 = 1 THEN handicap_price_away END) as hcap_a_t60,
            MAX(CASE WHEN rn_20 = 1 THEN price_home END) as h2h_h_t20,
            MAX(CASE WHEN rn_20 = 1 THEN price_draw END) as h2h_d_t20,
            MAX(CASE WHEN rn_20 = 1 THEN price_away END) as h2h_a_t20,
            MAX(CASE WHEN rn_20 = 1 THEN handicap_line END) as hcap_line_t20,
            MAX(CASE WHEN rn_20 = 1 THEN handicap_price_home END) as hcap_h_t20,
            MAX(CASE WHEN rn_20 = 1 THEN handicap_price_away END) as hcap_a_t20,
            MAX(CASE WHEN rn_5 = 1 THEN price_home END) as h2h_h_t5,
            MAX(CASE WHEN rn_5 = 1 THEN price_draw END) as h2h_d_t5,
            MAX(CASE WHEN rn_5 = 1 THEN price_away END) as h2h_a_t5,
            MAX(CASE WHEN rn_5 = 1 THEN handicap_line END) as hcap_line_t5,
            MAX(CASE WHEN rn_5 = 1 THEN handicap_price_home END) as hcap_h_t5,
            MAX(CASE WHEN rn_5 = 1 THEN handicap_price_away END) as hcap_a_t5
        FROM RankedSnapshots
        WHERE rn_60 = 1 OR rn_20 = 1 OR rn_5 = 1
        GROUP BY match_id
    )
    SELECT * FROM PivotedData WHERE h2h_h_t5 IS NOT NULL;
    """
    df = pd.read_sql(query, engine)
    logging.info(f"Ditemukan {len(df)} baris data training mentah.")
    
    df_clean = df.dropna(subset=[col for col in df.columns if 'hcap' in col])
    logging.info(f"Ditemukan {len(df_clean)} baris data dengan data handicap lengkap.")
    
    return df_clean

def create_features_for_training(df: pd.DataFrame) -> (pd.DataFrame, list):
    """
    Membuat fitur dari data mentah H2H dan Handicap.
    """
    
    for t in [60, 20, 5]:
        prob_h = 1 / df[f'h2h_h_t{t}']
        prob_d = 1 / df[f'h2h_d_t{t}']
        prob_a = 1 / df[f'h2h_a_t{t}']
        total_prob = prob_h + prob_d + prob_a
        df[f'h2h_prob_h_t{t}'] = prob_h / total_prob
        df[f'h2h_prob_d_t{t}'] = prob_d / total_prob
        df[f'h2h_prob_a_t{t}'] = prob_a / total_prob

    df['h2h_delta_h_60_5'] = df['h2h_h_t5'] - df['h2h_h_t60']
    df['h2h_delta_d_60_5'] = df['h2h_d_t5'] - df['h2h_d_t60']
    df['h2h_delta_a_60_5'] = df['h2h_a_t5'] - df['h2h_a_t60']
    df['h2h_volatility_h'] = df[[f'h2h_h_t{t}' for t in [60, 20, 5]]].std(axis=1)
    df['h2h_volatility_d'] = df[[f'h2h_d_t{t}' for t in [60, 20, 5]]].std(axis=1)
    df['h2h_volatility_a'] = df[[f'h2h_a_t{t}' for t in [60, 20, 5]]].std(axis=1)

    df['final_handicap_line'] = df['hcap_line_t5'] 
    df['delta_handicap_line_60_5'] = df['hcap_line_t5'] - df['hcap_line_t60']

    for t in [60, 20, 5]:
        prob_h = 1 / df[f'hcap_h_t{t}']
        prob_a = 1 / df[f'hcap_a_t{t}']
        total_prob = prob_h + prob_a
        df[f'hcap_prob_h_t{t}'] = prob_h / total_prob
        df[f'hcap_prob_a_t{t}'] = prob_a / total_prob

    df['hcap_volatility_h'] = df[[f'hcap_h_t{t}' for t in [60, 20, 5]]].std(axis=1)
    df['hcap_volatility_a'] = df[[f'hcap_a_t{t}' for t in [60, 20, 5]]].std(axis=1)

    feature_columns = [
        'h2h_h_t5', 'h2h_d_t5', 'h2h_a_t5',
        'h2h_prob_h_t5', 'h2h_prob_d_t5', 'h2h_prob_a_t5',
        'h2h_delta_h_60_5', 'h2h_delta_d_60_5', 'h2h_delta_a_60_5',
        'h2h_volatility_h', 'h2h_volatility_d', 'h2h_volatility_a',
        'final_handicap_line',
        'delta_handicap_line_60_5',
        'hcap_prob_h_t5', 'hcap_prob_a_t5',
        'hcap_volatility_h', 'hcap_volatility_a'
    ]
    
    return df[feature_columns], feature_columns

def main():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    
    logging.info("Menunggu database siap...")
    time.sleep(5) 
    
    engine = create_engine(DATABASE_URL)
    
    mlflow.set_experiment("P-APP Prediction Model v1.1")
    with mlflow.start_run(run_name="Training LogisticRegression with Handicap Features"):
        
        raw_data = get_training_data(engine)
        if raw_data.empty:
            logging.error("Tidak ada data training dengan handicap lengkap. Proses dihentikan.")
            return
            
        y = raw_data['result']
        X_raw = raw_data.drop(columns=['match_id', 'result'])
        X, feature_names = create_features_for_training(X_raw)
        
        logging.info(f"Feature engineering selesai. {len(feature_names)} fitur dibuat.")
        mlflow.log_param("features", feature_names)

        encoder = LabelEncoder()
        y_encoded = encoder.fit_transform(y)
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=0.25, random_state=42, stratify=y_encoded
        )
        
        pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='mean')),
            ('scaler', StandardScaler()),
            ('classifier', LogisticRegression(random_state=42, class_weight='balanced', max_iter=1000))
        ])
        
        pipeline.fit(X_train, y_train)
        
        y_pred = pipeline.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        logging.info(f"Akurasi model v1.1: {accuracy:.4f}")
        
        mlflow.log_param("model_type", "LogisticRegression_with_Handicap")
        mlflow.log_metric("accuracy", accuracy)
        mlflow.sklearn.log_model(pipeline, "model")
        
        joblib.dump(pipeline, MODEL_PATH)
        joblib.dump(encoder, ENCODER_PATH)
        joblib.dump(feature_names, FEATURES_PATH)
        logging.info(f"Model v1.1 dan artefak berhasil disimpan di {ARTIFACTS_DIR}")

if __name__ == "__main__":
    main()
