from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    the_odds_api_id = Column(String, unique=True, index=True)
    league = Column(String, index=True)
    home_team = Column(String, index=True)
    away_team = Column(String, index=True)
    kickoff_time = Column(DateTime)
    
    snapshots = relationship("OddsSnapshot", back_populates="match")

class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    snapshot_time = Column(DateTime)
    interval_marker = Column(Integer)
    odds_home = Column(Float)
    odds_draw = Column(Float)
    odds_away = Column(Float)

    match = relationship("Match", back_populates="snapshots")