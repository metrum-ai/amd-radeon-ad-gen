# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

"""Shared utilities for Celery task files.

Provides common database session setup, async execution helpers,
pipeline run tracking, and campaign error handling.
"""

import asyncio
import logging
import threading
import time
import uuid
from datetime import datetime, timezone

log = logging.getLogger(__name__)

from app.config import settings
from app.db.models import Campaign, LLMResponse, PipelineRun, PromptConfig
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

sync_engine = create_engine(
    settings.database_url.replace("+asyncpg", "+psycopg")
)
SyncSession = sessionmaker(sync_engine)


_loop_local = threading.local()


def run_async(coro: asyncio.coroutines) -> object:
    """Run an async coroutine from sync Celery task context.

    Reuses a thread-local event loop to avoid the overhead of creating
    and tearing down a new loop on every call.
    """
    loop = getattr(_loop_local, "loop", None)
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        _loop_local.loop = loop
    return loop.run_until_complete(coro)


def track_run(
    db: Session,
    campaign_id: str,
    stage: str,
    task_id: str | None = None,
) -> PipelineRun:
    """Create a PipelineRun record to track a task execution."""
    run = PipelineRun(
        campaign_id=uuid.UUID(campaign_id),
        stage=stage,
        status="running",
        celery_task_id=task_id,
    )
    db.add(run)
    db.commit()
    return run


def complete_run(
    db: Session, run: PipelineRun, t0: float, error: str | None = None
):
    """Mark a PipelineRun as completed or failed."""
    run.completed_at = datetime.now(timezone.utc)
    run.duration_ms = int((time.monotonic() - t0) * 1000)
    if error:
        run.status = "failed"
        run.error = error
    else:
        run.status = "completed"
    db.commit()


def complete_run_retrying(
    db: Session, run: PipelineRun, t0: float, error: str, retry_count: int
):
    """Close out this attempt as a scheduled Celery retry (not a terminal failure).

    Avoids marking the stage `failed` in the DB while the worker is still
    retrying — otherwise the Generate UI shows a cross during warmup/transients.
    """
    run.completed_at = datetime.now(timezone.utc)
    run.duration_ms = int((time.monotonic() - t0) * 1000)
    run.status = "retrying"
    run.error = error
    run.retry_count = retry_count
    db.commit()


def fail_campaign(db: Session, campaign_id: str, error_msg: str | None = None):
    """Set campaign status to 'failed' for unrecoverable errors."""
    if error_msg:
        log.error("Campaign %s failed: %s", campaign_id, error_msg)
    campaign = db.get(Campaign, uuid.UUID(campaign_id))
    if campaign:
        campaign.status = "failed"
        db.commit()


def structured_error(exc: Exception) -> str:
    """Build a JSON-serializable error string with type and message.

    Full traceback is sent to the server log for debugging but kept out
    of the DB/API response so the frontend shows a clean message.
    """
    import json

    log.error("Task error: %s: %s", type(exc).__name__, exc, exc_info=True)
    return json.dumps(
        {
            "type": type(exc).__name__,
            "message": str(exc),
        }
    )


def get_or_create_prompt_config(db: Session, campaign_id: str) -> PromptConfig:
    """Get the active prompt config for a campaign, or create one."""
    cid = uuid.UUID(campaign_id)
    existing = db.execute(
        select(PromptConfig)
        .where(PromptConfig.campaign_id == cid, PromptConfig.is_active)
        .order_by(PromptConfig.version.desc())
    ).scalar_one_or_none()
    if existing:
        return existing

    pc = PromptConfig(
        campaign_id=cid,
        version=1,
        llm_system_prompt="You are an expert advertising strategist.",
        is_active=True,
    )
    db.add(pc)
    db.commit()
    db.refresh(pc)
    return pc


def store_llm_response(
    db: Session,
    campaign_id: str,
    prompt_config_id: uuid.UUID,
    stage: str,
    result: object,
) -> None:
    """Store an LLM response audit record."""
    db.add(
        LLMResponse(
            campaign_id=uuid.UUID(campaign_id),
            prompt_config_id=prompt_config_id,
            stage=stage,
            raw_request=result.raw_request,
            raw_response=result.raw_response,
            model=result.model,
            tokens_used=result.tokens_used,
            latency_ms=result.latency_ms,
        )
    )
    db.commit()
