#!/bin/bash

# AI Trading Bot - Docker Run Script
# Simple script to run the bot in Docker/Podman

set -e

echo "╔═══════════════════════════════════════════════════════╗"
echo "║     AI Trading Bot - Docker Runner                    ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please create .env file first:"
    echo "  cp .env.example .env"
    echo "  vim .env  # Add your API keys"
    exit 1
fi

# Detect container runtime
if command -v podman &> /dev/null; then
    CONTAINER_RUNTIME="podman"
    echo "✅ Using Podman"
elif command -v docker &> /dev/null; then
    CONTAINER_RUNTIME="docker"
    echo "✅ Using Docker"
else
    echo "❌ Neither Podman nor Docker found!"
    exit 1
fi

echo ""
echo "📦 Building container..."
$CONTAINER_RUNTIME build -f Dockerfile.prod -t ai-trading-bot:latest .

echo ""
echo "🚀 Starting AI Trading Bot..."
echo ""
echo "Dashboard: http://localhost:8080"
echo "Logs: docker logs -f ai-trading-bot"
echo ""

# Run container
$CONTAINER_RUNTIME run -d \
    --name ai-trading-bot \
    --restart unless-stopped \
    -p 8080:8080 \
    -v $(pwd)/logs:/app/logs \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/config:/app/config \
    --env-file .env \
    ai-trading-bot:latest

echo "✅ Bot started!"
echo ""
echo "📋 Useful Commands:"
echo "   View logs:     $CONTAINER_RUNTIME logs -f ai-trading-bot"
echo "   Stop bot:      $CONTAINER_RUNTIME stop ai-trading-bot"
echo "   Remove bot:    $CONTAINER_RUNTIME rm ai-trading-bot"
echo "   Dashboard:     http://localhost:8080"
echo ""
