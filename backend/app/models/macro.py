"""
Macroeconomic indicator models.
Stores time-series data for GDP, CPI, employment, rates, etc.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Text,
    Boolean, ForeignKey, Index, UniqueConstraint, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class IndicatorCategory(str, enum.Enum):
    GROWTH = "growth"
    INFLATION = "inflation"
    LABOR = "labor"
    MONETARY = "monetary"
    SENTIMENT = "sentiment"
    POSITIONING = "positioning"
    PRICE = "price"
    VOLATILITY = "volatility"


class DataFrequency(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class MacroIndicator(Base):
    """Definition of a macroeconomic indicator series."""
    __tablename__ = "macro_indicators"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(256), nullable=False)
    description = Column(Text)
    category = Column(SAEnum(IndicatorCategory), nullable=False)
    frequency = Column(SAEnum(DataFrequency), nullable=False)
    unit = Column(String(64))            # e.g. "percent", "index", "billions USD"
    source = Column(String(64))          # e.g. "FRED", "BLS", "CFTC"
    source_series_id = Column(String(128))  # e.g. "UNRATE", "CPIAUCSL"
    country = Column(String(8), default="US")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    readings = relationship("MacroReading", back_populates="indicator", cascade="all, delete-orphan")
    z_scores = relationship("MacroZScore", back_populates="indicator", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MacroIndicator {self.code}>"


class MacroReading(Base):
    """Individual data point for a macro indicator series."""
    __tablename__ = "macro_readings"

    id = Column(Integer, primary_key=True, index=True)
    indicator_id = Column(Integer, ForeignKey("macro_indicators.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    value = Column(Float, nullable=False)
    prior_value = Column(Float)
    revision_flag = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    indicator = relationship("MacroIndicator", back_populates="readings")

    __table_args__ = (
        UniqueConstraint("indicator_id", "date", name="uq_indicator_date"),
        Index("ix_macro_readings_indicator_date", "indicator_id", "date"),
    )


class MacroZScore(Base):
    """Rolling z-scores for normalized macro comparisons (e.g. 12m, 36m, 60m window)."""
    __tablename__ = "macro_z_scores"

    id = Column(Integer, primary_key=True, index=True)
    indicator_id = Column(Integer, ForeignKey("macro_indicators.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    window_months = Column(Integer, nullable=False)   # 12, 36, 60
    z_score = Column(Float, nullable=False)
    percentile = Column(Float)                        # 0-100
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    indicator = relationship("MacroIndicator", back_populates="z_scores")

    __table_args__ = (
        UniqueConstraint("indicator_id", "date", "window_months", name="uq_zscore_indicator_date_window"),
    )
