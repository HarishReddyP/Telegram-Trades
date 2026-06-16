import type { Trade, Summary, Alert, RiskRule } from "../types";

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function http<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} — ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  overview: () =>
    http<{ summary: Summary; equity_curve: { t: string; value: number }[]; daily_pnl: { date: string; pnl: number }[] }>(
      "/api/dashboard/overview"
    ),
  dailyPnl: (days = 30) =>
    http<{ date: string; pnl: number }[]>(`/api/dashboard/daily-pnl?days=${days}`),
  strategyPerf: () =>
    http<{ strategy: string; trades: number; pnl: number; win_rate: number }[]>(
      "/api/dashboard/strategy-performance"
    ),
  tickerPerf: () =>
    http<{ ticker: string; trades: number; pnl: number }[]>("/api/dashboard/ticker-performance"),

  trades: (status?: string) =>
    http<Trade[]>(`/api/trades${status ? `?status=${status}` : ""}`),
  openTrades: () => http<Trade[]>("/api/trades/open"),
  closedTrades: () => http<Trade[]>("/api/trades/closed"),
  pendingTrades: () => http<Trade[]>("/api/trades/pending"),
  refreshMarks: () => http<{ refreshed: boolean; open_trades: Trade[] }>("/api/trades/refresh-marks", { method: "POST" }),
  approve: (id: number) => http<Trade>(`/api/trades/${id}/approve`, { method: "POST" }),
  reject: (id: number) => http<Trade>(`/api/trades/${id}/reject`, { method: "POST" }),

  alerts: (limit = 100) => http<Alert[]>(`/api/alerts?limit=${limit}`),
  preview: (text: string) =>
    http<Record<string, unknown>>("/api/alerts/preview", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  simulate: (text: string, auto_approve: boolean) =>
    http<{ message_id: number; trade: Trade | null; approve_error?: string }>(
      "/api/alerts/simulate",
      { method: "POST", body: JSON.stringify({ text, auto_approve }) }
    ),

  riskRules: () => http<RiskRule>("/api/risk-rules"),
  updateRiskRules: (r: RiskRule) =>
    http<RiskRule>("/api/risk-rules", { method: "PUT", body: JSON.stringify(r) }),
  settings: () => http<Record<string, unknown>>("/api/settings"),
  resetAll: () => http<{ status: string; deleted: Record<string, number>; account_value: number }>(
    "/api/reset", { method: "DELETE" }
  ),
};
