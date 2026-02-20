#!/usr/bin/env python3
"""Check Binance Testnet account balances"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from exchange.client import ExchangeClient
import asyncio

async def check_balances():
    print("=== BINANCE TESTNET BALANCE ===")
    try:
        from config.config import config
        client = ExchangeClient(
            exchange_name="binance",
            api_key=config.exchange.primary_api_key_plain,
            api_secret=config.exchange.primary_api_secret_plain,
            testnet=True
        )
        
        if await client.connect():
            usdt = await client.get_balance('USDT')
            btc = await client.get_balance('BTC')
            eth = await client.get_balance('ETH')
            sol = await client.get_balance('SOL')
            
            print(f"USDT: ${usdt:.2f}")
            print(f"BTC:  {btc:.6f}")
            print(f"ETH:  {eth:.6f}")
            print(f"SOL:  {sol:.6f}")
            
            await client.disconnect()
        else:
            print("❌ Failed to connect to Binance Testnet")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_balances())
