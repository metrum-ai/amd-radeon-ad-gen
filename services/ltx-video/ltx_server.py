# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

"""AnimateDiff-Lightning video generation HTTP server (ROCm / CUDA via PyTorch).

Exposes POST /v1/videos/generations returning raw MP4 bytes.
Uses ByteDance AnimateDiff-Lightning 2-step distilled weights on DreamShaper base
with 3 inference steps (officially recommended sweet spot) and a Motion LoRA
for stronger, more dynamic motion.
"""

from __future__ import annotations

import asyncio
import gc
import logging
import os
import subprocess  # nosec B404
import tempfile
import threading
import time

os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ["HF_HUB_DISABLE_XET"] = "1"
try:
    import huggingface_hub.constants as _hf_consts

    if hasattr(_hf_consts, "HF_HUB_DISABLE_XET"):
        _hf_consts.HF_HUB_DISABLE_XET = True
    if hasattr(_hf_consts, "HF_HUB_ENABLE_HF_TRANSFER"):
        _hf_consts.HF_HUB_ENABLE_HF_TRANSFER = False
except Exception:  # nosec B110
    pass

import imageio_ffmpeg
import torch
from diffusers import (
    AnimateDiffPipeline,
    EulerDiscreteScheduler,
    MotionAdapter,
)
from diffusers.utils import export_to_video
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from huggingface_hub import hf_hub_download
from pydantic import BaseModel, Field
from safetensors.torch import load_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_MODEL = os.getenv("VIDEO_BASE_MODEL", "Lykon/DreamShaper")
LIGHTNING_REPO = "ByteDance/AnimateDiff-Lightning"
LIGHTNING_STEPS = int(os.getenv("LIGHTNING_STEPS", "2"))
LIGHTNING_CKPT = (
    f"animatediff_lightning_{LIGHTNING_STEPS}step_diffusers.safetensors"
)

MOTION_LORA = os.getenv(
    "MOTION_LORA", "guoyww/animatediff-motion-lora-zoom-out"
)
MOTION_LORA_STRENGTH = float(os.getenv("MOTION_LORA_STRENGTH", "0.75"))

DEFAULT_NEGATIVE = (
    "ugly, blurry, noisy, grainy, pixelated, low quality, worst quality, "
    "deformed, disfigured, bad anatomy, bad proportions, extra limbs, "
    "text, watermark, signature, logo, face, person, human, hands, fingers, "
    "realistic photo, photograph, complex details, fine details"
)

app = FastAPI(title="AnimateDiff-Lightning Server")
pipeline: AnimateDiffPipeline | None = None
gpu_lock = threading.Lock()


class GenerateRequest(BaseModel):
    """Inbound payload for video generation."""

    prompt: str
    negative_prompt: str | None = None
    width: int = Field(default=512, ge=256, le=768)
    height: int = Field(default=512, ge=256, le=768)
    num_frames: int = Field(default=32, ge=4, le=32)
    num_inference_steps: int = Field(default=3, ge=1, le=20)
    guidance_scale: float = Field(default=1.0, ge=0.0, le=20.0)
    fps: int = Field(default=8, ge=1, le=30)
    seed: int | None = None


def _align_dim(x: int, multiple: int = 8, cap: int = 768) -> int:
    """SD1.5 latents work in multiples of 8."""
    x = min(max(x, multiple), cap)
    return (x // multiple) * multiple


def load_pipeline() -> AnimateDiffPipeline:
    """Load AnimateDiff-Lightning with fp16 weights."""
    device = "cuda"
    dtype = torch.float16

    torch.backends.cudnn.benchmark = True
    torch.backends.cuda.matmul.allow_tf32 = True

    logger.info(
        "Resolving Lightning weights: %s / %s ...",
        LIGHTNING_REPO,
        LIGHTNING_CKPT,
    )
    try:
        ckpt_path = hf_hub_download(
            LIGHTNING_REPO,
            LIGHTNING_CKPT,
            local_files_only=True,
        )
        logger.info("Lightning weights cache hit")
    except Exception:
        logger.info(
            "Lightning weights cache miss; downloading from Hugging Face"
        )
        ckpt_path = hf_hub_download(LIGHTNING_REPO, LIGHTNING_CKPT)

    logger.info("Loading MotionAdapter (%d-step) ...", LIGHTNING_STEPS)
    adapter = MotionAdapter().to(device, dtype)
    adapter.load_state_dict(load_file(ckpt_path, device=device))

    logger.info("Loading base model %s with motion adapter ...", BASE_MODEL)
    try:
        pipe = AnimateDiffPipeline.from_pretrained(
            BASE_MODEL,
            motion_adapter=adapter,
            torch_dtype=dtype,
            safety_checker=None,
            requires_safety_checker=False,
            local_files_only=True,
        )
        logger.info("Base model cache hit")
    except Exception:
        logger.info("Base model cache miss; downloading from Hugging Face")
        pipe = AnimateDiffPipeline.from_pretrained(
            BASE_MODEL,
            motion_adapter=adapter,
            torch_dtype=dtype,
            safety_checker=None,
            requires_safety_checker=False,
        )

    pipe = pipe.to(device)

    pipe.scheduler = EulerDiscreteScheduler.from_config(
        pipe.scheduler.config,
        timestep_spacing="trailing",
        beta_schedule="linear",
    )
    pipe.set_progress_bar_config(disable=True)
    pipe.enable_vae_slicing()

    if MOTION_LORA:
        logger.info(
            "Loading Motion LoRA: %s (strength=%.2f) ...",
            MOTION_LORA,
            MOTION_LORA_STRENGTH,
        )
        try:
            try:
                pipe.load_lora_weights(
                    MOTION_LORA,
                    adapter_name="motion_lora",
                    local_files_only=True,
                )
                logger.info("Motion LoRA cache hit")
            except Exception:
                logger.info(
                    "Motion LoRA cache miss; downloading from Hugging Face"
                )
                pipe.load_lora_weights(MOTION_LORA, adapter_name="motion_lora")
            pipe.set_adapters(
                ["motion_lora"], adapter_weights=[MOTION_LORA_STRENGTH]
            )
            logger.info("Motion LoRA loaded and active")
        except Exception:
            logger.warning(
                "Failed to load Motion LoRA, continuing without it",
                exc_info=True,
            )

    sdpa_available = hasattr(
        torch.nn.functional, "scaled_dot_product_attention"
    )
    logger.info("SDPA available: %s", sdpa_available)
    if sdpa_available:
        from diffusers.models.attention_processor import AttnProcessor2_0

        pipe.unet.set_attn_processor(AttnProcessor2_0())
        logger.info("Enabled SDPA (AttnProcessor2_0) on UNet")

    for name in ["unet", "vae", "text_encoder"]:
        comp = getattr(pipe, name, None)
        if comp is not None:
            actual = next(comp.parameters()).device
            logger.info("  %s device: %s", name, actual)

    vram_gb = torch.cuda.memory_allocated() / 1e9
    logger.info("Pipeline ready on GPU (VRAM allocated: %.2f GB)", vram_gb)
    return pipe


def _warmup(pipe: AnimateDiffPipeline) -> None:
    """Run one fast generation to pre-compile all ROCm/CUDA kernels."""
    logger.info("Warm-up: compiling kernels for 512x512 x 32 frames ...")
    t0 = time.monotonic()
    with gpu_lock:
        with torch.inference_mode():
            out = pipe(
                prompt="warmup test pattern",
                width=512,
                height=512,
                num_frames=32,
                num_inference_steps=3,
                guidance_scale=1.0,
            )
        torch.cuda.synchronize()
        del out
        gc.collect()
        torch.cuda.empty_cache()
    logger.info("Warm-up complete in %.1fs.", time.monotonic() - t0)


@app.on_event("startup")
async def startup() -> None:
    """Load the pipeline and run warm-up on startup."""
    global pipeline
    loop = asyncio.get_running_loop()
    pipeline = await loop.run_in_executor(None, load_pipeline)
    await loop.run_in_executor(None, _warmup, pipeline)


@app.get("/health")
async def health() -> dict:
    """Return server health and model load status."""
    return {"status": "ok", "loaded": pipeline is not None}


@app.post("/v1/videos/generations")
async def generate(req: GenerateRequest) -> Response:
    """Generate a video clip and return MP4 bytes."""
    if pipeline is None:
        raise HTTPException(503, "Model not loaded yet")

    w = _align_dim(req.width)
    h = _align_dim(req.height)

    generator = None
    if req.seed is not None:
        generator = torch.Generator(device="cpu").manual_seed(req.seed)

    loop = asyncio.get_running_loop()

    def _run() -> str:
        neg = req.negative_prompt or DEFAULT_NEGATIVE

        with gpu_lock:
            t0 = time.monotonic()
            with torch.inference_mode():
                out = pipeline(
                    prompt=req.prompt,
                    negative_prompt=neg,
                    width=w,
                    height=h,
                    num_frames=req.num_frames,
                    num_inference_steps=req.num_inference_steps,
                    guidance_scale=req.guidance_scale,
                    generator=generator,
                )
            torch.cuda.synchronize()
            frames = out.frames[0]
            del out
            gc.collect()
            torch.cuda.empty_cache()

            with tempfile.NamedTemporaryFile(
                suffix=".mp4", delete=False
            ) as tmp:
                raw_path = tmp.name
            export_to_video(frames, raw_path, fps=req.fps)
            del frames
            gc.collect()

            gpu_elapsed = time.monotonic() - t0
            logger.info(
                "GPU: %dx%d x %d frames in %.1fs",
                w,
                h,
                req.num_frames,
                gpu_elapsed,
            )

        t_ffmpeg = time.monotonic()
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            final_path = tmp.name
        try:
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
            subprocess.run(  # nosec B603 B607
                [
                    ffmpeg_bin,
                    "-y",
                    "-i",
                    raw_path,
                    "-vf",
                    (
                        "scale=1024:1024:flags=lanczos,"
                        "hqdn3d=4:3:6:4,"
                        "unsharp=5:5:0.8:5:5:0.0"
                    ),
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "18",
                    "-an",
                    final_path,
                ],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            logger.warning(
                "ffmpeg upscale failed, returning raw: %s",
                e.stderr[-200:] if e.stderr else "",
            )
            final_path = raw_path
            raw_path = None
        finally:
            if raw_path:
                try:
                    os.unlink(raw_path)
                except OSError:
                    pass

        ffmpeg_elapsed = time.monotonic() - t_ffmpeg
        total = time.monotonic() - t0
        logger.info(
            "ffmpeg: %.1fs | Total: %.1fs (GPU %.1fs + ffmpeg %.1fs)",
            ffmpeg_elapsed,
            total,
            gpu_elapsed,
            ffmpeg_elapsed,
        )
        return final_path

    path: str | None = None
    try:
        path = await loop.run_in_executor(None, _run)
        with open(path, "rb") as f:
            data = f.read()
    except Exception as exc:
        logger.exception("Video generation failed")
        raise HTTPException(500, str(exc)) from exc
    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass

    return Response(content=data, media_type="video/mp4")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)  # nosec B104
