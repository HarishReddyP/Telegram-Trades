"""Celery app, beat schedule, and background tasks:
  - telegram_listener_loop: keeps the Telethon client running
  - mark_to_market: refreshes unrealized P&L periodically
  - end_of_day_report: builds and emails the EOD summary
"""
from __future__ import annotations

import logging
from datetime import datetime

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings
from app.db.session import SessionLocal

log = logging.getLogger("workers")

celery_app = Celery("trade_system", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.MARKET_TZ,
    enable_utc=False,
)

# Beat schedule
hh, mm = (int(x) for x in settings.MARKET_CLOSE.split(":"))
celery_app.conf.beat_schedule = {
    "mark-to-market-every-5min": {
        "task": "app.workers.celery_app.mark_to_market_task",
        "schedule": 300.0,
    },
    "eod-report": {
        "task": "app.workers.celery_app.end_of_day_report_task",
        # Run 5 minutes after close on weekdays
        "schedule": crontab(hour=hh, minute=(mm + 5) % 60, day_of_week="1-5"),
    },
}


@celery_app.task
def mark_to_market_task():
    from app.services.trade_service import mark_to_market
    db = SessionLocal()
    try:
        mark_to_market(db)  # no live quote feed in paper mode → flat marks
        log.info("mark-to-market done at %s", datetime.utcnow())
    finally:
        db.close()


@celery_app.task
def end_of_day_report_task():
    from app.services.eod_report import build_and_store_eod
    from app.services.email_service import send_eod_report
    db = SessionLocal()
    try:
        payload = build_and_store_eod(db)
        send_eod_report(db, payload)
        log.info("EOD report sent: %s", payload)
        return payload
    finally:
        db.close()


@celery_app.task
def telegram_listener_task():
    """Long-running listener. Start with a dedicated worker:
        celery -A app.workers.celery_app worker -Q telegram --concurrency=1
    or simply run app.services.telegram_listener directly."""
    from app.services.telegram_listener import run_listener
    run_listener()
