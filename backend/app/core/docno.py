"""单据编号生成: 用 PostgreSQL 序列防并发重号
格式: 前缀 + 日期 + 全局递增序号, 如 SO202608130001
"""
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def next_doc_no(db: AsyncSession, prefix: str) -> str:
    seq = await db.scalar(text("SELECT nextval('doc_seq')"))
    return f"{prefix}{date.today().strftime('%Y%m%d')}{seq:04d}"
