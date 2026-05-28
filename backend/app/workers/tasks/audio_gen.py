# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

"""Phase 2 Track 2: Audio generation via Kokoro TTS."""

import time
import uuid

from app.db.models import AudioAd
from app.services.minio_client import upload_bytes
from app.workers.celery_app import celery
from app.workers.tasks.utils import (
    SyncSession,
    complete_run,
    fail_campaign,
    run_async,
    structured_error,
    track_run,
)
from sqlalchemy import select

# WAV header is 44 bytes; 24kHz mono 16-bit PCM = 48000 bytes/sec
WAV_HEADER_SIZE = 44
SAMPLE_RATE = 24000
BYTES_PER_SAMPLE = 2


@celery.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    name="app.workers.tasks.audio_gen.generate_audio",
    queue="audio",
)
def generate_audio(self, campaign_id: str) -> str:
    """Generate TTS audio for all audio ad scripts in the campaign."""
    from app.providers.factory import get_tts_provider

    t0 = time.monotonic()
    with SyncSession() as db:
        run = track_run(db, campaign_id, "audio_gen", self.request.id)

        try:
            audio_ads = (
                db.execute(
                    select(AudioAd).where(
                        AudioAd.campaign_id == uuid.UUID(campaign_id),
                        AudioAd.is_generated.is_(False),
                    )
                )
                .scalars()
                .all()
            )

            provider = get_tts_provider()

            for ad in audio_ads:
                audio_bytes = run_async(
                    provider.synthesize(ad.script, ad.voice, ad.speed)
                )

                asset_url = upload_bytes(
                    audio_bytes, campaign_id, "audio", "wav"
                )

                ad.asset_url = asset_url
                ad.is_generated = True
                # Account for 44-byte WAV header in duration calculation
                pcm_bytes = max(0, len(audio_bytes) - WAV_HEADER_SIZE)
                ad.duration_sec = pcm_bytes / (SAMPLE_RATE * BYTES_PER_SAMPLE)
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
