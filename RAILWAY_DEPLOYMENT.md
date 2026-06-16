# Railway Deployment Guide

This guide walks you through deploying the Telegram Trade System to Railway without running it locally.

## Overview

You'll deploy **3 separate services** on Railway:
1. **Backend** (FastAPI web service) — serves the API & dashboard
2. **Worker** (Celery) — runs background jobs & beat scheduler
3. **Telegram Listener** (Telethon) — monitors Telegram channel for trade alerts

Plus two **add-ons**:
- **PostgreSQL** — stores trades, alerts, P&L data
- **Redis** — Celery message broker

---

## Step 1: Create Railway Project & Add-ons

### 1.1 Create the project
1. Go to [railway.app](https://railway.app)
2. Log in / sign up
3. Click **New Project** → **Create**

### 1.2 Add PostgreSQL
1. In your new project, click **Add** (bottom-left)
2. Search for **PostgreSQL** → click it
3. Railway creates a `DATABASE_URL` environment variable automatically
   - You'll see it listed after the add-on deploys (visible in Variables tab)

### 1.3 Add Redis
1. Click **Add** again
2. Search for **Redis** → click it
3. Railway creates a `REDIS_URL` environment variable automatically

---

## Step 2: Create Three Services

### 2.1 Backend Service (FastAPI)
1. Click **Add** → **GitHub Repo** (or **Docker Image**)
   - If using GitHub: connect your repo, select branch `main`
   - If using Docker: select the `backend/Dockerfile`
2. **Service name**: `backend`
3. **Start command**: (set in Step 4 below)

### 2.2 Worker Service (Celery)
1. Click **Add** → **GitHub Repo** (same repo, same branch)
2. **Service name**: `worker`
3. **Start command**: (set in Step 4 below)

### 2.3 Telegram Listener Service
1. Click **Add** → **GitHub Repo** (same repo, same branch)
2. **Service name**: `telegram-listener`
3. **Start command**: (set in Step 4 below)

---

## Step 3: Configure Start Commands

Each service needs a **start command** that tells Railway what to run.

### For Backend service:
1. Click the **backend** service tile
2. Go to **Settings** → **Build & Deploy**
3. Under **Start Command**, paste:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
4. **Root Directory**: `backend` (Railway will cd here before running)
5. Save

### For Worker service:
1. Click the **worker** service tile
2. Go to **Settings** → **Build & Deploy**
3. Under **Start Command**, paste:
   ```
   celery -A app.workers.celery_app worker -B --loglevel=info
   ```
4. **Root Directory**: `backend`
5. **Deployment trigger**: _Optional — disable auto-deploy if you want to control it separately_
6. Save

### For Telegram Listener service:
1. Click the **telegram-listener** service tile
2. Go to **Settings** → **Build & Deploy**
3. Under **Start Command**, paste:
   ```
   python -m app.services.telegram_listener
   ```
4. **Root Directory**: `backend`
5. Save

---

## Step 4: Configure Environment Variables & Secrets

All three services share the same environment via Railway project variables. Add them once; they inherit automatically.

### 4.1 Required Variables
1. In your project, click **Variables** (or select any service → **Variables**)
2. Add the following **Key-Value** pairs:

#### Auto-generated (from add-ons):
- `DATABASE_URL` ← (Railway Postgres add-on auto-fills this)
- `REDIS_URL` ← (Railway Redis add-on auto-fills this)

#### Core config:
| Key | Value | Notes |
|---|---|---|
| `JWT_SECRET` | _(generate a random 32-character string)_ | Use: `openssl rand -hex 16` |
| `TRADING_MODE` | `paper` | or `live` if you're trading for real |
| `MANUAL_APPROVAL` | `true` | require manual approval before executing trades |
| `LIVE_TRADING_ENABLED` | `false` | keep false unless you have live broker credentials |
| `STARTING_CAPITAL` | `25000` | your paper trading account starting value |
| `ALLOWED_TICKERS` | `SPX,SPY,QQQ,IWM` | comma-separated, no spaces |
| `ALLOWED_STRATEGIES` | `BULL_PUT_SPREAD,BEAR_CALL_SPREAD,IRON_CONDOR,IRON_FLY,BUTTERFLY,SINGLE_LEG` | supported trade types |

#### Telegram (secrets):
| Key | Value | Notes |
|---|---|---|
| `TELEGRAM_API_ID` | _(from my.telegram.org)_ | **Store as Secret** |
| `TELEGRAM_API_HASH` | _(from my.telegram.org)_ | **Store as Secret** |
| `TELEGRAM_CHANNEL` | `@channel_name` or `-1001431432035` | numeric or @handle |
| `TELEGRAM_SESSION` | _(see Step 5 below)_ | **Store as Secret** |

#### Optional (if using features):
| Key | Value |
|---|---|
| `ANTHROPIC_API_KEY` | (for Claude Vision image parsing) |
| `SMTP_HOST` | (for email notifications) |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | (your email) |
| `SMTP_PASSWORD` | (app password, not main password) |
| `SMTP_FROM` | (sender email) |
| `REPORT_RECIPIENT` | (where EOD reports go) |
| `TRADIER_TOKEN` | (if using Tradier for live quotes) |
| `TRADIER_BASE_URL` | `https://sandbox.tradier.com` |

### 4.2 Mark Secrets as Secret
For sensitive variables (Telegram credentials), click the **lock icon** next to each one to mark them as **Secret** (encrypted, not logged).

---

## Step 5: Generate & Add TELEGRAM_SESSION

The `TELEGRAM_SESSION` is a Telethon StringSession token that represents your authenticated Telegram user. Generate it **locally** (recommended) or via Railway shell.

### Option A: Generate Locally (Recommended)

```bash
cd backend
python -m app.services.telegram_session
```

This will:
1. Prompt for your Telegram phone number
2. Ask for a verification code (sent to your Telegram account)
3. Print a long base64 string — copy it

Then paste it into Railway:
1. Go to your project → **Variables**
2. Add key `TELEGRAM_SESSION` with the copied string
3. Click the **lock icon** to make it a Secret
4. Save

### Option B: Generate via Railway Shell (if local setup unavailable)

1. In Railway, click the **backend** service
2. Go to **Logs** → **Shell** tab (or **Settings** → **Shell access**)
3. Run:
   ```bash
   cd backend
   python -m app.services.telegram_session
   ```
4. Copy the printed string and add it to Variables (Step 5 → Option A, steps 1–4)

---

## Step 6: Deploy Services

Once all variables are set and start commands configured:

### For each service:
1. Click the service tile
2. Click **Deploy** (or push to `main` branch if GitHub auto-deploy is enabled)
3. Watch the **Logs** tab — you should see:
   - **Backend**: FastAPI startup message (e.g., "Uvicorn running on 0.0.0.0:8000")
   - **Worker**: Celery worker ready message
   - **Telegram Listener**: "Telegram listener started on @channel_name"

---

## Step 7: Access Your Deployed System

### Dashboard & API
1. Click the **backend** service
2. Go to **Settings** → look for **Public URL** or **Deployment** section
3. Copy the Railway-generated domain (e.g., `https://telegram-trade-system-prod-abc123.railway.app`)
4. Open in browser:
   - Dashboard: `https://telegram-trade-system-prod-abc123.railway.app/` (frontend hosted here)
   - API docs: `https://telegram-trade-system-prod-abc123.railway.app/docs`
   - Health check: `https://telegram-trade-system-prod-abc123.railway.app/health`

### Monitor Telegram Listener
1. Click the **telegram-listener** service
2. Go to **Logs** — you'll see incoming Telegram messages in real-time
3. Look for messages like:
   ```
   Telegram listener started on @your_channel (filter=...)
   [DEBUG] chat_id=... photo=... doc=...
   image alert extracted (X chars)
   trade created id=... ticker=... strategy=...
   ```

### Worker & Celery Beat
1. Click the **worker** service
2. Go to **Logs** — see scheduled tasks, processing, etc.
3. Logs show EOD reports, mark-to-market runs, etc.

---

## Step 8: How Telegram Session Stays Active

### Long-running Behavior
- The `TELEGRAM_SESSION` token persists across restarts because it's stored in Railway environment variables.
- The **telegram-listener** service runs continuously; if it crashes, Railway auto-restarts it.
- As long as the service is running, the Telethon client can listen for new messages in your channel.

### Session Expiry / Invalidation
- Telegram invalidates sessions if:
  - The account logs out elsewhere (web, app, etc.)
  - Password changed or 2FA reconfigured
  - Telegram security policy forces re-auth (rare)
- If this happens, regenerate `TELEGRAM_SESSION` locally and update it in Railway Variables.

### Keep Sessions Fresh
- **Do not** manually log out from your Telegram account used for the session.
- **Do not** run `telegram_session` multiple times with the same account (creates new sessions).
- The listener process should run 24/7 on Railway; it keeps the session warm.

---

## Troubleshooting

### Backend won't start
- Check `DATABASE_URL` and `REDIS_URL` are auto-populated from add-ons.
- Check **Logs** for import errors or missing dependencies.
- Verify `requirements.txt` includes all dependencies (including `uvicorn`, `psycopg`, etc.).

### Worker won't start or tasks not running
- Ensure `REDIS_URL` is set.
- Check that **worker** service has same environment variables as backend.
- Look in **Logs** for Celery connection errors.

### Telegram Listener not receiving messages
- Verify `TELEGRAM_SESSION` is set and not empty.
- Verify `TELEGRAM_CHANNEL` is correct (@handle or numeric id).
- Check **Logs** for "Telegram listener started" message. If missing, the session is likely empty/invalid.
- Check if you're a member of the channel (the session represents your user account, not a bot).

### Frontend not showing
- Frontend is served by the backend (`backend/Dockerfile` includes Nginx; vite-built files are in `public/`).
- If you deployed a separate frontend service instead, ensure it's built and running.
- Check the public URL from the **backend** service and open it in a browser.

---

## Frontend Deployment (If Separate)

If you want to deploy frontend as a separate static service:

1. Create a separate Railway service from `frontend/Dockerfile`
2. Expose port 3000 (or configure Nginx port in `frontend/nginx.conf`)
3. Configure **CORS** on backend to allow frontend domain:
   - In `backend/app/main.py`, add the frontend URL to `allow_origins`
   - Example:
     ```python
     allow_origins=[
         "https://frontend-domain.railway.app",
         "https://backend-domain.railway.app",
         "localhost:5173",
     ]
     ```

---

## Database Setup (Automatic)

- Railway Postgres add-on auto-creates the database on first backend deployment.
- The backend runs `app.db.init_db.init_db()` on startup (if `DATABASE_URL` is valid).
- Tables are created automatically; no manual migrations needed.

---

## Monitoring & Logs

1. **Backend service** → **Logs** — API requests, errors, general app logs
2. **Worker service** → **Logs** — Celery tasks, beat scheduler
3. **Telegram Listener** → **Logs** — Telegram messages, parsing, trade creation
4. Use **Deployment** tab to see deployment history and status

---

## Summary Checklist

- [ ] Created Railway project
- [ ] Added PostgreSQL & Redis add-ons
- [ ] Created 3 services: backend, worker, telegram-listener
- [ ] Set start commands for each service
- [ ] Added environment variables (JWT_SECRET, TELEGRAM_*, TRADING_MODE, etc.)
- [ ] Generated and added TELEGRAM_SESSION as a Secret
- [ ] Deployed all services
- [ ] Verified backend public URL and dashboard access
- [ ] Confirmed telegram-listener is running (check Logs)
- [ ] (Optional) Deployed frontend as separate service if desired

---

## Questions?

Refer to Railway docs: https://docs.railway.app/
Or reach out with specific error messages from the **Logs** tab.
