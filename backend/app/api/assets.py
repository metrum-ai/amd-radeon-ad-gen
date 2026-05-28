# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

import logging
from urllib.parse import quote

from app.services.minio_client import download_bytes
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("/url")
async def get_asset_url(asset_url: str):
    """Return a backend-routed download URL for a given s3:// asset URL."""
    if not asset_url.startswith("s3://"):
        raise HTTPException(400, "Invalid asset URL format")
    encoded = quote(asset_url, safe="")
    return {
        "download_url": f"/backend/api/assets/download?asset_url={encoded}"
    }


@router.get("/download")
async def download_asset(asset_url: str):
    """Proxy asset bytes through the backend so browser URLs stay same-origin."""
    if not asset_url.startswith("s3://"):
        raise HTTPException(400, "Invalid asset URL format")
    try:
        data = download_bytes(asset_url)
    except Exception as e:
        log.warning("Asset download failed for %s: %s", asset_url, e)
        raise HTTPException(404, "Asset not found") from e

    ext = asset_url.rsplit(".", 1)[-1].lower() if "." in asset_url else ""
    content_types = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "mp4": "video/mp4",
        "zip": "application/zip",
        "pdf": "application/pdf",
    }
    media_type = content_types.get(ext, "application/octet-stream")
    return Response(content=data, media_type=media_type)
