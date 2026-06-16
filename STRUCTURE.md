# Project structure

```
telegram-trade-system/
├── README.md                     Setup & overview
├── STRUCTURE.md                  This file
├── docker-compose.yml            db, redis, api, worker, telegram, frontend
├── docs/
│   └── example_alerts.md         Example alerts + parsed outputs + P&L worked example
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example              Copy to .env and fill in
│   ├── app/
│   │   ├── main.py               FastAPI app, CORS, router registration, startup seed
│   │   ├── core/
│   │   │   ├── config.py         Pydantic settings (env-driven safety gates & risk)
│   │   │   ├── enums.py          Strategy / event / status / side enums
│   │   │   └── security.py       JWT + password hashing (auth optional in MVP)
│   │   ├── db/
│   │   │   ├── session.py        Engine, SessionLocal, Base, get_db
│   │   │   └── init_db.py        Create tables + seed default user & risk rule
│   │   ├── models/
│   │   │   └── models.py         All 13 tables (see Database below)
│   │   ├── schemas/
│   │   │   └── schemas.py        Pydantic request/response models
│   │   ├── parsers/
│   │   │   └── alert_parser.py   Telegram text → structured alert (the core NLP)
│   │   ├── services/
│   │   │   ├── trade_service.py  Orchestration: ingest→parse→normalize→risk→approve→fill
│   │   │   ├── risk_engine.py    Rule enforcement
│   │   │   ├── pnl_engine.py     P&L math (credit/debit, max-risk, unrealized)
│   │   │   ├── analytics.py      Dashboard aggregations (equity, daily, by strategy/ticker)
│   │   │   ├── email_service.py  Entry/exit/EOD emails + email_logs
│   │   │   ├── eod_report.py     Build & persist daily report + snapshot
│   │   │   ├── audit.py          audit_logs helper
│   │   │   ├── telegram_listener.py  Telethon real-time listener
│   │   │   ├── telegram_session.py   One-time session-string generator
│   │   │   └── simulate.py       Paper-trading end-to-end simulation
│   │   ├── brokers/
│   │   │   └── adapters.py       BrokerAdapter + PaperBroker + LiveBrokerAdapter (stub)
│   │   ├── workers/
│   │   │   └── celery_app.py     Celery app, beat schedule, MTM & EOD tasks
│   │   └── api/routes/
│   │       ├── dashboard.py      /api/dashboard/*
│   │       ├── trades.py         /api/trades/* (incl. approve/reject)
│   │       ├── alerts.py         /api/alerts/* (incl. preview/simulate)
│   │       └── settings.py       /api/risk-rules, /api/settings, /api/auth/login
│   └── tests/
│       ├── test_parser.py        9 parser tests (all strategies + events)
│       └── test_pnl.py           6 P&L tests
│
└── frontend/
    ├── Dockerfile, nginx.conf
    ├── package.json, vite.config.ts, tsconfig.json
    ├── tailwind.config.js, postcss.config.js, index.html
    └── src/
        ├── main.tsx, App.tsx     Entry + sidebar routing
        ├── index.css             Tailwind + base theme
        ├── types/index.ts        Shared TS types
        ├── lib/
        │   ├── api.ts            Typed fetch client
        │   └── ui.tsx            Card/Stat/Badge/format helpers
        ├── components/
        │   └── TradeTable.tsx    Reusable open/closed/pending table
        └── pages/
            ├── Overview.tsx          Stats + equity curve + daily P&L
            ├── OpenPositions.tsx     Pending approval + live paper positions
            ├── ClosedTrades.tsx      Realized trades with P&L & hold time
            ├── DailyPnL.tsx          Daily bars + period stats
            ├── StrategyAnalytics.tsx Per-strategy & per-ticker breakdowns
            ├── AlertsLog.tsx         Parsed alert feed + simulator
            ├── Settings.tsx          Safety gates & connection info
            └── RiskControls.tsx      Editable risk rules
```

## Database tables

| Table | Purpose |
|---|---|
| `users` | Auth / roles |
| `telegram_messages` | Raw inbound messages (audit + duplicate hash) |
| `parsed_alerts` | Structured parser output per message |
| `trades` | Normalized trades with status & P&L |
| `trade_legs` | Individual option legs per trade |
| `orders` | Open/close orders sent to broker (paper or live) |
| `positions` | Open position state + mark/unrealized |
| `pnl_snapshots` | Point-in-time account snapshots |
| `daily_reports` | EOD summaries |
| `settings` | Key/value app settings |
| `risk_rules` | Versioned risk configuration (latest = active) |
| `email_logs` | Every email attempt (sent/failed/skipped) |
| `audit_logs` | Append-only trail of every action |

## API endpoints

```
GET  /health
GET  /api/dashboard/overview
GET  /api/dashboard/equity-curve
GET  /api/dashboard/daily-pnl?days=30
GET  /api/dashboard/strategy-performance
GET  /api/dashboard/ticker-performance

GET  /api/trades?status=OPEN
GET  /api/trades/open | /closed | /pending
GET  /api/trades/{id}
POST /api/trades/{id}/approve
POST /api/trades/{id}/reject

GET  /api/alerts?limit=100
GET  /api/alerts/messages
POST /api/alerts/preview       {text}
POST /api/alerts/simulate      {text, auto_approve}

GET  /api/risk-rules
PUT  /api/risk-rules
GET  /api/settings
POST /api/auth/login
```

## Data flow

1. **telegram_listener** receives a message → `ingest_message` (dedupe by hash) →
   stores `telegram_messages`.
2. `process_message` → `parse_alert` → stores `parsed_alerts` (+ audit).
3. Entry → `_create_entry_trade`: builds `trades` + `trade_legs`, computes
   `max_risk`, runs `risk_engine`. Status = `NEEDS_REVIEW` or `PENDING_APPROVAL`.
4. User hits **Approve** → `approve_trade` re-checks risk → `PaperBroker.submit`
   fills → status `OPEN`, creates `positions`, writes `orders` (+ audit + email).
5. Exit alert → matched to open trade → approve → close order → `pnl_engine`
   computes realized P&L → status `CLOSED` (+ email).
6. Celery beat: `mark_to_market` every 5 min; `end_of_day_report` after close →
   `daily_reports` + EOD email.
```
