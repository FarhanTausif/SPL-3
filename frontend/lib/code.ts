import type { AttemptEvidence } from "./api";
export type AttemptDraft = { attempt_no: number; code: string };
export type DiffLine = { type: "same" | "add" | "remove"; text: string };
export function mergeAttempts(
  attempts: AttemptEvidence[],
  streamed: Record<number, string>
): AttemptDraft[] {
  const map = new Map<number, string>();
  for (const attempt of attempts) {
    map.set(attempt.output.attempt_no, attempt.output.code);
  }
  for (const [attemptNo, code] of Object.entries(streamed)) {
    if (code.trim() && !map.has(Number(attemptNo))) {
      const artifact = code.match(/```[^\n]*\n([\s\S]*?)(?:```|$)/);
      map.set(Number(attemptNo), artifact?.[1] ?? code);
    }
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a - b)
    .map(([attempt_no, code]) => ({ attempt_no, code }));
}

export function buildLineDiff(before: string, after: string): DiffLine[] {
  const a = before.split("\n");
  const b = after.split("\n");
  if (a.length * b.length > 1_000_000)
    return [
      ...a.map((text) => ({ type: "remove" as const, text })),
      ...b.map((text) => ({ type: "add" as const, text }))
    ];
  const rows = a.length + 1;
  const cols = b.length + 1;
  const table = Array.from({ length: rows }, () => Array<number>(cols).fill(0));

  for (let i = a.length - 1; i >= 0; i -= 1) {
    for (let j = b.length - 1; j >= 0; j -= 1) {
      table[i][j] =
        a[i] === b[j] ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1]);
    }
  }

  const lines: DiffLine[] = [];
  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      lines.push({ type: "same", text: a[i] });
      i += 1;
      j += 1;
    } else if (table[i + 1][j] >= table[i][j + 1]) {
      lines.push({ type: "remove", text: a[i] });
      i += 1;
    } else {
      lines.push({ type: "add", text: b[j] });
      j += 1;
    }
  }
  while (i < a.length) {
    lines.push({ type: "remove", text: a[i] });
    i += 1;
  }
  while (j < b.length) {
    lines.push({ type: "add", text: b[j] });
    j += 1;
  }
  return lines.length ? lines : [{ type: "same", text: "" }];
}
