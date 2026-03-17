"""
MacroIntel Platform - FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.routes import regime, trader, macro, alerts, pipeline

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    yield
    logger.info("Shutting down MacroIntel platform")


app = FastAPI(
    title="MacroIntel Platform",
    description=(
        "Professional macroeconomic intelligence platform. "
        "Translates macro data into actionable trading context."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Routers
app.include_router(regime.router, prefix="/api/v1")
app.include_router(trader.router, prefix="/api/v1")
app.include_router(macro.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(pipeline.router, prefix="/api/v1")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/api/v1/assets")
async def list_assets():
    """List all tracked assets (quick reference)."""
    from app.services.data_fetchers.price_fetcher import ASSET_TICKERS
    from app.services.data_fetchers.cot_fetcher import COT_MARKET_MAP

    return {
        "forex": [s for s in ASSET_TICKERS if any(
            c in s for c in ["USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"]
        ) and "=" not in ASSET_TICKERS.get(s, "")],
        "equity_indices": ["SPX", "NDX", "DJI", "DAX", "FTSE", "NIKKEI"],
        "commodities": ["GOLD", "SILVER", "CRUDE_OIL", "BRENT", "NATURAL_GAS", "COPPER"],
        "bonds": ["US2Y", "US10Y", "US30Y"],
        "volatility": ["VIX"],
    }
