"""Pipeline management endpoints."""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_db
from app.services.pipeline import pipeline

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run")
async def trigger_pipeline(
    background_tasks: BackgroundTasks,
    backfill: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a manual pipeline run."""
    background_tasks.add_task(pipeline.run_full_pipeline, db, backfill)
    return {"status": "Pipeline triggered", "backfill": backfill}


@router.post("/regime/recalculate")
async def recalculate_regime(db: AsyncSession = Depends(get_db)):
    """Recalculate regime classification from existing data."""
    result = await pipeline.compute_and_store_regime(db)
    return {"status": "Regime recalculated", "result": result}


@router.post("/bias/recalculate")
async def recalculate_bias(db: AsyncSession = Depends(get_db)):
    """Recalculate bias signals for all assets."""
    result = await pipeline.compute_and_store_bias(db)
    return {"status": "Bias signals recalculated", "result": result}
