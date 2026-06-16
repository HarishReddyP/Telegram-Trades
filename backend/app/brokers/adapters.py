"""Broker adapter pattern.

`BrokerAdapter` defines the interface. `PaperBroker` simulates fills locally and
is the default. `LiveBrokerAdapter` is a deliberately inert stub: it raises until
a real integration (IBKR / Tradier / Tastytrade / Alpaca) is implemented AND the
LIVE_TRADING_ENABLED gate is set. This prevents accidental real-money orders.
"""
from __future__ import annotations

import abc
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from app.core.config import settings
from app.core.enums import OrderAction, OrderStatus, PriceType, StrategyType


@dataclass
class OrderRequest:
    trade_id: int
    action: OrderAction
    strategy: StrategyType
    quantity: int
    limit_price: Optional[float]
    price_type: Optional[PriceType]
    legs: List[dict]
    underlying: Optional[str] = None
    expiration: Optional[object] = None  # datetime.date


@dataclass
class OrderResult:
    broker_order_id: str
    status: OrderStatus
    fill_price: Optional[float]
    filled_at: Optional[datetime]
    raw: dict


class BrokerAdapter(abc.ABC):
    name = "base"

    @abc.abstractmethod
    def submit(self, req: OrderRequest) -> OrderResult: ...

    @abc.abstractmethod
    def cancel(self, broker_order_id: str) -> bool: ...

    @abc.abstractmethod
    def mark_price(self, legs: List[dict]) -> Optional[float]: ...


class PaperBroker(BrokerAdapter):
    """Simulated broker. When a live quote provider is configured it prices the
    fill from the current market (mid or conservative per FILL_PRICE_MODE);
    otherwise it falls back to the requested limit price so the system still
    runs with no market-data connection."""

    name = "paper"

    def submit(self, req: OrderRequest) -> OrderResult:
        oid = f"paper-{uuid.uuid4().hex[:12]}"
        live = self._live_fill(req)
        fill = live if live is not None else req.limit_price
        return OrderResult(
            broker_order_id=oid,
            status=OrderStatus.FILLED,
            fill_price=fill,
            filled_at=datetime.utcnow(),
            raw={"simulated": True, "limit_price": req.limit_price,
                 "live_fill": live, "priced_from": "live" if live is not None else "limit"},
        )

    def _live_fill(self, req: OrderRequest) -> Optional[float]:
        from app.services.quotes import spread_mark, TradierClient
        client = TradierClient()
        if not client.enabled or not req.price_type or not req.underlying:
            return None
        return spread_mark(
            underlying=req.underlying,
            expiration=req.expiration,
            legs=req.legs,
            price_type=req.price_type,
            client=client,
        )

    def cancel(self, broker_order_id: str) -> bool:
        return True

    def mark_price(self, legs: List[dict]) -> Optional[float]:
        return None


class LiveBrokerAdapter(BrokerAdapter):
    """Stub for a real broker. Fill in the API calls for your broker of choice,
    then set LIVE_TRADING_ENABLED=true and TRADING_MODE=live to arm it."""

    name = "live"

    def __init__(self, broker: str = "tradier"):
        self.broker = broker

    def _guard(self):
        if not (settings.LIVE_TRADING_ENABLED and settings.TRADING_MODE == "live"):
            raise RuntimeError(
                "Live trading is disabled. Implement the broker integration and set "
                "LIVE_TRADING_ENABLED=true with TRADING_MODE=live to enable real orders."
            )

    def submit(self, req: OrderRequest) -> OrderResult:
        self._guard()
        # TODO: translate req.legs into the broker's multi-leg order schema,
        # POST to the broker, poll for fill, and map the response back.
        raise NotImplementedError("Implement live order submission for " + self.broker)

    def cancel(self, broker_order_id: str) -> bool:
        self._guard()
        raise NotImplementedError("Implement live cancel for " + self.broker)

    def mark_price(self, legs: List[dict]) -> Optional[float]:
        # TODO: query the broker/quote feed for the current spread mark.
        return None


def get_broker() -> BrokerAdapter:
    if settings.TRADING_MODE == "live" and settings.LIVE_TRADING_ENABLED:
        return LiveBrokerAdapter()
    return PaperBroker()
