import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { EvidencePanel } from "./EvidencePanel";
import type { RunEvidence } from "@/lib/api";

const emptyRun: RunEvidence = {
  run: { id: "r", status: "failed", prompt: "task", inferred: { language: "python", framework: null, runtime: null, libraries: [], requirements: [], constraints: [], uncertain_assumptions: [], clarification_questions: [], needs_clarification: false }, model_name: "m", max_retry: 0, created_at: null, completed_at: null, error: "provider unavailable", final_output: null, policy_decision: null },
  attempts: [], partial: { claims: [{ claim_text: "retained claim" }] }
};

describe("empty and interrupted evidence", () => {
  it("renders a failed run with no completed attempts and retained partial evidence", () => {
    const html = renderToStaticMarkup(<EvidencePanel evidence={emptyRun} />);
    expect(html).toContain("No completed attempts");
    expect(html).toContain("retained claim");
  });
  it("renders no selected run", () => {
    expect(renderToStaticMarkup(<EvidencePanel evidence={null} />)).toContain("Claims, findings");
  });
});
