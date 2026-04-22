# Created by Metrum AI for AMD

"""Phase 2 Track 3: Video generation and visual overlay compositing."""

import logging
import os
import subprocess  # nosec B404
import tempfile
import time
import uuid

from app.db.models import Brand, Campaign, CopyVariant, ScenePrompt, VideoAd
from app.services.minio_client import download_bytes, upload_bytes
from app.workers.celery_app import celery
from app.workers.tasks.utils import (
    SyncSession,
    complete_run,
    complete_run_retrying,
    run_async,
    structured_error,
    track_run,
)
from sqlalchemy import select

logger = logging.getLogger(__name__)
VIDEO_BOTTOM_BLUR_RATIO = 0.40
VIDEO_BOTTOM_BLUR_FEATHER_RATIO = 0.10
VIDEO_BOTTOM_BLUR_SIGMA = 18
VIDEO_BOTTOM_BLUR_TOTAL_RATIO = (
    VIDEO_BOTTOM_BLUR_RATIO + VIDEO_BOTTOM_BLUR_FEATHER_RATIO
)
VIDEO_BOTTOM_BLUR_FEATHER_PORTION = (
    VIDEO_BOTTOM_BLUR_FEATHER_RATIO / VIDEO_BOTTOM_BLUR_TOTAL_RATIO
)


def _ensure_video_ads(db, campaign_id: str):
    """Create a single VideoAd from the lifestyle ScenePrompt.

    Only one raw video is generated; mux_video later produces one
    final per CopyVariant."""
    cid = uuid.UUID(campaign_id)
    existing = (
        db.execute(select(VideoAd).where(VideoAd.campaign_id == cid))
        .scalars()
        .all()
    )
    if existing:
        return

    scenes = (
        db.execute(select(ScenePrompt).where(ScenePrompt.campaign_id == cid))
        .scalars()
        .all()
    )

    scene = next(
        (s for s in scenes if s.scene_type == "lifestyle"), None
    ) or next(iter(scenes), None)
    if scene is None:
        return

    db.add(
        VideoAd(
            campaign_id=cid,
            scene_prompt_id=scene.id,
            script=scene.video_script or scene.image_prompt,
        )
    )
    db.commit()


@celery.task(
    bind=True,
    max_retries=5,
    default_retry_delay=45,
    retry_backoff=True,
    soft_time_limit=1200,
    time_limit=1500,
    name="app.workers.tasks.video_gen.generate_video",
    queue="video_gen",
)
def generate_video(self, campaign_id: str) -> str:
    """Generate raw video clips for each scene prompt."""
    from app.providers.base import VideoGenParams, sanitize_video_prompt
    from app.providers.factory import get_video_provider

    t0 = time.monotonic()
    with SyncSession() as db:
        run = track_run(db, campaign_id, "video_gen", self.request.id)

        try:
            # Ensure VideoAd records exist from ScenePrompts
            _ensure_video_ads(db, campaign_id)

            video_ads = (
                db.execute(
                    select(VideoAd).where(
                        VideoAd.campaign_id == uuid.UUID(campaign_id),
                        VideoAd.is_generated.is_(False),
                    )
                )
                .scalars()
                .all()
            )

            provider = get_video_provider()

            campaign = db.get(Campaign, uuid.UUID(campaign_id))
            brand = db.get(Brand, campaign.brand_id) if campaign else None
            brand_name = brand.name if brand else ""
            brand_colors = brand.colors if brand else {}
            product_desc = campaign.product_description if campaign else ""

            logger.info("video_gen: %d ads to generate", len(video_ads))

            for i, ad in enumerate(video_ads):
                scene = db.get(ScenePrompt, ad.scene_prompt_id)
                raw_script = (
                    scene.video_script
                    if scene and scene.video_script
                    else ad.script
                )
                scene_type = scene.scene_type if scene else ""
                prompt = sanitize_video_prompt(
                    raw_script,
                    brand_name=brand_name,
                    brand_colors=brand_colors,
                    scene_type=scene_type,
                    product_description=product_desc,
                )
                logger.info(
                    "video_gen: ad %d scene_type=%s prompt=%s",
                    i + 1,
                    scene_type,
                    prompt[:120],
                )

                params = VideoGenParams()
                t_gen = time.monotonic()
                logger.info(
                    "video_gen: ad %d/%d starting (%dx%d, %d frames, %d steps)",
                    i + 1,
                    len(video_ads),
                    params.width,
                    params.height,
                    params.num_frames,
                    params.num_inference_steps,
                )
                video_bytes = run_async(
                    provider.generate_video(prompt, params)
                )
                logger.info(
                    "video_gen: ad %d/%d done, %d bytes in %.1fs",
                    i + 1,
                    len(video_ads),
                    len(video_bytes),
                    time.monotonic() - t_gen,
                )
                gen_ms = int((time.monotonic() - t_gen) * 1000)

                video_url = upload_bytes(
                    video_bytes, campaign_id, "videos", "mp4"
                )

                ad.video_url = video_url
                ad.model_used = "AnimateDiff-Lightning"
                ad.width = 1024
                ad.height = 1024
                ad.duration_sec = round(params.num_frames / params.fps, 1)
                ad.generation_time_ms = gen_ms
                db.commit()
                logger.info(
                    "video_gen: ad %d/%d committed to DB (visible to frontend)",
                    i + 1,
                    len(video_ads),
                )

            complete_run(db, run, t0)

        except Exception as exc:
            err = structured_error(exc)
            if self.request.retries >= self.max_retries:
                complete_run(db, run, t0, error=err)
                logger.warning(
                    "generate_video exhausted retries for campaign %s "
                    "(non-fatal, returning success to keep chord alive)",
                    campaign_id,
                )
                return campaign_id
            complete_run_retrying(db, run, t0, err, self.request.retries)
            raise self.retry(exc=exc)

    return campaign_id


@celery.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    name="app.workers.tasks.video_gen.generate_voiceover",
    queue="audio",
)
def generate_voiceover(self, campaign_id: str) -> str:
    """Generate TTS voiceovers for video ad scripts."""
    from app.providers.factory import get_tts_provider

    t0 = time.monotonic()
    with SyncSession() as db:
        run = track_run(db, campaign_id, "video_gen", self.request.id)

        try:
            video_ads = (
                db.execute(
                    select(VideoAd).where(
                        VideoAd.campaign_id == uuid.UUID(campaign_id),
                        VideoAd.voiceover_url.is_(None),
                    )
                )
                .scalars()
                .all()
            )

            provider = get_tts_provider()

            for ad in video_ads:
                audio_bytes = run_async(provider.synthesize(ad.script))
                vo_url = upload_bytes(
                    audio_bytes,
                    campaign_id,
                    "voiceovers",
                    "wav",
                )
                ad.voiceover_url = vo_url

            db.commit()

            complete_run(db, run, t0)

        except Exception as exc:
            complete_run(db, run, t0, error=structured_error(exc))
            run.retry_count = self.request.retries
            db.commit()
            if self.request.retries >= self.max_retries:
                logger.warning(
                    "generate_voiceover exhausted retries for campaign %s "
                    "(non-fatal, returning success to keep chord alive)",
                    campaign_id,
                )
                return campaign_id
            raise self.retry(exc=exc)

    return campaign_id


def _mux_single(vf_path, ovf_path, ref_path, out_path, thumb_path):
    """Run ffmpeg to composite one final video + thumbnail."""
    feather_height = (
        f"max(1\\,floor(H*{VIDEO_BOTTOM_BLUR_FEATHER_PORTION:.6f}))"
    )
    strip_height = f"floor(ih*{VIDEO_BOTTOM_BLUR_TOTAL_RATIO})"
    bottom_blur = (
        "[0:v]split=2[base][blur_src];"
        f"[blur_src]crop=w=iw:h='{strip_height}':x=0:y='ih-{strip_height}',"
        f"gblur=sigma={VIDEO_BOTTOM_BLUR_SIGMA},"
        "format=rgba,"
        f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
        f"a='if(lt(Y,{feather_height}),255*Y/{feather_height},255)'"
        "[blurred_strip];"
        "[base][blurred_strip]overlay=0:H-h[base_blurred];"
    )
    if ref_path:
        subprocess.run(  # nosec B603 B607
            [
                "ffmpeg",
                "-y",
                "-i",
                vf_path,
                "-loop",
                "1",
                "-i",
                ref_path,
                "-i",
                ovf_path,
                "-filter_complex",
                (
                    bottom_blur + "[1:v]format=rgba[ref];"
                    "[base_blurred][ref]overlay="
                    "x='(W-w)/2':y='(H-h)/2+8*sin(2*PI*t/2.5)'"
                    ":shortest=1:format=auto[tmp];"
                    "[tmp][2:v]overlay=0:0[out]"
                ),
                "-map",
                "[out]",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-an",
                out_path,
            ],
            check=True,
            capture_output=True,
        )
    else:
        subprocess.run(  # nosec B603 B607
            [
                "ffmpeg",
                "-y",
                "-i",
                vf_path,
                "-i",
                ovf_path,
                "-filter_complex",
                bottom_blur + "[base_blurred][1:v]overlay=0:0[out]",
                "-map",
                "[out]",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-an",
                out_path,
            ],
            check=True,
            capture_output=True,
        )

    subprocess.run(  # nosec B603 B607
        ["ffmpeg", "-y", "-i", out_path, "-frames:v", "1", thumb_path],
        check=True,
        capture_output=True,
    )

    with open(out_path, "rb") as f:
        video = f.read()
    with open(thumb_path, "rb") as f:
        thumb = f.read()
    return video, thumb


@celery.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    soft_time_limit=300,
    time_limit=360,
    name="app.workers.tasks.video_gen.mux_video",
    queue="default",
)
def mux_video(self, campaign_id: str) -> str:
    """Mux raw clips with brand overlays and voiceover audio."""
    from app.services.compositor import (
        compose_overlay_layer,
        compose_reference_layer,
    )

    t0 = time.monotonic()
    with SyncSession() as db:
        run = track_run(db, campaign_id, "video_mux", self.request.id)

        try:
            cid = uuid.UUID(campaign_id)
            campaign = db.get(Campaign, cid)
            brand = db.get(Brand, campaign.brand_id) if campaign else None
            copy_variants = (
                db.execute(
                    select(CopyVariant).where(CopyVariant.campaign_id == cid)
                )
                .scalars()
                .all()
            )
            source_ad = (
                db.execute(
                    select(VideoAd).where(
                        VideoAd.campaign_id == cid,
                        VideoAd.video_url.isnot(None),
                        VideoAd.final_url.is_(None),
                    )
                )
                .scalars()
                .first()
            )

            if not source_ad:
                complete_run(db, run, t0)
                return campaign_id

            if not copy_variants:
                copy_variants = [None]

            video_bytes = download_bytes(source_ad.video_url)
            width = source_ad.width or 1024
            height = source_ad.height or 1024
            ref_url = campaign.reference_image_url if campaign else None

            ref_png = None
            if ref_url:
                ref_png = compose_reference_layer(
                    ref_url,
                    target_size=(width, height),
                )

            for ci, cv in enumerate(copy_variants):
                overlay_png = compose_overlay_layer(
                    headline=cv.headline if cv else "",
                    body=cv.body if cv else "",
                    cta=cv.cta if cv else "",
                    brand_colors=brand.colors if brand else {},
                    brand_fonts=brand.fonts if brand else {},
                    logo_url=brand.logo_url if brand else None,
                    target_size=(width, height),
                )

                tmp_files = []
                try:
                    vf_fd, vf_path = tempfile.mkstemp(suffix=".mp4")
                    ovf_fd, ovf_path = tempfile.mkstemp(suffix=".png")
                    _, out_path = tempfile.mkstemp(suffix=".mp4")
                    _, thumb_path = tempfile.mkstemp(suffix=".jpg")
                    tmp_files.extend([vf_path, ovf_path, out_path, thumb_path])

                    os.write(vf_fd, video_bytes)
                    os.close(vf_fd)
                    os.write(ovf_fd, overlay_png)
                    os.close(ovf_fd)

                    ref_path = None
                    if ref_png:
                        ref_fd, ref_path = tempfile.mkstemp(suffix=".png")
                        tmp_files.append(ref_path)
                        os.write(ref_fd, ref_png)
                        os.close(ref_fd)

                    composited, thumb_bytes = _mux_single(
                        vf_path,
                        ovf_path,
                        ref_path,
                        out_path,
                        thumb_path,
                    )
                finally:
                    for p in tmp_files:
                        try:
                            os.unlink(p)
                        except OSError:
                            pass

                final_url = upload_bytes(
                    composited, campaign_id, "videos_final", "mp4"
                )
                thumb_url = upload_bytes(
                    thumb_bytes, campaign_id, "videos_thumbnails", "jpg"
                )

                if ci == 0:
                    source_ad.final_url = final_url
                    source_ad.voiceover_url = thumb_url
                    source_ad.is_generated = True
                else:
                    db.add(
                        VideoAd(
                            campaign_id=cid,
                            scene_prompt_id=source_ad.scene_prompt_id,
                            script=source_ad.script,
                            model_used=source_ad.model_used,
                            video_url=source_ad.video_url,
                            final_url=final_url,
                            voiceover_url=thumb_url,
                            width=width,
                            height=height,
                            duration_sec=source_ad.duration_sec,
                            generation_time_ms=source_ad.generation_time_ms,
                            is_generated=True,
                        )
                    )
                db.commit()

            complete_run(db, run, t0)

        except Exception as exc:
            err = structured_error(exc)
            if self.request.retries >= self.max_retries:
                complete_run(db, run, t0, error=err)
                logger.warning(
                    "mux_video exhausted retries for campaign %s "
                    "(non-fatal, returning success to keep chord alive)",
                    campaign_id,
                )
                return campaign_id
            complete_run_retrying(db, run, t0, err, self.request.retries)
            raise self.retry(exc=exc)

    return campaign_id
