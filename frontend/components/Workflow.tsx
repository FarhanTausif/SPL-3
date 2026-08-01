import { StatusBadge } from "./StatusBadge";

const stages = [
  "Intake",
  "Clarification",
  "Generation",
  "Claim Extraction",
  "Tree-sitter",
  "Semgrep/SAST",
  "Symbol Indexer",
  "Metrics",
  "Judge Pool",
  "Consensus",
  "CoVe",
  "Policy",
  "Repair"
];

export function Workflow({ status }: { status: string }) {
  return (
    <section className="panel">
      <div className="panelHeader">
        <h2>Workflow</h2>
        <StatusBadge value={status} />
      </div>
      <div className="workflow">
        {stages.map((stage) => (
          <div key={stage} className="stage">
            <span>{stage}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
