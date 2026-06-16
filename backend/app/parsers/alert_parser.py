"""Telegram options-alert parser.

Heuristic + regex engine that turns free-text alerts into a structured
``ParsedAlertResult``. It is deliberately tolerant: real alert channels are
messy. When something can't be determined, fields are left ``None`` and the
result is marked incomplete so the trade routes to NEEDS_REVIEW.

Recognized strategies:
  BULL_PUT_SPREAD, BEAR_CALL_SPREAD, IRON_CONDOR, IRON_FLY, BUTTERFLY, SINGLE_LEG
Recognized events:
  ENTRY, EXIT, STOP_LOSS, ADJUSTMENT
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import List, Optional

from app.core.enums import (
    StrategyType, AlertEvent, OptionRight, LegSide, PriceType,
)


@dataclass
class ParsedLeg:
    side: Optional[LegSide] = None
    right: Optional[OptionRight] = None
    strike: Optional[float] = None
    ratio: int = 1

    def to_dict(self):
        d = asdict(self)
        d["side"] = self.side.value if self.side else None
        d["right"] = self.right.value if self.right else None
        return d


@dataclass
class ParsedAlertResult:
    event: AlertEvent = AlertEvent.UNKNOWN
    strategy: StrategyType = StrategyType.UNKNOWN
    ticker: Optional[str] = None
    expiration: Optional[date] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    price_type: Optional[PriceType] = None
    legs: List[ParsedLeg] = field(default_factory=list)
    confidence: float = 0.0
    notes: str = ""
    source_text: str = ""

    @property
    def is_complete(self) -> bool:
        if self.event in (AlertEvent.EXIT, AlertEvent.STOP_LOSS):
            # exits only need to identify the underlying + an exit price
            return self.ticker is not None and self.price is not None
        if self.strategy == StrategyType.SINGLE_LEG:
            return all([self.ticker, self.legs, self.price is not None])
        # multi-leg entries need ticker, >=2 legs, a net price
        return all([
            self.ticker,
            self.strategy != StrategyType.UNKNOWN,
            len(self.legs) >= 2,
            self.price is not None,
        ])

    def to_payload(self):
        return {
            "event": self.event.value,
            "strategy": self.strategy.value,
            "ticker": self.ticker,
            "expiration": self.expiration.isoformat() if self.expiration else None,
            "quantity": self.quantity,
            "price": self.price,
            "price_type": self.price_type.value if self.price_type else None,
            "legs": [l.to_dict() for l in self.legs],
            "confidence": round(self.confidence, 2),
            "is_complete": self.is_complete,
            "notes": self.notes,
        }


# --------------------------------------------------------------------------- #
# Pattern dictionaries
# --------------------------------------------------------------------------- #
_TICKER_RE = re.compile(r"\$?\b([A-Z]{1,5})\b")
_QTY_RE = re.compile(r"\b(\d{1,3})\s*(?:x|contracts?|lots?|qty)\b", re.I)
_QTY_X_RE = re.compile(r"\bx\s*(\d{1,3})\b", re.I)
_CREDIT_RE = re.compile(r"(?:credit|cr|for)\s*\$?\s*(\d+(?:\.\d+)?)", re.I)
_DEBIT_RE = re.compile(r"(?:debit|db|paid)\s*\$?\s*(\d+(?:\.\d+)?)", re.I)
_AT_PRICE_RE = re.compile(r"@\s*\$?\s*(\d+(?:\.\d+)?)")
_STRIKE_PUT_RE = re.compile(r"(\d{2,5}(?:\.\d+)?)\s*[pP]\b")
_STRIKE_CALL_RE = re.compile(r"(\d{2,5}(?:\.\d+)?)\s*[cC]\b")
_SPREAD_PAIR_RE = re.compile(r"(\d{2,5}(?:\.\d+)?)\s*/\s*(\d{2,5}(?:\.\d+)?)")

_KNOWN_TICKERS = {
    "SPX", "SPY", "QQQ", "IWM", "NDX", "VIX", "DIA", "AAPL", "TSLA", "NVDA",
    "AMZN", "MSFT", "META", "GOOG", "GOOGL", "AMD", "ADBE", "NBIS", "IONQ",
}
_STOPWORDS = {
    "BTO", "STO", "BTC", "STC", "PUT", "CALL", "BUY", "SELL", "SPREAD", "IRON",
    "CONDOR", "FLY", "BUTTERFLY", "CREDIT", "DEBIT", "ENTRY", "EXIT", "STOP",
    "LOSS", "OPEN", "CLOSE", "TRIM", "ROLL", "ADJUST", "FILLED", "ALERT", "LOT",
    "QTY", "DTE", "EXP", "FOR", "AT", "THE",
}

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _detect_event(t: str) -> AlertEvent:
    low = t.lower()
    if any(k in low for k in ["stop loss", "stopped out", "sl hit", "stop hit"]):
        return AlertEvent.STOP_LOSS
    if any(k in low for k in ["adjust", "roll ", "rolling", "roll to"]):
        return AlertEvent.ADJUSTMENT
    if any(k in low for k in ["exit", "close", "closing", "btc", "stc", "took profit",
                              "take profit", "trim", "sold to close", "bought to close"]):
        return AlertEvent.EXIT
    if any(k in low for k in ["entry", "open", "bto", "sto", "new trade", "selling",
                              "buying", "sell ", "buy ", "sold ", "bought ", "credit",
                              "debit", "spread", "condor", "iron", "butterfly", "fly"]):
        return AlertEvent.ENTRY
    return AlertEvent.UNKNOWN


def _detect_strategy(t: str, legs: List[ParsedLeg]) -> StrategyType:
    low = t.lower()
    if "iron condor" in low or re.search(r"\bic\b", low):
        return StrategyType.IRON_CONDOR
    if "iron fly" in low or "iron butterfly" in low:
        return StrategyType.IRON_FLY
    if "butterfly" in low or re.search(r"\bbfly\b", low):
        return StrategyType.BUTTERFLY
    if "bull put" in low:
        return StrategyType.BULL_PUT_SPREAD
    if "bear call" in low:
        return StrategyType.BEAR_CALL_SPREAD
    # "put credit spread" is a bull put; "call credit spread" is a bear call
    if "put" in low and "spread" in low and "call" not in low:
        return StrategyType.BULL_PUT_SPREAD
    if "call" in low and "spread" in low and "put" not in low:
        return StrategyType.BEAR_CALL_SPREAD

    puts = [l for l in legs if l.right == OptionRight.PUT]
    calls = [l for l in legs if l.right == OptionRight.CALL]
    if len(puts) == 2 and len(calls) == 2:
        shorts = sorted(l.strike for l in legs if l.side == LegSide.SELL and l.strike)
        if len(shorts) == 2 and abs(shorts[0] - shorts[1]) < 1e-6:
            return StrategyType.IRON_FLY
        return StrategyType.IRON_CONDOR
    if len(puts) == 2 and not calls:
        return StrategyType.BULL_PUT_SPREAD
    if len(calls) == 2 and not puts:
        return StrategyType.BEAR_CALL_SPREAD
    if len(legs) == 3:
        return StrategyType.BUTTERFLY
    if len(legs) == 1:
        return StrategyType.SINGLE_LEG
    return StrategyType.UNKNOWN


def _extract_ticker(t: str) -> Optional[str]:
    # Prefer an explicit $TICKER
    m = re.search(r"\$([A-Z]{1,5})\b", t)
    if m:
        return m.group(1)
    for tok in _TICKER_RE.findall(t):
        if tok in _KNOWN_TICKERS:
            return tok
    for tok in _TICKER_RE.findall(t):
        if tok not in _STOPWORDS and 1 <= len(tok) <= 5:
            return tok
    return None


def _extract_expiration(t: str) -> Optional[date]:
    # 2026-06-19 / 06/19/2026 / 06/19 / Jun 19 / 6/19/26 / 19JUN26
    m = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", t)
    if m:
        y, mo, d = map(int, m.groups())
        return _safe_date(y, mo, d)
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", t)
    if m:
        mo, d, y = map(int, m.groups())
        y = y + 2000 if y < 100 else y
        return _safe_date(y, mo, d)
    m = re.search(r"\b([A-Za-z]{3})\s*(\d{1,2})(?:,?\s*(\d{2,4}))?\b", t)
    if m and m.group(1).lower() in _MONTHS:
        mo = _MONTHS[m.group(1).lower()]
        d = int(m.group(2))
        y = int(m.group(3)) if m.group(3) else datetime.utcnow().year
        y = y + 2000 if y < 100 else y
        return _safe_date(y, mo, d)
    m = re.search(r"\b(\d{1,2})([A-Za-z]{3})(\d{2})\b", t)
    if m and m.group(2).lower() in _MONTHS:
        d = int(m.group(1)); mo = _MONTHS[m.group(2).lower()]; y = 2000 + int(m.group(3))
        return _safe_date(y, mo, d)
    m = re.search(r"\b(\d{1,2})/(\d{1,2})\b", t)
    if m:
        mo, d = int(m.group(1)), int(m.group(2))
        return _safe_date(datetime.utcnow().year, mo, d)
    return None


def _safe_date(y, mo, d):
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def _extract_quantity(t: str) -> Optional[int]:
    m = _QTY_RE.search(t) or _QTY_X_RE.search(t)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def _extract_price(t: str):
    m = _CREDIT_RE.search(t)
    if m:
        return float(m.group(1)), PriceType.CREDIT
    m = _DEBIT_RE.search(t)
    if m:
        return float(m.group(1)), PriceType.DEBIT
    m = _AT_PRICE_RE.search(t)
    if m:
        return float(m.group(1)), None
    return None, None


def _mask_noise(t: str) -> str:
    """Blank out substrings that would otherwise be misread as strikes:
    dates, quantities, DTE counts, and explicit credit/debit amounts."""
    masked = t
    month_alt = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
    patterns = [
        r"\b20\d{2}-\d{1,2}-\d{1,2}\b",
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
        r"\b\d{1,2}/\d{1,2}\b",
        r"\b\d{1,2}(?:" + month_alt + r")\d{2}\b",
        r"\b(?:" + month_alt + r")\s*\d{1,2}(?:,?\s*\d{2,4})?\b",
        r"(?:credit|cr|debit|db|paid|@)\s*\$?\s*\d+(?:\.\d+)?",
        r"\bfor\s+\$?\s*\d+(?:\.\d+)?\s*(?:credit|debit|cr|db)",
        r"\b\d{1,3}\s*(?:x|contracts?|lots?|qty|dte)\b",
        r"\bx\s*\d{1,3}\b",
    ]
    for p in patterns:
        masked = re.sub(p, lambda m: " " * len(m.group(0)), masked, flags=re.I)
    return masked


def _extract_legs(t: str) -> List[ParsedLeg]:
    legs: List[ParsedLeg] = []
    consumed_spans = []
    masked = _mask_noise(t)  # leg detection runs on the masked text

    # Spread pairs like "4500/4490 put" or "540/545 call" → two legs
    for pair in _SPREAD_PAIR_RE.finditer(masked):
        a, b = float(pair.group(1)), float(pair.group(2))
        tail = masked[pair.end(): pair.end() + 10].lower()
        head = masked[max(0, pair.start() - 12): pair.start()].lower()
        ctx = head + " " + tail
        if "call" in ctx or re.search(r"\bc\b", tail):
            right = OptionRight.CALL
        elif "put" in ctx or re.search(r"\bp\b", tail):
            right = OptionRight.PUT
        else:
            right = None
        legs.append(ParsedLeg(side=None, right=right, strike=a))
        legs.append(ParsedLeg(side=None, right=right, strike=b))
        consumed_spans.append((pair.start(), pair.end()))

    def _in_consumed(pos):
        return any(s <= pos < e for s, e in consumed_spans)

    # Standalone strikes like "230C" / "4500P", skipping any already in a pair
    for m in _STRIKE_PUT_RE.finditer(masked):
        if not _in_consumed(m.start()):
            legs.append(ParsedLeg(right=OptionRight.PUT, strike=float(m.group(1))))
    for m in _STRIKE_CALL_RE.finditer(masked):
        if not _in_consumed(m.start()):
            legs.append(ParsedLeg(right=OptionRight.CALL, strike=float(m.group(1))))

    # If pair legs have no right but text says "put"/"call" spread, fill it
    if legs and any(l.right is None for l in legs):
        low = t.lower()
        fill = OptionRight.PUT if "put" in low else (
            OptionRight.CALL if "call" in low else None)
        if fill:
            for l in legs:
                if l.right is None:
                    l.right = fill

    # Deduplicate by (right, strike) — same leg can appear in both caption and image text
    seen: set = set()
    unique: List[ParsedLeg] = []
    for leg in legs:
        key = (leg.right, leg.strike)
        if key not in seen:
            seen.add(key)
            unique.append(leg)
    legs = unique

    _assign_vertical_sides(t, legs)
    return legs


def _assign_vertical_sides(t: str, legs: List[ParsedLeg]):
    low = t.lower()
    puts = [l for l in legs if l.right == OptionRight.PUT]
    calls = [l for l in legs if l.right == OptionRight.CALL]
    if len(puts) == 2 and not calls:
        puts.sort(key=lambda l: l.strike or 0)
        # bull put spread → sell higher, buy lower
        puts[0].side = LegSide.BUY
        puts[1].side = LegSide.SELL
    if len(calls) == 2 and not puts:
        calls.sort(key=lambda l: l.strike or 0)
        # bear call spread → sell lower, buy higher
        calls[0].side = LegSide.SELL
        calls[1].side = LegSide.BUY
    if len(puts) == 2 and len(calls) == 2:
        puts.sort(key=lambda l: l.strike or 0)
        calls.sort(key=lambda l: l.strike or 0)
        puts[0].side, puts[1].side = LegSide.BUY, LegSide.SELL
        calls[0].side, calls[1].side = LegSide.SELL, LegSide.BUY
    # Single explicit BTO/STO override
    if "bto" in low or "buy to open" in low:
        for l in legs:
            if l.side is None:
                l.side = LegSide.BUY
    if "sto" in low or "sell to open" in low:
        for l in legs:
            if l.side is None:
                l.side = LegSide.SELL


def _score_confidence(r: ParsedAlertResult) -> float:
    score = 0.0
    if r.event != AlertEvent.UNKNOWN:
        score += 0.2
    if r.ticker:
        score += 0.2
    if r.strategy != StrategyType.UNKNOWN:
        score += 0.2
    if r.legs:
        score += 0.2
    if r.price is not None:
        score += 0.1
    if r.expiration:
        score += 0.1
    return min(score, 1.0)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def parse_alert(text: str) -> ParsedAlertResult:
    text = (text or "").strip()
    r = ParsedAlertResult(source_text=text)
    if not text:
        r.notes = "empty message"
        return r

    r.event = _detect_event(text)
    r.ticker = _extract_ticker(text)
    r.expiration = _extract_expiration(text)
    r.quantity = _extract_quantity(text)
    r.price, r.price_type = _extract_price(text)
    r.legs = _extract_legs(text)
    r.strategy = _detect_strategy(text, r.legs)

    # default price_type by strategy when only "@" price found
    if r.price is not None and r.price_type is None:
        if r.strategy in (StrategyType.BULL_PUT_SPREAD, StrategyType.BEAR_CALL_SPREAD,
                          StrategyType.IRON_CONDOR, StrategyType.IRON_FLY):
            r.price_type = PriceType.CREDIT
        elif r.strategy == StrategyType.BUTTERFLY:
            r.price_type = PriceType.DEBIT

    r.confidence = _score_confidence(r)
    if not r.is_complete:
        missing = []
        if not r.ticker:
            missing.append("ticker")
        if r.strategy == StrategyType.UNKNOWN:
            missing.append("strategy")
        if r.event == AlertEvent.ENTRY and len(r.legs) < 2 and r.strategy != StrategyType.SINGLE_LEG:
            missing.append("legs")
        if r.price is None:
            missing.append("price")
        r.notes = "missing: " + ", ".join(missing) if missing else "incomplete"
    return r
