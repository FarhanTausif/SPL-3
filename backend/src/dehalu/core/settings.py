from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DEHALU_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "DeHalu Backend"
    app_version: str = "0.1.0"
    environment: str = "development"
    database_url: str = Field(
        default="postgresql+psycopg://dehalu:dehalu@localhost:5432/dehalu",
        description="Runtime database URL. Tests override this with SQLite.",
    )
    default_provider: str = "fake"
    default_language: str = "python"
    default_latency_budget_seconds: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()

