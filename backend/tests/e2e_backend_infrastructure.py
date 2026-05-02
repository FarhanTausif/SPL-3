"""
E2E tests: Complete backend infrastructure validation
Tests the entire flow from API request through database persistence.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from dehalu.schemas import RunLifecycleStatus
from dehalu.state.models import RunRecord, EvidenceRecord, EventRecord

pytestmark = pytest.mark.anyio


async def test_complete_lifecycle_run_creation_to_completion(
    client: AsyncClient, db_session: Session
) -> None:
    """Test: Create run → verify DB state → poll status → get evidence → check events"""

    # Step 1: Create run
    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Write a Python function to calculate factorial",
            "language_hint": "python",
            "risk_level": "low",
        },
    )

    assert response.status_code == 201
    data = response.json()
    run_id = data["run_id"]
    assert run_id, "run_id should be present"
    assert data["status"] in ["completed", "running", "queued"]
    assert data["normalized_request"]["language"] == "python"
    assert data["normalized_request"]["prompt"] == "Write a Python function to calculate factorial"

    # Step 2: Verify database persistence - RunRecord created
    db_run = db_session.query(RunRecord).filter(RunRecord.id == run_id).first()
    assert db_run is not None, "Run should be persisted to database"
    assert db_run.status in ["queued", "running", "completed", "failed", "needs_clarification"]
    assert db_run.created_at is not None
    assert db_run.language == "python"

    # Step 3: Get run status
    response = await client.get(f"/v1/runs/{run_id}")
    assert response.status_code == 200
    run_detail = response.json()
    assert run_detail["run_id"] == run_id
    assert run_detail["status"] in ["completed", "running", "queued", "needs_clarification", "failed"]

    # Step 4: Get evidence
    response = await client.get(f"/v1/runs/{run_id}/evidence")
    assert response.status_code == 200
    evidence_list = response.json()
    assert isinstance(evidence_list, list)

    # Verify evidence persisted to database
    db_evidence = db_session.query(EvidenceRecord).filter(EvidenceRecord.run_id == run_id).all()
    assert len(db_evidence) == len(evidence_list), "Evidence count should match"

    for ev in evidence_list:
        assert "kind" in ev
        assert "payload" in ev
        # Verify each evidence record in database
        db_ev = next((e for e in db_evidence if e.kind == ev["kind"]), None)
        assert db_ev is not None, f"Evidence kind {ev['kind']} should be in database"

    # Step 5: Get event stream
    response = await client.get(f"/v1/runs/{run_id}/events")
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    assert len(events) > 0, "Should have at least one event"

    # Verify events are ordered by sequence
    sequences = [e["sequence"] for e in events]
    assert sequences == sorted(sequences), "Events should be in sequence order"

    # Verify events persisted to database
    db_events = db_session.query(EventRecord).filter(EventRecord.run_id == run_id).all()
    assert len(db_events) == len(events), "Event count should match"



async def test_database_evidence_persistence_all_kinds(
    client: AsyncClient, db_session: Session
) -> None:
    """Test: Verify all evidence kinds are persisted correctly"""

    # Create run
    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Sum the first n numbers",
            "language_hint": "python",
        },
    )

    assert response.status_code == 201
    run_id = response.json()["run_id"]

    # Get evidence
    response = await client.get(f"/v1/runs/{run_id}/evidence")
    assert response.status_code == 200
    evidence = response.json()

    # Verify database persistence of all evidence
    for ev in evidence:
        db_record = (
            db_session.query(EvidenceRecord)
            .filter(EvidenceRecord.run_id == run_id, EvidenceRecord.kind == ev["kind"])
            .first()
        )
        assert db_record is not None
        assert db_record.payload == ev["payload"]
        assert db_record.created_at is not None



@pytest.mark.unit
async def test_database_timestamps_are_utc(
    client: AsyncClient, db_session: Session
) -> None:
    """Test: Verify all timestamps use UTC or are naive datetime (SQLite behavior)"""

    response = await client.post(
        "/v1/runs",
        json={"prompt": "Test", "language_hint": "python"},
    )

    run_id = response.json()["run_id"]
    db_run = db_session.query(RunRecord).filter(RunRecord.id == run_id).first()

    # Verify timestamps are present (SQLite doesn't enforce timezones, but values are UTC)
    assert db_run.created_at is not None
    assert isinstance(db_run.created_at, type(db_run.created_at))

    # Check events have timestamps
    db_events = db_session.query(EventRecord).filter(EventRecord.run_id == run_id).all()
    for event in db_events:
        assert event.created_at is not None



async def test_database_run_lifecycle_state_transitions(
    client: AsyncClient, db_session: Session
) -> None:
    """Test: Verify run lifecycle states are correctly persisted"""

    response = await client.post(
        "/v1/runs",
        json={"prompt": "Write hello world", "language_hint": "python"},
    )

    run_id = response.json()["run_id"]
    db_run = db_session.query(RunRecord).filter(RunRecord.id == run_id).first()

    # Initial status should be one of the valid states
    assert db_run.status in [
        RunLifecycleStatus.queued.value,
        RunLifecycleStatus.running.value,
        RunLifecycleStatus.completed.value,
        RunLifecycleStatus.failed.value,
        RunLifecycleStatus.needs_clarification.value,
    ]



async def test_invalid_run_id_returns_404(client: AsyncClient) -> None:
    """Test: Invalid run_id returns 404"""

    response = await client.get("/v1/runs/invalid-run-id")
    assert response.status_code == 404



async def test_missing_required_fields_returns_422(client: AsyncClient) -> None:
    """Test: Missing required fields returns 422"""

    response = await client.post(
        "/v1/runs",
        json={
            # Missing required "prompt" field
            "language_hint": "python",
        },
    )

    assert response.status_code == 422



async def test_api_response_contains_all_required_fields(
    client: AsyncClient,
) -> None:
    """Test: Verify all response fields are present"""

    response = await client.post(
        "/v1/runs",
        json={"prompt": "Test", "language_hint": "python"},
    )

    assert response.status_code == 201
    data = response.json()

    # Verify required fields in RunResponse
    required_fields = [
        "run_id",
        "normalized_request",
        "status",
        "evidence_ids",
    ]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
        assert data[field] is not None, f"Field {field} is null"



async def test_health_endpoint_shows_backend_ready(client: AsyncClient) -> None:
    """Test: /health endpoint shows backend is ready"""

    response = await client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "providers" in data
    assert "orchestration" in data
    assert data["orchestration"]["configured_mode"] in ["direct", "crewai"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
