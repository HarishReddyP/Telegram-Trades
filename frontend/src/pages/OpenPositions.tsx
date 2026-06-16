import { useEffect, useState } from "react";
import { api } from "../lib/api";
import TradeTable from "../components/TradeTable";
import type { Trade } from "../types";

export default function OpenPositions() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [pending, setPending] = useState<Trade[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const load = () => {
    api.openTrades().then(setTrades).catch(() => {});
    api.pendingTrades().then(setPending).catch(() => {});
  };
  useEffect(load, []);

  // Re-price open positions from live quotes when the page mounts.
  useEffect(() => {
    api.refreshMarks().then((r) => setTrades(r.open_trades)).catch(() => {});
  }, []);

  const approve = (id: number) => api.approve(id).then(load).catch((e) => alert(String(e)));
  const reject = (id: number) => api.reject(id).then(load).catch((e) => alert(String(e)));

  const refreshMarks = async () => {
    setRefreshing(true);
    try { const r = await api.refreshMarks(); setTrades(r.open_trades); }
    catch (e) { alert(String(e)); }
    finally { setRefreshing(false); }
  };

  const totalUnreal = trades.reduce((a, t) => a + (t.unrealized_pnl ?? 0), 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Open Positions</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted">
            Unrealized:{" "}
            <span className={totalUnreal >= 0 ? "text-pos" : "text-neg"}>
              ${totalUnreal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </span>
          <button onClick={refreshMarks} disabled={refreshing}
            className="px-3 py-1.5 rounded bg-panel2 border border-edge text-sm hover:bg-edge disabled:opacity-50">
            {refreshing ? "Refreshing…" : "Refresh live marks"}
          </button>
        </div>
      </div>

      <section>
        <h2 className="text-sm text-muted mb-2">Awaiting approval / review</h2>
        <TradeTable trades={pending} variant="pending" onApprove={approve} onReject={reject} />
      </section>

      <section>
        <h2 className="text-sm text-muted mb-2">Live (paper) positions</h2>
        <TradeTable trades={trades} variant="open" />
        <p className="text-xs text-muted mt-2">
          Unrealized P&L is marked from live option quotes when a quote provider is
          configured (Tradier). Without one, marks stay flat at entry.
        </p>
      </section>
    </div>
  );
}
