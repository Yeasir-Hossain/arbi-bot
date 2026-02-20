#!/bin/bash

# AI Trading Bot - Docker Compose Runner
# Runs everything with docker-compose (bot + dashboard + database)

set -e

echo "╔═══════════════════════════════════════════════════════╗"
echo "║     AI Trading Bot - Docker Compose                   ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo ""
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
echo "🚀 Starting AI Trading Bot with Docker Compose..."
echo ""

# Start with docker-compose
cd /home/yeasir/projects/ai-exp
$CONTAINER_RUNTIME compose -f docker-compose.prod.yml up -d

echo ""
echo "✅ Bot started!"
echo ""
echo "📊 Dashboard: http://localhost:8080"
echo ""
echo "📋 Useful Commands:"
echo "   View logs:     $CONTAINER_RUNTIME compose -f docker-compose.prod.yml logs -f"
echo "   Stop bot:      $CONTAINER_RUNTIME compose -f docker-compose.prod.yml down"
echo "   Restart:       $CONTAINER_RUNTIME compose -f docker-compose.prod.yml restart"
echo "   Status:        $CONTAINER_RUNTIME compose -f docker-compose.prod.yml ps"
echo ""
