import type {
  RunCreate,
  RunSummary,
  RunEvidence,
  AttemptEvidence,
  InferenceResult
} from "./contracts.generated";
export type {
  RunCreate,
  RunSummary,
  RunEvidence,
  AttemptEvidence,
  InferenceResult,
  GeneratedOutput,
  PolicyDecision
} from "./contracts.generated";

export type WorkflowStageKey =
  | "intake"
  | "clarification"
  | "generation"
  | "claim_extraction"
  | "tree_sitter"
  | "semgrep"
  | "symbol_indexer"
  | "metrics"
  | "judge_pool"
  | "consensus"
  | "cove"
  | "policy"
  | "repair";

export type StageStatus = "pending" | "running" | "done" | "failed";

export type RunStreamEvent =
  | { type: "run_created"; run_id: string; inferred: InferenceResult; model_name?: string }
  | { type: "clarification"; run: RunSummary }
  | {
      type: "stage";
      stage: WorkflowStageKey;
      status: StageStatus;
      progress: number;
      attempt_no?: number;
    }
  | { type: "token"; attempt_no: number; text: string }
  | { type: "attempt_completed"; attempt: AttemptEvidence }
  | { type: "run_completed"; run: RunSummary; evidence: RunEvidence }
  | { type: "context"; inferred: InferenceResult }
  | { type: "run_cancelled" | "run_interrupted" | "run_resumed" }
  | { type: "error"; message: string };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function errorMessage(response: Response): Promise<string> {
  const raw = await response.text();
  try {
    const data = JSON.parse(raw) as {
      detail?: string | { msg: string; loc?: (string | number)[] }[];
    };
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail))
      return data.detail
        .map(
          (item) =>
            `${item.loc?.filter((part) => part !== "body").join(".") || "Request"}: ${item.msg}`
        )
        .join("; ");
  } catch {
    /* Non-JSON errors are summarized below. */
  }
  return `Request failed (${response.status}). Check the API connection and try again.`;
}

export async function createRun(payload: RunCreate) {
  const response = await fetch(`${API_BASE}/api/runs`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return (await response.json()) as RunSummary;
}

export async function getEvidence(runId: string) {
  const response = await fetch(`${API_BASE}/api/runs/${runId}/evidence`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return (await response.json()) as RunEvidence;
}

export async function streamRun(
  payload: { prompt: string; constraints?: string[] },
  onEvent: (event: RunStreamEvent) => void
) {
  const response = await fetch(`${API_BASE}/api/runs/stream`, {
    method: "POST",
    headers: { accept: "text/event-stream", "content-type": "application/json" },
    body: JSON.stringify({ prompt: payload.prompt, constraints: payload.constraints ?? [] })
  });
  await readEventStream(response, onEvent);
}

export const terminalStatuses = new Set([
  "completed",
  "rejected",
  "reject",
  "failed",
  "cancelled",
  "interrupted",
  "needs_clarification"
]);

async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}/api${path}`, {
    cache: "no-store",
    ...(body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(body)
        })
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<T>;
}
export const listRuns = () => api<RunSummary[]>("/runs");
export const getRun = (id: string) => api<RunSummary>(`/runs/${id}`);
export const cancelRun = (id: string) => api<RunSummary>(`/runs/${id}/cancel`, {});
export const clarifyRun = (id: string, answers: string) =>
  api<RunSummary>(`/runs/${id}/clarification`, { answers });
export const exportUrl = (id: string) => `${API_BASE}/api/runs/${id}/export`;
export const getHealth = () => api<import("./contracts.generated").HealthResponse>("/health");

export async function readEventStream(
  response: Response,
  onEvent: (event: RunStreamEvent & { sequence?: number }) => void,
  signal?: AbortSignal
) {
  if (!response.ok || !response.body) throw new Error(await errorMessage(response));
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const parse = (frame: string) => {
    const data = frame
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (data) onEvent(JSON.parse(data));
  };
  try {
    while (!signal?.aborted) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r\n/g, "\n");
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";
      frames.forEach(parse);
    }
    buffer += decoder.decode();
    if (buffer.trim() && !signal?.aborted) parse(buffer);
  } finally {
    await reader.cancel();
    reader.releaseLock();
  }
}

export async function watchRun(
  id: string,
  onEvent: (event: RunStreamEvent) => void,
  signal: AbortSignal,
  onReconnect?: () => void
) {
  let sequence = 0;
  let retries = 0;
  while (!signal.aborted) {
    try {
      const response = await fetch(`${API_BASE}/api/runs/${id}/events?after=${sequence}`, {
        signal,
        headers: { accept: "text/event-stream" }
      });
      await readEventStream(
        response,
        (event) => {
          if (event.sequence && event.sequence <= sequence) return;
          sequence = event.sequence ?? sequence;
          retries = 0;
          onEvent(event);
        },
        signal
      );
      if (signal.aborted) return;
      const run = await getRun(id);
      if (terminalStatuses.has(run.status)) return;
    } catch (error) {
      if (signal.aborted) return;
      if (++retries > 10) throw error;
    }
    onReconnect?.();
    await new Promise<void>((resolve) => {
      const finish = () => {
        clearTimeout(timer);
        signal.removeEventListener("abort", finish);
        resolve();
      };
      const timer = setTimeout(finish, Math.min(500 * 2 ** retries, 5000));
      signal.addEventListener("abort", finish, { once: true });
    });
  }
}
