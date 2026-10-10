import "@/tests/setup";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "./api";
import { useWorkspace } from "./use-workspace";
import { makeAttempt, makeEvidence, makeRun, health } from "@/tests/fixtures";
vi.mock("./api", async (original) => ({
  ...(await original<typeof import("./api")>()),
  listRuns: vi.fn(),
  getHealth: vi.fn(),
  getEvidence: vi.fn(),
  watchRun: vi.fn(),
  createRun: vi.fn(),
  cancelRun: vi.fn(),
  clarifyRun: vi.fn()
}));
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listRuns).mockResolvedValue([]);
  vi.mocked(api.getHealth).mockResolvedValue(health);
  vi.mocked(api.getEvidence).mockResolvedValue(makeEvidence());
  vi.mocked(api.watchRun).mockImplementation(
    (_id, _callback, signal) =>
      new Promise((resolve) => signal.addEventListener("abort", () => resolve(), { once: true }))
  );
});
describe("durable workspace lifecycle", () => {
  it("restores the saved run and reconnects without changing its execution status", async () => {
    localStorage.setItem("dehalu-active-run", "run-1");
    vi.mocked(api.getEvidence).mockResolvedValue(
      makeEvidence({ run: makeRun({ status: "running" }) })
    );
    const { result } = renderHook(() => useWorkspace());
    await waitFor(() => expect(result.current.run?.id).toBe("run-1"));
    act(() => vi.mocked(api.watchRun).mock.calls[0][3]?.());
    expect(result.current.connection).toBe("reconnecting");
    expect(result.current.run?.status).toBe("running");
  });
  it("ignores responses from a run that was replaced", async () => {
    let resolve!: (e: ReturnType<typeof makeEvidence>) => void;
    vi.mocked(api.getEvidence).mockImplementation((id) =>
      id === "old"
        ? new Promise((r) => {
            resolve = r;
          })
        : Promise.resolve(makeEvidence({ run: makeRun({ id: "new" }) }))
    );
    const { result } = renderHook(() => useWorkspace());
    act(() => {
      void result.current.openRun("old");
    });
    act(() => {
      void result.current.openRun("new");
    });
    await waitFor(() => expect(result.current.run?.id).toBe("new"));
    await act(async () => resolve(makeEvidence({ run: makeRun({ id: "old" }) })));
    expect(result.current.run?.id).toBe("new");
  });
  it("holds historical attempt selection as new attempts arrive", async () => {
    const { result } = renderHook(() => useWorkspace());
    act(() => {
      void result.current.openRun("run-1");
    });
    await waitFor(() => expect(api.watchRun).toHaveBeenCalled());
    act(() => result.current.selectAttempt(1));
    act(() =>
      vi
        .mocked(api.watchRun)
        .mock.calls.at(-1)![1]({ type: "attempt_completed", attempt: makeAttempt(2) })
    );
    expect(result.current.selectedAttempt).toBe(1);
    expect(result.current.attempts).toHaveLength(2);
    act(() => result.current.selectAttempt(null));
    expect(result.current.selectedAttempt).toBeNull();
  });
  it("starts a new draft without cancelling the background run", async () => {
    const { result } = renderHook(() => useWorkspace());
    act(() => {
      void result.current.openRun("run-1");
    });
    await waitFor(() => expect(result.current.run).not.toBeNull());
    act(() => result.current.newRun());
    expect(result.current.run).toBeNull();
    expect(api.cancelRun).not.toHaveBeenCalled();
    expect(localStorage.getItem("dehalu-active-run")).toBeNull();
  });
  it("submits clarification on the same run and preserves evidence after cancellation", async () => {
    const clarification = makeEvidence({ run: makeRun({ status: "needs_clarification" }) });
    vi.mocked(api.getEvidence).mockResolvedValue(clarification);
    vi.mocked(api.clarifyRun).mockResolvedValue(makeRun({ status: "queued" }));
    const { result } = renderHook(() => useWorkspace());
    act(() => {
      void result.current.openRun("run-1");
    });
    await waitFor(() => expect(result.current.run).not.toBeNull());
    await act(async () => {
      await result.current.clarify("Python 3.11");
    });
    expect(api.clarifyRun).toHaveBeenCalledWith("run-1", "Python 3.11", false);
    vi.mocked(api.cancelRun).mockResolvedValue(makeRun({ status: "cancelled" }));
    vi.mocked(api.getEvidence).mockResolvedValue(
      makeEvidence({ run: makeRun({ status: "cancelled" }) })
    );
    await act(async () => {
      await result.current.cancel();
    });
    expect(result.current.run?.status).toBe("cancelled");
    expect(result.current.attempts).toHaveLength(1);
  });
});

it("does not let a late checkpoint erase a newly completed attempt", async () => {
  let finish!: (value: ReturnType<typeof makeEvidence>) => void;
  vi.mocked(api.getEvidence)
    .mockResolvedValueOnce(makeEvidence({ run: makeRun({ status: "running" }) }))
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        })
    );
  const { result } = renderHook(() => useWorkspace());
  act(() => {
    void result.current.openRun("run-1");
  });
  await waitFor(() => expect(api.watchRun).toHaveBeenCalled());
  const emit = vi.mocked(api.watchRun).mock.calls.at(-1)![1];
  act(() => emit({ type: "stage", stage: "policy", status: "done", progress: 100, attempt_no: 2 }));
  act(() => emit({ type: "attempt_completed", attempt: makeAttempt(2) }));
  await act(async () => finish(makeEvidence({ run: makeRun({ status: "running" }) })));
  expect(result.current.attempts.map((attempt) => attempt.output.attempt_no)).toEqual([1, 2]);
});

it("replaces invalid generation tokens after a format recovery reset", async () => {
  let emit: Parameters<typeof api.watchRun>[1] | undefined;
  localStorage.setItem("dehalu-active-run", "run-1");
  vi.mocked(api.getEvidence).mockResolvedValue(
    makeEvidence({ run: makeRun({ status: "running" }) })
  );
  vi.mocked(api.watchRun).mockImplementation((_id, callback, signal) => {
    emit = callback;
    return new Promise((resolve) =>
      signal.addEventListener("abort", () => resolve(), { once: true })
    );
  });
  const { result } = renderHook(() => useWorkspace());
  await waitFor(() => expect(emit).toBeDefined());
  act(() => {
    emit!({ type: "token", attempt_no: 2, text: "Old invalid response" });
    emit!({ type: "generation_reset", attempt_no: 2 });
    emit!({ type: "token", attempt_no: 2, text: "```python\ndef repaired(): pass\n```" });
  });
  expect(result.current.streamed[2]).toBe("```python\ndef repaired(): pass\n```");
});
