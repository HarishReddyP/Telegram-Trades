import React from "react";

export const fmt = (n: number | null | undefined, dp = 2) =>
  n === null || n === undefined ? "—" : n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });

export const money = (n: number | null | undefined) =>
  n === null || n === undefined ? "—" : `$${fmt(n)}`;

export const pnlClass = (n: number | null | undefined) =>
  (n ?? 0) > 0 ? "text-pos" : (n ?? 0) < 0 ? "text-neg" : "text-muted";

export function Card({ title, children, className = "" }: { title?: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-panel border border-edge rounded-xl p-4 ${className}`}>
      {title && <div className="text-xs uppercase tracking-wide text-muted mb-2">{title}</div>}
      {children}
    </div>
  );
}

export function Stat({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: string }) {
  return (
    <div className="bg-panel border border-edge rounded-xl p-4">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className={`text-2xl font-semibold mt-1 ${tone ?? ""}`}>{value}</div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  );
}

const STATUS_COLORS: Record<string, string> = {
  OPEN: "bg-accent/20 text-accent border-accent/40",
  CLOSED: "bg-muted/15 text-muted border-edge",
  PENDING_APPROVAL: "bg-yellow-500/15 text-yellow-400 border-yellow-500/40",
  NEEDS_REVIEW: "bg-orange-500/15 text-orange-400 border-orange-500/40",
  APPROVED: "bg-pos/15 text-pos border-pos/40",
  REJECTED: "bg-neg/15 text-neg border-neg/40",
  CANCELLED: "bg-muted/15 text-muted border-edge",
};

export function Badge({ label }: { label: string }) {
  const c = STATUS_COLORS[label] ?? "bg-muted/15 text-muted border-edge";
  return <span className={`text-xs px-2 py-0.5 rounded-full border ${c}`}>{label.replace(/_/g, " ")}</span>;
}

export function holdingTime(seconds: number | null) {
  if (seconds === null || seconds === undefined) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 24) return `${Math.floor(h / 24)}d ${h % 24}h`;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}
