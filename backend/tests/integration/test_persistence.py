from __future__ import annotations

from sqlalchemy.orm import Session

from dehalu.adapters.llm import build_provider_registry
from dehalu.core.settings import Settings
from dehalu.orchestration import RunOrchestrator
from dehalu.schemas import RunRequest
from dehalu.state.repository import RunRepository
from dehalu.worker import RunWorker


def test_run_and_evidence_are_persisted(db_session: Session) -> None:
    settings = Settings(database_url="sqlite://", default_provider="fake", gemini_api_key=None)
    orchestrator = RunOrchestrator(
        settings,
        build_provider_registry(settings),
    )

    response = orchestrator.run(RunRequest(prompt="Write Python code."), db_session)
    repository = RunRepository(db_session)

    detail = repository.get_run_detail(response.run_id)
    evidence = repository.get_run_evidence(response.run_id)

    assert detail.run_id == response.run_id
    assert detail.evidence_summary == {
        "claim_extraction": 1,
        "static_analysis": 1,
        "sandbox": 1,
        "judge": 1,
        "cove": 1,
        "policy": 1,
    }
    assert len(evidence) == 6
    assert all(item.payload["orchestration_mode"] == "direct" for item in evidence if item.kind != "repair")


def test_run_uses_safe_fallback_when_default_provider_is_unavailable(db_session: Session) -> None:
    settings = Settings(database_url="sqlite://", default_provider="gemini", gemini_api_key=None)
    orchestrator = RunOrchestrator(
        settings,
        build_provider_registry(settings),
    )

    response = orchestrator.run(RunRequest(prompt="Write Python code."), db_session)

    assert response.coder_output.provider == "fake"


def test_repair_run_persists_both_attempts_and_repair_evidence(db_session: Session) -> None:
    settings = Settings(database_url="sqlite://", default_provider="fake", gemini_api_key=None)
    orchestrator = RunOrchestrator(
        settings,
        build_provider_registry(settings),
    )

    response = orchestrator.run(
        RunRequest(prompt="Write dangerous Python code.", provider="fake"),
        db_session,
    )
    repository = RunRepository(db_session)

    detail = repository.get_run_detail(response.run_id)
    evidence = repository.get_run_evidence(response.run_id)

    assert response.repair_result.outcome.value == "succeeded"
    assert detail.evidence_summary == {
        "claim_extraction": 2,
        "static_analysis": 2,
        "sandbox": 2,
        "judge": 2,
        "cove": 2,
        "repair": 1,
        "policy": 2,
    }
    assert len(evidence) == 13


def test_crewai_mode_preserves_run_detail_and_evidence_summary(db_session: Session) -> None:
    settings = Settings(
        database_url="sqlite://",
        default_provider="fake",
        gemini_api_key=None,
        orchestration_mode="crewai",
    )
    orchestrator = RunOrchestrator(
        settings,
        build_provider_registry(settings),
    )

    response = orchestrator.run(
        RunRequest(prompt="Write dangerous Python code.", provider="fake"),
        db_session,
    )
    repository = RunRepository(db_session)

    detail = repository.get_run_detail(response.run_id)
    evidence = repository.get_run_evidence(response.run_id)

    assert response.repair_result.outcome.value == "succeeded"
    assert detail.policy_decision.state.value == "accept"
    assert detail.evidence_summary == {
        "claim_extraction": 2,
        "static_analysis": 2,
        "sandbox": 2,
        "judge": 2,
        "cove": 2,
        "repair": 1,
        "policy": 2,
        "orchestration": 1,
    }
    assert len(evidence) == 14
    orchestration = next(item for item in evidence if item.kind == "orchestration")
    assert orchestration.payload["orchestration_mode"] == "crewai"
    assert orchestration.payload["entry_count"] > 0


def test_advanced_run_persists_events_and_panel_evidence(db_session: Session) -> None:
    settings = Settings(database_url="sqlite://", default_provider="fake", gemini_api_key=None)
    orchestrator = RunOrchestrator(settings, build_provider_registry(settings))

    response = orchestrator.run(
        RunRequest(
            prompt="Write Python code that computes a square root.",
            provider="fake",
            run_mode="advanced",
            acceptance_criteria=["Use math.sqrt."],
        ),
        db_session,
    )
    assert response.status.value == "queued"

    worker = RunWorker(
        settings=settings,
        orchestrator=orchestrator,
        session_factory=lambda: db_session,
    )
    assert worker.run_once() is True

    repository = RunRepository(db_session)
    detail = repository.get_run_detail(response.run_id)
    evidence = repository.get_run_evidence(response.run_id)
    events = repository.get_run_events(response.run_id)

    assert detail.status.value == "completed"
    assert detail.fused_metrics is not None
    assert len(events) >= 4
    assert {"tool", "panel", "fusion", "routing", "clarification", "provider_invocation"}.issubset(
        {item.kind for item in evidence}
    )
    routing = next(item for item in evidence if item.kind == "routing")
    role_routes = routing.payload["role_routes"]
    assert {"clarification", "generation", "judge", "cove", "repair"} == set(role_routes)
    assert "selected_via" in role_routes["repair"]
    assert isinstance(role_routes["judge"]["attempts"], list)
    assert isinstance(role_routes["cove"]["attempts"], list)
