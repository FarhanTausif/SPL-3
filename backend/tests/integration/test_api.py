from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.anyio


async def test_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["providers"] == {"fake": True}


async def test_create_and_fetch_run(client: AsyncClient) -> None:
    create_response = await client.post(
        "/v1/runs",
        json={"prompt": "Write Python code that computes a square root."},
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    run_id = payload["run_id"]
    assert payload["policy_decision"]["state"] == "accept"
    assert len(payload["evidence_ids"]) == 3

    detail_response = await client.get(f"/v1/runs/{run_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["run_id"] == run_id

    evidence_response = await client.get(f"/v1/runs/{run_id}/evidence")
    assert evidence_response.status_code == 200
    assert {item["kind"] for item in evidence_response.json()} == {
        "claim_extraction",
        "static_analysis",
        "policy",
    }


async def test_create_run_rejects_unknown_provider(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/runs",
        json={"prompt": "Write Python code.", "provider": "missing"},
    )

    assert response.status_code == 400
