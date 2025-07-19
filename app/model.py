from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    api_id = Column(String, unique=True, index=True)
    sport_key = Column(String)
    home_team = Column(String)
    away_team = Column(String)
    commence_time = Column(DateTime(timezone=True))
    
    result_home_score = Column(Integer, nullable=True)
    result_away_score = Column(Integer, nullable=True)

    odds_snapshots = relationship("OddsSnapshot", back_populates="match", cascade="all, delete-orphan")

class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    bookmaker = Column(String)
    price_home = Column(Float)
    price_draw = Column(Float)
    price_away = Column(Float)
    timestamp = Column(DateTime(timezone=True))

    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    
    match = relationship("Match", back_populates="odds_snapshots")