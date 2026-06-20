from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.trade_service import _hit_profit_target, _is_near_market_close


def test_hit_profit_target_at_threshold():
    assert _hit_profit_target(unrealized_pnl=250.0, max_risk=500.0) is True


def test_hit_profit_target_below_threshold():
    assert _hit_profit_target(unrealized_pnl=249.99, max_risk=500.0) is False


def test_hit_profit_target_no_max_risk():
    assert _hit_profit_target(unrealized_pnl=250.0, max_risk=None) is False


def test_hit_profit_target_no_unrealized_pnl():
    assert _hit_profit_target(unrealized_pnl=None, max_risk=500.0) is False


def test_near_market_close_within_window():
    now = datetime(2026, 6, 22, 15, 56, tzinfo=ZoneInfo("America/New_York"))
    assert _is_near_market_close(now) is True


def test_near_market_close_outside_window():
    now = datetime(2026, 6, 22, 15, 30, tzinfo=ZoneInfo("America/New_York"))
    assert _is_near_market_close(now) is False


def test_near_market_close_after_close():
    now = datetime(2026, 6, 22, 16, 1, tzinfo=ZoneInfo("America/New_York"))
    assert _is_near_market_close(now) is False


def test_near_market_close_at_close():
    now = datetime(2026, 6, 22, 16, 0, tzinfo=ZoneInfo("America/New_York"))
    assert _is_near_market_close(now) is True
