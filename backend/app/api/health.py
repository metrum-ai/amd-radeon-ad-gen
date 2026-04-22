# Created by Metrum AI for AMD

"""Provider health-check and capability detection endpoints."""

import asyncio
import logging

import httpx
from app.config import settings
from fastapi import APIRouter

router = APIRouter(prefix="/api/health", tags=["health"])
log = logging.getLogger(__name__)


async def _probe(url: str, timeout: float = 3.0) -> bool:
    """Return True if a GET to *url* returns a non-5xx response."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            return resp.status_code < 500
    except Exception:
        return False


async def _check_http(name: str, url: str, timeout: float = 5.0) -> dict:
    """Probe an HTTP endpoint and return status dict."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            return {
                "name": name,
                "url": url,
                "status": "ok" if resp.status_code < 500 else "degraded",
                "status_code": resp.status_code,
            }
    except Exception as exc:
        return {
            "name": name,
            "url": url,
            "status": "unreachable",
            "error": str(exc),
        }


async def _check_postgres() -> dict:
    from sqlalchemy import text

    from app.db.session import engine as async_engine

    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))  # nosemgrep: avoid-sqlalchemy-text
        return {"name": "postgresql", "status": "ok"}
    except Exception as exc:
        return {
            "name": "postgresql",
            "status": "unreachable",
            "error": str(exc),
        }


async def _check_valkey() -> dict:
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        return {"name": "valkey", "status": "ok"}
    except Exception as exc:
        return {"name": "valkey", "status": "unreachable", "error": str(exc)}


async def _check_minio() -> dict:
    proto = "https" if settings.minio_use_ssl else "http"
    url = f"{proto}://{settings.minio_endpoint}/minio/health/live"
    return await _check_http("minio", url)


@router.get("/providers")
async def provider_health():
    """Check connectivity to all configured providers and infrastructure."""
    checks = [
        _check_postgres(),
        _check_valkey(),
        _check_minio(),
        _check_http("tts", f"{settings.tts_api_url}/health"),
        _check_http("video", f"{settings.local_video_url.rstrip('/')}/health"),
    ]

    checks.append(_check_http("llm", f"{settings.local_llm_url}/health"))

    checks.append(_check_http("image", f"{settings.local_image_url}/health"))

    results = await asyncio.gather(*checks)

    all_ok = all(r["status"] == "ok" for r in results)
    return {
        "status": "ok" if all_ok else "degraded",
        "providers": results,
    }


@router.get("/capabilities")
async def capabilities():
    """Detect available generation tracks by probing local services."""
    llm_url = f"{settings.local_llm_url.rstrip('/')}/health"
    llm_up = await _probe(llm_url)
    llm_available = llm_up

    img_mode = "local"
    image_url = f"{settings.local_image_url.rstrip('/')}/health"
    image_up = await _probe(image_url)

    vid_mode = "local"
    video_url = f"{settings.local_video_url.rstrip('/')}/health"
    video_up = await _probe(video_url)

    return {
        "services": {
            "llm": {"url": llm_url, "up": llm_up},
            "image": {"url": image_url, "up": image_up, "mode": img_mode},
            "video": {"url": video_url, "up": video_up, "mode": vid_mode},
        },
        "allowed_tracks": {
            "llm": llm_available,
            "image": image_up,
            "video": video_up,
        },
    }
