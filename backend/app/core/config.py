from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """全局配置, 全部支持环境变量覆盖 (见 docker-compose.yml)"""

    APP_ENV: str = "dev"
    APP_NAME: str = "Egg Platform API"
    API_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+asyncpg://egg:egg_dev_2026@localhost:5432/egg_platform"
    REDIS_URL: str = "redis://localhost:6379/0"
    RABBITMQ_URL: str = "amqp://egg:egg_dev_2026@localhost:5672/"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "egg"
    MINIO_SECRET_KEY: str = "egg_dev_2026"
    MINIO_BUCKET: str = "egg-files"
    MINIO_SECURE: bool = False

    JWT_SECRET: str = "dev-only-secret-change-in-prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 720

    # 初始管理员(后端首次启动时自动创建)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
