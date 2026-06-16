"""End-of-day report builder + persistence."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.enums import TradeStatus
from app.models.models import Trade, DailyReport, PnLSnapshot
from app.services import analytics


def build_and_store_eod(db: Session, for_date: date = None) -> dict:
    for_date = for_date or date.today()
    day_start = datetime.combine(for_date, datetime.min.time())
    day_end = datetime.combine(for_date, datetime.max.time())

    summary = analytics.account_summary(db)

    opened = db.query(func.count(Trade.id)).filter(
        Trade.opened_at >= day_start, Trade.opened_at <= day_end).scalar() or 0
    closed_today = db.query(Trade).filter(
        Trade.status == TradeStatus.CLOSED,
        Trade.closed_at >= day_start, Trade.closed_at <= day_end).all()
    closed_count = len(closed_today)
    wins = [t for t in closed_today if (t.realized_pnl or 0) > 0]
    win_rate = (len(wins) / closed_count * 100) if closed_count else 0.0
    realized_today = sum(t.realized_pnl or 0 for t in closed_today)

    ending_value = summary["account_value"]
    starting_value = ending_value - summary["daily_pnl"]

    payload = {
        "report_date": for_date.isoformat(),
        "starting_value": round(starting_value, 2),
        "ending_value": round(ending_value, 2),
        "daily_pnl": round(summary["daily_pnl"], 2),
        "realized_pnl": round(realized_today, 2),
        "unrealized_pnl": round(summary["unrealized_pnl"], 2),
        "trades_opened": opened,
        "trades_closed": closed_count,
        "win_rate": round(win_rate, 1),
        "open_trades": summary["open_trades"],
        "total_pnl": summary["total_pnl"],
    }

    existing = db.query(DailyReport).filter_by(report_date=for_date).first()
    if existing:
        for k in ("starting_value", "ending_value", "daily_pnl", "realized_pnl",
                  "unrealized_pnl", "trades_opened", "trades_closed", "win_rate"):
            setattr(existing, k, payload[k])
        existing.payload = payload
    else:
        db.add(DailyReport(
            report_date=for_date,
            starting_value=payload["starting_value"],
            ending_value=payload["ending_value"],
            daily_pnl=payload["daily_pnl"],
            realized_pnl=payload["realized_pnl"],
            unrealized_pnl=payload["unrealized_pnl"],
            trades_opened=opened,
            trades_closed=closed_count,
            win_rate=payload["win_rate"],
            payload=payload,
        ))
    db.add(PnLSnapshot(
        account_value=ending_value,
        realized_pnl=summary["realized_pnl"],
        unrealized_pnl=summary["unrealized_pnl"],
        daily_pnl=summary["daily_pnl"],
        open_trades=summary["open_trades"],
    ))
    db.commit()
    return payload
