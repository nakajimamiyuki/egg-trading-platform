from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import BizError
from app.core.security import parse_token
from app.database.session import get_db
from app.models import SysRole, SysUser, SysUserRole


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> tuple[SysUser, list[str]]:
    """解析 Bearer Token, 返回 (用户, 角色code列表)"""
    if not authorization or not authorization.startswith("Bearer "):
        raise BizError("未登录", code=401)
    payload = parse_token(authorization.removeprefix("Bearer ").strip())
    if not payload:
        raise BizError("登录已过期, 请重新登录", code=401)
    user = await db.get(SysUser, payload["user_id"])
    if not user or user.deleted or user.status != 1:
        raise BizError("账号不存在或已禁用", code=401)
    rows = await db.execute(
        select(SysRole.code)
        .join(SysUserRole, SysUserRole.role_id == SysRole.id)
        .where(SysUserRole.user_id == user.id)
    )
    roles = [r[0] for r in rows.all()]
    return user, roles


async def get_optional_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> tuple[SysUser | None, list[str]]:
    """可选登录: 有合法 token 返回用户, 否则返回 (None, [])。
    用于注册场景下的证照上传等"登录前后都可用"的接口"""
    if not authorization or not authorization.startswith("Bearer "):
        return None, []
    payload = parse_token(authorization.removeprefix("Bearer ").strip())
    if not payload:
        return None, []
    user = await db.get(SysUser, payload["user_id"])
    return (user, []) if user else (None, [])


def require_roles(*allowed: str):
    """RBAC 依赖: 任一角色命中即放行, ADMIN 永远放行"""

    async def checker(ctx: tuple[SysUser, list[str]] = Depends(get_current_user)) -> tuple[SysUser, list[str]]:
        user, roles = ctx
        if "ADMIN" in roles or set(roles) & set(allowed):
            return ctx
        raise BizError("无权访问", code=403)

    return checker
