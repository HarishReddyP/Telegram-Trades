"""Telegram listener.

Connects with a Telethon StringSession to a single channel/group the user is
already a member of, and forwards new messages into the ingestion pipeline.

LEGAL: only configure a channel you are legitimately a member of and permitted
to read programmatically. See README "Legal & compliance notes".
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.enums import TradeStatus
from app.db.session import SessionLocal
from app.services.trade_service import ingest_message, process_message, is_duplicate, approve_trade, mark_to_market
from app.services.analytics import snapshot_account
from app.services.image_parser import extract_text_from_image

log = logging.getLogger("telegram_listener")

# Only the 2 PM CST alert is scanned — everything else (off-hours, weekends,
# other alert types) is ignored entirely. Matching is on "2pm"/"2 pm" mention
# alone; the word "challenge" is not required.
ALERT_WINDOW_TZ = ZoneInfo("America/Chicago")
ALERT_WINDOW_START_HOUR = 14  # 2 PM CST/CDT
ALERT_WINDOW_END_HOUR = 15    # 3 PM CST/CDT
_CHALLENGE_TIME_RE = re.compile(r"2\s*pm", re.IGNORECASE)


def _within_alert_window(now: datetime) -> bool:
    if now.weekday() > 4:  # Mon=0 ... Fri=4; Sat/Sun excluded
        return False
    return ALERT_WINDOW_START_HOUR <= now.hour < ALERT_WINDOW_END_HOUR


def _is_challenge_trade_alert(text: str) -> bool:
    if not text:
        return False
    return bool(_CHALLENGE_TIME_RE.search(text))


async def _run():
    from telethon import TelegramClient, events
    from telethon.sessions import StringSession

    if not settings.TELEGRAM_SESSION:
        log.warning("TELEGRAM_SESSION empty — listener idle. Generate one first.")
        while True:
            await asyncio.sleep(3600)

    client = TelegramClient(
        StringSession(settings.TELEGRAM_SESSION),
        settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH,
    )

    # Telethon needs an int for numeric IDs; string form silently fails to match
    ch = settings.TELEGRAM_CHANNEL
    channel_filter = int(ch) if ch.lstrip("-").isdigit() else ch

    # Debug: log every incoming message so we can see the actual chat_id
    @client.on(events.NewMessage())
    async def debug_all(event):
        chat_id = event.chat_id
        has_photo = bool(event.message.photo)
        has_doc = bool(event.message.document)
        has_media = bool(event.message.media)
        log.info("[DEBUG] chat_id=%s photo=%s doc=%s media=%s text_len=%s (filter=%s match=%s)",
                 chat_id, has_photo, has_doc, has_media,
                 len(event.message.message or ""), channel_filter, chat_id == channel_filter)

    @client.on(events.NewMessage(chats=channel_filter))
    async def handler(event):
        now = datetime.now(ALERT_WINDOW_TZ)
        if not _within_alert_window(now):
            return

        text = event.message.message or ""
        channel = settings.TELEGRAM_CHANNEL

        # If the message contains an image (photo or image sent as document), extract trade text
        media_type = None
        if event.message.photo:
            media_type = "image/jpeg"
        elif event.message.document:
            mime = getattr(event.message.document, "mime_type", "") or ""
            if mime.startswith("image/"):
                media_type = mime

        if media_type:
            try:
                image_bytes = await client.download_media(event.message, file=bytes)
                extracted = await extract_text_from_image(image_bytes, media_type=media_type)
                if extracted:
                    text = (text + "\n" + extracted).strip() if text else extracted
                    log.info("image alert extracted (%d chars)", len(extracted))
            except Exception as e:  # noqa: BLE001
                log.error("image extraction failed: %s", e)

        if not text:
            log.info("message has no parseable text, skipping")
            return

        if not _is_challenge_trade_alert(text):
            log.info("message is not a 2pm challenge trade alert, ignoring. text=%r", text[:300])
            return

        log.info("2pm challenge trade alert matched, processing. text=%r", text[:300])
        db = SessionLocal()
        try:
            if is_duplicate(db, channel, text):
                log.info("duplicate alert ignored")
                return
            sender = str(getattr(event.message, "sender_id", "") or "")
            msg = ingest_message(
                db, channel=channel, tg_message_id=event.message.id,
                sender=sender, text=text,
                raw={"date": str(event.message.date), "has_image": bool(event.message.photo)},
            )
            trade = process_message(db, msg)
            if trade:
                log.info("trade created id=%s ticker=%s strategy=%s status=%s",
                         trade.id, trade.ticker, trade.strategy, trade.status)
                # Auto-execute in paper mode — force to PENDING_APPROVAL then approve
                if settings.TRADING_MODE == "paper" and not settings.MANUAL_APPROVAL:
                    try:
                        if trade.status == TradeStatus.NEEDS_REVIEW:
                            trade.status = TradeStatus.PENDING_APPROVAL
                            db.commit()
                        trade = approve_trade(db, trade.id, actor="auto")
                        log.info("auto-executed trade id=%s fill=%.2f status=%s",
                                 trade.id, trade.entry_price or 0, trade.status)
                        # Update unrealized P&L marks then snapshot account value
                        mark_to_market(db)
                        snap = snapshot_account(db)
                        log.info("account snapshot: value=%.2f realized=%.2f unrealized=%.2f open_trades=%s",
                                 snap.account_value, snap.realized_pnl, snap.unrealized_pnl, snap.open_trades)
                    except Exception as e:  # noqa: BLE001
                        log.error("auto-execute failed for trade %s: %s", trade.id, e)
            else:
                log.info("message parsed but no trade signal found")
        finally:
            db.close()

    asyncio.create_task(_auto_close_loop())

    await client.start()
    # Warm up the entity cache so Telethon delivers updates from all chats
    await client.get_dialogs()
    log.info("Telegram listener started on %s (filter=%s)", settings.TELEGRAM_CHANNEL, channel_filter)
    await client.run_until_disconnected()


async def _auto_close_loop():
    """Runs the 50%-profit / near-market-close auto-close check on its own
    cadence. The Celery beat task does this too, but lives here as well so
    auto-close keeps working even if the worker/Redis stack is down."""
    from app.services.trade_service import auto_manage_open_trades

    while True:
        try:
            db = SessionLocal()
            try:
                closed = auto_manage_open_trades(db)
                if closed:
                    log.info("auto-closed %d trade(s)", len(closed))
            finally:
                db.close()
        except Exception as e:  # noqa: BLE001
            log.error("auto-close loop failed: %s", e)
        await asyncio.sleep(60)


def run_listener():
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_run())


if __name__ == "__main__":
    run_listener()
