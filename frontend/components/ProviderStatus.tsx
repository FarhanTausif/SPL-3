import { Activity, ChevronDown } from "lucide-react";
import type { HealthResponse, JudgeResult } from "@/lib/contracts.generated";
import { Button } from "./ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";
import { StatusBadge } from "./StatusBadge";
export function ProviderStatus({
  health,
  judges
}: {
  health: HealthResponse | null;
  judges: JudgeResult[];
}) {
  const degraded = !health || health.status !== "ok" || judges.some((j) => j.status !== "ok");
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="sm" className="text-muted-foreground">
          <Activity className={degraded ? "size-4 text-warning" : "size-4 text-good"} />
          <span>{degraded ? "Limited coverage" : "Providers configured"}</span>
          <ChevronDown className="size-3" />
        </Button>
      </PopoverTrigger>
      <PopoverContent>
        <h2 className="mb-3 text-sm font-semibold">Provider status</h2>
        {!health ? (
          <p className="text-xs text-warning">
            API health unavailable. Run details remain inspectable.
          </p>
        ) : (
          <div className="space-y-3 text-xs">
            <div className="flex justify-between gap-2">
              <span>Database</span>
              <StatusBadge value={health.database} />
            </div>
            <div className="flex justify-between gap-2">
              <span>Ollama</span>
              <StatusBadge
                value={
                  health.ollama.fake_mode
                    ? "simulated"
                    : health.ollama.model_available
                      ? "available"
                      : "unavailable"
                }
              />
            </div>
            {Object.entries(health.judges).map(([name, raw]) => {
              const info = raw as { configured?: boolean; model?: string };
              const observed = judges.find(
                (j) => j.judge_name.toLowerCase() === name.toLowerCase()
              );
              return (
                <div key={name} className="border-t pt-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium capitalize">{name}</span>
                    <StatusBadge
                      value={observed?.status ?? (info.configured ? "configured" : "unavailable")}
                    />
                  </div>
                  <p className="mt-1 break-all font-mono text-muted-foreground">{info.model}</p>
                  <p className="mt-1 text-muted-foreground">
                    {observed
                      ? observed.status === "ok"
                        ? "Valid response for this attempt"
                        : observed.explanation
                      : info.configured
                        ? "Credentials configured; access and quota unchecked"
                        : "Credentials missing"}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}
