from dehalu.domain.models import Claim, CoVeResult, StaticFinding


def run_cove(claims: list[Claim], findings: list[StaticFinding]) -> list[CoVeResult]:
    results = []
    for claim in claims:
        linked = [f for f in findings if claim.id in f.claim_ids]
        contradictory = any(f.severity == 'error' for f in linked)
        verdict = 'unsupported' if contradictory else claim.status if claim.status in {'supported', 'unsupported'} and claim.evidence else 'uncertain'
        results.append(CoVeResult(claim_id=claim.id, verification_question=f"What evidence confirms {claim.claim_type}: {claim.claim_text}?",
            verdict=verdict, evidence=claim.evidence or 'No direct supporting evidence is available.',
            evidence_ids=list(dict.fromkeys(claim.evidence_ids + [f.id for f in linked])), confidence=.95 if verdict != 'uncertain' else 0))
    return results


def merge_semantic_checks(claims, results, checks, findings, extra_evidence_ids=()):
    """Accept semantic support only with existing evidence IDs; never override contradiction."""
    by_id = {c.id: c for c in claims}
    allowed = set(extra_evidence_ids) | {f.id for f in findings} | {c.id for c in claims if c.status == 'supported' and c.evidence}
    indexed = {r.claim_id: r for r in results}
    for raw in checks:
        check = CoVeResult.model_validate(raw)
        claim = by_id.get(check.claim_id)
        prior = indexed.get(check.claim_id)
        if not claim or not prior or prior.verdict == 'unsupported': continue
        if claim.claim_type not in {'behavior', 'runtime', 'assumption', 'safety'}: continue
        if check.verdict != 'uncertain' and (not check.evidence_ids or not set(check.evidence_ids) <= allowed): continue
        indexed[check.claim_id] = check
        claim.status = check.verdict
        claim.evidence = check.evidence
        claim.evidence_ids = check.evidence_ids
    return list(indexed.values())
