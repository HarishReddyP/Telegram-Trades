import type { Trade } from "../types";
import { Badge, money, pnlClass, holdingTime, fmt } from "../lib/ui";

interface Props {
  trades: Trade[];
  variant: "open" | "closed" | "pending";
  onApprove?: (id: number) => void;
  onReject?: (id: number) => void;
}

function legSummary(t: Trade) {
  if (!t.legs.length) return "—";
  return t.legs
    .map((l) => `${l.side?.[0] ?? "?"}${l.strike ?? "?"}${l.right?.[0] ?? ""}`)
    .join(" / ");
}

export default function TradeTable({ trades, variant, onApprove, onReject }: Props) {
  if (!trades.length)
    return <div className="text-muted text-sm py-8 text-center">No trades.</div>;

  return (
    <div className="overflow-x-auto border border-edge rounded-xl">
      <table className="w-full text-sm">
        <thead className="bg-panel2 text-muted text-xs uppercase">
          <tr>
            <th className="text-left px-3 py-2">Ticker</th>
            <th className="text-left px-3 py-2">Strategy</th>
            <th className="text-left px-3 py-2">Legs</th>
            <th className="text-right px-3 py-2">Qty</th>
            <th className="text-right px-3 py-2">Entry</th>
            {variant !== "open" && <th className="text-right px-3 py-2">Exit</th>}
            <th className="text-right px-3 py-2">Max Risk</th>
            {variant === "open" && <th className="text-right px-3 py-2">Unrealized</th>}
            {variant === "closed" && <th className="text-right px-3 py-2">Net P&L</th>}
            {variant === "closed" && <th className="text-right px-3 py-2">Hold</th>}
            <th className="text-left px-3 py-2">Status</th>
            {variant === "pending" && <th className="text-right px-3 py-2">Action</th>}
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id} className="border-t border-edge hover:bg-panel2/50">
              <td className="px-3 py-2 font-medium">{t.ticker ?? "—"}</td>
              <td className="px-3 py-2 text-muted">{t.strategy?.replace(/_/g, " ") ?? "—"}</td>
              <td className="px-3 py-2 text-muted font-mono text-xs">{legSummary(t)}</td>
              <td className="px-3 py-2 text-right">{t.quantity}</td>
              <td className="px-3 py-2 text-right">
                {fmt(t.entry_price)}{" "}
                <span className="text-muted text-xs">{t.entry_price_type?.[0] ?? ""}</span>
              </td>
              {variant !== "open" && <td className="px-3 py-2 text-right">{fmt(t.exit_price)}</td>}
              <td className="px-3 py-2 text-right text-muted">{money(t.max_risk)}</td>
              {variant === "open" && (
                <td className={`px-3 py-2 text-right ${pnlClass(t.unrealized_pnl)}`}>{money(t.unrealized_pnl)}</td>
              )}
              {variant === "closed" && (
                <td className={`px-3 py-2 text-right font-medium ${pnlClass(t.realized_pnl)}`}>{money(t.realized_pnl)}</td>
              )}
              {variant === "closed" && (
                <td className="px-3 py-2 text-right text-muted">{holdingTime(t.holding_seconds)}</td>
              )}
              <td className="px-3 py-2">
                <Badge label={t.status} />
                {t.review_reason && (
                  <div className="text-[11px] text-muted mt-1 max-w-[220px]">{t.review_reason}</div>
                )}
              </td>
              {variant === "pending" && (
                <td className="px-3 py-2 text-right whitespace-nowrap">
                  {t.status === "PENDING_APPROVAL" && (
                    <button onClick={() => onApprove?.(t.id)}
                      className="px-2 py-1 rounded bg-pos/20 text-pos border border-pos/40 text-xs mr-1 hover:bg-pos/30">
                      Approve
                    </button>
                  )}
                  <button onClick={() => onReject?.(t.id)}
                    className="px-2 py-1 rounded bg-neg/20 text-neg border border-neg/40 text-xs hover:bg-neg/30">
                    Reject
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
