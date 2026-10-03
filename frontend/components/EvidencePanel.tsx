"use client";

import { Activity, Bot, FileSearch, Gauge, Info, ListChecks, ShieldCheck, WandSparkles, type LucideIcon } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { RunEvidence } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { StatusBadge } from "./StatusBadge";

const metricHelp: Record<string, string> = {
  MiHN: "Micro Hallucination Number: count of invalid, unsupported, or suspicious low-level claims found in the output.",
  MaHR: "Macro Hallucination Rate: proportion of extracted claims that appear hallucinated or unsupported.",
  "TR-S": "Token Repetition Score: detects repetitive or degenerated output patterns.",
  Entropy: "Provider uncertainty signal when available. Ollama currently returns this as unavailable unless metadata is supplied.",
  Risk: "Combined hallucination risk score used by the policy gateway.",
  "Judge Avg": "Average confidence score across Gemini, Groq, and Mistral judge results."
};

export function EvidencePanel({ evidence }: { evidence: RunEvidence | null }) {
  if (!evidence) {
    return (
      <Card className="border-stone-200/80 bg-white/90 shadow-sm">
        <CardHeader className="p-5">
          <CardTitle className="flex items-center gap-2">
            <FileSearch className="size-4 text-emerald-700" />
            Evidence
          </CardTitle>
          <CardDescription>Claims, findings, metrics, judge results, CoVe, and policy will appear after verification.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const latest = evidence.attempts[evidence.attempts.length - 1];

  return (
    <TooltipProvider delayDuration={120}>
      <Card className="border-stone-200/80 bg-white/90 shadow-sm">
        <CardHeader className="flex-row items-start justify-between gap-4 p-5 pb-3">
          <div>
            <CardTitle className="flex items-center gap-2">
              <FileSearch className="size-4 text-emerald-700" />
              Evidence
            </CardTitle>
            <CardDescription>{evidence.attempts.length} attempt(s) recorded for this run</CardDescription>
          </div>
          <StatusBadge value={latest.policy.decision} />
        </CardHeader>
        <CardContent className="p-5 pt-0">
          <Tabs defaultValue="claims" className="w-full">
            <TabsList className="h-auto w-full justify-start overflow-x-auto rounded-md bg-stone-100 p-1">
              <Tab value="claims" label="Claims" icon={ListChecks} />
              <Tab value="static" label="Static" icon={FileSearch} />
              <Tab value="metrics" label="Metrics" icon={Gauge} />
              <Tab value="judges" label="Judges" icon={Bot} />
              <Tab value="cove" label="CoVe" icon={ShieldCheck} />
              <Tab value="policy" label="Policy" icon={Activity} />
              <Tab value="attempts" label="Attempts" icon={WandSparkles} />
            </TabsList>

            <TabsContent value="claims">
              <EvidenceList
                empty="No claims extracted."
                rows={latest.claims.map((claim) => ({
                  status: claim.status,
                  title: claim.claim_type,
                  body: claim.claim_text,
                  meta: claim.location
                }))}
              />
            </TabsContent>

            <TabsContent value="static">
              <EvidenceList
                empty="No static findings."
                rows={latest.static_findings.map((finding) => ({
                  status: finding.severity,
                  title: finding.rule_id,
                  body: finding.message,
                  meta: `${finding.location || "snippet"} · ${finding.evidence_source}`
                }))}
              />
            </TabsContent>

            <TabsContent value="metrics">
              <MetricsTable attempts={evidence.attempts} />
            </TabsContent>

            <TabsContent value="judges">
              <EvidenceList
                empty="No judge results."
                rows={latest.judge_results.map((judge) => ({
                  status: judge.verdict,
                  title: `${judge.judge_name} · ${judge.score.toFixed(2)}`,
                  body: judge.explanation,
                  meta: judge.judge_model
                }))}
              />
            </TabsContent>

            <TabsContent value="cove">
              <EvidenceList
                empty="No CoVe results."
                rows={latest.cove_results.map((item) => ({
                  status: item.verdict,
                  title: `Confidence ${item.confidence.toFixed(2)}`,
                  body: item.evidence,
                  meta: item.claim_id ?? "claim pending"
                }))}
              />
            </TabsContent>

            <TabsContent value="policy">
              <div className="rounded-lg border border-stone-200 bg-stone-50 p-4">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <StatusBadge value={latest.policy.decision} />
                  <span className="text-sm font-semibold text-stone-800">Policy Decision</span>
                </div>
                <MarkdownText value={latest.policy.reason} />
                <div className="mt-4 border-t border-stone-200 pt-3">
                  <p className="text-xs font-semibold uppercase text-stone-500">Consensus</p>
                  <MarkdownText value={latest.judge_consensus.summary} />
                </div>
              </div>
            </TabsContent>

            <TabsContent value="attempts">
              <EvidenceList
                empty="No attempts."
                rows={evidence.attempts.map((attempt) => ({
                  status: attempt.policy.decision,
                  title: `Attempt ${attempt.output.attempt_no}`,
                  body: attempt.output.explanation || attempt.policy.reason,
                  meta: `${attempt.output.provider} · risk ${attempt.metrics.hallucination_risk_score.toFixed(2)}`
                }))}
              />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </TooltipProvider>
  );
}

function Tab({ value, label, icon: Icon }: { value: string; label: string; icon: LucideIcon }) {
  return (
    <TabsTrigger value={value} className="shrink-0">
      <Icon className="size-3.5" />
      {label}
    </TabsTrigger>
  );
}

function EvidenceList({
  rows,
  empty
}: {
  rows: Array<{ status: string; title: string; body: string; meta?: string }>;
  empty: string;
}) {
  if (rows.length === 0) return <p className="rounded-lg border border-dashed border-stone-200 p-6 text-sm text-stone-500">{empty}</p>;
  return (
    <div className="grid gap-3">
      {rows.map((row, index) => (
        <div className="grid gap-3 rounded-lg border border-stone-200 bg-stone-50 p-3 sm:grid-cols-[max-content_minmax(0,1fr)]" key={`${row.title}-${index}`}>
          <StatusBadge value={row.status} />
          <div className="min-w-0">
            <strong className="block truncate text-sm text-stone-900">{row.title}</strong>
            <MarkdownText value={row.body} />
            {row.meta ? <p className="mt-1 break-words text-xs text-stone-500">{row.meta}</p> : null}
          </div>
        </div>
      ))}
    </div>
  );
}

function MarkdownText({ value }: { value: string }) {
  return (
    <div className="prose-lite">
      <ReactMarkdown>{value || "No details provided."}</ReactMarkdown>
    </div>
  );
}

function MetricsTable({ attempts }: { attempts: RunEvidence["attempts"] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-stone-200">
      <table className="w-full min-w-[760px] border-collapse text-left text-sm">
        <thead className="bg-stone-100 text-xs uppercase text-stone-500">
          <tr>
            <th className="px-3 py-2 font-semibold">Attempt</th>
            <MetricHeader label="MiHN" />
            <MetricHeader label="MaHR" />
            <MetricHeader label="TR-S" />
            <MetricHeader label="Entropy" />
            <MetricHeader label="Risk" />
            <MetricHeader label="Judge Avg" />
            <th className="px-3 py-2 font-semibold">Policy</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-200 bg-white">
          {attempts.map((attempt) => (
            <tr className="transition hover:bg-stone-50" key={attempt.output.attempt_no}>
              <td className="px-3 py-3 font-semibold text-stone-900">Attempt {attempt.output.attempt_no}</td>
              <MetricCell value={attempt.metrics.mihn} />
              <MetricCell value={attempt.metrics.mahr} />
              <MetricCell value={attempt.metrics.tr_s} />
              <MetricCell value={attempt.metrics.entropy_score} />
              <MetricCell value={attempt.metrics.hallucination_risk_score} />
              <MetricCell value={attempt.judge_consensus.average_score} />
              <td className="px-3 py-3">
                <StatusBadge value={attempt.policy.decision} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MetricHeader({ label }: { label: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <th className="cursor-help px-3 py-2 font-semibold">
          <span className="inline-flex items-center gap-1">
            {label}
            <Info className="size-3 text-stone-400" />
          </span>
        </th>
      </TooltipTrigger>
      <TooltipContent>{metricHelp[label]}</TooltipContent>
    </Tooltip>
  );
}

function MetricCell({ value }: { value: number }) {
  return <td className="px-3 py-3 tabular-nums text-stone-700">{Number(value).toFixed(2)}</td>;
}
