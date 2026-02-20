#!/usr/bin/env python3
"""
Database Initialization Script
Creates/updates database schema for AI Trading Bot
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from config.config import config

def init_database():
    """Initialize database schema"""
    print("╔═══════════════════════════════════════════════════════╗")
    print("║     AI Trading Bot - Database Initialization          ║")
    print("╚═══════════════════════════════════════════════════════╝")
    print()
    
    try:
        engine = create_engine(config.database.database_url)
        
        with engine.connect() as conn:
            # Test connection
            conn.execute(text("SELECT 1"))
            print("✅ Database connected")
            
            # Create bot_state table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS bot_state (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(50) UNIQUE NOT NULL,
                    value JSONB NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✅ bot_state table ready")
            
            # Create open_positions table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS open_positions (
                    id SERIAL PRIMARY KEY,
                    position_id VARCHAR(50) UNIQUE NOT NULL,
                    type VARCHAR(20) NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    pair VARCHAR(20) NOT NULL,
                    amount FLOAT NOT NULL,
                    entry_price FLOAT NOT NULL,
                    target_price FLOAT NOT NULL,
                    stop_price FLOAT NOT NULL,
                    data JSONB,
                    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sold BOOLEAN DEFAULT false,
                    closed_at TIMESTAMP
                )
            """))
            print("✅ open_positions table ready")
            
            # Create trade_history table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS trade_history (
                    id SERIAL PRIMARY KEY,
                    trade_type VARCHAR(20) NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    action VARCHAR(10) NOT NULL,
                    amount FLOAT NOT NULL,
                    price FLOAT NOT NULL,
                    pnl FLOAT,
                    pnl_percent FLOAT,
                    data JSONB,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✅ trade_history table ready")
            
            # Create profit_stats table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS profit_stats (
                    id SERIAL PRIMARY KEY,
                    stat_key VARCHAR(50) UNIQUE NOT NULL,
                    stat_value FLOAT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✅ profit_stats table ready")
            
            # Initialize default profit stats
            conn.execute(text("""
                INSERT INTO profit_stats (stat_key, stat_value)
                VALUES ('total_profit', 0.0)
                ON CONFLICT (stat_key) DO NOTHING
            """))
            
            conn.commit()
            
            print()
            print("╔═══════════════════════════════════════════════════════╗")
            print("║     ✅ Database Initialization Complete!              ║")
            print("╚═══════════════════════════════════════════════════════╝")
            print()
            print("Tables created:")
            print("  - bot_state (key-value config)")
            print("  - open_positions (active positions)")
            print("  - trade_history (all trades)")
            print("  - profit_stats (profit tracking)")
            print()
            
            return True
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def reset_database():
    """Reset database (truncate all tables)"""
    print("⚠️  RESETTING DATABASE...")
    print("⚠️  This will DELETE ALL DATA!")
    print()
    
    try:
        engine = create_engine(config.database.database_url)
        
        with engine.connect() as conn:
            # Truncate all tables
            conn.execute(text("TRUNCATE TABLE trade_history, open_positions, profit_stats, bot_state RESTART IDENTITY CASCADE"))
            conn.commit()
            
            print("✅ Database reset complete!")
            print()
            
            # Re-initialize
            return init_database()
            
    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'reset':
        confirm = input("Are you sure you want to RESET the database? (yes/no): ")
        if confirm.lower() == 'yes':
            reset_database()
        else:
            print("Reset cancelled")
    else:
        init_database()
