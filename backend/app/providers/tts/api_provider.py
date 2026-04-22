# Created by Metrum AI for AMD

import httpx
from app.config import settings
from app.providers.base import TTSProvider


class APITTSProvider(TTSProvider):
    """Calls the Kokoro TTS server over HTTP."""

    def __init__(self) -> None:
        self._base_url = settings.tts_api_url.rstrip("/")

    async def synthesize(
        self, text: str, voice: str = "af_heart", speed: float = 1.0
    ) -> bytes:
        payload = {
            "input": text,
            "voice": voice,
            "speed": speed,
            "response_format": "wav",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self._base_url}/v1/audio/speech",
                json=payload,
            )
            resp.raise_for_status()
            return resp.content
