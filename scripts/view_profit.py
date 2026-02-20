#!/usr/bin/env python3
"""
View Total Profit from Database
Usage: python scripts/view_profit.py
"""

import sys
sys.path.insert(0, '/home/yeasir/projects/ai-exp')

from sqlalchemy import create_engine, text
from config.config import config

def view_profit():
    """View total profit from database"""
    try:
        engine = create_engine(config.database.database_url)
        
        with engine.connect() as conn:
            # Get total profit
            result = conn.execute(text("""
                SELECT stat_value, updated_at 
                FROM profit_stats 
                WHERE stat_key = 'total_profit'
            """))
            row = result.first()
            
            if row:
                total_profit = row.stat_value
                updated_at = row.updated_at
                
                print("╔═══════════════════════════════════════════════════════╗")
                print("║          AI TRADING BOT - PROFIT STATUS               ║")
                print("╠═══════════════════════════════════════════════════════╣")
                print(f"║  Total Profit:    ${total_profit:>14.6f}                  ║")
                print(f"║  Last Updated:    {updated_at}                  ║")
                print("╠═══════════════════════════════════════════════════════╣")
                
                # Get trade count
                result = conn.execute(text("""
                    SELECT COUNT(*) as count, SUM(pnl) as sum_pnl
                    FROM trade_history
                """))
                row = result.first()
                
                if row:
                    print(f"║  Total Trades:    {row.count:>12}                  ║")
                    if row.sum_pnl:
                        print(f"║  Trade P&L:       ${row.sum_pnl:>14.6f}                  ║")
                
                print("╠═══════════════════════════════════════════════════════╣")
                
                # Get today's profit
                result = conn.execute(text("""
                    SELECT SUM(pnl) as today_pnl
                    FROM trade_history
                    WHERE DATE(timestamp) = CURRENT_DATE
                """))
                row = result.first()
                
                if row and row.today_pnl:
                    print(f"║  Today's Profit:  ${row.today_pnl:>14.6f}                  ║")
                
                print("╚═══════════════════════════════════════════════════════╝")
                
                return total_profit
            else:
                print("❌ No profit data found in database")
                return 0.0
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0.0

if __name__ == "__main__":
    view_profit()
