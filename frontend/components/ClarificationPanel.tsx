"use client";
import { useState } from "react";
import type { InferenceResult } from "@/lib/api";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
export function ClarificationPanel({
  inferred,
  pending,
  onContinue
}: {
  inferred: InferenceResult;
  pending: boolean;
  onContinue: (answers: string, skip?: boolean) => void;
}) {
  const questions = inferred.clarification_details?.length
    ? inferred.clarification_details
    : inferred.clarification_questions.slice(0, 3).map((question) => ({
        question,
        choices: [
          {
            label: "Choose for me",
            value: "Use sensible defaults for my original request.",
            recommended: true
          },
          {
            label: "Keep it simple",
            value: "Implement the simplest useful version of my original request.",
            recommended: false
          },
          {
            label: "Handle more cases",
            value: "Include input validation and common edge cases.",
            recommended: false
          }
        ]
      }));
  const [selected, setSelected] = useState<Record<number, string>>({});
  const [custom, setCustom] = useState<Record<number, string>>({});
  const answers = () =>
    questions
      .map((q, i) => {
        const value =
          custom[i]?.trim() || selected[i] || q.choices.find((c) => c.recommended)!.value;
        // Preserve the legacy single free-text answer contract.
        return questions.length === 1 && custom[i]?.trim() ? value : `${q.question}\n${value}`;
      })
      .join("\n\n");
  return (
    <form
      className="rounded-lg border border-sky-200 bg-active-surface p-4"
      onSubmit={(event) => {
        event.preventDefault();
        onContinue(answers());
      }}
    >
      <h2 className="text-base font-semibold">A little more context</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        One quick round, then generation starts. You can also let DeHalu choose.
      </p>
      <div className="my-4 space-y-5">
        {questions.map((q, i) => (
          <fieldset key={q.question} disabled={pending} className="min-w-0 space-y-2">
            <legend className="mb-2 text-sm font-medium">{q.question}</legend>
            {q.choices.map((choice, j) => (
              <label
                key={j}
                className="flex cursor-pointer items-start gap-3 rounded-md border bg-card p-3 text-sm"
              >
                <input
                  type="radio"
                  className="mt-1 shrink-0"
                  name={`question-${i}`}
                  checked={
                    (selected[i] ?? q.choices.find((c) => c.recommended)!.value) === choice.value
                  }
                  onChange={() => setSelected((values) => ({ ...values, [i]: choice.value }))}
                />
                <span>
                  {choice.label}
                  {choice.recommended && (
                    <span className="ml-2 text-xs font-medium text-primary">(Recommended)</span>
                  )}
                </span>
              </label>
            ))}
            <label className="block text-xs font-medium" htmlFor={`custom-${i}`}>
              Or write your own answer
            </label>
            <Textarea
              id={`custom-${i}`}
              aria-label={
                questions.length === 1 ? "Clarification answers" : `Custom answer: ${q.question}`
              }
              value={custom[i] ?? ""}
              onChange={(event) => setCustom((values) => ({ ...values, [i]: event.target.value }))}
              placeholder="Your answer takes priority over the selected option…"
              className="bg-card"
            />
          </fieldset>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={pending}>
          {pending ? "Resuming…" : "Continue"}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={pending}
          onClick={() => onContinue(answers(), true)}
        >
          Run Anyway
        </Button>
      </div>
    </form>
  );
}
