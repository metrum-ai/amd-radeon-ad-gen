# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

"""Phase 2 Track 1: Image generation via FLUX.1-Dev provider.

When two FLUX servers are available (4-GPU setup), individual scene
images are dispatched as separate Celery tasks so two GPU workers can
process them in parallel.  The fan-out coordinator
(``generate_images``) creates a ``group`` of ``_generate_single_image``
tasks and waits for all of them to finish before returning.
"""

import logging
import random  # nosec B311
import time
import uuid

from app.db.models import Brand, Campaign, GeneratedImage, ScenePrompt
from app.services.minio_client import upload_bytes
from app.workers.celery_app import celery
from app.workers.tasks.utils import (
    SyncSession,
    complete_run,
    complete_run_retrying,
    fail_campaign,
    run_async,
    structured_error,
    track_run,
)
from sqlalchemy import select

logger = logging.getLogger(__name__)


@celery.task(
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    retry_backoff=True,
    name="app.workers.tasks.image_gen._generate_single_image",
    queue="image_gen",
)
def _generate_single_image(self, campaign_id: str, scene_id: str) -> str:
    """Generate one image for a single scene prompt.

    Designed to be dispatched in a Celery group so multiple GPU workers
    can process different scenes concurrently across FLUX server replicas.
    """
    from app.providers.base import ImageGenParams, sanitize_image_prompt
    from app.providers.factory import get_image_provider

    with SyncSession() as db:
        try:
            scene = db.get(ScenePrompt, uuid.UUID(scene_id))
            if not scene:
                logger.warning("Scene %s not found, skipping", scene_id)
                return campaign_id

            already = db.execute(
                select(GeneratedImage).where(
                    GeneratedImage.scene_prompt_id == scene.id
                )
            ).scalar_one_or_none()
            if already:
                return campaign_id

            campaign = db.get(Campaign, uuid.UUID(campaign_id))
            brand = db.get(Brand, campaign.brand_id) if campaign else None
            category_source = " ".join(
                p
                for p in [
                    campaign.product_category if campaign else "",
                    campaign.product_description if campaign else "",
                ]
                if p
            ).strip()

            provider = get_image_provider()
            params = ImageGenParams(
                seed=random.randint(1, 2**31),  # nosec B311
            )
            prompt = sanitize_image_prompt(
                scene.image_prompt,
                product_description=category_source,
                brand_colors=brand.colors if brand else None,
                scene_type=scene.scene_type,
            )

            t_gen = time.monotonic()
            image_bytes = run_async(provider.generate_image(prompt, params))
            gen_ms = int((time.monotonic() - t_gen) * 1000)

            asset_url = upload_bytes(
                image_bytes,
                campaign_id,
                "images",
                "png",
            )
            db.add(
                GeneratedImage(
                    campaign_id=uuid.UUID(campaign_id),
                    scene_prompt_id=scene.id,
                    asset_url=asset_url,
                    seed=params.seed,
                    width=params.width,
                    height=params.height,
                    inference_steps=params.num_inference_steps,
                    guidance_scale=params.guidance_scale,
                    generation_time_ms=gen_ms,
                )
            )
            db.commit()
            logger.info(
                "image_gen: scene %s (%s) done in %dms",
                scene.scene_type,
                scene_id[:8],
                gen_ms,
            )

        except Exception as exc:
            logger.error(
                "image_gen: scene %s failed: %s",
                scene_id[:8],
                exc,
            )
            raise self.retry(exc=exc)

    return campaign_id


@celery.task(
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    retry_backoff=True,
    name="app.workers.tasks.image_gen.generate_images",
    queue="default",
)
def generate_images(self, campaign_id: str) -> str:
    """Fan out per-scene image generation across available GPU workers.

    Each scene is dispatched as a separate ``_generate_single_image``
    task on the ``image_gen`` queue.  When two GPU workers consume that
    queue (each talking to its own FLUX server), two scenes are
    generated in parallel.
    """
    from celery import group as celery_group

    t0 = time.monotonic()
    with SyncSession() as db:
        run = track_run(db, campaign_id, "image_gen", self.request.id)

        try:
            scenes = (
                db.execute(
                    select(ScenePrompt).where(
                        ScenePrompt.campaign_id == uuid.UUID(campaign_id)
                    )
                )
                .scalars()
                .all()
            )

            pending_scene_ids = []
            for scene in scenes:
                already = db.execute(
                    select(GeneratedImage).where(
                        GeneratedImage.scene_prompt_id == scene.id
                    )
                ).scalar_one_or_none()
                if not already:
                    pending_scene_ids.append(str(scene.id))

            if not pending_scene_ids:
                logger.info("image_gen: all scenes already generated")
                complete_run(db, run, t0)
                return campaign_id

            logger.info(
                "image_gen: dispatching %d scene(s) in parallel",
                len(pending_scene_ids),
            )

        except Exception as exc:
            err = structured_error(exc)
            if self.request.retries >= self.max_retries:
                complete_run(db, run, t0, error=err)
                fail_campaign(db, campaign_id)
                raise
            complete_run_retrying(db, run, t0, err, self.request.retries)
            raise self.retry(exc=exc)

    job = celery_group(
        _generate_single_image.si(campaign_id, sid)
        for sid in pending_scene_ids
    )
    result = job.apply_async()
    result.get(timeout=600, disable_sync_subtasks=False)

    with SyncSession() as db:
        run = track_run(db, campaign_id, "image_gen", self.request.id)
        complete_run(db, run, t0)

    return campaign_id
