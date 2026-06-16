import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Card } from "../lib/ui";
import { useNavigate } from "react-router-dom";

export default function Settings() {
  const [settings, setSettings] = useState<Record<string, unknown> | null>(null);
  const [resetting, setResetting] = useState(false);
  const [resetDone, setResetDone] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => { api.settings().then(setSettings).catch(() => {}); }, []);

  async function handleReset() {
    if (!window.confirm("This will delete ALL trades, alerts and P&L history and reset the account to starting capital.\n\nAre you sure?")) return;
    setResetting(true);
    setResetDone(null);
    try {
      const res = await api.resetAll();
      setResetDone(`Reset complete. Account reset to $${res.account_value.toLocaleString()}.`);
      setTimeout(() => navigate("/"), 1500);
    } catch (e: unknown) {
      setResetDone(`Error: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setResetting(false);
    }
  }

  if (!settings) return <div className="text-muted">Loading…</div>;

  const safety: [string, unknown][] = [
    ["Trading mode", settings.trading_mode],
    ["Manual approval", String(settings.manual_approval)],
    ["Live trading enabled", String(settings.live_trading_enabled)],
    ["Kill switch", String(settings.kill_switch)],
  ];
  const conn: [string, unknown][] = [
    ["Telegram channel", settings.telegram_channel || "(not set)"],
    ["Report recipient", settings.report_recipient || "(not set)"],
    ["Market timezone", settings.market_tz],
    ["Market close", settings.market_close],
  ];

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold">Settings</h1>

      <Card title="Safety gates">
        <KV rows={safety} />
        <p className="text-xs text-muted mt-3">
          These are controlled via environment variables (see <code>backend/.env</code>).
          Live trading requires both <code>LIVE_TRADING_ENABLED=true</code> and{" "}
          <code>TRADING_MODE=live</code>, plus an implemented broker adapter.
        </p>
      </Card>

      <Card title="Connections & schedule">
        <KV rows={conn} />
      </Card>

      <Card title="Danger zone">
        <p className="text-sm text-muted mb-4">
          Clears all trades, alerts, messages and P&amp;L history. Risk rules and settings are kept.
          The account resets to starting capital. This cannot be undone.
        </p>
        {resetDone && (
          <p className={`text-sm mb-3 font-medium ${resetDone.startsWith("Error") ? "text-red-400" : "text-green-400"}`}>
            {resetDone}
          </p>
        )}
        <button
          onClick={handleReset}
          disabled={resetting}
          className="px-4 py-2 rounded text-sm font-medium bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white transition-colors"
        >
          {resetting ? "Resetting…" : "Reset — Clear All Trades & Start Fresh"}
        </button>
      </Card>
    </div>
  );
}

function KV({ rows }: { rows: [string, unknown][] }) {
  return (
    <table className="w-full text-sm">
      <tbody>
        {rows.map(([k, v], i) => (
          <tr key={i} className="border-t border-edge first:border-0">
            <td className="py-2 text-muted">{k}</td>
            <td className="py-2 text-right font-mono">{String(v)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
