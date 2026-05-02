"""
E2E tests: Complete orchestration flows
Tests end-to-end verification pipeline stages: claims → static → sandbox → judges → policy
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from dehalu.state.models import RunRecord, EvidenceRecord

pytestmark = pytest.mark.anyio


async def test_direct_execution_complete_flow(
    client: AsyncClient, db_session: Session
) -> None:
    """Test: Complete direct execution (request → response)"""

    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Write a function to compute factorial",
            "language_hint": "python",
            "risk_level": "low",
        },
    )

    assert response.status_code == 201
    data = response.json()

    # Verify all stages completed
    assert data["stage_summary"] is not None
    stages = {stage["stage"]: stage for stage in data["stage_summary"]}
    assert "generation" in stages
    assert "verification" in stages
    assert "policy" in stages

    # Verify generation stage
    assert stages["generation"]["status"] == "completed"
    assert data["coder_output"] is not None

    # Verify verification stage includes all substages
    assert data["extracted_claims"] is not None
    assert len(data["extracted_claims"]) > 0
    assert data["static_findings"] is not None
    assert data["sandbox_result"] is not None
    assert data["judge_result"] is not None
    assert data["cove_result"] is not None

    # Verify policy stage
    assert stages["policy"]["status"] == "completed"
    assert data["policy_decision"] is not None
    assert data["policy_decision"]["state"] in ["accept", "warn_and_return_partial", "repair_and_retry", "reject"]

    # Verify complete evidence collection
    assert len(data["evidence_ids"]) > 0


async def test_verification_pipeline_claims_extraction(
    client: AsyncClient,
) -> None:
    """Test: Claim extraction from generated code"""

    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Write a Python function",
            "language_hint": "python",
        },
    )

    data = response.json()
    assert len(data["extracted_claims"]) > 0

    # Verify claim structure
    for claim in data["extracted_claims"]:
        assert "kind" in claim
        assert "value" in claim
        assert "source" in claim
        assert claim["kind"] in [
            "code", "assumption", "import", "symbol", "builtin", "class_def", "function_def"
        ]


async def test_verification_pipeline_static_analysis(
    client: AsyncClient,
) -> None:
    """Test: Static analysis stage of verification"""

    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Write valid Python code",
            "language_hint": "python",
        },
    )

    data = response.json()

    # Verify static findings exist
    assert "static_findings" in data
    assert isinstance(data["static_findings"], list)

    # For valid code, should have no errors (may have info/warnings)
    errors = [f for f in data["static_findings"] if f.get("severity") == "error"]
    assert len(errors) == 0, "Valid code should have no errors"


async def test_verification_pipeline_sandbox_execution(
    client: AsyncClient,
) -> None:
    """Test: Sandbox execution stage"""

    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Write Python code",
            "language_hint": "python",
        },
    )

    data = response.json()

    # Verify sandbox result
    assert "sandbox_result" in data
    result = data["sandbox_result"]
    assert "status" in result
    assert result["status"] in ["passed", "failed", "timeout", "error"]
    assert "duration_ms" in result


async def test_verification_pipeline_judge_verdict(
    client: AsyncClient,
) -> None:
    """Test: Judge stage (CoVe or LLM judge)"""

    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Write Python code",
            "language_hint": "python",
        },
    )

    data = response.json()

    # Verify judge result
    assert "judge_result" in data
    result = data["judge_result"]
    assert result["verdict"] in ["pass", "fail", "uncertain"]
    assert "hallucination_score" in result
    assert 0 <= result["hallucination_score"] <= 1


async def test_verification_pipeline_cove_stage(
    client: AsyncClient,
) -> None:
    """Test: CoVE verification stage"""

    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Write Python code",
            "language_hint": "python",
        },
    )

    data = response.json()

    # Verify CoVE result
    assert "cove_result" in data
    result = data["cove_result"]
    assert result["verdict"] in ["pass", "fail", "uncertain"]
    assert "hallucination_score" in result
    assert isinstance(result.get("checks", []), list)


async def test_verification_pipeline_policy_decision(
    client: AsyncClient,
) -> None:
    """Test: Policy decision stage"""

    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Write Python code",
            "language_hint": "python",
        },
    )

    data = response.json()

    # Verify policy decision
    assert "policy_decision" in data
    decision = data["policy_decision"]
    assert decision["state"] in ["accept", "warn_and_return_partial", "repair_and_retry", "reject"]
    assert "reasons" in decision
    assert isinstance(decision.get("reasons", []), list)
    assert "metrics" in decision


async def test_repair_flow_triggered_on_failure(
    client: AsyncClient,
) -> None:
    """Test: Repair flow is triggered when verification fails"""

    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Write Python code",
            "language_hint": "python",
            "risk_level": "high",  # High risk to potentially trigger repair
        },
    )

    data = response.json()

    # Verify repair result exists
    assert "repair_result" in data
    result = data["repair_result"]
    assert "outcome" in result
    assert result["outcome"] in ["skipped", "attempted", "succeeded", "failed"]

    # If repair was attempted, verify attempt details
    if result["outcome"] in ["attempted", "succeeded", "failed"]:
        assert "attempts" in result
        assert isinstance(result["attempts"], list)


async def test_evidence_collection_across_all_stages(
    client: AsyncClient,
) -> None:
    """Test: Evidence collected from all verification stages"""

    response = await client.post(
        "/v1/runs",
        json={
            "prompt": "Write Python function",
            "language_hint": "python",
        },
    )

    run_id = response.json()["run_id"]

    # Get evidence
    response = await client.get(f"/v1/runs/{run_id}/evidence")
    evidence = response.json()

    # Should have evidence from multiple stages
    kinds = {ev["kind"] for ev in evidence}
    assert len(kinds) > 1, "Should have evidence from multiple stages"


async def test_complete_orchestration_state_flow(
    client: AsyncClient, db_session: Session
) -> None:
    """Test: Complete orchestration flow with state transitions"""

    # Create run
    response = await client.post(
        "/v1/runs",
        json={"prompt": "Test", "language_hint": "python"},
    )

    run_id = response.json()["run_id"]
    initial_status = response.json()["status"]

    # Get run to verify state
    response = await client.get(f"/v1/runs/{run_id}")
    retrieved_status = response.json()["status"]

    # Verify consistency
    assert retrieved_status == initial_status

    # Check database state
    db_run = db_session.query(RunRecord).filter(RunRecord.id == run_id).first()
    assert db_run is not None
    assert db_run.status == initial_status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
