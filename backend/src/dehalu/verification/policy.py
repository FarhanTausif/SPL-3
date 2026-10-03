from __future__ import annotations

from dehalu.api.schemas import CoVeResult, JudgeConsensus, MetricResult, PolicyDecision, StaticFinding


def decide_policy(
    findings: list[StaticFinding],
    metrics: MetricResult,
    consensus: JudgeConsensus,
    cove: list[CoVeResult],
    *,
    can_repair: bool,
) -> PolicyDecision:
    blocking = [f for f in findings if f.severity == "error"]
    unsupported = [item for item in cove if item.verdict == "unsupported"]
    uncertain = [item for item in cove if item.verdict == "uncertain"]
    hard_blocking = [
        f
        for f in blocking
        if f.rule_id.startswith("tree-sitter.")
        or f.rule_id in {"symbol-indexer.api-conflict", "symbol-indexer.unresolved-import"}
        or f.rule_id == "semgrep.unsafe-shell"
    ]

    if hard_blocking or unsupported or metrics.hallucination_risk_score >= 0.65 or consensus.final_verdict == "fail":
        if can_repair:
            return PolicyDecision(
                decision="repair",
                reason="Blocking hallucination evidence was found and repair attempts remain.",
            )
        if not hard_blocking and not unsupported and metrics.hallucination_risk_score < 0.85:
            return PolicyDecision(
                decision="warn",
                reason="Risk remains after retry limit, but no hard static hallucination blocker remains.",
            )
        return PolicyDecision(
            decision="reject",
            reason="Blocking hallucination evidence remains after retry limit was reached.",
        )
    if blocking or uncertain or metrics.hallucination_risk_score >= 0.3 or consensus.final_verdict == "warn":
        if can_repair:
            return PolicyDecision(
                decision="repair",
                reason="Warning-level hallucination evidence was found and repair attempts remain.",
            )
        return PolicyDecision(decision="warn", reason="Non-blocking uncertain evidence remains.")
    return PolicyDecision(decision="accept", reason="No blocking hallucination evidence detected.")


def consensus_from_judges(judges) -> JudgeConsensus:
    if not judges:
        return JudgeConsensus(final_verdict="warn", average_score=0.5, agreement_level="none", summary="No judges ran.")
    avg = sum(j.score for j in judges) / len(judges)
    verdicts = [j.verdict for j in judges]
    final = "fail" if verdicts.count("fail") >= 2 else "warn" if "warn" in verdicts or "fail" in verdicts else "pass"
    agreement = "high" if len(set(verdicts)) == 1 else "medium" if len(set(verdicts)) == 2 else "low"
    return JudgeConsensus(
        final_verdict=final,
        average_score=round(avg, 3),
        agreement_level=agreement,
        summary=f"Judge pool verdicts: {', '.join(verdicts)}.",
    )
