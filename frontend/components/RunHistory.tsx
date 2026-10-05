"use client";
import { useState } from "react";
import { Plus, RefreshCw, Search, ShieldCheck } from "lucide-react";
import type { RunSummary } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Skeleton } from "./ui/skeleton";
import { StatusBadge } from "./StatusBadge";
export function RunHistory({
  runs,
  selected,
  loading,
  error,
  onNew,
  onOpen,
  onRefresh
}: {
  runs: RunSummary[];
  selected?: string;
  loading: boolean;
  error: string | null;
  onNew: () => void;
  onOpen: (id: string) => void;
  onRefresh: () => void;
}) {
  const [query, setQuery] = useState("");
  const filtered = runs
    .filter((run) => run.prompt.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? ""));
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="mb-7 flex items-center gap-2 px-2 text-base font-semibold tracking-tight">
        <ShieldCheck className="size-5 text-primary" />
        DeHalu
        <span className="ml-auto rounded border px-1.5 text-[10px] font-medium text-muted-foreground">
          WORKSPACE
        </span>
      </div>
      <Button variant="outline" className="mb-5 justify-start bg-card" onClick={onNew}>
        <Plus className="size-4" />
        New run
      </Button>
      <div className="relative">
        <Search className="absolute left-3 top-3 size-4 text-muted-foreground" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search run history"
          placeholder="Search runs"
          className="h-9 bg-card pl-9 text-xs"
        />
      </div>
      <div className="mb-2 mt-5 flex items-center justify-between px-2">
        <span className="text-xs font-medium text-muted-foreground">Recent runs</span>
        <Button
          variant="ghost"
          size="icon"
          className="size-7"
          aria-label="Refresh history"
          onClick={onRefresh}
          disabled={loading}
        >
          <RefreshCw className={cn("size-3.5", loading && "animate-spin")} />
        </Button>
      </div>
      <nav aria-label="Run history" className="min-h-0 flex-1 space-y-1 overflow-y-auto">
        {loading && !runs.length ? (
          <div className="space-y-3 p-2">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-16" />
            ))}
          </div>
        ) : error ? (
          <p role="alert" className="px-2 text-xs text-danger">
            {error}
          </p>
        ) : !filtered.length ? (
          <p className="px-2 py-4 text-xs text-muted-foreground">
            {query ? "No matching runs." : "Your runs will appear here."}
          </p>
        ) : (
          filtered.map((run) => (
            <button
              key={run.id}
              aria-current={selected === run.id ? "page" : undefined}
              onClick={() => onOpen(run.id)}
              className={cn(
                "block w-full rounded-md border border-transparent px-2 py-3 text-left transition-colors hover:bg-muted",
                selected === run.id && "border-border bg-card shadow-sm"
              )}
            >
              <span className="block truncate text-sm font-medium">{run.prompt}</span>
              <span className="mt-2 flex flex-wrap items-center justify-between gap-1">
                <StatusBadge value={run.policy_decision?.decision ?? run.status} compact />
                <time
                  className="text-[11px] text-muted-foreground"
                  dateTime={run.created_at ?? undefined}
                >
                  {run.created_at
                    ? new Date(run.created_at).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric"
                      })
                    : "Date unavailable"}
                </time>
              </span>
            </button>
          ))
        )}
      </nav>
      <div className="mt-4 border-t px-2 pt-4 text-xs text-muted-foreground">
        Code generation with evidence
      </div>
    </div>
  );
}
