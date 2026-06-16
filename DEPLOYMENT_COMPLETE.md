# 🚀 Railway Deployment - Final Steps (Complete Setup Ready!)

## Status ✅

The following are **already configured**:
- ✅ PostgreSQL add-on created
- ✅ Redis add-on created  
- ✅ Environment variables set (TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION, etc.)
- ✅ Procfile ready with 3 services
- ✅ Dockerfiles ready

**What you need to do:** Deploy services via GitHub or Docker

---

## Option 1: Deploy via GitHub (Recommended - Fastest)

### Step 1: Push to GitHub
If not already pushed, push this repo to GitHub:
```bash
git remote add origin https://github.com/YOUR_USERNAME/telegram-trade-system.git
git branch -M main
git push -u origin main
```

### Step 2: Connect to Railway
1. Open: https://railway.app/dashboard
2. Click **New Project** → **Deploy from GitHub Repo**
3. Authorize GitHub if needed
4. Select your `telegram-trade-system` repository
5. Click **Deploy**

### Step 3: Add Services
After repo is connected, Railway will auto-detect the **Procfile** and create 3 services:
- `web` - Backend (FastAPI)
- `worker` - Celery
- `telegram` - Telegram Listener

**All environment variables are already set!** Services will inherit them automatically.

### Step 4: Monitor
1. Dashboard → each service → **Logs** tab
2. Backend should say: `Uvicorn running on 0.0.0.0:8000`
3. Telegram Listener should say: `Telegram listener started on @your_channel`
4. Worker should show Celery ready message

---

## Option 2: Deploy via Web UI (Manual - More Control)

### Step 1: Create Project
1. Go to https://railway.app/dashboard
2. Click **New Project** → **Create**
3. Name it: `telegram-trade-system`

### Step 2: Add Add-ons *(if not already added)*
1. Click **Add** → **PostgreSQL** (wait for it to initialize)
2. Click **Add** → **Redis** (wait for it to initialize)

### Step 3: Verify Variables
1. Go to project settings → **Variables**
2. You should see all these already set:
   ```
   TELEGRAM_API_ID=33480216
   TELEGRAM_API_HASH=23a2a9295ae91d...
   TELEGRAM_SESSION=1AZWarzUB...
   TELEGRAM_CHANNEL=-1001431432035
   JWT_SECRET=...
   TRADING_MODE=paper
   MANUAL_APPROVAL=true
   ... and more
   ```
3. If any are missing, add them from `RAILWAY_ENV_VARS.env`

### Step 4: Create 3 Services

#### Service 1: Backend (Web)
1. Click **Add** → **GitHub Repo** (or **Dockerfile**)
2. Connect your repo / select backend Dockerfile
3. Name: `backend`
4. Click **Settings** → **Build & Deploy**
5. **Root Directory**: `backend`
6. **Start Command**: 
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
7. **Port**: `8000`
8. Save & Deploy

#### Service 2: Worker (Celery)  
1. Click **Add** → **GitHub Repo** (same repo)
2. Name: `worker`
3. **Root Directory**: `backend`
4. **Start Command**:
   ```
   celery -A app.workers.celery_app worker -B --loglevel=info
   ```
5. Save & Deploy

#### Service 3: Telegram Listener
1. Click **Add** → **GitHub Repo** (same repo)
2. Name: `telegram-listener`
3. **Root Directory**: `backend`
4. **Start Command**:
   ```
   python -m app.services.telegram_listener
   ```
5. Save & Deploy

---

## Access Your Deployed System

### Dashboard & API
1. Click **backend** service
2. Go to **Settings** → scroll to **Public URL**
3. Copy the Railway-generated URL (e.g., `https://chatty-production-abc123.railway.app`)
4. Open in browser:
   - Dashboard: `https://your-url/`
   - API docs: `https://your-url/docs`
   - Health: `https://your-url/health`

### Monitor Services
- **backend** → **Logs** → API requests, FastAPI startup
- **worker** → **Logs** → Celery tasks, beat scheduler
- **telegram-listener** → **Logs** → Incoming Telegram messages (real-time)

---

## How Telegram Session Persists

✅ **Session stays active because:**
- Stored in Railway environment variables (survives restarts)
- `telegram-listener` service runs 24/7
- Railway auto-restarts on crashes

⚠️ **Session expires if:**
- You log out Telegram account elsewhere
- Password/2FA changed
- Regenerate: `cd backend && python -m app.services.telegram_session`

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Backend won't start** | Check `DATABASE_URL` auto-set from Postgres add-on; view Logs for errors |
| **Telegram not receiving** | Verify `TELEGRAM_SESSION` is set (not empty); check Logs for "listener started" |
| **Worker tasks not running** | Verify `REDIS_URL` auto-set from Redis add-on; restart worker service |
| **Frontend not loading** | Open backend public URL; frontend is served by backend |

---

## Summary

1. **Already done:**
   - Environment variables configured ✅
   - Add-ons (PostgreSQL, Redis) created ✅
   - Procfile ready ✅
   - Dockerfiles ready ✅

2. **Next (choose one):**
   - **Option 1 (Fast):** Push to GitHub → connect in Railway → auto-deploy from Procfile
   - **Option 2 (Manual):** Web UI → create 3 services manually → start each

3. **After deploy:**
   - Copy backend public URL
   - Open dashboard in browser
   - Monitor Telegram Listener logs

**Estimated time to live:** 3-5 minutes after starting deployment 🚀

Questions? See: 
- [RAILWAY_QUICKSTART.md](./RAILWAY_QUICKSTART.md)
- [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md)
