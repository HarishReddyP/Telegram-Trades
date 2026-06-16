# Railway Manual Setup Guide

Since Railway's Procfile support is limited, follow these exact steps in the Railway dashboard:

## Prerequisites ✅
- GitHub repo connected: https://github.com/HarishReddyP/Telegram-Trades
- PostgreSQL add-on created
- Redis add-on created
- Environment variables configured

---

## Step-by-Step Railway Setup

### Step 1: Delete Existing Services (if build failed)
1. Go to your Railway project dashboard
2. For each service (backend, worker, telegram-listener):
   - Click the service → Settings → **Delete Service**
3. Confirm deletion

---

### Step 2: Create 3 New Services from GitHub

#### Service 1: Backend (Web)
1. Click **New Service** → **GitHub Repo**
2. Select: `HarishReddyP/Telegram-Trades` repo, `main` branch
3. **Service name**: `backend`
4. Once created:
   - Click `backend` service
   - Go to **Settings** → **Build & Deploy**
   - **Root Directory**: (leave blank - repo root)
   - **Start Command**:
     ```
     bash -c "cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
     ```
   - **Port**: `8000`
   - Click **Save**

#### Service 2: Worker (Celery)
1. Click **New Service** → **GitHub Repo** (same repo)
2. **Service name**: `worker`
3. Once created:
   - Click `worker` service
   - Go to **Settings** → **Build & Deploy**
   - **Root Directory**: (leave blank)
   - **Start Command**:
     ```
     bash -c "cd backend && celery -A app.workers.celery_app worker -B --loglevel=info"
     ```
   - **Auto-deploy**: Toggle OFF (optional - prevents automatic restarts)
   - Click **Save**

#### Service 3: Telegram Listener
1. Click **New Service** → **GitHub Repo** (same repo)
2. **Service name**: `telegram-listener`
3. Once created:
   - Click `telegram-listener` service
   - Go to **Settings** → **Build & Deploy**
   - **Root Directory**: (leave blank)
   - **Start Command**:
     ```
     bash -c "cd backend && python -m app.services.telegram_listener"
     ```
   - Click **Save**

---

## Step 3: Deploy

For each service (in this order):
1. Click the service
2. Click **Deploy** button (or go to **Deployment** tab → **Trigger Deploy**)
3. Watch **Logs** tab during build
4. Wait for "Build successful" message

---

## Expected Startup Logs

### Backend Service ✅
Should contain:
```
Starting Uvicorn server process
Application startup complete
Uvicorn running on 0.0.0.0:8000
```

### Worker Service ✅
Should contain:
```
celery worker ready
Connected to redis://...
```

### Telegram Listener Service ✅
Should contain:
```
Telegram listener started on -1001431432035
Listening for messages
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Build fails** | Check Logs tab → look for "COPY requirements.txt" error → verify Dockerfile path |
| **Service won't start** | Check start command syntax, verify environment variables are set |
| **Can't connect to Postgres** | Verify PostgreSQL add-on exists, check `DATABASE_URL` in Variables |
| **Redis connection error** | Verify Redis add-on exists, check `REDIS_URL` in Variables |
| **No Telegram messages** | Verify `TELEGRAM_SESSION` is set and not empty; check listener logs |

---

## Accessing Your System

### Dashboard
1. Click **backend** service → **Settings**
2. Find **Public URL** (e.g., `https://telegram-trades-prod.railway.app`)
3. Open in browser: `https://your-url/`
4. API docs: `https://your-url/docs`

### Monitor Services
```bash
railway logs --service backend
railway logs --service worker  
railway logs --service telegram-listener --tail 100
```

---

## Environment Variables Check

In Railway Dashboard, go to **Variables** and verify these exist:
- `TELEGRAM_API_ID` ✓
- `TELEGRAM_API_HASH` ✓
- `TELEGRAM_SESSION` ✓
- `TELEGRAM_CHANNEL` ✓
- `JWT_SECRET` ✓
- `DATABASE_URL` (auto-set by Postgres add-on)
- `REDIS_URL` (auto-set by Redis add-on)

---

Done! Services should be live within 3-5 minutes. 🚀
