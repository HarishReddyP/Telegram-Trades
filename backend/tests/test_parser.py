"""Parser unit tests covering each strategy and event type."""
from app.parsers.alert_parser import parse_alert
from app.core.enums import StrategyType, AlertEvent, PriceType


def test_bull_put_spread():
    r = parse_alert("SPX selling 5x 5400/5390 put credit spread @ 1.20 credit exp 2026-06-19")
    assert r.event == AlertEvent.ENTRY
    assert r.strategy == StrategyType.BULL_PUT_SPREAD
    assert r.ticker == "SPX"
    assert r.quantity == 5
    assert r.price == 1.20
    assert r.price_type == PriceType.CREDIT
    assert len(r.legs) == 2
    assert r.is_complete


def test_bear_call_spread():
    r = parse_alert("$SPY Bear Call Spread 540/545 for 0.80 credit 06/20/2026 x3")
    assert r.strategy == StrategyType.BEAR_CALL_SPREAD
    assert r.ticker == "SPY"
    assert r.quantity == 3
    assert r.price == 0.80
    assert len(r.legs) == 2


def test_iron_condor():
    r = parse_alert("QQQ Iron Condor 470/465 put 500/505 call credit 2.10 06/19/2026 x2")
    assert r.strategy == StrategyType.IRON_CONDOR
    assert r.ticker == "QQQ"
    assert len(r.legs) == 4
    assert r.price == 2.10


def test_iron_fly():
    r = parse_alert("IWM Iron Fly 200p/195p 200c/205c credit 3.40 06/19/2026")
    assert r.strategy == StrategyType.IRON_FLY
    assert len(r.legs) == 4


def test_single_leg():
    r = parse_alert("BTO 1 AAPL 230C 06/20/2026 @ 4.50")
    assert r.strategy == StrategyType.SINGLE_LEG
    assert r.ticker == "AAPL"
    assert len(r.legs) == 1


def test_exit_event():
    r = parse_alert("Exit SPX put spread @ 0.40 took profit")
    assert r.event == AlertEvent.EXIT
    assert r.ticker == "SPX"
    assert r.price == 0.40
    assert r.is_complete


def test_stop_loss_event():
    r = parse_alert("Stopped out TSLA call spread @ 2.10 stop loss")
    assert r.event == AlertEvent.STOP_LOSS
    assert r.ticker == "TSLA"


def test_adjustment_event():
    r = parse_alert("Rolling SPY 5400/5390 put spread to next week adjustment")
    assert r.event == AlertEvent.ADJUSTMENT


def test_incomplete_flags_review():
    r = parse_alert("something happened with the market today")
    assert not r.is_complete
