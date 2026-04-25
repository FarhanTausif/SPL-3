from __future__ import annotations

from dehalu.adapters.language import build_language_registry
from dehalu.adapters.llm import build_provider_registry
from dehalu.core.settings import Settings
from dehalu.orchestration import RunOrchestrator, normalize_request
from dehalu.orchestration.execution import (
    CrewAIExecutionEngine,
    DirectExecutionEngine,
    build_execution_engine,
)
from dehalu.schemas import PolicyDecisionState, RiskLevel, RunRequest
from dehalu.verification.claims import ClaimExtractor
from dehalu.verification.policy import PolicyEngine
from dehalu.verification.sandbox import SandboxVerifier
from dehalu.verification.static_analysis import StaticAnalyzer


def _components() -> tuple[ClaimExtractor, StaticAnalyzer, SandboxVerifier, PolicyEngine]:
    language_registry = build_language_registry()
    return (
        ClaimExtractor(language_registry),
        StaticAnalyzer(language_registry),
        SandboxVerifier(),
        PolicyEngine(),
    )


def test_orchestration_mode_defaults_to_direct() -> None:
    settings = Settings(database_url="sqlite://", default_provider="fake", gemini_api_key=None)
    orchestrator = RunOrchestrator(settings, build_provider_registry(settings))

    assert isinstance(orchestrator.execution_engine, DirectExecutionEngine)


def test_orchestration_mode_can_switch_to_crewai() -> None:
    settings = Settings(
        database_url="sqlite://",
        default_provider="fake",
        gemini_api_key=None,
        orchestration_mode="crewai",
    )
    orchestrator = RunOrchestrator(settings, build_provider_registry(settings))

    assert isinstance(orchestrator.execution_engine, CrewAIExecutionEngine)


def test_build_execution_engine_selects_expected_implementation() -> None:
    claim_extractor, static_analyzer, sandbox_verifier, policy_engine = _components()

    direct = build_execution_engine(
        "direct",
        claim_extractor,
        static_analyzer,
        sandbox_verifier,
        policy_engine,
    )
    crewai = build_execution_engine(
        "crewai",
        claim_extractor,
        static_analyzer,
        sandbox_verifier,
        policy_engine,
    )

    assert isinstance(direct, DirectExecutionEngine)
    assert isinstance(crewai, CrewAIExecutionEngine)


def test_crewai_execution_engine_matches_direct_for_clean_run() -> None:
    settings = Settings(database_url="sqlite://", default_provider="fake", gemini_api_key=None)
    normalized = normalize_request(
        RunRequest(prompt="Write Python code.", provider="fake"),
        settings,
    )
    provider = build_provider_registry(settings).get("fake")
    claim_extractor, static_analyzer, sandbox_verifier, policy_engine = _components()
    direct = DirectExecutionEngine(
        claim_extractor,
        static_analyzer,
        sandbox_verifier,
        policy_engine,
    )
    crewai = CrewAIExecutionEngine(
        claim_extractor,
        static_analyzer,
        sandbox_verifier,
        policy_engine,
    )

    direct_result = direct.execute(normalized, provider)
    crewai_result = crewai.execute(normalized, provider)

    assert direct_result.final_attempt.policy_decision.state == PolicyDecisionState.accept
    assert crewai_result.final_attempt.policy_decision.state == PolicyDecisionState.accept
    assert direct_result.repair_result.outcome == crewai_result.repair_result.outcome


def test_crewai_execution_engine_runs_single_repair_and_retry() -> None:
    settings = Settings(database_url="sqlite://", default_provider="fake", gemini_api_key=None)
    normalized = normalize_request(
        RunRequest(
            prompt="Write dangerous Python code.",
            provider="fake",
            risk_level=RiskLevel.medium,
        ),
        settings,
    )
    provider = build_provider_registry(settings).get("fake")
    claim_extractor, static_analyzer, sandbox_verifier, policy_engine = _components()
    crewai = CrewAIExecutionEngine(
        claim_extractor,
        static_analyzer,
        sandbox_verifier,
        policy_engine,
    )

    result = crewai.execute(normalized, provider)

    assert result.initial_attempt.policy_decision.state == PolicyDecisionState.repair_and_retry
    assert result.final_attempt.policy_decision.state == PolicyDecisionState.accept
    assert result.repair_result.outcome.value == "succeeded"
    assert result.repair_result.final_attempt_number == 2


def test_direct_and_crewai_preserve_deterministic_precedence() -> None:
    settings = Settings(database_url="sqlite://", default_provider="fake", gemini_api_key=None)
    normalized = normalize_request(
        RunRequest(
            prompt="Write Python syntax error code.",
            provider="fake",
            risk_level=RiskLevel.medium,
        ),
        settings,
    )
    provider = build_provider_registry(settings).get("fake")
    claim_extractor, static_analyzer, sandbox_verifier, policy_engine = _components()
    direct = DirectExecutionEngine(
        claim_extractor,
        static_analyzer,
        sandbox_verifier,
        policy_engine,
    )
    crewai = CrewAIExecutionEngine(
        claim_extractor,
        static_analyzer,
        sandbox_verifier,
        policy_engine,
    )

    direct_result = direct.execute(normalized, provider)
    crewai_result = crewai.execute(normalized, provider)

    assert direct_result.final_attempt.policy_decision.state == PolicyDecisionState.reject
    assert crewai_result.final_attempt.policy_decision.state == PolicyDecisionState.reject
    assert direct_result.repair_result.outcome.value == "skipped"
    assert crewai_result.repair_result.outcome.value == "skipped"
