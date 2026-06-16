# Railway Deployment — Quick Start (5 minutes)

## TL;DR

Deploy to Railway without coding. Follow these steps:

### 1. Create Project & Add-ons (2 min)
```
railway.app → New Project → Create
Click Add → PostgreSQL (wait ~30s)
Click Add → Redis (wait ~30s)
```

### 2. Generate Telegram Session (1 min)
```bash
cd backend
python -m app.services.telegram_session
# Follow prompts (phone + code from Telegram)
# Copy the printed session string
```

### 3. Create 3 Services (1 min each)
For each service, click **Add** → **GitHub Repo** → select same repo/branch:

| Service | Root Dir | Start Command |
|---------|----------|---|
| `backend` | `backend` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| `worker` | `backend` | `celery -A app.workers.celery_app worker -B --loglevel=info` |
| `telegram-listener` | `backend` | `python -m app.services.telegram_listener` |

### 4. Add Environment Variables (1 min)
Click **Variables** in project → add these:

| Key | Value |
|---|---|
| `JWT_SECRET` | (any random 32-char string) |
| `TRADING_MODE` | `paper` |
| `MANUAL_APPROVAL` | `true` |
| `TELEGRAM_API_ID` | (from https://my.telegram.org) |
| `TELEGRAM_API_HASH` | (from https://my.telegram.org) |
| `TELEGRAM_CHANNEL` | `@yourchannel` or numeric id |
| `TELEGRAM_SESSION` | _(paste from step 2)_ → **click lock to make Secret** |

**Optional**: Add more from `RAILWAY_ENV_VARS.env` as needed.

### 5. Deploy & Monitor
- Each service auto-deploys
- Go to **backend** service → copy **Public URL**
- Open in browser: `https://your-url/docs` (API)
- Click **telegram-listener** → **Logs** → see incoming Telegram messages
- Done! 🎉

---

## Accessing Your System

### Dashboard & API
```
https://your-railway-url/          ← trade dashboard
https://your-railway-url/docs      ← API documentation
https://your-railway-url/health    ← health check
```

### Live Telegram Messages
1. Click **telegram-listener** service
2. Go to **Logs** tab
3. Watch for incoming channel messages (real-time)

---

## How Telegram Session Stays Active

✅ **It persists** because:
- Session token stored in Railway environment variables
- `telegram-listener` service runs 24/7
- Railway auto-restarts on crash

⚠️ **Session expires if**:
- You log out your Telegram account elsewhere
- Password/2FA changed
- Regenerate if needed: `cd backend && python -m app.services.telegram_session`

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Backend won't start | Check **Logs** for errors; ensure PostgreSQL & Redis add-ons deployed |
| Telegram listener not receiving messages | Verify `TELEGRAM_SESSION` is set; check **Logs** for "listener started" message |
| Worker not running tasks | Ensure `REDIS_URL` set; check **Logs** for Celery connection errors |
| Frontend not loading | Open backend public URL; frontend is served by backend |

---

## For More Details

See [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md) (full guide with troubleshooting, architecture, migration, etc.)
