# AI Trading System

Autonomous AI-powered cryptocurrency trading system with multi-agent decision making, risk management, and live exchange integration.

## ⚠️ Important Warnings

**READ BEFORE USING:**

1. **Start with Paper Trading**: Always test with paper trading first
2. **Testnet Before Live**: Use exchange testnet before risking real money
3. **Never Trade More Than You Can Lose**: Cryptocurrency trading is extremely risky
4. **Monitor Constantly**: This is not a "set and forget" system
5. **Profit Withdrawal**: Configure auto-withdrawal to ensure AI survival (pay bills, API costs)

## Features

### Core Capabilities

- **Multi-Agent AI System**: 5 specialized AI agents (Mayor, Researcher, Trader, Risk Manager, Reporter)
- **Signal Validation**: Risk-based validation before any trade execution
- **Paper Trading**: Test strategies with virtual money
- **Live Trading**: Connect to 100+ exchanges via CCXT
- **Profit Withdrawal**: Auto-withdraw earnings to your wallet
- **Emergency Stop**: Automatic halt on adverse conditions

### Security Features

- Encrypted credential storage
- API key management
- Daily loss limits
- Position size limits
- Emergency stop mechanism
- Comprehensive audit logging

### Monitoring

- Real-time CLI dashboard
- Performance tracking
- Trade history
- Alert system (Telegram, Email)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AI TRADING SYSTEM                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐ │
│  │   AI Agents  │────►│   Signal     │────►│   Exchange   │ │
│  │  (Claude)    │     │   Validator  │     │  Connector   │ │
│  └──────────────┘     └──────────────┘     └──────────────┘ │
│         │                      │                      │      │
│         ▼                      ▼                      ▼      │
│  ┌──────────────────────────────────────────────────────────┐│
│  │              Monitoring & Security Layer                  ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Installation

```bash
# Clone/create project
cd ai-exp

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies (for Hardhat)
cd blockchain
npm install
cd ..
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
vim .env
```

Required configuration:
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `EXCHANGE_API_KEY`: Exchange API key (testnet first!)
- `EXCHANGE_API_SECRET`: Exchange API secret
- `WITHDRAW_WALLET_ADDRESS`: Your wallet for profit withdrawal

### 3. Start Trading

```bash
# Paper trading (recommended first)
python main.py --mode paper

# Testnet trading
python main.py --mode testnet

# Live trading (⚠️ real money)
python main.py --mode live
```

## Project Structure

```
ai-exp/
├── config/              # Configuration
│   ├── config.py        # Pydantic configuration
│   └── logging_config.py # Logging setup
├── agents/              # AI Agent Framework
│   ├── orchestrator.py  # Multi-agent manager
│   ├── roles.py         # Agent roles
│   ├── prompts.py       # System prompts
│   └── scheduler.py     # Task scheduler
├── blockchain/          # Local Blockchain
│   ├── contracts/       # Smart contracts
│   ├── scripts/         # Deployment scripts
│   └── web3_client.py   # Web3 client
├── bridge/              # Signal Validation
│   ├── signal_validator.py
│   └── risk_rules.py
├── exchange/            # Exchange Integration
│   ├── client.py        # CCXT client
│   ├── paper_trading.py # Paper trading
│   └── live_bridge.py   # Live trading
├── monitoring/          # Monitoring
│   ├── tracker.py       # Performance tracking
│   ├── dashboard.py     # CLI dashboard
│   └── alerts.py        # Alert system
├── security/            # Security
│   ├── encryption.py    # Credential encryption
│   └── emergency_stop.py # Emergency stop
├── main.py              # Main entry point
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## Trading Modes

### Paper Trading (Recommended First)

```bash
python main.py --mode paper --balance 10000
```

- Virtual money, real market data
- Test strategies risk-free
- No API keys required

### Testnet Trading

```bash
python main.py --mode testnet
```

- Real exchange, test money
- Requires testnet API keys
- Best for final testing

### Live Trading

```bash
python main.py --mode live
```

- ⚠️ **REAL MONEY** ⚠️
- Requires verified exchange account
- Start with small amounts

## Configuration Options

### Risk Limits

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MAX_POSITION_SIZE` | 0.1 (10%) | Max portfolio per trade |
| `MAX_DAILY_TRADES` | 10 | Max trades per day |
| `DAILY_LOSS_LIMIT` | 0.05 (5%) | Max daily loss |
| `MIN_CONFIDENCE` | 0.7 (70%) | Min AI confidence |
| `STOP_LOSS_PERCENT` | 0.05 (5%) | Auto stop loss |
| `TAKE_PROFIT_PERCENT` | 0.10 (10%) | Auto take profit |

### Profit Withdrawal

| Parameter | Default | Description |
|-----------|---------|-------------|
| `AUTO_WITHDRAW_ENABLED` | true | Enable auto withdrawal |
| `WITHDRAW_PERCENTAGE` | 0.5 (50%) | % of profits to withdraw |
| `WITHDRAW_WALLET_ADDRESS` | "" | Destination wallet |

## AI Agents

### Mayor
- Main coordinator
- Strategic decisions
- Final approval authority

### Researcher
- Market analysis
- Opportunity identification
- Data-driven insights

### Trader
- Trade execution
- Position management
- Entry/exit optimization

### Risk Manager
- Risk assessment
- Position limits
- Capital protection

### Reporter
- Performance tracking
- Reporting
- Continuous improvement

## Safety Features

### Emergency Stop

The system automatically stops trading when:
- Daily loss limit reached (5%)
- Maximum drawdown exceeded (10%)
- Abnormal trade loss detected
- System errors occur

Manual emergency stop:
```python
from security import get_emergency_stop
get_emergency_stop().trigger(reason=EmergencyReason.MANUAL, details="User requested")
```

### Signal Validation

Every AI signal is validated:
1. Confidence check (>70%)
2. Position size check (<10%)
3. Daily trade limit check (<10)
4. Daily loss check (<5%)
5. Portfolio exposure check (<50%)

## Monitoring

### CLI Dashboard

Real-time monitoring:
```bash
python -m monitoring.dashboard
```

Shows:
- Portfolio value
- Open positions
- P&L metrics
- System status

### Performance Reports

```python
from monitoring import PerformanceTracker

tracker = PerformanceTracker()
print(tracker.generate_report())
```

### Alerts

Configure alerts in `.env`:
```bash
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-password
```

## Local Blockchain (Development)

For testing AI strategies on a local DEX:

```bash
# Start Hardhat node
cd blockchain
./start.sh

# Or manually
npx hardhat node
npx hardhat run scripts/deploy.js --network localhost
```

## API Usage

### Basic Trading

```python
from exchange import PaperExchange

exchange = PaperExchange(initial_balance=10000)
await exchange.place_order(
    symbol='BTC/USDT',
    side='buy',
    amount=0.1
)
```

### AI Analysis

```python
from agents import AgentOrchestrator, AgentRole

orchestrator = AgentOrchestrator(api_key="your-key")
orchestrator.create_agent("researcher", AgentRole.RESEARCHER)

analysis = await orchestrator.send_message(
    "researcher",
    "Analyze BTC/USDT market conditions"
)
```

## Troubleshooting

### Common Issues

**"Cannot connect to blockchain"**
```bash
cd blockchain && npx hardhat node
```

**"No exchange credentials"**
- Check `.env` file
- Ensure `EXCHANGE_API_KEY` is set
- Verify secrets manager has credentials

**"Daily loss limit reached"**
- System halted for safety
- Reset next day or adjust limits in config

**"API rate limit exceeded"**
- Reduce trading frequency
- Check rate limiter settings
- Upgrade API plan if needed

## Security Best Practices

1. **Never commit `.env`** - Already in `.gitignore`
2. **Use encrypted secrets** - Secrets manager handles this
3. **Restrict API keys** - No withdrawal permissions
4. **Enable 2FA** - On all exchange accounts
5. **Regular audits** - Review trade logs daily
6. **Start small** - Test thoroughly before scaling

## Disclaimer

⚠️ **CRYPTOCURRENCY TRADING INVOLVES SUBSTANTIAL RISK**

This software is for educational purposes. The authors are not responsible for any financial losses. Always:
- Test thoroughly with paper trading
- Start with small amounts
- Never trade money you can't afford to lose
- Consult financial advisors
- Comply with local regulations

## License

MIT License - See LICENSE file for details.

## Support

For issues and questions:
1. Check this README
2. Review logs in `./logs/`
3. Check troubleshooting section

---

**Remember: The AI is a tool to assist your trading, not replace your judgment. Always monitor and maintain control.**
