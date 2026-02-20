#!/bin/bash

# Stop Trading Bot Script
# Stops both bot and dashboard

PID_FILE="/tmp/ai_trading_bot.pid"
DASHBOARD_PID_FILE="/tmp/ai_dashboard.pid"

echo "🛑 Stopping AI Trading Bot..."

# Stop bot
if [ -f "$PID_FILE" ]; then
    BOT_PID=$(cat "$PID_FILE")
    
    if ps -p $BOT_PID > /dev/null 2>&1; then
        echo "✓ Stopping bot (PID: $BOT_PID)..."
        kill $BOT_PID 2>/dev/null || true
        
        # Wait for graceful shutdown
        for i in {1..10}; do
            if ! ps -p $BOT_PID > /dev/null 2>&1; then
                echo "✓ Bot stopped gracefully"
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        if ps -p $BOT_PID > /dev/null 2>&1; then
            echo "⚠️  Force killing bot..."
            kill -9 $BOT_PID 2>/dev/null || true
            sleep 1
        fi
    else
        echo "⚠️  Bot process not running (stale PID file)"
    fi
    
    rm -f "$PID_FILE"
else
    echo "⚠️  No bot PID file found"
fi

# Stop dashboard
if [ -f "$DASHBOARD_PID_FILE" ]; then
    DASH_PID=$(cat "$DASHBOARD_PID_FILE")
    
    if ps -p $DASH_PID > /dev/null 2>&1; then
        echo "✓ Stopping dashboard (PID: $DASH_PID)..."
        kill $DASH_PID 2>/dev/null || true
        sleep 2
        
        # Force kill if still running
        if ps -p $DASH_PID > /dev/null 2>&1; then
            echo "⚠️  Force killing dashboard..."
            kill -9 $DASH_PID 2>/dev/null || true
        fi
    else
        echo "⚠️  Dashboard process not running (stale PID file)"
    fi
    
    rm -f "$DASHBOARD_PID_FILE"
else
    # Try to kill any dashboard processes
    pkill -f "web_dashboard.py" 2>/dev/null && echo "✓ Dashboard stopped" || echo "⚠️  No dashboard found"
fi

# Kill any orphaned processes
ORPHANS=$(ps aux | grep "python.*main.py" | grep -v grep | awk '{print $2}' || true)
if [ -n "$ORPHANS" ]; then
    echo "⚠️  Killing orphaned bot processes..."
    echo "$ORPHANS" | xargs kill -9 2>/dev/null || true
fi

echo ""
echo "✅ All processes stopped"
