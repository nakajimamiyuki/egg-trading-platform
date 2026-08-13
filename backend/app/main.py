from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from sqlalchemy import text

from app.api.router import api_router
from app.bootstrap import bootstrap
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.response import ok
from app.database.session import async_session, engine


async def daily_turnover_check() -> None:
    """每日周转预警 (F7.1)"""
    from app.modules.risk.service import check_turnover_warnings
    async with async_session() as db:
        count = await check_turnover_warnings(db)
        await db.commit()
        if count:
            import logging
            logging.getLogger(__name__).info("周转预警: %s 条", count)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bootstrap()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(daily_turnover_check, "cron", hour=9, minute=0)  # 每日9点预警检查
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title=settings.APP_NAME, version="1.0", lifespan=lifespan)

register_exception_handlers(app)
app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get(f"{settings.API_PREFIX}/health/db")
async def health_db():
    """验证数据库连通性 + 初始化脚本是否执行"""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
        result = await conn.execute(text("SELECT count(*) FROM sys_role"))
        role_count = result.scalar()
    return ok({"database": "ok", "seed_roles": role_count})
