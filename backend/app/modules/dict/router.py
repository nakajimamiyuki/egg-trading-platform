from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles
from app.core.response import BizError, ok
from app.database.session import get_db
from app.models import SysConfig, SysDictItem, SysDictType

router = APIRouter()


@router.get("/dict/{type_code}")
async def dict_items(type_code: str, db: AsyncSession = Depends(get_db)):
    """字典下拉数据 (公开, 注册等场景需要)"""
    rows = await db.execute(
        select(SysDictItem)
        .join(SysDictType, SysDictType.id == SysDictItem.type_id)
        .where(SysDictType.code == type_code)
        .order_by(SysDictItem.sort)
    )
    return ok([{"code": i.code, "name": i.name} for i in rows.scalars().all()])


@router.get("/config")
async def list_config(ctx=Depends(require_roles("ADMIN", "BUSINESS")), db: AsyncSession = Depends(get_db)):
    rows = await db.scalars(select(SysConfig).order_by(SysConfig.id))
    return ok([{"key": c.config_key, "value": c.config_value, "remark": c.remark} for c in rows.all()])


@router.put("/config/{key}")
async def update_config(key: str, body: dict, ctx=Depends(require_roles("ADMIN")), db: AsyncSession = Depends(get_db)):
    """修改业务参数 (定金比例/垫资比例/周转天数/折价/分利等), 仅管理员"""
    config = await db.scalar(select(SysConfig).where(SysConfig.config_key == key))
    if not config:
        raise BizError("配置项不存在", code=404)
    value = body.get("value")
    if value is None:
        raise BizError("缺少 value")
    config.config_value = str(value)
    await db.commit()
    return ok(message="已更新")
