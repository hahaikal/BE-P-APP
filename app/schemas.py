from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

# --- Odds Snapshot Schemas ---

class OddsSnapshotBase(BaseModel):
    bookmaker: str
    price_home: float
    price_draw: float
    price_away: float

    # Skema untuk Asian Handicap
    handicap_line: Optional[float] = None
    handicap_price_home: Optional[float] = None
    handicap_price_away: Optional[float] = None

class OddsSnapshotCreate(OddsSnapshotBase):
    pass

class OddsSnapshot(OddsSnapshotBase):
    id: int
    match_id: int
    timestamp: datetime

    class Config:
        from_attributes = True # Mengganti orm_mode yang usang


# --- Match Schemas ---

class MatchBase(BaseModel):
    api_id: str
    sport_key: str
    # --- PERBAIKAN FINAL DI SINI ---
    # Membuat sport_title menjadi opsional untuk menangani data lama yang bernilai NULL
    sport_title: Optional[str] = None
    commence_time: datetime
    home_team: str
    away_team: str

class MatchCreate(MatchBase):
    pass

class Match(MatchBase):
    id: int
    result_home_score: Optional[int] = None
    result_away_score: Optional[int] = None
    odds_snapshots: List[OddsSnapshot] = []

    class Config:
        from_attributes = True # Mengganti orm_mode yang usang


# --- User & Auth Schemas ---

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None


# --- Schemas for Manual Operations & Predictions ---

class ManualMatchCreate(BaseModel):
    home_team: str
    away_team: str
    commence_time: datetime
    api_id: Optional[str] = None
    sport_key: str = "soccer_epl"
    sport_title: str = "EPL"

class ManualOddsSnapshotCreate(BaseModel):
    bookmaker: str = "manual"
    price_home: float
    price_draw: float
    price_away: float
    snapshot_time: str
    snapshot_timezone: str = "Asia/Jakarta"

class ScoreUpdate(BaseModel):
    result_home_score: int
    result_away_score: int

class PredictionOutput(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    predicted_outcome: str
    probabilities: dict[str, float]

class StatusOverview(BaseModel):
    complete: List[Match]
    incomplete: List[Match]
    empty: List[Match]

    class Config:
        from_attributes = True
