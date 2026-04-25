from __future__ import annotations

from dehalu.schemas import (
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


def test_policy_rejects_errors() -> None:
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

    assert decision.state == PolicyDecisionState.reject
    assert decision.hard_fail is True
    assert decision.metrics["sandbox_status"] == "failed"


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

    assert decision.state == PolicyDecisionState.reject
    assert decision.hard_fail is True
    assert decision.metrics["judge_verdict"] == "fail"


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

    assert decision.state == PolicyDecisionState.warn_and_return_partial
    assert decision.hard_fail is False
    assert decision.metrics["judge_verdict"] == "uncertain"


def test_policy_rejects_judge_uncertain_for_high_risk() -> None:
    judge_result = JudgeResult(
        verdict=JudgeVerdict.uncertain,
        provider="fake",
        model="fake",
        duration_ms=1.0,
        hallucination_score=0.55,
    )

    decision = PolicyEngine().decide([], RiskLevel.high, judge_result=judge_result)

    assert decision.state == PolicyDecisionState.reject
    assert decision.hard_fail is True
