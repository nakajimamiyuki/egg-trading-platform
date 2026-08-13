from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_optional_user
from app.core.response import BizError, ok
from app.database.session import get_db
from app.models import FileRecord
from app.modules.file import service as file_service

router = APIRouter()

MAX_SIZE = 20 * 1024 * 1024  # 20MB

# 上传类型白名单(防可执行文件上传)
ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif",   # 图片(证照/装车照片/点位图)
    ".mp4", ".mov", ".m4v",                      # 视频(装车视频)
    ".pdf", ".html", ".txt",                     # 文档(合同/报告/回单)
    ".xlsx", ".xls", ".docx", ".doc", ".csv",    # 办公文档
}


@router.post("/upload")
async def upload_file(file: UploadFile, biz_type: str = "OTHER",
                      ctx=Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """上传文件。注册场景允许未登录上传(仅用于证照), 登录用户记录 created_by"""
    import os

    user, _ = ctx
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise BizError(f"不支持的文件类型 {ext or '(无扩展名)'}, 仅允许图片/视频/文档")
    data = await file.read()
    if len(data) > MAX_SIZE:
        raise BizError("文件超过 20MB 限制")
    bucket, object_key = await file_service.upload(data, file.filename, file.content_type or "application/octet-stream")
    record = FileRecord(
        bucket=bucket, object_key=object_key, file_name=file.filename,
        file_size=len(data), content_type=file.content_type, biz_type=biz_type,
        created_by=user.id if user else None,
    )
    db.add(record)
    await db.commit()
    return ok({"file_id": record.id, "file_name": record.file_name})


@router.get("/{file_id}/url")
async def get_url(file_id: int, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    record = await db.get(FileRecord, file_id)
    if not record or record.deleted:
        raise BizError("文件不存在", code=404)
    url = await file_service.presigned_url(record.bucket, record.object_key)
    return ok({"url": url, "file_name": record.file_name})
