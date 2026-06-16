"""Tradier market-data client for live option quotes.

Used by both the paper broker (to price fills) and the mark-to-market loop (to
value open spreads). Only the market-data endpoints are touched here — this is
read-only and does NOT place orders.

Tradier API docs: https://documentation.tradier.com/brokerage-api/markets/get-quotes

Config (.env):
    TRADIER_TOKEN       Bearer token (sandbox or production)
    TRADIER_BASE_URL    https://sandbox.tradier.com  or  https://api.tradier.com
    QUOTE_PROVIDER      'tradier' to enable; 'none' (default) keeps pure simulation
    FILL_PRICE_MODE     mid | conservative   (how a paper fill is priced)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.enums import OptionRight, LegSide, PriceType

log = logging.getLogger("quotes")


@dataclass
class Quote:
    symbol: str
    bid: Optional[float]
    ask: Optional[float]
    last: Optional[float]

    @property
    def mid(self) -> Optional[float]:
        if self.bid is not None and self.ask is not None and (self.bid or self.ask):
            return round((self.bid + self.ask) / 2, 4)
        return self.last


def occ_symbol(underlying: str, expiration: date, right: OptionRight, strike: float) -> str:
    """Build an OCC option symbol, e.g. SPXW...  -> 'SPY260619C00540000'.
    Format: ROOT + YYMMDD + C/P + strike*1000 zero-padded to 8 digits.
    """
    ymd = expiration.strftime("%y%m%d")
    cp = "C" if right == OptionRight.CALL else "P"
    strike_int = int(round(strike * 1000))
    return f"{underlying.upper()}{ymd}{cp}{strike_int:08d}"


class TradierClient:
    def __init__(self, token: str = None, base_url: str = None, timeout: float = 10.0):
        self.token = token or settings.TRADIER_TOKEN
        self.base_url = (base_url or settings.TRADIER_BASE_URL).rstrip("/")
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.token and settings.QUOTE_PROVIDER.lower() == "tradier")

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}

    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Fetch quotes for a list of OCC option symbols. Returns {symbol: Quote}."""
        if not symbols:
            return {}
        if not self.enabled:
            log.debug("Tradier disabled; no live quotes")
            return {}
        url = f"{self.base_url}/v1/markets/quotes"
        params = {"symbols": ",".join(symbols), "greeks": "false"}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, params=params, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:  # noqa: BLE001
            log.warning("Tradier quote fetch failed: %s", e)
            return {}

        out: Dict[str, Quote] = {}
        quotes = (data or {}).get("quotes", {})
        if not quotes or quotes == "null":
            return {}
        rows = quotes.get("quote", [])
        if isinstance(rows, dict):  # single result comes back un-listed
            rows = [rows]
        for q in rows:
            sym = q.get("symbol")
            if not sym:
                continue
            out[sym] = Quote(
                symbol=sym,
                bid=_f(q.get("bid")),
                ask=_f(q.get("ask")),
                last=_f(q.get("last")),
            )
        return out


def _f(v) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _leg_symbols(underlying: str, expiration: date, legs: List[dict]) -> List[Optional[str]]:
    syms = []
    for l in legs:
        right = l.get("right")
        strike = l.get("strike")
        if right and strike is not None and expiration:
            syms.append(occ_symbol(underlying, expiration, OptionRight(right), strike))
        else:
            syms.append(None)
    return syms


def spread_mark(
    *,
    underlying: str,
    expiration: Optional[date],
    legs: List[dict],
    price_type: PriceType,
    mode: str = None,
    client: TradierClient = None,
) -> Optional[float]:
    """Compute the net price of a multi-leg spread from live quotes.

    The net is sum over legs of (sign * leg_price), where SELL legs contribute
    positively to a credit and BUY legs negatively. The returned value is the
    absolute net the position is worth right now, expressed in the same
    credit/debit convention as the entry.

    mode: 'mid' (default) or 'conservative'. Conservative prices the spread
    against you — sells at bid, buys at ask — to avoid optimistic marks/fills.
    """
    client = client or TradierClient()
    mode = (mode or settings.FILL_PRICE_MODE or "mid").lower()
    if not (client.enabled and expiration and legs):
        return None

    symbols = _leg_symbols(underlying, expiration, legs)
    valid = [s for s in symbols if s]
    if len(valid) != len(legs):
        return None  # incomplete legs → can't price reliably

    quotes = client.get_quotes(valid)
    if len(quotes) < len(valid):
        return None

    net = 0.0
    for l, sym in zip(legs, symbols):
        q = quotes.get(sym)
        if not q:
            return None
        side = l.get("side")
        # choose per-leg price depending on mode and direction
        if mode == "conservative":
            if side == LegSide.SELL.value:
                price = q.bid if q.bid is not None else q.mid
            else:  # BUY
                price = q.ask if q.ask is not None else q.mid
        else:  # mid
            price = q.mid
        if price is None:
            return None
        sign = 1.0 if side == LegSide.SELL.value else -1.0
        net += sign * price

    # net > 0 means the spread is a net credit to hold; report absolute value
    return round(abs(net), 4)
