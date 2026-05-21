from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/pentashield"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # External APIs
    shodan_api_key: str = ""
    anthropic_api_key: str = ""
    nvd_api_key: str = ""

    # App
    environment: str = "development"
    app_name: str = "PentaShield"
    app_version: str = "0.1.0"
    max_concurrent_scans_per_user: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
