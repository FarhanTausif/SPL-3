import type {
  AttemptEvidence,
  RunEvidence,
  RunSummary,
  HealthResponse
} from "@/lib/contracts.generated";
export const makeRun = (patch: Partial<RunSummary> = {}): RunSummary => ({
  id: "run-1",
  status: "completed",
  prompt: "Write a Python function that adds two numbers.",
  inferred: {
    language: "python",
    framework: null,
    runtime: "Python 3.11",
    libraries: [],
    requirements: [],
    constraints: [],
    uncertain_assumptions: [],
    clarification_questions: [],
    needs_clarification: false
  },
  model_name: "qwen2.5-coder",
  max_retry: 3,
  created_at: "2026-10-05T10:00:00Z",
  completed_at: "2026-10-05T10:01:00Z",
  error: null,
  final_output: null,
  policy_decision: {
    decision: "warn",
    reason: "Some claims remain uncertain.",
    evidence_ids: [],
    version: "2"
  },
  ...patch
});
export const makeAttempt = (
  number = 1,
  decision: "accept" | "warn" | "reject" | "repair" = "warn"
): AttemptEvidence => ({
  output: {
    id: `output-${number}`,
    attempt_no: number,
    code: number === 1 ? "def add(a, b):\n    return a - b" : "def add(a, b):\n    return a + b",
    explanation: "A simple addition function.",
    provider: "ollama",
    entropy_summary: {},
    logprob_summary: {},
    metadata: {},
    repair_summary: number > 1 ? ["Changed subtraction to addition."] : []
  },
  claims: [
    {
      id: `claim-${number}`,
      claim_type: "behavior",
      claim_text: "Adds two numbers",
      location: "line 2",
      status: number === 1 ? "unsupported" : "supported",
      source_range: { start_line: 2, end_line: 2 },
      check_method: "cove",
      evidence_ids: [`finding-${number}`],
      evidence: "Return operation inspected.",
      details: {}
    }
  ],
  static_findings: [
    {
      id: `finding-${number}`,
      rule_id: "logic.addition",
      severity: "warning",
      message: "Inspect arithmetic operation",
      location: "line 2",
      evidence_source: "Static analysis",
      claim_ids: [`claim-${number}`],
      source_range: { start_line: 2, end_line: 2 }
    }
  ],
  coverage: [
    {
      analyzer: "tree_sitter",
      language: "python",
      status: "available",
      detail: "Parsed without syntax errors.",
      version: "0.25.2"
    }
  ],
  metrics: {
    mihn: number === 1 ? 1 : 0,
    mahr: number === 1 ? 1 : 0,
    tr_s: 0,
    entropy_score: null,
    hallucination_risk_score: 0.3,
    static_severity_score: 0.1,
    uncertainty_score: 0.2,
    unsupported_count: number === 1 ? 1 : 0,
    uncertain_count: 0,
    total_claims: 1,
    version: "2"
  },
  judge_results: [
    {
      judge_name: "Gemini",
      judge_model: "gemini-flash-latest",
      role: "Requirement alignment",
      status: "failed",
      verdict: null,
      score: null,
      rubric_json: {},
      explanation: "Provider quota exceeded.",
      blocking_issues: [],
      evidence_ids: [],
      repair_suggestions: []
    }
  ],
  judge_consensus: {
    final_verdict: "warn",
    average_score: null,
    agreement_level: "incomplete",
    summary: "Judge coverage incomplete.",
    valid_count: 0,
    expected_count: 3
  },
  cove_results: [
    {
      claim_id: `claim-${number}`,
      verification_question: "Does this add two numbers?",
      verdict: number === 1 ? "unsupported" : "supported",
      evidence: "Inspected return expression.",
      evidence_ids: [`finding-${number}`],
      confidence: 0.9
    }
  ],
  policy: {
    decision,
    reason:
      decision === "reject"
        ? "Blocking issue remains unresolved."
        : decision === "accept"
          ? "Material claims supported."
          : "Some claims remain uncertain.",
    evidence_ids: [`claim-${number}`],
    version: "2"
  }
});
export const makeEvidence = (patch: Partial<RunEvidence> = {}): RunEvidence => ({
  run: makeRun(),
  attempts: [makeAttempt()],
  partial: {},
  ...patch
});
export const health: HealthResponse = {
  status: "ok",
  database: "ok",
  ollama: { model_available: true, fake_mode: false },
  judges: {
    gemini: { configured: true, model: "gemini-flash-latest" },
    groq: { configured: true, model: "gpt-oss" },
    mistral: { configured: true, model: "mistral-small" }
  },
  capabilities: []
};
