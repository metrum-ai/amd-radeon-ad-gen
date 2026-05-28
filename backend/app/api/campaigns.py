# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

import uuid
from datetime import datetime, timezone
from typing import Literal

from app.config import settings
from app.db.models import Campaign
from app.db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    """Request body for creating a new campaign."""

    user_id: uuid.UUID
    brand_id: uuid.UUID
    name: str
    objective: str | None = None
    style: str | None = None
    tone: str | None = None
    product_description: str | None = None
    product_category: str | None = None
    target_audience: str | None = None
    reference_image_url: str | None = None
    tracks: dict = {
        "image_text": True,
        "audio_podcast": True,
        "video": False,
    }


class CampaignOut(BaseModel):
    """Serialised campaign returned by list/create endpoints."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    brand_id: uuid.UUID
    name: str
    objective: str | None
    style: str | None
    tone: str | None
    product_description: str | None
    product_category: str | None
    target_audience: str | None
    reference_image_url: str | None
    tracks: dict
    status: str
    created_at: datetime
    completed_at: datetime | None


class CampaignDetail(CampaignOut):
    """Extended campaign view with all related assets and metrics."""

    strategy: list[dict] = []
    copy_variants: list[dict] = []
    scene_prompts: list[dict] = []
    generated_images: list[dict] = []
    compositions: list[dict] = []
    audio_ads: list[dict] = []
    video_ads: list[dict] = []
    pipeline_runs: list[dict] = []
    metrics: dict | None = None


CampaignStatus = Literal[
    "pending",
    "strategy_running",
    "strategy_complete",
    "generation_running",
    "completed",
    "failed",
]


class CampaignUpdate(BaseModel):
    """Request body for partial campaign updates."""

    status: CampaignStatus | None = None
    tracks: dict | None = None


@router.post("", response_model=CampaignOut, status_code=201)
async def create_campaign(
    body: CampaignCreate, db: AsyncSession = Depends(get_db)
):
    """Persist a new campaign and return it."""
    campaign = Campaign(**body.model_dump())
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(
    user_id: uuid.UUID | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Return campaigns with optional user/status filters."""
    stmt = select(Campaign).order_by(Campaign.created_at.desc())
    if user_id:
        stmt = stmt.where(Campaign.user_id == user_id)
    if status:
        stmt = stmt.where(Campaign.status == status)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(
    campaign_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    """Return a single campaign with all assets, metrics, and pipeline runs."""
    stmt = (
        select(Campaign)
        .where(Campaign.id == campaign_id)
        .options(
            selectinload(Campaign.strategy),
            selectinload(Campaign.copy_variants),
            selectinload(Campaign.scene_prompts),
            selectinload(Campaign.generated_images),
            selectinload(Campaign.compositions),
            selectinload(Campaign.audio_ads),
            selectinload(Campaign.video_ads),
            selectinload(Campaign.pipeline_runs),
            selectinload(Campaign.llm_responses),
        )
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    def _serialize(items):
        out = []
        for item in items:
            d = {
                k: v for k, v in item.__dict__.items() if not k.startswith("_")
            }
            for k, v in d.items():
                if isinstance(v, (uuid.UUID,)):
                    d[k] = str(v)
                elif isinstance(v, datetime):
                    d[k] = v.isoformat()
            out.append(d)
        return out

    scene_prompts = _serialize(campaign.scene_prompts)
    copy_variants = _serialize(campaign.copy_variants)

    scene_map = {sp["id"]: sp for sp in scene_prompts}
    copy_map = {cv["id"]: cv for cv in copy_variants}

    generated_images = _serialize(campaign.generated_images)
    for img in generated_images:
        sp = scene_map.get(img.get("scene_prompt_id"))
        if sp:
            img["scene_type"] = sp.get("scene_type", "")
            img["image_prompt"] = sp.get("image_prompt", "")

    image_map = {img["id"]: img for img in generated_images}

    compositions = _serialize(campaign.compositions)
    for comp in compositions:
        cv = copy_map.get(comp.get("copy_variant_id"))
        if cv:
            comp["headline"] = cv.get("headline", "")
            comp["cta"] = cv.get("cta", "")
            comp["framework"] = cv.get("framework", "")
            comp["body"] = cv.get("body", "")
        img = image_map.get(comp.get("image_id"))
        if img:
            comp["scene_type"] = img.get("scene_type", "")

    video_ads = _serialize(campaign.video_ads)
    for v in video_ads:
        if v.get("voiceover_url"):
            v["thumbnail_url"] = v.get("voiceover_url")

    # Compute performance metrics from stored data
    metrics = {}

    llm_rows = campaign.llm_responses or []
    if llm_rows:
        total_tokens = sum(r.tokens_used or 0 for r in llm_rows)
        total_latency = sum(r.latency_ms or 0 for r in llm_rows)
        tokens_per_sec = (
            round(total_tokens / (total_latency / 1000), 1)
            if total_latency > 0
            else None
        )
        metrics["llm"] = {
            "total_tokens": total_tokens,
            "total_latency_ms": total_latency,
            "tokens_per_sec": tokens_per_sec,
            "calls": len(llm_rows),
            "model": llm_rows[-1].model if llm_rows else None,
        }

    img_rows = campaign.generated_images or []
    imgs_with_time = [i for i in img_rows if i.generation_time_ms is not None]
    if imgs_with_time:
        total_gen_ms = sum(i.generation_time_ms for i in imgs_with_time)
        images_per_min = (
            round(len(imgs_with_time) / (total_gen_ms / 60000), 2)
            if total_gen_ms > 0
            else None
        )
        metrics["image_gen"] = {
            "total_images": len(imgs_with_time),
            "total_generation_ms": total_gen_ms,
            "avg_generation_ms": round(total_gen_ms / len(imgs_with_time)),
            "images_per_min": images_per_min,
            "model": settings.image_model_name,
        }

    vid_rows = campaign.video_ads or []
    vids_with_time = [v for v in vid_rows if v.generation_time_ms is not None]
    if vids_with_time:
        total_vid_ms = sum(v.generation_time_ms for v in vids_with_time)
        vids_per_min = (
            round(len(vids_with_time) / (total_vid_ms / 60000), 2)
            if total_vid_ms > 0
            else None
        )
        avg_dur = round(
            sum(v.duration_sec or 0 for v in vids_with_time)
            / len(vids_with_time),
            1,
        )
        resolution = None
        sample = next((v for v in vids_with_time if v.width), None)
        if sample:
            resolution = f"{sample.width}x{sample.height}"
        metrics["video_gen"] = {
            "total_clips": len(vids_with_time),
            "total_generation_ms": total_vid_ms,
            "avg_generation_ms": round(total_vid_ms / len(vids_with_time)),
            "clips_per_min": vids_per_min,
            "avg_duration_sec": avg_dur,
            "resolution": resolution,
            "model": vids_with_time[-1].model_used if vids_with_time else None,
        }

    strategy_rows = _serialize(campaign.strategy)
    strategy_rows.sort(
        key=lambda x: (x.get("created_at") or ""),
        reverse=True,
    )

    return CampaignDetail(
        **{
            k: v
            for k, v in campaign.__dict__.items()
            if not k.startswith("_")
            and k
            not in (
                "strategy",
                "copy_variants",
                "scene_prompts",
                "generated_images",
                "compositions",
                "audio_ads",
                "video_ads",
                "pipeline_runs",
                "llm_responses",
            )
        },
        strategy=strategy_rows,
        copy_variants=copy_variants,
        scene_prompts=scene_prompts,
        generated_images=generated_images,
        compositions=compositions,
        audio_ads=_serialize(campaign.audio_ads),
        video_ads=video_ads,
        pipeline_runs=_serialize(campaign.pipeline_runs),
        metrics=metrics or None,
    )


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    campaign_id: uuid.UUID,
    body: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Patch campaign status or track configuration."""
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    if body.status is None and body.tracks is None:
        raise HTTPException(400, "At least one field must be provided")
    if body.status is not None:
        campaign.status = body.status
        if body.status == "completed":
            campaign.completed_at = datetime.now(timezone.utc)
    if body.tracks is not None:
        campaign.tracks = body.tracks
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    """Delete a campaign and cascade to related records."""
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    await db.delete(campaign)
    await db.commit()
