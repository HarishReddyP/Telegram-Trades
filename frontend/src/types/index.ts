export interface Leg {
  side: string | null;
  right: string | null;
  strike: number | null;
  ratio: number;
}

export interface Trade {
  id: number;
  strategy: string | null;
  ticker: string | null;
  expiration: string | null;
  quantity: number;
  entry_price: number | null;
  entry_price_type: string | null;
  exit_price: number | null;
  status: string;
  mode: string;
  realized_pnl: number;
  unrealized_pnl: number;
  max_risk: number | null;
  commissions: number;
  opened_at: string | null;
  closed_at: string | null;
  holding_seconds: number | null;
  review_reason: string | null;
  legs: Leg[];
}

export interface Summary {
  starting_capital: number;
  account_value: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  daily_pnl: number;
  open_trades: number;
  closed_trades: number;
  win_rate: number;
  avg_profit: number;
  avg_loss: number;
  max_drawdown: number;
  trading_mode: string;
  manual_approval: boolean;
  live_enabled: boolean;
  kill_switch: boolean;
}

export interface Alert {
  id: number;
  event: string;
  strategy: string;
  ticker: string | null;
  expiration: string | null;
  quantity: number | null;
  price: number | null;
  price_type: string | null;
  is_complete: boolean;
  confidence: number;
  parse_notes: string | null;
  source_text: string;
  created_at: string;
}

export interface RiskRule {
  id?: number;
  starting_capital: number;
  max_risk_per_trade: number;
  max_contracts_per_trade: number;
  max_daily_loss: number;
  max_open_trades: number;
  allowed_tickers: string[];
  allowed_strategies: string[];
  no_trade_near_close: boolean;
  no_trade_minutes_before_close: number;
  commission_per_contract: number;
}
