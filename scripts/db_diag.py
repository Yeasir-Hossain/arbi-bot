#!/usr/bin/env python3
"""
Database Diagnostics for AI Trading Bot
Check database state, view trades, positions, and profit
"""

import sys
sys.path.insert(0, '/home/yeasir/projects/ai-exp')

from trading.state_manager import get_state_manager
from config.config import config

def show_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def main():
    show_header("AI TRADING BOT - DATABASE DIAGNOSTICS")
    
    try:
        sm = get_state_manager()
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        print("\nMake sure PostgreSQL is running:")
        print("  podman compose up -d postgres")
        return
    
    # Show capital
    show_header("CAPITAL ALLOCATION")
    capital = sm.get_capital()
    print(f"  Total Capital:     ${capital.get('total', 0):.2f}")
    print(f"  Arb Pool:          ${capital.get('arb_pool', 0):.2f}")
    print(f"  Arb Used:          ${capital.get('arb_used', 0):.2f}")
    print(f"  Arb Available:     ${capital.get('arb_pool', 0) - capital.get('arb_used', 0):.2f}")
    print(f"  Launch Pool:       ${capital.get('launch_pool', 0):.2f}")
    print(f"  Launch Used:       ${capital.get('launch_used', 0):.2f}")
    print(f"  Launch Available:  ${capital.get('launch_pool', 0) - capital.get('launch_used', 0):.2f}")
    
    # Show open positions
    show_header("OPEN POSITIONS")
    positions = sm.get_open_positions()
    if not positions:
        print("  No open positions")
    else:
        print(f"  Total Open: {len(positions)}")
        print()
        for i, pos in enumerate(positions[:10], 1):  # Show first 10
            print(f"  {i}. {pos.get('symbol')} {pos.get('pair')}")
            print(f"     Amount: {pos.get('amount')} @ ${pos.get('buy_price'):.2f}")
            print(f"     Target: ${pos.get('target_price'):.4f}")
            print(f"     Stop:   ${pos.get('stop_price'):.4f}")
            print()
        if len(positions) > 10:
            print(f"  ... and {len(positions) - 10} more")
    
    # Show profit stats
    show_header("PROFIT STATISTICS")
    profit_stats = sm.get_profit_stats()
    total_profit = profit_stats.get('total_profit', 0)
    if total_profit >= 0:
        print(f"  Total Profit:  +${total_profit:.6f}")
    else:
        print(f"  Total Profit:  ${total_profit:.6f}")
    
    # Show recent trades
    show_header("RECENT TRADES (Last 20)")
    trades = sm.get_trade_history(limit=20)
    if not trades:
        print("  No trades yet")
    else:
        print(f"  {'ID':<6} {'Type':<6} {'Symbol':<10} {'Action':<6} {'Amount':<12} {'Price':<12} {'P&L':<12}")
        print("  " + "-" * 70)
        for trade in trades:
            pnl = trade.get('pnl', 0)
            pnl_str = f"${pnl:+.4f}" if pnl != 0 else "-"
            print(f"  {trade.get('id', 0):<6} {trade.get('type', 'arb'):<6} {trade.get('symbol', 'N/A'):<10} {trade.get('action', 'N/A'):<6} {trade.get('amount', 0):<12.6f} ${trade.get('price', 0):<11.2f} {pnl_str:<12}")
    
    show_header("DIAGNOSTICS COMPLETE")
    print()
    print("Commands:")
    print("  python scripts/db_diag.py trades 50  - View last 50 trades")
    print("  python scripts/db_diag.py positions  - View all open positions")
    print("  python scripts/db_diag.py profit     - View profit stats")
    print()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        
        sm = get_state_manager()
        
        if cmd == 'trades':
            show_header(f"RECENT TRADES (Last {limit})")
            trades = sm.get_trade_history(limit=limit)
            for trade in trades:
                pnl = trade.get('pnl', 0)
                print(f"[{trade.get('timestamp', 'N/A')[:19]}] {trade.get('action')} {trade.get('symbol')} {trade.get('amount'):.6f} @ ${trade.get('price'):.2f} | P&L: ${pnl:+.4f}")
        
        elif cmd == 'positions':
            show_header("OPEN POSITIONS")
            positions = sm.get_open_positions()
            for pos in positions:
                print(f"{pos.get('symbol')} {pos.get('pair')}: {pos.get('amount')} @ ${pos.get('buy_price'):.2f} → ${pos.get('target_price'):.4f}")
        
        elif cmd == 'profit':
            show_header("PROFIT STATISTICS")
            profit_stats = sm.get_profit_stats()
            for key, value in profit_stats.items():
                print(f"  {key}: ${value:.6f}")
    else:
        main()
