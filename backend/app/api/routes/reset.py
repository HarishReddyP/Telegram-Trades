"""Reset endpoint — wipes all trade data and starts fresh."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import (
    Trade, TradeLeg, Order, Position,
    ParsedAlert, TelegramMessage, PnLSnapshot, AuditLog,
)
from app.services.analytics import snapshot_account

router = APIRouter(prefix="/api", tags=["reset"])


@router.delete("/reset")
def reset_all(db: Session = Depends(get_db)):
    """Delete all trades, alerts, messages and P&L history. Risk rules are kept."""
    counts = {}
    for Model in (AuditLog, Order, TradeLeg, Position, Trade,
                  ParsedAlert, TelegramMessage, PnLSnapshot):
        n = db.query(Model).delete(synchronize_session=False)
        counts[Model.__tablename__] = n
    db.commit()

    # Take a fresh baseline snapshot at starting capital
    snap = snapshot_account(db)
    return {
        "status": "reset",
        "deleted": counts,
        "account_value": snap.account_value,
    }
