# Created by Metrum AI for AMD

"""Phase 2 Track 1: Compositor -- overlay copy + brand kit on images."""

import time
import uuid

from app.db.models import (
    Brand,
    Campaign,
    Composition,
    CopyVariant,
    GeneratedImage,
)
from app.services.minio_client import download_bytes, upload_bytes
from app.workers.celery_app import celery
from app.workers.tasks.utils import (
    SyncSession,
    complete_run,
    complete_run_retrying,
    fail_campaign,
    structured_error,
    track_run,
)
from sqlalchemy import delete, select


@celery.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    name="app.workers.tasks.compositor.compose_creatives",
    queue="compositor",
)
def compose_creatives(self, campaign_id: str) -> str:
    """Composite copy onto winner images for all ad sizes."""
    from app.services.compositor import compose_ad

    t0 = time.monotonic()
    with SyncSession() as db:
        run = track_run(db, campaign_id, "composition", self.request.id)

        try:
            campaign = db.get(Campaign, uuid.UUID(campaign_id))
            brand = db.get(Brand, campaign.brand_id)

            images = (
                db.execute(
                    select(GeneratedImage).where(
                        GeneratedImage.campaign_id == uuid.UUID(campaign_id)
                    )
                )
                .scalars()
                .all()
            )

            copy_variants = (
                db.execute(
                    select(CopyVariant).where(
                        CopyVariant.campaign_id == uuid.UUID(campaign_id)
                    )
                )
                .scalars()
                .all()
            )

            # Replace old compositions on re-run so stale creatives
            # (e.g. prior CTA styling) do not remain in previews.
            db.execute(
                delete(Composition).where(
                    Composition.campaign_id == uuid.UUID(campaign_id)
                )
            )
            db.flush()

            for img in images:
                img_bytes = download_bytes(img.asset_url)

                for cv in copy_variants:
                    composed = compose_ad(
                        img_bytes,
                        headline=cv.headline,
                        body=cv.body,
                        cta=cv.cta,
                        brand_colors=brand.colors,
                        brand_fonts=brand.fonts,
                        logo_url=brand.logo_url,
                    )

                    asset_url = upload_bytes(
                        composed,
                        campaign_id,
                        "compositions",
                        "png",
                    )

                    db.add(
                        Composition(
                            campaign_id=uuid.UUID(campaign_id),
                            image_id=img.id,
                            copy_variant_id=cv.id,
                            asset_url=asset_url,
                            ad_size="1080x1350",
                        )
                    )

            db.commit()

            complete_run(db, run, t0)

        except Exception as exc:
            err = structured_error(exc)
            if self.request.retries >= self.max_retries:
                complete_run(db, run, t0, error=err)
                fail_campaign(db, campaign_id)
                raise
            complete_run_retrying(db, run, t0, err, self.request.retries)
            raise self.retry(exc=exc)

    return campaign_id
