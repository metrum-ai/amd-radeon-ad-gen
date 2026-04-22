# Created by Metrum AI for AMD

"""Phase 2 Track 1: Quality gate -- OCR, CLIP, safe zone scoring."""

import logging
import time
import uuid

from app.db.models import Brand, Campaign, GeneratedImage
from app.workers.celery_app import celery
from app.workers.tasks.utils import (
    SyncSession,
    complete_run,
    fail_campaign,
    structured_error,
    track_run,
)
from sqlalchemy import select

log = logging.getLogger(__name__)

MIN_QUALITY_SCORE = 0.6


@celery.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    soft_time_limit=30,
    time_limit=45,
    name="app.workers.tasks.quality_gate.score_images",
    queue="default",
)
def score_images(self, campaign_id: str) -> str:
    """Run OCR, safe-zone, and CLIP quality checks on generated images."""
    from app.services.quality import score_image

    t0 = time.monotonic()
    with SyncSession() as db:
        run = track_run(db, campaign_id, "quality_gate", self.request.id)

        try:
            campaign = db.get(Campaign, uuid.UUID(campaign_id))
            brand = db.get(Brand, campaign.brand_id) if campaign else None

            brand_terms = []
            if brand and brand.name:
                brand_terms = [
                    t.strip()
                    for t in brand.name.replace("-", " ").split()
                    if len(t.strip()) > 1
                ]

            images = (
                db.execute(
                    select(GeneratedImage).where(
                        GeneratedImage.campaign_id == uuid.UUID(campaign_id)
                    )
                )
                .scalars()
                .all()
            )

            for img in images:
                scores = score_image(img.asset_url, brand_terms=brand_terms)
                img.clip_score = scores.get("clip_score")
                img.ocr_pass = scores.get("ocr_pass", True)
                img.ocr_text_found = scores.get("ocr_text_found", "")
                img.safe_zone_pass = scores.get("safe_zone_pass", True)
                img.final_score = scores.get("final_score", 0.0)

            db.commit()

            passing = [
                img
                for img in images
                if (img.final_score or 0) >= MIN_QUALITY_SCORE
            ]

            if not passing:
                log.warning(
                    "No images passed quality gate (min=%.2f) for "
                    "campaign %s -- all %d images will proceed with "
                    "best-effort ranking",
                    MIN_QUALITY_SCORE,
                    campaign_id,
                    len(images),
                )
                passing = images

            sorted_images = sorted(
                passing,
                key=lambda x: x.final_score or 0,
                reverse=True,
            )
            for img in sorted_images[:3]:
                img.is_winner = True

            rejected = len(images) - len(passing)
            if rejected > 0:
                log.info(
                    "Quality gate: %d/%d images passed (min=%.2f)",
                    len(passing),
                    len(images),
                    MIN_QUALITY_SCORE,
                )

            db.commit()

            complete_run(db, run, t0)

        except Exception as exc:
            complete_run(db, run, t0, error=structured_error(exc))
            run.retry_count = self.request.retries
            db.commit()
            if self.request.retries >= self.max_retries:
                fail_campaign(db, campaign_id)
                raise
            raise self.retry(exc=exc)

    return campaign_id
