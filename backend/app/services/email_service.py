"""Email notification service. Sends on entry, exit, and end-of-day.

Uses SMTP. Every send is recorded in email_logs for the audit trail. If SMTP
is not configured, emails are logged as 'skipped' so the system still runs in
paper mode without a mail server.
"""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import EmailLog, Trade
from app.services import analytics


def _send_smtp(to_addr: str, subject: str, html: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_addr
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as s:
        s.starttls()
        if settings.SMTP_USER:
            s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        s.sendmail(settings.SMTP_FROM, [to_addr], msg.as_string())


def _record(db: Session, to_addr, subject, html, kind, status, error=None):
    db.add(EmailLog(to_addr=to_addr, subject=subject,
                    body_preview=html[:500], kind=kind, status=status, error=error))
    db.commit()


def send_email(db: Session, *, to_addr: str, subject: str, html: str, kind: str) -> bool:
    if not (settings.SMTP_HOST and to_addr):
        _record(db, to_addr or "", subject, html, kind, "skipped",
                "SMTP not configured")
        return False
    try:
        _send_smtp(to_addr, subject, html)
        _record(db, to_addr, subject, html, kind, "sent")
        return True
    except Exception as e:  # noqa: BLE001
        _record(db, to_addr, subject, html, kind, "failed", str(e))
        return False


def _summary_block(db: Session) -> str:
    s = analytics.account_summary(db)
    return f"""
    <table cellpadding="6" style="border-collapse:collapse;font-family:Arial">
      <tr><td>Account value</td><td><b>${s['account_value']:,.2f}</b></td></tr>
      <tr><td>Daily P&L</td><td>${s['daily_pnl']:,.2f}</td></tr>
      <tr><td>Total P&L</td><td>${s['total_pnl']:,.2f}</td></tr>
      <tr><td>Open trades</td><td>{s['open_trades']}</td></tr>
      <tr><td>Closed trades</td><td>{s['closed_trades']}</td></tr>
      <tr><td>Win rate</td><td>{s['win_rate']}%</td></tr>
    </table>"""


def notify_entry(db: Session, trade: Trade):
    subject = f"[ENTRY] {trade.ticker} {trade.strategy.value} x{trade.quantity}"
    html = f"""
      <h3>Trade Entry</h3>
      <p>{trade.ticker} — {trade.strategy.value}<br>
      Quantity: {trade.quantity}<br>
      Entry: {trade.entry_price} ({trade.entry_price_type.value if trade.entry_price_type else '-'})<br>
      Max risk: ${trade.max_risk or 0:,.2f}</p>
      {_summary_block(db)}"""
    return send_email(db, to_addr=settings.REPORT_RECIPIENT, subject=subject,
                      html=html, kind="entry")


def notify_exit(db: Session, trade: Trade):
    subject = f"[EXIT] {trade.ticker} {trade.strategy.value} P&L ${trade.realized_pnl:,.2f}"
    html = f"""
      <h3>Trade Exit</h3>
      <p>{trade.ticker} — {trade.strategy.value}<br>
      Quantity: {trade.quantity}<br>
      Entry: {trade.entry_price} → Exit: {trade.exit_price}<br>
      Realized P&L: <b>${trade.realized_pnl:,.2f}</b><br>
      Commissions: ${trade.commissions:,.2f}</p>
      {_summary_block(db)}"""
    return send_email(db, to_addr=settings.REPORT_RECIPIENT, subject=subject,
                      html=html, kind="exit")


def send_eod_report(db: Session, payload: dict):
    subject = f"[EOD] Daily summary — P&L ${payload['daily_pnl']:,.2f}"
    rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in payload.items())
    html = f"""
      <h3>End-of-Day Report</h3>
      <table cellpadding="6" style="border-collapse:collapse;font-family:Arial">{rows}</table>
      {_summary_block(db)}"""
    return send_email(db, to_addr=settings.REPORT_RECIPIENT, subject=subject,
                      html=html, kind="eod")
