# Created by Metrum AI for AMD

"""CLI health check script for all services.

Usage: python -m app.cli.healthcheck
"""

import asyncio
import sys
from urllib.parse import urlparse

import httpx
from app.config import settings


def _redact_url(url: str) -> str:
    """Strip credentials from a database URL for safe display."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "unknown"
        port = f":{parsed.port}" if parsed.port else ""
        db = parsed.path.lstrip("/") or "unknown"
        return f"{parsed.scheme}://***@{host}{port}/{db}"
    except Exception:
        return "***"


async def check_http(name: str, url: str, timeout: float = 5.0) -> bool:
    """Check reachability of an HTTP endpoint."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            ok = resp.status_code < 500
            status = "OK" if ok else f"DEGRADED ({resp.status_code})"
            print(f"  [{status}] {name}: {url}")
            return ok
    except Exception as exc:
        print(f"  [FAIL] {name}: {url} -- {exc}")
        return False


async def check_postgres() -> bool:
    """Verify PostgreSQL connectivity."""
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(settings.database_url)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))  # nosemgrep: avoid-sqlalchemy-text
        await engine.dispose()
        print(f"  [OK] PostgreSQL: {_redact_url(settings.database_url)}")
        return True
    except Exception as exc:
        print(f"  [FAIL] PostgreSQL: {_redact_url(settings.database_url)} -- {exc}")
        return False


async def check_valkey() -> bool:
    """Verify Valkey connectivity."""
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        print(f"  [OK] Valkey: {settings.redis_url}")
        return True
    except Exception as exc:
        print(f"  [FAIL] Valkey: {settings.redis_url} -- {exc}")
        return False


async def check_minio() -> bool:
    """Verify MinIO liveness."""
    proto = "https" if settings.minio_use_ssl else "http"
    url = f"{proto}://{settings.minio_endpoint}/minio/health/live"
    return await check_http("MinIO", url)


async def main():
    """Run all health checks and report results."""
    print("\n=== AI Ad Generator - Health Check ===\n")
    print(f"Provider mode: {settings.provider_mode}")
    print(
        f"LLM provider:  {settings.llm_provider_mode or settings.provider_mode}"
    )
    print(
        f"Image provider: {settings.image_provider_mode or settings.provider_mode}"
    )
    print(
        f"TTS provider:  {settings.tts_provider_mode or settings.provider_mode}"
    )
    print(
        f"Video provider: {settings.video_provider_mode or settings.provider_mode}"
    )
    print()

    print("Infrastructure:")
    results = []
    results.append(await check_postgres())
    results.append(await check_valkey())
    results.append(await check_minio())

    print("\nServices:")
    results.append(
        await check_http("TTS (Kokoro)", f"{settings.tts_api_url}/health")
    )
    video_health = f"{settings.local_video_url.rstrip('/')}/health"
    results.append(await check_http("Video (LTX)", video_health))

    print("\nProviders:")
    results.append(
        await check_http("LLM (local)", f"{settings.local_llm_url}/health")
    )

    results.append(
        await check_http(
            "Image (local)", f"{settings.local_image_url}/health"
        )
    )

    print()
    passed = sum(results)
    total = len(results)
    if passed == total:
        print(f"All {total} checks passed.")
    else:
        print(f"{passed}/{total} checks passed. {total - passed} failed.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
