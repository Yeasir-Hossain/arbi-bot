#!/usr/bin/env python3
"""
Configuration Test Script
Verifies all .env variables load correctly into config
"""

import sys
sys.path.insert(0, '/home/yeasir/projects/ai-exp')

from config.config import config

def test_config():
    """Test all configuration values"""
    print("╔═══════════════════════════════════════════════════════╗")
    print("║     CONFIGURATION TEST                                ║")
    print("╚═══════════════════════════════════════════════════════╝")
    print()
    
    errors = []
    
    # Test Trading Config
    print("📊 TRADING CONFIGURATION:")
    print(f"  MAX_POSITION_SIZE:     {config.trading.max_position_size:.2f} ({config.trading.max_position_size*100:.0f}%)")
    print(f"  MAX_DAILY_TRADES:      {config.trading.max_daily_trades}")
    print(f"  DAILY_LOSS_LIMIT:      {config.trading.daily_loss_limit:.2f} ({config.trading.daily_loss_limit*100:.0f}%)")
    print(f"  STOP_LOSS_PERCENT:     {config.trading.stop_loss_percent:.2f} ({config.trading.stop_loss_percent*100:.0f}%)")
    print(f"  TAKE_PROFIT_PERCENT:   {config.trading.take_profit_percent:.2f} ({config.trading.take_profit_percent*100:.0f}%)")
    print(f"  MIN_CONFIDENCE:        {config.trading.min_confidence:.2f} ({config.trading.min_confidence*100:.0f}%)")
    print(f"  MIN_ARB_PROFIT:        {config.trading.min_arb_profit_percent:.2f} ({config.trading.min_arb_profit_percent*100:.0f}%)")
    print(f"  MULTI_EXCHANGE:        {config.trading.multi_exchange_trading}")
    print()
    
    # Validate values
    if config.trading.max_position_size > 1.0:
        errors.append(f"❌ MAX_POSITION_SIZE ({config.trading.max_position_size}) should be between 0 and 1")
    
    if config.trading.min_arb_profit_percent < 0.01:
        errors.append(f"⚠️  MIN_ARB_PROFIT ({config.trading.min_arb_profit_percent:.2f}) is very low - may cause too many trades")
    
    if config.trading.min_arb_profit_percent > 0.10:
        errors.append(f"⚠️  MIN_ARB_PROFIT ({config.trading.min_arb_profit_percent:.2f}) is very high - may miss opportunities")
    
    # Test Exchange Config
    print("💱 EXCHANGE CONFIGURATION:")
    print(f"  PRIMARY_EXCHANGE:      {config.exchange.primary_exchange}")
    print(f"  PRIMARY_TESTNET:       {config.exchange.primary_testnet}")
    print(f"  TRADING_PAIRS:         {', '.join(config.exchange.get_trading_pairs_list())}")
    print(f"  MONITOR_EXCHANGES:     {', '.join(config.exchange.get_monitor_exchanges_list())}")
    print()
    
    # Test Database Config
    print("🗄️  DATABASE CONFIGURATION:")
    print(f"  DATABASE_URL:          {config.database.database_url}")
    print()
    
    # Test Withdrawal Config
    print("💰 WITHDRAWAL CONFIGURATION:")
    print(f"  AUTO_WITHDRAW:         {config.trading.auto_withdraw_enabled}")
    print(f"  WITHDRAW_PERCENT:      {config.trading.withdraw_percentage:.0%}")
    print(f"  WITHDRAW_WALLET:       {config.trading.withdraw_wallet_address[:20]}...")
    print(f"  MIN_WITHDRAW:          ${config.trading.min_withdraw_threshold:.0f}")
    print()
    
    # Summary
    print("╔═══════════════════════════════════════════════════════╗")
    if errors:
        print("║     ⚠️  WARNINGS/ERRORS FOUND                         ║")
        print("╚═══════════════════════════════════════════════════════╝")
        for error in errors:
            print(f"  {error}")
    else:
        print("║     ✅ ALL CONFIGURATION VALUES VALID                 ║")
        print("╚═══════════════════════════════════════════════════════╝")
    
    print()
    return len(errors) == 0

if __name__ == "__main__":
    success = test_config()
    sys.exit(0 if success else 1)
