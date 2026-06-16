import { useEffect, useState } from "react";
import {
  Bar, BarChart, Cell, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../lib/api";
import React from "react";
import { Card, money, pnlClass } from "../lib/ui";

type Strat = { strategy: string; trades: number; pnl: number; win_rate: number };
type Tick = { ticker: string; trades: number; pnl: number };

export default function StrategyAnalytics() {
  const [strat, setStrat] = useState<Strat[]>([]);
  const [tick, setTick] = useState<Tick[]>([]);

  useEffect(() => {
    api.strategyPerf().then(setStrat).catch(() => {});
    api.tickerPerf().then(setTick).catch(() => {});
  }, []);

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold">Strategy Analytics</h1>

      <Card title="P&L by strategy">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={strat}>
            <CartesianGrid stroke="#273042" strokeDasharray="3 3" />
            <XAxis dataKey="strategy" tick={{ fill: "#8b97ad", fontSize: 10 }}
              tickFormatter={(s) => s.replace(/_/g, " ")} />
            <YAxis tick={{ fill: "#8b97ad", fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "#141925", border: "1px solid #273042" }} />
            <Bar dataKey="pnl">
              {strat.map((d, i) => <Cell key={i} fill={d.pnl >= 0 ? "#2ecc71" : "#ff5d5d"} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Strategy breakdown">
          <Table headers={["Strategy", "Trades", "Win %", "P&L"]}
            rows={strat.map((s) => [s.strategy.replace(/_/g, " "), String(s.trades), `${s.win_rate}%`,
              <span className={pnlClass(s.pnl)}>{money(s.pnl)}</span>])} />
        </Card>
        <Card title="Ticker breakdown">
          <Table headers={["Ticker", "Trades", "P&L"]}
            rows={tick.map((t) => [t.ticker, String(t.trades),
              <span className={pnlClass(t.pnl)}>{money(t.pnl)}</span>])} />
        </Card>
      </div>
    </div>
  );
}

function Table({ headers, rows }: { headers: string[]; rows: React.ReactNode[][] }) {
  if (!rows.length) return <div className="text-muted text-sm py-4">No data yet.</div>;
  return (
    <table className="w-full text-sm">
      <thead className="text-muted text-xs uppercase">
        <tr>{headers.map((h, i) => <th key={i} className={`py-1 ${i === 0 ? "text-left" : "text-right"}`}>{h}</th>)}</tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} className="border-t border-edge">
            {r.map((c, j) => <td key={j} className={`py-1.5 ${j === 0 ? "text-left" : "text-right"}`}>{c}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

