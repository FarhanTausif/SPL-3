import { AlertCircle, Boxes, Cpu, Library, MonitorCog, type LucideIcon } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { RunSummary } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "./StatusBadge";

export function ResultPanel({ run }: { run: RunSummary | null }) {
  if (!run) {
    return (
      <Card className="border-stone-200/80 bg-white/90 shadow-sm">
        <CardHeader className="p-4">
          <CardTitle className="text-[15px]">Run Summary</CardTitle>
          <CardDescription>Submit a prompt to start inference, generation, verification, and repair.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="border-stone-200/80 bg-white/90 shadow-sm">
      <CardHeader className="flex-row items-start justify-between gap-4 p-4 pb-3">
        <div>
          <CardTitle className="text-[15px]">Run Summary</CardTitle>
          <CardDescription className="break-all">{run.model_name}</CardDescription>
        </div>
        <StatusBadge value={run.policy_decision?.decision ?? run.status} />
      </CardHeader>
      <CardContent className="space-y-3 p-4 pt-0">
        {run.inferred.needs_clarification ? (
          <div className="rounded-lg border border-sky-200 bg-sky-50 p-3">
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-sky-900">
              <AlertCircle className="size-4" />
              Clarification Needed
            </div>
            <div className="prose-lite">
              <ReactMarkdown>{run.inferred.clarification_questions.map((question) => `- ${question}`).join("\n")}</ReactMarkdown>
            </div>
          </div>
        ) : null}

        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
          <SummaryItem icon={Cpu} label="Language" value={run.inferred.language ?? "generic"} />
          <SummaryItem icon={Boxes} label="Framework" value={run.inferred.framework ?? "none"} />
          <SummaryItem icon={MonitorCog} label="Runtime" value={run.inferred.runtime ?? "unspecified"} />
          <SummaryItem icon={Library} label="Libraries" value={run.inferred.libraries.length ? run.inferred.libraries.join(", ") : "none"} />
        </div>

        {run.inferred.uncertain_assumptions.length > 0 ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
            <p className="mb-1 text-xs font-semibold uppercase text-amber-900">Uncertain Assumptions</p>
            <div className="prose-lite">
              <ReactMarkdown>{run.inferred.uncertain_assumptions.map((item) => `- ${item}`).join("\n")}</ReactMarkdown>
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function SummaryItem({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md border border-stone-200 bg-stone-50 p-3">
      <div className="mb-1 flex items-center gap-1.5 text-xs text-stone-500">
        <Icon className="size-3.5" />
        {label}
      </div>
      <strong className="block break-words text-sm font-semibold text-stone-900">{value}</strong>
    </div>
  );
}
