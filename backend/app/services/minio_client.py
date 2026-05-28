# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

import io
import uuid
from urllib.parse import urlsplit, urlunsplit

from app.config import settings
from minio import Minio


def _get_client() -> Minio:
    """Return an S3 client configured for the RustFS storage backend."""
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_use_ssl,
        region=settings.minio_region,
    )


def ensure_bucket() -> None:
    """Create the configured storage bucket if it does not exist."""
    client = _get_client()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def upload_bytes(
    data: bytes,
    campaign_id: str,
    category: str,
    extension: str = "png",
) -> str:
    """Upload binary data to object storage under
    {campaign_id}/{category}/{uuid}.{ext}. Returns the object key."""
    client = _get_client()
    object_name = f"{campaign_id}/{category}/{uuid.uuid4()}.{extension}"
    client.put_object(
        settings.minio_bucket,
        object_name,
        io.BytesIO(data),
        length=len(data),
        content_type=_content_type(extension),
    )
    return f"s3://{settings.minio_bucket}/{object_name}"


def upload_file(
    file_obj,
    length: int,
    campaign_id: str,
    category: str,
    extension: str = "png",
) -> str:
    """Upload a seekable file object to object storage. Avoids loading the full
    payload into a ``bytes`` object, keeping memory usage flat for
    large files like ZIP exports."""
    client = _get_client()
    object_name = f"{campaign_id}/{category}/{uuid.uuid4()}.{extension}"
    client.put_object(
        settings.minio_bucket,
        object_name,
        file_obj,
        length=length,
        content_type=_content_type(extension),
    )
    return f"s3://{settings.minio_bucket}/{object_name}"


def download_bytes(asset_url: str) -> bytes:
    """Download an object from storage given an s3:// URL."""
    client = _get_client()
    _, _, bucket_and_key = asset_url.partition("s3://")
    bucket, _, key = bucket_and_key.partition("/")
    response = client.get_object(bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def _get_public_client() -> Minio:
    endpoint = settings.minio_public_endpoint or settings.minio_endpoint
    return Minio(
        endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_use_ssl,
        region=settings.minio_region,
    )


def presigned_url(asset_url: str, expires_hours: int = 1) -> str:
    """Generate a presigned download URL for the frontend."""
    from datetime import timedelta

    client = _get_public_client()
    _, _, bucket_and_key = asset_url.partition("s3://")
    bucket, _, key = bucket_and_key.partition("/")
    url = client.presigned_get_object(
        bucket, key, expires=timedelta(hours=expires_hours)
    )
    prefix = (settings.minio_public_path_prefix or "").strip()
    if not prefix:
        return url

    if not prefix.startswith("/"):
        prefix = f"/{prefix}"
    prefix = prefix.rstrip("/")

    parts = urlsplit(url)
    rewritten_path = f"{prefix}{parts.path}"
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            rewritten_path,
            parts.query,
            parts.fragment,
        )
    )


def _content_type(ext: str) -> str:
    types = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "mp4": "video/mp4",
        "zip": "application/zip",
    }
    return types.get(ext, "application/octet-stream")
