from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.enums import TradeStatus
from app.models.models import Trade
from app.schemas.schemas import TradeOut
from app.services import trade_service, email_service

router = APIRouter(prefix="/api/trades", tags=["trades"])


def _to_out(t: Trade) -> dict:
    return {
        "id": t.id,
        "strategy": t.strategy.value if t.strategy else None,
        "ticker": t.ticker,
        "expiration": t.expiration,
        "quantity": t.quantity,
        "entry_price": t.entry_price,
        "entry_price_type": t.entry_price_type.value if t.entry_price_type else None,
        "exit_price": t.exit_price,
        "status": t.status.value,
        "mode": t.mode,
        "realized_pnl": t.realized_pnl,
        "unrealized_pnl": t.unrealized_pnl,
        "max_risk": t.max_risk,
        "commissions": t.commissions,
        "opened_at": t.opened_at,
        "closed_at": t.closed_at,
        "holding_seconds": t.holding_seconds,
        "review_reason": t.review_reason,
        "legs": [{"side": l.side.value if l.side else None,
                  "right": l.right.value if l.right else None,
                  "strike": l.strike, "ratio": l.ratio} for l in t.legs],
    }


@router.get("", response_model=List[TradeOut])
def list_trades(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Trade)
    if status:
        q = q.filter(Trade.status == TradeStatus(status))
    return [_to_out(t) for t in q.order_by(Trade.created_at.desc()).all()]


@router.get("/open", response_model=List[TradeOut])
def open_trades(db: Session = Depends(get_db)):
    return [_to_out(t) for t in db.query(Trade).filter(
        Trade.status == TradeStatus.OPEN).all()]


@router.get("/closed", response_model=List[TradeOut])
def closed_trades(db: Session = Depends(get_db)):
    return [_to_out(t) for t in db.query(Trade).filter(
        Trade.status == TradeStatus.CLOSED).order_by(Trade.closed_at.desc()).all()]


@router.get("/pending", response_model=List[TradeOut])
def pending(db: Session = Depends(get_db)):
    return [_to_out(t) for t in db.query(Trade).filter(
        Trade.status.in_([TradeStatus.PENDING_APPROVAL, TradeStatus.NEEDS_REVIEW])
    ).order_by(Trade.created_at.desc()).all()]


@router.post("/refresh-marks")
def refresh_marks(db: Session = Depends(get_db)):
    """Re-price all open positions from live quotes (or flat if unavailable)."""
    trade_service.mark_to_market(db)
    return {"refreshed": True, "open_trades": [
        _to_out(t) for t in db.query(Trade).filter(Trade.status == TradeStatus.OPEN).all()
    ]}


@router.get("/{trade_id}", response_model=TradeOut)
def get_trade(trade_id: int, db: Session = Depends(get_db)):
    t = db.get(Trade, trade_id)
    if not t:
        raise HTTPException(404, "trade not found")
    return _to_out(t)


@router.post("/{trade_id}/approve", response_model=TradeOut)
def approve(trade_id: int, db: Session = Depends(get_db)):
    try:
        t = trade_service.approve_trade(db, trade_id, actor="user")
    except ValueError as e:
        raise HTTPException(400, str(e))
    # Fire notifications based on the resulting state
    try:
        if t.status == TradeStatus.OPEN:
            email_service.notify_entry(db, t)
        elif t.status == TradeStatus.CLOSED:
            email_service.notify_exit(db, t)
    except Exception:  # noqa: BLE001
        pass
    return _to_out(t)


@router.post("/{trade_id}/reject", response_model=TradeOut)
def reject(trade_id: int, db: Session = Depends(get_db)):
    try:
        t = trade_service.reject_trade(db, trade_id, actor="user")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _to_out(t)
