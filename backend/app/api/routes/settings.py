from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.core.security import verify_password, create_token
from app.models.models import RiskRule, User
from app.schemas.schemas import RiskRuleIn, RiskRuleOut, LoginIn, TokenOut
from app.services.trade_service import get_active_rules
from app.services.audit import audit

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/risk-rules", response_model=RiskRuleOut)
def get_rules(db: Session = Depends(get_db)):
    r = get_active_rules(db)
    if not r:
        raise HTTPException(404, "no risk rules configured")
    return r


@router.put("/risk-rules", response_model=RiskRuleOut)
def update_rules(body: RiskRuleIn, db: Session = Depends(get_db)):
    r = RiskRule(**body.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    audit(db, "risk_rule", "updated", r.id, body.model_dump())
    return r


@router.get("/settings")
def get_settings_view(db: Session = Depends(get_db)):
    return {
        "trading_mode": settings.TRADING_MODE,
        "manual_approval": settings.MANUAL_APPROVAL,
        "live_trading_enabled": settings.LIVE_TRADING_ENABLED,
        "kill_switch": settings.KILL_SWITCH,
        "telegram_channel": settings.TELEGRAM_CHANNEL,
        "report_recipient": settings.REPORT_RECIPIENT,
        "market_tz": settings.MARKET_TZ,
        "market_close": settings.MARKET_CLOSE,
    }


@router.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "invalid credentials")
    return TokenOut(access_token=create_token(user.email))
