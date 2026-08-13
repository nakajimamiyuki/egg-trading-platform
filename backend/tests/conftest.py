"""集成测试基础设施: 独立测试库 egg_platform_test, 不影响开发数据
运行方式(容器内): docker exec egg-backend python -m pytest
"""
import os

# 必须在任何 app 模块导入前指向测试库
os.environ["DATABASE_URL"] = "postgresql+asyncpg://egg:egg_dev_2026@postgres:5432/egg_platform_test"

import asyncpg  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

TEST_DB = "egg_platform_test"
ADMIN_DSN = "postgresql://egg:egg_dev_2026@postgres:5432/postgres"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_db():
    """建测试库 -> 建表(用模型元数据) -> 跑 bootstrap 种子"""
    conn = await asyncpg.connect(ADMIN_DSN)
    await conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
    await conn.execute(f"CREATE DATABASE {TEST_DB}")
    await conn.close()

    from app.database.session import engine
    from app.models import Base
    async with engine.begin() as conn2:
        await conn2.run_sync(Base.metadata.create_all)

    from app.bootstrap import bootstrap
    await bootstrap()
    yield

    await engine.dispose()
    conn = await asyncpg.connect(ADMIN_DSN)
    await conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
    await conn.close()


@pytest_asyncio.fixture
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
