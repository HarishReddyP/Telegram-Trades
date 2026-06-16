import { useEffect, useState } from "react";
import {
  Bar, BarChart, Cell, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../lib/api";
import { Card, money, pnlClass } from "../lib/ui";

export default function DailyPnL() {
  const [data, setData] = useState<{ date: string; pnl: number }[]>([]);
  const [days, setDays] = useState(30);

  useEffect(() => { api.dailyPnl(days).then(setData).catch(() => {}); }, [days]);

  const total = data.reduce((a, b) => a + b.pnl, 0);
  const best = data.reduce((a, b) => (b.pnl > a ? b.pnl : a), -Infinity);
  const worst = data.reduce((a, b) => (b.pnl < a ? b.pnl : a), Infinity);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Daily P&L</h1>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))}
          className="bg-panel2 border border-edge rounded px-2 py-1 text-sm">
          <option value={14}>14 days</option>
          <option value={30}>30 days</option>
          <option value={90}>90 days</option>
        </select>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <Card title="Period total"><div className={`text-2xl font-semibold ${pnlClass(total)}`}>{money(total)}</div></Card>
        <Card title="Best day"><div className="text-2xl font-semibold text-pos">{money(best === -Infinity ? 0 : best)}</div></Card>
        <Card title="Worst day"><div className="text-2xl font-semibold text-neg">{money(worst === Infinity ? 0 : worst)}</div></Card>
      </div>

      <Card title="Realized P&L by day">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <CartesianGrid stroke="#273042" strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fill: "#8b97ad", fontSize: 11 }} tickFormatter={(d) => d.slice(5)} />
            <YAxis tick={{ fill: "#8b97ad", fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "#141925", border: "1px solid #273042" }} />
            <Bar dataKey="pnl">
              {data.map((d, i) => <Cell key={i} fill={d.pnl >= 0 ? "#2ecc71" : "#ff5d5d"} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}
