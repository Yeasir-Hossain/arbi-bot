#!/bin/bash

# AI Trading System - Setup Script
# Automates initial setup process

set -e

echo "╔═══════════════════════════════════════════════════════╗"
echo "║     AI Trading System - Setup Script                  ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python version: $python_version${NC}"

# Check Node.js version
echo "Checking Node.js version..."
if command -v node &> /dev/null; then
    node_version=$(node --version)
    echo -e "${GREEN}✓ Node.js version: $node_version${NC}"
else
    echo -e "${YELLOW}⚠ Node.js not found. Install for blockchain features.${NC}"
fi

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Install blockchain dependencies
if command -v node &> /dev/null; then
    echo ""
    echo "Installing blockchain dependencies..."
    cd blockchain
    npm install
    cd ..
    echo -e "${GREEN}✓ Blockchain dependencies installed${NC}"
fi

# Create directories
echo ""
echo "Creating directories..."
mkdir -p logs data config logs/executions logs/alerts logs/signals logs/paper_trading logs/live_trading logs/emergency
echo -e "${GREEN}✓ Directories created${NC}"

# Setup environment file
echo ""
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit .env with your actual API keys!${NC}"
    echo ""
    echo "Required configuration:"
    echo "  1. ANTHROPIC_API_KEY - Your Anthropic API key"
    echo "  2. EXCHANGE_API_KEY - Exchange API key (testnet first!)"
    echo "  3. EXCHANGE_API_SECRET - Exchange API secret"
    echo "  4. WITHDRAW_WALLET_ADDRESS - Your wallet for profit withdrawal"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# Setup git ignore
if [ ! -f ".gitignore" ]; then
    echo "Creating .gitignore..."
    cat > .gitignore << 'EOF'
.env
.env.local
.secrets.key
.secrets.enc
config/contracts.json
*.key
*.pem
venv/
__pycache__/
*.pyc
logs/
data/
.DS_Store
EOF
    echo -e "${GREEN}✓ .gitignore created${NC}"
fi

# Summary
echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║              Setup Complete!                          ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys"
echo "2. (Optional) Start local blockchain: cd blockchain && ./start.sh"
echo "3. Run paper trading: python main.py --mode paper"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: Start with paper trading first!${NC}"
echo ""
