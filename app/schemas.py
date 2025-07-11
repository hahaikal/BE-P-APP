from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Dict

# ======================================================================
# Skema untuk Odds
# ======================================================================

class OddsSnapshotBase(BaseModel):
    bookmaker: str
    price_home: float
    price_away: float
    price_draw: float

class OddsSnapshotCreate(OddsSnapshotBase):
    pass

class OddsSnapshot(OddsSnapshotBase):
    id: int
    match_id: int
    # ===== PERBAIKAN DI SINI =====
    # Field 'snapshot_time' sekarang bersifat opsional.
    # Ini akan menerima nilai NULL dari database tanpa menyebabkan error.
    snapshot_time: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

# ======================================================================
# Skema untuk Pertandingan (Match)
# ======================================================================

class MatchBase(BaseModel):
    sport_key: str
    home_team: str
    away_team: str
    commence_time: datetime

class MatchCreate(MatchBase):
    api_id: str

class Match(MatchBase):
    id: int
    api_id: str
    result_home_score: int | None = None
    result_away_score: int | None = None
    
    # List ini sekarang akan menggunakan skema OddsSnapshot yang sudah diperbaiki
    odds_snapshots: List[OddsSnapshot] = []

    # Konfigurasi ini mengizinkan Pydantic untuk membaca data
    # langsung dari model ORM (SQLAlchemy).
    model_config = ConfigDict(from_attributes=True)

# ======================================================================
# Skema untuk Prediksi
# ======================================================================

class MatchPredictionPayload(BaseModel):
    home_team: str
    away_team: str

class MatchPredictionResult(BaseModel):
    home_team: str
    away_team: str
    predicted_outcome: str
    prediction_probabilities: Dict[str, float]

class PredictionOutput(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    prediction: str
    probabilities: dict[str, float]