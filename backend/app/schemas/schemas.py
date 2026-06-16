from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class LegOut(BaseModel):
    side: Optional[str] = None
    right: Optional[str] = None
    strike: Optional[float] = None
    ratio: int = 1


class TradeOut(BaseModel):
    id: int
    strategy: Optional[str]
    ticker: Optional[str]
    expiration: Optional[date]
    quantity: int
    entry_price: Optional[float]
    entry_price_type: Optional[str]
    exit_price: Optional[float]
    status: str
    mode: str
    realized_pnl: float
    unrealized_pnl: float
    max_risk: Optional[float]
    commissions: float
    opened_at: Optional[datetime]
    closed_at: Optional[datetime]
    holding_seconds: Optional[float]
    review_reason: Optional[str]
    legs: List[LegOut] = []

    class Config:
        from_attributes = True


class AlertOut(BaseModel):
    id: int
    event: str
    strategy: str
    ticker: Optional[str]
    expiration: Optional[date]
    quantity: Optional[int]
    price: Optional[float]
    price_type: Optional[str]
    is_complete: bool
    confidence: float
    parse_notes: Optional[str]
    source_text: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    channel: str
    sender: Optional[str]
    text: str
    received_at: datetime
    processed: bool

    class Config:
        from_attributes = True


class RiskRuleIn(BaseModel):
    starting_capital: float
    max_risk_per_trade: float
    max_contracts_per_trade: int
    max_daily_loss: float
    max_open_trades: int
    allowed_tickers: List[str]
    allowed_strategies: List[str]
    no_trade_near_close: bool
    no_trade_minutes_before_close: int
    commission_per_contract: float


class RiskRuleOut(RiskRuleIn):
    id: int

    class Config:
        from_attributes = True


class SimulateAlertIn(BaseModel):
    text: str
    auto_approve: bool = False


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
