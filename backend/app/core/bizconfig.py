"""读取 sys_config 业务参数(后台可配置)"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SysConfig


async def get_config(db: AsyncSession, key: str, default: str = "") -> str:
    row = await db.scalar(select(SysConfig).where(SysConfig.config_key == key))
    return row.config_value if row else default


async def get_config_int(db: AsyncSession, key: str, default: int = 0) -> int:
    return int(await get_config(db, key, str(default)))


async def get_config_decimal(db: AsyncSession, key: str, default: str = "0"):
    from decimal import Decimal
    return Decimal(await get_config(db, key, default))
