"""MinIO 文件服务: 上传/下载(预签名URL)"""
import asyncio
import uuid
from datetime import timedelta

from minio import Minio

from app.core.config import settings

_client: Minio | None = None
_public_client: Minio | None = None


def get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
    return _client


def get_public_client() -> Minio:
    """预签名专用: endpoint 用外部可达地址, 否则浏览器无法打开链接
    region 显式指定以避免 SDK 联网查询 bucket location"""
    global _public_client
    if _public_client is None:
        _public_client = Minio(
            settings.MINIO_PUBLIC_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
            region="us-east-1",
        )
    return _public_client


async def ensure_bucket() -> None:
    client = get_client()
    exists = await asyncio.to_thread(client.bucket_exists, settings.MINIO_BUCKET)
    if not exists:
        await asyncio.to_thread(client.make_bucket, settings.MINIO_BUCKET)


async def upload(data: bytes, file_name: str, content_type: str) -> tuple[str, str]:
    """返回 (bucket, object_key)"""
    import io

    await ensure_bucket()
    object_key = f"{uuid.uuid4().hex}/{file_name}"
    client = get_client()
    await asyncio.to_thread(
        client.put_object, settings.MINIO_BUCKET, object_key, io.BytesIO(data), len(data), content_type=content_type
    )
    return settings.MINIO_BUCKET, object_key


async def presigned_url(bucket: str, object_key: str) -> str:
    client = get_public_client()
    return await asyncio.to_thread(
        client.presigned_get_object, bucket, object_key, timedelta(hours=2)
    )
