from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Dict, Optional
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
    snapshot_time: datetime | None = None
    model_config = ConfigDict(from_attributes=True)

class MatchBase(BaseModel):
    sport_key: str
    home_team: str
    away_team: str
    commence_time: datetime

class MatchCreate(MatchBase):
    api_id: str

class ManualMatchCreate(MatchBase):
    api_id: Optional[str] = None
    sport_key: Optional[str] = "manual_input"

class Match(MatchBase):
    id: int
    api_id: str
    result_home_score: int | None = None
    result_away_score: int | None = None
    odds_snapshots: List[OddsSnapshot] = []
    model_config = ConfigDict(from_attributes=True)

class ScoreUpdate(BaseModel):
    result_home_score: int
    result_away_score: int


class PredictionOutput(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    predicted_outcome: str
    probabilities: dict[str, float]