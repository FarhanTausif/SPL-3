"use client";
import { CheckCircle2, ChevronDown, Circle, Loader2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { StatusBadge } from "./StatusBadge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./ui/collapsible";
import type { StageStatus, WorkflowStageKey } from "@/lib/api";
export type StageView = {
  key: WorkflowStageKey;
  label: string;
  status: StageStatus;
  progress: number;
  attemptNo?: number;
};
export const defaultStages: StageView[] = [
  ["intake", "Intake"],
  ["clarification", "Clarification"],
  ["generation", "Generation"],
  ["claim_extraction", "Claims"],
  ["tree_sitter", "Parsing"],
  ["semgrep", "Safety scan"],
  ["symbol_indexer", "Symbols & APIs"],
  ["metrics", "Metrics"],
  ["judge_pool", "Judge pool"],
  ["consensus", "Consensus"],
  ["cove", "Chain of verification"],
  ["policy", "Policy"],
  ["repair", "Repair"]
].map(([key, label]) => ({ key: key as WorkflowStageKey, label, status: "pending", progress: 0 }));
const groups: { label: string; keys: WorkflowStageKey[] }[] = [
  { label: "Intake", keys: ["intake", "clarification"] },
  { label: "Generation", keys: ["generation"] },
  {
    label: "Static checks",
    keys: ["claim_extraction", "tree_sitter", "semgrep", "symbol_indexer", "metrics"]
  },
  { label: "Judges", keys: ["judge_pool", "consensus"] },
  { label: "Verification", keys: ["cove"] },
  { label: "Decision", keys: ["policy"] }
];
export function Workflow({ status, stages }: { status: string; stages: StageView[] }) {
  const active = stages.find((s) => s.status === "running");
  const iteration = Math.max(1, ...stages.map((s) => s.attemptNo ?? 1));
  return (
    <section aria-label="Verification workflow" className="border-b bg-card px-4 py-3 sm:px-6">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <span>
          {active
            ? `${active.label} in progress`
            : status === "queued"
              ? "Queued · waiting for a worker"
              : status === "completed" || status === "rejected"
                ? "Verification finished"
                : status === "idle"
                  ? "Generation and verification"
                  : `Run ${status.replace(/_/g, " ")}`}
        </span>
        <span className="font-mono">
          Attempt {iteration}
          {iteration > 1 ? ` · repair ${iteration - 1}` : ""}
        </span>
      </div>
      <div className="overflow-x-auto pb-1">
        <div className="flex min-w-[680px] gap-2">
          {groups.map((group) => {
            const underlying = stages.filter((s) => group.keys.includes(s.key));
            const required = underlying.filter(
              (s) => s.key !== "clarification" || s.status !== "pending"
            );
            const groupStatus = required.some((s) => s.status === "failed")
              ? "failed"
              : required.some((s) => s.status === "running")
                ? "running"
                : required.every((s) => s.status === "done")
                  ? "done"
                  : "pending";
            const Icon =
              groupStatus === "done"
                ? CheckCircle2
                : groupStatus === "running"
                  ? Loader2
                  : groupStatus === "failed"
                    ? XCircle
                    : Circle;
            return (
              <Collapsible key={group.label} className="min-w-0 flex-1">
                <CollapsibleTrigger
                  className={cn(
                    "flex w-full items-center justify-between gap-2 rounded-md px-2 py-2 text-xs font-medium hover:bg-muted",
                    groupStatus === "running" && "bg-active-surface text-active",
                    groupStatus === "done" && "text-good",
                    groupStatus === "failed" && "text-danger"
                  )}
                >
                  <span className="flex items-center gap-2">
                    <Icon
                      className={cn("size-4 shrink-0", groupStatus === "running" && "animate-spin")}
                    />
                    {group.label}
                  </span>
                  <ChevronDown className="size-3 shrink-0" />
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-2 space-y-2 text-xs">
                  {underlying.map((s) => (
                    <div key={s.key} className="space-y-1">
                      <span className="block text-muted-foreground">{s.label}</span>
                      <StatusBadge
                        value={
                          s.key === "clarification" && s.status === "pending"
                            ? "not required"
                            : s.status
                        }
                        compact
                      />
                      {s.status === "running" && (
                        <span className="ml-1 font-mono">{s.progress}%</span>
                      )}
                    </div>
                  ))}
                </CollapsibleContent>
              </Collapsible>
            );
          })}
        </div>
      </div>
      {active?.key === "repair" && (
        <p className="mt-2 text-xs text-warning">Preparing evidence-constrained repair</p>
      )}
    </section>
  );
}
