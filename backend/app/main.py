# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

from contextlib import asynccontextmanager

from app.api import (
    assets,
    brands,
    campaigns,
    exports,
    health,
    metrics,
    pipeline,
)
from app.config import settings
from app.services.minio_client import ensure_bucket
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):  # pylint: disable=redefined-outer-name,unused-argument
    """Ensure the MinIO bucket exists on startup."""
    ensure_bucket()
    yield


app = FastAPI(
    title="AI Ad Campaign Pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(brands.router)
app.include_router(campaigns.router)
app.include_router(pipeline.router)
app.include_router(assets.router)
app.include_router(metrics.router)
app.include_router(exports.router)
app.include_router(health.router)


@app.get("/health")
async def root_health():
    """Lightweight liveness probe for the API gateway."""
    return {"status": "ok", "service": "adgen-api"}
