"""Risk engine — validates a normalized trade against configured rules
before it can be approved or sent to a broker."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Optional
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.enums import StrategyType


@dataclass
class RiskContext:
    open_trades: int
    realized_today: float            # realized P&L so far today (negative = loss)
    starting_capital: float


@dataclass
class RiskDecision:
    allowed: bool
    reasons: List[str] = field(default_factory=list)

    def block(self, reason: str):
        self.allowed = False
        self.reasons.append(reason)


def _market_close_dt(now: datetime) -> datetime:
    hh, mm = (int(x) for x in settings.MARKET_CLOSE.split(":"))
    return now.replace(hour=hh, minute=mm, second=0, microsecond=0)


def evaluate_trade(
    *,
    ticker: Optional[str],
    strategy: StrategyType,
    quantity: int,
    max_risk: Optional[float],
    ctx: RiskContext,
    now: Optional[datetime] = None,
    rules=None,
) -> RiskDecision:
    """rules: an optional RiskRule ORM row; falls back to settings."""
    d = RiskDecision(allowed=True)

    max_risk_per_trade = getattr(rules, "max_risk_per_trade", settings.MAX_RISK_PER_TRADE)
    max_contracts = getattr(rules, "max_contracts_per_trade", settings.MAX_CONTRACTS_PER_TRADE)
    max_daily_loss = getattr(rules, "max_daily_loss", settings.MAX_DAILY_LOSS)
    max_open = getattr(rules, "max_open_trades", settings.MAX_OPEN_TRADES)
    _db_tickers = getattr(rules, "allowed_tickers", None)
    allowed_tickers = _db_tickers if _db_tickers is not None else settings.allowed_tickers
    allowed_strategies = getattr(rules, "allowed_strategies", None) or settings.allowed_strategies
    no_trade_near_close = getattr(rules, "no_trade_near_close", settings.NO_TRADE_NEAR_CLOSE)
    mins_before = getattr(rules, "no_trade_minutes_before_close",
                          settings.NO_TRADE_MINUTES_BEFORE_CLOSE)

    if settings.KILL_SWITCH:
        d.block("Kill switch is active — all new orders halted.")

    if ticker and allowed_tickers and ticker.upper() not in [t.upper() for t in allowed_tickers]:
        d.block(f"Ticker {ticker} not in allowed list {allowed_tickers}.")

    if strategy and allowed_strategies and strategy.value not in [s.upper() for s in allowed_strategies]:
        d.block(f"Strategy {strategy.value} not in allowed list.")

    if quantity > max_contracts:
        d.block(f"Quantity {quantity} exceeds max contracts {max_contracts}.")

    if max_risk is not None and max_risk > max_risk_per_trade:
        d.block(f"Max risk ${max_risk:.0f} exceeds per-trade cap ${max_risk_per_trade:.0f}.")

    if ctx.open_trades >= max_open:
        d.block(f"Open trades {ctx.open_trades} at/over max {max_open}.")

    if ctx.realized_today <= -abs(max_daily_loss):
        d.block(f"Daily loss limit hit (realized ${ctx.realized_today:.0f}).")

    if no_trade_near_close:
        now = now or datetime.now(ZoneInfo(settings.MARKET_TZ))
        close_dt = _market_close_dt(now)
        cutoff = close_dt.timestamp() - mins_before * 60
        if now.timestamp() >= cutoff and now.timestamp() < close_dt.timestamp():
            d.block(f"Within {mins_before}m of market close — entries disabled.")

    return d
