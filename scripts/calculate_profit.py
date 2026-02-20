#!/usr/bin/env python3
"""
Calculate profit by comparing current balance with baseline
"""

import sys
sys.path.insert(0, '/home/yeasir/projects/ai-exp')

from exchange.client import ExchangeClient
import asyncio
import json
from datetime import datetime

# Approximate prices (would fetch from API in production)
PRICES = {
    'BTC': 67000,
    'ETH': 1980,
    'SOL': 200,
    'BNB': 600
}

# Baseline from INITIAL_BALANCE_RECORD.md
BASELINE = {
    'USDT': 11572.66,
    'BTC': 0.981940,
    'ETH': 1.025400,
    'SOL': 0.030000
}

async def calculate_profit():
    print("╔═══════════════════════════════════════════════════════╗")
    print("║          PROFIT CALCULATOR                            ║")
    print("╚═══════════════════════════════════════════════════════╝")
    print("")
    
    try:
        from config.config import config
        client = ExchangeClient(
            exchange_name="binance",
            api_key=config.exchange.primary_api_key_plain,
            api_secret=config.exchange.primary_api_secret_plain,
            testnet=True
        )
        
        if await client.connect():
            # Get current balances
            current = {
                'USDT': await client.get_balance('USDT'),
                'BTC': await client.get_balance('BTC'),
                'ETH': await client.get_balance('ETH'),
                'SOL': await client.get_balance('SOL')
            }
            
            await client.disconnect()
            
            # Calculate totals
            baseline_total = sum(BASELINE[asset] * PRICES.get(asset, 1) for asset in BASELINE)
            current_total = sum(current[asset] * PRICES.get(asset, 1) for asset in current)
            profit = current_total - baseline_total
            
            print("📊 CURRENT BALANCES:")
            print(f"   USDT: ${current['USDT']:,.2f}")
            print(f"   BTC:  {current['BTC']:.6f} (≈ ${current['BTC'] * PRICES['BTC']:,.2f})")
            print(f"   ETH:  {current['ETH']:.6f} (≈ ${current['ETH'] * PRICES['ETH']:,.2f})")
            print(f"   SOL:  {current['SOL']:.6f} (≈ ${current['SOL'] * PRICES['SOL']:,.2f})")
            print("")
            print("📊 BASELINE (from record):")
            print(f"   Total: ${baseline_total:,.2f}")
            print("")
            print("📊 CURRENT TOTAL:")
            print(f"   Total: ${current_total:,.2f}")
            print("")
            print("💰 PROFIT/LOSS:")
            
            if profit >= 0:
                print(f"   ✅ PROFIT: +${profit:,.2f} ({profit/baseline_total*100:+.2f}%)")
            else:
                print(f"   ❌ LOSS: ${profit:,.2f} ({profit/baseline_total*100:+.2f}%)")
            
            print("")
            print("📝 Note: This is TESTNET (fake money)")
            print("   For REAL profit tracking, check bot's internal $15 tracking")
            
        else:
            print("❌ Failed to connect to Binance Testnet")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(calculate_profit())
