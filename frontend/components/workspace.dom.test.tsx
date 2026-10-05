import "@/tests/setup";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RunComposer } from "./RunComposer";
import { RunHistory } from "./RunHistory";
import { EvidencePanel } from "./EvidencePanel";
import { CodeAttempts } from "./CodeAttempts";
import { ResultPanel } from "./ResultPanel";
import { makeAttempt, makeEvidence, makeRun } from "@/tests/fixtures";

describe("workspace interactions", () => {
  it("starts empty and submits configured context with the keyboard", async () => {
    const submit = vi.fn();
    const user = userEvent.setup();
    render(<RunComposer onSubmit={submit} pending={false} />);
    expect(screen.getByLabelText("Prompt")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Generate" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Advanced options" }));
    await user.type(screen.getByLabelText("Framework"), "FastAPI");
    fireEvent.change(screen.getByLabelText("Maximum repairs"), { target: { value: "2" } });
    await user.type(screen.getByLabelText("Prompt"), "Build an endpoint");
    fireEvent.keyDown(screen.getByLabelText("Prompt"), { key: "Enter", ctrlKey: true });
    expect(submit).toHaveBeenCalledWith(
      expect.objectContaining({
        prompt: "Build an endpoint",
        framework_hint: "FastAPI",
        max_retry: 2
      })
    );
  });
  it("searches history and opens the matching run", async () => {
    const open = vi.fn();
    const user = userEvent.setup();
    render(
      <RunHistory
        runs={[makeRun(), makeRun({ id: "run-2", prompt: "Rust parser" })]}
        loading={false}
        error={null}
        onNew={vi.fn()}
        onOpen={open}
        onRefresh={vi.fn()}
      />
    );
    await user.type(screen.getByLabelText("Search run history"), "Rust");
    expect(
      screen.queryByText("Write a Python function that adds two numbers.")
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Rust parser/ }));
    expect(open).toHaveBeenCalledWith("run-2");
  });
  it("links findings to code and claims to their evidence", async () => {
    const source = vi.fn();
    const user = userEvent.setup();
    render(<EvidencePanel evidence={makeEvidence()} onSource={source} />);
    await user.click(screen.getByRole("tab", { name: /Claims/ }));
    await user.click(screen.getByText("Adds two numbers"));
    await user.click(screen.getByRole("button", { name: "Evidence finding-" }));
    expect(screen.getByRole("tab", { name: /Findings/ })).toHaveAttribute("data-state", "active");
    await user.click(screen.getByRole("button", { name: "Line 2" }));
    expect(source).toHaveBeenCalledWith({ attempt: 1, start: 2, end: 2 });
  });
  it("shows unavailable measurements and provider failures", async () => {
    const user = userEvent.setup();
    render(<EvidencePanel evidence={makeEvidence()} />);
    await user.click(screen.getByRole("tab", { name: "Metrics" }));
    expect(screen.getAllByText("Unavailable")).toHaveLength(2);
    await user.click(screen.getByRole("tab", { name: "Judges" }));
    expect(screen.getByText("Provider quota exceeded.")).toBeInTheDocument();
    expect(screen.getByText(/0\/3 valid responses/)).toBeInTheDocument();
  });
  it("shows selected historical code and disables changes for the initial attempt", () => {
    render(
      <CodeAttempts
        attempts={[makeAttempt(1), makeAttempt(2)]}
        streamed={{}}
        selectedAttempt={1}
        language="python"
      />
    );
    expect(screen.getByText("python", { exact: false })).toBeDefined();
    expect(screen.getByRole("tab", { name: "Changes" })).toBeDisabled();
    expect(screen.getByText(/attempt 1/)).toBeInTheDocument();
  });
  it("keeps the warning decision visible for completed runs", () => {
    render(<ResultPanel run={makeRun()} />);
    expect(screen.getByText("warn")).toBeInTheDocument();
    expect(screen.getByText("Some claims remain uncertain.")).toBeInTheDocument();
  });
  it("renders retained partial claims in a zero-attempt failure", async () => {
    const user = userEvent.setup();
    const partial = makeAttempt();
    render(
      <EvidencePanel
        evidence={makeEvidence({
          run: makeRun({ status: "failed" }),
          attempts: [],
          partial: { output: partial.output, claims: partial.claims }
        })}
      />
    );
    expect(screen.getByText(/No completed attempts yet/)).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: /Claims/ }));
    expect(screen.getByText("Adds two numbers")).toBeInTheDocument();
  });
});
