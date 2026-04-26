from __future__ import annotations

from dehalu.adapters.language import build_language_registry
from dehalu.adapters.llm import build_provider_registry
from dehalu.agents.compat import HAS_CREWAI
from dehalu.agents.runner import CrewAIRunner
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
    assert direct_result.final_attempt.coder_output.code == crewai_result.final_attempt.coder_output.code
    assert len(crewai_result.orchestration_trace) > 0


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
    assert any(entry.task_name == "repair_output" and entry.status == "completed" for entry in result.orchestration_trace)


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
    assert any(entry.task_name == "repair_output" and entry.status == "skipped" for entry in crewai_result.orchestration_trace)


def test_crewai_execution_engine_rejects_after_failed_high_risk_repair() -> None:
    settings = Settings(database_url="sqlite://", default_provider="fake", gemini_api_key=None)
    normalized = normalize_request(
        RunRequest(
            prompt="Write dangerous Python code with repair failure.",
            provider="fake",
            risk_level=RiskLevel.high,
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
    assert result.final_attempt.policy_decision.state == PolicyDecisionState.reject
    assert result.repair_result.outcome.value == "failed"


def test_crewai_execution_engine_records_stage_order_and_attempt_context() -> None:
    settings = Settings(database_url="sqlite://", default_provider="fake", gemini_api_key=None)
    normalized = normalize_request(
        RunRequest(prompt="Write dangerous Python code.", provider="fake"),
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
    completed_tasks = [
        entry.task_name
        for entry in result.orchestration_trace
        if entry.status == "completed"
    ]

    assert completed_tasks[:7] == [
        "generate_output",
        "extract_claims",
        "static_analysis",
        "sandbox_verify",
        "judge_output",
        "cove_output",
        "policy_decide",
    ]
    assert "repair_output" in completed_tasks
    assert any(entry.attempt_stage == "repair" for entry in result.orchestration_trace if entry.status == "completed")


def test_crewai_runner_reports_availability_state() -> None:
    runner = CrewAIRunner()

    assert runner.available is HAS_CREWAI
