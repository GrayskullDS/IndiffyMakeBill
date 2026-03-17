"""Macro indicator data endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timedelta
from app.db.base import get_db
from app.models.macro import MacroIndicator, MacroReading, IndicatorCategory

router = APIRouter(prefix="/macro", tags=["macro"])


@router.get("/indicators")
async def list_indicators(
    category: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """List all tracked macro indicators."""
    query = select(MacroIndicator).where(MacroIndicator.is_active == True)
    if category:
        query = query.where(MacroIndicator.category == category)
    result = await db.execute(query.order_by(MacroIndicator.category, MacroIndicator.name))
    indicators = result.scalars().all()

    return [
        {
            "id": i.id,
            "code": i.code,
            "name": i.name,
            "category": i.category,
            "frequency": i.frequency,
            "unit": i.unit,
            "source": i.source,
        }
        for i in indicators
    ]


@router.get("/indicators/{code}/series")
async def get_indicator_series(
    code: str,
    days: int = Query(default=365, ge=30, le=3650),
    db: AsyncSession = Depends(get_db),
):
    """Get time-series data for a macro indicator."""
    result = await db.execute(
        select(MacroIndicator).where(MacroIndicator.code == code.upper())
    )
    indicator = result.scalar_one_or_none()
    if not indicator:
        raise HTTPException(status_code=404, detail=f"Indicator {code} not found")

    since = date.today() - timedelta(days=days)
    readings_result = await db.execute(
        select(MacroReading)
        .where(MacroReading.indicator_id == indicator.id, MacroReading.date >= since)
        .order_by(MacroReading.date.asc())
    )
    readings = readings_result.scalars().all()

    return {
        "indicator": {
            "code": indicator.code,
            "name": indicator.name,
            "category": indicator.category,
            "unit": indicator.unit,
            "frequency": indicator.frequency,
        },
        "data": [
            {"date": r.date, "value": r.value}
            for r in readings
        ],
    }


@router.get("/dashboard")
async def get_macro_dashboard(db: AsyncSession = Depends(get_db)):
    """
    Macro dashboard snapshot:
    Latest value for each key indicator, organized by category.
    """
    from sqlalchemy import text

    query = text("""
        SELECT i.code, i.name, i.category, i.unit, r.value, r.date, r.prior_value
        FROM macro_indicators i
        INNER JOIN LATERAL (
            SELECT value, date, prior_value FROM macro_readings
            WHERE indicator_id = i.id
            ORDER BY date DESC
            LIMIT 1
        ) r ON true
        WHERE i.is_active = true
        ORDER BY i.category, i.name
    """)
    result = await db.execute(query)
    rows = result.fetchall()

    # Organize by category
    dashboard = {}
    for row in rows:
        cat = row.category
        if cat not in dashboard:
            dashboard[cat] = []
        dashboard[cat].append({
            "code": row.code,
            "name": row.name,
            "value": row.value,
            "date": row.date,
            "unit": row.unit,
            "prior_value": row.prior_value,
            "change": round(row.value - row.prior_value, 4) if row.prior_value else None,
        })

    return dashboard
