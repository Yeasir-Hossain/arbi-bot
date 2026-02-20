# ARBI-BOT — TODO

## Remaining Tasks

### Wire in Emergency Stop
- `security/emergency_stop.py` exists but is never called from main.py
- Should trigger on: daily loss limit hit, repeated order failures, manual kill signal

### Future: Activate Agents
- `agents/` has orchestrator/roles/scheduler stubs
- `bridge/` has signal_validator and risk_rules
- When ready: wire into trading loop for AI-driven decisions
- Will need `anthropic` package added back to requirements.txt

### Nice to Have
- [ ] Add position timeout (force-close positions open too long)
- [ ] Add daily P&L tracking with auto-stop if daily loss limit hit
- [ ] Write tests for arbitrage_engine and capital_manager
- [ ] Add proper retry logic for failed orders
