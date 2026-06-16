"""Account & analytics aggregations for the dashboard."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import TradeStatus
from app.models.models import Trade, PnLSnapshot


def starting_capital(db: Session) -> float:
    from app.services.trade_service import _starting_capital
    return _starting_capital(db)


def snapshot_account(db: Session) -> PnLSnapshot:
    """Take a point-in-time snapshot of account value and persist it."""
    summary = account_summary(db)
    snap = PnLSnapshot(
        snapshot_at=datetime.utcnow(),
        account_value=summary["account_value"],
        realized_pnl=summary["realized_pnl"],
        unrealized_pnl=summary["unrealized_pnl"],
        daily_pnl=summary["daily_pnl"],
        open_trades=summary["open_trades"],
    )
    db.add(snap)
    db.commit()
    return snap


def account_summary(db: Session) -> dict:
    start_cap = starting_capital(db)
    realized = db.query(func.coalesce(func.sum(Trade.realized_pnl), 0.0)).filter(
        Trade.status == TradeStatus.CLOSED).scalar() or 0.0
    unrealized = db.query(func.coalesce(func.sum(Trade.unrealized_pnl), 0.0)).filter(
        Trade.status == TradeStatus.OPEN).scalar() or 0.0
    account_value = start_cap + realized + unrealized

    day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    daily_realized = db.query(func.coalesce(func.sum(Trade.realized_pnl), 0.0)).filter(
        Trade.status == TradeStatus.CLOSED, Trade.closed_at >= day_start).scalar() or 0.0
    daily_pnl = daily_realized + unrealized

    open_count = db.query(func.count(Trade.id)).filter(
        Trade.status == TradeStatus.OPEN).scalar() or 0
    closed = db.query(Trade).filter(Trade.status == TradeStatus.CLOSED).all()
    closed_count = len(closed)
    wins = [t for t in closed if (t.realized_pnl or 0) > 0]
    losses = [t for t in closed if (t.realized_pnl or 0) < 0]
    win_rate = (len(wins) / closed_count * 100) if closed_count else 0.0
    avg_profit = (sum(t.realized_pnl for t in wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(t.realized_pnl for t in losses) / len(losses)) if losses else 0.0

    return {
        "starting_capital": round(start_cap, 2),
        "account_value": round(account_value, 2),
        "realized_pnl": round(realized, 2),
        "unrealized_pnl": round(unrealized, 2),
        "total_pnl": round(realized + unrealized, 2),
        "daily_pnl": round(daily_pnl, 2),
        "open_trades": open_count,
        "closed_trades": closed_count,
        "win_rate": round(win_rate, 1),
        "avg_profit": round(avg_profit, 2),
        "avg_loss": round(avg_loss, 2),
        "max_drawdown": round(max_drawdown(db), 2),
        "trading_mode": settings.TRADING_MODE,
        "manual_approval": settings.MANUAL_APPROVAL,
        "live_enabled": settings.LIVE_TRADING_ENABLED,
        "kill_switch": settings.KILL_SWITCH,
    }


def equity_curve(db: Session):
    """Account value over time using PnL snapshots (taken after each trade event)."""
    start_cap = starting_capital(db)
    snaps = db.query(PnLSnapshot).order_by(PnLSnapshot.snapshot_at.asc()).all()
    if snaps:
        points = [{"t": s.snapshot_at.isoformat(), "value": round(s.account_value, 2)}
                  for s in snaps]
    else:
        # Fall back to closed-trade reconstruction when no snapshots exist
        closed = db.query(Trade).filter(
            Trade.status == TradeStatus.CLOSED, Trade.closed_at.isnot(None)
        ).order_by(Trade.closed_at.asc()).all()
        running = start_cap
        points = []
        for t in closed:
            running += (t.realized_pnl or 0.0)
            points.append({"t": t.closed_at.isoformat(), "value": round(running, 2)})
    if not points:
        points = [{"t": datetime.utcnow().isoformat(), "value": round(start_cap, 2)}]
    return points


def max_drawdown(db: Session) -> float:
    curve = [p["value"] for p in equity_curve(db)]
    peak = curve[0]
    mdd = 0.0
    for v in curve:
        peak = max(peak, v)
        mdd = min(mdd, v - peak)
    return mdd


def daily_pnl_series(db: Session, days: int = 30):
    closed = db.query(Trade).filter(
        Trade.status == TradeStatus.CLOSED, Trade.closed_at.isnot(None)).all()
    by_day = defaultdict(float)
    for t in closed:
        by_day[t.closed_at.date().isoformat()] += (t.realized_pnl or 0.0)
    today = date.today()
    out = []
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        out.append({"date": d, "pnl": round(by_day.get(d, 0.0), 2)})
    return out


def strategy_performance(db: Session):
    closed = db.query(Trade).filter(Trade.status == TradeStatus.CLOSED).all()
    agg = defaultdict(lambda: {"trades": 0, "pnl": 0.0, "wins": 0})
    for t in closed:
        k = t.strategy.value if t.strategy else "UNKNOWN"
        agg[k]["trades"] += 1
        agg[k]["pnl"] += (t.realized_pnl or 0.0)
        if (t.realized_pnl or 0) > 0:
            agg[k]["wins"] += 1
    return [
        {"strategy": k, "trades": v["trades"], "pnl": round(v["pnl"], 2),
         "win_rate": round(v["wins"] / v["trades"] * 100, 1) if v["trades"] else 0.0}
        for k, v in agg.items()
    ]


def ticker_performance(db: Session):
    closed = db.query(Trade).filter(Trade.status == TradeStatus.CLOSED).all()
    agg = defaultdict(lambda: {"trades": 0, "pnl": 0.0})
    for t in closed:
        k = t.ticker or "?"
        agg[k]["trades"] += 1
        agg[k]["pnl"] += (t.realized_pnl or 0.0)
    return [{"ticker": k, "trades": v["trades"], "pnl": round(v["pnl"], 2)}
            for k, v in agg.items()]
