from __future__ import annotations

from dehalu.schemas import (
    CoVeResult,
    CoVeVerdict,
    JudgeResult,
    JudgeVerdict,
    PolicyDecision,
    PolicyDecisionState,
    RepairTrigger,
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
        judge_result: JudgeResult | None = None,
        cove_result: CoVeResult | None = None,
        allow_repair: bool = True,
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
        if judge_result:
            metrics["judge_verdict"] = judge_result.verdict.value
            metrics["judge_hallucination_score"] = judge_result.hallucination_score
        if cove_result:
            metrics["cove_verdict"] = cove_result.verdict.value
            metrics["cove_hallucination_score"] = cove_result.hallucination_score
            metrics["supported_claim_count"] = cove_result.metrics.get("supported_claim_count", 0)
            metrics["unsupported_claim_count"] = cove_result.metrics.get("unsupported_claim_count", 0)
            metrics["uncertain_claim_count"] = cove_result.metrics.get("uncertain_claim_count", 0)

        if errors:
            return PolicyDecision(
                state=PolicyDecisionState.reject,
                reasons=[finding.message for finding in errors],
                hard_fail=True,
                score=0.0,
                metrics=metrics,
            )

        if judge_result and judge_result.verdict == JudgeVerdict.fail:
            if allow_repair:
                metrics["repair_trigger"] = RepairTrigger.judge_fail.value
                return PolicyDecision(
                    state=PolicyDecisionState.repair_and_retry,
                    reasons=[finding.message for finding in judge_result.findings]
                    or ["Judge detected hallucination risk."],
                    hard_fail=False,
                    score=max(0.0, 1.0 - judge_result.hallucination_score),
                    metrics=metrics,
                )
            return PolicyDecision(
                state=PolicyDecisionState.reject,
                reasons=[finding.message for finding in judge_result.findings]
                or ["Judge detected hallucination risk."],
                hard_fail=True,
                score=max(0.0, 1.0 - judge_result.hallucination_score),
                metrics=metrics,
            )

        if cove_result and cove_result.verdict == CoVeVerdict.fail:
            if allow_repair:
                metrics["repair_trigger"] = RepairTrigger.cove_fail.value
                return PolicyDecision(
                    state=PolicyDecisionState.repair_and_retry,
                    reasons=[finding.message for finding in cove_result.findings]
                    or ["CoVe detected unsupported claims in the output."],
                    hard_fail=False,
                    score=max(0.0, 1.0 - cove_result.hallucination_score),
                    metrics=metrics,
                )
            return PolicyDecision(
                state=PolicyDecisionState.reject,
                reasons=[finding.message for finding in cove_result.findings]
                or ["CoVe detected unsupported claims in the output."],
                hard_fail=True,
                score=max(0.0, 1.0 - cove_result.hallucination_score),
                metrics=metrics,
            )

        prompt_warnings: list[str] = []
        prompt_trigger: RepairTrigger | None = None
        if judge_result and judge_result.verdict == JudgeVerdict.uncertain:
            if prompt_trigger is None:
                prompt_trigger = RepairTrigger.judge_uncertain
            prompt_warnings.extend(
                [finding.message for finding in judge_result.findings]
                or ["Judge could not verify the output with confidence."]
            )
        if cove_result and cove_result.verdict == CoVeVerdict.uncertain:
            if prompt_trigger is None:
                prompt_trigger = RepairTrigger.cove_uncertain
            prompt_warnings.extend(
                [finding.message for finding in cove_result.findings]
                or ["CoVe could not verify one or more claims with confidence."]
            )

        if prompt_warnings:
            if allow_repair and prompt_trigger is not None:
                metrics["repair_trigger"] = prompt_trigger.value
                return PolicyDecision(
                    state=PolicyDecisionState.repair_and_retry,
                    reasons=prompt_warnings,
                    hard_fail=False,
                    score=0.65,
                    metrics=metrics,
                )
            if risk_level == RiskLevel.high:
                return PolicyDecision(
                    state=PolicyDecisionState.reject,
                    reasons=prompt_warnings,
                    hard_fail=True,
                    score=0.2,
                    metrics=metrics,
                )
            return PolicyDecision(
                state=PolicyDecisionState.warn_and_return_partial,
                reasons=prompt_warnings,
                hard_fail=False,
                score=0.65,
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
