from __future__ import annotations

from dehalu.schemas import (
    CoVeCheckVerdict,
    CoVeClaimCheck,
    CoVeResult,
    CoVeVerdict,
    JudgeFinding,
    JudgeResult,
    JudgeVerdict,
    PolicyDecisionState,
    RiskLevel,
    SandboxResult,
    SandboxStatus,
    StaticFinding,
    StaticFindingSeverity,
)
from dehalu.verification.policy import PolicyEngine


def test_policy_repairs_errors_before_final_reject() -> None:
    decision = PolicyEngine().decide(
        [
            StaticFinding(
                code="syntax_error",
                message="invalid syntax",
                severity=StaticFindingSeverity.error,
            )
        ],
        RiskLevel.medium,
    )

    assert decision.state == PolicyDecisionState.repair_and_retry
    assert decision.hard_fail is False
    assert decision.metrics["repair_trigger"] == "deterministic_error"


def test_policy_rejects_errors_after_repair_attempt() -> None:
    decision = PolicyEngine().decide(
        [
            StaticFinding(
                code="syntax_error",
                message="invalid syntax",
                severity=StaticFindingSeverity.error,
            )
        ],
        RiskLevel.medium,
        allow_repair=False,
    )

    assert decision.state == PolicyDecisionState.reject
    assert decision.hard_fail is True


def test_policy_warns_on_warnings_for_medium_risk() -> None:
    decision = PolicyEngine().decide(
        [
            StaticFinding(
                code="dangerous_symbol",
                message="eval is risky",
                severity=StaticFindingSeverity.warning,
            )
        ],
        RiskLevel.medium,
    )

    assert decision.state == PolicyDecisionState.warn_and_return_partial
    assert decision.hard_fail is False


def test_policy_accepts_clean_evidence() -> None:
    decision = PolicyEngine().decide([], RiskLevel.low)

    assert decision.state == PolicyDecisionState.accept
    assert decision.score == 0.95


def test_policy_rejects_sandbox_errors() -> None:
    sandbox_result = SandboxResult(
        status=SandboxStatus.failed,
        check_type="compile_only",
        language="python",
        duration_ms=1.0,
        findings=[
            StaticFinding(
                code="sandbox_compile_error",
                message="invalid syntax",
                severity=StaticFindingSeverity.error,
            )
        ],
    )

    decision = PolicyEngine().decide([], RiskLevel.medium, sandbox_result)

    assert decision.state == PolicyDecisionState.repair_and_retry
    assert decision.hard_fail is False
    assert decision.metrics["sandbox_status"] == "failed"
    assert decision.metrics["repair_trigger"] == "deterministic_error"


def test_policy_rejects_judge_fail_without_deterministic_errors() -> None:
    judge_result = JudgeResult(
        verdict=JudgeVerdict.fail,
        provider="fake",
        model="fake",
        duration_ms=1.0,
        hallucination_score=0.9,
        findings=[
            JudgeFinding(
                code="empty_output",
                message="Coder output did not include code to verify.",
                severity=StaticFindingSeverity.error,
            )
        ],
    )

    decision = PolicyEngine().decide([], RiskLevel.medium, judge_result=judge_result)

    assert decision.state == PolicyDecisionState.repair_and_retry
    assert decision.hard_fail is False
    assert decision.metrics["judge_verdict"] == "fail"
    assert decision.metrics["repair_trigger"] == "judge_fail"


def test_policy_warns_on_judge_uncertain_for_medium_risk() -> None:
    judge_result = JudgeResult(
        verdict=JudgeVerdict.uncertain,
        provider="fake",
        model="fake",
        duration_ms=1.0,
        hallucination_score=0.55,
        findings=[
            JudgeFinding(
                code="unsafe_or_unverifiable_construct",
                message="Code uses construct requiring stronger verification: eval.",
                severity=StaticFindingSeverity.warning,
            )
        ],
    )

    decision = PolicyEngine().decide([], RiskLevel.medium, judge_result=judge_result)

    assert decision.state == PolicyDecisionState.repair_and_retry
    assert decision.hard_fail is False
    assert decision.metrics["judge_verdict"] == "uncertain"
    assert decision.metrics["repair_trigger"] == "judge_uncertain"


def test_policy_rejects_judge_uncertain_for_high_risk() -> None:
    judge_result = JudgeResult(
        verdict=JudgeVerdict.uncertain,
        provider="fake",
        model="fake",
        duration_ms=1.0,
        hallucination_score=0.55,
    )

    decision = PolicyEngine().decide([], RiskLevel.high, judge_result=judge_result, allow_repair=False)

    assert decision.state == PolicyDecisionState.reject
    assert decision.hard_fail is True


def test_policy_repairs_high_risk_warnings_before_final_reject() -> None:
    decision = PolicyEngine().decide(
        [
            StaticFinding(
                code="unsupported_import",
                message="Import could not be validated.",
                severity=StaticFindingSeverity.warning,
            )
        ],
        RiskLevel.high,
    )

    assert decision.state == PolicyDecisionState.repair_and_retry
    assert decision.hard_fail is False
    assert decision.metrics["repair_trigger"] == "deterministic_error"


def test_policy_rejects_cove_fail_without_deterministic_errors() -> None:
    cove_result = CoVeResult(
        verdict=CoVeVerdict.fail,
        provider="fake",
        model="fake",
        duration_ms=1.0,
        hallucination_score=0.9,
        checks=[
            CoVeClaimCheck(
                claim="math.sqrt",
                question="Does the code use math.sqrt?",
                answer="No matching symbol was found.",
                verdict=CoVeCheckVerdict.unsupported,
            )
        ],
        metrics={
            "supported_claim_count": 0,
            "unsupported_claim_count": 1,
            "uncertain_claim_count": 0,
        },
    )

    decision = PolicyEngine().decide([], RiskLevel.medium, cove_result=cove_result)

    assert decision.state == PolicyDecisionState.repair_and_retry
    assert decision.hard_fail is False
    assert decision.metrics["cove_verdict"] == "fail"
    assert decision.metrics["repair_trigger"] == "cove_fail"


def test_policy_warns_on_cove_uncertain_for_medium_risk() -> None:
    cove_result = CoVeResult(
        verdict=CoVeVerdict.uncertain,
        provider="fake",
        model="fake",
        duration_ms=1.0,
        hallucination_score=0.55,
        checks=[
            CoVeClaimCheck(
                claim="eval(user_input)",
                question="Is this claim safe and fully verified?",
                answer="The claim depends on eval and needs stronger verification.",
                verdict=CoVeCheckVerdict.uncertain,
            )
        ],
        metrics={
            "supported_claim_count": 0,
            "unsupported_claim_count": 0,
            "uncertain_claim_count": 1,
        },
    )

    decision = PolicyEngine().decide([], RiskLevel.medium, cove_result=cove_result)

    assert decision.state == PolicyDecisionState.repair_and_retry
    assert decision.hard_fail is False
    assert decision.metrics["uncertain_claim_count"] == 1
    assert decision.metrics["repair_trigger"] == "cove_uncertain"


def test_policy_rejects_cove_uncertain_for_high_risk() -> None:
    cove_result = CoVeResult(
        verdict=CoVeVerdict.uncertain,
        provider="fake",
        model="fake",
        duration_ms=1.0,
        hallucination_score=0.55,
        metrics={
            "supported_claim_count": 0,
            "unsupported_claim_count": 0,
            "uncertain_claim_count": 1,
        },
    )

    decision = PolicyEngine().decide([], RiskLevel.high, cove_result=cove_result, allow_repair=False)

    assert decision.state == PolicyDecisionState.reject
    assert decision.hard_fail is True


def test_policy_warns_on_judge_uncertain_after_repair_attempt() -> None:
    judge_result = JudgeResult(
        verdict=JudgeVerdict.uncertain,
        provider="fake",
        model="fake",
        duration_ms=1.0,
        hallucination_score=0.55,
    )

    decision = PolicyEngine().decide([], RiskLevel.medium, judge_result=judge_result, allow_repair=False)

    assert decision.state == PolicyDecisionState.warn_and_return_partial
    assert decision.hard_fail is False
