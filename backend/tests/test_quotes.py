"""Tests for OCC symbol construction and spread-mark netting.

These use an injected fake client so no network or live token is needed.
"""
from datetime import date

from app.services.quotes import occ_symbol, spread_mark, Quote, TradierClient
from app.core.enums import OptionRight, PriceType


def test_occ_symbol_call():
    assert occ_symbol("SPY", date(2026, 6, 19), OptionRight.CALL, 540) == "SPY260619C00540000"


def test_occ_symbol_put_large_strike():
    assert occ_symbol("SPX", date(2026, 6, 19), OptionRight.PUT, 5390) == "SPX260619P05390000"


class _FakeClient(TradierClient):
    enabled = True

    def __init__(self, quotes):
        self._q = quotes

    def get_quotes(self, symbols):
        return {s: self._q[s] for s in symbols if s in self._q}


def _spread_quotes():
    exp = date(2026, 6, 19)
    s_sell = occ_symbol("SPX", exp, OptionRight.PUT, 5400)
    s_buy = occ_symbol("SPX", exp, OptionRight.PUT, 5390)
    return exp, {
        s_sell: Quote(s_sell, 1.45, 1.55, 1.50),
        s_buy: Quote(s_buy, 0.25, 0.35, 0.30),
    }


def test_spread_mark_mid():
    exp, q = _spread_quotes()
    legs = [{"side": "SELL", "right": "PUT", "strike": 5400},
            {"side": "BUY", "right": "PUT", "strike": 5390}]
    mark = spread_mark(underlying="SPX", expiration=exp, legs=legs,
                       price_type=PriceType.CREDIT, mode="mid", client=_FakeClient(q))
    assert mark == 1.20


def test_spread_mark_conservative():
    exp, q = _spread_quotes()
    legs = [{"side": "SELL", "right": "PUT", "strike": 5400},
            {"side": "BUY", "right": "PUT", "strike": 5390}]
    mark = spread_mark(underlying="SPX", expiration=exp, legs=legs,
                       price_type=PriceType.CREDIT, mode="conservative", client=_FakeClient(q))
    assert mark == 1.10  # sell at bid 1.45, buy at ask 0.35


def test_spread_mark_missing_quote_returns_none():
    exp, q = _spread_quotes()
    legs = [{"side": "SELL", "right": "PUT", "strike": 5400},
            {"side": "BUY", "right": "PUT", "strike": 9999}]  # no quote for this leg
    mark = spread_mark(underlying="SPX", expiration=exp, legs=legs,
                       price_type=PriceType.CREDIT, client=_FakeClient(q))
    assert mark is None
