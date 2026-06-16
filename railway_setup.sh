#!/bin/bash
# Quick Railway CLI setup script
# 
# Prerequisites:
#  - Railway CLI installed: https://docs.railway.app/cli/installation
#  - Logged in: railway login
#  - cd to repo root before running this script
#
# Usage:
#  bash railway_setup.sh

set -e

echo "=== Railway Deployment Setup ==="
echo

# Create project
echo "1. Creating Railway project..."
railway init --name telegram-trade-system

echo
echo "2. Adding PostgreSQL add-on..."
railway add --plugin postgres

echo
echo "3. Adding Redis add-on..."
railway add --plugin redis

echo
echo "4. Setting environment variables..."
echo "   (Note: You still need to set TELEGRAM_CHANNEL, TELEGRAM_SESSION, JWT_SECRET manually)"

# Set basic vars (user must fill in secrets)
read -p "Enter JWT_SECRET (or press Enter to skip - set manually later): " JWT_SECRET
if [ ! -z "$JWT_SECRET" ]; then
  railway variables set JWT_SECRET="$JWT_SECRET"
fi

read -p "Enter TELEGRAM_CHANNEL (@handle or numeric id): " TELEGRAM_CHANNEL
if [ ! -z "$TELEGRAM_CHANNEL" ]; then
  railway variables set TELEGRAM_CHANNEL="$TELEGRAM_CHANNEL"
fi

# Set defaults
railway variables set TRADING_MODE=paper
railway variables set MANUAL_APPROVAL=true
railway variables set LIVE_TRADING_ENABLED=false
railway variables set STARTING_CAPITAL=25000
railway variables set ALLOWED_TICKERS="SPX,SPY,QQQ,IWM"
railway variables set ALLOWED_STRATEGIES="BULL_PUT_SPREAD,BEAR_CALL_SPREAD,IRON_CONDOR,IRON_FLY,BUTTERFLY,SINGLE_LEG"
railway variables set MARKET_TZ="America/New_York"
railway variables set MARKET_CLOSE="16:00"

echo
echo "5. Ready to create services!"
echo
echo "Next steps (via Railway Dashboard):"
echo "  a) Add 3 services from your GitHub repo:"
echo "     - backend (start: uvicorn app.main:app --host 0.0.0.0 --port \$PORT)"
echo "     - worker (start: celery -A app.workers.celery_app worker -B --loglevel=info)"
echo "     - telegram-listener (start: python -m app.services.telegram_listener)"
echo "  b) Generate TELEGRAM_SESSION locally: cd backend && python -m app.services.telegram_session"
echo "  c) Add TELEGRAM_SESSION to Railway Variables as a Secret"
echo "  d) Deploy!"
echo
echo "Dashboard: railway open.app"
