"""
Market regime and trade environment models.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Text,
    Boolean, JSON, Enum as SAEnum
)
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class RegimeType(str, enum.Enum):
    RISK_ON_EXPANSION = "risk_on_expansion"
    RISK_OFF_FEAR = "risk_off_fear"
    INFLATIONARY_BOOM = "inflationary_boom"
    DEFLATIONARY_SLOWDOWN = "deflationary_slowdown"
    POLICY_TIGHTENING = "policy_tightening"
    POLICY_EASING = "policy_easing"
    LIQUIDITY_EXPANSION = "liquidity_expansion"
    LIQUIDITY_CONTRACTION = "liquidity_contraction"
    STAGFLATION = "stagflation"
    RECOVERY = "recovery"


class GrowthPhase(str, enum.Enum):
    EXPANSION = "expansion"
    PEAK = "peak"
    CONTRACTION = "contraction"
    TROUGH = "trough"


class InflationPhase(str, enum.Enum):
    RISING = "rising"
    HIGH_STABLE = "high_stable"
    FALLING = "falling"
    LOW_STABLE = "low_stable"


class MacroRegime(Base):
    """Daily macro regime classification with component scores."""
    __tablename__ = "macro_regimes"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True, index=True)

    # Primary regime
    regime_type = Column(SAEnum(RegimeType), nullable=False)
    regime_label = Column(String(128), nullable=False)   # Human-readable
    regime_confidence = Column(Float, nullable=False)    # 0-1
    regime_duration_days = Column(Integer, default=0)    # Days in current regime

    # Sub-scores (0-10 each)
    growth_score = Column(Float)       # Composite growth momentum
    inflation_score = Column(Float)    # Composite inflation pressure
    labor_score = Column(Float)        # Labor market strength
    monetary_score = Column(Float)     # Policy stance (hawkish=10, dovish=0)
    risk_score = Column(Float)         # Risk appetite (risk-on=10, risk-off=0)
    liquidity_score = Column(Float)    # Liquidity conditions

    # Phase classifications
    growth_phase = Column(SAEnum(GrowthPhase))
    inflation_phase = Column(SAEnum(InflationPhase))

    # Composite scores
    macro_composite_score = Column(Float)  # -10 to +10 (bearish to bullish)
    recession_probability = Column(Float)  # 0-1

    # Narrative
    regime_summary = Column(Text)         # Plain-language summary
    key_drivers = Column(JSON)            # List of key factors
    favorable_assets = Column(JSON)       # Assets that perform well
    unfavorable_assets = Column(JSON)     # Assets that struggle

    # Change detection
    is_regime_change = Column(Boolean, default=False)
    previous_regime = Column(SAEnum(RegimeType))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<MacroRegime {self.date} {self.regime_type}>"


class RegimeHistory(Base):
    """Historical regime periods for backtesting and context."""
    __tablename__ = "regime_history"

    id = Column(Integer, primary_key=True, index=True)
    regime_type = Column(SAEnum(RegimeType), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    duration_days = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
