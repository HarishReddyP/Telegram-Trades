import { useEffect, useState } from "react";
import { api } from "../lib/api";
import TradeTable from "../components/TradeTable";
import type { Trade } from "../types";

export default function ClosedTrades() {
  const [trades, setTrades] = useState<Trade[]>([]);
  useEffect(() => { api.closedTrades().then(setTrades).catch(() => {}); }, []);
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Closed Trades</h1>
      <TradeTable trades={trades} variant="closed" />
    </div>
  );
}
