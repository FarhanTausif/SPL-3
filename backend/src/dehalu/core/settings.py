from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
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
    orchestration_mode: str = "direct"
    gemini_api_key: str | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_generate_model: str = "gemini-2.0-flash"
    gemini_verify_model: str = "gemini-2.0-flash"
    gemini_timeout_seconds: float = Field(default=15.0, gt=0.0)

    @field_validator(
        "default_provider",
        "default_language",
        "orchestration_mode",
        "gemini_api_key",
        "gemini_base_url",
        "gemini_generate_model",
        "gemini_verify_model",
    )
    @classmethod
    def normalize_tokens(cls, value: str | None) -> str | None:
        if value is None:
            return None
        token = value.strip()
        return token or None

    @field_validator("orchestration_mode")
    @classmethod
    def validate_orchestration_mode(cls, value: str) -> str:
        if value not in {"direct", "crewai"}:
            raise ValueError("orchestration_mode must be 'direct' or 'crewai'")
        return value

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
