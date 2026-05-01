from __future__ import annotations

from sqlalchemy.orm import Session

from dehalu.adapters.llm.runtime import ProviderExecutionError
from dehalu.core.settings import Settings
from dehalu.schemas import AgentRole, NormalizedRequest, ProviderFailureKind, ProviderInvocationRecord, RiskLevel, RunMode
from dehalu.state.repository import RunRepository
from dehalu.worker import RunWorker


def _queued_run(db_session: Session) -> str:
    repository = RunRepository(db_session)
    created = repository.create_pending_run(
        normalized_request=NormalizedRequest(
            prompt="Write Python code.",
            language="python",
            risk_level=RiskLevel.medium,
            latency_budget_seconds=15,
            provider="fake",
            run_mode=RunMode.advanced,
        ),
        run_mode=RunMode.advanced,
    )
    return created.run_id


def test_worker_records_runtime_failures_with_operator_hint(db_session: Session) -> None:
    class FailingOrchestrator:
        def process_claimed_run(self, _run_record, _session) -> None:
            raise RuntimeError("boom")

    settings = Settings(database_url="sqlite://", default_provider="fake", gemini_api_key=None)
    run_id = _queued_run(db_session)
    worker = RunWorker(settings=settings, orchestrator=FailingOrchestrator(), session_factory=lambda: db_session)

    assert worker.run_once() is True
    detail = RunRepository(db_session).get_run_detail(run_id)
    events = RunRepository(db_session).get_run_events(run_id)

    assert detail.status.value == "failed"
    assert detail.stage_summary[-1].stage == "worker_failure"
    assert "operator_hint" in detail.stage_summary[-1].details
    assert any(event.event_type == "worker_runtime_failure" for event in events)


def test_worker_records_provider_failures_with_actionable_context(db_session: Session) -> None:
    class ProviderFailingOrchestrator:
        def process_claimed_run(self, _run_record, _session) -> None:
            record = ProviderInvocationRecord(
                provider_name="gemini",
                model="gemini-2.0-flash",
                stage="generation",
                role=AgentRole.coder,
                success=False,
                latency_ms=12.0,
                retry_count=1,
                failure_kind=ProviderFailureKind.auth,
            )
            raise ProviderExecutionError("unauthorized", record=record)

    settings = Settings(database_url="sqlite://", default_provider="fake", gemini_api_key=None)
    run_id = _queued_run(db_session)
    worker = RunWorker(settings=settings, orchestrator=ProviderFailingOrchestrator(), session_factory=lambda: db_session)

    assert worker.run_once() is True
    detail = RunRepository(db_session).get_run_detail(run_id)
    events = RunRepository(db_session).get_run_events(run_id)

    assert detail.status.value == "failed"
    assert detail.stage_summary[-1].stage == "provider_failure"
    assert detail.stage_summary[-1].details["provider"] == "gemini"
    assert detail.stage_summary[-1].details["failure_kind"] == "auth"
    assert any(event.event_type == "worker_provider_failure" for event in events)
