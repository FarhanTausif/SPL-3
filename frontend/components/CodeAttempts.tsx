"use client";
import { useEffect, useMemo, useState } from "react";
import { Check, Code2, Copy, GitCompareArrows } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/cjs/styles/prism";
import type { AttemptEvidence } from "@/lib/api";
import { buildLineDiff, mergeAttempts } from "@/lib/code";
import { Button } from "./ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
export type SourceTarget = {
  attempt: number;
  start: number;
  end: number;
  nonce: number;
};
export function CodeAttempts({
  attempts,
  streamed,
  language = "text",
  selectedAttempt = null,
  sourceTarget
}: {
  attempts: AttemptEvidence[];
  streamed: Record<number, string>;
  language?: string;
  selectedAttempt?: number | null;
  sourceTarget?: SourceTarget | null;
}) {
  const drafts = useMemo(() => mergeAttempts(attempts, streamed), [attempts, streamed]);
  const initial = drafts[0];
  const selected =
    drafts.find((a) => a.attempt_no === selectedAttempt) ?? drafts[drafts.length - 1];
  const output = attempts.find((a) => a.output.attempt_no === selected?.attempt_no)?.output;
  const [tab, setTab] = useState("code");
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const [highlight, setHighlight] = useState<SourceTarget | null>(null);
  const diff = useMemo(
    () => buildLineDiff(initial?.code ?? "", selected?.code ?? ""),
    [initial?.code, selected?.code]
  );
  useEffect(() => {
    setTab("code");
    setCopied(false);
    setCopyError(false);
  }, [selected?.attempt_no]);
  useEffect(() => {
    if (!sourceTarget) return;
    setTab("code");
    setHighlight(sourceTarget);
    const frame = requestAnimationFrame(() =>
      document
        .getElementById(`code-${sourceTarget.attempt}-line-${sourceTarget.start}`)
        ?.scrollIntoView({
          block: "center",
          behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"
        })
    );
    const timer = setTimeout(() => setHighlight(null), 4000);
    return () => {
      cancelAnimationFrame(frame);
      clearTimeout(timer);
    };
  }, [sourceTarget]);
  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), 1500);
    return () => clearTimeout(timer);
  }, [copied]);
  if (!selected)
    return (
      <section className="flex min-h-80 flex-col items-center justify-center rounded-lg border border-dashed bg-card px-6 text-center">
        <Code2 className="mb-3 size-6 text-muted-foreground" />
        <h2 className="text-base font-medium">Waiting for generation</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Code appears here as generation starts.
        </p>
      </section>
    );
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(selected.code);
      setCopied(true);
      setCopyError(false);
    } catch {
      setCopyError(true);
    }
  };
  return (
    <section className="min-w-0" aria-label="Generated code">
      <Tabs value={tab} onValueChange={setTab}>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <TabsList>
            <TabsTrigger value="code">
              <Code2 className="size-4" />
              Code
            </TabsTrigger>
            <TabsTrigger value="changes" disabled={selected.attempt_no === initial.attempt_no}>
              <GitCompareArrows className="size-4" />
              Changes
            </TabsTrigger>
          </TabsList>
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs text-muted-foreground">
              {language} · attempt {selected.attempt_no}
            </span>
          </div>
        </div>
        {copyError && (
          <p role="alert" className="mb-2 text-xs text-danger">
            Clipboard unavailable. Select the code to copy it.
          </p>
        )}
        <TabsContent value="code" className="mt-0">
          <div className="editor min-w-0 max-w-full overflow-hidden rounded-lg border border-zinc-800 bg-[#161b22]">
            <div className="flex items-center gap-2 border-b border-zinc-800 px-4 py-2 font-mono text-xs text-zinc-400">
              <span className="size-1.5 rounded-full bg-emerald-500" />
              {output ? "Generated artifact" : "Streaming generation"}
              <span className="ml-auto">{selected.code.split("\n").length} lines</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={copy}
                aria-label="Copy code"
                className="shrink-0 text-zinc-200 hover:bg-zinc-800 hover:text-white"
              >
                {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
                {copied ? "Copied" : "Copy code"}
              </Button>
            </div>
            <SyntaxHighlighter
              language={language === "cpp" ? "cpp" : language}
              style={vscDarkPlus}
              showLineNumbers
              wrapLongLines
              wrapLines
              lineProps={(line) => ({
                id: `code-${selected.attempt_no}-line-${line}`,
                className:
                  highlight?.attempt === selected.attempt_no &&
                  line >= highlight.start &&
                  line <= highlight.end
                    ? "source-highlight"
                    : "",
                style: { display: "block" }
              })}
              codeTagProps={{
                style: {
                  fontFamily: "var(--font-geist-mono), monospace",
                  whiteSpace: "pre-wrap",
                  overflowWrap: "anywhere"
                }
              }}
              customStyle={{
                margin: 0,
                minHeight: 360,
                maxHeight: "65vh",
                width: "100%",
                maxWidth: "100%",
                overflow: "auto",
                background: "#161b22",
                fontSize: 13,
                lineHeight: 1.8,
                padding: "16px 12px"
              }}
            >
              {selected.code}
            </SyntaxHighlighter>
          </div>
        </TabsContent>
        <TabsContent value="changes" className="mt-0">
          <p className="mb-2 text-xs text-muted-foreground">
            Attempt 1 → attempt {selected.attempt_no}
          </p>
          <div className="editor max-h-[65vh] overflow-auto rounded-lg border border-zinc-800 bg-[#161b22] py-3 font-mono text-[13px] leading-6">
            {diff.map((line, i) => (
              <div
                key={i}
                className={`grid grid-cols-[24px_minmax(0,1fr)] gap-2 px-3 ${line.type === "add" ? "bg-emerald-500/15 text-emerald-100" : line.type === "remove" ? "bg-red-500/15 text-red-100" : "text-zinc-300"}`}
              >
                <span aria-label={line.type} className="select-none text-zinc-500">
                  {line.type === "add" ? "+" : line.type === "remove" ? "−" : " "}
                </span>
                <span className="whitespace-pre-wrap break-words [overflow-wrap:anywhere]">
                  {line.text || " "}
                </span>
              </div>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </section>
  );
}
