from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from dehalu.schemas import NormalizedRequest, RiskLevel, RunMode
from dehalu.state.repository import RunRepository


def _request() -> NormalizedRequest:
    return NormalizedRequest(
        prompt="Write Python code.",
        language="python",
        risk_level=RiskLevel.medium,
        latency_budget_seconds=15,
        provider="fake",
        run_mode=RunMode.advanced,
    )


def test_repository_claims_queued_advanced_run(db_session: Session) -> None:
    repository = RunRepository(db_session)
    created = repository.create_pending_run(normalized_request=_request(), run_mode=RunMode.advanced)

    claimed = repository.claim_next_advanced_run(worker_id="worker-a", lease_seconds=30)

    assert claimed is not None
    assert claimed.id == created.run_id
    assert claimed.claimed_by == "worker-a"
    assert claimed.status == "running"
    assert claimed.attempt_count == 1


def test_repository_skips_currently_leased_run(db_session: Session) -> None:
    repository = RunRepository(db_session)
    repository.create_pending_run(normalized_request=_request(), run_mode=RunMode.advanced)
    claimed = repository.claim_next_advanced_run(worker_id="worker-a", lease_seconds=30)

    second = repository.claim_next_advanced_run(worker_id="worker-b", lease_seconds=30)

    assert claimed is not None
    assert second is None


def test_repository_reclaims_stale_lease(db_session: Session) -> None:
    repository = RunRepository(db_session)
    created = repository.create_pending_run(normalized_request=_request(), run_mode=RunMode.advanced)
    claimed = repository.claim_next_advanced_run(worker_id="worker-a", lease_seconds=30)
    assert claimed is not None

    run_record = repository._get_run(created.run_id)
    run_record.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    reclaimed = repository.claim_next_advanced_run(worker_id="worker-b", lease_seconds=30)

    assert reclaimed is not None
    assert reclaimed.claimed_by == "worker-b"
    assert reclaimed.attempt_count == 2
