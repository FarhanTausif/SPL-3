export type InferenceResult = {
  language: string | null;
  framework: string | null;
  runtime: string | null;
  libraries: string[];
  requirements: string[];
  uncertain_assumptions: string[];
  clarification_questions: string[];
  needs_clarification: boolean;
};

export type GeneratedOutput = {
  id: string | null;
  attempt_no: number;
  code: string;
  explanation: string;
  provider: string;
  entropy_summary: Record<string, unknown>;
  logprob_summary: Record<string, unknown>;
};

export type PolicyDecision = {
  decision: string;
  reason: string;
};

export type RunSummary = {
  id: string;
  status: string;
  prompt: string;
  inferred: InferenceResult;
  model_name: string;
  max_retry: number;
  final_output: GeneratedOutput | null;
  policy_decision: PolicyDecision | null;
};

export type AttemptEvidence = {
  output: GeneratedOutput;
  claims: Array<{ id: string | null; claim_type: string; claim_text: string; location: string; status: string }>;
  static_findings: Array<{ rule_id: string; severity: string; message: string; location: string; evidence_source: string }>;
  metrics: { mihn: number; mahr: number; tr_s: number; entropy_score: number; hallucination_risk_score: number };
  judge_results: Array<{ judge_name: string; judge_model: string; verdict: string; score: number; explanation: string; rubric_json: Record<string, unknown> }>;
  judge_consensus: { final_verdict: string; average_score: number; agreement_level: string; summary: string };
  cove_results: Array<{ claim_id: string | null; verdict: string; evidence: string; confidence: number }>;
  policy: PolicyDecision;
};

export type RunEvidence = {
  run: RunSummary;
  attempts: AttemptEvidence[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function createRun(payload: { prompt: string; language_hint?: string; max_retry: number; constraints: string[] }) {
  const response = await fetch(`${API_BASE}/api/runs`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as RunSummary;
}

export async function getEvidence(runId: string) {
  const response = await fetch(`${API_BASE}/api/runs/${runId}/evidence`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as RunEvidence;
}
