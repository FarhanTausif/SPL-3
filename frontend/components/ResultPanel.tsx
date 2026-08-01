import type { RunSummary } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

export function ResultPanel({ run }: { run: RunSummary | null }) {
  if (!run) {
    return (
      <section className="panel empty">
        <h2>Result</h2>
      </section>
    );
  }
  return (
    <section className="panel result">
      <div className="panelHeader">
        <h2>Result</h2>
        <StatusBadge value={run.policy_decision?.decision ?? run.status} />
      </div>
      {run.inferred.needs_clarification ? (
        <div className="notice">
          {run.inferred.clarification_questions.map((question) => (
            <p key={question}>{question}</p>
          ))}
        </div>
      ) : null}
      <div className="assumptions">
        <span>Language: {run.inferred.language ?? "generic"}</span>
        <span>Framework: {run.inferred.framework ?? "none"}</span>
        <span>Runtime: {run.inferred.runtime ?? "unspecified"}</span>
      </div>
      {run.inferred.uncertain_assumptions.length > 0 ? (
        <div className="notice subtle">
          {run.inferred.uncertain_assumptions.map((item) => (
            <p key={item}>{item}</p>
          ))}
        </div>
      ) : null}
      <pre className="code">{run.final_output?.code ?? "No generated code yet."}</pre>
    </section>
  );
}
