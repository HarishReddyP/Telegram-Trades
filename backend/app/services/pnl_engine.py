"""P&L engine.

Options multiplier is 100 per contract. Credit strategies profit when the
spread can be bought back for less than the entry credit; debit strategies
profit when sold for more than entry debit.

  credit P&L per contract = (entry_credit - exit_debit) * 100
  debit  P&L per contract = (exit_value  - entry_debit) * 100
  total  = per_contract * quantity  - commissions
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.enums import PriceType

MULTIPLIER = 100


@dataclass
class PnLResult:
    per_contract: float
    gross: float
    commissions: float
    net: float


def commission_for(quantity: int, legs: int, per_contract: float) -> float:
    """Commission charged per leg per contract, both on open and close."""
    return per_contract * quantity * max(legs, 1) * 2


def trade_pnl(
    *,
    entry_price: float,
    exit_price: float,
    price_type: PriceType,
    quantity: int,
    legs: int = 2,
    commission_per_contract: float = 0.0,
) -> PnLResult:
    if price_type == PriceType.CREDIT:
        per_contract = (entry_price - exit_price) * MULTIPLIER
    else:  # DEBIT
        per_contract = (exit_price - entry_price) * MULTIPLIER
    gross = per_contract * quantity
    commissions = commission_for(quantity, legs, commission_per_contract)
    return PnLResult(
        per_contract=round(per_contract, 2),
        gross=round(gross, 2),
        commissions=round(commissions, 2),
        net=round(gross - commissions, 2),
    )


def unrealized_pnl(
    *,
    entry_price: float,
    mark_price: float,
    price_type: PriceType,
    quantity: int,
) -> float:
    """Mark-to-market for an open spread (commissions excluded until close)."""
    if price_type == PriceType.CREDIT:
        per_contract = (entry_price - mark_price) * MULTIPLIER
    else:
        per_contract = (mark_price - entry_price) * MULTIPLIER
    return round(per_contract * quantity, 2)


def max_risk_for_spread(
    *,
    width: float,
    entry_credit: Optional[float],
    quantity: int,
    price_type: PriceType,
) -> Optional[float]:
    """Defined-risk max loss for a vertical credit spread:
        (width - credit) * 100 * qty.
    For debit spreads the max risk is simply the debit paid.
    """
    if price_type == PriceType.CREDIT and entry_credit is not None:
        return round((width - entry_credit) * MULTIPLIER * quantity, 2)
    if price_type == PriceType.DEBIT and entry_credit is not None:
        return round(entry_credit * MULTIPLIER * quantity, 2)
    return None


def spread_width(legs) -> Optional[float]:
    """Largest absolute strike distance among same-right legs."""
    strikes = [l.get("strike") for l in legs if l.get("strike") is not None]
    if len(strikes) < 2:
        return None
    return abs(max(strikes) - min(strikes))
