import type { RunEvidence } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

export function EvidencePanel({ evidence }: { evidence: RunEvidence | null }) {
  if (!evidence) {
    return (
      <section className="panel empty">
        <h2>Evidence</h2>
      </section>
    );
  }
  const latest = evidence.attempts[evidence.attempts.length - 1];
  return (
    <section className="panel evidence">
      <div className="panelHeader">
        <h2>Evidence</h2>
        <span>{evidence.attempts.length} attempt(s)</span>
      </div>
      <div className="grid two">
        <div>
          <h3>Claims</h3>
          <div className="list">
            {latest.claims.map((claim, index) => (
              <div className="row" key={`${claim.claim_text}-${index}`}>
                <StatusBadge value={claim.status} />
                <span>{claim.claim_type}</span>
                <code>{claim.claim_text}</code>
                <small>{claim.location}</small>
              </div>
            ))}
          </div>
        </div>
        <div>
          <h3>Static Findings</h3>
          <div className="list">
            {latest.static_findings.map((finding, index) => (
              <div className="row" key={`${finding.rule_id}-${index}`}>
                <StatusBadge value={finding.severity} />
                <span>{finding.rule_id}</span>
                <small>{finding.message}</small>
              </div>
            ))}
            {latest.static_findings.length === 0 ? <p className="muted">No static findings.</p> : null}
          </div>
        </div>
      </div>
      <div className="grid three">
        <Metric label="MiHN" value={latest.metrics.mihn} />
        <Metric label="MaHR" value={latest.metrics.mahr} />
        <Metric label="TR-S" value={latest.metrics.tr_s} />
        <Metric label="Entropy" value={latest.metrics.entropy_score} />
        <Metric label="Risk" value={latest.metrics.hallucination_risk_score} />
        <Metric label="Judge Avg" value={latest.judge_consensus.average_score} />
      </div>
      <div className="grid two">
        <div>
          <h3>Judges</h3>
          {latest.judge_results.map((judge) => (
            <div className="row" key={judge.judge_name}>
              <StatusBadge value={judge.verdict} />
              <span>{judge.judge_name}</span>
              <small>{judge.explanation}</small>
            </div>
          ))}
        </div>
        <div>
          <h3>Policy</h3>
          <div className="row">
            <StatusBadge value={latest.policy.decision} />
            <span>{latest.policy.reason}</span>
          </div>
          <h3>CoVe</h3>
          {latest.cove_results.slice(0, 6).map((item, index) => (
            <div className="row" key={index}>
              <StatusBadge value={item.verdict} />
              <small>{item.evidence}</small>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{Number(value).toFixed(2)}</strong>
    </div>
  );
}
