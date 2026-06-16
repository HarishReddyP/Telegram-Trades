import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Card } from "../lib/ui";
import type { RiskRule } from "../types";

const FIELDS: { key: keyof RiskRule; label: string; type: "number" }[] = [
  { key: "starting_capital", label: "Starting capital ($)", type: "number" },
  { key: "max_risk_per_trade", label: "Max risk per trade ($)", type: "number" },
  { key: "max_contracts_per_trade", label: "Max contracts per trade", type: "number" },
  { key: "max_daily_loss", label: "Max daily loss ($)", type: "number" },
  { key: "max_open_trades", label: "Max open trades", type: "number" },
  { key: "no_trade_minutes_before_close", label: "No-trade window before close (min)", type: "number" },
  { key: "commission_per_contract", label: "Commission per contract ($)", type: "number" },
];

export default function RiskControls() {
  const [rule, setRule] = useState<RiskRule | null>(null);
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { api.riskRules().then(setRule).catch((e) => setErr(String(e))); }, []);

  if (err) return <div className="text-neg text-sm">No risk rules found. Start the backend so it can seed defaults. ({err})</div>;
  if (!rule) return <div className="text-muted">Loading…</div>;

  const update = (k: keyof RiskRule, v: unknown) => setRule({ ...rule, [k]: v });

  const save = async () => {
    setSaved(false);
    try { const r = await api.updateRiskRules(rule); setRule(r); setSaved(true); }
    catch (e) { alert(String(e)); }
  };

  return (
    <div className="space-y-5 max-w-2xl">
      <h1 className="text-xl font-semibold">Risk Controls</h1>

      <Card title="Limits">
        <div className="grid md:grid-cols-2 gap-4">
          {FIELDS.map((f) => (
            <label key={f.key} className="text-sm">
              <span className="text-muted block mb-1">{f.label}</span>
              <input type="number" value={Number(rule[f.key])}
                onChange={(e) => update(f.key, Number(e.target.value))}
                className="w-full bg-panel2 border border-edge rounded px-2 py-1.5" />
            </label>
          ))}
        </div>

        <label className="flex items-center gap-2 text-sm mt-4">
          <input type="checkbox" checked={rule.no_trade_near_close}
            onChange={(e) => update("no_trade_near_close", e.target.checked)} />
          <span>Block entries near market close</span>
        </label>
      </Card>

      <Card title="Allowed tickers (comma-separated)">
        <input value={rule.allowed_tickers.join(", ")}
          onChange={(e) => update("allowed_tickers", e.target.value.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean))}
          className="w-full bg-panel2 border border-edge rounded px-2 py-1.5 text-sm" />
      </Card>

      <Card title="Allowed strategies (comma-separated)">
        <input value={rule.allowed_strategies.join(", ")}
          onChange={(e) => update("allowed_strategies", e.target.value.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean))}
          className="w-full bg-panel2 border border-edge rounded px-2 py-1.5 text-sm font-mono" />
        <p className="text-xs text-muted mt-2">
          e.g. BULL_PUT_SPREAD, BEAR_CALL_SPREAD, IRON_CONDOR, IRON_FLY, BUTTERFLY, SINGLE_LEG
        </p>
      </Card>

      <div className="flex items-center gap-3">
        <button onClick={save}
          className="px-4 py-2 rounded bg-accent/20 border border-accent/40 text-accent text-sm hover:bg-accent/30">
          Save risk rules
        </button>
        {saved && <span className="text-pos text-sm">Saved ✓</span>}
      </div>
      <p className="text-xs text-muted">
        Saving creates a new versioned rule row; the latest is always active. Changes apply to
        future approvals immediately.
      </p>
    </div>
  );
}
