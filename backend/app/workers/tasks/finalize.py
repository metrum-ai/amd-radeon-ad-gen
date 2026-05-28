# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

"""Finalize campaign after all tracks complete + periodic cleanup."""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from app.db.models import (
    AudioAd,
    Campaign,
    Composition,
    GeneratedImage,
    PipelineRun,
    VideoAd,
)
from app.services.minio_client import download_bytes
from app.workers.celery_app import celery
from app.workers.tasks.utils import (
    SyncSession,
    complete_run,
    fail_campaign,
    track_run,
)
from sqlalchemy import select

log = logging.getLogger(__name__)

STUCK_THRESHOLD_MINUTES = 30


@celery.task(
    bind=True,
    max_retries=1,
    name="app.workers.tasks.finalize.finalize_campaign",
    queue="finalize",
)
def finalize_campaign(self, campaign_id: str) -> str:
    """Called by chord callback after all Phase 2 tracks complete."""
    import time

    t0 = time.monotonic()
    with SyncSession() as db:
        run = track_run(db, campaign_id, "finalize", self.request.id)
        cid = uuid.UUID(campaign_id)
        try:
            campaign = db.get(Campaign, cid)
            if not campaign:
                raise ValueError("Campaign not found")
            tracks = campaign.tracks or {}
            image_enabled = tracks.get("image_text") is True
            audio_enabled = tracks.get("audio_podcast") is True
            video_enabled = tracks.get("video") is True

            if not any([image_enabled, audio_enabled, video_enabled]):
                raise ValueError("Finalize failed: no tracks enabled")

            images = (
                db.execute(
                    select(GeneratedImage).where(
                        GeneratedImage.campaign_id == cid
                    )
                )
                .scalars()
                .all()
            )
            compositions = (
                db.execute(
                    select(Composition).where(Composition.campaign_id == cid)
                )
                .scalars()
                .all()
            )
            audio_ads = (
                db.execute(select(AudioAd).where(AudioAd.campaign_id == cid))
                .scalars()
                .all()
            )
            video_ads = (
                db.execute(select(VideoAd).where(VideoAd.campaign_id == cid))
                .scalars()
                .all()
            )

            # Hard integrity checks only for enabled tracks.
            if image_enabled:
                if not images:
                    raise ValueError("Finalize failed: no generated images")
                if not compositions:
                    raise ValueError("Finalize failed: no composed creatives")
                for img in images:
                    if not img.asset_url:
                        raise ValueError(
                            "Finalize failed: generated image missing asset_url"
                        )
                    download_bytes(img.asset_url)
                for comp in compositions:
                    if not comp.asset_url:
                        raise ValueError(
                            "Finalize failed: composition missing asset_url"
                        )
                    download_bytes(comp.asset_url)

            if audio_enabled:
                generated_audio = [
                    ad for ad in audio_ads if ad.is_generated and ad.asset_url
                ]
                if not generated_audio:
                    raise ValueError("Finalize failed: no generated audio ads")
                for ad in generated_audio:
                    download_bytes(ad.asset_url)

            # Video check is non-fatal: video_gen failures should not
            # block campaign completion when image + audio succeeded.
            if video_enabled:
                generated_videos = [
                    v
                    for v in video_ads
                    if v.is_generated and (v.final_url or v.video_url)
                ]
                if not generated_videos:
                    log.warning(
                        "Campaign %s: video track enabled but no generated "
                        "videos found (non-fatal, continuing finalization)",
                        campaign_id,
                    )
                else:
                    for v in generated_videos:
                        download_bytes(v.final_url or v.video_url)

            campaign.status = "completed"
            campaign.completed_at = datetime.now(timezone.utc)
            complete_run(db, run, t0)
        except Exception as exc:
            fail_campaign(db, campaign_id, str(exc))
            complete_run(db, run, t0, error=str(exc))
            raise

    return campaign_id


@celery.task(
    name="app.workers.tasks.finalize.cleanup_stuck_campaigns",
)
def cleanup_stuck_campaigns() -> dict:
    """Periodic task: find campaigns stuck in *_running for too long and fail them."""
    cutoff = datetime.now(timezone.utc) - timedelta(
        minutes=STUCK_THRESHOLD_MINUTES
    )
    cleaned = 0

    with SyncSession() as db:
        stuck = (
            db.execute(
                select(Campaign).where(
                    Campaign.status.in_(
                        ["strategy_running", "generation_running"]
                    ),
                )
            )
            .scalars()
            .all()
        )

        for campaign in stuck:
            latest_run = (
                db.execute(
                    select(PipelineRun)
                    .where(PipelineRun.campaign_id == campaign.id)
                    .order_by(PipelineRun.started_at.desc())
                )
                .scalars()
                .first()
            )
            last_activity = None
            if latest_run:
                last_activity = (
                    latest_run.completed_at or latest_run.started_at
                )
            if not last_activity:
                last_activity = campaign.created_at
            if not last_activity or last_activity >= cutoff:
                continue
            log.warning(
                "Marking stuck campaign %s as failed (status=%s, last_activity=%s)",
                campaign.id,
                campaign.status,
                last_activity,
            )
            campaign.status = "failed"
            cleaned += 1

        if cleaned:
            db.commit()

    return {"cleaned": cleaned}
