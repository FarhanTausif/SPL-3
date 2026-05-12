from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from dehalu.core.app import create_app
from dehalu.state.database import get_session


def _build_sync_client(db_session: Session) -> TestClient:
    app = create_app()

    async def override_get_session() -> AsyncGenerator[Session, None]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


def test_run_stream_sends_snapshot_and_terminal_event(db_session: Session) -> None:
    with _build_sync_client(db_session) as client:
        create_response = client.post(
            "/v1/runs",
            json={"prompt": "Write Python code that computes a square root.", "provider": "fake"},
        )
        run_id = create_response.json()["run_id"]

        with client.websocket_connect(f"/v1/runs/{run_id}/stream") as websocket:
            snapshot = websocket.receive_json()
            terminal = websocket.receive_json()

    assert snapshot["type"] == "run.snapshot"
    assert snapshot["runId"] == run_id
    assert snapshot["data"]["run"]["run_id"] == run_id
    assert len(snapshot["data"]["evidence"]) >= 6
    assert len(snapshot["data"]["events"]) >= 2
    assert terminal["type"] == "run.completed"
    assert terminal["data"]["run"]["status"] == "completed"


def test_run_stream_reports_missing_run_as_error(db_session: Session) -> None:
    with _build_sync_client(db_session) as client:
        with client.websocket_connect("/v1/runs/missing/stream") as websocket:
            message = websocket.receive_json()

    assert message["type"] == "error"
    assert message["data"]["message"] == "Run not found"
