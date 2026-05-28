# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

"""Phase 1 Celery tasks: LLM-driven strategy, copy, scene prompts,
and audio script generation. Each task reads from PostgreSQL, calls
the LLM provider, and writes structured output back to PostgreSQL."""

import time
import uuid

from app.db.models import (
    AudioAd,
    Campaign,
    CampaignStrategy,
    CopyVariant,
    ScenePrompt,
)
from app.services.phase1_llm import (
    run_openclaw_then_direct_llm,
    validate_audio_result,
    validate_copy_result,
    validate_scene_result,
    validate_strategy_result,
)
from app.workers.celery_app import celery
from app.workers.tasks.utils import (
    SyncSession,
    complete_run,
    fail_campaign,
    get_or_create_prompt_config,
    store_llm_response,
    structured_error,
    track_run,
)
from celery import Task
from sqlalchemy import select


@celery.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    name="app.workers.tasks.strategy.generate_strategy",
    queue="strategy",
)
def generate_strategy(self: Task, campaign_id: str) -> str:
    """Run the LLM to produce a campaign strategy."""
    from app.services.prompts.strategy import (
        build_strategy_prompt,
        strategy_response_format,
    )

    t0 = time.monotonic()
    with SyncSession() as db:
        run = track_run(db, campaign_id, "strategy", self.request.id)
        try:
            campaign = db.get(Campaign, uuid.UUID(campaign_id))
            pc = get_or_create_prompt_config(db, campaign_id)

            system_prompt, user_prompt = build_strategy_prompt(campaign)
            result = run_openclaw_then_direct_llm(
                system_prompt,
                user_prompt,
                strategy_response_format(),
                validate_strategy_result,
            )

            store_llm_response(db, campaign_id, pc.id, "strategy", result)

            data = result.data
            strategy = CampaignStrategy(
                campaign_id=uuid.UUID(campaign_id),
                prompt_config_id=pc.id,
                campaign_direction=data.get("campaign_direction", ""),
                audience_segments=data.get("audience_segments", []),
                platform_strategy=data.get("platform_strategy", {}),
                track_recommendations=data.get("track_recommendations", {}),
                messaging_angles=data.get("messaging_angles", []),
            )
            db.add(strategy)
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


@celery.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    name="app.workers.tasks.strategy.generate_copy",
    queue="strategy",
)
def generate_copy(self: Task, campaign_id: str) -> str:
    """Run the LLM to produce copy variants for all frameworks."""
    from app.services.prompts.copy import (
        build_copy_prompt,
        copy_response_format,
    )

    t0 = time.monotonic()
    with SyncSession() as db:
        run = track_run(db, campaign_id, "copy_gen", self.request.id)
        try:
            campaign = db.get(Campaign, uuid.UUID(campaign_id))
            pc = get_or_create_prompt_config(db, campaign_id)
            strategy = db.execute(
                select(CampaignStrategy).where(
                    CampaignStrategy.campaign_id == uuid.UUID(campaign_id)
                )
            ).scalar_one()

            system_prompt, user_prompt = build_copy_prompt(
                campaign, strategy
            )
            result = run_openclaw_then_direct_llm(
                system_prompt,
                user_prompt,
                copy_response_format(),
                validate_copy_result,
            )

            store_llm_response(db, campaign_id, pc.id, "copy_gen", result)

            variants = result.data.get("copy_variants", [])
            required_frameworks = {"AIDA", "PAS", "BAB"}
            got = {v.get("framework") for v in variants}
            missing = required_frameworks - got
            if missing:
                raise ValueError(
                    f"LLM returned {len(variants)} copy variant(s), "
                    f"missing frameworks: {missing}"
                )

            for variant in variants:
                db.add(
                    CopyVariant(
                        campaign_id=uuid.UUID(campaign_id),
                        prompt_config_id=pc.id,
                        framework=variant["framework"],
                        headline=variant["headline"],
                        body=variant["body"],
                        cta=variant["cta"],
                        hashtags=variant.get("hashtags", []),
                        platform_versions=variant.get("platform_versions", {}),
                    )
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


@celery.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    name="app.workers.tasks.strategy.generate_scene_prompts",
    queue="strategy",
)
def generate_scene_prompts(self: Task, campaign_id: str) -> str:
    """Run the LLM to produce image and video scene prompts."""
    from app.providers.base import sanitize_video_prompt
    from app.services.prompts.scenes import (
        build_scene_prompt,
        scene_response_format,
    )

    t0 = time.monotonic()
    with SyncSession() as db:
        run = track_run(db, campaign_id, "scene_gen", self.request.id)
        try:
            campaign = db.get(Campaign, uuid.UUID(campaign_id))
            pc = get_or_create_prompt_config(db, campaign_id)
            strategy = db.execute(
                select(CampaignStrategy).where(
                    CampaignStrategy.campaign_id == uuid.UUID(campaign_id)
                )
            ).scalar_one()

            system_prompt, user_prompt = build_scene_prompt(
                campaign, strategy
            )
            result = run_openclaw_then_direct_llm(
                system_prompt,
                user_prompt,
                scene_response_format(),
                validate_scene_result,
            )

            store_llm_response(db, campaign_id, pc.id, "scene_gen", result)

            for scene in result.data.get("scene_prompts", []):
                db.add(
                    ScenePrompt(
                        campaign_id=uuid.UUID(campaign_id),
                        prompt_config_id=pc.id,
                        scene_type=scene["scene_type"],
                        image_prompt=scene["image_prompt"],
                        video_script=(
                            sanitize_video_prompt(scene.get("video_script"))
                            if scene.get("video_script")
                            else None
                        ),
                    )
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


@celery.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    name="app.workers.tasks.strategy.generate_audio_scripts",
    queue="strategy",
)
def generate_audio_scripts(self: Task, campaign_id: str) -> str:
    """Run the LLM to produce TTS audio scripts."""
    from app.services.prompts.scenes import (
        audio_script_response_format,
        build_audio_script_prompt,
    )

    t0 = time.monotonic()
    with SyncSession() as db:
        run = track_run(db, campaign_id, "audio_script_gen", self.request.id)
        try:
            campaign = db.get(Campaign, uuid.UUID(campaign_id))
            pc = get_or_create_prompt_config(db, campaign_id)
            strategy = db.execute(
                select(CampaignStrategy).where(
                    CampaignStrategy.campaign_id == uuid.UUID(campaign_id)
                )
            ).scalar_one()
            copy_variants = (
                db.execute(
                    select(CopyVariant).where(
                        CopyVariant.campaign_id == uuid.UUID(campaign_id)
                    )
                )
                .scalars()
                .all()
            )

            system_prompt, user_prompt = build_audio_script_prompt(
                campaign, strategy, copy_variants
            )
            result = run_openclaw_then_direct_llm(
                system_prompt,
                user_prompt,
                audio_script_response_format(),
                validate_audio_result,
            )

            store_llm_response(
                db, campaign_id, pc.id, "audio_script_gen", result
            )

            for script in result.data.get("audio_scripts", []):
                db.add(
                    AudioAd(
                        campaign_id=uuid.UUID(campaign_id),
                        prompt_config_id=pc.id,
                        tone=script["tone"],
                        script=script["script"],
                        voice=script.get("voice", "af_heart"),
                        speed=script.get("speed", 1.0),
                    )
                )
            db.commit()

            campaign.status = "strategy_complete"
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
