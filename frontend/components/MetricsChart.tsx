"use client";
import { useEffect, useRef, useState } from "react";
import type { AttemptEvidence } from "@/lib/api";
export function MetricsChart({ attempts }: { attempts: AttemptEvidence[] }) {
  const [active, setActive] = useState<string | null>(null);
  const svg = useRef<SVGSVGElement>(null);
  const [chartWidth, setChartWidth] = useState(660);
  useEffect(() => {
    const element = svg.current;
    if (!element) return;
    const resize = () => {
      const width = element.getBoundingClientRect().width;
      if (width > 0) setChartWidth(Math.max(260, width));
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    return () => observer.disconnect();
  }, [attempts.length]);
  const points = [...attempts].sort((a, b) => a.output.attempt_no - b.output.attempt_no);
  if (!points.length) return null;
  const first = points[0],
    last = points[points.length - 1];
  const x = (attempt: number) =>
    points.length === 1
      ? chartWidth / 2
      : 60 +
        ((attempt - first.output.attempt_no) / (last.output.attempt_no - first.output.attempt_no)) *
          (chartWidth - 84);
  const y = (value: number) => 200 - value * 160;
  const series = [
    {
      name: "Hallucination risk",
      color: "#7c3aed",
      value: (a: AttemptEvidence) => a.metrics.hallucination_risk_score
    },
    {
      name: "MaHR",
      color: "#0284c7",
      value: (a: AttemptEvidence) => a.metrics.mahr
    }
  ];
  const detail = series
    .flatMap((s) =>
      points.map((a) => ({
        id: `${s.name}-${a.output.attempt_no}`,
        text: `Attempt ${a.output.attempt_no}: ${s.name} ${(s.value(a) * 100).toFixed(1)}%`
      }))
    )
    .find((p) => p.id === active)?.text;
  return (
    <section aria-label="Hallucination trend" className="mb-5 rounded-lg border bg-card p-4">
      <h3 className="text-sm font-semibold">Hallucination across attempts</h3>
      <p className="mt-1 text-xs text-muted-foreground">
        Lower is better. Risk is a comparative score; MaHR includes unsupported and uncertain
        claims.
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {series.map((s) => {
          const change = (s.value(last) - s.value(first)) * 100;
          return (
            <div key={s.name} className="text-xs">
              <span
                className="mr-2 inline-block size-2 rounded-full"
                style={{ backgroundColor: s.color }}
              />
              {s.name}
              <p className="mt-1 font-mono">
                {(s.value(first) * 100).toFixed(1)}% → {(s.value(last) * 100).toFixed(1)}%
                {points.length > 1 && ` · ${change > 0 ? "+" : ""}${change.toFixed(1)} pp`}
              </p>
            </div>
          );
        })}
      </div>
      <svg
        ref={svg}
        viewBox={`0 0 ${chartWidth} 245`}
        className="mt-2 w-full"
        role="group"
        aria-label="Risk and MaHR by attempt, from zero to one hundred percent"
      >
        {[0, 25, 50, 75, 100].map((tick) => (
          <g key={tick}>
            <line
              x1="60"
              x2={chartWidth - 24}
              y1={y(tick / 100)}
              y2={y(tick / 100)}
              stroke="currentColor"
              opacity="0.12"
            />
            <text x="48" y={y(tick / 100) + 4} textAnchor="end" fill="currentColor" fontSize="12">
              {tick}%
            </text>
          </g>
        ))}
        {points.map((a) => (
          <text
            key={a.output.attempt_no}
            x={x(a.output.attempt_no)}
            y="223"
            textAnchor="middle"
            fill="currentColor"
            fontSize="12"
          >
            {a.output.attempt_no === 1 ? "Initial" : `Repair ${a.output.attempt_no - 1}`}
          </text>
        ))}
        {series.map((s) => (
          <g key={s.name}>
            <polyline
              fill="none"
              stroke={s.color}
              strokeWidth="2.5"
              points={points.map((a) => `${x(a.output.attempt_no)},${y(s.value(a))}`).join(" ")}
            />
            {points.map((a) => {
              const id = `${s.name}-${a.output.attempt_no}`;
              const label = `Attempt ${a.output.attempt_no}: ${s.name} ${(s.value(a) * 100).toFixed(1)}%`;
              return (
                <circle
                  key={id}
                  cx={x(a.output.attempt_no)}
                  cy={y(s.value(a))}
                  r={active === id ? 7 : 5}
                  fill={s.color}
                  stroke="white"
                  strokeWidth="2"
                  tabIndex={0}
                  aria-label={label}
                  onFocus={() => setActive(id)}
                  onBlur={() => setActive(null)}
                  onMouseEnter={() => setActive(id)}
                  onMouseLeave={() => setActive(null)}
                >
                  <title>{label}</title>
                </circle>
              );
            })}
          </g>
        ))}
      </svg>
      <p aria-live="polite" className="min-h-5 text-xs text-muted-foreground">
        {detail ??
          (points.length === 1
            ? "One completed attempt. A repair is needed to compare changes."
            : "Hover or focus a point to inspect its measured value.")}
      </p>
    </section>
  );
}
