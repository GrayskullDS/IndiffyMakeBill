"""
Trader Mode API endpoints.
Core feature: directional bias, trade environment, asset context.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timedelta
from typing import Optional, List
from app.db.base import get_db
from app.models.asset import Asset, BiasSignal, COTReading, SeasonalityData, AssetPrice
from app.models.regime import MacroRegime

router = APIRouter(prefix="/trader", tags=["trader"])


@router.get("/overview")
async def get_trader_overview(db: AsyncSession = Depends(get_db)):
    """
    Full Trader Mode overview:
    - Current macro regime
    - All asset bias signals
    - Trade environment classification
    - Trader summary text
    """
    # Regime
    regime_result = await db.execute(
        select(MacroRegime).order_by(MacroRegime.date.desc()).limit(1)
    )
    regime = regime_result.scalar_one_or_none()

    # All latest bias signals
    bias_result = await db.execute(
        select(BiasSignal, Asset)
        .join(Asset, BiasSignal.asset_id == Asset.id)
        .where(
            BiasSignal.date >= date.today() - timedelta(days=2),
            Asset.is_active == True,
        )
        .order_by(BiasSignal.strength_score.desc())
    )
    bias_rows = bias_result.all()

    bias_signals = []
    for bias, asset in bias_rows:
        bias_signals.append({
            "symbol": asset.symbol,
            "name": asset.name,
            "asset_class": asset.asset_class,
            "direction": bias.direction,
            "strength_score": bias.strength_score,
            "confidence": bias.confidence,
            "timing_label": bias.timing_label,
            "volatility_regime": bias.volatility_regime,
            "is_favorable_environment": bias.is_favorable_environment,
            "summary_text": bias.summary_text,
        })

    # Trade environment classification
    environment = _classify_trade_environment(regime, bias_signals)

    # Trader summary
    summary = _build_trader_summary(regime, bias_signals, environment)

    return {
        "date": date.today(),
        "regime": {
            "type": regime.regime_type if regime else None,
            "label": regime.regime_label if regime else "Unknown",
            "confidence": regime.regime_confidence if regime else None,
            "scores": {
                "growth": regime.growth_score if regime else None,
                "inflation": regime.inflation_score if regime else None,
                "labor": regime.labor_score if regime else None,
                "monetary": regime.monetary_score if regime else None,
                "risk": regime.risk_score if regime else None,
                "liquidity": regime.liquidity_score if regime else None,
            } if regime else {},
            "recession_probability": regime.recession_probability if regime else None,
            "regime_summary": regime.regime_summary if regime else None,
        },
        "trade_environment": environment,
        "bias_signals": bias_signals,
        "trader_summary": summary,
    }


@router.get("/bias")
async def get_all_bias_signals(
    asset_class: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Get current directional bias for all assets (or filter by class)."""
    query = (
        select(BiasSignal, Asset)
        .join(Asset, BiasSignal.asset_id == Asset.id)
        .where(
            BiasSignal.date >= date.today() - timedelta(days=2),
            Asset.is_active == True,
        )
    )
    if asset_class:
        query = query.where(Asset.asset_class == asset_class)

    query = query.order_by(BiasSignal.strength_score.desc())
    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "symbol": asset.symbol,
            "name": asset.name,
            "asset_class": asset.asset_class,
            "direction": bias.direction,
            "strength_score": bias.strength_score,
            "confidence": bias.confidence,
            "components": {
                "macro_alignment": bias.macro_alignment_score,
                "rate_differential": bias.rate_differential_score,
                "growth_inflation": bias.growth_inflation_score,
                "risk_sentiment": bias.risk_sentiment_score,
                "cot_positioning": bias.cot_positioning_score,
                "seasonality": bias.seasonality_score,
                "technical": bias.technical_score,
            },
            "timing_label": bias.timing_label,
            "volatility_regime": bias.volatility_regime,
            "macro_drivers": bias.macro_drivers,
            "summary_text": bias.summary_text,
        }
        for bias, asset in rows
    ]


@router.get("/asset/{symbol}")
async def get_asset_context(symbol: str, db: AsyncSession = Depends(get_db)):
    """
    Full asset context panel:
    - Bias signal with all components
    - COT positioning
    - Seasonality data
    - Recent price performance
    """
    # Get asset
    result = await db.execute(select(Asset).where(Asset.symbol == symbol.upper()))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {symbol} not found")

    # Latest bias
    bias_result = await db.execute(
        select(BiasSignal)
        .where(
            BiasSignal.asset_id == asset.id,
            BiasSignal.date >= date.today() - timedelta(days=3),
        )
        .order_by(BiasSignal.date.desc())
        .limit(1)
    )
    bias = bias_result.scalar_one_or_none()

    # COT data
    cot_result = await db.execute(
        select(COTReading)
        .where(COTReading.asset_id == asset.id)
        .order_by(COTReading.report_date.desc())
        .limit(4)
    )
    cot_readings = cot_result.scalars().all()

    # Seasonality (10-year)
    season_result = await db.execute(
        select(SeasonalityData)
        .where(
            SeasonalityData.asset_id == asset.id,
            SeasonalityData.lookback_years == 10,
        )
        .order_by(SeasonalityData.month.asc())
    )
    seasonality = season_result.scalars().all()

    # Price history (last 90 days)
    price_result = await db.execute(
        select(AssetPrice)
        .where(
            AssetPrice.asset_id == asset.id,
            AssetPrice.date >= date.today() - timedelta(days=90),
        )
        .order_by(AssetPrice.date.asc())
    )
    prices = price_result.scalars().all()

    return {
        "asset": {
            "symbol": asset.symbol,
            "name": asset.name,
            "asset_class": asset.asset_class,
        },
        "bias": {
            "direction": bias.direction if bias else None,
            "strength_score": bias.strength_score if bias else None,
            "confidence": bias.confidence if bias else None,
            "components": {
                "macro_alignment": bias.macro_alignment_score,
                "rate_differential": bias.rate_differential_score,
                "growth_inflation": bias.growth_inflation_score,
                "risk_sentiment": bias.risk_sentiment_score,
                "cot_positioning": bias.cot_positioning_score,
                "seasonality": bias.seasonality_score,
                "technical": bias.technical_score,
            } if bias else {},
            "timing_label": bias.timing_label if bias else None,
            "volatility_regime": bias.volatility_regime if bias else None,
            "macro_drivers": bias.macro_drivers if bias else [],
            "key_risks": bias.key_risks if bias else [],
            "summary_text": bias.summary_text if bias else None,
        },
        "cot_positioning": [
            {
                "report_date": r.report_date,
                "noncommercial_net": r.noncommercial_net,
                "net_position_index": r.net_position_index,
                "percentile_52w": r.percentile_52w,
                "positioning_extreme": r.positioning_extreme,
                "open_interest": r.open_interest,
            }
            for r in cot_readings
        ],
        "seasonality": [
            {
                "month": s.month,
                "avg_return": s.avg_return,
                "win_rate": s.win_rate,
                "std_dev": s.std_dev,
                "sample_size": s.sample_size,
            }
            for s in seasonality
        ],
        "price_history": [
            {
                "date": p.date,
                "close": p.close,
                "sma_20": p.sma_20,
                "sma_50": p.sma_50,
                "sma_200": p.sma_200,
                "rsi_14": p.rsi_14,
            }
            for p in prices
        ],
    }


@router.get("/bias/history/{symbol}")
async def get_bias_history(
    symbol: str,
    days: int = Query(default=90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get bias signal history for an asset."""
    result = await db.execute(select(Asset).where(Asset.symbol == symbol.upper()))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {symbol} not found")

    since = date.today() - timedelta(days=days)
    bias_result = await db.execute(
        select(BiasSignal)
        .where(BiasSignal.asset_id == asset.id, BiasSignal.date >= since)
        .order_by(BiasSignal.date.asc())
    )
    signals = bias_result.scalars().all()

    return [
        {
            "date": s.date,
            "direction": s.direction,
            "strength_score": s.strength_score,
            "confidence": s.confidence,
        }
        for s in signals
    ]


def _classify_trade_environment(regime, bias_signals: list) -> dict:
    """Classify the current trade environment for Trader Mode."""
    if not regime:
        return {"label": "Unknown", "description": "No regime data available.", "type": "unknown"}

    risk = regime.risk_score or 5
    monetary = regime.monetary_score or 5
    growth = regime.growth_score or 5
    vix_regimes = [b.get("volatility_regime") for b in bias_signals if b.get("volatility_regime")]
    vix_mode = max(set(vix_regimes), key=vix_regimes.count) if vix_regimes else "normal"

    environments = []

    if vix_mode in ("high", "extreme"):
        environments.append({
            "label": "High Volatility Regime",
            "type": "high_volatility",
            "description": "Elevated market fear. Reduce position sizing, focus on breakouts with volume confirmation.",
            "trade_style": "Defensive / Selective",
        })
    elif risk >= 7 and growth >= 6:
        environments.append({
            "label": "Trend Following Conditions",
            "type": "trend_following",
            "description": "Risk appetite strong, growth supportive. Favorable for momentum and trend-following strategies.",
            "trade_style": "Trend / Momentum",
        })
    elif risk <= 4:
        environments.append({
            "label": "Risk-Off / Defensive Mode",
            "type": "risk_off",
            "description": "Fear dominant. Focus on safe-havens and hedges. Avoid cyclical longs.",
            "trade_style": "Defensive / Counter-trend",
        })
    elif monetary >= 7:
        environments.append({
            "label": "Policy Tightening Headwinds",
            "type": "tightening",
            "description": "Aggressive rate hikes creating headwinds. Dollar-positive. Risk assets under pressure.",
            "trade_style": "Selective / Short-biased on risk",
        })
    else:
        environments.append({
            "label": "Mixed / Range Environment",
            "type": "mixed",
            "description": "No dominant macro theme. Mean-reversion and range-trading strategies may outperform.",
            "trade_style": "Mean Reversion / Range",
        })

    return environments[0] if environments else {}


def _build_trader_summary(regime, bias_signals: list, environment: dict) -> dict:
    """Build the plain-language Trader Summary panel."""
    if not regime:
        return {"what_is_happening": "No data available."}

    bullish = [b["symbol"] for b in bias_signals if b.get("strength_score", 5) >= 6.5]
    bearish = [b["symbol"] for b in bias_signals if b.get("strength_score", 5) <= 3.5]

    return {
        "what_is_happening": (
            f"The macro environment is currently classified as **{regime.regime_label}** "
            f"with {int((regime.regime_confidence or 0) * 100)}% confidence."
        ),
        "why_it_matters": regime.regime_summary or "See regime analysis for details.",
        "assets_that_benefit": bullish[:5],
        "assets_that_struggle": bearish[:5],
        "trade_environment": environment.get("label", ""),
        "recommended_style": environment.get("trade_style", ""),
        "recession_risk": f"{int((regime.recession_probability or 0) * 100)}%",
        "key_watch": (
            "Monitor: yield curve, VIX, Fed communications, "
            "and DXY for regime shift signals."
        ),
    }
