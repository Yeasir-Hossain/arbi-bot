#!/bin/bash

# AI Trading System - Blockchain Setup Script
# Starts Hardhat node and deploys contracts

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔═══════════════════════════════════════════════════════╗"
echo "║     AI Trading System - Blockchain Setup              ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

echo "✅ Node.js version: $(node --version)"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Check if Hardhat node is already running
if curl -s -X POST -H "Content-Type: application/json" --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' http://localhost:8545 2>/dev/null; then
    echo ""
    echo "⚠️  Hardhat node appears to be already running on port 8545"
    echo ""
    read -p "Do you want to deploy contracts to the running node? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "🚀 Deploying contracts..."
        npm run deploy
        echo ""
        echo "✅ Setup complete!"
    fi
    exit 0
fi

echo ""
echo "🚀 Starting Hardhat node..."
echo ""

# Start Hardhat node in background
npx hardhat node > /tmp/hardhat.log 2>&1 &
HARDHAT_PID=$!

echo "Hardhat node started with PID: $HARDHAT_PID"
echo ""
echo "Waiting for node to initialize (5 seconds)..."
sleep 5

# Check if node is running
if ! curl -s -X POST -H "Content-Type: application/json" --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' http://localhost:8545 > /dev/null 2>&1; then
    echo ""
    echo "❌ Failed to connect to Hardhat node"
    echo "Check /tmp/hardhat.log for details"
    exit 1
fi

echo ""
echo "✅ Hardhat node is running on http://localhost:8545"
echo ""

# Deploy contracts
echo "🚀 Deploying contracts..."
npm run deploy

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║              Setup Complete!                          ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "Hardhat node is running in the background (PID: $HARDHAT_PID)"
echo ""
echo "To stop the node: kill $HARDHAT_PID"
echo ""
echo "Next steps:"
echo "1. Run the AI trading agent: python main.py"
echo "2. Monitor the dashboard: python -m agents.dashboard"
echo ""

# Save PID for later
echo $HARDHAT_PID > /tmp/hardhat.pid
