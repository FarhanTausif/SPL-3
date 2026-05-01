from __future__ import annotations

from functools import lru_cache
from typing import ClassVar, Iterable

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    KNOWN_PROVIDERS: ClassVar[frozenset[str]] = frozenset({"auto", "fake", "gemini", "grok", "mistral", "cerebras"})

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
    default_provider: str = "auto"
    default_language: str = "python"
    default_latency_budget_seconds: int = 15
    orchestration_mode: str = "direct"
    routing_policy_version: str = "v1"
    prompt_policy_version: str = "v1"
    provider_capture_full_payloads: bool = False
    provider_live_smoke_checks_enabled: bool = False
    provider_health_timeout_seconds: float = Field(default=2.0, gt=0.0, le=30.0)
    gemini_api_key: str | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_generate_model: str = "gemini-2.0-flash"
    gemini_verify_model: str = "gemini-2.0-flash"
    gemini_timeout_seconds: float = Field(default=15.0, gt=0.0)
    gemini_retry_attempts: int = Field(default=1, ge=0, le=5)
    grok_api_key: str | None = None
    grok_base_url: str = "https://api.x.ai/v1"
    grok_generate_model: str = "grok-code-fast-1"
    grok_verify_model: str = "grok-beta"
    grok_timeout_seconds: float = Field(default=15.0, gt=0.0)
    grok_retry_attempts: int = Field(default=1, ge=0, le=5)
    mistral_api_key: str | None = None
    mistral_base_url: str = "https://api.mistral.ai/v1"
    mistral_generate_model: str = "codestral-latest"
    mistral_verify_model: str = "mistral-large-latest"
    mistral_timeout_seconds: float = Field(default=15.0, gt=0.0)
    mistral_retry_attempts: int = Field(default=1, ge=0, le=5)
    cerebras_api_key: str | None = None
    cerebras_base_url: str = "https://api.cerebras.ai/v1"
    cerebras_generate_model: str = "llama3.1-70b"
    cerebras_verify_model: str = "llama3.1-70b"
    cerebras_timeout_seconds: float = Field(default=15.0, gt=0.0)
    cerebras_retry_attempts: int = Field(default=1, ge=0, le=5)
    clarification_provider_order: tuple[str, ...] = ("gemini", "mistral")
    generation_provider_order: tuple[str, ...] = ("grok", "gemini")
    judge_provider_order: tuple[str, ...] = ("gemini", "mistral", "cerebras")
    cove_provider_order: tuple[str, ...] = ("mistral", "gemini")
    repair_provider_order: tuple[str, ...] = ("gemini", "mistral", "cerebras", "grok")
    worker_poll_interval_seconds: float = Field(default=1.0, gt=0.0, le=30.0)
    worker_lease_seconds: int = Field(default=30, ge=5, le=300)
    worker_max_retries: int = Field(default=3, ge=1, le=20)
    worker_batch_size: int = Field(default=1, ge=1, le=20)
    worker_id: str = "dehalu-worker-1"

    @field_validator(
        "default_provider",
        "default_language",
        "orchestration_mode",
        "gemini_api_key",
        "gemini_base_url",
        "gemini_generate_model",
        "gemini_verify_model",
        "grok_api_key",
        "grok_base_url",
        "grok_generate_model",
        "grok_verify_model",
        "mistral_api_key",
        "mistral_base_url",
        "mistral_generate_model",
        "mistral_verify_model",
        "cerebras_api_key",
        "cerebras_base_url",
        "cerebras_generate_model",
        "cerebras_verify_model",
        "routing_policy_version",
        "prompt_policy_version",
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

    @field_validator("default_provider")
    @classmethod
    def validate_default_provider(cls, value: str | None) -> str:
        provider = (value or "").strip().lower()
        if provider not in cls.KNOWN_PROVIDERS:
            options = ", ".join(sorted(cls.KNOWN_PROVIDERS))
            raise ValueError(f"default_provider must be one of: {options}")
        return provider

    @field_validator(
        "clarification_provider_order",
        "generation_provider_order",
        "judge_provider_order",
        "cove_provider_order",
        "repair_provider_order",
        mode="before",
    )
    @classmethod
    def normalize_provider_orders(cls, value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            return tuple(token.strip().lower() for token in value.split(",") if token.strip())
        if isinstance(value, (list, tuple)):
            return tuple(str(token).strip().lower() for token in value if str(token).strip())
        raise TypeError("provider order settings must be a comma-separated string or sequence")

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def grok_enabled(self) -> bool:
        return bool(self.grok_api_key)

    @property
    def mistral_enabled(self) -> bool:
        return bool(self.mistral_api_key)

    @property
    def cerebras_enabled(self) -> bool:
        return bool(self.cerebras_api_key)

    def resolve_default_provider(self, available_provider_names: Iterable[str]) -> str:
        available = set(available_provider_names)
        if self.default_provider == "auto":
            for name in self.generation_provider_order:
                if name != "fake" and name in available:
                    return name
            if "fake" in available:
                return "fake"
            if available:
                return next(iter(available))
            return "fake"

        if self.default_provider in available:
            return self.default_provider
        if "fake" in available:
            return "fake"
        return self.default_provider


@lru_cache
def get_settings() -> Settings:
    return Settings()
