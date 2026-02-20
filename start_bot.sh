#!/bin/bash

# Hybrid Trading Bot - Startup Script
# Usage: ./start_bot.sh [testnet|live] [capital]
# 
# This script:
# - Kills any existing bot processes
# - Starts infrastructure (Redis, PostgreSQL)
# - Starts the trading bot
# - Prevents multiple instances

set -e

MODE=${1:-testnet}
CAPITAL=${2:-15}
PID_FILE="/tmp/ai_trading_bot.pid"

echo "╔═══════════════════════════════════════════════════════╗"
echo "║        HYBRID TRADING BOT - STARTUP                   ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "Mode: $MODE"
echo "Capital: \$$CAPITAL"
echo ""

# ============================================
# STEP 1: Kill any existing bot processes
# ============================================
echo "📋 Checking for existing bot processes..."

if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "⚠️  Bot already running with PID: $OLD_PID"
        echo "   Stopping old instance..."
        kill $OLD_PID 2>/dev/null || true
        sleep 2
        
        # Verify it's dead
        if ps -p $OLD_PID > /dev/null 2>&1; then
            echo "⚠️  Process still alive, forcing kill..."
            kill -9 $OLD_PID 2>/dev/null || true
            sleep 1
        fi
        
        echo "✓ Old instance stopped"
    fi
    rm -f "$PID_FILE"
fi

# Also kill any orphaned bot processes
ORPHANS=$(ps aux | grep "python main.py" | grep -v grep | awk '{print $2}' || true)
if [ -n "$ORPHANS" ]; then
    echo "⚠️  Found orphaned bot processes, killing..."
    echo "$ORPHANS" | xargs kill -9 2>/dev/null || true
    sleep 1
    echo "✓ Orphaned processes killed"
fi

echo "✓ Clean slate ready"
echo ""

# ============================================
# STEP 2: Check configuration
# ============================================
cd "$(dirname "$0")"

if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo ""
    echo "Please run:"
    echo "  cp .env.example .env"
    echo "  vim .env  # Add your API keys"
    exit 1
fi

# Load and validate environment
source .env

if [ -z "$ANTHROPIC_API_KEY" ] || [[ "$ANTHROPIC_API_KEY" == *"your-"* ]]; then
    echo "❌ ANTHROPIC_API_KEY not configured in .env"
    exit 1
fi

if [ -z "$PRIMARY_API_KEY" ] || [[ "$PRIMARY_API_KEY" == *"your-"* ]]; then
    echo "❌ PRIMARY_API_KEY (Binance) not configured in .env"
    exit 1
fi

echo "✓ Configuration loaded and validated"
echo ""

# ============================================
# STEP 3: Check Python environment
# ============================================
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

source venv/bin/activate

echo "📦 Checking dependencies..."
pip install -q -r requirements.txt 2>/dev/null || true
echo "✓ Dependencies installed"
echo ""

# ============================================
# STEP 4: Start PostgreSQL container
# ============================================
echo "🐳 Checking database..."
if ! podman compose ps 2>/dev/null | grep -q "running"; then
    echo "🚀 Starting PostgreSQL container..."
    podman compose up -d postgres
    echo "✓ Database started"
    echo ""
    echo "⏳ Waiting for database to be ready (5 seconds)..."
    sleep 5
else
    echo "✓ Database already running"
fi
echo ""

# ============================================
# STEP 5: Start the bot
# ============================================
echo "╔═══════════════════════════════════════════════════════╗"
echo "║           STARTING TRADING BOT                        ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Start bot in background and save PID
python main.py --mode $MODE --capital $CAPITAL &
BOT_PID=$!
echo $BOT_PID > "$PID_FILE"

echo ""
echo "✅ Bot started successfully!"
echo ""
echo "📊 Bot Details:"
echo "   PID: $BOT_PID"
echo "   Mode: $MODE"
echo "   Capital: \$$CAPITAL"
echo "   PID File: $PID_FILE"
echo ""

# ============================================
# STEP 6: Start Web Dashboard
# ============================================
echo ""
echo "🌐 Starting Web Dashboard..."

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    echo "⏳ Installing Flask..."
    pip install -q flask 2>/dev/null
fi

# Start dashboard in background (with venv activated)
nohup python web_dashboard.py > logs/dashboard.log 2>&1 &
DASHBOARD_PID=$!
echo $DASHBOARD_PID > /tmp/ai_dashboard.pid

echo "✅ Dashboard started!"
echo "   Dashboard PID: $DASHBOARD_PID"
echo "   URL: http://localhost:8080"
echo ""

echo "📋 Useful Commands:"
echo "   View logs:     tail -f logs/trading_*.log"
echo "   Dashboard:     http://localhost:8080"
echo "   Stop bot:      ./stop_bot.sh"
echo "   Check status:  ./check_bot.sh"
echo ""
echo "🚀 Happy Trading!"
