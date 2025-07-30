from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    api_id = Column(String, unique=True, index=True)
    sport_key = Column(String)
    sport_title = Column(String)
    commence_time = Column(DateTime(timezone=True))
    home_team = Column(String)
    away_team = Column(String)
    
    # Kolom untuk hasil pertandingan
    result_home_score = Column(Integer, nullable=True)
    result_away_score = Column(Integer, nullable=True)

    odds_snapshots = relationship("OddsSnapshot", back_populates="match", cascade="all, delete-orphan")

class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    bookmaker = Column(String)
    
    # Odds untuk pasaran 1X2 (H2H)
    price_home = Column(Float)
    price_draw = Column(Float)
    price_away = Column(Float)
    
    # --- [KOLOM BARU UNTUK ASIAN HANDICAP] ---
    # Nilai handicap, contoh: -0.5, 1.25. Dibuat nullable karena tidak semua snapshot memilikinya.
    handicap_line = Column(Float, nullable=True) 
    # Harga untuk tim tuan rumah pada handicap line tersebut.
    handicap_price_home = Column(Float, nullable=True)
    # Harga untuk tim tamu pada handicap line tersebut.
    handicap_price_away = Column(Float, nullable=True)
    # --- [AKHIR KOLOM BARU] ---

    timestamp = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

    match = relationship("Match", back_populates="odds_snapshots")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
