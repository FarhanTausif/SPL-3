"use client";
import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import {
  cancelRun,
  clarifyRun,
  createRun,
  getEvidence,
  getHealth,
  listRuns,
  terminalStatuses,
  watchRun,
  type AttemptEvidence,
  type RunCreate,
  type RunEvidence,
  type RunStreamEvent,
  type RunSummary
} from "./api";
import type { HealthResponse } from "./contracts.generated";
import { defaultStages, type StageView } from "@/components/Workflow";

export type WorkspaceState = {
  run: RunSummary | null;
  evidence: RunEvidence | null;
  attempts: AttemptEvidence[];
  streamed: Record<number, string>;
  stages: StageView[];
  selectedAttempt: number | null;
  connection: "idle" | "connecting" | "connected" | "reconnecting" | "offline";
  opening: boolean;
  submitting: boolean;
  actionPending: boolean;
  error: string | null;
};
const fresh = (): WorkspaceState => ({
  run: null,
  evidence: null,
  attempts: [],
  streamed: {},
  stages: defaultStages.map((s) => ({ ...s })),
  selectedAttempt: null,
  connection: "idle",
  opening: false,
  submitting: false,
  actionPending: false,
  error: null
});
type Action =
  | { type: "reset" }
  | { type: "opening" }
  | { type: "snapshot"; evidence: RunEvidence }
  | { type: "event"; event: RunStreamEvent }
  | { type: "patch"; patch: Partial<WorkspaceState> }
  | { type: "select"; attempt: number | null };
export function workspaceReducer(state: WorkspaceState, action: Action): WorkspaceState {
  if (action.type === "reset") return fresh();
  if (action.type === "opening") return { ...fresh(), opening: true, connection: "connecting" };
  if (action.type === "patch") return { ...state, ...action.patch };
  if (action.type === "select") return { ...state, selectedAttempt: action.attempt };
  if (action.type === "snapshot") {
    const saved = new Map(state.attempts.map((attempt) => [attempt.output.attempt_no, attempt]));
    action.evidence.attempts.forEach((attempt) => saved.set(attempt.output.attempt_no, attempt));
    return {
      ...state,
      run: action.evidence.run,
      evidence: action.evidence,
      attempts: Array.from(saved.values()).sort(
        (a, b) => a.output.attempt_no - b.output.attempt_no
      ),
      opening: false,
      submitting: false
    };
  }
  const event = action.event;
  let next = { ...state, connection: "connected" as const };
  if (event.type === "stage") {
    if (
      event.stage === "generation" &&
      event.status === "running" &&
      event.attempt_no &&
      event.attempt_no > Math.max(0, ...state.stages.map((s) => s.attemptNo ?? 0))
    )
      next.stages = defaultStages.map((s) =>
        s.key === "intake" || s.key === "clarification"
          ? state.stages.find((old) => old.key === s.key)!
          : { ...s }
      );
    next.stages = next.stages.map((s) =>
      s.key === event.stage
        ? { ...s, status: event.status, progress: event.progress, attemptNo: event.attempt_no }
        : s
    );
    if (next.run && !terminalStatuses.has(next.run.status))
      next.run = { ...next.run, status: "running" };
  } else if (event.type === "token")
    next.streamed = {
      ...state.streamed,
      [event.attempt_no]: (state.streamed[event.attempt_no] ?? "") + event.text
    };
  else if (event.type === "context" || event.type === "run_created") {
    if (state.run) next.run = { ...state.run, inferred: event.inferred };
  } else if (event.type === "attempt_completed")
    next.attempts = [
      ...state.attempts.filter((a) => a.output.attempt_no !== event.attempt.output.attempt_no),
      event.attempt
    ].sort((a, b) => a.output.attempt_no - b.output.attempt_no);
  else if (event.type === "run_completed")
    next = { ...next, run: event.run, evidence: event.evidence, attempts: event.evidence.attempts };
  else if (event.type === "clarification") next.run = event.run;
  else if (event.type === "run_cancelled" || event.type === "run_interrupted") {
    if (state.run)
      next.run = {
        ...state.run,
        status: event.type === "run_cancelled" ? "cancelled" : "interrupted"
      };
  } else if (event.type === "error") {
    next.error = event.message;
    if (state.run) next.run = { ...state.run, status: "failed", error: event.message };
  }
  return next;
}

export function useWorkspace() {
  const [state, dispatch] = useReducer(workspaceReducer, undefined, fresh);
  const [history, setHistory] = useState<RunSummary[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const epoch = useRef(0);
  const watcher = useRef<AbortController | null>(null);
  const alive = useRef(true);
  const refreshHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const items = await listRuns();
      if (alive.current) {
        setHistory(items);
        setHistoryError(null);
      }
    } catch {
      if (alive.current) setHistoryError("History is unavailable. Check the API connection.");
    } finally {
      if (alive.current) setHistoryLoading(false);
    }
  }, []);
  const openRun = useCallback(
    async (id: string) => {
      const ticket = ++epoch.current;
      watcher.current?.abort();
      const controller = new AbortController();
      watcher.current = controller;
      dispatch({ type: "opening" });
      localStorage.setItem("dehalu-active-run", id);
      let snapshotVersion = 0;
      const current = () => ticket === epoch.current && !controller.signal.aborted && alive.current;
      const snapshot = async () => {
        const version = ++snapshotVersion;
        const evidence = await getEvidence(id);
        if (current() && version === snapshotVersion) dispatch({ type: "snapshot", evidence });
      };
      try {
        await snapshot();
        if (!current()) return;
        await watchRun(
          id,
          (event) => {
            if (!current()) return;
            if (
              event.type !== "stage" &&
              event.type !== "token" &&
              event.type !== "context" &&
              event.type !== "run_created"
            )
              ++snapshotVersion;
            dispatch({ type: "event", event });
            // Durable checkpoints provide partial evidence during long judge calls.
            if (event.type === "stage" && event.status === "done") void snapshot().catch(() => {});
          },
          controller.signal,
          () => {
            if (current()) dispatch({ type: "patch", patch: { connection: "reconnecting" } });
          }
        );
        if (!current()) return;
        await snapshot();
        if (current()) {
          dispatch({ type: "patch", patch: { connection: "idle" } });
          void refreshHistory();
        }
      } catch (error) {
        if (current())
          dispatch({
            type: "patch",
            patch: {
              opening: false,
              submitting: false,
              connection: "offline",
              error: error instanceof Error ? error.message : "Unable to open run."
            }
          });
      }
    },
    [refreshHistory]
  );
  useEffect(() => {
    alive.current = true;
    void refreshHistory();
    void getHealth()
      .then((h) => {
        if (alive.current) setHealth(h);
      })
      .catch(() => {});
    const saved = localStorage.getItem("dehalu-active-run");
    if (saved) void openRun(saved);
    const generation = epoch;
    return () => {
      alive.current = false;
      ++generation.current;
      watcher.current?.abort();
    };
  }, [openRun, refreshHistory]);
  function newRun() {
    ++epoch.current;
    watcher.current?.abort();
    localStorage.removeItem("dehalu-active-run");
    dispatch({ type: "reset" });
  }
  async function submit(payload: RunCreate) {
    const ticket = epoch.current;
    dispatch({ type: "patch", patch: { submitting: true, error: null } });
    try {
      const run = await createRun(payload);
      if (ticket !== epoch.current || !alive.current) return;
      setHistory((previous) => [run, ...previous.filter((r) => r.id !== run.id)]);
      void openRun(run.id);
    } catch (error) {
      if (ticket === epoch.current)
        dispatch({
          type: "patch",
          patch: {
            submitting: false,
            error: error instanceof Error ? error.message : "Submission failed."
          }
        });
    }
  }
  async function cancel() {
    if (!state.run) return;
    const id = state.run.id;
    const ticket = epoch.current;
    dispatch({ type: "patch", patch: { actionPending: true, error: null } });
    try {
      const cancelled = await cancelRun(id);
      if (ticket === epoch.current) {
        watcher.current?.abort();
        dispatch({ type: "patch", patch: { run: cancelled, connection: "idle" } });
        const evidence = await getEvidence(id);
        if (ticket === epoch.current) {
          dispatch({ type: "snapshot", evidence });
          dispatch({ type: "patch", patch: { connection: "idle" } });
          void refreshHistory();
        }
      }
    } catch (error) {
      if (ticket === epoch.current)
        dispatch({
          type: "patch",
          patch: { error: error instanceof Error ? error.message : "Cancellation failed." }
        });
    } finally {
      if (ticket === epoch.current) dispatch({ type: "patch", patch: { actionPending: false } });
    }
  }
  async function clarify(answers: string) {
    if (!state.run) return;
    const id = state.run.id;
    const ticket = epoch.current;
    dispatch({ type: "patch", patch: { actionPending: true, error: null } });
    try {
      await clarifyRun(id, answers);
      if (ticket === epoch.current) void openRun(id);
    } catch (error) {
      if (ticket === epoch.current)
        dispatch({
          type: "patch",
          patch: {
            actionPending: false,
            error: error instanceof Error ? error.message : "Clarification failed."
          }
        });
    }
  }
  const evidence = state.evidence
    ? { ...state.evidence, run: state.run ?? state.evidence.run, attempts: state.attempts }
    : null;
  return {
    ...state,
    evidence,
    history,
    historyLoading,
    historyError,
    health,
    openRun,
    newRun,
    submit,
    cancel,
    clarify,
    refreshHistory,
    selectAttempt: (attempt: number | null) => dispatch({ type: "select", attempt })
  };
}
