"""LLM-based trade alert parser using Claude.

Uses tool use to force structured JSON output — no markdown wrapping issues.
Replaces the regex alert_parser so natural-language and image-extracted
messages are understood the way a human trader would read them.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from typing import Optional

from app.parsers.alert_parser import ParsedAlertResult, ParsedLeg
from app.core.enums import AlertEvent, StrategyType, OptionRight, LegSide, PriceType

log = logging.getLogger(__name__)

_SYSTEM = """You are an expert options trader monitoring a trading group chat.

Read each message and decide: is this an ACTIONABLE trade to execute right now?

TRADE signals → call the extract_trade tool:
- Specific spread alerts with strikes: "Sell SPX 5500P Buy 5480P collect $4"
- Clear entry/exit orders with strikes and prices
- Vertical spreads, iron condors, butterflies, single-leg options
- Broker fill confirmations showing what was executed

NOT trades → call the not_a_trade tool:
- General market commentary: "SPX looks bullish today"
- Vague intentions without strikes or prices: "watching calls here"
- Educational content, results/profit updates, news, links, announcements
- Price targets without specific option legs

Leg construction rules:
- BULL_PUT_SPREAD: SELL higher PUT, BUY lower PUT
- BEAR_CALL_SPREAD: SELL lower CALL, BUY higher CALL
- IRON_CONDOR: SELL put, BUY lower put, SELL call, BUY higher call
- IRON_FLY: same strikes for both short legs
"""

_TOOLS = [
    {
        "name": "extract_trade",
        "description": "Call this when the message contains an actionable trade to execute.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event": {
                    "type": "string",
                    "enum": ["ENTRY", "EXIT", "STOP_LOSS"],
                    "description": "ENTRY for new trades, EXIT for close/take-profit, STOP_LOSS for stops hit"
                },
                "strategy": {
                    "type": "string",
                    "enum": ["BULL_PUT_SPREAD", "BEAR_CALL_SPREAD", "IRON_CONDOR", "IRON_FLY", "BUTTERFLY", "SINGLE_LEG", "UNKNOWN"]
                },
                "ticker": {"type": "string", "description": "Underlying symbol e.g. SPX, SPY, NDX, QQQ"},
                "expiration": {"type": "string", "description": "Option expiration date YYYY-MM-DD, or null"},
                "quantity": {"type": "integer", "description": "Number of contracts, default 1"},
                "price": {"type": "number", "description": "Net credit or debit per spread"},
                "price_type": {"type": "string", "enum": ["CREDIT", "DEBIT"]},
                "legs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "side": {"type": "string", "enum": ["BUY", "SELL"]},
                            "right": {"type": "string", "enum": ["CALL", "PUT"]},
                            "strike": {"type": "number"}
                        },
                        "required": ["side", "right", "strike"]
                    }
                }
            },
            "required": ["event", "strategy", "ticker", "legs"]
        }
    },
    {
        "name": "not_a_trade",
        "description": "Call this when the message is informational and has no actionable trade.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Brief reason why this is not a trade"}
            },
            "required": ["reason"]
        }
    }
]


def parse_alert_llm(text: str) -> ParsedAlertResult:
    """Parse a message using Claude. Returns empty result for non-trades."""
    from app.core.config import settings

    r = ParsedAlertResult(source_text=text)

    if not text or not text.strip():
        r.notes = "empty message"
        return r

    if not settings.ANTHROPIC_API_KEY:
        log.warning("ANTHROPIC_API_KEY not set — cannot use LLM parser")
        r.notes = "no api key"
        return r

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=512,
            system=_SYSTEM,
            tools=_TOOLS,
            messages=[{"role": "user", "content": text}],
        )

        # Find tool use block
        tool_block = next(
            (b for b in response.content if b.type == "tool_use"), None
        )
        if not tool_block:
            log.info("LLM parser: no tool call in response")
            r.notes = "no tool call"
            return r

        if tool_block.name == "not_a_trade":
            reason = tool_block.input.get("reason", "not a trade")
            log.info("LLM: not a trade — %s", reason)
            r.notes = reason
            return r

        data = tool_block.input
        log.info("LLM trade extracted: %s", json.dumps(data))

    except Exception as e:
        log.error("LLM parser error: %s", e)
        r.notes = f"llm error: {e}"
        return r

    # Map tool output → ParsedAlertResult
    try:
        r.event = AlertEvent(data.get("event", "ENTRY"))
    except ValueError:
        r.event = AlertEvent.ENTRY

    try:
        r.strategy = StrategyType(data.get("strategy", "UNKNOWN"))
    except ValueError:
        r.strategy = StrategyType.UNKNOWN

    r.ticker = _normalize_ticker(data.get("ticker"))
    r.quantity = 1  # always 1 contract regardless of what the alert says
    r.price = data.get("price")

    pt = data.get("price_type")
    try:
        r.price_type = PriceType(pt) if pt else None
    except ValueError:
        r.price_type = None

    exp = data.get("expiration")
    if exp:
        try:
            r.expiration = date.fromisoformat(exp)
        except ValueError:
            r.expiration = None

    for leg in data.get("legs", []):
        try:
            r.legs.append(ParsedLeg(
                side=LegSide(leg["side"]) if leg.get("side") else None,
                right=OptionRight(leg["right"]) if leg.get("right") else None,
                strike=float(leg["strike"]) if leg.get("strike") is not None else None,
            ))
        except (ValueError, KeyError):
            continue

    r.confidence = _score(r)
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


_TICKER_MAP = {
    "SPXW": "SPX",   # SPX weekly options → underlying SPX
    "NDXP": "NDX",   # NDX PM-settled weekly
    "RUTW": "RUT",   # RUT weekly
    "SPXPM": "SPX",
}

def _normalize_ticker(ticker: Optional[str]) -> Optional[str]:
    if not ticker:
        return ticker
    return _TICKER_MAP.get(ticker.upper(), ticker.upper())


def _score(r: ParsedAlertResult) -> float:
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
