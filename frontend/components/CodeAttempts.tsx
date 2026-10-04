"use client";

import { Check, Code2, Copy, GitCompareArrows } from "lucide-react";
import { useMemo, useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/cjs/styles/prism";
import type { AttemptEvidence } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

type AttemptDraft = {
  attempt_no: number;
  code: string;
};

type DiffLine = {
  type: "same" | "add" | "remove";
  text: string;
};

export function CodeAttempts({
  attempts,
  streamed,
  language = "text"
}: {
  attempts: AttemptEvidence[];
  streamed: Record<number, string>;
  language?: string;
}) {
  const [selectedAttempt, setSelectedAttempt] = useState(0);
  const drafts = useMemo(() => mergeAttempts(attempts, streamed), [attempts, streamed]);
  const initial = drafts[0];
  const latest = drafts.find(attempt => attempt.attempt_no === selectedAttempt) ?? drafts[drafts.length - 1];
  const diff = useMemo(() => buildLineDiff(initial?.code ?? "", latest?.code ?? ""), [initial?.code, latest?.code]);

  if (!initial) {
    return (
    <Card className="min-h-[360px] min-w-0 max-w-full overflow-hidden border-stone-200/80 bg-white/90 shadow-sm">
        <CardHeader className="p-5">
          <CardTitle className="flex items-center gap-2">
            <Code2 className="size-4 text-emerald-700" />
            Generated Code
          </CardTitle>
          <CardDescription>Code will stream here as soon as generation starts.</CardDescription>
        </CardHeader>
        <CardContent className="p-5 pt-0">
          <div className="grid min-h-[240px] place-items-center rounded-lg border border-dashed border-stone-300 bg-stone-50 text-sm text-stone-500">
            Waiting for generation
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card id={attempts[attempts.length - 1]?.output.id} className="min-w-0 max-w-full overflow-hidden border-stone-200/80 bg-white/90 shadow-sm">
      <CardHeader className="flex-row items-start justify-between gap-4 p-5 pb-3">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Code2 className="size-4 text-emerald-700" />
            Generated Code
          </CardTitle>
          <CardDescription>Initial, latest, and line-level diff are preserved across repair attempts.</CardDescription>
          <label className="mt-2 block text-xs text-stone-600">Compare with initial <select aria-label="Code attempt" className="ml-2 rounded border p-1" value={selectedAttempt} onChange={event => setSelectedAttempt(Number(event.target.value))}>
            <option value={0}>Latest attempt</option>
            {drafts.map(attempt => <option key={attempt.attempt_no} value={attempt.attempt_no}>Attempt {attempt.attempt_no}</option>)}
          </select></label>
        </div>
      </CardHeader>
      <CardContent className="min-w-0 p-5 pt-0">
        <Tabs defaultValue="latest" className="min-w-0 max-w-full">
          <TabsList className="h-auto w-full justify-start overflow-x-auto rounded-md bg-stone-100 p-1">
            <TabsTrigger value="initial" className="shrink-0">Initial</TabsTrigger>
            <TabsTrigger value="latest" className="shrink-0">Latest</TabsTrigger>
            <TabsTrigger value="diff" className="shrink-0">
              <GitCompareArrows className="size-3.5" />
              Diff
            </TabsTrigger>
          </TabsList>
          <TabsContent value="initial" className="min-w-0">
            <CodeBlock label={`Initial generation · attempt ${initial.attempt_no}`} code={initial.code} language={language} />
          </TabsContent>
          <TabsContent value="latest" className="min-w-0">
            <CodeBlock label={`Selected generation · attempt ${latest.attempt_no}`} code={latest.code} language={language} />
          </TabsContent>
          <TabsContent value="diff" className="min-w-0">
            <div className="max-h-[620px] max-w-full overflow-auto rounded-lg border border-stone-800 bg-[#1e1e1e] py-3 text-[13px] leading-6 shadow-inner">
              {diff.map((line, index) => (
                <div
                  className={
                    line.type === "add"
                      ? "grid grid-cols-[28px_minmax(0,1fr)] gap-2 bg-emerald-500/15 px-3 text-emerald-50"
                      : line.type === "remove"
                        ? "grid grid-cols-[28px_minmax(0,1fr)] gap-2 bg-red-500/15 px-3 text-red-50"
                        : "grid grid-cols-[28px_minmax(0,1fr)] gap-2 px-3 text-stone-200"
                  }
                  key={`${line.type}-${index}-${line.text}`}
                >
                  <span className="select-none text-stone-500">{line.type === "add" ? "+" : line.type === "remove" ? "-" : " "}</span>
                  <DiffCode line={line.text || " "} language={language} />
                </div>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

function CodeBlock({ label, code, language }: { label: string; code: string; language: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  }

  return (
    <div className="max-w-full overflow-hidden rounded-lg border border-stone-800 bg-[#1e1e1e] shadow-inner">
      <div className="flex items-center justify-between gap-3 border-b border-stone-800 bg-[#252526] px-3 py-2 text-xs text-stone-300">
        <span className="truncate">{label}</span>
        <Button variant="ghost" size="icon" className="h-8 w-8 text-stone-200 hover:bg-stone-700 hover:text-white" type="button" onClick={copy} aria-label="Copy code">
          {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
        </Button>
      </div>
      <SyntaxHighlighter
        language={language}
        style={vscDarkPlus}
        codeTagProps={{
          style: {
            whiteSpace: "pre-wrap",
            wordBreak: "break-word"
          }
        }}
        customStyle={{
          margin: 0,
          minHeight: 320,
          maxHeight: 620,
          width: "100%",
          maxWidth: "100%",
          overflow: "auto",
          background: "#1e1e1e",
          fontSize: 13,
          lineHeight: 1.65,
          padding: 16
        }}
        showLineNumbers
        wrapLongLines
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}

function DiffCode({ line, language }: { line: string; language: string }) {
  return (
    <SyntaxHighlighter
      language={language}
      style={vscDarkPlus}
      PreTag="span"
      CodeTag="span"
      codeTagProps={{
        style: {
          whiteSpace: "pre-wrap",
          wordBreak: "break-word"
        }
      }}
      customStyle={{
        margin: 0,
        padding: 0,
        background: "transparent",
        display: "inline",
        fontSize: 13,
        lineHeight: 1.5
      }}
      wrapLongLines
    >
      {line}
    </SyntaxHighlighter>
  );
}

function mergeAttempts(attempts: AttemptEvidence[], streamed: Record<number, string>): AttemptDraft[] {
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

function buildLineDiff(before: string, after: string): DiffLine[] {
  const a = before.split("\n");
  const b = after.split("\n");
  if (a.length * b.length > 1_000_000) return [...a.map(text => ({ type: "remove" as const, text })), ...b.map(text => ({ type: "add" as const, text }))];
  const rows = a.length + 1;
  const cols = b.length + 1;
  const table = Array.from({ length: rows }, () => Array<number>(cols).fill(0));

  for (let i = a.length - 1; i >= 0; i -= 1) {
    for (let j = b.length - 1; j >= 0; j -= 1) {
      table[i][j] = a[i] === b[j] ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1]);
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
