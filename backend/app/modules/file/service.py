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


async def download(bucket: str, object_key: str) -> bytes:
    client = get_client()
    resp = await asyncio.to_thread(client.get_object, bucket, object_key)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()


async def reupload(bucket: str, object_key: str, data: bytes, content_type: str = "image/jpeg") -> None:
    import io

    client = get_client()
    await asyncio.to_thread(client.put_object, bucket, object_key, io.BytesIO(data), len(data), content_type=content_type)


def watermark_image(data: bytes, text: str) -> bytes:
    """给图片右下角加水印文字 (F5.1 装车照片防复用)"""
    import io

    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(io.BytesIO(data)).convert("RGB")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=max(18, img.width // 35))
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = img.width - w - 24, img.height - h - 24
    draw.rectangle([x - 12, y - 8, x + w + 12, y + h + 8], fill=(0, 0, 0))
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()
