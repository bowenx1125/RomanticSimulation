from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Love Simulator API"
    api_prefix: str = "/api"
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/love_simulator"
    )
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:3000"]
    worker_poll_seconds: int = 3
    claim_timeout_seconds: int = 300
    director_provider_mode: str = "auto"
    dashscope_api_key: str | None = None
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    director_model: str = "qwen-plus"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

