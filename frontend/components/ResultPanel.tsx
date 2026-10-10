import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import type { RunSummary, PolicyDecision } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";
import { MarkdownText } from "./MarkdownText";
import { cn } from "@/lib/utils";
export function ResultPanel({
  run,
  policy
}: {
  run: RunSummary | null;
  policy?: PolicyDecision | null;
}) {
  if (!run) return null;
  const decision = policy === undefined ? run.policy_decision : policy;
  const Icon =
    decision?.decision === "accept"
      ? CheckCircle2
      : decision?.decision === "reject" || run.status === "failed"
        ? XCircle
        : decision?.decision === "warn" || run.status === "interrupted"
          ? AlertTriangle
          : Info;
  return (
    <section
      aria-label="Run outcome"
      className={cn(
        "flex items-start gap-3 rounded-lg border p-4",
        decision?.decision === "warn" || run.status === "interrupted"
          ? "border-amber-200 bg-warning-surface"
          : decision?.decision === "reject" || run.status === "failed"
            ? "border-red-200 bg-danger-surface"
            : decision?.decision === "accept"
              ? "border-emerald-200 bg-good-surface"
              : "bg-card"
      )}
    >
      <Icon className="mt-1 size-4 shrink-0" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-sm font-semibold">
            {run.status === "failed"
              ? "Run failed"
              : decision
                ? "Verification decision"
                : "Run status"}
          </h2>
          <StatusBadge
            value={run.status === "failed" ? "failed" : (decision?.decision ?? run.status)}
          />
        </div>
        <div className="mt-1 text-sm">
          <MarkdownText>
            {run.error ||
              decision?.reason ||
              (run.status === "queued"
                ? "Your run is queued. Generation starts when a worker is available."
                : run.status === "needs_clarification"
                  ? "Answer the questions below to continue this run."
                  : run.status === "cancelled"
                    ? "This run was cancelled. Completed evidence is preserved."
                    : run.status === "interrupted"
                      ? "The worker stopped before finishing. Saved evidence is preserved; start a new run to retry."
                      : "Generating code and collecting verification evidence.")}
          </MarkdownText>
        </div>
      </div>
    </section>
  );
}
