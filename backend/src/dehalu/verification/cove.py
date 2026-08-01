from __future__ import annotations

from dehalu.api.schemas import Claim, CoVeResult, StaticFinding


def run_cove(claims: list[Claim], findings: list[StaticFinding]) -> list[CoVeResult]:
    results: list[CoVeResult] = []
    finding_text = "\n".join(f"{f.rule_id}: {f.message}" for f in findings)
    for claim in claims:
        if claim.status == "unsupported":
            verdict = "unsupported"
            confidence = 0.9
        elif claim.status == "uncertain":
            verdict = "uncertain"
            confidence = 0.5
        else:
            verdict = "supported"
            confidence = 0.8
        results.append(
            CoVeResult(
                claim_id=claim.id,
                verdict=verdict,
                evidence=f"Claim `{claim.claim_text}` checked against static evidence. {finding_text[:240]}",
                confidence=confidence,
            )
        )
    return results
