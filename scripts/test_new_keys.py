#!/usr/bin/env python3
"""Test new API keys and record baseline"""

import sys
sys.path.insert(0, '/home/yeasir/projects/ai-exp')

from config.config import config
import asyncio
from exchange.client import ExchangeClient

print("=== TESTING NEW API KEYS ===")
print(f"API Key: {config.exchange.primary_api_key_plain[:20]}...")
print(f"API Secret: {config.exchange.primary_api_secret_plain[:20]}...")
print(f"Testnet: {config.exchange.primary_testnet}")
print("")

async def test():
    client = ExchangeClient(
        exchange_name="binance",
        api_key=config.exchange.primary_api_key_plain,
        api_secret=config.exchange.primary_api_secret_plain,
        testnet=True
    )
    
    if await client.connect():
        print("✅ Connected to Binance Testnet!")
        print("")
        
        # Get balances
        balances = {}
        for coin in ['USDT', 'BTC', 'ETH', 'SOL', 'BNB']:
            bal = await client.get_balance(coin)
            balances[coin] = bal
            print(f"{coin}: {bal:.6f}")
        
        await client.disconnect()
        
        # Save to file
        with open('initial_balances.txt', 'w') as f:
            f.write("=== BINANCE TESTNET BASELINE ===\n")
            f.write(f"Date: 2026-02-20\n")
            f.write("\n")
            for coin, bal in balances.items():
                f.write(f"{coin}: {bal:.6f}\n")
        
        print("")
        print("✅ Baseline saved to initial_balances.txt")
        
    else:
        print("❌ Connection failed")
        print("Check your API keys in .env file")

asyncio.run(test())
