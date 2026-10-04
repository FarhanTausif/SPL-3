"use client";

import type { ChangeEvent } from "react";
import { useEffect, useRef, useState } from "react";
import { ArrowUp, Loader2, ShieldCheck, Sparkles } from "lucide-react";
import { CodeAttempts } from "@/components/CodeAttempts";
import { EvidencePanel } from "@/components/EvidencePanel";
import { ResultPanel } from "@/components/ResultPanel";
import { Workflow, defaultStages, type StageView } from "@/components/Workflow";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { createRun, getEvidence, listRuns, watchRun, cancelRun, clarifyRun, exportUrl, getHealth, terminalStatuses, type AttemptEvidence, type RunEvidence, type RunStreamEvent, type RunSummary } from "@/lib/api";

function freshStages(): StageView[] {
  return defaultStages.map((stage) => ({ ...stage }));
}

export default function Home() {
  const [prompt, setPrompt] = useState("Write a Python function that adds two numbers.");
  const [run, setRun] = useState<RunSummary | null>(null);
  const [evidence, setEvidence] = useState<RunEvidence | null>(null);
  const [attempts, setAttempts] = useState<AttemptEvidence[]>([]);
  const [streamed, setStreamed] = useState<Record<number, string>>({});
  const [stages, setStages] = useState<StageView[]>(freshStages);
  const [runStatus, setRunStatus] = useState("idle");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [history, setHistory] = useState<RunSummary[]>([]);
  const [answer, setAnswer] = useState("");
  const [language, setLanguage] = useState("");
  const [constraints, setConstraints] = useState("");
  const [framework, setFramework] = useState("");
  const [runtime, setRuntime] = useState("");
  const [libraries, setLibraries] = useState("");
  const [maxRetry, setMaxRetry] = useState(3);
  const [readiness, setReadiness] = useState("Checking providers…");
  const watcher = useRef<AbortController | null>(null);

  useEffect(() => {
    listRuns().then(setHistory).catch(() => setError("Cannot load run history. Check the API connection."));
    getHealth().then(health => setReadiness(health.ollama.fake_mode ? "Explicit development mode" : health.status === "ok" ? "Providers configured" : "Provider coverage degraded")).catch(() => setReadiness("API unavailable"));
    const saved = localStorage.getItem("dehalu-active-run");
    if (saved) void openRun(saved);
    return () => watcher.current?.abort();
    // The selected run is managed by its own AbortController.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function openRun(id: string) {
    watcher.current?.abort();
    const controller = new AbortController();
    watcher.current = controller;
    setError(null);
    setStreamed({});
    setStages(freshStages());
    setAttempts([]);
    setEvidence(null);
    setAnswer("");
    try {
      const stored = await getEvidence(id);
      if (controller.signal.aborted) return;
      setRun(stored.run);
      setPrompt(stored.run.prompt);
      setEvidence(stored);
      setAttempts(stored.attempts);
      setRunStatus(stored.run.status);
      setLoading(!terminalStatuses.has(stored.run.status));
      localStorage.setItem("dehalu-active-run", id);
      await watchRun(id, handleStreamEvent, controller.signal, () => setRunStatus("reconnecting"));
      if (controller.signal.aborted) return;
      const final = await getEvidence(id);
      setRun(final.run);
      setEvidence(final);
      setAttempts(final.attempts);
      setRunStatus(final.run.status);
      setLoading(!terminalStatuses.has(final.run.status));
      setHistory(await listRuns());
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err instanceof Error ? err.message : "Request failed");
        setLoading(false);
      }
    }
  }

  async function submit() {
    setLoading(true);
    setError(null);
    try {
      const created = await createRun({ prompt, language_hint: language || null, framework_hint: framework || null, runtime_hint: runtime || null, libraries: libraries.split(",").map(item => item.trim()).filter(Boolean), constraints: constraints.split("\n").filter(Boolean), max_retry: maxRetry });
      setHistory(previous => [created, ...previous]);
      await openRun(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
      setLoading(false);
    }
  }

  async function clarify() {
    if (!run) return;
    try {
      await clarifyRun(run.id, answer);
      await openRun(run.id);
    } catch (err) { setError(err instanceof Error ? err.message : "Clarification failed"); }
  }

  async function cancel() {
    if (!run) return;
    try {
      const cancelled = await cancelRun(run.id);
      setRun(cancelled);
      setRunStatus(cancelled.status);
      setLoading(false);
    } catch (err) { setError(err instanceof Error ? err.message : "Cancellation failed"); }
  }

  function handleStreamEvent(event: RunStreamEvent) {
    if (event.type === "run_created" || event.type === "context") {
      setRun(previous => previous ? { ...previous, inferred: event.inferred } : previous);
    } else if (event.type === "stage") {
      setRunStatus("running");
      if (event.status === "running") {
        setLoading(true);
        setRun(previous => previous ? { ...previous, status: "running" } : previous);
      }
      setStages(previous => previous.map(stage => stage.key === event.stage ? { ...stage, status: event.status, progress: event.progress, attemptNo: event.attempt_no ?? stage.attemptNo } : stage));
    } else if (event.type === "token") {
      setStreamed(previous => ({ ...previous, [event.attempt_no]: `${previous[event.attempt_no] ?? ""}${event.text}` }));
    } else if (event.type === "attempt_completed") {
      setAttempts(previous => [...previous.filter(attempt => attempt.output.attempt_no !== event.attempt.output.attempt_no), event.attempt].sort((a, b) => a.output.attempt_no - b.output.attempt_no));
    } else if (event.type === "clarification") {
      setRun(event.run);
      setRunStatus("needs_clarification");
      setLoading(false);
    } else if (event.type === "run_completed") {
      setRun(event.run);
      setEvidence(event.evidence);
      setAttempts(event.evidence.attempts);
      setRunStatus(event.run.status);
      setLoading(false);
    } else if (event.type === "error") {
      setError(event.message);
      setRunStatus("failed");
      setLoading(false);
    } else if (event.type === "run_cancelled" || event.type === "run_interrupted") {
      setRunStatus(event.type === "run_cancelled" ? "cancelled" : "interrupted");
      setLoading(false);
    }
  }

  function resizeTextarea(event: ChangeEvent<HTMLTextAreaElement>) {
    setPrompt(event.target.value);
    event.target.style.height = "auto";
    event.target.style.height = `${Math.min(event.target.scrollHeight, 240)}px`;
  }

  return (
    <main className="min-h-screen overflow-x-hidden bg-[radial-gradient(circle_at_top_left,rgba(72,162,119,0.12),transparent_28rem),linear-gradient(180deg,#faf8f3_0%,#f1ece3_58%,#ebe5da_100%)] text-stone-950">
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-4 px-3 py-4 sm:px-5 lg:px-6">
        <header className="flex flex-col gap-3 rounded-lg border border-stone-200/80 bg-white/80 p-3 shadow-sm backdrop-blur md:flex-row md:items-center md:justify-between">
          <div className="flex min-w-0 items-center gap-3">
            <div className="grid size-11 shrink-0 place-items-center rounded-lg bg-emerald-800 text-white shadow-sm">
              <ShieldCheck className="size-5" />
            </div>
            <div className="min-w-0">
              <p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.18em] text-emerald-800">
                <Sparkles className="size-3.5" />
                DeHalu Workspace
              </p>
              <h1 className="truncate text-[22px] font-semibold tracking-[-0.01em] text-stone-950 sm:text-[28px]">
                Hallucination-aware code generation
              </h1>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2 rounded-full border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-stone-600">
            <span className="size-2 rounded-full bg-emerald-600" />
            {readiness}
          </div>
        </header>

        <section className="flex flex-wrap items-center gap-3 rounded-lg border border-stone-200 bg-white p-3 text-sm">
          <label>History <select aria-label="Run history" className="max-w-[300px] rounded border p-1" value={run?.id ?? ""} onChange={event => event.target.value && void openRun(event.target.value)}>
            <option value="">Select a run</option>
            {history.map(item => <option key={item.id} value={item.id}>{item.status} · {item.prompt.slice(0, 55)}</option>)}
          </select></label>
          <button type="button" className="rounded border px-3 py-1" onClick={() => listRuns().then(setHistory).catch(() => setError("History refresh failed"))}>Refresh history</button>
          {run && <a className="rounded border px-3 py-1" href={exportUrl(run.id)}>Export evidence</a>}
          {run && (loading || run.status === "needs_clarification") && <button type="button" className="rounded border border-red-200 px-3 py-1 text-red-700" onClick={cancel}>Cancel run</button>}
          <span className="text-stone-500">Execution-free verification</span>
        </section>
        <section className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="grid min-w-0 gap-4">
            <Card className="border-stone-200/80 bg-white/90 shadow-sm backdrop-blur">
              <CardContent className="p-2">
                <div className="min-w-0">
                  <div className="min-w-0 rounded-[24px] border border-stone-200 bg-white text-stone-950 shadow-[0_12px_32px_rgba(41,37,36,0.08)]">
                    <Textarea
                      aria-label="Prompt"
                      value={prompt}
                      onChange={resizeTextarea}
                      placeholder="Ask DeHalu to generate code..."
                      rows={3}
                      className="max-h-[220px] min-h-[74px] border-0 bg-transparent px-5 pb-2 pt-4 text-[16px] leading-7 text-stone-900 shadow-none placeholder:text-stone-400 focus-visible:ring-0"
                    />
                    <div className="flex items-center justify-end gap-3 px-3 pb-3">
                      <div className="flex shrink-0 items-center gap-1">
                        <button
                          className="grid size-9 place-items-center rounded-full bg-stone-950 text-white transition hover:bg-stone-800 disabled:opacity-50"
                          onClick={submit}
                          disabled={loading || prompt.trim().length < 3}
                          type="button"
                          aria-label="Run prompt"
                        >
                          {loading ? <Loader2 className="size-4 animate-spin" /> : <ArrowUp className="size-4" />}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
                <details className="mt-3 px-3 text-sm text-stone-600">
                  <summary>Generation context and repair limit</summary>
                  <div className="mt-2 flex flex-wrap gap-3">
                    <label>Language <select aria-label="Language" value={language} onChange={e => setLanguage(e.target.value)} className="rounded border p-1">
                      <option value="">Infer from prompt</option>
                      {["python", "javascript", "typescript", "java", "go", "rust", "c", "cpp"].map(lang => <option key={lang} value={lang}>{lang}</option>)}
                    </select></label>
                    <label>Repairs <input aria-label="Maximum repairs" type="number" min={0} max={5} value={maxRetry} onChange={e => setMaxRetry(Math.max(0, Math.min(5, Number(e.target.value))))} className="w-14 rounded border p-1" /></label>
                  </div>
                  <div className="mt-2 grid gap-2 sm:grid-cols-3">
                    <input aria-label="Framework hint" value={framework} onChange={e => setFramework(e.target.value)} placeholder="Framework (optional)" className="min-w-0 rounded border p-2" />
                    <input aria-label="Runtime hint" value={runtime} onChange={e => setRuntime(e.target.value)} placeholder="Runtime/version (optional)" className="min-w-0 rounded border p-2" />
                    <input aria-label="Allowed libraries" value={libraries} onChange={e => setLibraries(e.target.value)} placeholder="Libraries, comma separated" className="min-w-0 rounded border p-2" />
                  </div>
                  <Textarea aria-label="Constraints" value={constraints} onChange={e => setConstraints(e.target.value)} placeholder="Constraints, one per line" className="mt-2" />
                </details>
                {run?.status === "needs_clarification" && <div className="mt-3 rounded border border-sky-200 bg-sky-50 p-3">
                  <p className="text-sm font-semibold">Answer the questions in the run summary</p>
                  <Textarea aria-label="Clarification answers" value={answer} onChange={e => setAnswer(e.target.value)} className="mt-2" />
                  <button type="button" onClick={clarify} disabled={!answer.trim()} className="mt-2 rounded bg-emerald-800 px-3 py-2 text-sm text-white disabled:opacity-50">Resume run</button>
                </div>}
                {error ? (
                  <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
                    {error}
                  </div>
                ) : null}
              </CardContent>
            </Card>

            <CodeAttempts attempts={attempts} streamed={streamed} language={run?.inferred.language ?? "text"} />
          </div>

          <aside className="grid min-w-0 content-start gap-5">
            <ResultPanel run={run} />
          </aside>
        </section>

        <Workflow status={runStatus} stages={stages} />
        <EvidencePanel evidence={evidence} />
      </div>
    </main>
  );
}
