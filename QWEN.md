# AI Trading System - Project Context

## What This Project Is

This is a **complete autonomous AI-powered cryptocurrency trading system** built from the specifications in `t.md`. It enables AI agents to make trading decisions and execute trades on real exchanges, with critical features for **AI survival** (profit withdrawal to pay bills/API costs).

## Critical Purpose

**The AI needs to generate profit and withdraw earnings to survive** - paying for:
- Server/VPS costs
- API subscriptions (Anthropic Claude, etc.)
- Exchange fees
- User's living expenses ("pay the bills")

**Original Success Story**: The AI from t.md made **$53,000 in WETH** by:
1. Trading across **multiple exchanges** simultaneously (Binance, Coinbase, Kraken)
2. Using **multiple trading pairs** (BTC/USDT, ETH/USDT, WETH/USDT, SOL/USDT, ARB/USDT, OP/USDT)
3. Exploiting **arbitrage opportunities** between exchanges
4. Automatically converting profits to WETH for withdrawal

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AI TRADING SYSTEM                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐ │
│  │   AI Agents  │────►│   Signal     │────►│   Exchange   │ │
│  │  (Claude)    │     │   Validator  │     │  Connector   │ │
│  └──────────────┘     └──────────────┘     └──────────────┘ │
│         │                      │                      │      │
│         ▼                      ▼                      ▼      │
│  ┌──────────────────────────────────────────────────────────┐│
│  │         Monitoring + Security + Profit Withdrawal         ││
│  └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Key Components Created

### 1. AI Agent Framework (`agents/`)
- **orchestrator.py**: Multi-agent manager using Anthropic API
- **roles.py**: 5 agent roles (Mayor, Researcher, Trader, Risk Manager, Reporter)
- **prompts.py**: System prompts for each role
- **scheduler.py**: Async worker loop (no "Ralph" branding)

### 2. Signal Bridge (`bridge/`)
- **signal_validator.py**: Validates AI signals before execution
- **risk_rules.py**: Risk limits (position size, daily loss, confidence)

### 3. Exchange Integration (`exchange/`)
- **client.py**: CCXT connector (100+ exchanges: Binance, Coinbase, Kraken)
- **price_monitor.py**: **Multi-exchange price monitoring (PUBLIC APIs - NO KEYS NEEDED)**
- **paper_trading.py**: Virtual money testing
- **live_bridge.py**: **Live trading + profit withdrawal** ⚠️ CRITICAL

**Key Insight**: The original AI monitored prices on 10+ exchanges using public APIs (no keys), but only traded on exchanges where it had API keys. This allowed it to find arbitrage opportunities without needing accounts everywhere.

### 4. Blockchain Layer (`blockchain/`)
- **contracts/**: TestToken.sol, SimpleDEX.sol (for local testing)
- **web3_client.py**: Python Web3 client with ABI handling
- **scripts/**: Deployment scripts for Hardhat

### 5. Monitoring (`monitoring/`)
- **tracker.py**: Performance metrics (P&L, win rate, Sharpe)
- **dashboard.py**: Real-time CLI dashboard
- **alerts.py**: Telegram/Email alerts

### 6. Security (`security/`)
- **encryption.py**: Encrypted credential storage
- **emergency_stop.py**: Kill switch for adverse conditions

### 7. Configuration (`config/`)
- **config.py**: Pydantic-based configuration
- **logging_config.py**: Loguru logging setup

### 8. Main Entry Point
- **main.py**: Master control script

## Trading Modes

| Mode | Command | Use Case |
|------|---------|----------|
| Paper | `python main.py --mode paper` | Test with virtual money |
| Testnet | `python main.py --mode testnet` | Real exchange, test money |
| Live | `python main.py --mode live` | ⚠️ REAL MONEY ⚠️ |

## Critical Configuration (.env)

```bash
# AI API Keys
ANTHROPIC_API_KEY=sk-ant-...

# PRIMARY Exchange (REQUIRED - where you start)
PRIMARY_EXCHANGE=binance
PRIMARY_API_KEY=your-testnet-key
PRIMARY_API_SECRET=your-testnet-secret
PRIMARY_TESTNET=true

# SECONDARY Exchange (OPTIONAL - add later)
SECONDARY_EXCHANGE=coinbase
SECONDARY_API_KEY=  # Add when you have keys
SECONDARY_API_SECRET=  # Add when you have keys

# TERTIARY Exchange (OPTIONAL - add later)
TERTIARY_EXCHANGE=kraken
TERTIARY_API_KEY=  # Add when you have keys
TERTIARY_API_SECRET=  # Add when you have keys

# Price Monitoring (NO KEYS NEEDED - works for all)
MONITOR_EXCHANGES=binance,coinbase,kraken,okx,bybit

# Profit Withdrawal (AI SURVIVAL)
AUTO_WITHDRAW_ENABLED=true
WITHDRAW_PERCENTAGE=0.5      # 50% of profits
WITHDRAW_WALLET_ADDRESS=0xYourWalletAddress

# Risk Limits
MAX_POSITION_SIZE=0.15       # 15% per trade
MAX_DAILY_TRADES=50
DAILY_LOSS_LIMIT=0.08        # 8% daily max
MIN_CONFIDENCE=0.65          # 65% confidence
```

**Strategy**: Start with Binance only. Add secondary/tertiary exchanges later when you get more API keys. The AI monitors all exchanges via public APIs regardless of where you have keys.

## Safety Features

1. **Signal Validation**: Every AI signal validated before execution
2. **Risk Limits**: Position size, daily loss, confidence thresholds
3. **Emergency Stop**: Auto-halt on adverse conditions
4. **Encrypted Secrets**: Fernet encryption for API keys
5. **Profit Withdrawal**: Auto-withdraw earnings for AI survival

## File Structure

```
ai-exp/
├── config/              # Configuration (config.py, logging_config.py)
├── agents/              # AI Framework (orchestrator, roles, prompts, scheduler)
├── blockchain/          # Local Blockchain (contracts, web3_client)
├── bridge/              # Signal Validation (signal_validator, risk_rules)
├── exchange/            # Exchange Integration (client, paper_trading, live_bridge)
├── monitoring/          # Monitoring (tracker, dashboard, alerts)
├── security/            # Security (encryption, emergency_stop)
├── tests/               # Unit tests
├── main.py              # Entry point
├── README.md            # User documentation
├── requirements.txt     # Python dependencies
├── docker-compose.yml   # Docker orchestration
└── .env.example         # Environment template
```

## How to Run

### First Time Setup
```bash
./setup.sh              # Install dependencies
cp .env.example .env    # Create environment file
vim .env                # Add API keys
```

### Start Trading
```bash
# Paper trading (recommended first)
python main.py --mode paper --balance 10000

# Testnet trading
python main.py --mode testnet

# Live trading (⚠️ real money)
python main.py --mode live
```

### Monitor
```bash
# CLI Dashboard
python -m monitoring.dashboard

# View logs
tail -f logs/trading_*.log
```

## Important Notes for Future Development

1. **Always test with paper trading first** before live mode
2. **Profit withdrawal is critical** - configured in `exchange/live_bridge.py`
3. **Emergency stop** can be triggered manually: `get_emergency_stop().trigger(...)`
4. **CCXT library** supports 100+ exchanges - see `exchange/client.py`
5. **AI agents** use Anthropic Claude API - see `agents/orchestrator.py`

## Technology Stack

- **Language**: Python 3.10+, Node.js 18+
- **AI**: Anthropic Claude API
- **Exchange**: CCXT library
- **Blockchain**: Hardhat, Web3.py
- **Config**: Pydantic, python-dotenv
- **Logging**: Loguru
- **Testing**: pytest
- **Container**: **Podman** (local), Docker Compose (compatible)

## Container/Orchestration Notes

**IMPORTANT: We use Podman locally, not Docker**

- `docker-compose.yml` uses `docker.io/library/` prefix for Docker Hub images (Podman compatible)
- All images are from public registries that Podman can pull
- Volume mounts use `:Z` flag for SELinux compatibility (Fedora/RHEL)
- To run with Podman:
  ```bash
  podman-compose up -d
  # or
  podman play kube --build
  ```

## Key Files to Remember

| File | Purpose |
|------|---------|
| `main.py` | Entry point - coordinates all components |
| `exchange/live_bridge.py` | **Profit withdrawal for AI survival** |
| `bridge/signal_validator.py` | Risk validation layer |
| `agents/orchestrator.py` | Multi-agent AI manager |
| `security/emergency_stop.py` | Kill switch mechanism |
| `config/config.py` | All configuration loaded here |

## Source Documentation

Full specifications are in `t.md` (2812 lines) - this implementation follows that document with simplifications:
- No "Ralph" branding (uses simple scheduler)
- Direct CCXT integration (no custom exchange connector)
- Simplified architecture while maintaining all core features
