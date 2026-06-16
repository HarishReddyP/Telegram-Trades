from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import ParsedAlert, TelegramMessage
from app.schemas.schemas import AlertOut, MessageOut, SimulateAlertIn
from app.parsers.llm_parser import parse_alert_llm as parse_alert
from app.services import trade_service
from app.api.routes.trades import _to_out

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=List[AlertOut])
def list_alerts(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(ParsedAlert).order_by(
        ParsedAlert.created_at.desc()).limit(limit).all()


@router.get("/messages", response_model=List[MessageOut])
def list_messages(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(TelegramMessage).order_by(
        TelegramMessage.received_at.desc()).limit(limit).all()


@router.post("/preview")
def preview(body: SimulateAlertIn):
    """Parse text without persisting — useful for testing parser output."""
    return parse_alert(body.text).to_payload()


@router.post("/simulate")
def simulate(body: SimulateAlertIn, db: Session = Depends(get_db)):
    """Inject a synthetic alert as if it arrived on Telegram. Respects the
    duplicate guard and the full normalize→risk pipeline. Optionally
    auto-approves (paper mode convenience)."""
    import time
    msg = trade_service.ingest_message(
        db, channel="SIMULATION", tg_message_id=int(time.time() * 1000) % 2_000_000_000,
        sender="simulator", text=body.text, raw={"simulated": True},
    )
    trade = trade_service.process_message(db, msg)
    result = {"message_id": msg.id, "trade": _to_out(trade) if trade else None}
    if trade and body.auto_approve and trade.status.value == "PENDING_APPROVAL":
        try:
            trade = trade_service.approve_trade(db, trade.id, actor="simulator")
            result["trade"] = _to_out(trade)
        except ValueError as e:
            result["approve_error"] = str(e)
    return result
