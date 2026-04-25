from __future__ import annotations

from dehalu.schemas import (
    CoVeCheckVerdict,
    CoVeClaimCheck,
    CoVeFinding,
    CoVeResult,
    CoVeVerdict,
    ExtractedClaim,
    StaticFindingSeverity,
)


def claim_to_question(claim: ExtractedClaim) -> str:
    if claim.kind == "dependency":
        return f"Does the generated output actually depend on '{claim.value}'?"
    if claim.kind == "import":
        return f"Does the code import '{claim.value}'?"
    if claim.kind == "symbol":
        return f"Does the code use or define the symbol '{claim.value}'?"
    if claim.kind == "assumption":
        return f"Is the assumption '{claim.value}' supported by the generated output?"
    return "Is this claim supported by the generated output?"


def build_cove_summary_findings(checks: list[CoVeClaimCheck]) -> list[CoVeFinding]:
    findings: list[CoVeFinding] = []
    for check in checks:
        if check.verdict == CoVeCheckVerdict.unsupported:
            findings.append(
                CoVeFinding(
                    code="cove_unsupported_claim",
                    message=f"CoVe could not support claim: {check.claim}",
                    severity=StaticFindingSeverity.error,
                    claim=check.claim,
                    metadata={"question": check.question, **check.metadata},
                )
            )
        elif check.verdict == CoVeCheckVerdict.uncertain:
            findings.append(
                CoVeFinding(
                    code="cove_uncertain_claim",
                    message=f"CoVe could not verify claim with confidence: {check.claim}",
                    severity=StaticFindingSeverity.warning,
                    claim=check.claim,
                    metadata={"question": check.question, **check.metadata},
                )
            )
    return findings


def build_cove_result(
    *,
    provider: str,
    model: str,
    duration_ms: float,
    checks: list[CoVeClaimCheck],
    extra_findings: list[CoVeFinding] | None = None,
    hallucination_score: float | None = None,
) -> CoVeResult:
    extra_findings = extra_findings or []
    findings = [*build_cove_summary_findings(checks), *extra_findings]
    unsupported_count = sum(
        1 for check in checks if check.verdict == CoVeCheckVerdict.unsupported
    )
    uncertain_count = sum(
        1 for check in checks if check.verdict == CoVeCheckVerdict.uncertain
    )
    supported_count = sum(
        1 for check in checks if check.verdict == CoVeCheckVerdict.supported
    )

    error_findings = [
        finding for finding in findings if finding.severity == StaticFindingSeverity.error
    ]
    warning_findings = [
        finding for finding in findings if finding.severity == StaticFindingSeverity.warning
    ]

    if error_findings or unsupported_count:
        verdict = CoVeVerdict.fail
        default_score = 0.9
    elif warning_findings or uncertain_count:
        verdict = CoVeVerdict.uncertain
        default_score = 0.55
    else:
        verdict = CoVeVerdict.pass_
        default_score = 0.05

    return CoVeResult(
        verdict=verdict,
        provider=provider,
        model=model,
        duration_ms=round(duration_ms, 3),
        hallucination_score=default_score if hallucination_score is None else hallucination_score,
        checks=checks,
        findings=findings,
        metrics={
            "supported_claim_count": supported_count,
            "unsupported_claim_count": unsupported_count,
            "uncertain_claim_count": uncertain_count,
            "check_count": len(checks),
        },
    )
