#!/bin/bash

# Quick .env setup helper
# Generates missing keys and helps configure the system

set -e

echo "╔═══════════════════════════════════════════════════════╗"
echo "║     AI Trading System - Environment Setup             ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo "✓ .env created"
else
    echo "✓ .env already exists"
fi

echo ""
echo "Generating security keys..."

# Generate encryption key if not set
ENCRYPTION_KEY=$(grep "^ENCRYPTION_KEY=" .env | cut -d'=' -f2)
if [ "$ENCRYPTION_KEY" = "your-fernet-encryption-key-here" ] || [ -z "$ENCRYPTION_KEY" ]; then
    NEW_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "CHANGE_ME")
    sed -i "s|^ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$NEW_KEY|" .env
    echo "✓ Generated new ENCRYPTION_KEY"
else
    echo "✓ ENCRYPTION_KEY already set"
fi

# Generate JWT secret if not set
JWT_SECRET=$(grep "^JWT_SECRET=" .env | cut -d'=' -f2)
if [ "$JWT_SECRET" = "your-random-jwt-secret-here" ] || [ -z "$JWT_SECRET" ]; then
    NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "CHANGE_ME")
    sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$NEW_SECRET|" .env
    echo "✓ Generated new JWT_SECRET"
else
    echo "✓ JWT_SECRET already set"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "Configuration Checklist:"
echo "═══════════════════════════════════════════════════════"
echo ""

# Check required values
check_var() {
    local var_name=$1
    local var_value=$(grep "^${var_name}=" .env | cut -d'=' -f2)
    
    if [ "$var_value" = "" ] || [[ "$var_value" == *"your-"* ]] || [[ "$var_value" == *"CHANGE_ME"* ]]; then
        echo "❌ $var_name - NOT CONFIGURED"
        return 1
    else
        echo "✓ $var_name - Configured"
        return 0
    fi
}

echo "AI API Keys:"
check_var "ANTHROPIC_API_KEY"
echo ""

echo "Exchange Configuration:"
check_var "PRIMARY_EXCHANGE"
check_var "PRIMARY_API_KEY"
check_var "PRIMARY_API_SECRET"
echo ""

echo "Trading Pairs:"
TRADING_PAIRS=$(grep "^TRADING_PAIRS=" .env | cut -d'=' -f2)
echo "  Current pairs: $TRADING_PAIRS"
echo ""

echo "Profit Withdrawal (CRITICAL):"
check_var "WITHDRAW_WALLET_ADDRESS"
echo ""

echo "═══════════════════════════════════════════════════════"
echo ""
echo "Next Steps:"
echo ""
echo "1. Get Anthropic API Key:"
echo "   → https://console.anthropic.com/"
echo ""
echo "2. Get Exchange API Keys (Testnet first!):"
echo "   → Binance Testnet: https://testnet.binance.vision/"
echo "   → Binance Futures Testnet: https://testnet.binancefuture.com/"
echo ""
echo "3. Set your wallet address for profit withdrawal:"
echo "   → Your MetaMask/Trust Wallet address"
echo ""
echo "4. Edit .env with your values:"
echo "   vim .env"
echo ""
echo "5. Start containers:"
echo "   podman compose up -d"
echo ""
echo "═══════════════════════════════════════════════════════"
