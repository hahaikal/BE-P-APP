import pandas as pd
import numpy as np
import joblib
import mlflow
import mlflow.sklearn
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_data_from_db():
    """Mengambil data mentah dari database."""
    # ... (komentar penjelasan tetap sama)
    print("Membuat data dummy untuk pelatihan...")
    data = {
        'match_id': [
            1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6,
            7, 7, 7, 8, 8, 8, 9, 9, 9, 10, 10, 10
        ],
        'interval_marker': [
            60, 20, 5, 60, 20, 5, 60, 20, 5, 60, 20, 5, 60, 20, 5, 60, 20, 5,
            60, 20, 5, 60, 20, 5, 60, 20, 5, 60, 20, 5
        ],
        'odds_home': [
            2.1, 2.0, 1.9, 1.5, 1.55, 1.6, 3.0, 3.1, 3.0, 2.2, 2.1, 2.0, 1.6, 1.7, 1.8, 3.1, 3.1, 3.2,
            2.0, 2.1, 2.2, 1.7, 1.65, 1.6, 2.8, 2.9, 3.0, 1.9, 1.85, 1.8
        ],
        'odds_draw': [
            3.0, 3.1, 3.2, 4.0, 3.9, 3.8, 2.5, 2.5, 2.4, 3.1, 3.2, 3.3, 4.1, 4.0, 3.9, 2.6, 2.5, 2.5,
            3.2, 3.3, 3.4, 3.8, 3.9, 4.0, 2.6, 2.7, 2.8, 3.5, 3.6, 3.7
        ],
        'odds_away': [
            2.5, 2.6, 2.8, 4.5, 4.3, 4.1, 1.8, 1.7, 1.75, 2.4, 2.5, 2.7, 4.6, 4.4, 4.2, 1.9, 1.8, 1.8,
            2.7, 2.8, 2.9, 4.0, 4.1, 4.2, 1.7, 1.6, 1.5, 2.0, 2.1, 2.2
        ],
        'result': [
            'HOME_WIN', 'HOME_WIN', 'HOME_WIN', 
            'AWAY_WIN', 'AWAY_WIN', 'AWAY_WIN', 
            'DRAW', 'DRAW', 'DRAW',
            'HOME_WIN', 'HOME_WIN', 'HOME_WIN',
            'AWAY_WIN', 'AWAY_WIN', 'AWAY_WIN',
            'DRAW', 'DRAW', 'DRAW',
            'HOME_WIN', 'HOME_WIN', 'HOME_WIN',
            'AWAY_WIN', 'AWAY_WIN', 'AWAY_WIN',
            'DRAW', 'DRAW', 'DRAW',
            'HOME_WIN', 'HOME_WIN', 'HOME_WIN'
        ]
    }
    return pd.DataFrame(data)

def engineer_features(df):
    """Melakukan rekayasa fitur sesuai dokumen proyek."""
    # Pivot tabel agar setiap baris adalah satu pertandingan unik
    pivot_df = df.pivot_table(
        index='match_id', 
        columns='interval_marker', 
        values=['odds_home', 'odds_draw', 'odds_away']
    )
    pivot_df.columns = [f'{val}_{col}' for val, col in pivot_df.columns]
    
    # Ambil hasil pertandingan
    results = df.groupby('match_id')['result'].first()
    featured_df = pivot_df.join(results)

    # 1. Fitur Pergerakan Odds (Delta)
    featured_df['delta_home_60_20'] = featured_df['odds_home_20'] - featured_df['odds_home_60']
    featured_df['delta_home_20_5'] = featured_df['odds_home_5'] - featured_df['odds_home_20']

    # 2. Fitur Volatilitas Odds (Standar Deviasi)
    home_odds_cols = ['odds_home_60', 'odds_home_20', 'odds_home_5']
    featured_df['volatility_home'] = featured_df[home_odds_cols].std(axis=1)

    # 3. Fitur Probabilitas Implisit (diambil dari odds terakhir T-5)
    for outcome in ['home', 'draw', 'away']:
        featured_df[f'prob_{outcome}'] = 1 / featured_df[f'odds_{outcome}_5']
    
    # Normalisasi probabilitas agar jumlahnya 1
    prob_cols = ['prob_home', 'prob_draw', 'prob_away']
    total_prob = featured_df[prob_cols].sum(axis=1)
    for col in prob_cols:
        featured_df[col] = featured_df[col] / total_prob

    return featured_df.dropna()


if __name__ == "__main__":
    with mlflow.start_run():
        print("Memulai pipeline pelatihan model...")
        
        # 1. Ambil & proses data
        raw_data = get_data_from_db()
        featured_data = engineer_features(raw_data)

        # 2. Siapkan data untuk Scikit-learn
        features = [col for col in featured_data.columns if col != 'result']
        X = featured_data[features]
        y_raw = featured_data['result']

        # Encode target variable
        encoder = LabelEncoder()
        y = encoder.fit_transform(y_raw)
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
        
        # 3. Latih model
        model = LogisticRegression(random_state=42)
        model.fit(X_train, y_train)

        # 4. Evaluasi & Log ke MLflow
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Akurasi Model: {accuracy:.2f}")

        mlflow.log_param("model_type", "LogisticRegression")
        mlflow.log_metric("accuracy", accuracy)
        
        # 5. Simpan semua artefak
        columns_path = "feature_columns.joblib"
        joblib.dump(list(X.columns), columns_path)
        print(f"Nama kolom fitur berhasil disimpan di: {columns_path}")

        model_path = "trained_model.joblib"
        joblib.dump(model, model_path)
        print(f"Model berhasil disimpan di: {model_path}")

        encoder_path = "label_encoder.joblib"
        joblib.dump(encoder, encoder_path)
        print(f"Encoder berhasil disimpan di: {encoder_path}")

        mlflow.sklearn.log_model(model, "model", input_example=X_train.head(1))

        print("Pipeline selesai.")