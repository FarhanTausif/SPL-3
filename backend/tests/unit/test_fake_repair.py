from __future__ import annotations

from dehalu.adapters.llm import build_provider_registry
from dehalu.adapters.llm.fake import FakeLLMProvider
from dehalu.core.settings import Settings
from dehalu.orchestration import RunOrchestrator
from dehalu.schemas import (
    CoVeResult,
    CoVeVerdict,
    JudgeResult,
    JudgeVerdict,
    NormalizedRequest,
    PolicyDecision,
    PolicyDecisionState,
    RiskLevel,
    RunRequest,
)
from dehalu.state.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def _request(prompt: str = "Write dangerous Python code.", risk_level: RiskLevel = RiskLevel.medium) -> NormalizedRequest:
    return NormalizedRequest(
        prompt=prompt,
        language="python",
        risk_level=risk_level,
        latency_budget_seconds=15,
        provider="fake",
    )


def _policy_decision() -> PolicyDecision:
    return PolicyDecision(
        state=PolicyDecisionState.repair_and_retry,
        reasons=["Repair the risky output."],
        hard_fail=False,
        score=0.65,
        metrics={"repair_trigger": "judge_uncertain"},
    )


def _judge_result(verdict: JudgeVerdict = JudgeVerdict.uncertain) -> JudgeResult:
    return JudgeResult(
        verdict=verdict,
        provider="fake",
        model="fake",
        duration_ms=1.0,
        hallucination_score=0.55,
    )


def _cove_result(verdict: CoVeVerdict = CoVeVerdict.uncertain) -> CoVeResult:
    return CoVeResult(
        verdict=verdict,
        provider="fake",
        model="fake",
        duration_ms=1.0,
        hallucination_score=0.55,
    )


def _db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return testing_session()


def test_fake_repair_returns_clean_python_output_for_known_bad_code() -> None:
    provider = FakeLLMProvider()
    request = _request()
    output = provider.generate(request)

    repaired = provider.repair(request, output, _policy_decision(), _judge_result(), _cove_result())

    assert "math.sqrt" in repaired.code
    assert any("repair" in note.lower() for note in repaired.execution_notes)


def test_fake_repair_failure_path_returns_failed_repair_result_and_final_reject() -> None:
    settings = Settings(database_url="sqlite://", default_provider="fake", gemini_api_key=None)
    orchestrator = RunOrchestrator(settings, build_provider_registry(settings))
    session = _db_session()
    try:
        response = orchestrator.run(
            RunRequest(
                prompt="Write dangerous Python code with repair failure.",
                provider="fake",
                risk_level=RiskLevel.high,
            ),
            session,
        )
    finally:
        session.close()

    assert response.repair_result.outcome.value == "failed"
    assert response.policy_decision.state == PolicyDecisionState.reject
    assert response.repair_result.final_attempt_number == 2
