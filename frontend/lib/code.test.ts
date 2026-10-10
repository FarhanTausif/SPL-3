import { expect, it } from "vitest";
import { mergeAttempts, streamedCodeArtifact } from "./code";
import { makeAttempt } from "@/tests/fixtures";
it("never presents prose or JSON metadata as streamed code", () => {
  expect(
    mergeAttempts([], { 2: "Based on the provided evidence, processor.predict is uncertain." })
  ).toEqual([]);
  expect(streamedCodeArtifact('```json\n{"assumptions": []}\n```')).toBe("");
});
it("streams only source lines and excludes explanation after the fence", () => {
  const code = "def add(a, b):\n    return a + b";
  expect(
    streamedCodeArtifact(`Here is code:\n\`\`\`python\n${code}\n\`\`\`\nThis is explanation.`)
  ).toBe(code + "\n");
  expect(streamedCodeArtifact(`\`\`\`json\n{}\n\`\`\`\n\`\`\`python\n${code}`)).toBe(code);
  expect(streamedCodeArtifact("```py")).toBe("");
});
it("keeps the last completed code when the repair response is prose", () => {
  const first = makeAttempt();
  expect(mergeAttempts([first], { 2: "The claim is uncertain." })).toEqual([
    { attempt_no: 1, code: first.output.code }
  ]);
});
