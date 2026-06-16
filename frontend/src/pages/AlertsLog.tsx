import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Card, Badge } from "../lib/ui";
import type { Alert } from "../types";

export default function AlertsLog() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [text, setText] = useState("SPX selling 5x 5400/5390 put credit spread @ 1.20 credit exp 2026-06-19");
  const [auto, setAuto] = useState(false);
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => { api.alerts(100).then(setAlerts).catch(() => {}); };
  useEffect(load, []);

  const doPreview = () => api.preview(text).then(setPreview).catch((e) => alert(String(e)));
  const doSimulate = async () => {
    setBusy(true);
    try { await api.simulate(text, auto); await load(); }
    catch (e) { alert(String(e)); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold">Telegram Alerts Log</h1>

      <Card title="Simulate an alert (paper)">
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={2}
          className="w-full bg-panel2 border border-edge rounded p-2 text-sm font-mono" />
        <div className="flex items-center gap-3 mt-2">
          <button onClick={doPreview} className="px-3 py-1.5 rounded bg-panel2 border border-edge text-sm hover:bg-edge">Preview parse</button>
          <button onClick={doSimulate} disabled={busy}
            className="px-3 py-1.5 rounded bg-accent/20 border border-accent/40 text-accent text-sm hover:bg-accent/30 disabled:opacity-50">
            {busy ? "Sending…" : "Inject alert"}
          </button>
          <label className="text-xs text-muted flex items-center gap-1">
            <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} />
            auto-approve
          </label>
        </div>
        {preview && (
          <pre className="mt-3 bg-ink border border-edge rounded p-3 text-xs overflow-x-auto">
            {JSON.stringify(preview, null, 2)}
          </pre>
        )}
      </Card>

      <Card title="Parsed alerts">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-muted text-xs uppercase">
              <tr>
                <th className="text-left py-1">Time</th>
                <th className="text-left py-1">Event</th>
                <th className="text-left py-1">Strategy</th>
                <th className="text-left py-1">Ticker</th>
                <th className="text-right py-1">Price</th>
                <th className="text-right py-1">Conf.</th>
                <th className="text-left py-1">Source</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr key={a.id} className="border-t border-edge align-top">
                  <td className="py-1.5 text-muted text-xs whitespace-nowrap">{new Date(a.created_at).toLocaleString()}</td>
                  <td className="py-1.5"><Badge label={a.event} /></td>
                  <td className="py-1.5 text-muted">{a.strategy.replace(/_/g, " ")}</td>
                  <td className="py-1.5">{a.ticker ?? "—"}</td>
                  <td className="py-1.5 text-right">{a.price ?? "—"} <span className="text-muted text-xs">{a.price_type?.[0] ?? ""}</span></td>
                  <td className="py-1.5 text-right text-muted">{a.confidence}</td>
                  <td className="py-1.5 text-muted text-xs max-w-[280px] truncate" title={a.source_text}>{a.source_text}</td>
                </tr>
              ))}
              {!alerts.length && <tr><td colSpan={7} className="text-muted py-6 text-center">No alerts yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
