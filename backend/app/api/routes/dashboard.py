from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import analytics
from app.services.trade_service import mark_to_market

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview")
def overview(refresh: bool = True, db: Session = Depends(get_db)):
    # Refresh open-position marks from live quotes on load (best-effort).
    if refresh:
        try:
            mark_to_market(db)
        except Exception:  # noqa: BLE001
            pass
    return {
        "summary": analytics.account_summary(db),
        "equity_curve": analytics.equity_curve(db),
        "daily_pnl": analytics.daily_pnl_series(db, days=14),
    }


@router.get("/equity-curve")
def equity(db: Session = Depends(get_db)):
    return analytics.equity_curve(db)


@router.get("/daily-pnl")
def daily(days: int = 30, db: Session = Depends(get_db)):
    return analytics.daily_pnl_series(db, days=days)


@router.get("/strategy-performance")
def strat(db: Session = Depends(get_db)):
    return analytics.strategy_performance(db)


@router.get("/ticker-performance")
def tick(db: Session = Depends(get_db)):
    return analytics.ticker_performance(db)
