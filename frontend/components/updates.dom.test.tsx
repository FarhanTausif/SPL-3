import "@/tests/setup";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { ClarificationPanel } from "./ClarificationPanel";
import { MetricsChart } from "./MetricsChart";
import { CodeAttempts } from "./CodeAttempts";
import { ProviderStatus } from "./ProviderStatus";
import { makeRun, makeAttempt, health } from "@/tests/fixtures";

const inferred = {
  ...makeRun().inferred,
  needs_clarification: true,
  clarification_questions: ["How should it work?"],
  clarification_details: [
    {
      question: "How should it work?",
      choices: [
        {
          label: "Simple calculator",
          value: "Add two numbers",
          recommended: true
        },
        {
          label: "Scientific calculator",
          value: "Support scientific functions",
          recommended: false
        },
        {
          label: "History calculator",
          value: "Save past calculations",
          recommended: false
        }
      ]
    }
  ]
};
it("offers three options with a recommendation and custom text takes priority", async () => {
  const user = userEvent.setup(),
    submit = vi.fn();
  render(<ClarificationPanel inferred={inferred} pending={false} onContinue={submit} />);
  expect(screen.getAllByRole("radio")).toHaveLength(3);
  expect(screen.getByText("(Recommended)")).toBeVisible();
  await user.click(screen.getByLabelText("Scientific calculator"));
  await user.type(screen.getByLabelText("Clarification answers"), "Only multiplication");
  await user.click(screen.getByRole("button", { name: "Continue" }));
  expect(submit).toHaveBeenCalledWith("Only multiplication");
});
it("Run Anyway submits recommended defaults and skips another round", async () => {
  const user = userEvent.setup(),
    submit = vi.fn();
  render(<ClarificationPanel inferred={inferred} pending={false} onContinue={submit} />);
  await user.click(screen.getByRole("button", { name: "Run Anyway" }));
  expect(submit).toHaveBeenCalledWith("How should it work?\nAdd two numbers", true);
});
it.each([0.1, 0.3, 0.8])("charts real risk changes to %s without assuming improvement", (risk) => {
  const first = makeAttempt(1),
    last = makeAttempt(2);
  first.metrics.hallucination_risk_score = 0.3;
  last.metrics.hallucination_risk_score = risk;
  render(<MetricsChart attempts={[last, first]} />);
  expect(
    screen.getByLabelText(`Attempt 2: Hallucination risk ${(risk * 100).toFixed(1)}%`)
  ).toBeInTheDocument();
  const expected = (risk - 0.3) * 100;
  expect(
    screen.getByText(
      `30.0% → ${(risk * 100).toFixed(1)}% · ${expected > 0 ? "+" : ""}${expected.toFixed(1)} pp`
    )
  ).toBeVisible();
});
it("shows an honest single-attempt chart", () => {
  render(<MetricsChart attempts={[makeAttempt()]} />);
  expect(screen.getByText(/One completed attempt/)).toBeVisible();
});
it("copies only the selected artifact from the code header", async () => {
  const user = userEvent.setup();
  const write = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
  const attempts = [makeAttempt(1), makeAttempt(2)];
  render(<CodeAttempts attempts={attempts} streamed={{}} selectedAttempt={1} />);
  await user.click(screen.getByRole("button", { name: "Copy code" }));
  expect(write).toHaveBeenCalledWith(attempts[0].output.code);
  expect(screen.getByText("Copied")).toBeVisible();
});
it("separates service degradation from configured unchecked judges and refreshes health", async () => {
  const user = userEvent.setup(),
    refresh = vi.fn().mockResolvedValue(undefined);
  render(
    <ProviderStatus
      health={{ ...health, status: "degraded", database: "unavailable" }}
      judges={[]}
      onRefresh={refresh}
    />
  );
  await user.click(screen.getByRole("button", { name: /Judges configured/ }));
  expect(screen.getByText(/Service health: degraded/)).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Refresh provider status" }));
  expect(refresh).toHaveBeenCalledOnce();
  expect(
    within(screen.getByRole("dialog")).getAllByText(/access and quota unchecked/)
  ).toHaveLength(3);
});

it("keeps generated explanations out of the code view", () => {
  const attempt = makeAttempt();
  attempt.output.explanation = "Based on the evidence, the claim is uncertain.";
  render(<CodeAttempts attempts={[attempt]} streamed={{ 2: attempt.output.explanation }} />);
  expect(screen.queryByText(/Based on the evidence/)).not.toBeInTheDocument();
  expect(screen.queryByText("Generation explanation")).not.toBeInTheDocument();
});
