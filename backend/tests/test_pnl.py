from app.services import pnl_engine
from app.core.enums import PriceType


def test_credit_spread_profit():
    r = pnl_engine.trade_pnl(
        entry_price=1.20, exit_price=0.40, price_type=PriceType.CREDIT,
        quantity=5, legs=2, commission_per_contract=0.65)
    assert r.gross == 400.0          # (1.20-0.40)*100*5
    assert r.commissions == 13.0     # 0.65*5*2*2
    assert r.net == 387.0


def test_credit_spread_loss():
    r = pnl_engine.trade_pnl(
        entry_price=1.00, exit_price=2.50, price_type=PriceType.CREDIT,
        quantity=1, legs=2, commission_per_contract=0.0)
    assert r.gross == -150.0


def test_debit_spread_profit():
    r = pnl_engine.trade_pnl(
        entry_price=2.00, exit_price=3.50, price_type=PriceType.DEBIT,
        quantity=2, legs=2, commission_per_contract=0.0)
    assert r.gross == 300.0


def test_max_risk_credit_spread():
    mr = pnl_engine.max_risk_for_spread(
        width=10, entry_credit=1.20, quantity=5, price_type=PriceType.CREDIT)
    assert mr == 4400.0              # (10-1.20)*100*5


def test_unrealized():
    u = pnl_engine.unrealized_pnl(
        entry_price=1.20, mark_price=0.70, price_type=PriceType.CREDIT, quantity=5)
    assert u == 250.0


def test_spread_width():
    legs = [{"strike": 5400}, {"strike": 5390}]
    assert pnl_engine.spread_width(legs) == 10
