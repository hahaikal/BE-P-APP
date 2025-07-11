from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, func

from .database import Base
from sqlalchemy.orm import relationship


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

    odds_snapshots = relationship("OddsSnapshot", back_populates="match")


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    bookmaker = Column(String)
    price_home = Column(Float)
    price_draw = Column(Float)
    price_away = Column(Float)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    match_id = Column(Integer, ForeignKey("matches.id"))
    match = relationship("Match", back_populates="odds_snapshots")