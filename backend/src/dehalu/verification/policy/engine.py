from __future__ import annotations

from dehalu.schemas import (
    PolicyDecision,
    PolicyDecisionState,
    RiskLevel,
    StaticFinding,
    StaticFindingSeverity,
)


class PolicyEngine:
    def decide(self, findings: list[StaticFinding], risk_level: RiskLevel) -> PolicyDecision:
        errors = [finding for finding in findings if finding.severity == StaticFindingSeverity.error]
        warnings = [finding for finding in findings if finding.severity == StaticFindingSeverity.warning]

        if errors:
            return PolicyDecision(
                state=PolicyDecisionState.reject,
                reasons=[finding.message for finding in errors],
                hard_fail=True,
                score=0.0,
                metrics={
                    "error_count": len(errors),
                    "warning_count": len(warnings),
                    "risk_level": risk_level.value,
                },
            )

        if risk_level == RiskLevel.high and warnings:
            return PolicyDecision(
                state=PolicyDecisionState.reject,
                reasons=[finding.message for finding in warnings],
                hard_fail=True,
                score=0.2,
                metrics={
                    "error_count": 0,
                    "warning_count": len(warnings),
                    "risk_level": risk_level.value,
                },
            )

        if warnings:
            return PolicyDecision(
                state=PolicyDecisionState.warn_and_return_partial,
                reasons=[finding.message for finding in warnings],
                hard_fail=False,
                score=0.65,
                metrics={
                    "error_count": 0,
                    "warning_count": len(warnings),
                    "risk_level": risk_level.value,
                },
            )

        return PolicyDecision(
            state=PolicyDecisionState.accept,
            reasons=["No blocking hallucination evidence detected in first-iteration checks."],
            hard_fail=False,
            score=0.95,
            metrics={
                "error_count": 0,
                "warning_count": 0,
                "risk_level": risk_level.value,
            },
        )

