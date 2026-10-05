import "@/tests/setup";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import Home from "./page";
import * as api from "@/lib/api";
import { makeEvidence, makeRun, health } from "@/tests/fixtures";
vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
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
  vi.mocked(api.watchRun).mockImplementation(
    (_id, _cb, signal) =>
      new Promise((resolve) => signal.addEventListener("abort", () => resolve(), { once: true }))
  );
});
it("shows clarification questions with the answer form and resumes the same run", async () => {
  const user = userEvent.setup();
  const run = makeRun({
    status: "needs_clarification",
    inferred: {
      ...makeRun().inferred,
      needs_clarification: true,
      clarification_questions: ["Which runtime should be used?"]
    }
  });
  vi.mocked(api.createRun).mockResolvedValue(makeRun({ status: "queued" }));
  vi.mocked(api.getEvidence).mockResolvedValue(makeEvidence({ run, attempts: [] }));
  vi.mocked(api.clarifyRun).mockResolvedValue(makeRun({ status: "queued" }));
  render(<Home />);
  await user.type(screen.getByLabelText("Prompt", { exact: true }), "Create a service");
  await user.click(screen.getByRole("button", { name: "Generate" }));
  await screen.findByText("Which runtime should be used?");
  await user.type(screen.getByLabelText("Clarification answers"), "Python 3.11");
  await user.click(screen.getByRole("button", { name: "Resume run" }));
  await waitFor(() => expect(api.clarifyRun).toHaveBeenCalledWith("run-1", "Python 3.11"));
});
it("cancels from the header while retaining completed evidence", async () => {
  const user = userEvent.setup();
  localStorage.setItem("dehalu-active-run", "run-1");
  vi.mocked(api.getEvidence).mockResolvedValue(
    makeEvidence({ run: makeRun({ status: "running" }) })
  );
  vi.mocked(api.cancelRun).mockImplementation(async () => {
    vi.mocked(api.getEvidence).mockResolvedValue(
      makeEvidence({ run: makeRun({ status: "cancelled" }) })
    );
    return makeRun({ status: "cancelled" });
  });
  render(<Home />);
  await user.click(await screen.findByRole("button", { name: "Cancel" }));
  await waitFor(() =>
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument()
  );
  await user.click(screen.getByRole("tab", { name: "Evidence" }));
  expect(screen.getByText("Analyzer coverage")).toBeInTheDocument();
});
