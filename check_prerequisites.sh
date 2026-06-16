#!/bin/bash
# Prerequisites checker for Railway deployment
# Verifies you have everything needed before deploying

set -e

echo "=========================================="
echo "Railway Deployment Prerequisites Checker"
echo "=========================================="
echo

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

READY=true

# Check 1: Railway CLI
echo -n "Checking Railway CLI... "
if command -v railway &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "  Install with: npm install -g @railway/cli"
    READY=false
fi

# Check 2: Railway authentication
echo -n "Checking Railway login... "
if railway whoami > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} ($(railway whoami))"
else
    echo -e "${RED}✗${NC}"
    echo "  Run: railway login"
    READY=false
fi

# Check 3: Backend files
echo -n "Checking backend/Dockerfile... "
if [ -f "backend/Dockerfile" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    READY=false
fi

echo -n "Checking backend/requirements.txt... "
if [ -f "backend/requirements.txt" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    READY=false
fi

# Check 4: Telegram credentials
echo
echo "Telegram Credentials Needed:"
echo "  ☐ TELEGRAM_API_ID (from https://my.telegram.org)"
echo "  ☐ TELEGRAM_API_HASH (from https://my.telegram.org)"
echo "  ☐ TELEGRAM_CHANNEL (@handle or numeric id)"
echo "  ☐ TELEGRAM_SESSION (generated from: cd backend && python -m app.services.telegram_session)"
echo

if [ "$READY" = true ]; then
    echo -e "${GREEN}✓ All prerequisites met!${NC}"
    echo
    echo "Next step:"
    echo "  1. Generate TELEGRAM_SESSION (if you don't have it):"
    echo "     cd backend && python -m app.services.telegram_session"
    echo
    echo "  2. Run the deployment:"
    echo "     bash deploy.sh"
    exit 0
else
    echo -e "${RED}✗ Some prerequisites missing.${NC}"
    echo "Please fix the items above and try again."
    exit 1
fi
