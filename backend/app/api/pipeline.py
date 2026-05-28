# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

import uuid

from app.db.models import Campaign
from app.db.session import get_db
from app.workers.tasks.strategy import (
    generate_audio_scripts,
    generate_copy,
    generate_scene_prompts,
    generate_strategy,
)
from celery import chain, chord, group
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/campaigns", tags=["pipeline"])


class PipelineStatus(BaseModel):
    """Response body after triggering a pipeline phase."""

    campaign_id: str
    phase: str
    celery_task_id: str


@router.post("/{campaign_id}/strategize", response_model=PipelineStatus)
async def trigger_phase1(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Enqueue the strategy pipeline (strategy -> copy + scenes -> audio scripts)."""
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    if campaign.status not in ("pending", "strategy_complete", "failed"):
        raise HTTPException(
            409, f"Cannot strategize in status '{campaign.status}'"
        )

    cid = str(campaign_id)
    task = chain(
        generate_strategy.si(cid),
        chord(
            [generate_copy.si(cid), generate_scene_prompts.si(cid)],
            generate_audio_scripts.si(cid),
        ),
    )
    try:
        result = task.apply_async()
    except Exception as exc:
        raise HTTPException(
            503, f"Failed to enqueue strategy pipeline: {exc}"
        ) from exc

    campaign.status = "strategy_running"
    await db.commit()

    return PipelineStatus(
        campaign_id=cid,
        phase="phase1",
        celery_task_id=result.id,
    )


@router.post("/{campaign_id}/generate", response_model=PipelineStatus)
async def trigger_phase2(
    campaign_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    """Enqueue the generation pipeline (images, audio, video -> finalize)."""
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    if campaign.status != "strategy_complete":
        raise HTTPException(
            409,
            f"Cannot generate in status '{campaign.status}'."
            " Must be 'strategy_complete'.",
        )

    cid = str(campaign_id)
    tracks = campaign.tracks or {}

    from app.workers.tasks.audio_gen import generate_audio
    from app.workers.tasks.compositor import compose_creatives
    from app.workers.tasks.finalize import finalize_campaign
    from app.workers.tasks.image_gen import generate_images
    from app.workers.tasks.quality_gate import score_images
    from app.workers.tasks.video_gen import generate_video, mux_video

    track_tasks = []

    if tracks.get("image_text") is True:
        track_tasks.append(
            chain(
                generate_images.si(cid),
                score_images.si(cid),
                compose_creatives.si(cid),
            )
        )

    if tracks.get("audio_podcast") is True:
        track_tasks.append(generate_audio.si(cid))

    if tracks.get("video") is True:
        track_tasks.append(
            chain(
                generate_video.si(cid),
                mux_video.si(cid),
            )
        )

    if not track_tasks:
        raise HTTPException(400, "No tracks enabled")

    task = chord(
        group(track_tasks),
        finalize_campaign.si(cid),
    )
    try:
        result = task.apply_async()
    except Exception as exc:
        raise HTTPException(
            503, f"Failed to enqueue generation pipeline: {exc}"
        ) from exc

    campaign.status = "generation_running"
    await db.commit()

    return PipelineStatus(
        campaign_id=cid,
        phase="phase2",
        celery_task_id=result.id,
    )


@router.get("/{campaign_id}/pipeline-status")
async def get_pipeline_status(
    campaign_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    """Return per-stage pipeline status for a campaign."""
    from app.db.models import PipelineRun
    from sqlalchemy import select

    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.campaign_id == campaign_id)
        .order_by(PipelineRun.started_at)
    )
    runs = result.scalars().all()

    return {
        "campaign_id": str(campaign_id),
        "campaign_status": campaign.status,
        "stages": [
            {
                "stage": r.stage,
                "status": r.status,
                "started_at": (
                    r.started_at.isoformat() if r.started_at else None
                ),
                "completed_at": (
                    r.completed_at.isoformat() if r.completed_at else None
                ),
                "duration_ms": r.duration_ms,
                "error": r.error,
                "retry_count": r.retry_count,
            }
            for r in runs
        ],
    }
