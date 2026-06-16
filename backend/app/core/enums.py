import enum


class StrategyType(str, enum.Enum):
    BULL_PUT_SPREAD = "BULL_PUT_SPREAD"
    BEAR_CALL_SPREAD = "BEAR_CALL_SPREAD"
    IRON_CONDOR = "IRON_CONDOR"
    IRON_FLY = "IRON_FLY"
    BUTTERFLY = "BUTTERFLY"
    SINGLE_LEG = "SINGLE_LEG"
    UNKNOWN = "UNKNOWN"


class AlertEvent(str, enum.Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    STOP_LOSS = "STOP_LOSS"
    ADJUSTMENT = "ADJUSTMENT"
    UNKNOWN = "UNKNOWN"


class OptionRight(str, enum.Enum):
    CALL = "CALL"
    PUT = "PUT"


class LegSide(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class PriceType(str, enum.Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class TradeStatus(str, enum.Enum):
    NEEDS_REVIEW = "NEEDS_REVIEW"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class OrderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class OrderAction(str, enum.Enum):
    OPEN = "OPEN"
    CLOSE = "CLOSE"


class TradingMode(str, enum.Enum):
    PAPER = "paper"
    LIVE = "live"
