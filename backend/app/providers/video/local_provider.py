# Created by Metrum AI for AMD

"""Local video provider: POST JSON to video generation HTTP service, MP4 bytes back."""

import httpx
from app.config import settings
from app.providers.base import VideoGenParams, VideoProvider


class LocalVideoProvider(VideoProvider):
    """Calls the self-hosted AnimateDiff-Lightning FastAPI service."""

    def __init__(self) -> None:
        self._base_url = settings.local_video_url.rstrip("/")

    async def generate_video(
        self, prompt: str, params: VideoGenParams
    ) -> bytes:
        payload = {
            "prompt": prompt,
            "width": params.width,
            "height": params.height,
            "num_frames": params.num_frames,
            "num_inference_steps": params.num_inference_steps,
            "guidance_scale": params.guidance_scale,
            "fps": params.fps,
        }
        if params.seed is not None:
            payload["seed"] = params.seed

        timeout = httpx.Timeout(600.0, connect=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{self._base_url}/v1/videos/generations",
                json=payload,
            )
            resp.raise_for_status()
            return resp.content
