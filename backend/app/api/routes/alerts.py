"""Alert endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timedelta
from app.db.base import get_db
from app.models.alert import Alert

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/")
async def get_alerts(
    days: int = Query(default=30, ge=1, le=365),
    unread_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    """Get platform alerts."""
    since = date.today() - timedelta(days=days)
    query = select(Alert).where(Alert.date >= since, Alert.is_active == True)
    if unread_only:
        query = query.where(Alert.is_read == False)
    query = query.order_by(Alert.created_at.desc())

    result = await db.execute(query)
    alerts = result.scalars().all()

    return [
        {
            "id": a.id,
            "type": a.alert_type,
            "severity": a.severity,
            "date": a.date,
            "title": a.title,
            "message": a.message,
            "asset_symbol": a.asset_symbol,
            "is_read": a.is_read,
        }
        for a in alerts
    ]
