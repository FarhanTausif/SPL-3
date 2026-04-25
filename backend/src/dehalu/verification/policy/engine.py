from __future__ import annotations

from dehalu.schemas import (
    PolicyDecision,
    PolicyDecisionState,
    RiskLevel,
    SandboxResult,
    StaticFinding,
    StaticFindingSeverity,
)


class PolicyEngine:
    def decide(
        self,
        findings: list[StaticFinding],
        risk_level: RiskLevel,
        sandbox_result: SandboxResult | None = None,
    ) -> PolicyDecision:
        sandbox_findings = sandbox_result.findings if sandbox_result else []
        all_findings = [*findings, *sandbox_findings]
        errors = [
            finding
            for finding in all_findings
            if finding.severity == StaticFindingSeverity.error
        ]
        warnings = [
            finding
            for finding in all_findings
            if finding.severity == StaticFindingSeverity.warning
        ]
        metrics = {
            "error_count": len(errors),
            "warning_count": len(warnings),
            "risk_level": risk_level.value,
        }
        if sandbox_result:
            metrics["sandbox_status"] = sandbox_result.status.value
            metrics["sandbox_check_type"] = sandbox_result.check_type

        if errors:
            return PolicyDecision(
                state=PolicyDecisionState.reject,
                reasons=[finding.message for finding in errors],
                hard_fail=True,
                score=0.0,
                metrics=metrics,
            )

        if risk_level == RiskLevel.high and warnings:
            return PolicyDecision(
                state=PolicyDecisionState.reject,
                reasons=[finding.message for finding in warnings],
                hard_fail=True,
                score=0.2,
                metrics=metrics,
            )

        if warnings:
            return PolicyDecision(
                state=PolicyDecisionState.warn_and_return_partial,
                reasons=[finding.message for finding in warnings],
                hard_fail=False,
                score=0.65,
                metrics=metrics,
            )

        return PolicyDecision(
            state=PolicyDecisionState.accept,
            reasons=["No blocking hallucination evidence detected in first-iteration checks."],
            hard_fail=False,
            score=0.95,
            metrics=metrics,
        )
