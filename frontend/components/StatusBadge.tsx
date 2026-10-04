import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const toneMap: Record<string, "good" | "warn" | "bad" | "info" | "neutral"> = {
  accept: "good",
  available: "good",
  ok: "good",
  partial: "warn",
  configured: "neutral",
  completed: "good",
  done: "good",
  pass: "good",
  supported: "good",
  reject: "bad",
  rejected: "bad",
  interrupted: "warn",
  cancelled: "neutral",
  queued: "info",
  unavailable: "warn",
  simulated: "warn",
  error: "bad",
  failed: "bad",
  fail: "bad",
  unsupported: "bad",
  repair: "warn",
  warn: "warn",
  warning: "warn",
  uncertain: "warn",
  running: "info",
  needs_clarification: "info",
  pending: "neutral",
  not_checked: "neutral"
};

export function StatusBadge({ value, compact = false }: { value: string; compact?: boolean }) {
  const normalized = value.toLowerCase();
  const tone = toneMap[normalized] ?? "neutral";
  return (
    <Badge
      variant={tone}
      className={cn(
        "shrink-0 whitespace-nowrap",
        compact ? "px-1.5 py-0 text-[10px] leading-4" : ""
      )}
    >
      {value.replace(/_/g, " ")}
    </Badge>
  );
}
