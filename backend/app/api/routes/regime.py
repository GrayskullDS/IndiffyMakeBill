"""Regime classification API endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timedelta
from typing import Optional
from app.db.base import get_db
from app.models.regime import MacroRegime

router = APIRouter(prefix="/regime", tags=["regime"])


@router.get("/current")
async def get_current_regime(db: AsyncSession = Depends(get_db)):
    """Get the latest macro regime classification with all scores."""
    result = await db.execute(
        select(MacroRegime).order_by(MacroRegime.date.desc()).limit(1)
    )
    regime = result.scalar_one_or_none()
    if not regime:
        raise HTTPException(status_code=404, detail="No regime data available. Run the data pipeline first.")

    return {
        "date": regime.date,
        "regime_type": regime.regime_type,
        "regime_label": regime.regime_label,
        "regime_confidence": regime.regime_confidence,
        "regime_duration_days": regime.regime_duration_days,
        "scores": {
            "growth": regime.growth_score,
            "inflation": regime.inflation_score,
            "labor": regime.labor_score,
            "monetary": regime.monetary_score,
            "risk": regime.risk_score,
            "liquidity": regime.liquidity_score,
        },
        "phases": {
            "growth": regime.growth_phase,
            "inflation": regime.inflation_phase,
        },
        "macro_composite_score": regime.macro_composite_score,
        "recession_probability": regime.recession_probability,
        "favorable_assets": regime.favorable_assets,
        "unfavorable_assets": regime.unfavorable_assets,
        "regime_summary": regime.regime_summary,
        "key_drivers": regime.key_drivers,
        "is_regime_change": regime.is_regime_change,
        "previous_regime": regime.previous_regime,
    }


@router.get("/history")
async def get_regime_history(
    days: int = Query(default=365, ge=30, le=1825),
    db: AsyncSession = Depends(get_db),
):
    """Get regime history for the last N days."""
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(MacroRegime)
        .where(MacroRegime.date >= since)
        .order_by(MacroRegime.date.asc())
    )
    regimes = result.scalars().all()

    return [
        {
            "date": r.date,
            "regime_type": r.regime_type,
            "regime_label": r.regime_label,
            "regime_confidence": r.regime_confidence,
            "macro_composite_score": r.macro_composite_score,
            "recession_probability": r.recession_probability,
            "scores": {
                "growth": r.growth_score,
                "inflation": r.inflation_score,
                "risk": r.risk_score,
                "monetary": r.monetary_score,
            },
        }
        for r in regimes
    ]


@router.get("/scores/heatmap")
async def get_scores_heatmap(
    days: int = Query(default=180, ge=30, le=730),
    db: AsyncSession = Depends(get_db),
):
    """Get score heatmap data for all regime dimensions over time."""
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(MacroRegime)
        .where(MacroRegime.date >= since)
        .order_by(MacroRegime.date.asc())
    )
    regimes = result.scalars().all()

    return {
        "dates": [r.date for r in regimes],
        "growth": [r.growth_score for r in regimes],
        "inflation": [r.inflation_score for r in regimes],
        "labor": [r.labor_score for r in regimes],
        "monetary": [r.monetary_score for r in regimes],
        "risk": [r.risk_score for r in regimes],
        "liquidity": [r.liquidity_score for r in regimes],
        "composite": [r.macro_composite_score for r in regimes],
    }
