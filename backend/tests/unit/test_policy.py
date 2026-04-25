from __future__ import annotations

from dehalu.schemas import (
    PolicyDecisionState,
    RiskLevel,
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

