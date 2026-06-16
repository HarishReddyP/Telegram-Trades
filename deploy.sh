#!/bin/bash
# =============================================================================
# Railway Automated Deployment Script
# =============================================================================
# This script deploys the entire Telegram Trade System to Railway.
# 
# PREREQUISITES:
#   1. Railway CLI installed: railway --version
#   2. Logged in: railway login
#   3. You have TELEGRAM_API_ID and TELEGRAM_API_HASH from https://my.telegram.org
#   4. TELEGRAM_SESSION generated locally: cd backend && python -m app.services.telegram_session
#
# USAGE:
#   bash deploy.sh
# 
# INTERACTIVE PROMPTS:
#   The script will ask for sensitive values (Telegram credentials).
#   They will be stored as Railway Secrets (encrypted).
#
# =============================================================================

set -e

echo "=========================================="
echo "Railway Deployment Script"
echo "=========================================="
echo

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if already logged in
echo -e "${YELLOW}✓ Checking Railway authentication...${NC}"
if ! railway whoami > /dev/null 2>&1; then
    echo -e "${RED}✗ Not logged into Railway. Please run: railway login${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Authenticated${NC}"
echo

# =========================================================================
# STEP 1: Create Project
# =========================================================================
echo -e "${YELLOW}STEP 1: Creating Railway Project${NC}"
read -p "Enter project name (default: telegram-trade-system): " PROJECT_NAME
PROJECT_NAME=${PROJECT_NAME:-telegram-trade-system}

railway init --name "$PROJECT_NAME" --empty || true
# (ignoring error if project already exists)

echo -e "${GREEN}✓ Project created/selected${NC}"
echo

# =========================================================================
# STEP 2: Add PostgreSQL & Redis
# =========================================================================
echo -e "${YELLOW}STEP 2: Adding PostgreSQL & Redis Add-ons${NC}"
echo "This may take 30-60 seconds..."

railway add --plugin postgres || echo "PostgreSQL may already exist"
railway add --plugin redis || echo "Redis may already exist"

echo -e "${GREEN}✓ Add-ons added${NC}"
sleep 5  # Wait for add-ons to initialize
echo

# =========================================================================
# STEP 3: Collect Sensitive Variables
# =========================================================================
echo -e "${YELLOW}STEP 3: Collecting Telegram Credentials${NC}"
echo "You'll need values from https://my.telegram.org"
echo

read -p "Enter TELEGRAM_API_ID: " TELEGRAM_API_ID
read -p "Enter TELEGRAM_API_HASH: " TELEGRAM_API_HASH
read -p "Enter TELEGRAM_CHANNEL (@handle or numeric id): " TELEGRAM_CHANNEL

echo
echo "Now, provide your TELEGRAM_SESSION string."
echo "If you don't have one, generate it first:"
echo "  cd backend"
echo "  python -m app.services.telegram_session"
echo
read -p "Enter TELEGRAM_SESSION (paste the full string): " TELEGRAM_SESSION

read -p "Enter JWT_SECRET (or press Enter for auto-generated): " JWT_SECRET
if [ -z "$JWT_SECRET" ]; then
    JWT_SECRET=$(openssl rand -hex 16)
    echo "Generated JWT_SECRET: $JWT_SECRET"
fi

echo -e "${GREEN}✓ Credentials collected${NC}"
echo

# =========================================================================
# STEP 4: Set Environment Variables (as Secrets)
# =========================================================================
echo -e "${YELLOW}STEP 4: Setting Environment Variables & Secrets${NC}"

# Secrets (encrypted)
echo "Setting secrets..."
railway variables set TELEGRAM_API_ID "$TELEGRAM_API_ID" --context "$PROJECT_NAME" || true
railway variables set TELEGRAM_API_HASH "$TELEGRAM_API_HASH" --context "$PROJECT_NAME" || true
railway variables set TELEGRAM_SESSION "$TELEGRAM_SESSION" --context "$PROJECT_NAME" || true
railway variables set JWT_SECRET "$JWT_SECRET" --context "$PROJECT_NAME" || true

# Non-sensitive variables
echo "Setting standard variables..."
railway variables set TELEGRAM_CHANNEL "$TELEGRAM_CHANNEL" --context "$PROJECT_NAME" || true
railway variables set TRADING_MODE "paper" --context "$PROJECT_NAME" || true
railway variables set MANUAL_APPROVAL "true" --context "$PROJECT_NAME" || true
railway variables set LIVE_TRADING_ENABLED "false" --context "$PROJECT_NAME" || true
railway variables set STARTING_CAPITAL "25000" --context "$PROJECT_NAME" || true
railway variables set ALLOWED_TICKERS "SPX,SPY,QQQ,IWM" --context "$PROJECT_NAME" || true
railway variables set ALLOWED_STRATEGIES "BULL_PUT_SPREAD,BEAR_CALL_SPREAD,IRON_CONDOR,IRON_FLY,BUTTERFLY,SINGLE_LEG" --context "$PROJECT_NAME" || true
railway variables set MAX_RISK_PER_TRADE "500" --context "$PROJECT_NAME" || true
railway variables set MAX_DAILY_LOSS "1000" --context "$PROJECT_NAME" || true
railway variables set MAX_OPEN_TRADES "5" --context "$PROJECT_NAME" || true
railway variables set MAX_CONTRACTS_PER_TRADE "5" --context "$PROJECT_NAME" || true
railway variables set NO_TRADE_NEAR_CLOSE "true" --context "$PROJECT_NAME" || true
railway variables set NO_TRADE_MINUTES_BEFORE_CLOSE "15" --context "$PROJECT_NAME" || true
railway variables set COMMISSION_PER_CONTRACT "0.65" --context "$PROJECT_NAME" || true
railway variables set MARKET_TZ "America/New_York" --context "$PROJECT_NAME" || true
railway variables set MARKET_CLOSE "16:00" --context "$PROJECT_NAME" || true
railway variables set QUOTE_PROVIDER "none" --context "$PROJECT_NAME" || true

echo -e "${GREEN}✓ Environment variables set${NC}"
echo

# =========================================================================
# STEP 5: Deploy Services
# =========================================================================
echo -e "${YELLOW}STEP 5: Deploying Services${NC}"
echo "This will deploy 3 services: backend, worker, telegram-listener"
echo

# Deploy from current directory (must be repo root with Dockerfile, etc.)
CURRENT_DIR=$(pwd)
if [ ! -f "backend/Dockerfile" ]; then
    echo -e "${RED}✗ Error: backend/Dockerfile not found in $CURRENT_DIR${NC}"
    echo "Please run this script from the repo root directory."
    exit 1
fi

echo "Starting deployments..."
echo

# Deploy backend (web service)
echo -e "${YELLOW}→ Deploying backend (FastAPI)...${NC}"
railway up --service backend \
    --build \
    --detach \
    --start-command "cd backend && uvicorn app.main:app --host 0.0.0.0 --port \$PORT" \
    || true

sleep 10

# Deploy worker (Celery)
echo -e "${YELLOW}→ Deploying worker (Celery)...${NC}"
railway up --service worker \
    --build \
    --detach \
    --start-command "cd backend && celery -A app.workers.celery_app worker -B --loglevel=info" \
    || true

sleep 10

# Deploy telegram-listener
echo -e "${YELLOW}→ Deploying telegram-listener (Telethon)...${NC}"
railway up --service telegram-listener \
    --build \
    --detach \
    --start-command "cd backend && python -m app.services.telegram_listener" \
    || true

echo -e "${GREEN}✓ Services deployed${NC}"
echo

# =========================================================================
# STEP 6: Summary & Next Steps
# =========================================================================
echo -e "${GREEN}=========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "==========================================${NC}"
echo

echo "📊 Dashboard:"
echo "  railway open"
echo

echo "🌐 Access Your App:"
echo "  backend service → Settings → copy Public URL"
echo "  Open in browser: https://your-railway-url/"
echo
echo "📡 Monitor Telegram Listener:"
echo "  Click telegram-listener service → Logs tab"
echo "  Watch for incoming Telegram messages in real-time"
echo

echo "🔍 View Logs:"
echo "  railway logs --service backend"
echo "  railway logs --service worker"
echo "  railway logs --service telegram-listener"
echo

echo "📝 Change Variables Later:"
echo "  railway variables set KEY VALUE"
echo "  Or: railway open (Dashboard → Variables)"
echo

echo -e "${YELLOW}⚠️  Important:${NC}"
echo "  • Dashboard will be available at: https://your-railway-url/"
echo "  • API docs at: https://your-railway-url/docs"
echo "  • Monitor service health in Railway Dashboard"
echo

echo "Done! 🚀"
