"""
State Manager for AI Trading Bot
Uses PostgreSQL for proper state persistence

Tables used:
- bot_state: Simple key-value config (capital, settings)
- open_positions: Active trading positions
- trade_history: All completed trades
- profit_stats: Profit tracking
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from loguru import logger
from config.config import config


class StateManager:
    """
    Manages bot state persistence using PostgreSQL
    """

    def __init__(self):
        """Initialize state manager"""
        self.engine = None
        self.use_db = False
        
        # Try PostgreSQL
        try:
            from sqlalchemy import create_engine, text
            self.engine = create_engine(config.database.database_url)
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self.use_db = True
            logger.info("✓ PostgreSQL connected for state persistence")
        except Exception as e:
            logger.error(f"PostgreSQL not available: {e}")
            raise RuntimeError("Database connection required")

        # Initialize state
        self.state = {
            'capital': {
                'total': 15.0,
                'arb_pool': 13.50,
                'launch_pool': 1.50,
                'arb_used': 0.0,
                'launch_used': 0.0
            }
        }

        logger.info("State Manager initialized")

    def load(self) -> bool:
        """Load state from database"""
        if not self.use_db:
            return False
        
        try:
            from sqlalchemy import text

            with self.engine.connect() as conn:
                # Load capital from bot_state
                result = conn.execute(text(
                    "SELECT value FROM bot_state WHERE key = 'capital'"
                ))
                row = result.first()
                if row:
                    self.state['capital'].update(row.value)

                # Load open positions from open_positions table
                result = conn.execute(text(
                    "SELECT * FROM open_positions WHERE sold = false"
                ))
                self.state['open_positions'] = [
                    {
                        'position_id': row.position_id,
                        'type': row.type,
                        'symbol': row.symbol,
                        'pair': row.pair,
                        'amount': row.amount,
                        'buy_price': row.entry_price,
                        'target_price': row.target_price,
                        'stop_price': row.stop_price,
                        'opened_at': row.opened_at.isoformat() if row.opened_at else None,
                        'data': row.data or {}
                    }
                    for row in result.fetchall()
                ]

                logger.info(f"✓ Loaded state from database")
                logger.info(f"  Open positions: {len(self.state['open_positions'])}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to load from database: {e}")
            return False

    def save(self) -> bool:
        """Save state to database"""
        if not self.use_db:
            return False
        
        try:
            from sqlalchemy import text
            import json

            with self.engine.connect() as conn:
                # Save capital to bot_state
                conn.execute(text("""
                    INSERT INTO bot_state (key, value, updated_at)
                    VALUES ('capital', :value, :time)
                    ON CONFLICT (key) DO UPDATE SET value = :value, updated_at = :time
                """), {'value': json.dumps(self.state['capital']), 'time': datetime.now()})

                conn.commit()

            logger.debug("✓ State saved to database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save to database: {e}")
            return False

    def add_position(self, position: Dict[str, Any]) -> None:
        """Add open position to database"""
        if not self.use_db:
            return
        
        try:
            from sqlalchemy import text
            import json

            # Generate position_id
            position_id = f"{position.get('symbol')}_{datetime.now().isoformat()}"
            
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO open_positions (
                        position_id, type, symbol, pair, amount,
                        entry_price, target_price, stop_price, data, opened_at
                    ) VALUES (
                        :position_id, :type, :symbol, :pair, :amount,
                        :entry_price, :target_price, :stop_price, :data, :opened_at
                    )
                """), {
                    'position_id': position_id,
                    'type': position.get('type', 'arbitrage'),
                    'symbol': position.get('symbol'),
                    'pair': position.get('pair'),
                    'amount': position.get('amount'),
                    'entry_price': position.get('buy_price'),
                    'target_price': position.get('target_price'),
                    'stop_price': position.get('stop_price'),
                    'data': json.dumps(position.get('data', {})),
                    'opened_at': datetime.now()
                })
                conn.commit()

            # Also keep in-memory for fast access
            position['position_id'] = position_id
            if 'open_positions' not in self.state:
                self.state['open_positions'] = []
            self.state['open_positions'].append(position)
            
            logger.info(f"💾 Position saved: {position.get('symbol')}")
            
        except Exception as e:
            logger.error(f"Failed to add position: {e}")

    def remove_position(self, position_id: str) -> bool:
        """Remove closed position from database"""
        if not self.use_db:
            return False
        
        try:
            from sqlalchemy import text

            with self.engine.connect() as conn:
                # Mark as sold instead of deleting (for history)
                conn.execute(text("""
                    UPDATE open_positions SET sold = true, closed_at = :time
                    WHERE position_id = :position_id
                """), {'position_id': position_id, 'time': datetime.now()})
                conn.commit()

            # Remove from in-memory
            if 'open_positions' in self.state:
                self.state['open_positions'] = [
                    p for p in self.state['open_positions']
                    if p.get('position_id') != position_id
                ]
            
            logger.info(f"✓ Position removed: {position_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove position: {e}")
            return False

    def add_trade(self, trade: Dict[str, Any]) -> None:
        """Save trade to history"""
        if not self.use_db:
            return
        
        try:
            from sqlalchemy import text
            import json

            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO trade_history (
                        trade_type, symbol, action, amount, price,
                        pnl, pnl_percent, data, timestamp
                    ) VALUES (
                        :trade_type, :symbol, :action, :amount, :price,
                        :pnl, :pnl_percent, :data, :timestamp
                    )
                """), {
                    'trade_type': trade.get('type', 'arb'),
                    'symbol': trade.get('symbol'),
                    'action': trade.get('action'),
                    'amount': trade.get('amount'),
                    'price': trade.get('price'),
                    'pnl': trade.get('pnl', 0),
                    'pnl_percent': trade.get('pnl_percent', 0),
                    'data': json.dumps(trade.get('data', {})),
                    'timestamp': datetime.now()
                })
                conn.commit()

            logger.debug(f"✓ Trade saved: {trade.get('action')} {trade.get('symbol')}")
            
        except Exception as e:
            logger.error(f"Failed to save trade: {e}")

    def update_profit(self, profit: float) -> None:
        """Update profit stats"""
        if not self.use_db:
            return
        
        try:
            from sqlalchemy import text

            with self.engine.connect() as conn:
                # Update or insert profit stats
                conn.execute(text("""
                    INSERT INTO profit_stats (stat_key, stat_value, updated_at)
                    VALUES ('total_profit', :profit, :time)
                    ON CONFLICT (stat_key) DO UPDATE 
                    SET stat_value = profit_stats.stat_value + :profit, updated_at = :time
                """), {'profit': profit, 'time': datetime.now()})
                conn.commit()

            logger.debug(f"✓ Profit updated: +${profit:.6f}")
            
        except Exception as e:
            logger.error(f"Failed to update profit: {e}")

    def update_capital(self, capital: Dict[str, float]) -> None:
        """Update capital allocation in database"""
        if not self.use_db:
            return
        
        try:
            from sqlalchemy import text
            import json

            with self.engine.connect() as conn:
                # Update capital in bot_state
                conn.execute(text("""
                    INSERT INTO bot_state (key, value, updated_at)
                    VALUES ('capital', :value, :time)
                    ON CONFLICT (key) DO UPDATE SET value = :value, updated_at = :time
                """), {'value': json.dumps(capital), 'time': datetime.now()})
                conn.commit()

            # Also update in-memory state
            self.state['capital'].update(capital)
            
            logger.debug(f"✓ Capital updated: total=${capital.get('total', 0):.2f}")
            
        except Exception as e:
            logger.error(f"Failed to update capital: {e}")

    def get_total_profit(self) -> float:
        """Get total profit from database"""
        if not self.use_db:
            return 0.0
        
        try:
            from sqlalchemy import text

            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT stat_value FROM profit_stats WHERE stat_key = 'total_profit'"
                ))
                row = result.first()
                return float(row.stat_value) if row else 0.0
                
        except Exception as e:
            logger.error(f"Failed to get total profit: {e}")
            return 0.0

    def get_capital(self) -> Dict[str, float]:
        """Get current capital allocation"""
        return self.state.get('capital', {
            'total': 15.0,
            'arb_pool': 13.50,
            'launch_pool': 1.50,
            'arb_used': 0.0,
            'launch_used': 0.0
        })

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        return self.state.get('open_positions', [])

    def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent trade history"""
        if not self.use_db:
            return []
        
        try:
            from sqlalchemy import text

            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT * FROM trade_history
                    ORDER BY timestamp DESC
                    LIMIT :limit
                """), {'limit': limit})
                
                return [
                    {
                        'id': row.id,
                        'type': row.trade_type,
                        'symbol': row.symbol,
                        'action': row.action,
                        'amount': row.amount,
                        'price': row.price,
                        'pnl': row.pnl,
                        'pnl_percent': row.pnl_percent,
                        'timestamp': row.timestamp.isoformat() if row.timestamp else None
                    }
                    for row in result.fetchall()
                ]
                
        except Exception as e:
            logger.error(f"Failed to get trade history: {e}")
            return []

    def get_profit_stats(self) -> Dict[str, float]:
        """Get profit statistics"""
        if not self.use_db:
            return {'total_profit': 0.0}
        
        try:
            from sqlalchemy import text

            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT stat_key, stat_value FROM profit_stats"
                ))
                
                return {row.stat_key: row.stat_value for row in result.fetchall()}
                
        except Exception as e:
            logger.error(f"Failed to get profit stats: {e}")
            return {}

    def save_initial_balance(self, balance: float) -> None:
        """Save initial wallet balance"""
        if not self.use_db:
            return
        
        try:
            from sqlalchemy import text

            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO profit_stats (stat_key, stat_value, updated_at)
                    VALUES ('initial_balance', :balance, :time)
                    ON CONFLICT (stat_key) DO NOTHING
                """), {'balance': balance, 'time': datetime.now()})
                conn.commit()

            logger.info(f"✓ Initial balance saved: ${balance:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to save initial balance: {e}")

    def get_initial_balance(self) -> float:
        """Get initial wallet balance"""
        if not self.use_db:
            return 15.0
        
        try:
            from sqlalchemy import text

            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT stat_value FROM profit_stats WHERE stat_key = 'initial_balance'"
                ))
                row = result.first()
                return float(row.stat_value) if row else 15.0
                
        except Exception as e:
            logger.error(f"Failed to get initial balance: {e}")
            return 15.0

    def get_position_count(self) -> int:
        """Get number of open positions"""
        positions = self.get_open_positions()
        return len(positions) if positions else 0


# Global instance
_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Get or create global state manager"""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
        _state_manager.load()
    return _state_manager
