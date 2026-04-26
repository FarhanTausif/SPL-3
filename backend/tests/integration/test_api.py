from __future__ import annotations

import json

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session

from dehalu.adapters.llm import GeminiLLMProvider, ProviderRegistry, build_provider_registry
from dehalu.api.dependencies import get_orchestrator, get_provider_registry
from dehalu.core.app import create_app
from dehalu.core.settings import Settings
from dehalu.orchestration import RunOrchestrator
from dehalu.state.database import get_session

pytestmark = pytest.mark.anyio


def _build_test_app(
    settings: Settings,
    registry: ProviderRegistry,
    db_session: Session,
):
    app = create_app()

    async def override_registry() -> ProviderRegistry:
        return registry

    async def override_orchestrator() -> RunOrchestrator:
        return RunOrchestrator(settings, registry)

    async def override_get_session() -> Session:
        return db_session

    app.dependency_overrides[get_provider_registry] = override_registry
    app.dependency_overrides[get_orchestrator] = override_orchestrator
    app.dependency_overrides[get_session] = override_get_session
    return app


def _json_candidate(payload: dict[str, object]) -> dict[str, object]:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(payload),
                        }
                    ]
                }
            }
        ]
    }


async def test_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["providers"]["fake"] is True
    assert response.json()["orchestration"]["configured_mode"] == "direct"
    assert response.json()["orchestration"]["crewai_enabled"] is False


async def test_create_and_fetch_run(client: AsyncClient) -> None:
    create_response = await client.post(
        "/v1/runs",
        json={"prompt": "Write Python code that computes a square root.", "provider": "fake"},
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    run_id = payload["run_id"]
    assert payload["policy_decision"]["state"] == "accept"
    assert payload["sandbox_result"]["status"] == "passed"
    assert payload["judge_result"]["verdict"] == "pass"
    assert payload["cove_result"]["verdict"] == "pass"
    assert payload["repair_result"]["outcome"] == "skipped"
    assert len(payload["evidence_ids"]) == 6

    detail_response = await client.get(f"/v1/runs/{run_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["run_id"] == run_id

    evidence_response = await client.get(f"/v1/runs/{run_id}/evidence")
    assert evidence_response.status_code == 200
    evidence = evidence_response.json()
    assert {item["kind"] for item in evidence} == {
        "claim_extraction",
        "static_analysis",
        "sandbox",
        "judge",
        "cove",
        "policy",
    }
    claim_evidence = next(item for item in evidence if item["kind"] == "claim_extraction")
    assert claim_evidence["payload"]["orchestration_mode"] == "direct"
    assert claim_evidence["payload"]["stage"] == "extract_claims"


async def test_create_run_rejects_unknown_provider(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/runs",
        json={"prompt": "Write Python code.", "provider": "missing"},
    )

    assert response.status_code == 400


async def test_create_run_repairs_fake_output_and_returns_final_accept(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/runs",
        json={"prompt": "Write dangerous Python code.", "provider": "fake"},
    )

    payload = response.json()

    assert response.status_code == 201
    assert payload["repair_result"]["outcome"] == "succeeded"
    assert payload["repair_result"]["final_attempt_number"] == 2
    assert payload["policy_decision"]["state"] == "accept"
    assert len(payload["evidence_ids"]) == 13

    evidence_response = await client.get(f"/v1/runs/{payload['run_id']}/evidence")
    evidence = evidence_response.json()

    assert evidence_response.status_code == 200
    assert len(evidence) == 13
    assert {item["kind"] for item in evidence} == {
        "claim_extraction",
        "static_analysis",
        "sandbox",
        "judge",
        "cove",
        "repair",
        "policy",
    }
    assert sum(1 for item in evidence if item["kind"] == "repair") == 1


async def test_create_run_repair_failure_fails_closed(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Write dangerous Python code with repair failure.",
            "provider": "fake",
            "risk_level": "high",
        },
    )

    payload = response.json()

    assert response.status_code == 201
    assert payload["repair_result"]["outcome"] == "failed"
    assert payload["policy_decision"]["state"] == "reject"
    assert payload["repair_result"]["final_attempt_number"] == 2
    assert len(payload["evidence_ids"]) == 13


async def test_create_run_with_gemini_provider_persists_judge_cove_and_repair_metadata(
    db_session: Session,
) -> None:
    responses = iter(
        [
            httpx.Response(
                200,
                json={
                    "candidates": [
                        {"content": {"parts": [{"text": "import math\n\nprint(math.sqrt(4))\n"}]}}
                    ]
                },
            ),
            httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": json.dumps(
                                            {
                                                "verdict": "pass",
                                                "hallucination_score": 0.08,
                                                "findings": [],
                                                "metrics": {"judge_mode": "gemini"},
                                            }
                                        )
                                    }
                                ]
                            }
                        }
                    ]
                },
            ),
            httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": json.dumps(
                                            {
                                                "checks": [
                                                    {
                                                        "claim": "math.sqrt",
                                                        "question": "Does the code use math.sqrt?",
                                                        "answer": "Yes.",
                                                        "verdict": "supported",
                                                        "metadata": {"kind": "symbol"},
                                                    }
                                                ],
                                                "findings": [],
                                                "hallucination_score": 0.08,
                                            }
                                        )
                                    }
                                ]
                            }
                        }
                    ]
                },
            ),
        ]
    )
    client = httpx.Client(transport=httpx.MockTransport(lambda request: next(responses)))
    settings = Settings(database_url="sqlite://", gemini_api_key="test-key")
    registry = ProviderRegistry([GeminiLLMProvider(settings, http_client=client)])
    app = _build_test_app(settings, registry, db_session)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        response = await test_client.post(
            "/v1/runs",
            json={"prompt": "Write Python code that computes a square root.", "provider": "gemini"},
        )

    payload = response.json()

    assert response.status_code == 201
    assert payload["judge_result"]["provider"] == "gemini"
    assert payload["cove_result"]["provider"] == "gemini"
    assert payload["repair_result"]["outcome"] == "skipped"
    assert len(payload["evidence_ids"]) == 6

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as evidence_client:
        evidence_response = await evidence_client.get(f"/v1/runs/{payload['run_id']}/evidence")

    assert evidence_response.status_code == 200
    assert {item["kind"] for item in evidence_response.json()} == {
        "claim_extraction",
        "static_analysis",
        "sandbox",
        "judge",
        "cove",
        "policy",
    }


async def test_create_run_in_crewai_mode_matches_direct_for_clean_fake(
    db_session: Session,
) -> None:
    settings = Settings(
        database_url="sqlite://",
        default_provider="fake",
        gemini_api_key=None,
        orchestration_mode="crewai",
    )
    registry = build_provider_registry(settings)
    app = _build_test_app(settings, registry, db_session)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        response = await test_client.post(
            "/v1/runs",
            json={"prompt": "Write Python code that computes a square root.", "provider": "fake"},
        )

    payload = response.json()

    assert response.status_code == 201
    assert payload["policy_decision"]["state"] == "accept"
    assert payload["repair_result"]["outcome"] == "skipped"
    assert len(payload["evidence_ids"]) == 7

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as evidence_client:
        evidence_response = await evidence_client.get(f"/v1/runs/{payload['run_id']}/evidence")

    evidence = evidence_response.json()

    assert evidence_response.status_code == 200
    assert {item["kind"] for item in evidence} == {
        "claim_extraction",
        "static_analysis",
        "sandbox",
        "judge",
        "cove",
        "policy",
        "orchestration",
    }
    orchestration_evidence = next(item for item in evidence if item["kind"] == "orchestration")
    assert orchestration_evidence["payload"]["orchestration_mode"] == "crewai"
    assert orchestration_evidence["payload"]["entry_count"] > 0


async def test_create_run_in_crewai_mode_repairs_fake_output(
    db_session: Session,
) -> None:
    settings = Settings(
        database_url="sqlite://",
        default_provider="fake",
        gemini_api_key=None,
        orchestration_mode="crewai",
    )
    registry = build_provider_registry(settings)
    app = _build_test_app(settings, registry, db_session)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        response = await test_client.post(
            "/v1/runs",
            json={"prompt": "Write dangerous Python code.", "provider": "fake"},
        )

    payload = response.json()

    assert response.status_code == 201
    assert payload["policy_decision"]["state"] == "accept"
    assert payload["repair_result"]["outcome"] == "succeeded"
    assert len(payload["evidence_ids"]) == 14


async def test_create_run_in_crewai_mode_fails_closed_on_bad_repair(
    db_session: Session,
) -> None:
    settings = Settings(
        database_url="sqlite://",
        default_provider="fake",
        gemini_api_key=None,
        orchestration_mode="crewai",
    )
    registry = build_provider_registry(settings)
    app = _build_test_app(settings, registry, db_session)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        response = await test_client.post(
            "/v1/runs",
            json={
                "prompt": "Write dangerous Python code with repair failure.",
                "provider": "fake",
                "risk_level": "high",
            },
        )

    payload = response.json()

    assert response.status_code == 201
    assert payload["policy_decision"]["state"] == "reject"
    assert payload["repair_result"]["outcome"] == "failed"
    assert len(payload["evidence_ids"]) == 14


async def test_create_run_in_crewai_mode_supports_gemini_provider(
    db_session: Session,
) -> None:
    responses = iter(
        [
            httpx.Response(
                200,
                json={
                    "candidates": [
                        {"content": {"parts": [{"text": "import math\n\nprint(math.sqrt(4))\n"}]}}
                    ]
                },
            ),
            httpx.Response(
                200,
                json=_json_candidate(
                    {
                        "verdict": "pass",
                        "hallucination_score": 0.08,
                        "findings": [],
                        "metrics": {"judge_mode": "gemini"},
                    }
                ),
            ),
            httpx.Response(
                200,
                json=_json_candidate(
                    {
                        "checks": [
                            {
                                "claim": "math.sqrt",
                                "question": "Does the code use math.sqrt?",
                                "answer": "Yes.",
                                "verdict": "supported",
                                "metadata": {"kind": "symbol"},
                            }
                        ],
                        "findings": [],
                        "hallucination_score": 0.08,
                    }
                ),
            ),
        ]
    )
    client = httpx.Client(transport=httpx.MockTransport(lambda request: next(responses)))
    settings = Settings(
        database_url="sqlite://",
        gemini_api_key="test-key",
        orchestration_mode="crewai",
    )
    registry = ProviderRegistry([GeminiLLMProvider(settings, http_client=client)])
    app = _build_test_app(settings, registry, db_session)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        response = await test_client.post(
            "/v1/runs",
            json={"prompt": "Write Python code that computes a square root.", "provider": "gemini"},
        )

    payload = response.json()

    assert response.status_code == 201
    assert payload["judge_result"]["provider"] == "gemini"
    assert payload["cove_result"]["provider"] == "gemini"
    assert payload["repair_result"]["outcome"] == "skipped"
    assert len(payload["evidence_ids"]) == 7


async def test_create_advanced_run_returns_completed_status_and_events(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Write Python code that computes a square root.",
            "provider": "fake",
            "run_mode": "advanced",
            "acceptance_criteria": ["Use math.sqrt."],
        },
    )

    payload = response.json()

    assert response.status_code == 201
    assert payload["status"] == "completed"
    assert payload["clarification_result"]["language"] == "python"
    assert payload["fused_metrics"]["overall_hallucination_score"] >= 0.0

    detail_response = await client.get(f"/v1/runs/{payload['run_id']}")
    events_response = await client.get(f"/v1/runs/{payload['run_id']}/events")
    evidence_response = await client.get(f"/v1/runs/{payload['run_id']}/evidence")

    detail = detail_response.json()
    events = events_response.json()
    evidence = evidence_response.json()

    assert detail_response.status_code == 200
    assert detail["status"] == "completed"
    assert events_response.status_code == 200
    assert len(events) >= 3
    assert events[0]["event_type"] == "run_created"
    assert evidence_response.status_code == 200
    assert {"tool", "panel", "fusion", "routing", "clarification"}.issubset({item["kind"] for item in evidence})


async def test_create_advanced_run_can_stop_for_clarification(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Maybe write something for Python, whatever works.",
            "provider": "fake",
            "run_mode": "advanced",
        },
    )

    payload = response.json()

    assert response.status_code == 201
    assert payload["status"] == "needs_clarification"
    assert payload["coder_output"] is None

    detail_response = await client.get(f"/v1/runs/{payload['run_id']}")
    events_response = await client.get(f"/v1/runs/{payload['run_id']}/events")

    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "needs_clarification"
    assert any(event["event_type"] == "clarification_completed" for event in events_response.json())
