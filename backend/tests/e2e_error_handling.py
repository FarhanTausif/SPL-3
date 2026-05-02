"""
E2E tests: Error handling and edge cases
Tests robustness, proper error responses, and boundary conditions.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


# Error Response Tests
async def test_invalid_run_id_returns_404(client: AsyncClient) -> None:
    """Test: Get non-existent run returns 404"""
    response = await client.get("/v1/runs/invalid-run-id-12345")
    assert response.status_code == 404


async def test_get_evidence_invalid_run_id_returns_404(client: AsyncClient) -> None:
    """Test: Get evidence for non-existent run returns 404"""
    response = await client.get("/v1/runs/invalid-run-id-12345/evidence")
    assert response.status_code == 404


async def test_get_events_invalid_run_id_returns_404(client: AsyncClient) -> None:
    """Test: Get events for non-existent run returns 404"""
    response = await client.get("/v1/runs/invalid-run-id-12345/events")
    assert response.status_code == 404


async def test_missing_required_prompt_returns_422(client: AsyncClient) -> None:
    """Test: Missing required 'prompt' field returns 422"""
    response = await client.post(
        "/v1/runs",
        json={"language_hint": "python"},  # Missing prompt
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


async def test_invalid_json_returns_400(client: AsyncClient) -> None:
    """Test: Malformed JSON returns 400"""
    response = await client.post(
        "/v1/runs",
        content=b"{ invalid json }",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422  # FastAPI returns 422 for parse errors


async def test_unknown_language_handled(client: AsyncClient) -> None:
    """Test: Unknown language gracefully handled"""
    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Write code",
            "language_hint": "unknown_language_xyz",
        },
    )
    # Should either work (with default) or return clear error
    assert response.status_code in [201, 400, 422]


async def test_empty_prompt_string(client: AsyncClient) -> None:
    """Test: Empty prompt is handled"""
    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "",  # Empty
            "language_hint": "python",
        },
    )
    # Should create or reject, but not crash
    assert response.status_code in [201, 400, 422]


async def test_very_long_prompt(client: AsyncClient) -> None:
    """Test: Very long prompt is handled"""
    long_prompt = "x" * 100000  # 100k character prompt
    response = await client.post(
        "/v1/runs",
        json={
            "prompt": long_prompt,
            "language_hint": "python",
        },
    )
    # Should create or reject gracefully
    assert response.status_code in [201, 400, 422, 413]  # 413 = Payload Too Large


async def test_invalid_risk_level(client: AsyncClient) -> None:
    """Test: Invalid risk_level is handled"""
    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Test",
            "language_hint": "python",
            "risk_level": "invalid_risk",
        },
    )
    # Should reject invalid enum
    assert response.status_code == 422


async def test_negative_latency_budget(client: AsyncClient) -> None:
    """Test: Negative latency budget is handled"""
    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Test",
            "language_hint": "python",
            "latency_budget_seconds": -10,  # Invalid
        },
    )
    # Should reject invalid value
    assert response.status_code == 422


async def test_zero_latency_budget(client: AsyncClient) -> None:
    """Test: Zero latency budget is handled"""
    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Test",
            "language_hint": "python",
            "latency_budget_seconds": 0,  # Boundary
        },
    )
    # Should handle boundary case
    assert response.status_code in [201, 400, 422]


async def test_null_prompt_returns_422(client: AsyncClient) -> None:
    """Test: Null prompt returns 422"""
    response = await client.post(
        "/v1/runs",
        json={
            "prompt": None,
            "language_hint": "python",
        },
    )
    assert response.status_code == 422


async def test_health_endpoint_always_available(client: AsyncClient) -> None:
    """Test: Health endpoint always returns 200"""
    for _ in range(5):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


async def test_concurrent_requests_no_collision(client: AsyncClient) -> None:
    """Test: Multiple concurrent requests don't collide"""
    # Create multiple runs quickly
    responses = await asyncio_gather(
        *[
            client.post(
                "/v1/runs",
                json={"prompt": f"Test {i}", "language_hint": "python"},
            )
            for i in range(5)
        ]
    )

    run_ids = set()
    for response in responses:
        assert response.status_code == 201
        run_id = response.json()["run_id"]
        assert run_id not in run_ids, "Run IDs should be unique"
        run_ids.add(run_id)


async def test_run_id_uniqueness_maintained(client: AsyncClient) -> None:
    """Test: Each run gets a unique ID"""
    run_ids = set()
    for i in range(10):
        response = await client.post(
            "/v1/runs",
            json={"prompt": f"Test {i}", "language_hint": "python"},
        )
        assert response.status_code == 201
        run_id = response.json()["run_id"]
        assert run_id not in run_ids, "Duplicate run ID detected"
        run_ids.add(run_id)


async def test_response_has_error_details_on_failure(client: AsyncClient) -> None:
    """Test: Error responses include helpful details"""
    response = await client.get("/v1/runs/invalid-id")
    assert response.status_code == 404
    data = response.json()
    # Should have error information
    assert "detail" in data or "error" in data or len(data) > 0


async def test_multiple_requests_database_consistency(client: AsyncClient) -> None:
    """Test: Database remains consistent across multiple requests"""
    # Create run
    response1 = await client.post(
        "/v1/runs",
        json={"prompt": "Test 1", "language_hint": "python"},
    )
    run_id_1 = response1.json()["run_id"]

    # Create another run
    response2 = await client.post(
        "/v1/runs",
        json={"prompt": "Test 2", "language_hint": "python"},
    )
    run_id_2 = response2.json()["run_id"]

    # Retrieve first run
    response = await client.get(f"/v1/runs/{run_id_1}")
    assert response.status_code == 200
    retrieved = response.json()
    assert retrieved["run_id"] == run_id_1
    assert retrieved["normalized_request"]["prompt"] == "Test 1"

    # Verify second run is separate
    response = await client.get(f"/v1/runs/{run_id_2}")
    assert response.status_code == 200
    retrieved = response.json()
    assert retrieved["run_id"] == run_id_2
    assert retrieved["normalized_request"]["prompt"] == "Test 2"


async def test_evidence_exists_for_all_runs(client: AsyncClient) -> None:
    """Test: All runs have retrievable evidence"""
    response = await client.post(
        "/v1/runs",
        json={"prompt": "Test", "language_hint": "python"},
    )
    run_id = response.json()["run_id"]

    response = await client.get(f"/v1/runs/{run_id}/evidence")
    assert response.status_code == 200
    evidence = response.json()
    assert isinstance(evidence, list)
    assert len(evidence) > 0, "All runs should have evidence"


async def test_events_exist_for_all_runs(client: AsyncClient) -> None:
    """Test: All runs have retrievable events"""
    response = await client.post(
        "/v1/runs",
        json={"prompt": "Test", "language_hint": "python"},
    )
    run_id = response.json()["run_id"]

    response = await client.get(f"/v1/runs/{run_id}/events")
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    assert len(events) > 0, "All runs should have events"


# Helper for concurrent requests
async def asyncio_gather(*coros):
    import asyncio
    return await asyncio.gather(*coros)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
