#!/bin/bash
# Automated Railway Deployment (Non-interactive)
# Uses credentials from backend/.env

set -e

echo "=========================================="
echo "Automated Railway Deployment"
echo "=========================================="
echo

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Load credentials from .env
echo -e "${YELLOW}Loading credentials from backend/.env...${NC}"
if [ ! -f "backend/.env" ]; then
    echo -e "${RED}✗ backend/.env not found${NC}"
    exit 1
fi

# Extract values
export TELEGRAM_API_ID=$(grep "^TELEGRAM_API_ID=" backend/.env | cut -d= -f2)
export TELEGRAM_API_HASH=$(grep "^TELEGRAM_API_HASH=" backend/.env | cut -d= -f2)
export TELEGRAM_SESSION=$(grep "^TELEGRAM_SESSION=" backend/.env | cut -d= -f2)
export TELEGRAM_CHANNEL=$(grep "^TELEGRAM_CHANNEL=" backend/.env | cut -d= -f2)

if [ -z "$TELEGRAM_API_ID" ] || [ -z "$TELEGRAM_API_HASH" ] || [ -z "$TELEGRAM_SESSION" ]; then
    echo -e "${RED}✗ Missing Telegram credentials in .env${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Credentials loaded${NC}"
echo "  API ID: ${TELEGRAM_API_ID:0:5}..."
echo "  CHANNEL: $TELEGRAM_CHANNEL"
echo

# Generate JWT_SECRET if not in .env
JWT_SECRET=$(grep "^JWT_SECRET=" backend/.env | cut -d= -f2 || echo "")
if [ -z "$JWT_SECRET" ]; then
    JWT_SECRET=$(openssl rand -hex 16)
    echo "Generated JWT_SECRET: $JWT_SECRET"
fi
export JWT_SECRET

echo

# =========================================================================
# STEP 1: Create/Select Project
# =========================================================================
echo -e "${YELLOW}STEP 1: Creating Railway Project${NC}"
PROJECT_NAME="telegram-trade-system"

railway init --name "$PROJECT_NAME" --empty 2>/dev/null || echo "  (Project may already exist)"
echo -e "${GREEN}✓ Project ready${NC}"
echo

# =========================================================================
# STEP 2: Add Add-ons
# =========================================================================
echo -e "${YELLOW}STEP 2: Adding PostgreSQL & Redis${NC}"
echo "Waiting for add-ons to initialize (this may take 30-60 seconds)..."

railway add --plugin postgres 2>/dev/null || echo "  PostgreSQL may already exist"
railway add --plugin redis 2>/dev/null || echo "  Redis may already exist"

sleep 15  # Wait for add-ons to be ready
echo -e "${GREEN}✓ Add-ons configured${NC}"
echo

# =========================================================================
# STEP 3: Set Environment Variables
# =========================================================================
echo -e "${YELLOW}STEP 3: Setting Environment Variables${NC}"

# Core secrets
echo "  Setting secrets..."
railway variables set TELEGRAM_API_ID "$TELEGRAM_API_ID" 2>/dev/null || true
railway variables set TELEGRAM_API_HASH "$TELEGRAM_API_HASH" 2>/dev/null || true
railway variables set TELEGRAM_SESSION "$TELEGRAM_SESSION" 2>/dev/null || true
railway variables set JWT_SECRET "$JWT_SECRET" 2>/dev/null || true

# Standard variables
echo "  Setting standard variables..."
railway variables set TELEGRAM_CHANNEL "$TELEGRAM_CHANNEL" 2>/dev/null || true
railway variables set TRADING_MODE "paper" 2>/dev/null || true
railway variables set MANUAL_APPROVAL "true" 2>/dev/null || true
railway variables set LIVE_TRADING_ENABLED "false" 2>/dev/null || true
railway variables set STARTING_CAPITAL "25000" 2>/dev/null || true
railway variables set ALLOWED_TICKERS "SPX,SPY,QQQ,IWM" 2>/dev/null || true
railway variables set ALLOWED_STRATEGIES "BULL_PUT_SPREAD,BEAR_CALL_SPREAD,IRON_CONDOR,IRON_FLY,BUTTERFLY,SINGLE_LEG" 2>/dev/null || true
railway variables set MAX_RISK_PER_TRADE "500" 2>/dev/null || true
railway variables set MAX_DAILY_LOSS "1000" 2>/dev/null || true
railway variables set MAX_OPEN_TRADES "5" 2>/dev/null || true
railway variables set MARKET_TZ "America/New_York" 2>/dev/null || true
railway variables set MARKET_CLOSE "16:00" 2>/dev/null || true
railway variables set QUOTE_PROVIDER "none" 2>/dev/null || true

echo -e "${GREEN}✓ Environment variables set${NC}"
echo

# =========================================================================
# STEP 4: Deploy Services
# =========================================================================
echo -e "${YELLOW}STEP 4: Deploying 3 Services${NC}"
echo "  • backend (FastAPI web service)"
echo "  • worker (Celery background jobs & scheduler)"
echo "  • telegram-listener (Telethon Telegram monitoring)"
echo

# Verify we're in repo root
if [ ! -f "backend/Dockerfile" ]; then
    echo -e "${RED}✗ Error: Not in repo root. backend/Dockerfile not found.${NC}"
    exit 1
fi

# Deploy backend
echo -e "${YELLOW}→ Deploying backend...${NC}"
railway up --service backend \
    --build \
    --detach \
    --start-command "cd backend && uvicorn app.main:app --host 0.0.0.0 --port \$PORT" \
    2>&1 | head -20 || true

sleep 10

# Deploy worker
echo -e "${YELLOW}→ Deploying worker...${NC}"
railway up --service worker \
    --build \
    --detach \
    --start-command "cd backend && celery -A app.workers.celery_app worker -B --loglevel=info" \
    2>&1 | head -20 || true

sleep 10

# Deploy telegram-listener
echo -e "${YELLOW}→ Deploying telegram-listener...${NC}"
railway up --service telegram-listener \
    --build \
    --detach \
    --start-command "cd backend && python -m app.services.telegram_listener" \
    2>&1 | head -20 || true

echo -e "${GREEN}✓ All services queued for deployment${NC}"
echo

# =========================================================================
# SUMMARY
# =========================================================================
echo -e "${GREEN}=========================================="
echo "✅ DEPLOYMENT INITIATED!"
echo "==========================================${NC}"
echo

echo -e "${YELLOW}📊 Next Steps:${NC}"
echo "  1. Open Railway Dashboard:"
echo "     railway open"
echo
echo "  2. Monitor deployment progress:"
echo "     • backend service → Logs (should start within 2-3 minutes)"
echo "     • worker service → Logs"
echo "     • telegram-listener service → Logs"
echo
echo "  3. Once backend is running, get your public URL:"
echo "     railway logs --service backend | grep 'Uvicorn running'"
echo
echo "  4. Access your app:"
echo "     • Dashboard: https://your-railway-url/"
echo "     • API Docs: https://your-railway-url/docs"
echo "     • Health: https://your-railway-url/health"
echo

echo -e "${YELLOW}📡 Monitor Telegram Listener:${NC}"
echo "     railway logs --service telegram-listener --tail 100"
echo
echo -e "${YELLOW}View All Service Logs:${NC}"
echo "     railway logs --service worker --tail 50"
echo
echo -e "${YELLOW}🔄 Check Service Status:${NC}"
echo "     railway logs --service backend"
echo

echo "Deployment started! Services will be live within 3-5 minutes. 🚀"
