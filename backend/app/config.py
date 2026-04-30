# Created by Metrum AI for AMD

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables with APP_ prefix."""

    model_config = {"env_prefix": "APP_", "case_sensitive": False}

    database_url: str = ""
    redis_url: str = "redis://valkey:6379/0"
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "campaign-assets"
    minio_use_ssl: bool = False
    minio_public_endpoint: str = ""
    minio_public_path_prefix: str = ""
    minio_region: str = "us-east-1"
    newsapi_key: str = ""
    market_data_country: str = "us"
    market_data_trend_timeframe: str = "today 3-m"

    provider_mode: str = "local"

    # Per-provider mode overrides (kept for compatibility; local-only)
    llm_provider_mode: str | None = None
    image_provider_mode: str | None = None
    tts_provider_mode: str | None = None
    video_provider_mode: str | None = None

    # LLM provider (chat-completions compatible; local by default)
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "qwen3:8b"

    # Image provider
    image_api_url: str = ""
    image_api_key: str = ""
    image_model_name: str = "FLUX.1-schnell"

    # TTS provider
    tts_api_url: str = "http://kokoro-tts:8880"

    # Video provider
    video_api_url: str = ""

    # Local provider URLs (used when provider_mode is "local")
    local_llm_url: str = "http://ollama:11434/v1"
    local_image_url: str = "http://flux-server:8002"
    local_tts_url: str = "http://kokoro-tts:8880"
    local_video_url: str = "http://ltx-video:8004"

    # OpenClaw gateway (used when llm_provider_mode is "openclaw")
    openclaw_gateway_url: str = "http://openclaw:18789/v1"
    openclaw_api_key: str = ""
    openclaw_agent_id: str = "main"

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    debug: bool = False


settings = Settings()
