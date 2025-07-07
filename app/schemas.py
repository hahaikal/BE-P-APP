from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict

# ======================================================================
# Skema untuk Odds
# ======================================================================

class OddsSnapshotBase(BaseModel):
    bookmaker: str
    home_team_odds: float
    away_team_odds: float
    draw_odds: float

class OddsSnapshotCreate(OddsSnapshotBase):
    pass

class OddsSnapshot(OddsSnapshotBase):
    id: int
    match_id: int
    snapshot_time: datetime

    model_config = ConfigDict(from_attributes=True) # Untuk Pydantic v2
    # class Config: # Untuk Pydantic v1
    #     orm_mode = True

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
    result_home_score: Optional[int] = None
    result_away_score: Optional[int] = None
    odds_snapshots: List[OddsSnapshot] = []

    # --- INI BAGIAN PENTING YANG MEMPERBAIKI MASALAH ---
    # Konfigurasi ini mengizinkan Pydantic untuk membaca data
    # langsung dari model ORM (SQLAlchemy).
    model_config = ConfigDict(from_attributes=True) # Untuk Pydantic v2
    # class Config: # Untuk Pydantic v1
    #     orm_mode = True
    # --- SELESAI ---

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
