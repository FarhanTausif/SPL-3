from __future__ import annotations

from dehalu.adapters.llm import build_provider_registry
from dehalu.core.settings import Settings
from dehalu.orchestration.routing import ProviderRouter
from dehalu.schemas import JudgeResult, JudgeVerdict


def _settings(**overrides: object) -> Settings:
    values = {
        "database_url": "sqlite://",
        "gemini_api_key": "gemini-key",
        "grok_api_key": "grok-key",
        "mistral_api_key": "mistral-key",
        "cerebras_api_key": "cerebras-key",
    }
    values.update(overrides)
    return Settings(
        **values,
    )


def test_provider_router_uses_static_role_matrix() -> None:
    router = ProviderRouter(build_provider_registry(_settings()))

    assert router.get_clarification_provider().name == "gemini"
    assert router.get_generation_provider().name == "grok"
    assert [provider.name for provider in router.get_judge_providers()] == ["gemini", "mistral", "cerebras"]
    assert [provider.name for provider in router.get_cove_providers()] == ["mistral", "gemini"]


def test_provider_router_selects_best_verifier_for_repair() -> None:
    registry = build_provider_registry(_settings())
    router = ProviderRouter(registry)
    generation = router.get_generation_provider()
    judge_results = [
        JudgeResult(verdict=JudgeVerdict.uncertain, provider="gemini", model="g", duration_ms=1.0, hallucination_score=0.55),
        JudgeResult(verdict=JudgeVerdict.fail, provider="mistral", model="m", duration_ms=1.0, hallucination_score=0.88),
        JudgeResult(verdict=JudgeVerdict.fail, provider="cerebras", model="c", duration_ms=1.0, hallucination_score=0.72),
    ]

    selection = router.choose_repair_provider(judge_results=judge_results, generation_provider=generation)

    assert selection.provider_name == "mistral"
    assert selection.fallback_used is False


def test_provider_router_reports_role_readiness() -> None:
    readiness = ProviderRouter(build_provider_registry(_settings(mistral_api_key=None))).readiness()

    assert readiness["clarification"]["ready"] is True
    assert readiness["generation"]["ready"] is True
    assert readiness["judges"]["ready"] is True
    assert readiness["cove"]["available"] == ["gemini"]
