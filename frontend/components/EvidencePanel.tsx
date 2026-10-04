"use client";
import { useEffect, useState } from "react";
import { ArrowUpRight, ChevronDown, Info, Search } from "lucide-react";
import type { RunEvidence, AttemptEvidence } from "@/lib/api";
import type { Claim, StaticFinding } from "@/lib/contracts.generated";
import { MarkdownText } from "./MarkdownText";
import { StatusBadge } from "./StatusBadge";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./ui/collapsible";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "./ui/table";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./ui/tooltip";
export type SourceLocation = { attempt: number; start: number; end: number };
const help: Record<string, string> = {
  MiHN: "Number of unsupported claims. Lower is better.",
  MaHR: "Fraction of unsupported and uncertain claims. Lower is better; zero claims does not establish coverage.",
  "TR-S": "Structural repetition score. Lower indicates less repetition.",
  Entropy: "Measured model uncertainty, available only when the generator supplies suitable data.",
  Risk: "Comparative evidence-based risk score. This is not a probability of incorrect code.",
  "Judge average": "Average score across valid judge responses, from 0 to 1. Higher is better."
};
const format = (value: number | null | undefined) =>
  value == null ? "Unavailable" : Number(value).toFixed(2);
export function selectedEvidence(
  evidence: RunEvidence,
  number: number | null
): Partial<AttemptEvidence> | undefined {
  const partial = evidence.partial as Partial<AttemptEvidence>;
  const latestNumber = Math.max(
    0,
    ...evidence.attempts.map((a) => a.output.attempt_no),
    partial.output?.attempt_no ?? 0
  );
  const target = number ?? latestNumber;
  return (
    evidence.attempts.find((a) => a.output.attempt_no === target) ??
    (partial.output?.attempt_no === target ? partial : undefined)
  );
}
export function EvidencePanel({
  evidence,
  selectedAttempt = null,
  onSource
}: {
  evidence: RunEvidence | null;
  selectedAttempt?: number | null;
  onSource?: (location: SourceLocation) => void;
}) {
  const [tab, setTab] = useState("overview");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [focused, setFocused] = useState<string | null>(null);
  const current = evidence ? selectedEvidence(evidence, selectedAttempt) : undefined;
  const number = current?.output?.attempt_no ?? selectedAttempt ?? 1;
  useEffect(() => {
    setQuery("");
    setFilter("all");
  }, [tab, number]);
  useEffect(() => {
    setFocused(null);
  }, [number]);
  useEffect(() => {
    if (!focused) return;
    const frame = requestAnimationFrame(() => {
      const el = document.getElementById(`evidence-${focused}`);
      el?.scrollIntoView({ block: "center", behavior: "auto" });
      el?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(frame);
  }, [focused, tab]);
  if (!evidence)
    return (
      <Empty
        title="No evidence yet"
        text="Claims, findings, metrics, and judge results appear as verification proceeds."
      />
    );
  const partial = evidence.partial as Partial<AttemptEvidence>;
  const data = current ?? (!evidence.attempts.length ? partial : {});
  const claims = data.claims ?? [];
  const findings = data.static_findings ?? [];
  const go = (id: string) => {
    if (claims.some((c) => c.id === id)) {
      setTab("claims");
      setFocused(id);
    } else if (findings.some((f) => f.id === id)) {
      setTab("findings");
      setFocused(id);
    } else if (data.output?.id === id) onSource?.({ attempt: number, start: 1, end: 1 });
  };
  const links = (ids: string[]) => (
    <div className="mt-2 flex flex-wrap gap-2">
      {ids.map((id) =>
        claims.some((c) => c.id === id) ||
        findings.some((f) => f.id === id) ||
        data.output?.id === id ? (
          <Button
            key={id}
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-xs text-primary"
            onClick={() => go(id)}
          >
            Evidence {id.slice(0, 8)}
            <ArrowUpRight className="size-3" />
          </Button>
        ) : (
          <span key={id} className="font-mono text-xs text-muted-foreground">
            Reference {id.slice(0, 8)} · unavailable
          </span>
        )
      )}
    </div>
  );
  const matches = (row: Claim | StaticFinding) =>
    (("status" in row ? row.status : row.severity) === filter || filter === "all") &&
    JSON.stringify(row).toLowerCase().includes(query.toLowerCase());
  const source = (row: Claim | StaticFinding) => {
    const start = row.source_range?.start_line;
    const end = row.source_range?.end_line ?? start;
    return start && onSource ? (
      <Button
        size="sm"
        variant="ghost"
        className="h-7 px-0 text-xs text-primary"
        onClick={() => onSource({ attempt: number, start, end })}
      >
        Line {start}
        {end > start ? `–${end}` : ""}
        <ArrowUpRight className="size-3" />
      </Button>
    ) : (
      <span className="text-xs text-muted-foreground">
        {row.location || "Source location unavailable"}
      </span>
    );
  };
  return (
    <TooltipProvider delayDuration={150}>
      <section className="min-w-0" aria-label="Verification evidence">
        {!evidence.attempts.length && (
          <p className="mb-3 text-sm text-muted-foreground">
            No completed attempts yet. Available stage evidence is preserved below.
          </p>
        )}
        <Tabs value={tab} onValueChange={setTab}>
          <div className="max-w-full overflow-x-auto pb-1">
            <TabsList className="w-max justify-start">
              {[
                "overview",
                "claims",
                "findings",
                "metrics",
                "judges",
                "verification",
                "attempts"
              ].map((key) => (
                <TabsTrigger key={key} value={key}>
                  {key[0].toUpperCase() + key.slice(1)}
                  {key === "claims"
                    ? ` (${claims.length})`
                    : key === "findings"
                      ? ` (${findings.length})`
                      : ""}
                </TabsTrigger>
              ))}
            </TabsList>
          </div>
          {(tab === "claims" || tab === "findings") && (
            <div className="mt-4 flex flex-wrap gap-2">
              <div className="relative min-w-0 flex-1">
                <Search className="absolute left-3 top-3 size-4 text-muted-foreground" />
                <Input
                  aria-label="Filter evidence"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search evidence"
                  className="pl-9"
                />
              </div>
              <Select value={filter} onValueChange={setFilter}>
                <SelectTrigger aria-label="Evidence status filter" className="w-44">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(tab === "claims"
                    ? ["all", "supported", "unsupported", "uncertain", "not_checked"]
                    : ["all", "error", "warning", "info"]
                  ).map((s) => (
                    <SelectItem key={s} value={s}>
                      {s === "all" ? "All statuses" : s.replace(/_/g, " ")}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          <TabsContent value="overview">
            <div className="space-y-5">
              <div className="rounded-lg border bg-card p-4">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <h2 className="text-base font-semibold">Decision and coverage</h2>
                  <StatusBadge value={data.policy?.decision ?? evidence.run.status} />
                </div>
                <MarkdownText>
                  {data.policy?.reason ??
                    "Verification is incomplete. Available evidence is shown without implying acceptance."}
                </MarkdownText>
                {links(data.policy?.evidence_ids ?? [])}
                <div className="mt-4 grid grid-cols-2 gap-4 border-t pt-4 sm:grid-cols-4">
                  {[
                    ["Supported", claims.filter((c) => c.status === "supported").length],
                    ["Unsupported", claims.filter((c) => c.status === "unsupported").length],
                    ["Uncertain", claims.filter((c) => c.status === "uncertain").length],
                    ["Static blockers", findings.filter((f) => f.severity === "error").length]
                  ].map(([label, count]) => (
                    <div key={label}>
                      <span className="block text-xs text-muted-foreground">{label}</span>
                      <span className="font-mono text-xl font-medium">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
              {findings.some((f) => f.severity === "error") && (
                <div>
                  <h3 className="mb-2 text-sm font-semibold">Blocking findings</h3>
                  {findings
                    .filter((f) => f.severity === "error")
                    .map((f) => (
                      <div
                        key={f.id}
                        className="flex items-start justify-between gap-2 border-b py-2"
                      >
                        <span className="min-w-0 text-sm">{f.message}</span>
                        {source(f)}
                      </div>
                    ))}
                </div>
              )}
              <div>
                <h3 className="mb-2 text-sm font-semibold">Analyzer coverage</h3>
                {!data.coverage?.length ? (
                  <p className="text-sm text-muted-foreground">
                    Coverage has not been reported yet.
                  </p>
                ) : (
                  <div className="divide-y rounded-lg border bg-card">
                    {data.coverage.map((c, i) => (
                      <div key={`${c.analyzer}-${i}`} className="px-4 py-3">
                        <div className="flex flex-wrap justify-between gap-2">
                          <span className="text-sm font-medium">
                            {c.analyzer.replace(/_/g, " ")}
                          </span>
                          <StatusBadge value={c.status} />
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">{c.detail}</p>
                        <p className="mt-1 font-mono text-xs text-muted-foreground">
                          {c.language} · {c.version ?? "version unavailable"}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              {evidence.run.inferred.uncertain_assumptions.length > 0 && (
                <div className="rounded-lg border border-amber-200 bg-warning-surface p-4">
                  <h3 className="mb-2 text-sm font-semibold">Uncertain assumptions</h3>
                  <MarkdownText>
                    {evidence.run.inferred.uncertain_assumptions.map((s) => `- ${s}`).join("\n")}
                  </MarkdownText>
                </div>
              )}
              <div className="rounded-lg border bg-card p-4">
                <h3 className="mb-3 text-sm font-semibold">Run context</h3>
                <dl className="grid gap-3 text-sm sm:grid-cols-2">
                  {[
                    ["Language", evidence.run.inferred.language ?? "Unspecified"],
                    ["Framework", evidence.run.inferred.framework ?? "None"],
                    ["Runtime", evidence.run.inferred.runtime ?? "Unspecified"],
                    ["Libraries", evidence.run.inferred.libraries.join(", ") || "None"],
                    ["Model", evidence.run.model_name],
                    ["Repair limit", String(evidence.run.max_retry)]
                  ].map(([label, value]) => (
                    <div key={label} className="min-w-0">
                      <dt className="text-xs text-muted-foreground">{label}</dt>
                      <dd className="break-words font-medium">{value}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            </div>
          </TabsContent>
          <TabsContent value="claims">
            <div className="divide-y rounded-lg border bg-card">
              {claims.filter(matches).map((c) => (
                <details
                  id={`evidence-${c.id}`}
                  key={c.id}
                  tabIndex={-1}
                  open={focused === c.id || undefined}
                  className="p-4"
                >
                  <summary className="cursor-pointer text-sm">
                    <span className="ml-1 inline-flex flex-wrap items-center gap-2">
                      <StatusBadge value={c.status} />
                      <span className="font-medium">{c.claim_type}</span>
                      <span className="break-words">{c.claim_text}</span>
                    </span>
                  </summary>
                  <div className="mt-3 pl-4">
                    <MarkdownText>
                      {c.evidence || "Supporting evidence is unavailable."}
                    </MarkdownText>
                    {source(c)}
                    <p className="text-xs text-muted-foreground">
                      Method: {c.check_method || "Not checked"}
                    </p>
                    {links(c.evidence_ids ?? [])}
                  </div>
                </details>
              ))}
              {!claims.filter(matches).length && (
                <Empty
                  title="No matching claims"
                  text={
                    claims.length
                      ? "Try another search or status."
                      : "Claim extraction has not produced evidence for this attempt."
                  }
                />
              )}
            </div>
          </TabsContent>
          <TabsContent value="findings">
            <div className="divide-y rounded-lg border bg-card">
              {findings.filter(matches).map((f) => (
                <details
                  id={`evidence-${f.id}`}
                  key={f.id}
                  tabIndex={-1}
                  open={focused === f.id || undefined}
                  className="p-4"
                >
                  <summary className="cursor-pointer text-sm">
                    <span className="ml-1 inline-flex flex-wrap items-center gap-2">
                      <StatusBadge value={f.severity} />
                      <span className="break-words font-medium">{f.message}</span>
                    </span>
                  </summary>
                  <div className="mt-3 pl-4">
                    <p className="mb-2 font-mono text-xs text-muted-foreground">
                      {f.rule_id} · {f.evidence_source}
                    </p>
                    {source(f)}
                    {links(f.claim_ids ?? [])}
                  </div>
                </details>
              ))}
              {!findings.filter(matches).length && (
                <Empty
                  title="No matching findings"
                  text={
                    findings.length
                      ? "Try another search or severity."
                      : "No static findings are recorded. Check analyzer coverage before interpreting this result."
                  }
                />
              )}
            </div>
          </TabsContent>
          <TabsContent value="metrics">
            <MetricsTable attempts={evidence.attempts} />
          </TabsContent>
          <TabsContent value="judges">
            <div className="space-y-4">
              {data.judge_consensus && (
                <div className="rounded-lg border bg-card p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-semibold">Judge consensus</h3>
                    <StatusBadge value={data.judge_consensus.final_verdict} />
                    <span className="text-xs text-muted-foreground">
                      {data.judge_consensus.valid_count}/{data.judge_consensus.expected_count} valid
                      responses · {data.judge_consensus.agreement_level}
                    </span>
                  </div>
                  <MarkdownText>{data.judge_consensus.summary}</MarkdownText>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Average score{" "}
                    <span className="font-mono">{format(data.judge_consensus.average_score)}</span>
                  </p>
                </div>
              )}
              {(data.judge_results ?? []).map((j) => (
                <div key={j.judge_name} className="rounded-lg border bg-card p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-base font-semibold">{j.judge_name}</h3>
                    <div className="flex gap-2">
                      <StatusBadge value={j.status} />
                      <StatusBadge value={j.verdict ?? "Unavailable"} />
                    </div>
                  </div>
                  <p className="mb-3 mt-1 text-xs text-muted-foreground">
                    {j.role} · {j.judge_model} · score {format(j.score)}
                  </p>
                  <MarkdownText>{j.explanation}</MarkdownText>
                  {Object.keys(j.rubric_json).length > 0 && (
                    <div className="mt-4 divide-y border-t">
                      {Object.entries(j.rubric_json).map(([key, raw]) => {
                        const rubric = raw as { score?: number; evidence?: string[] };
                        return (
                          <div key={key} className="py-3">
                            <div className="flex justify-between gap-2 text-sm">
                              <span className="capitalize">{key.replace(/_/g, " ")}</span>
                              <span className="font-mono">{format(rubric.score)}</span>
                            </div>
                            {rubric.evidence?.length ? (
                              <MarkdownText>
                                {rubric.evidence.map((s) => `- ${s}`).join("\n")}
                              </MarkdownText>
                            ) : null}
                          </div>
                        );
                      })}
                    </div>
                  )}
                  {j.blocking_issues.length > 0 && (
                    <div className="mt-3 text-danger">
                      <h4 className="text-xs font-semibold">Blocking issues</h4>
                      <MarkdownText>
                        {j.blocking_issues.map((s) => `- ${s}`).join("\n")}
                      </MarkdownText>
                    </div>
                  )}
                  {j.repair_suggestions.length > 0 && (
                    <div className="mt-3">
                      <h4 className="text-xs font-semibold">Repair suggestions</h4>
                      <MarkdownText>
                        {j.repair_suggestions.map((s) => `- ${s}`).join("\n")}
                      </MarkdownText>
                    </div>
                  )}
                  {links(j.evidence_ids)}
                </div>
              ))}
              {!data.judge_results?.length && (
                <Empty
                  title="No judge responses"
                  text="Responses appear after independent provider calls complete."
                />
              )}
            </div>
          </TabsContent>
          <TabsContent value="verification">
            <div className="divide-y rounded-lg border bg-card">
              {(data.cove_results ?? []).map((c, i) => (
                <div key={`${c.claim_id}-${i}`} className="p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <h3 className="min-w-0 text-sm font-medium">{c.verification_question}</h3>
                    <StatusBadge value={c.verdict} />
                  </div>
                  <div className="mt-2">
                    <MarkdownText>{c.evidence}</MarkdownText>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Confidence <span className="font-mono">{format(c.confidence)}</span>
                  </p>
                  {links([
                    ...new Set([...(c.evidence_ids ?? []), ...(c.claim_id ? [c.claim_id] : [])])
                  ])}
                </div>
              ))}
              {!data.cove_results?.length && (
                <Empty
                  title="No verification answers"
                  text="Claim-specific questions and linked evidence appear here."
                />
              )}
            </div>
          </TabsContent>
          <TabsContent value="attempts">
            <div className="divide-y rounded-lg border bg-card">
              {evidence.attempts.map((a) => (
                <div key={a.output.id} className="p-4">
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-base font-semibold">
                      Attempt {a.output.attempt_no}
                      {a.output.attempt_no > 1 ? " · repair" : " · initial"}
                    </h3>
                    <StatusBadge value={a.policy.decision} />
                  </div>
                  <MarkdownText>
                    {a.output.repair_summary.length
                      ? a.output.repair_summary.map((s) => `- ${s}`).join("\n")
                      : "Initial generation; no repair changes."}
                  </MarkdownText>
                  <MarkdownText>{a.policy.reason}</MarkdownText>
                  <p className="mt-2 font-mono text-xs text-muted-foreground">
                    {a.output.provider} · comparative risk{" "}
                    {format(a.metrics.hallucination_risk_score)}
                  </p>
                </div>
              ))}
              {!evidence.attempts.length && (
                <Empty
                  title="No completed attempts"
                  text="Completed attempts remain available after failures and interruptions."
                />
              )}
            </div>
          </TabsContent>
        </Tabs>
        {Object.keys(evidence.partial).length > 0 && (
          <Collapsible className="mt-5 border-t pt-3">
            <CollapsibleTrigger className="flex items-center gap-2 text-xs text-muted-foreground">
              Partial stage diagnostics
              <ChevronDown className="size-3" />
            </CollapsibleTrigger>
            <CollapsibleContent>
              <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-md bg-muted p-3 font-mono text-xs">
                {JSON.stringify(
                  Object.fromEntries(
                    Object.entries(evidence.partial).filter(
                      ([key]) =>
                        ![
                          "claims",
                          "static_findings",
                          "coverage",
                          "judge_results",
                          "cove_results",
                          "policy",
                          "metrics",
                          "judge_consensus",
                          "output"
                        ].includes(key)
                    )
                  ),
                  null,
                  2
                )}
              </pre>
            </CollapsibleContent>
          </Collapsible>
        )}
      </section>
    </TooltipProvider>
  );
}
function Empty({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-lg px-4 py-8 text-center">
      <h3 className="text-sm font-medium">{title}</h3>
      <p className="mt-1 text-sm text-muted-foreground">{text}</p>
    </div>
  );
}
function MetricsTable({ attempts }: { attempts: AttemptEvidence[] }) {
  if (!attempts.length)
    return (
      <Empty
        title="Metrics unavailable"
        text="Comparison metrics appear when an attempt completes."
      />
    );
  return (
    <>
      <p className="mb-3 text-xs text-muted-foreground">
        Compare completed attempts. Missing measurements are unavailable, rather than zero.
      </p>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Attempt</TableHead>
            {Object.keys(help).map((label) => (
              <TableHead key={label}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button type="button" className="inline-flex items-center gap-1 text-xs">
                      {label}
                      <Info className="size-3" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>{help[label]}</TooltipContent>
                </Tooltip>
              </TableHead>
            ))}
            {["Supported", "Unsupported", "Uncertain", "Policy"].map((label) => (
              <TableHead key={label}>{label}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {attempts.map((a) => (
            <TableRow key={a.output.id}>
              <TableCell>
                <span className="font-medium">{a.output.attempt_no}</span>
              </TableCell>
              {[
                a.metrics.mihn,
                a.metrics.mahr,
                a.metrics.tr_s,
                a.metrics.entropy_score,
                a.metrics.hallucination_risk_score,
                a.judge_consensus.average_score
              ].map((value, i) => (
                <TableCell key={i}>
                  <span className="font-mono text-xs">{format(value)}</span>
                </TableCell>
              ))}
              {[
                a.claims.filter((c) => c.status === "supported").length,
                a.metrics.unsupported_count,
                a.metrics.uncertain_count
              ].map((count, i) => (
                <TableCell key={i}>
                  <span className="font-mono">{count}</span>
                </TableCell>
              ))}
              <TableCell>
                <StatusBadge value={a.policy.decision} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <p className="mt-3 text-xs text-muted-foreground">
        {attempts.some((a) => !a.metrics.total_claims)
          ? "Zero claims: coverage is insufficient to establish support. "
          : ""}
        Metric definition {attempts[attempts.length - 1].metrics.version}.
      </p>
    </>
  );
}
