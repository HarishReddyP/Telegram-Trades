"""Trade orchestration: ingest a Telegram message → parse → persist alert →
normalize into a Trade → run risk checks → set status.

Default behavior is safe: entries land in NEEDS_REVIEW (if incomplete) or
PENDING_APPROVAL (if complete) and require explicit approval before any order.
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import (
    AlertEvent, StrategyType, TradeStatus, OrderAction, OrderStatus,
    PriceType, LegSide, OptionRight,
)
from app.models.models import (
    TelegramMessage, ParsedAlert, Trade, TradeLeg, Order, Position, RiskRule,
)
from app.parsers.llm_parser import parse_alert_llm as parse_alert
from app.services.risk_engine import evaluate_trade, RiskContext
from app.services import pnl_engine
from app.services.audit import audit
from app.brokers.adapters import get_broker, OrderRequest


def content_hash(channel: str, text: str) -> str:
    return hashlib.sha256(f"{channel}|{(text or '').strip().lower()}".encode()).hexdigest()


def is_duplicate(db: Session, channel: str, text: str) -> bool:
    h = content_hash(channel, text)
    return db.query(TelegramMessage).filter(TelegramMessage.content_hash == h).first() is not None


def get_active_rules(db: Session) -> Optional[RiskRule]:
    return db.query(RiskRule).order_by(RiskRule.id.desc()).first()


def ingest_message(db: Session, *, channel: str, tg_message_id: int,
                   sender: str, text: str, raw: dict = None) -> TelegramMessage:
    """Persist a raw Telegram message (idempotent on channel+tg_message_id)."""
    existing = db.query(TelegramMessage).filter_by(
        channel=channel, tg_message_id=tg_message_id).first()
    if existing:
        return existing
    msg = TelegramMessage(
        channel=channel, tg_message_id=tg_message_id, sender=sender,
        text=text, raw=raw, content_hash=content_hash(channel, text),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    audit(db, "message", "received", msg.id, {"channel": channel, "sender": sender})
    return msg


def process_message(db: Session, msg: TelegramMessage) -> Optional[Trade]:
    """Parse a stored message and normalize into a trade if applicable."""
    result = parse_alert(msg.text)
    alert = ParsedAlert(
        message_id=msg.id,
        event=result.event,
        strategy=result.strategy,
        ticker=result.ticker,
        expiration=result.expiration,
        quantity=result.quantity,
        price=result.price,
        price_type=result.price_type,
        is_complete=result.is_complete,
        confidence=result.confidence,
        legs=[l.to_dict() for l in result.legs],
        parse_notes=result.notes,
        source_text=msg.text,
    )
    db.add(alert)
    msg.processed = True
    db.commit()
    db.refresh(alert)
    audit(db, "alert", "parsed", alert.id,
          {"event": result.event.value, "strategy": result.strategy.value,
           "complete": result.is_complete, "confidence": result.confidence})

    if result.event in (AlertEvent.EXIT, AlertEvent.STOP_LOSS):
        return _handle_exit_alert(db, alert)
    if result.event == AlertEvent.ENTRY:
        return _create_entry_trade(db, alert)
    # ADJUSTMENT / UNKNOWN → leave for manual handling
    return None


def _create_entry_trade(db: Session, alert: ParsedAlert) -> Trade:
    qty = alert.quantity or 1
    legs_payload = alert.legs or []
    width = pnl_engine.spread_width(legs_payload)
    max_risk = None
    if width is not None and alert.price is not None and alert.price_type:
        max_risk = pnl_engine.max_risk_for_spread(
            width=width, entry_credit=alert.price, quantity=qty,
            price_type=alert.price_type,
        )

    trade = Trade(
        alert_id=alert.id,
        strategy=alert.strategy,
        ticker=alert.ticker,
        expiration=alert.expiration,
        quantity=qty,
        entry_price=alert.price,
        entry_price_type=alert.price_type,
        max_risk=max_risk,
        mode=settings.TRADING_MODE,
        status=TradeStatus.NEEDS_REVIEW if not alert.is_complete else TradeStatus.PENDING_APPROVAL,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)

    for l in legs_payload:
        db.add(TradeLeg(
            trade_id=trade.id,
            side=LegSide(l["side"]) if l.get("side") else None,
            right=OptionRight(l["right"]) if l.get("right") else None,
            strike=l.get("strike"),
            expiration=alert.expiration,
            ratio=l.get("ratio", 1),
        ))
    db.commit()

    # Risk evaluation (advisory at this stage; enforced again at approval)
    rules = get_active_rules(db)
    ctx = RiskContext(
        open_trades=_open_trade_count(db),
        realized_today=_realized_today(db),
        starting_capital=_starting_capital(db),
    )
    decision = evaluate_trade(
        ticker=trade.ticker, strategy=trade.strategy, quantity=qty,
        max_risk=max_risk, ctx=ctx, rules=rules,
    )
    if not decision.allowed and trade.status == TradeStatus.PENDING_APPROVAL:
        trade.status = TradeStatus.NEEDS_REVIEW
        trade.review_reason = "; ".join(decision.reasons)
    elif not alert.is_complete:
        trade.review_reason = alert.parse_notes
    db.commit()
    audit(db, "trade", "created", trade.id,
          {"status": trade.status.value, "risk_ok": decision.allowed,
           "reasons": decision.reasons, "max_risk": max_risk})
    return trade


def _handle_exit_alert(db: Session, alert: ParsedAlert) -> Optional[Trade]:
    """Match an exit alert to the most recent open trade on the same ticker."""
    q = db.query(Trade).filter(Trade.status == TradeStatus.OPEN)
    if alert.ticker:
        q = q.filter(Trade.ticker == alert.ticker)
    trade = q.order_by(Trade.opened_at.desc()).first()
    if not trade:
        audit(db, "alert", "exit_unmatched", alert.id, {"ticker": alert.ticker})
        return None
    # Exits are queued for approval too (close orders), price taken from alert
    trade.exit_price = alert.price
    trade.status = TradeStatus.PENDING_APPROVAL
    trade.review_reason = "Exit alert received — approve to close."
    db.commit()
    audit(db, "trade", "exit_queued", trade.id, {"exit_price": alert.price})
    return trade


def approve_trade(db: Session, trade_id: int, actor: str = "user") -> Trade:
    """Manual approval gate. Enforces risk again, then routes to the broker."""
    trade = db.get(Trade, trade_id)
    if not trade:
        raise ValueError("trade not found")
    if trade.status not in (TradeStatus.PENDING_APPROVAL,):
        raise ValueError(f"trade not awaiting approval (status={trade.status.value})")

    # Decide whether this is an open or a close
    is_close = trade.exit_price is not None and trade.status == TradeStatus.PENDING_APPROVAL \
        and trade.opened_at is not None
    rules = get_active_rules(db)

    if not is_close:
        ctx = RiskContext(
            open_trades=_open_trade_count(db),
            realized_today=_realized_today(db),
            starting_capital=_starting_capital(db),
        )
        decision = evaluate_trade(
            ticker=trade.ticker, strategy=trade.strategy, quantity=trade.quantity,
            max_risk=trade.max_risk, ctx=ctx, rules=rules,
        )
        if not decision.allowed:
            trade.status = TradeStatus.NEEDS_REVIEW
            trade.review_reason = "; ".join(decision.reasons)
            db.commit()
            audit(db, "trade", "approval_blocked", trade.id, {"reasons": decision.reasons}, actor)
            raise ValueError("Risk check failed: " + "; ".join(decision.reasons))

    trade.status = TradeStatus.APPROVED
    trade.approved_by = actor
    db.commit()
    audit(db, "trade", "approved", trade.id, {"close": is_close}, actor)

    if is_close:
        return _submit_close(db, trade, rules)
    return _submit_open(db, trade, rules)


def reject_trade(db: Session, trade_id: int, actor: str = "user") -> Trade:
    trade = db.get(Trade, trade_id)
    if not trade:
        raise ValueError("trade not found")
    trade.status = TradeStatus.REJECTED
    db.commit()
    audit(db, "trade", "rejected", trade.id, actor=actor)
    return trade


def _submit_open(db: Session, trade: Trade, rules) -> Trade:
    broker = get_broker()
    legs = [{"side": l.side.value if l.side else None,
             "right": l.right.value if l.right else None,
             "strike": l.strike, "ratio": l.ratio} for l in trade.legs]
    order = Order(
        trade_id=trade.id, action=OrderAction.OPEN, strategy=trade.strategy,
        quantity=trade.quantity, limit_price=trade.entry_price,
        price_type=trade.entry_price_type, status=OrderStatus.DRAFT,
        broker=broker.name, legs=legs, submitted_at=datetime.utcnow(),
    )
    db.add(order); db.commit(); db.refresh(order)

    res = broker.submit(OrderRequest(
        trade_id=trade.id, action=OrderAction.OPEN, strategy=trade.strategy,
        quantity=trade.quantity, limit_price=trade.entry_price,
        price_type=trade.entry_price_type, legs=legs,
        underlying=trade.ticker, expiration=trade.expiration,
    ))
    order.status = res.status
    order.broker_order_id = res.broker_order_id
    order.fill_price = res.fill_price
    order.filled_at = res.filled_at
    db.commit()

    if res.status == OrderStatus.FILLED:
        trade.status = TradeStatus.OPEN
        trade.opened_at = res.filled_at or datetime.utcnow()
        for l in trade.legs:
            l.entry_fill = res.fill_price
        db.add(Position(trade_id=trade.id, is_open=True, quantity=trade.quantity,
                        mark_price=res.fill_price,
                        unrealized_pnl=0.0))
        db.commit()
        audit(db, "order", "filled_open", order.id,
              {"fill": res.fill_price, "broker": broker.name})
    return trade


def _submit_close(db: Session, trade: Trade, rules) -> Trade:
    broker = get_broker()
    legs = [{"side": l.side.value if l.side else None,
             "right": l.right.value if l.right else None,
             "strike": l.strike, "ratio": l.ratio} for l in trade.legs]
    order = Order(
        trade_id=trade.id, action=OrderAction.CLOSE, strategy=trade.strategy,
        quantity=trade.quantity, limit_price=trade.exit_price,
        price_type=trade.entry_price_type, status=OrderStatus.DRAFT,
        broker=broker.name, legs=legs, submitted_at=datetime.utcnow(),
    )
    db.add(order); db.commit(); db.refresh(order)

    res = broker.submit(OrderRequest(
        trade_id=trade.id, action=OrderAction.CLOSE, strategy=trade.strategy,
        quantity=trade.quantity, limit_price=trade.exit_price,
        price_type=trade.entry_price_type, legs=legs,
        underlying=trade.ticker, expiration=trade.expiration,
    ))
    order.status = res.status
    order.broker_order_id = res.broker_order_id
    order.fill_price = res.fill_price
    order.filled_at = res.filled_at
    db.commit()

    if res.status == OrderStatus.FILLED:
        commission = getattr(rules, "commission_per_contract", settings.COMMISSION_PER_CONTRACT)
        pnl = pnl_engine.trade_pnl(
            entry_price=trade.entry_price, exit_price=res.fill_price,
            price_type=trade.entry_price_type, quantity=trade.quantity,
            legs=max(len(trade.legs), 1), commission_per_contract=commission,
        )
        trade.exit_price = res.fill_price
        trade.realized_pnl = pnl.net
        trade.unrealized_pnl = 0.0
        trade.commissions = pnl.commissions
        trade.status = TradeStatus.CLOSED
        trade.closed_at = res.filled_at or datetime.utcnow()
        for l in trade.legs:
            l.exit_fill = res.fill_price
        if trade.position:
            trade.position.is_open = False
            trade.position.unrealized_pnl = 0.0
        db.commit()
        audit(db, "order", "filled_close", order.id,
              {"fill": res.fill_price, "realized_pnl": pnl.net})
        # Snapshot account value after close so equity curve updates
        try:
            from app.services.analytics import snapshot_account
            snapshot_account(db)
        except Exception:  # noqa: BLE001
            pass
    return trade


def live_mark_lookup(trade) -> Optional[float]:
    """Default mark source: price the open spread from live Tradier quotes.
    Returns None when quotes are unavailable so callers fall back to entry."""
    from app.services.quotes import spread_mark, TradierClient
    client = TradierClient()
    if not client.enabled or not trade.entry_price_type:
        return None
    legs = [{"side": l.side.value if l.side else None,
             "right": l.right.value if l.right else None,
             "strike": l.strike, "ratio": l.ratio} for l in trade.legs]
    return spread_mark(
        underlying=trade.ticker,
        expiration=trade.expiration,
        legs=legs,
        price_type=trade.entry_price_type,
        client=client,
    )


def mark_to_market(db: Session, mark_lookup=None):
    """Refresh unrealized P&L for open positions. mark_lookup(trade)->price.
    Defaults to live quotes; falls back to entry price (flat) when unavailable."""
    if mark_lookup is None:
        mark_lookup = live_mark_lookup
    open_trades = db.query(Trade).filter(Trade.status == TradeStatus.OPEN).all()
    for trade in open_trades:
        mark = None
        try:
            mark = mark_lookup(trade)
        except Exception:  # noqa: BLE001
            mark = None
        if mark is None:
            mark = trade.entry_price  # fallback: flat
        u = pnl_engine.unrealized_pnl(
            entry_price=trade.entry_price, mark_price=mark,
            price_type=trade.entry_price_type, quantity=trade.quantity,
        )
        trade.unrealized_pnl = u
        if trade.position:
            trade.position.mark_price = mark
            trade.position.unrealized_pnl = u
    db.commit()


# ---- account helpers ---- #
def _starting_capital(db: Session) -> float:
    rules = get_active_rules(db)
    return getattr(rules, "starting_capital", settings.STARTING_CAPITAL)


def _open_trade_count(db: Session) -> int:
    return db.query(func.count(Trade.id)).filter(Trade.status == TradeStatus.OPEN).scalar() or 0


def _realized_today(db: Session) -> float:
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    val = db.query(func.coalesce(func.sum(Trade.realized_pnl), 0.0)).filter(
        Trade.status == TradeStatus.CLOSED, Trade.closed_at >= start).scalar()
    return float(val or 0.0)
