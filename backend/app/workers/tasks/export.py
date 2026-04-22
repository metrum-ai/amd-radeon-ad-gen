# Created by Metrum AI for AMD

"""Export task: package all campaign assets into a ZIP file."""

import io
import json
import tempfile
import time
import uuid
import zipfile

from app.db.models import (
    AudioAd,
    Campaign,
    CampaignExport,
    CampaignStrategy,
    Composition,
    CopyVariant,
    GeneratedImage,
    PipelineRun,
    ScenePrompt,
    VideoAd,
)
from app.services.minio_client import download_bytes, upload_file
from app.workers.celery_app import celery
from app.workers.tasks.utils import (
    SyncSession,
    complete_run,
    structured_error,
    track_run,
)
from PIL import Image, ImageOps
from sqlalchemy import select


def _safe_download(asset_url: str) -> bytes | None:
    """Download bytes from MinIO, returning None on failure."""
    try:
        return download_bytes(asset_url)
    except Exception:
        return None


def _resize_for_export(
    image_bytes: bytes, target_size: tuple[int, int]
) -> bytes:
    """Create a platform-size PNG using center-crop fit (no stretching)."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    fitted = ImageOps.fit(
        img, target_size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)
    )
    out = io.BytesIO()
    fitted.save(out, format="PNG", optimize=True)
    return out.getvalue()


@celery.task(
    bind=True,
    max_retries=2,
    default_retry_delay=15,
    name="app.workers.tasks.export.export_campaign",
    queue="default",
)
def export_campaign(self, campaign_id: str) -> str:
    """Build a ZIP archive of all campaign assets and upload to MinIO."""
    t0 = time.monotonic()
    with SyncSession() as db:
        run = track_run(db, campaign_id, "export", self.request.id)

        try:
            campaign = db.get(Campaign, uuid.UUID(campaign_id))
            if not campaign:
                raise ValueError("Campaign not found")
            tracks = campaign.tracks or {}
            image_enabled = tracks.get("image_text") is True
            audio_enabled = tracks.get("audio_podcast") is True
            video_enabled = tracks.get("video") is True

            buf = tempfile.SpooledTemporaryFile(max_size=50 * 1024 * 1024)
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                # Strategy JSON (raw text outputs)
                strategies = (
                    db.execute(
                        select(CampaignStrategy).where(
                            CampaignStrategy.campaign_id
                            == uuid.UUID(campaign_id)
                        )
                    )
                    .scalars()
                    .all()
                )
                if strategies:
                    s = strategies[0]
                    zf.writestr(
                        "strategy/strategy.json",
                        json.dumps(
                            {
                                "campaign_direction": s.campaign_direction,
                                "audience_segments": s.audience_segments,
                                "platform_strategy": s.platform_strategy,
                                "messaging_angles": s.messaging_angles,
                            },
                            indent=2,
                        ),
                    )

                # Copy variants JSON (raw text outputs)
                copy_variants = (
                    db.execute(
                        select(CopyVariant).where(
                            CopyVariant.campaign_id == uuid.UUID(campaign_id)
                        )
                    )
                    .scalars()
                    .all()
                )
                if copy_variants:
                    zf.writestr(
                        "strategy/copy_variants.json",
                        json.dumps(
                            [
                                {
                                    "framework": cv.framework,
                                    "headline": cv.headline,
                                    "body": cv.body,
                                    "cta": cv.cta,
                                    "hashtags": cv.hashtags,
                                }
                                for cv in copy_variants
                            ],
                            indent=2,
                        ),
                    )

                # Scene prompts JSON (raw text outputs)
                scenes = (
                    db.execute(
                        select(ScenePrompt).where(
                            ScenePrompt.campaign_id == uuid.UUID(campaign_id)
                        )
                    )
                    .scalars()
                    .all()
                )
                if scenes:
                    zf.writestr(
                        "strategy/scene_prompts.json",
                        json.dumps(
                            [
                                {
                                    "scene_type": sp.scene_type,
                                    "image_prompt": sp.image_prompt,
                                    "video_script": sp.video_script,
                                }
                                for sp in scenes
                            ],
                            indent=2,
                        ),
                    )

                # Audio scripts JSON (raw text outputs)
                all_audio_ads = (
                    db.execute(
                        select(AudioAd).where(
                            AudioAd.campaign_id == uuid.UUID(campaign_id)
                        )
                    )
                    .scalars()
                    .all()
                )
                if all_audio_ads:
                    zf.writestr(
                        "strategy/audio_scripts.json",
                        json.dumps(
                            [
                                {
                                    "tone": ad.tone,
                                    "script": ad.script,
                                    "voice": ad.voice,
                                    "speed": ad.speed,
                                }
                                for ad in all_audio_ads
                            ],
                            indent=2,
                        ),
                    )

                # Raw images (enabled tracks only)
                images = (
                    db.execute(
                        select(GeneratedImage).where(
                            GeneratedImage.campaign_id
                            == uuid.UUID(campaign_id)
                        )
                    )
                    .scalars()
                    .all()
                )
                if image_enabled:
                    for i, img in enumerate(images):
                        data = _safe_download(img.asset_url)
                        if data:
                            zf.writestr(
                                f"assets/raw/images/{img.scene_prompt_id}_{i}.png",
                                data,
                            )

                # Final image compositions
                compositions = (
                    db.execute(
                        select(Composition).where(
                            Composition.campaign_id == uuid.UUID(campaign_id)
                        )
                    )
                    .scalars()
                    .all()
                )
                if image_enabled:
                    for i, comp in enumerate(compositions):
                        data = _safe_download(comp.asset_url)
                        if data:
                            # Keep original composition plus normalized platform variants.
                            zf.writestr(
                                f"assets/final/compositions/{comp.ad_size}_{i}.png",
                                data,
                            )
                            variants = {
                                "1080x1080": (1080, 1080),
                                "1080x1350": (1080, 1350),
                                "1200x628": (1200, 628),
                            }
                            for size_label, target in variants.items():
                                if size_label == comp.ad_size:
                                    continue
                                variant_bytes = _resize_for_export(
                                    data, target
                                )
                                zf.writestr(
                                    f"assets/final/compositions/{size_label}_{i}.png",
                                    variant_bytes,
                                )

                # Final audio outputs
                audio_ads = (
                    db.execute(
                        select(AudioAd).where(
                            AudioAd.campaign_id == uuid.UUID(campaign_id),
                            AudioAd.is_generated.is_(True),
                        )
                    )
                    .scalars()
                    .all()
                )
                if audio_enabled:
                    for i, ad in enumerate(audio_ads):
                        if ad.asset_url:
                            data = _safe_download(ad.asset_url)
                            if data:
                                zf.writestr(
                                    f"assets/final/audio/{ad.tone}_{i}.wav",
                                    data,
                                )

                # Video raw + final outputs
                video_ads = (
                    db.execute(
                        select(VideoAd).where(
                            VideoAd.campaign_id == uuid.UUID(campaign_id),
                        )
                    )
                    .scalars()
                    .all()
                )
                if video_enabled:
                    for i, ad in enumerate(video_ads):
                        if ad.video_url:
                            raw_video = _safe_download(ad.video_url)
                            if raw_video:
                                zf.writestr(
                                    f"assets/raw/video/video_raw_{i}.mp4",
                                    raw_video,
                                )
                        if ad.final_url or ad.video_url:
                            final_video = _safe_download(
                                ad.final_url or ad.video_url
                            )
                            if final_video:
                                zf.writestr(
                                    f"assets/final/video/video_{i}.mp4",
                                    final_video,
                                )

                # OCR report for visual tracks only (skip audio-only campaigns)
                if image_enabled or video_enabled:
                    ocr_rows = [
                        {
                            "image_id": str(img.id),
                            "ocr_pass": img.ocr_pass,
                            "ocr_text_found": img.ocr_text_found or "",
                            "safe_zone_pass": img.safe_zone_pass,
                            "final_score": img.final_score,
                            "is_winner": img.is_winner,
                            "asset_url": img.asset_url,
                        }
                        for img in images
                    ]
                    zf.writestr(
                        "reports/ocr_report.json",
                        json.dumps(
                            {
                                "tracks": tracks,
                                "summary": {
                                    "total_images": len(images),
                                    "ocr_pass_count": sum(
                                        1
                                        for img in images
                                        if img.ocr_pass is True
                                    ),
                                    "ocr_fail_count": sum(
                                        1
                                        for img in images
                                        if img.ocr_pass is False
                                    ),
                                },
                                "rows": ocr_rows,
                            },
                            indent=2,
                        ),
                    )

                pipeline_runs = (
                    db.execute(
                        select(PipelineRun).where(
                            PipelineRun.campaign_id == uuid.UUID(campaign_id)
                        )
                    )
                    .scalars()
                    .all()
                )
                if pipeline_runs:
                    zf.writestr(
                        "reports/pipeline_runs.json",
                        json.dumps(
                            [
                                {
                                    "stage": r.stage,
                                    "status": r.status,
                                    "duration_ms": r.duration_ms,
                                    "retry_count": r.retry_count,
                                    "error": r.error,
                                }
                                for r in pipeline_runs
                            ],
                            indent=2,
                        ),
                    )

                # Campaign metadata
                zf.writestr(
                    "campaign.json",
                    json.dumps(
                        {
                            "id": str(campaign.id),
                            "name": campaign.name,
                            "objective": campaign.objective,
                            "product_description": campaign.product_description,
                            "tone": campaign.tone,
                            "status": campaign.status,
                            "tracks": campaign.tracks,
                        },
                        indent=2,
                    ),
                )

            buf.seek(0, 2)
            zip_size = buf.tell()
            buf.seek(0)
            asset_url = upload_file(
                buf, zip_size, campaign_id, "exports", "zip"
            )

            db.add(
                CampaignExport(
                    campaign_id=uuid.UUID(campaign_id),
                    asset_url=asset_url,
                    format="zip",
                )
            )
            db.commit()

            complete_run(db, run, t0)

        except Exception as exc:
            complete_run(db, run, t0, error=structured_error(exc))
            raise self.retry(exc=exc)

    return campaign_id
