# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

"""Self-hosted FLUX.1-schnell image generation server.

Wraps HuggingFace diffusers FluxPipeline in a minimal FastAPI service
that exposes a single POST /v1/images/generations endpoint.
Returns raw PNG bytes (Content-Type: image/png).

FLUX.1-schnell is the distilled variant of FLUX.1-dev (same 12B-param
architecture) trained with latent adversarial diffusion distillation.
It produces good images in only 4 steps with guidance_scale=0.0 and
max_sequence_length=256, cutting denoising time by ~6x compared to
the 25-step FLUX.1-dev workflow.

Uses bf16 weights with CPU offload (model exceeds single-GPU VRAM).
"""

import asyncio
import gc
import io
import logging
import os
import threading
import time

# hf_transfer is not installed in this image, so keep it off.
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
# Xet downloads are on by default: in testing they moved ~31% fewer bytes,
# ran ~3x faster, and tolerate slow links better (300s read timeout, adaptive
# concurrency, backoff retries). Set HF_HUB_DISABLE_XET=1 in the compose file
# to fall back to plain HTTP, e.g. on networks that block Xet's CAS endpoint.
os.environ.setdefault("HF_HUB_DISABLE_XET", "0")
try:
    import huggingface_hub.constants as _hf_consts

    if hasattr(_hf_consts, "HF_HUB_ENABLE_HF_TRANSFER"):
        _hf_consts.HF_HUB_ENABLE_HF_TRANSFER = False
except Exception:  # nosec B110
    pass

import torch
from diffusers import FluxPipeline
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FLUX_MODEL_ID = os.getenv("FLUX_MODEL_ID", "black-forest-labs/FLUX.1-schnell")

app = FastAPI(title="FLUX.1-schnell Image Server")

pipeline: FluxPipeline | None = None
gpu_lock = threading.Lock()


class GenerateRequest(BaseModel):
    """Inbound payload for image generation."""

    prompt: str
    negative_prompt: str | None = None
    width: int = Field(default=1024, ge=256, le=2048)
    height: int = Field(default=1024, ge=256, le=2048)
    num_inference_steps: int = Field(default=4, ge=1, le=100)
    guidance_scale: float = Field(default=0.0, ge=0.0, le=20.0)
    max_sequence_length: int = Field(default=256, ge=64, le=512)
    seed: int | None = None


def load_model() -> FluxPipeline:
    """Load FLUX.1-schnell with bf16 weights and CPU offload."""
    logger.info("Loading %s (bf16, CPU offload) ...", FLUX_MODEL_ID)
    try:
        pipe = FluxPipeline.from_pretrained(
            FLUX_MODEL_ID,
            torch_dtype=torch.bfloat16,
            local_files_only=True,
        )
        logger.info("Model cache hit")
    except Exception:
        logger.info("Model cache miss; downloading from Hugging Face")
        pipe = FluxPipeline.from_pretrained(
            FLUX_MODEL_ID,
            torch_dtype=torch.bfloat16,
        )
    pipe.enable_model_cpu_offload()
    pipe.vae.enable_tiling()
    pipe.vae.enable_slicing()
    pipe.set_progress_bar_config(disable=True)
    logger.info("Model loaded: bf16 with CPU offload + VAE tiling/slicing.")
    return pipe


def _warmup(pipe: FluxPipeline):
    """Run a full-resolution dummy inference to JIT-compile HIP/ROCm
    kernels and pre-allocate GPU memory pools at the target ad
    resolution. This avoids the ~4-minute cold-start penalty on the
    first real request (expandable_segments needs to build its pool)."""
    warmup_w, warmup_h = 1088, 1344
    logger.info("Running warm-up inference at %dx%d ...", warmup_w, warmup_h)
    t0 = time.monotonic()
    out = pipe(
        prompt="warmup",
        width=warmup_w,
        height=warmup_h,
        num_inference_steps=4,
        guidance_scale=0.0,
        max_sequence_length=256,
    )
    torch.cuda.synchronize()
    del out
    gc.collect()
    torch.cuda.empty_cache()
    elapsed = time.monotonic() - t0
    logger.info("Warm-up complete in %.1fs. GPU memory pools primed.", elapsed)


@app.on_event("startup")
async def startup():
    """Load the model and run warm-up on application startup."""
    global pipeline
    loop = asyncio.get_running_loop()
    pipeline = await loop.run_in_executor(None, load_model)
    await loop.run_in_executor(None, _warmup, pipeline)


@app.get("/health")
async def health():
    """Return server health and model load status."""
    return {"status": "ok", "loaded": pipeline is not None}


@app.post("/v1/images/generations")
async def generate(req: GenerateRequest):
    """Generate an image from the given prompt and return PNG bytes."""
    if pipeline is None:
        raise HTTPException(503, "Model not loaded yet")

    generator = None
    if req.seed is not None:
        generator = torch.Generator(device="cpu").manual_seed(req.seed)

    kwargs = {
        "prompt": req.prompt,
        "width": req.width,
        "height": req.height,
        "num_inference_steps": req.num_inference_steps,
        "guidance_scale": req.guidance_scale,
        "max_sequence_length": req.max_sequence_length,
        "generator": generator,
    }

    loop = asyncio.get_running_loop()

    def _run():
        with gpu_lock:
            t0 = time.monotonic()
            result = pipeline(**kwargs)
            torch.cuda.synchronize()
            elapsed = time.monotonic() - t0
            logger.info(
                "Generated %dx%d in %.1fs (%d steps)",
                req.width,
                req.height,
                elapsed,
                req.num_inference_steps,
            )
            img = result.images[0]
            del result
            gc.collect()
            torch.cuda.empty_cache()
            return img

    try:
        image = await loop.run_in_executor(None, _run)
    except Exception as exc:
        logger.exception("Generation failed")
        raise HTTPException(500, str(exc)) from exc

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)  # nosec B104
