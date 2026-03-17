"""Alert and signal notification models."""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, Boolean, JSON, Enum as SAEnum
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class AlertType(str, enum.Enum):
    REGIME_CHANGE = "regime_change"
    POSITIONING_EXTREME = "positioning_extreme"
    MACRO_DIVERGENCE = "macro_divergence"
    RECESSION_WARNING = "recession_warning"
    VOLATILITY_SPIKE = "volatility_spike"
    BIAS_CHANGE = "bias_change"
    SEASONAL_SETUP = "seasonal_setup"


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert(Base):
    """Platform alerts for regime shifts, extremes, and divergences."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(SAEnum(AlertType), nullable=False)
    severity = Column(SAEnum(AlertSeverity), default=AlertSeverity.INFO)
    date = Column(Date, nullable=False, index=True)
    title = Column(String(256), nullable=False)
    message = Column(Text, nullable=False)
    asset_symbol = Column(String(32))     # Optional: related asset
    extra_data = Column(JSON)              # Additional context data
    is_read = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
