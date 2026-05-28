# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

import uuid
from datetime import datetime, timedelta, timezone

from app.db.models import GpuMetric
from app.db.session import get_db
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

_GPU_HISTORY_COLS = [
    GpuMetric.id,
    GpuMetric.recorded_at,
    GpuMetric.gpu_index,
    GpuMetric.vram_used_mb,
    GpuMetric.vram_total_mb,
    GpuMetric.gpu_util_pct,
    GpuMetric.power_watts,
    GpuMetric.temp_celsius,
    GpuMetric.inference_rps,
    GpuMetric.ttft_ms,
]


@router.get("/gpu")
async def get_latest_gpu_metrics(
    db: AsyncSession = Depends(get_db),
):
    """Return the latest GPU metric snapshot per GPU index."""
    latest = (
        select(
            GpuMetric.gpu_index,
            func.max(GpuMetric.recorded_at).label("max_ts"),
        )
        .group_by(GpuMetric.gpu_index)
        .subquery()
    )
    stmt = (
        select(*_GPU_HISTORY_COLS)
        .join(
            latest,
            (GpuMetric.gpu_index == latest.c.gpu_index)
            & (GpuMetric.recorded_at == latest.c.max_ts),
        )
        .order_by(GpuMetric.gpu_index)
    )
    result = await db.execute(stmt)
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.get("/gpu/history")
async def get_gpu_history(
    minutes: int = 60,
    gpu_index: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Return GPU metrics for the last N minutes."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    stmt = select(*_GPU_HISTORY_COLS).where(GpuMetric.recorded_at > cutoff)
    if gpu_index is not None:
        stmt = stmt.where(GpuMetric.gpu_index == gpu_index)
    stmt = stmt.order_by(GpuMetric.recorded_at.desc()).limit(1000)

    result = await db.execute(stmt)
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.get("/pipeline/{campaign_id}")
async def get_pipeline_metrics(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return per-stage timing for a campaign pipeline run."""
    from app.db.models import PipelineRun

    result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.campaign_id == campaign_id)
        .order_by(PipelineRun.started_at)
    )
    runs = result.scalars().all()
    return [
        {
            "stage": r.stage,
            "status": r.status,
            "duration_ms": r.duration_ms,
            "retry_count": r.retry_count,
        }
        for r in runs
    ]
