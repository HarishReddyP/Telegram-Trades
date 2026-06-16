# Telegram Trade Alert Tracking & Execution System

A production-ready MVP that reads options trade alerts from a Telegram channel you are
**legally a member of**, parses them, applies risk controls, simulates fills in **paper-trading
mode**, tracks P&L, surfaces everything on a web dashboard, and emails daily performance.

> **Safety first.** The system ships in **paper-trading mode** with **manual approval enabled**.
> Live broker execution is disabled until you explicitly implement and enable a broker adapter,
> wire up credentials, and flip the relevant flags. Nothing trades real money out of the box.

---

## What it does

1. **Telegram Alert Scanner** — Telethon client listens to a single channel/group you already
   belong to, stores raw messages, and hands them to the parser.
2. **Alert Parser** — Regex + heuristic engine that recognizes bull put / bear call spreads,
   iron flies, iron condors, butterflies, single legs, and entry / exit / stop / adjustment
   events. Extracts ticker, expiry, strikes, side, legs, credit/debit, qty, prices, timestamp.
3. **Trade Decision Engine** — Normalizes alerts into structured trades, flags incomplete ones
   as `NEEDS_REVIEW`, and requires manual approval before any (paper or live) order.
4. **Risk Engine** — Enforces max risk/trade, max contracts, max daily loss, max open trades,
   allowed tickers/strategies, and a no-trade-near-close window.
5. **Broker layer** — Adapter pattern. `PaperBroker` is the default. `LiveBrokerAdapter` is a
   stub you fill in for IBKR / Tradier / Tastytrade / Alpaca. Kill switch + duplicate detection.
6. **P&L Engine** — Per-contract, per-trade, realized/unrealized, daily ending balance.
7. **Dashboard** — React + TS + Tailwind + Recharts. Overview, Open Positions, Closed Trades,
   Daily P&L, Strategy Analytics, Telegram Alerts Log, Settings, Risk Controls.
8. **Email Reports** — On entry, on exit, and an end-of-day summary (scheduled).
9. **Audit trail** — Every message, parsed alert, decision, order, and P&L update is logged.

## Architecture

```
Telegram ─► Listener ─► raw message ─► Parser ─► Normalizer ─► Risk Engine ─► (manual approve)
                                                                                   │
                                          PaperBroker / LiveBrokerAdapter ◄────────┘
                                                       │
                                            Orders / Positions ─► P&L Engine ─► Snapshots
                                                       │
                                  Dashboard API ◄──────┴──────► Email Service / EOD Scheduler
```

Services live under `backend/app/services`. The FastAPI app exposes the dashboard API; a Celery
worker + beat handle the Telegram listener loop, periodic mark-to-market, and the EOD report.

## Quick start (Docker)

```bash
cp backend/.env.example backend/.env      # fill in values (see below)
docker compose up --build
```

- API:        http://localhost:8000  (docs at /docs)
- Dashboard:  http://localhost:5173
- Default mode: **paper**, manual approval **on**.

## Quick start (local, no Docker)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                      # edit
alembic upgrade head        # or: python -m app.db.init_db
uvicorn app.main:app --reload

# Worker (separate shell)
celery -A app.workers.celery_app worker -B --loglevel=info

# Frontend
cd ../frontend
npm install
npm run dev
```

## Live option quotes (execution price + open-position marks)

By default the system runs in pure simulation (`QUOTE_PROVIDER=none`): paper fills
use the alert's stated price and open-position unrealized P&L stays flat at entry.

To price fills and marks from the **live market**, enable Tradier market data
(read-only — this never places real orders):

```
QUOTE_PROVIDER=tradier
TRADIER_TOKEN=your_tradier_token
TRADIER_BASE_URL=https://sandbox.tradier.com   # or https://api.tradier.com
FILL_PRICE_MODE=mid                            # mid | conservative
```

With it enabled:

- **On execution (open):** the paper broker fetches live quotes for each leg and
  fills the spread at the current net price (`mid`, or `conservative` = sell legs
  at bid, buy legs at ask). Falls back to the alert price if quotes are missing.
- **On exit (close):** same — the close fills at the live net price, and realized
  P&L is computed from that. If no quote is available it uses the alert's exit price.
- **Open positions:** unrealized P&L is marked from live quotes. Marks refresh
  on-demand when the **Open Positions** or **Overview** page loads (and via the
  "Refresh live marks" button), plus on the existing 5-minute Celery loop.

Spread net price = Σ over legs of (sell legs **+** their price, buy legs **−** their
price). For a credit spread, a falling mark means it's cheaper to buy back →
unrealized profit rises.

## Configuration (`backend/.env`)

| Var | Meaning |
|---|---|
| `DATABASE_URL` | Postgres DSN, e.g. `postgresql+psycopg://user:pass@db:5432/trades` |
| `REDIS_URL` | Redis DSN for Celery, e.g. `redis://redis:6379/0` |
| `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` | From https://my.telegram.org |
| `TELEGRAM_SESSION` | Telethon session string (generate once, see below) |
| `TELEGRAM_CHANNEL` | The @handle or numeric id of the channel you belong to |
| `TRADING_MODE` | `paper` (default) or `live` |
| `MANUAL_APPROVAL` | `true` (default) |
| `LIVE_TRADING_ENABLED` | `false` (default) — hard gate for real orders |
| `SMTP_*` | Mail server settings for reports |
| `JWT_SECRET` | Auth signing key |

### Generate a Telegram session string

```bash
cd backend && python -m app.services.telegram_session
```

Follow the prompts (phone + code). Paste the printed string into `TELEGRAM_SESSION`.

## Legal & compliance notes

- Only connect to channels/groups **you are a legitimate, paying member of** and whose terms
  permit programmatic access. You are responsible for compliance with the channel's rules,
  Telegram's ToS, your broker's automated-trading policies, and applicable securities law.
- Copying another person's trade alerts may carry redistribution restrictions — keep outputs
  private to your own account.
- Live execution requires real broker credentials, options approval, and your own risk
  controls and compliance review before enabling. The `LiveBrokerAdapter` intentionally
  refuses to send orders until implemented.

## Project layout

See `STRUCTURE.md` for the full tree and a per-file description.

## Tests

```bash
cd backend && pytest
```

Parser unit tests cover each strategy and event type with example alerts (see
`backend/tests/test_parser.py` and `docs/example_alerts.md`).
