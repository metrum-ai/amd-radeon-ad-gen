# Created by Metrum AI for AMD

from app.config import settings
from app.providers.base import (
    ImageProvider,
    LLMProvider,
    TTSProvider,
    VideoProvider,
)


def _effective_mode(per_provider: str | None) -> str:
    """Return the effective provider mode, checking per-provider override first."""
    return per_provider or settings.provider_mode


def _require_local(mode: str, name: str) -> None:
    """Raise ValueError if the resolved mode is not 'local'."""
    if mode != "local":
        raise ValueError(
            f"Only local provider mode is supported (got {name}={mode!r})."
        )


def get_llm_provider() -> LLMProvider:
    """Instantiate the configured LLM provider."""
    mode = _effective_mode(settings.llm_provider_mode)
    _require_local(mode, "llm_provider_mode")
    from app.providers.llm.local_provider import LocalLLMProvider

    return LocalLLMProvider()


def get_image_provider() -> ImageProvider:
    """Instantiate the configured image generation provider."""
    mode = _effective_mode(settings.image_provider_mode)
    _require_local(mode, "image_provider_mode")
    from app.providers.image.local_provider import LocalImageProvider

    return LocalImageProvider()


def get_tts_provider() -> TTSProvider:
    """Instantiate the configured TTS provider."""
    mode = _effective_mode(settings.tts_provider_mode)
    _require_local(mode, "tts_provider_mode")
    from app.providers.tts.local_provider import LocalTTSProvider

    return LocalTTSProvider()


def get_video_provider() -> VideoProvider:
    """Instantiate the configured video generation provider."""
    mode = _effective_mode(settings.video_provider_mode)
    _require_local(mode, "video_provider_mode")
    from app.providers.video.local_provider import LocalVideoProvider

    return LocalVideoProvider()
