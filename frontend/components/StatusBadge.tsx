export function StatusBadge({ value }: { value: string }) {
  const tone = value === "accept" || value === "completed" || value === "pass"
    ? "good"
    : value === "repair" || value === "warn" || value === "needs_clarification"
      ? "warn"
      : value === "reject" || value === "fail"
        ? "bad"
        : "neutral";
  return <span className={`status ${tone}`}>{value.replace(/_/g, " ")}</span>;
}
