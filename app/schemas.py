from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# --- OddsSnapshot Schemas ---
class OddsSnapshotBase(BaseModel):
    bookmaker: str
    price_home: float
    price_draw: float
    price_away: float

class OddsSnapshotCreate(OddsSnapshotBase):
    timestamp: datetime

class OddsSnapshot(OddsSnapshotBase):
    id: int
    match_id: int
    timestamp: datetime

    class Config:
        from_attributes = True

# --- Match Schemas ---
class MatchBase(BaseModel):
    api_id: str
    sport_key: str
    home_team: str
    away_team: str
    commence_time: datetime
    result_home_score: Optional[int] = None
    result_away_score: Optional[int] = None

class MatchCreate(MatchBase):
    pass

class Match(MatchBase):
    id: int
    odds_snapshots: list[OddsSnapshot] = []

    class Config:
        from_attributes = True

# --- Prediction Schemas ---
class PredictionOutput(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    prediction: str
    probabilities: dict[str, float]