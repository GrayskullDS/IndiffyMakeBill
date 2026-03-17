"""
Asset, bias signal, and positioning models.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Text,
    Boolean, JSON, ForeignKey, UniqueConstraint, Index, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class AssetClass(str, enum.Enum):
    FOREX = "forex"
    EQUITY_INDEX = "equity_index"
    COMMODITY = "commodity"
    BOND = "bond"
    CRYPTO = "crypto"


class BiasDirection(str, enum.Enum):
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL_BULLISH = "neutral_bullish"
    NEUTRAL = "neutral"
    NEUTRAL_BEARISH = "neutral_bearish"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"


class Asset(Base):
    """Tradeable asset definition."""
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(32), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    asset_class = Column(SAEnum(AssetClass), nullable=False)
    yfinance_ticker = Column(String(32))       # e.g. "EURUSD=X", "^GSPC", "GC=F"
    base_currency = Column(String(8))          # For forex pairs
    quote_currency = Column(String(8))         # For forex pairs
    country = Column(String(8))                # For equity indices
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    price_readings = relationship("AssetPrice", back_populates="asset", cascade="all, delete-orphan")
    bias_signals = relationship("BiasSignal", back_populates="asset", cascade="all, delete-orphan")
    cot_readings = relationship("COTReading", back_populates="asset", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Asset {self.symbol}>"


class AssetPrice(Base):
    """Daily OHLCV price data for assets."""
    __tablename__ = "asset_prices"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float, nullable=False)
    volume = Column(Float)
    adj_close = Column(Float)

    # Technical indicators
    sma_20 = Column(Float)
    sma_50 = Column(Float)
    sma_200 = Column(Float)
    ema_20 = Column(Float)
    rsi_14 = Column(Float)
    atr_14 = Column(Float)

    asset = relationship("Asset", back_populates="price_readings")

    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_asset_price_date"),
        Index("ix_asset_prices_asset_date", "asset_id", "date"),
    )


class BiasSignal(Base):
    """
    Directional bias signal for an asset on a given date.
    Core output of the Directional Bias Engine.
    """
    __tablename__ = "bias_signals"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)

    # Core bias output
    direction = Column(SAEnum(BiasDirection), nullable=False)
    strength_score = Column(Float, nullable=False)      # 1-10
    confidence = Column(Float, nullable=False)          # 0-1

    # Component sub-scores (each 0-10)
    macro_alignment_score = Column(Float)
    rate_differential_score = Column(Float)             # Forex primarily
    growth_inflation_score = Column(Float)
    risk_sentiment_score = Column(Float)
    cot_positioning_score = Column(Float)
    seasonality_score = Column(Float)
    technical_score = Column(Float)
    relative_strength_score = Column(Float)

    # Trade timing
    timing_label = Column(String(64))   # "trend_following", "mean_reversion", etc.
    volatility_regime = Column(String(32))  # "low", "normal", "high", "extreme"
    is_favorable_environment = Column(Boolean, default=True)

    # Context
    macro_drivers = Column(JSON)         # List of top macro drivers
    key_risks = Column(JSON)             # Risk factors
    summary_text = Column(Text)          # Plain language summary

    asset = relationship("Asset", back_populates="bias_signals")

    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_bias_asset_date"),
        Index("ix_bias_signals_asset_date", "asset_id", "date"),
    )


class COTReading(Base):
    """CFTC Commitment of Traders weekly data."""
    __tablename__ = "cot_readings"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    report_date = Column(Date, nullable=False, index=True)    # Tuesday snapshot date
    release_date = Column(Date)                               # Friday release

    # Commercial traders (hedgers)
    commercial_long = Column(Float)
    commercial_short = Column(Float)
    commercial_net = Column(Float)

    # Non-commercial traders (large speculators)
    noncommercial_long = Column(Float)
    noncommercial_short = Column(Float)
    noncommercial_net = Column(Float)

    # Non-reportable (small speculators)
    nonreportable_long = Column(Float)
    nonreportable_short = Column(Float)
    nonreportable_net = Column(Float)

    # Open interest
    open_interest = Column(Float)

    # Derived metrics (calculated)
    net_position_index = Column(Float)      # Normalized -100 to +100
    positioning_extreme = Column(Boolean, default=False)  # > 90th or < 10th percentile
    percentile_52w = Column(Float)          # Where current net is vs 52w range

    asset = relationship("Asset", back_populates="cot_readings")

    __table_args__ = (
        UniqueConstraint("asset_id", "report_date", name="uq_cot_asset_date"),
    )


class SeasonalityData(Base):
    """Historical monthly seasonality statistics per asset."""
    __tablename__ = "seasonality_data"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    month = Column(Integer, nullable=False)          # 1-12
    lookback_years = Column(Integer, nullable=False) # 5, 10, 20
    avg_return = Column(Float)                       # Average monthly return
    win_rate = Column(Float)                         # % positive months
    median_return = Column(Float)
    std_dev = Column(Float)
    best_return = Column(Float)
    worst_return = Column(Float)
    sample_size = Column(Integer)

    __table_args__ = (
        UniqueConstraint("asset_id", "month", "lookback_years", name="uq_seasonality"),
    )
