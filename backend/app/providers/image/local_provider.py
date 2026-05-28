# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

"""Local FLUX.1-Dev provider -- calls a locally-served FLUX FastAPI
server running on GPU 1.

POLICY: Generated images must NEVER contain text. All text is added in
post-production by the compositor.
"""

import httpx
from app.config import settings
from app.providers.base import (
    AD_NEGATIVE_PROMPT,
    ImageGenParams,
    ImageProvider,
    sanitize_image_prompt,
)


class LocalImageProvider(ImageProvider):
    """Calls a locally-served FLUX FastAPI server for image generation."""

    def __init__(self) -> None:
        self._base_url = settings.local_image_url

    async def generate_image(
        self, prompt: str, params: ImageGenParams
    ) -> bytes:
        prompt = sanitize_image_prompt(prompt)

        if not params.negative_prompt:
            params.negative_prompt = AD_NEGATIVE_PROMPT

        payload = {
            "prompt": prompt,
            "negative_prompt": params.negative_prompt,
            "width": params.width,
            "height": params.height,
            "num_inference_steps": params.num_inference_steps,
            "guidance_scale": params.guidance_scale,
            "max_sequence_length": params.max_sequence_length,
        }
        if params.seed is not None:
            payload["seed"] = params.seed

        timeout = httpx.Timeout(300, connect=10)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{self._base_url}/v1/images/generations",
                json=payload,
            )
            resp.raise_for_status()
            return resp.content
