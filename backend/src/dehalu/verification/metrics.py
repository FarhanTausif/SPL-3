from __future__ import annotations

from collections import Counter

from dehalu.api.schemas import Claim, MetricResult, StaticFinding


def compute_metrics(
    code: str,
    claims: list[Claim],
    findings: list[StaticFinding],
    entropy_summary: dict,
) -> MetricResult:
    hallucinated = [claim for claim in claims if claim.status in {"unsupported", "uncertain"}]
    mihn = float(len(hallucinated))
    mahr = float(len(hallucinated) / len(claims)) if claims else 0.0
    tr_s = _repetition_score(code)
    entropy_score = float(entropy_summary.get("score", 0.0) or 0.0)
    severity = sum(1.0 if item.severity == "error" else 0.5 for item in findings)
    severity_score = min(1.0, severity / 5.0)
    risk = min(1.0, (mahr * 0.4) + (tr_s * 0.2) + (severity_score * 0.3) + (entropy_score * 0.1))
    return MetricResult(
        mihn=round(mihn, 3),
        mahr=round(mahr, 3),
        tr_s=round(tr_s, 3),
        entropy_score=round(entropy_score, 3),
        hallucination_risk_score=round(risk, 3),
    )


def _repetition_score(code: str) -> float:
    lines = [line.strip() for line in code.splitlines() if line.strip()]
    if not lines:
        return 0.0
    counts = Counter(lines)
    repeated = sum(count - 1 for count in counts.values() if count > 1)
    return min(1.0, repeated / max(1, len(lines)))
