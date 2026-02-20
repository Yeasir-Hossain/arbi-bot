# ARBI-BOT — Project Instructions

## What This Is

A crypto arbitrage trading bot. Starting capital: $15 on Binance testnet.
The ONLY goal is to **make real money**. Every decision, every line of code should serve that goal.

## Current Architecture

```
main.py                        → Entry point, trading loop (10s interval)
config/config.py               → Pydantic config from .env
config/logging_config.py       → Loguru logging setup
exchange/client.py             → CCXT Binance client (orders, balances)
exchange/price_monitor.py      → Public API price fetching (Binance, OKX, Bybit, CoinGecko, Coinbase)
exchange/multi_exchange.py     → Multi-exchange manager
trading/arbitrage_engine.py    → Core arbitrage logic (find spread, buy low, sell high)
trading/capital_manager.py     → 90% arb / 10% launch capital split
trading/state_manager.py       → PostgreSQL persistence (positions, trades, capital)
trading/launch_monitor.py      → Token launch monitoring
trading/launch_hunter.py       → New token launch scanner (Pump.fun, Base, BSC, ETH)
trading/smart_pair_selector.py → Auto-selects best performing pairs
monitoring/tracker.py          → Performance metrics (win rate, P&L, Sharpe)
monitoring/dashboard.py        → CLI dashboard
```

## How It Makes Money

1. **Arbitrage (90% of capital = $13.50)**: Monitor prices across 5+ exchanges via public APIs. When Binance price is lower than others, buy on Binance. Wait for price convergence, then sell. Target: 3%+ profit per trade.

2. **Token launches (10% of capital = $1.50)**: Scan for new token launches on Pump.fun, Base, BSC, Ethereum. Buy early on high-confidence launches. Moonshot potential.

## Trading Rules (from .env)

- Max position size: 20% of portfolio per trade
- Max daily trades: 50
- Daily loss limit: 10%
- Stop loss: 2%
- Take profit: 10%
- Min arbitrage profit: 3%
- Profit distribution: 50% reinvest, 30% withdraw (logged), 20% reserve

## How to Run

```bash
# Testnet
python main.py --mode testnet --capital 15

# Live
python main.py --mode live --capital 15
```

Requires PostgreSQL running on port 15432 (via docker-compose.yml / podman compose).

## Critical Rules for AI

### Money-First Mindset
- Every change must either: increase profit, reduce loss, or fix a bug that prevents trading
- Do NOT add features that don't directly help make money
- Do NOT over-engineer. Simple code that trades > elegant code that doesn't
- Do NOT add unnecessary abstractions, wrappers, or "future-proofing"
- Test on testnet before any live change

### Trading Safety
- NEVER remove or weaken stop-loss logic
- NEVER increase position sizes without explicit user approval
- NEVER change risk parameters (stop loss %, daily limits) without asking
- NEVER hardcode API keys — always use .env via config
- NEVER commit .env to git (it has real API keys)
- All profits stay on Binance — no withdrawal implementation needed for now
- Binance API keys handle all trading — that's sufficient

### Known Issues That MUST Be Fixed (see TODO.md)
1. **Arbitrage engine only works one-way** — buys on Binance when cheap vs other exchanges, sells on Binance too. Not true cross-exchange arb. Needs either multi-exchange API keys or strategy pivot.
2. **Launch hunter doesn't execute buys** — `launch_hunter.py:303` has `# TODO: Implement actual buy execution`. It only logs.
3. **Price monitor gets rate-limited** — No throttling on CoinGecko free tier. Will get 429 errors.
4. **Minimum order size issue** — 50% of $13.50 arb pool = $6.75, but Binance minimum is ~$10 for most pairs.

### Code Standards
- Python 3.10+, async/await throughout
- Use loguru for logging (already configured)
- Use ccxt for all exchange operations
- Use aiohttp for async HTTP (not requests)
- Use pydantic for config validation
- Keep the 10-second main loop — don't slow it down
- Error handling: log and continue, don't crash the loop

### What NOT to Touch Without Asking
- `.env` — contains live API keys
- `config/config.py` — risk parameters
- Position sizing logic in `capital_manager.py`
- Stop loss / take profit thresholds

### Modules Kept for Future (don't delete, don't use yet)
- `agents/` — AI agent system for future AI-driven trading decisions
- `bridge/` — Signal validation layer for when agents are activated
- `security/` — Emergency stop mechanism (should be wired in eventually)

### Dead Code to Clean Up (see TODO.md for full list)
- `blockchain/` — Remove (not needed)
- `web_dashboard.py` + `templates/` — Remove (CLI dashboard is enough)
- `exchange/paper_trading.py`, `exchange/live_bridge.py` — Remove
- `monitoring/alerts.py` — Remove
- Shell scripts in root — Remove
- 12+ unused packages in requirements.txt

## Database

PostgreSQL on `localhost:15432` (user: trading, pass: password, db: trading_db).
Tables: `bot_state`, `open_positions`, `trade_history`, `profit_stats`.
State manager creates tables automatically.

## Key Files Quick Reference

| When you need to... | Look at |
|---|---|
| Change trading pairs | `.env` → `TRADING_PAIRS` and `price_monitor.py` symbol mappings |
| Change risk limits | `.env` → `MAX_POSITION_SIZE`, `STOP_LOSS_PERCENT`, etc. |
| Fix arbitrage logic | `trading/arbitrage_engine.py` |
| Fix order execution | `exchange/client.py` |
| Fix price fetching | `exchange/price_monitor.py` |
| Change capital allocation | `trading/capital_manager.py` |
| Debug state/positions | `trading/state_manager.py` |
| See trading loop flow | `main.py:302-513` |

## Environment

- User uses **podman**, not docker
- Container tooling: `podman compose` for PostgreSQL
- No withdrawal needed — profits compound on Binance
- Testnet API keys are in `.env` (Binance testnet)
