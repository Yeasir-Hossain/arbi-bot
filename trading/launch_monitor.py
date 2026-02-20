"""
Launch Monitor for Arbi-Bot
Tracks performance of launch positions and manages exits.
Works alongside LaunchHunter (which detects and buys new listings).
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger


class LaunchMonitor:
    """
    Token launch position manager.

    Tracks positions opened by LaunchHunter:
    - Trailing stop loss
    - Take profit at configurable levels (2x, 5x, 10x)
    - Stop loss at -50%
    """

    def __init__(
        self,
        capital_manager,
        binance_client,
        take_profit_levels: List[float] = None,
        stop_loss: float = 0.50
    ):
        self.capital = capital_manager
        self.binance = binance_client

        self.take_profit_levels = take_profit_levels or [2, 5, 10]
        self.stop_loss = stop_loss

        self.tracked_launches: List[Dict] = []

        logger.info("Launch Monitor initialized")
        logger.info(f"  Take profit levels: {self.take_profit_levels}x")
        logger.info(f"  Stop loss: {self.stop_loss:.0%}")

    async def get_upcoming_launches(self) -> List[Dict[str, Any]]:
        """Get upcoming launches — now handled by LaunchHunter"""
        return []

    async def evaluate_launch(self, launch: Dict[str, Any]) -> float:
        """Evaluate a launch (delegated to LaunchHunter for new listings)"""
        return 0.0

    async def buy_launch(self, launch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Buy handled by LaunchHunter — this is kept for interface compatibility"""
        return None

    async def track_position(self, position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Track launch position and manage exits.

        Returns exit signal if should exit, None otherwise.
        """
        try:
            current_price = await self.binance.get_price(position['pair'])

            if not current_price or current_price <= 0:
                return None

            # Update highest price seen
            if current_price > position.get('highest_price', 0):
                position['highest_price'] = current_price

            # Check take-profit levels
            for i, tp_level in enumerate(position.get('take_profit_levels', [])):
                tp_price = position['entry_price'] * tp_level

                if current_price >= tp_price:
                    sell_amount = position['amount'] / len(position['take_profit_levels'])

                    sell_order = await self.binance.place_order(
                        symbol=position['pair'],
                        side='sell',
                        amount=sell_amount,
                        order_type='market'
                    )

                    if sell_order:
                        profit = (current_price - position['entry_price']) * sell_amount
                        profit_multiple = current_price / position['entry_price']

                        logger.info(f"LAUNCH TAKE PROFIT @ {tp_level}x")
                        logger.info(f"   Sold {sell_amount:.2f} {position['symbol']} @ ${current_price:.6f}")
                        logger.info(f"   Profit: ${profit:.6f} ({profit_multiple:.1f}x)")

                        position['take_profit_levels'].pop(i)

                        return {
                            'action': 'take_profit',
                            'profit': profit,
                            'profit_multiple': profit_multiple,
                            'level': tp_level
                        }

            # Check stop loss
            if current_price <= position.get('stop_loss', 0):
                sell_order = await self.binance.place_order(
                    symbol=position['pair'],
                    side='sell',
                    amount=position['amount'],
                    order_type='market'
                )

                if sell_order:
                    loss = (current_price - position['entry_price']) * position['amount']
                    loss_percent = loss / position['entry_cost']

                    logger.warning(f"LAUNCH STOP LOSS")
                    logger.warning(f"   Sold @ ${current_price:.6f}")
                    logger.warning(f"   Loss: ${loss:.6f} ({loss_percent:.2%})")

                    return {
                        'action': 'stop_loss',
                        'loss': loss,
                        'loss_percent': loss_percent
                    }

            # Trail stop loss if up significantly
            if current_price >= position['entry_price'] * 5:
                new_stop = position['entry_price'] * 1.10
                if new_stop > position.get('stop_loss', 0):
                    position['stop_loss'] = new_stop

            if current_price >= position['entry_price'] * 20:
                new_stop = current_price * 0.70
                if new_stop > position.get('stop_loss', 0):
                    position['stop_loss'] = new_stop

            return None

        except Exception as e:
            logger.error(f"Position tracking error: {e}")
            return None

    async def monitor_launches(self):
        """Main monitoring loop (called periodically from main trading loop)"""
        pass
