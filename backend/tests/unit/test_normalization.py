from __future__ import annotations

from dehalu.core.settings import Settings
from dehalu.orchestration import normalize_request
from dehalu.schemas import RiskLevel, RunRequest


def test_normalize_request_uses_defaults() -> None:
    settings = Settings(database_url="sqlite://")
    normalized = normalize_request(RunRequest(prompt="Write Python code"), settings)

    assert normalized.language == "python"
    assert normalized.provider == "fake"
    assert normalized.risk_level == RiskLevel.medium
    assert normalized.latency_budget_seconds == 15


def test_normalize_request_honors_explicit_values() -> None:
    settings = Settings(database_url="sqlite://")
    normalized = normalize_request(
        RunRequest(
            prompt="Build this",
            language_hint="Python",
            risk_level=RiskLevel.high,
            latency_budget_seconds=5,
            provider="fake",
        ),
        settings,
    )

    assert normalized.language == "python"
    assert normalized.provider == "fake"
    assert normalized.risk_level == RiskLevel.high
    assert normalized.latency_budget_seconds == 5

