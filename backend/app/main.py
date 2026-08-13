from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.router import api_router
from app.bootstrap import bootstrap
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.response import ok
from app.database.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bootstrap()
    yield


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
