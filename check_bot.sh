#!/bin/bash

# Check Trading Bot Status
# Usage: ./check_bot.sh

PID_FILE="/tmp/ai_trading_bot.pid"

echo "╔═══════════════════════════════════════════════════════╗"
echo "║        AI TRADING BOT - STATUS CHECK                  ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Check if bot is running
if [ -f "$PID_FILE" ]; then
    BOT_PID=$(cat "$PID_FILE")
    
    if ps -p $BOT_PID > /dev/null 2>&1; then
        echo "✅ Bot Status: RUNNING"
        echo "   PID: $BOT_PID"
        echo "   Started: $(ps -p $BOT_PID -o lstart=)"
        echo ""
        
        # Show recent activity
        echo "📊 Recent Activity (last 10 log lines):"
        echo "────────────────────────────────────────"
        tail -10 logs/trading_*.log 2>/dev/null | tail -10 || echo "   No logs yet"
        echo ""
        
        # Show profit summary
        if [ -f "logs/trading_$(date +%Y-%m-%d).log" ]; then
            PROFITS=$(grep "PROFIT" logs/trading_$(date +%Y-%m-%d).log 2>/dev/null | wc -l || echo "0")
            echo "💰 Today's Profits: $PROFITS trades"
        fi
    else
        echo "❌ Bot Status: NOT RUNNING"
        echo "   (PID file exists but process is dead)"
        echo ""
        echo "💡 Run './start_bot.sh' to start"
    fi
else
    echo "❌ Bot Status: NOT RUNNING"
    echo "   (No PID file found)"
    echo ""
    echo "💡 Run './start_bot.sh' to start"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
