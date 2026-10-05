"use client";
import { useEffect, useState } from "react";
import {
  ChevronDown,
  Code2,
  Download,
  FileSearch,
  Loader2,
  Menu,
  ShieldCheck,
  Square,
  WifiOff
} from "lucide-react";
import { useWorkspace } from "@/lib/use-workspace";
import { exportUrl, terminalStatuses } from "@/lib/api";
import { mergeAttempts } from "@/lib/code";
import type { GeneratedOutput } from "@/lib/contracts.generated";
import { RunHistory } from "@/components/RunHistory";
import { RunComposer } from "@/components/RunComposer";
import { ProviderStatus } from "@/components/ProviderStatus";
import { CodeAttempts, type SourceTarget } from "@/components/CodeAttempts";
import { EvidencePanel, selectedEvidence, type SourceLocation } from "@/components/EvidencePanel";
import { ResultPanel } from "@/components/ResultPanel";
import { Workflow } from "@/components/Workflow";
import { StatusBadge } from "@/components/StatusBadge";
import { MarkdownText } from "@/components/MarkdownText";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
  SheetTrigger
} from "@/components/ui/sheet";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Skeleton } from "@/components/ui/skeleton";
export default function Home() {
  const workspace = useWorkspace();
  const { run, evidence } = workspace;
  const [view, setView] = useState("code");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [draftKey, setDraftKey] = useState(0);
  const [answer, setAnswer] = useState("");
  const [source, setSource] = useState<SourceTarget | null>(null);
  useEffect(() => {
    setView("code");
    setAnswer("");
    setSource(null);
  }, [run?.id]);
  const freshRun = () => {
    workspace.newRun();
    setDraftKey((k) => k + 1);
    setHistoryOpen(false);
    setView("code");
  };
  const open = (id: string) => {
    setHistoryOpen(false);
    void workspace.openRun(id);
  };
  const history = (
    <RunHistory
      runs={workspace.history}
      selected={run?.id}
      loading={workspace.historyLoading}
      error={workspace.historyError}
      onNew={freshRun}
      onOpen={open}
      onRefresh={() => void workspace.refreshHistory()}
    />
  );
  const partialOutput = evidence?.partial.output as GeneratedOutput | undefined;
  const streamed =
    partialOutput &&
    !workspace.attempts.some((a) => a.output.attempt_no === partialOutput.attempt_no)
      ? { ...workspace.streamed, [partialOutput.attempt_no]: partialOutput.code }
      : workspace.streamed;
  const drafts = mergeAttempts(workspace.attempts, streamed);
  const data = evidence ? selectedEvidence(evidence, workspace.selectedAttempt) : undefined;
  const sourceClick = (location: SourceLocation) => {
    workspace.selectAttempt(location.attempt);
    setView("code");
    setSource({ ...location, nonce: Date.now() });
  };
  const active = run && (!terminalStatuses.has(run.status) || run.status === "needs_clarification");
  return (
    <div className="flex min-h-screen min-w-0 bg-background">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 border-r bg-[#f1f3f5] p-4 lg:block">
        {history}
      </aside>
      <main className="min-w-0 flex-1">
        <header className="flex min-h-16 flex-wrap items-center justify-between gap-3 border-b bg-card px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <Sheet open={historyOpen} onOpenChange={setHistoryOpen}>
              <SheetTrigger asChild>
                <Button
                  size="icon"
                  variant="ghost"
                  className="shrink-0 lg:hidden"
                  aria-label="Open history"
                >
                  <Menu className="size-4" />
                </Button>
              </SheetTrigger>
              <SheetContent>
                <SheetTitle className="sr-only">Run history</SheetTitle>
                <SheetDescription className="sr-only">
                  Select a saved run or start a new generation.
                </SheetDescription>
                <div className="h-full pt-10">{history}</div>
              </SheetContent>
            </Sheet>
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <ShieldCheck className="size-3.5" />
                <span>Workspace</span>
                {run && (
                  <>
                    <span>/</span>
                    <span className="font-mono">{run.id.slice(0, 8)}</span>
                  </>
                )}
              </div>
              <h1 className="max-w-[45vw] truncate text-sm font-medium sm:max-w-[55vw]">
                {run ? run.prompt : "New generation"}
              </h1>
            </div>
          </div>
          <div className="flex max-w-full flex-wrap items-center gap-1">
            {run && <StatusBadge value={run.status} />}
            <ProviderStatus health={workspace.health} judges={data?.judge_results ?? []} />
            {active && (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => void workspace.cancel()}
                disabled={workspace.actionPending}
              >
                <Square className="size-3" />
                Cancel
              </Button>
            )}
            {run && (
              <Button variant="outline" size="sm" asChild>
                <a href={exportUrl(run.id)} aria-label="Export evidence">
                  <Download className="size-4" />
                  <span className="hidden sm:inline">Export</span>
                </a>
              </Button>
            )}
          </div>
        </header>
        {(workspace.connection === "reconnecting" || workspace.connection === "offline") && (
          <div
            role="status"
            className="flex flex-wrap items-center gap-2 border-b bg-warning-surface px-6 py-2 text-xs text-warning"
          >
            <WifiOff className="size-4" />
            {workspace.connection === "reconnecting"
              ? "Reconnecting to live updates. Your run continues in the background."
              : "Live updates are disconnected. Saved evidence is still available."}
            {workspace.connection === "offline" && run && (
              <Button size="sm" variant="ghost" onClick={() => void workspace.openRun(run.id)}>
                Reconnect
              </Button>
            )}
          </div>
        )}
        {run && <Workflow status={run.status} stages={workspace.stages} />}
        <div className="mx-auto w-full max-w-[1240px] space-y-4 px-4 py-5 sm:px-6 sm:py-6">
          {workspace.error && (
            <div
              role="alert"
              className="rounded-lg border border-red-200 bg-danger-surface px-4 py-3 text-sm text-danger"
            >
              {workspace.error}
            </div>
          )}
          {workspace.opening ? (
            <div aria-label="Loading run" className="space-y-4">
              <Skeleton className="h-20" />
              <Skeleton className="h-10 w-60" />
              <Skeleton className="h-96" />
            </div>
          ) : !run ? (
            <RunComposer
              key={draftKey}
              pending={workspace.submitting}
              onSubmit={(payload) => void workspace.submit(payload)}
            />
          ) : (
            <>
              <Collapsible className="rounded-lg border bg-card">
                <CollapsibleTrigger className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left">
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-muted-foreground">Submitted prompt</p>
                    <p className="mt-1 line-clamp-2 text-sm">{run.prompt}</p>
                  </div>
                  <ChevronDown className="mt-1 size-4 shrink-0 text-muted-foreground" />
                </CollapsibleTrigger>
                <CollapsibleContent className="space-y-3 border-t px-4 py-3">
                  <MarkdownText>{run.prompt}</MarkdownText>
                  <p className="text-xs text-muted-foreground">
                    {run.inferred.language ?? "Language unresolved"} ·{" "}
                    {run.inferred.framework ?? "No framework"} ·{" "}
                    {run.inferred.runtime ?? "Runtime unspecified"} · up to {run.max_retry} repairs
                  </p>
                  {run.inferred.constraints.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold">Constraints</p>
                      <MarkdownText>
                        {run.inferred.constraints.map((s) => `- ${s}`).join("\n")}
                      </MarkdownText>
                    </div>
                  )}
                  {run.inferred.libraries.length > 0 && (
                    <p className="text-xs">Libraries: {run.inferred.libraries.join(", ")}</p>
                  )}
                </CollapsibleContent>
              </Collapsible>
              <ResultPanel run={run} policy={data?.policy ?? null} />
              {run.status === "needs_clarification" && (
                <form
                  className="rounded-lg border border-sky-200 bg-active-surface p-4"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (answer.trim()) void workspace.clarify(answer.trim());
                  }}
                >
                  <h2 className="text-base font-semibold">A little more context</h2>
                  <div className="my-3">
                    <MarkdownText>
                      {run.inferred.clarification_questions.map((q) => `- ${q}`).join("\n")}
                    </MarkdownText>
                  </div>
                  <label className="sr-only" htmlFor="clarification">
                    Clarification answers
                  </label>
                  <Textarea
                    id="clarification"
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    placeholder="Answer the questions to continue…"
                    disabled={workspace.actionPending}
                    className="bg-card"
                  />
                  <Button
                    type="submit"
                    disabled={!answer.trim() || workspace.actionPending}
                    className="mt-3"
                  >
                    {workspace.actionPending && <Loader2 className="size-4 animate-spin" />}Resume
                    run
                  </Button>
                </form>
              )}
              <Tabs value={view} onValueChange={setView} className="min-w-0">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-3">
                  <TabsList aria-label="Workspace view">
                    <TabsTrigger value="code">
                      <Code2 className="size-4" />
                      Code
                    </TabsTrigger>
                    <TabsTrigger value="evidence">
                      <FileSearch className="size-4" />
                      Evidence
                    </TabsTrigger>
                  </TabsList>
                  {drafts.length > 0 && (
                    <div className="flex items-center gap-2">
                      <label id="attempt-label" className="text-xs text-muted-foreground">
                        Inspect
                      </label>
                      <Select
                        value={
                          workspace.selectedAttempt === null
                            ? "latest"
                            : String(workspace.selectedAttempt)
                        }
                        onValueChange={(value) => {
                          workspace.selectAttempt(value === "latest" ? null : Number(value));
                          setSource(null);
                        }}
                      >
                        <SelectTrigger aria-labelledby="attempt-label" className="h-9 w-44">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="latest">Latest attempt</SelectItem>
                          {drafts.map((d) => (
                            <SelectItem key={d.attempt_no} value={String(d.attempt_no)}>
                              Attempt {d.attempt_no}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                </div>
                <TabsContent value="code">
                  <CodeAttempts
                    attempts={workspace.attempts}
                    streamed={streamed}
                    selectedAttempt={workspace.selectedAttempt}
                    sourceTarget={source}
                    language={run.inferred.language ?? "text"}
                  />
                </TabsContent>
                <TabsContent value="evidence">
                  <EvidencePanel
                    evidence={evidence}
                    selectedAttempt={workspace.selectedAttempt}
                    onSource={sourceClick}
                  />
                </TabsContent>
              </Tabs>
              <footer className="flex flex-wrap justify-between gap-2 border-t pt-4 text-xs text-muted-foreground">
                <span>Execution-free verification · evidence-backed decisions</span>
                <span className="font-mono">
                  {workspace.connection === "connected"
                    ? "Live updates connected"
                    : run.status.replace(/_/g, " ")}
                </span>
              </footer>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
