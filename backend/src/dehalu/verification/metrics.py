from collections import Counter
import re
from dehalu.domain.models import Claim, MetricResult, StaticFinding


def compute_metrics(code: str, claims: list[Claim], findings: list[StaticFinding], entropy_summary: dict) -> MetricResult:
    unsupported = sum(c.status == 'unsupported' for c in claims)
    uncertain = sum(c.status in {'uncertain', 'not_checked'} for c in claims)
    mahr = (unsupported + uncertain) / len(claims) if claims else 0.0
    entropy = entropy_summary.get('score') if entropy_summary.get('available') else None
    severity = min(1, sum({'error': 1, 'warning': .3, 'info': 0}[f.severity] for f in findings) / 5)
    repetition = _repetition_score(code)
    risk = .4 * mahr + .2 * repetition + .3 * severity + .1 * (entropy or 0)
    return MetricResult(mihn=unsupported, mahr=round(mahr, 4), tr_s=round(repetition, 4), entropy_score=entropy,
        static_severity_score=round(severity, 4), uncertainty_score=round(uncertain / len(claims), 4) if claims else 1,
        unsupported_count=unsupported, uncertain_count=uncertain, total_claims=len(claims), hallucination_risk_score=round(min(1, risk), 4))


def _repetition_score(code: str) -> float:
    lines = [line.strip() for line in code.splitlines() if line.strip() and line.strip() not in {'{', '}', 'else:', 'pass'}]
    duplicate_lines = sum(n - 1 for n in Counter(lines).values() if n > 1) / max(1, len(lines))
    tokens = re.findall(r'\w+|[^\w\s]', code)
    blocks = [tuple(tokens[i:i+12]) for i in range(0, len(tokens)-11, 12)]
    duplicate_blocks = sum(n - 1 for n in Counter(blocks).values() if n > 1) / max(1, len(blocks))
    return min(1, max(duplicate_lines, duplicate_blocks))
