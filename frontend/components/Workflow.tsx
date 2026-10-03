import { Activity, CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { StatusBadge } from "./StatusBadge";
import type { StageStatus, WorkflowStageKey } from "@/lib/api";

export type StageView = {
  key: WorkflowStageKey;
  label: string;
  status: StageStatus;
  progress: number;
  attemptNo?: number;
};

export const defaultStages: StageView[] = [
  { key: "intake", label: "Intake", status: "pending", progress: 0 },
  { key: "clarification", label: "Clarify", status: "pending", progress: 0 },
  { key: "generation", label: "Generate", status: "pending", progress: 0 },
  { key: "claim_extraction", label: "Claims", status: "pending", progress: 0 },
  { key: "tree_sitter", label: "AST", status: "pending", progress: 0 },
  { key: "semgrep", label: "SAST", status: "pending", progress: 0 },
  { key: "symbol_indexer", label: "Symbols", status: "pending", progress: 0 },
  { key: "metrics", label: "Metrics", status: "pending", progress: 0 },
  { key: "judge_pool", label: "Judges", status: "pending", progress: 0 },
  { key: "consensus", label: "Consensus", status: "pending", progress: 0 },
  { key: "cove", label: "CoVe", status: "pending", progress: 0 },
  { key: "policy", label: "Policy", status: "pending", progress: 0 },
  { key: "repair", label: "Repair", status: "pending", progress: 0 }
];

export function Workflow({ status, stages }: { status: string; stages: StageView[] }) {
  const active = stages.find((stage) => stage.status === "running");
  const doneCount = stages.filter((stage) => stage.status === "done").length;

  return (
    <Card className="overflow-hidden border-stone-200/80 bg-white/90 shadow-sm backdrop-blur">
      <CardHeader className="flex-row items-start justify-between gap-4 p-4 pb-2">
        <div>
          <CardTitle className="flex items-center gap-2 text-[15px]">
            <Activity className="size-4 text-emerald-700" />
            Workflow
          </CardTitle>
          <CardDescription>
            {active ? `${active.label} is running` : `${doneCount}/${stages.length} stages complete`}
          </CardDescription>
        </div>
        <StatusBadge value={status} />
      </CardHeader>
      <CardContent className="p-4 pt-2">
        <div className="overflow-x-auto pb-1">
          <div className="grid min-w-[920px] grid-cols-[repeat(13,minmax(0,1fr))] gap-2">
            {stages.map((stage) => (
              <StageTile key={stage.key} stage={stage} />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function StageTile({ stage }: { stage: StageView }) {
  const Icon = stage.status === "done" ? CheckCircle2 : stage.status === "failed" ? XCircle : stage.status === "running" ? Loader2 : Circle;

  return (
    <div
      className={cn(
        "min-w-0 rounded-md border bg-stone-50 p-2 transition-all",
        stage.status === "running" && "border-sky-300 bg-sky-50 shadow-[0_0_0_3px_rgba(14,165,233,0.12)]",
        stage.status === "done" && "border-emerald-200 bg-emerald-50/70",
        stage.status === "failed" && "border-red-200 bg-red-50"
      )}
    >
      <div className="mb-2 flex items-center justify-between gap-1">
        <Icon
          className={cn(
            "size-3.5 shrink-0",
            stage.status === "running" && "animate-spin text-sky-700",
            stage.status === "done" && "text-emerald-700",
            stage.status === "failed" && "text-red-700",
            stage.status === "pending" && "text-stone-400"
          )}
        />
        <span className="truncate text-[11px] font-semibold text-stone-700">{stage.label}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-stone-200">
        <div
          className={cn("h-full rounded-full transition-[width] duration-300", stage.status === "failed" ? "bg-red-600" : "bg-emerald-700")}
          style={{ width: `${Math.max(0, Math.min(stage.progress, 100))}%` }}
        />
      </div>
      <div className="mt-1 flex items-center justify-between text-[10px] text-stone-500">
        <span>{stage.progress}%</span>
        {stage.attemptNo ? <span>A{stage.attemptNo}</span> : null}
      </div>
    </div>
  );
}
