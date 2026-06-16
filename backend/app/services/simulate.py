"""Paper-trading simulation.

Feeds a sequence of example alerts through the full pipeline (ingest → parse →
normalize → risk → approve → paper fill → P&L), then prints the resulting
account summary and an EOD report. Safe to run repeatedly against a throwaway DB.

Usage:
    python -m app.services.simulate
"""
from __future__ import annotations

import time

from app.db.session import SessionLocal
from app.db.init_db import init_db
from app.services import trade_service, analytics
from app.services.eod_report import build_and_store_eod
from app.core.enums import TradeStatus, AlertEvent

EXAMPLE_ALERTS = [
    "SPX selling 5x 5400/5390 put credit spread @ 1.20 credit exp 2026-06-19",
    "QQQ Iron Condor 470/465 put 500/505 call credit 2.10 06/19/2026 x2",
    "SPY Bear Call Spread 540/545 for 0.80 credit 06/20/2026 x3",
    "IWM Iron Fly 200p/195p 200c/205c credit 3.40 06/19/2026",
]
# Exit prices to simulate later (buy-to-close debits)
EXIT_ALERTS = [
    "Exit SPX put spread @ 0.40 took profit",
    "Close QQQ iron condor @ 0.90 trim",
]


def _approve_all_pending(db):
    pending = db.query(trade_service.Trade).filter(
        trade_service.Trade.status == TradeStatus.PENDING_APPROVAL).all()
    for t in pending:
        try:
            trade_service.approve_trade(db, t.id, actor="simulator")
            print(f"  approved & filled: #{t.id} {t.ticker} {t.strategy.value}")
        except ValueError as e:
            print(f"  blocked: #{t.id} {t.ticker} -> {e}")


def run():
    init_db()
    db = SessionLocal()
    try:
        print("== Injecting entry alerts ==")
        for text in EXAMPLE_ALERTS:
            msg = trade_service.ingest_message(
                db, channel="SIMULATION",
                tg_message_id=int(time.time() * 1000) % 2_000_000_000,
                sender="sim", text=text, raw={"sim": True})
            t = trade_service.process_message(db, msg)
            if t:
                print(f"  parsed -> #{t.id} {t.ticker} {t.strategy.value} "
                      f"status={t.status.value} risk=${t.max_risk}")
            time.sleep(0.01)

        print("\n== Approving entries (manual approval gate) ==")
        _approve_all_pending(db)

        print("\n== Injecting exit alerts ==")
        for text in EXIT_ALERTS:
            msg = trade_service.ingest_message(
                db, channel="SIMULATION",
                tg_message_id=int(time.time() * 1000) % 2_000_000_000 + 7,
                sender="sim", text=text, raw={"sim": True})
            trade_service.process_message(db, msg)
            time.sleep(0.01)

        print("\n== Approving exits ==")
        _approve_all_pending(db)

        print("\n== Account summary ==")
        s = analytics.account_summary(db)
        for k, v in s.items():
            print(f"  {k:18}: {v}")

        print("\n== EOD report ==")
        payload = build_and_store_eod(db)
        for k, v in payload.items():
            print(f"  {k:18}: {v}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
