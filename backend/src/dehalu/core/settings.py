from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _load_dotenv() -> None:
    root = Path(__file__).resolve().parents[4]
    for path in [root / "backend" / ".env", root / ".env"]:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            clean = line.strip()
            if not clean or clean.startswith("#") or "=" not in clean:
                continue
            key, value = clean.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = "DeHalu"
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://dehalu:dehalu@localhost:5433/dehalu",
    )
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "codellama:7b")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    mistral_api_key: str | None = os.getenv("MISTRAL_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    mistral_model: str = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
    quality_safety_provider: str = os.getenv("QUALITY_SAFETY_PROVIDER", "gemini")
    allow_fake_llm: bool = os.getenv("DEHALU_ALLOW_FAKE_LLM", "false").lower() == "true"
    default_max_retry: int = int(os.getenv("DEHALU_MAX_RETRY", "3"))
    request_timeout_seconds: float = float(os.getenv("DEHALU_REQUEST_TIMEOUT_SECONDS", "120"))
    package_lookups: bool = os.getenv("DEHALU_PACKAGE_LOOKUPS", "false").lower() == "true"
    worker_concurrency: int = int(os.getenv("DEHALU_WORKER_CONCURRENCY", "2"))
    worker_lease_seconds: int = int(os.getenv("DEHALU_WORKER_LEASE_SECONDS", "120"))
    provider_retries: int = int(os.getenv("DEHALU_PROVIDER_RETRIES", "2"))
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("DEHALU_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
        if origin.strip()
    )
    cors_origin_regex: str = os.getenv(
        "DEHALU_CORS_ORIGIN_REGEX",
        r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?",
    )

    def __post_init__(self) -> None:
        if self.quality_safety_provider not in {"gemini", "mistral"}:
            raise ValueError("QUALITY_SAFETY_PROVIDER must be gemini or mistral")


settings = Settings()
