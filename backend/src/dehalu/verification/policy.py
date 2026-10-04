from dehalu.domain.models import AnalyzerCoverage, CoVeResult, JudgeConsensus, MetricResult, PolicyDecision, StaticFinding


def decide_policy(findings: list[StaticFinding], metrics: MetricResult, consensus: JudgeConsensus,
                  cove: list[CoVeResult], *, can_repair: bool, coverage: list[AnalyzerCoverage] | None = None) -> PolicyDecision:
    blockers = [f for f in findings if f.severity == 'error']
    contradictions = [c for c in cove if c.verdict == 'unsupported']
    if blockers or contradictions or consensus.final_verdict == 'fail':
        return PolicyDecision(decision='repair' if can_repair else 'reject',
            reason='Blocking static/claim evidence or majority semantic failure remains.' + (' Repair attempts remain.' if can_repair else ' No further repairs allowed.'),
            evidence_ids=[f.id for f in blockers])
    incomplete = any(c.status != 'available' for c in (coverage or []))
    uncertain = any(c.verdict == 'uncertain' for c in cove)
    if incomplete or uncertain or not cove or consensus.valid_count < 3 or consensus.final_verdict != 'pass' or any(f.severity == 'warning' for f in findings) or metrics.tr_s >= .3:
        return PolicyDecision(decision='warn', reason='No blocking contradiction found; uncertainty, limited coverage, quality findings or incomplete/disagreeing judges remain.')
    return PolicyDecision(decision='accept', reason='Material claims are supported, configured checks completed, and all three judges pass.')


def consensus_from_judges(judges) -> JudgeConsensus:
    valid = [j for j in judges if j.status == 'ok' and j.verdict is not None and j.score is not None]
    verdicts = [j.verdict for j in valid]
    final = 'fail' if verdicts.count('fail') >= 2 else 'pass' if len(valid) == 3 and all(v == 'pass' for v in verdicts) else 'warn'
    agreement = 'none' if not valid else 'high' if len(set(verdicts)) == 1 else 'medium' if len(set(verdicts)) == 2 else 'low'
    return JudgeConsensus(final_verdict=final, average_score=round(sum(j.score for j in valid) / len(valid), 4) if valid else None,
        agreement_level=agreement, valid_count=len(valid), summary=f"{len(valid)}/3 valid judges: {', '.join(verdicts) or 'none'}. Missing/simulated results do not establish support.")
