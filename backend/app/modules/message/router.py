from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.response import ok
from app.database.session import get_db
from app.models import Message

router = APIRouter()


@router.get("/list")
async def list_messages(unread_only: bool = False, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user, _ = ctx
    q = select(Message).where(Message.user_id == user.id, Message.deleted == False)  # noqa: E712
    if unread_only:
        q = q.where(Message.read_flag == False)  # noqa: E712
    rows = await db.scalars(q.order_by(Message.created_time.desc()).limit(50))
    return ok([
        {"id": m.id, "type": m.type, "title": m.title, "content": m.content,
         "read_flag": m.read_flag, "created_time": m.created_time.isoformat()}
        for m in rows.all()
    ])


@router.get("/unread-count")
async def unread_count(ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user, _ = ctx
    from sqlalchemy import func
    count = await db.scalar(
        select(func.count()).select_from(Message).where(Message.user_id == user.id, Message.read_flag == False, Message.deleted == False)  # noqa: E712
    )
    return ok({"count": count})


@router.post("/{message_id}/read")
async def mark_read(message_id: int, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user, _ = ctx
    await db.execute(update(Message).where(Message.id == message_id, Message.user_id == user.id).values(read_flag=True))
    await db.commit()
    return ok()


async def notify(db: AsyncSession, user_ids: list[int], type_: str, title: str, content: str = "",
                 biz_type: str | None = None, biz_id: int | None = None) -> None:
    """供其他模块调用的站内信发送"""
    for uid in user_ids:
        db.add(Message(user_id=uid, type=type_, title=title, content=content, biz_type=biz_type, biz_id=biz_id))


async def notify_enterprise(db: AsyncSession, enterprise_id: int, type_: str, title: str, content: str = "",
                            biz_type: str | None = None, biz_id: int | None = None) -> None:
    """向某企业下所有用户发站内信"""
    from app.models import SysUser
    rows = await db.scalars(select(SysUser).where(SysUser.enterprise_id == enterprise_id, SysUser.deleted == False))  # noqa: E712
    await notify(db, [u.id for u in rows.all()], type_, title, content, biz_type, biz_id)


async def notify_role(db: AsyncSession, role_code: str, type_: str, title: str, content: str = "",
                      biz_type: str | None = None, biz_id: int | None = None) -> None:
    """向某角色所有用户发站内信"""
    from app.models import SysRole, SysUser, SysUserRole
    rows = await db.scalars(
        select(SysUser).join(SysUserRole, SysUserRole.user_id == SysUser.id)
        .join(SysRole, SysRole.id == SysUserRole.role_id)
        .where(SysRole.code == role_code, SysUser.deleted == False)  # noqa: E712
    )
    await notify(db, [u.id for u in rows.all()], type_, title, content, biz_type, biz_id)
