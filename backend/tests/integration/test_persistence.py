from __future__ import annotations

from sqlalchemy.orm import Session

from dehalu.adapters.llm import build_provider_registry
from dehalu.core.settings import Settings
from dehalu.orchestration import RunOrchestrator
from dehalu.schemas import RunRequest
from dehalu.state.repository import RunRepository


def test_run_and_evidence_are_persisted(db_session: Session) -> None:
    orchestrator = RunOrchestrator(
        Settings(database_url="sqlite://"),
        build_provider_registry(),
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
        "policy": 1,
    }
    assert len(evidence) == 4
