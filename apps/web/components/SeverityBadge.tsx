export function SeverityBadge({ severity }: { severity: number }) {
  const label = severity >= 10 ? "critical" : severity >= 7 ? "high" : severity >= 4 ? "medium" : "low";
  return <span className="badge">{label} · {severity}</span>;
}
