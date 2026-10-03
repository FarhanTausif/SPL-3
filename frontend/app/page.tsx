"use client";

import type { ChangeEvent } from "react";
import { useState } from "react";
import { ArrowUp, Loader2, ShieldCheck, Sparkles } from "lucide-react";
import { CodeAttempts } from "@/components/CodeAttempts";
import { EvidencePanel } from "@/components/EvidencePanel";
import { ResultPanel } from "@/components/ResultPanel";
import { Workflow, defaultStages, type StageView } from "@/components/Workflow";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { streamRun, type AttemptEvidence, type RunEvidence, type RunStreamEvent, type RunSummary } from "@/lib/api";

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

  async function submit() {
    setLoading(true);
    setRunStatus("running");
    setError(null);
    setEvidence(null);
    setAttempts([]);
    setStreamed({});
    setStages(freshStages());
    try {
      await streamRun({ prompt }, (event) => {
        handleStreamEvent(event);
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
      setRunStatus("error");
    } finally {
      setLoading(false);
    }
  }

  function handleStreamEvent(event: RunStreamEvent) {
    if (event.type === "run_created") {
      setRun({
        id: event.run_id,
        prompt,
        status: "running",
        inferred: event.inferred,
        model_name: event.model_name ?? "ollama",
        max_retry: 0,
        final_output: null,
        policy_decision: null
      });
      return;
    }
    if (event.type === "stage") {
      setStages((previous) =>
        previous.map((stage) =>
          stage.key === event.stage
            ? { ...stage, status: event.status, progress: event.progress, attemptNo: event.attempt_no ?? stage.attemptNo }
            : stage
        )
      );
      return;
    }
    if (event.type === "token") {
      setStreamed((previous) => ({
        ...previous,
        [event.attempt_no]: `${previous[event.attempt_no] ?? ""}${event.text}`
      }));
      return;
    }
    if (event.type === "attempt_completed") {
      setAttempts((previous) =>
        [...previous.filter((attempt) => attempt.output.attempt_no !== event.attempt.output.attempt_no), event.attempt].sort(
          (a, b) => a.output.attempt_no - b.output.attempt_no
        )
      );
      return;
    }
    if (event.type === "clarification") {
      setRun(event.run);
      setRunStatus("needs_clarification");
      setLoading(false);
      return;
    }
    if (event.type === "run_completed") {
      setRun(event.run);
      setEvidence(event.evidence);
      setAttempts(event.evidence.attempts);
      setRunStatus(event.run.status);
      return;
    }
    if (event.type === "error") {
      setError(event.message);
      setRunStatus("error");
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
            Local CodeLLM + Judge Pool
          </div>
        </header>

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
                {error ? (
                  <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
                    {error}
                  </div>
                ) : null}
              </CardContent>
            </Card>

            <CodeAttempts attempts={attempts} streamed={streamed} />
          </div>

          <aside className="grid min-w-0 content-start gap-5">
            <ResultPanel run={run} />
          </aside>
        </section>

        <Workflow status={run?.status ?? runStatus} stages={stages} />
        <EvidencePanel evidence={evidence} />
      </div>
    </main>
  );
}
