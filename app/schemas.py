from pydantic import BaseModel, Field
from datetime import datetime

class PredictionSchema(BaseModel):
    home_win_percentage: float
    draw_percentage: float
    away_win_percentage: float

class MatchSchema(BaseModel):
    id: int
    league: str
    # 'Field(alias=...)' digunakan agar di JSON namanya 'match_time'
    # tapi di kode Python kita tetap bisa pakai 'kickoff_time'
    match_time: datetime = Field(alias="kickoff_time")
    home_team: str
    away_team: str
    prediction: PredictionSchema

    class Config:
        from_attributes = True 
        populate_by_name = True 