"""SQLAlchemy ORM models for every required table.

Tables: users, telegram_messages, parsed_alerts, trades, trade_legs, orders,
positions, pnl_snapshots, daily_reports, settings, risk_rules, email_logs,
audit_logs.
"""
from datetime import datetime, date

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, Float, ForeignKey, Integer,
    JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.core.enums import (
    StrategyType, AlertEvent, OptionRight, LegSide, PriceType,
    TradeStatus, OrderStatus, OrderAction,
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="trader")  # trader | admin | viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TelegramMessage(Base):
    __tablename__ = "telegram_messages"
    id = Column(Integer, primary_key=True)
    tg_message_id = Column(Integer, index=True)
    channel = Column(String(255), index=True)
    sender = Column(String(255), nullable=True)
    text = Column(Text)
    raw = Column(JSON, nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow, index=True)
    processed = Column(Boolean, default=False)
    content_hash = Column(String(64), index=True)  # for duplicate detection

    __table_args__ = (
        UniqueConstraint("channel", "tg_message_id", name="uq_channel_msg"),
    )

    parsed_alert = relationship("ParsedAlert", back_populates="message", uselist=False)


class ParsedAlert(Base):
    __tablename__ = "parsed_alerts"
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("telegram_messages.id"))
    event = Column(Enum(AlertEvent), default=AlertEvent.UNKNOWN)
    strategy = Column(Enum(StrategyType), default=StrategyType.UNKNOWN)
    ticker = Column(String(16), index=True, nullable=True)
    expiration = Column(Date, nullable=True)
    quantity = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)            # credit or debit, abs value
    price_type = Column(Enum(PriceType), nullable=True)
    is_complete = Column(Boolean, default=False)
    confidence = Column(Float, default=0.0)
    legs = Column(JSON, default=list)               # list of leg dicts
    parse_notes = Column(Text, nullable=True)
    source_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    message = relationship("TelegramMessage", back_populates="parsed_alert")
    trade = relationship("Trade", back_populates="alert", uselist=False)


class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    alert_id = Column(Integer, ForeignKey("parsed_alerts.id"), nullable=True)
    strategy = Column(Enum(StrategyType))
    ticker = Column(String(16), index=True)
    expiration = Column(Date, nullable=True)
    quantity = Column(Integer, default=1)
    entry_price = Column(Float, nullable=True)       # credit(+)/debit value at open
    entry_price_type = Column(Enum(PriceType), nullable=True)
    exit_price = Column(Float, nullable=True)
    status = Column(Enum(TradeStatus), default=TradeStatus.NEEDS_REVIEW, index=True)
    mode = Column(String(10), default="paper")       # paper | live
    realized_pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    max_risk = Column(Float, nullable=True)
    commissions = Column(Float, default=0.0)
    opened_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    approved_by = Column(String(255), nullable=True)
    review_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    alert = relationship("ParsedAlert", back_populates="trade")
    legs = relationship("TradeLeg", back_populates="trade", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="trade", cascade="all, delete-orphan")
    position = relationship("Position", back_populates="trade", uselist=False)

    @property
    def holding_seconds(self):
        if self.opened_at and self.closed_at:
            return (self.closed_at - self.opened_at).total_seconds()
        return None


class TradeLeg(Base):
    __tablename__ = "trade_legs"
    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer, ForeignKey("trades.id"))
    side = Column(Enum(LegSide))
    right = Column(Enum(OptionRight))
    strike = Column(Float)
    expiration = Column(Date, nullable=True)
    ratio = Column(Integer, default=1)
    entry_fill = Column(Float, nullable=True)
    exit_fill = Column(Float, nullable=True)

    trade = relationship("Trade", back_populates="legs")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer, ForeignKey("trades.id"))
    action = Column(Enum(OrderAction))               # OPEN | CLOSE
    strategy = Column(Enum(StrategyType))
    quantity = Column(Integer)
    limit_price = Column(Float, nullable=True)
    price_type = Column(Enum(PriceType), nullable=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.DRAFT)
    broker = Column(String(50), default="paper")
    broker_order_id = Column(String(128), nullable=True)
    legs = Column(JSON, default=list)
    fill_price = Column(Float, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    filled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    trade = relationship("Trade", back_populates="orders")


class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), unique=True)
    is_open = Column(Boolean, default=True, index=True)
    quantity = Column(Integer)
    mark_price = Column(Float, nullable=True)         # current mark for the spread
    unrealized_pnl = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow)

    trade = relationship("Trade", back_populates="position")


class PnLSnapshot(Base):
    __tablename__ = "pnl_snapshots"
    id = Column(Integer, primary_key=True)
    snapshot_at = Column(DateTime, default=datetime.utcnow, index=True)
    account_value = Column(Float)
    realized_pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    daily_pnl = Column(Float, default=0.0)
    open_trades = Column(Integer, default=0)


class DailyReport(Base):
    __tablename__ = "daily_reports"
    id = Column(Integer, primary_key=True)
    report_date = Column(Date, unique=True, index=True)
    starting_value = Column(Float)
    ending_value = Column(Float)
    daily_pnl = Column(Float)
    realized_pnl = Column(Float)
    unrealized_pnl = Column(Float)
    trades_opened = Column(Integer, default=0)
    trades_closed = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SettingKV(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, index=True)
    value = Column(JSON)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RiskRule(Base):
    __tablename__ = "risk_rules"
    id = Column(Integer, primary_key=True)
    starting_capital = Column(Float, default=25000)
    max_risk_per_trade = Column(Float, default=500)
    max_contracts_per_trade = Column(Integer, default=5)
    max_daily_loss = Column(Float, default=1000)
    max_open_trades = Column(Integer, default=5)
    allowed_tickers = Column(JSON, default=list)
    allowed_strategies = Column(JSON, default=list)
    no_trade_near_close = Column(Boolean, default=True)
    no_trade_minutes_before_close = Column(Integer, default=15)
    commission_per_contract = Column(Float, default=0.65)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmailLog(Base):
    __tablename__ = "email_logs"
    id = Column(Integer, primary_key=True)
    to_addr = Column(String(255))
    subject = Column(String(500))
    body_preview = Column(Text)
    kind = Column(String(50))                        # entry | exit | eod
    status = Column(String(50), default="queued")    # queued | sent | failed
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    entity = Column(String(50), index=True)          # message|alert|trade|order|pnl
    entity_id = Column(Integer, nullable=True)
    action = Column(String(100))
    detail = Column(JSON, nullable=True)
    actor = Column(String(255), default="system")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
