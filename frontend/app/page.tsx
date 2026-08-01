"use client";

import { useState } from "react";
import { EvidencePanel } from "@/components/EvidencePanel";
import { ResultPanel } from "@/components/ResultPanel";
import { Workflow } from "@/components/Workflow";
import { createRun, getEvidence, type RunEvidence, type RunSummary } from "@/lib/api";

export default function Home() {
  const [prompt, setPrompt] = useState("Write a Python function that adds two numbers.");
  const [language, setLanguage] = useState("");
  const [maxRetry, setMaxRetry] = useState(1);
  const [run, setRun] = useState<RunSummary | null>(null);
  const [evidence, setEvidence] = useState<RunEvidence | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setLoading(true);
    setError(null);
    setEvidence(null);
    try {
      const created = await createRun({
        prompt,
        language_hint: language || undefined,
        max_retry: maxRetry,
        constraints: []
      });
      setRun(created);
      if (created.status !== "needs_clarification") {
        setEvidence(await getEvidence(created.id));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <h1>DeHalu</h1>
          <p>Agentic hallucination detection and mitigation for local CodeLLMs.</p>
        </div>
        <button onClick={submit} disabled={loading || prompt.trim().length < 3}>
          {loading ? "Running" : "Run"}
        </button>
      </section>

      <section className="panel inputPanel">
        <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} />
        <div className="controls">
          <label>
            Language hint
            <input value={language} onChange={(event) => setLanguage(event.target.value)} placeholder="optional" />
          </label>
          <label>
            Max retry
            <input
              type="number"
              min={0}
              max={5}
              value={maxRetry}
              onChange={(event) => setMaxRetry(Number(event.target.value))}
            />
          </label>
        </div>
        {error ? <p className="error">{error}</p> : null}
      </section>

      <Workflow status={run?.status ?? "idle"} />
      <div className="grid two">
        <ResultPanel run={run} />
        <EvidencePanel evidence={evidence} />
      </div>
    </main>
  );
}
