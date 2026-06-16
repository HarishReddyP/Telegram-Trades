import { useEffect, useState } from "react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../lib/api";
import { Card, Stat, money, pnlClass } from "../lib/ui";
import type { Summary } from "../types";

export default function Overview() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [equity, setEquity] = useState<{ t: string; value: number }[]>([]);
  const [daily, setDaily] = useState<{ date: string; pnl: number }[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.overview()
      .then((d) => { setSummary(d.summary); setEquity(d.equity_curve); setDaily(d.daily_pnl); })
      .catch((e) => setErr(String(e)));
  }, []);

  if (err) return <Banner msg={err} />;
  if (!summary) return <div className="text-muted">Loading…</div>;

  return (
    <div className="space-y-5">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Overview</h1>
        <div className="flex gap-2 text-xs">
          <Pill on={summary.trading_mode === "paper"} text={`mode: ${summary.trading_mode}`} />
          <Pill on={summary.manual_approval} text="manual approval" />
          <Pill on={!summary.live_enabled} text={summary.live_enabled ? "LIVE ENABLED" : "live disabled"} />
          {summary.kill_switch && <Pill on={false} text="KILL SWITCH" />}
        </div>
      </header>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Account Value" value={money(summary.account_value)}
          sub={`start ${money(summary.starting_capital)}`} />
        <Stat label="Daily P&L" value={money(summary.daily_pnl)} tone={pnlClass(summary.daily_pnl)} />
        <Stat label="Total P&L" value={money(summary.total_pnl)} tone={pnlClass(summary.total_pnl)}
          sub={`realized ${money(summary.realized_pnl)} · unreal ${money(summary.unrealized_pnl)}`} />
        <Stat label="Win Rate" value={`${summary.win_rate}%`}
          sub={`${summary.closed_trades} closed`} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Open Trades" value={String(summary.open_trades)} />
        <Stat label="Avg Profit" value={money(summary.avg_profit)} tone="text-pos" />
        <Stat label="Avg Loss" value={money(summary.avg_loss)} tone="text-neg" />
        <Stat label="Max Drawdown" value={money(summary.max_drawdown)} tone="text-neg" />
      </div>

      <Card title="Equity Curve">
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={equity}>
            <defs>
              <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#5b8cff" stopOpacity={0.5} />
                <stop offset="100%" stopColor="#5b8cff" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#273042" strokeDasharray="3 3" />
            <XAxis dataKey="t" tick={{ fill: "#8b97ad", fontSize: 11 }}
              tickFormatter={(t) => new Date(t).toLocaleDateString()} />
            <YAxis tick={{ fill: "#8b97ad", fontSize: 11 }} domain={["auto", "auto"]} />
            <Tooltip contentStyle={{ background: "#141925", border: "1px solid #273042" }}
              labelFormatter={(t) => new Date(t as string).toLocaleString()} />
            <Area type="monotone" dataKey="value" stroke="#5b8cff" fill="url(#eq)" />
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      <Card title="Daily P&L (last 14 days)">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={daily}>
            <CartesianGrid stroke="#273042" strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fill: "#8b97ad", fontSize: 11 }}
              tickFormatter={(d) => d.slice(5)} />
            <YAxis tick={{ fill: "#8b97ad", fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "#141925", border: "1px solid #273042" }} />
            <Bar dataKey="pnl">
              {daily.map((d, i) => (
                <Cell key={i} fill={d.pnl >= 0 ? "#2ecc71" : "#ff5d5d"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}


function Pill({ on, text }: { on: boolean; text: string }) {
  return (
    <span className={`px-2 py-1 rounded-full border ${on ? "border-pos/40 text-pos bg-pos/10" : "border-neg/40 text-neg bg-neg/10"}`}>
      {text}
    </span>
  );
}

function Banner({ msg }: { msg: string }) {
  return (
    <div className="bg-neg/10 border border-neg/40 text-neg rounded-lg p-4 text-sm">
      Failed to load: {msg}. Is the backend running on :8000?
    </div>
  );
}
