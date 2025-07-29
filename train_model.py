import pandas as pd
import joblib
import mlflow
import os
import logging
from datetime import datetime

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score

# Impor untuk koneksi database dan model
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from app.model import Match, OddsSnapshot, Base
from app.utils.feature_engineering import select_time_bucketed_snapshots, process_odds_to_features, get_target

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Konfigurasi ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/p_app_db")
ARTIFACTS_DIR = "artifacts"
MODEL_PATH = os.path.join(ARTIFACTS_DIR, "trained_model.joblib")
ENCODER_PATH = os.path.join(ARTIFACTS_DIR, "label_encoder.joblib")
FEATURES_PATH = os.path.join(ARTIFACTS_DIR, "feature_columns.joblib")

def get_data_from_db(session):
    """
    Mengambil data pertandingan yang sudah lengkap dari database.
    Lengkap = memiliki skor akhir dan minimal 3 snapshot odds.
    """
    logging.info("Mengambil data pertandingan lengkap dari database...")
    
    completed_matches = session.query(Match).options(
        joinedload(Match.odds_snapshots)
    ).filter(
        Match.result_home_score.isnot(None),
        Match.odds_snapshots.any() 
    ).all()
    
    logging.info(f"Ditemukan {len(completed_matches)} pertandingan dengan skor.")
    
    processed_data = []
    for match in completed_matches:
        if len(match.odds_snapshots) < 3:
            continue

        # --- PERBAIKAN FINAL ---
        # Menggunakan atribut 'commence_time' yang benar sesuai hasil debug.
        selected_snapshots = select_time_bucketed_snapshots(match.odds_snapshots, match.commence_time)
        
        if len(selected_snapshots) == 0:
            continue

        features = process_odds_to_features(selected_snapshots)
        features['target'] = get_target(match)
        
        processed_data.append(features)
        
    logging.info(f"Berhasil memproses {len(processed_data)} pertandingan menjadi dataset.")
    return pd.DataFrame(processed_data)

def main():
    """Fungsi utama untuk menjalankan pipeline training model."""
    logging.info("Memulai pipeline training model v1.0...")

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()

    try:
        df = get_data_from_db(db_session)
        
        if df.empty or 'target' not in df.columns or df['target'].nunique() < 2:
            logging.error("Dataset tidak cukup untuk training. Periksa data di database.")
            return

        X = df.drop('target', axis=1)
        y = df['target']

        encoder = LabelEncoder()
        y_encoded = encoder.fit_transform(y)
        logging.info(f"Label target di-encode. Kelas: {encoder.classes_}")

        X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded)
        logging.info(f"Data dibagi: {len(X_train)} train, {len(X_test)} test.")

        feature_columns = X_train.columns.tolist()
        joblib.dump(feature_columns, FEATURES_PATH)
        logging.info(f"Kolom fitur disimpan di {FEATURES_PATH}")
        
        mlflow.set_experiment("P-APP Predictions")
        with mlflow.start_run(run_name=f"LogisticRegression_Training_{datetime.now().strftime('%Y%m%d_%H%M')}_v1"):
            logging.info("Memulai training model Logistic Regression...")
            
            model = LogisticRegression(random_state=42, max_iter=1000)
            model.fit(X_train, y_train)
            
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            logging.info(f"Akurasi model pada data test: {accuracy:.4f}")
            
            mlflow.log_param("model_type", "LogisticRegression")
            mlflow.log_metric("accuracy", accuracy)
            mlflow.sklearn.log_model(model, "model")

            joblib.dump(model, MODEL_PATH)
            joblib.dump(encoder, ENCODER_PATH)
            logging.info(f"✅ Model berhasil dilatih dan disimpan di {MODEL_PATH}")
            logging.info(f"✅ Encoder berhasil disimpan di {ENCODER_PATH}")

    finally:
        db_session.close()

if __name__ == "__main__":
    main()
