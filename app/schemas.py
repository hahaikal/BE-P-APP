from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class OddsSnapshotBase(BaseModel):
    bookmaker: str
    price_home: float
    price_draw: float
    price_away: float

class OddsSnapshotCreate(OddsSnapshotBase):
    pass

class ManualOddsSnapshotCreate(OddsSnapshotBase):
    snapshot_time: str = Field(
        ..., 
        description="Waktu snapshot dalam format HH:MM, contoh: '19:00'",
        example="19:00"
    )
    snapshot_timezone: str = Field(
        "Asia/Jakarta", 
        description="Timezone dari waktu yang dimasukkan (IANA format)",
        example="Asia/Jakarta"
    )

class OddsSnapshot(OddsSnapshotBase):
    id: int
    match_id: int
    timestamp: datetime

    class Config:
        orm_mode = True

class MatchBase(BaseModel):
    sport_key: str
    home_team: str
    away_team: str
    commence_time: datetime

class ManualMatchCreate(MatchBase):
    api_id: Optional[str] = None

class MatchCreate(MatchBase):
    api_id: str

class ScoreUpdate(BaseModel):
    result_home_score: int
    result_away_score: int

class Match(MatchBase):
    id: int
    api_id: str
    result_home_score: Optional[int] = None
    result_away_score: Optional[int] = None
    odds_snapshots: list[OddsSnapshot] = []

    class Config:
        orm_mode = True

class PredictionOutput(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    predicted_outcome: str
    probabilities: dict[str, float]
