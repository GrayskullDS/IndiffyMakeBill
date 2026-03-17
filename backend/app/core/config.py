from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "MacroIntel"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://macrointel:macrointel@localhost:5432/macrointel"
    DATABASE_SYNC_URL: str = "postgresql://macrointel:macrointel@localhost:5432/macrointel"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "changeme-super-secret-key-32chars-min"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://macrointel.app",
    ]

    # Data API Keys
    FRED_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""
    TRADING_ECONOMICS_API_KEY: str = ""
    TRADING_ECONOMICS_API_SECRET: str = ""

    # Cache TTLs (seconds)
    CACHE_TTL_PRICES: int = 300          # 5 min for price data
    CACHE_TTL_MACRO: int = 3600          # 1 hour for macro indicators
    CACHE_TTL_COT: int = 86400           # 24 hours for COT (weekly)
    CACHE_TTL_REGIME: int = 3600         # 1 hour for regime calculations
    CACHE_TTL_BIAS: int = 1800           # 30 min for bias engine

    # Data Pipeline
    PIPELINE_SCHEDULE_MACRO: str = "0 6 * * *"      # 6am daily
    PIPELINE_SCHEDULE_PRICES: str = "*/15 * * * *"   # Every 15 min
    PIPELINE_SCHEDULE_COT: str = "0 21 * * 5"        # 9pm Friday

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
