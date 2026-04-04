from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # 應用程式設定
    APP_NAME: str = "app-login-service"
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"

    # 資料庫
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 限流
    RATE_LIMIT_PER_MINUTE: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
