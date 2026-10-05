"use client";
import { useLayoutEffect, useRef, useState } from "react";
import { ArrowUp, ChevronDown, Loader2, SlidersHorizontal, Terminal } from "lucide-react";
import type { RunCreate } from "@/lib/api";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Input } from "./ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./ui/collapsible";
const examples = [
  {
    title: "Python utility",
    prompt:
      "Write a Python function that groups a list of records by a specified key. Handle missing keys without external dependencies."
  },
  {
    title: "TypeScript validation",
    prompt:
      "Write a TypeScript function that validates an email address and returns a typed validation result. Use no external dependencies."
  },
  {
    title: "Go data handling",
    prompt:
      "Write a Go function that decodes JSON into a struct and returns clear errors for invalid input."
  }
];
export function RunComposer({
  onSubmit,
  pending
}: {
  onSubmit: (payload: RunCreate) => void;
  pending: boolean;
}) {
  const [prompt, setPrompt] = useState("");
  const [language, setLanguage] = useState("auto");
  const [framework, setFramework] = useState("");
  const [runtime, setRuntime] = useState("");
  const [libraries, setLibraries] = useState("");
  const [constraints, setConstraints] = useState("");
  const [repairs, setRepairs] = useState(3);
  const textarea = useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(() => {
    if (textarea.current) {
      textarea.current.style.height = "auto";
      textarea.current.style.height = `${Math.min(240, textarea.current.scrollHeight)}px`;
    }
  }, [prompt]);
  const submit = () => {
    if (!pending && prompt.trim().length >= 3)
      onSubmit({
        prompt: prompt.trim(),
        language_hint: language === "auto" ? null : language,
        framework_hint: framework || null,
        runtime_hint: runtime || null,
        libraries: libraries
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        constraints: constraints
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        max_retry: repairs
      });
  };
  return (
    <section className="mx-auto w-full max-w-3xl py-8 sm:py-16" aria-label="New generation">
      <div className="mb-8">
        <div className="mb-4 flex size-10 items-center justify-center rounded-lg border bg-card text-primary">
          <Terminal className="size-5" />
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">What would you like to build?</h1>
        <p className="mt-2 text-muted-foreground">
          Generate code. Inspect the evidence. Understand the result.
        </p>
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="rounded-lg border bg-card shadow-sm"
      >
        <label htmlFor="prompt" className="sr-only">
          Prompt
        </label>
        <Textarea
          id="prompt"
          ref={textarea}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
              e.preventDefault();
              submit();
            }
          }}
          placeholder="Describe the code you need…"
          disabled={pending}
          className="min-h-32 border-0 px-4 py-4 text-base leading-7 shadow-none focus-visible:ring-0"
        />
        <div className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3">
          <span className="text-xs text-muted-foreground">Ctrl / ⌘ Enter to generate</span>
          <Button type="submit" disabled={pending || prompt.trim().length < 3}>
            {pending ? <Loader2 className="size-4 animate-spin" /> : <ArrowUp className="size-4" />}
            {pending ? "Submitting…" : "Generate"}
          </Button>
        </div>
      </form>
      <Collapsible className="mt-3">
        <CollapsibleTrigger className="flex items-center gap-2 rounded-md py-2 text-xs font-medium text-muted-foreground hover:text-foreground">
          <SlidersHorizontal className="size-4" />
          Advanced options
          <ChevronDown className="size-3" />
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-2 rounded-lg border bg-card p-4">
          <fieldset disabled={pending} className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-1 text-xs font-medium">
              Language
              <Select value={language} onValueChange={setLanguage}>
                <SelectTrigger aria-label="Language" className="mt-1 w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[
                    "auto",
                    "python",
                    "javascript",
                    "typescript",
                    "java",
                    "go",
                    "rust",
                    "c",
                    "cpp"
                  ].map((lang) => (
                    <SelectItem key={lang} value={lang}>
                      {lang === "auto" ? "Automatic" : lang === "cpp" ? "C++" : lang}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </label>
            <label className="space-y-1 text-xs font-medium">
              Maximum repairs
              <Input
                aria-label="Maximum repairs"
                type="number"
                min={0}
                max={5}
                value={repairs}
                onChange={(e) => setRepairs(Math.min(5, Math.max(0, Number(e.target.value))))}
                className="mt-1"
              />
            </label>
            <label className="space-y-1 text-xs font-medium">
              Framework
              <Input
                aria-label="Framework"
                value={framework}
                onChange={(e) => setFramework(e.target.value)}
                placeholder="e.g. FastAPI"
                className="mt-1"
              />
            </label>
            <label className="space-y-1 text-xs font-medium">
              Runtime
              <Input
                aria-label="Runtime"
                value={runtime}
                onChange={(e) => setRuntime(e.target.value)}
                placeholder="e.g. Python 3.11"
                className="mt-1"
              />
            </label>
            <label className="space-y-1 text-xs font-medium sm:col-span-2">
              Allowed libraries
              <Input
                aria-label="Allowed libraries"
                value={libraries}
                onChange={(e) => setLibraries(e.target.value)}
                placeholder="Comma-separated library names"
                className="mt-1"
              />
            </label>
            <label className="space-y-1 text-xs font-medium sm:col-span-2">
              Constraints
              <Textarea
                aria-label="Constraints"
                value={constraints}
                onChange={(e) => setConstraints(e.target.value)}
                placeholder="One constraint per line"
                className="mt-1 min-h-20"
              />
            </label>
          </fieldset>
        </CollapsibleContent>
      </Collapsible>
      <div className="mt-8">
        <p className="mb-3 text-xs font-medium text-muted-foreground">Try a starting point</p>
        <div className="grid gap-2 sm:grid-cols-3">
          {examples.map((example) => (
            <Button
              key={example.title}
              variant="outline"
              className="h-auto justify-start whitespace-normal py-3 text-left font-normal"
              disabled={pending}
              onClick={() => {
                setPrompt(example.prompt);
                textarea.current?.focus();
              }}
            >
              {example.title}
            </Button>
          ))}
        </div>
      </div>
      <p className="mt-8 text-xs text-muted-foreground">
        Static analysis and evidence-based verification. Generated code is never executed.
      </p>
    </section>
  );
}
