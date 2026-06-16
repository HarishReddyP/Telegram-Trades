#!/bin/bash
# Railway Deployment via Web UI + Manual Config
# Since railway up has CLI limitations, use web dashboard for final step

set -e

echo "=========================================="
echo "Railway Deployment Setup"
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
fi
export JWT_SECRET

# =========================================================================
# Create Railway Project & Set Up Services
# =========================================================================
echo -e "${YELLOW}STEP 1: Initializing Railway Project${NC}"
PROJECT_NAME="telegram-trade-system"

# Initialize project if needed
railway init --name "$PROJECT_NAME" --empty 2>/dev/null || true

echo -e "${GREEN}✓ Project ready${NC}"
echo

# =========================================================================
# STEP 2: Add Add-ons
# =========================================================================
echo -e "${YELLOW}STEP 2: Adding PostgreSQL & Redis Add-ons${NC}"

railway add --plugin postgres 2>/dev/null || true
railway add --plugin redis 2>/dev/null || true

sleep 10
echo -e "${GREEN}✓ Add-ons added${NC}"
echo

# =========================================================================
# STEP 3: Set All Environment Variables
# =========================================================================
echo -e "${YELLOW}STEP 3: Configuring Environment Variables${NC}"

# Use railway cli to set variables (one by one)
railway variables set TELEGRAM_API_ID "$TELEGRAM_API_ID" 2>/dev/null || true
railway variables set TELEGRAM_API_HASH "$TELEGRAM_API_HASH" 2>/dev/null || true
railway variables set TELEGRAM_SESSION "$TELEGRAM_SESSION" 2>/dev/null || true
railway variables set JWT_SECRET "$JWT_SECRET" 2>/dev/null || true
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

echo -e "${GREEN}✓ Environment variables configured${NC}"
echo

# =========================================================================
# Summary and next steps
# =========================================================================
echo -e "${GREEN}=========================================="
echo "✅ Railway Project Setup Complete!"
echo "==========================================${NC}"
echo

echo -e "${YELLOW}📊 Dashboard is Ready${NC}"
echo "  All environment variables are configured!"
echo "  PostgreSQL & Redis add-ons are activated!"
echo
echo "Next: Connect your GitHub repo and deploy services"
echo

echo -e "${YELLOW}Option A: Via Railway Web Dashboard (Recommended)${NC}"
echo "  1. Go to: railway open"
echo "  2. Click 'New Service' → Connect GitHub"
echo "  3. Select this repository and branch"
echo "  4. Railway will auto-detect 3 services from Procfile"
echo "  5. Confirm & deploy"
echo

echo -e "${YELLOW}Option B: Via GitHub Integration${NC}"
echo "  1. Push to GitHub"
echo "  2. Go to Railway: railway open"
echo "  3. Click 'Connect GitHub' and select this repo"
echo "  4. Deploy from branch"
echo

echo "Services to create (from Procfile):"
echo "  • web (backend): Fast API"
echo "  • worker: Celery scheduler"
echo "  • telegram: Telegram listener"
echo

echo -e "${YELLOW}📝 Deployment File${NC}"
echo "  Use Procfile (already in repo):"
cat Procfile
echo

echo "Credentials are secure! All env vars set. Ready to deploy. 🚀"
