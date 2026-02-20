"""
Launch Monitor for Hybrid Trading Bot
Monitors and trades new token launches
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
import aiohttp


class LaunchMonitor:
    """
    Token launch monitor and trader
    
    Strategy:
    - Monitor Binance Launchpad and DEX launches
    - Evaluate launch quality (score 0-1)
    - Buy high-confidence launches (>0.7 score)
    - Set take-profit at 10x, 50x, 100x, 500x
    - Set stop-loss at -50%
    - Trail stops as price increases
    """

    def __init__(
        self,
        capital_manager,
        binance_client,
        take_profit_levels: List[float] = None,
        stop_loss: float = 0.50
    ):
        """
        Initialize launch monitor
        
        Args:
            capital_manager: Capital manager instance
            binance_client: Binance exchange client
            take_profit_levels: Take profit multipliers [10, 50, 100, 500]
            stop_loss: Stop loss percentage (0.50 = -50%)
        """
        self.capital = capital_manager
        self.binance = binance_client
        
        self.take_profit_levels = take_profit_levels or [10, 50, 100, 500]
        self.stop_loss = stop_loss
        
        self.tracked_launches = []
        self.session: Optional[aiohttp.ClientSession] = None
        
        logger.info("Launch Monitor initialized")
        logger.info(f"  Take profit levels: {self.take_profit_levels}")
        logger.info(f"  Stop loss: {self.stop_loss:.0%}")

    async def start(self):
        """Start the monitor"""
        self.session = aiohttp.ClientSession()
        logger.info("Launch monitor started")

    async def stop(self):
        """Stop the monitor"""
        if self.session:
            await self.session.close()
            logger.info("Launch monitor stopped")

    async def get_upcoming_launches(self) -> List[Dict[str, Any]]:
        """
        Get upcoming token launches
        
        Returns:
            List of launch info dicts
        """
        launches = []
        
        try:
            # Check Binance Launchpad (public API)
            binance_launches = await self._fetch_binance_launches()
            launches.extend(binance_launches)
            
            # Check CoinList
            coinlist_launches = await self._fetch_coinlist_launches()
            launches.extend(coinlist_launches)
            
            # Mark already tracked
            for launch in launches:
                launch['tracked'] = any(
                    l.get('symbol') == launch.get('symbol') 
                    for l in self.tracked_launches
                )
            
            return launches
            
        except Exception as e:
            logger.error(f"Error fetching launches: {e}")
            return []

    async def _fetch_binance_launches(self) -> List[Dict[str, Any]]:
        """Fetch Binance Launchpad launches"""
        try:
            # Binance doesn't have a public launchpad API
            # This would need web scraping or manual entry
            # For now, return empty list
            
            # TODO: Implement web scraping or use manual launch entry
            return []
            
        except Exception as e:
            logger.debug(f"Binance launch fetch error: {e}")
            return []

    async def _fetch_coinlist_launches(self) -> List[Dict[str, Any]]:
        """Fetch CoinList launches"""
        try:
            if not self.session:
                return []
            
            async with self.session.get(
                'https://coinlist.co/api/v1/sales',
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Parse and return launches
                    # This is simplified - actual implementation needs proper parsing
                    return []
            
            return []
            
        except Exception as e:
            logger.debug(f"CoinList fetch error: {e}")
            return []

    async def evaluate_launch(self, launch: Dict[str, Any]) -> float:
        """
        Evaluate a token launch (score 0-1)
        
        Args:
            launch: Launch info dict
            
        Returns:
            Score from 0 to 1
        """
        score = 0.0
        
        # Factor 1: Platform (Binance = +0.3)
        if launch.get('platform') == 'binance':
            score += 0.3
        elif launch.get('platform') == 'coinlist':
            score += 0.2
        
        # Factor 2: Tokenomics (reasonable supply = +0.2)
        total_supply = launch.get('total_supply', 0)
        if 0 < total_supply < 1_000_000_000:
            score += 0.2
        
        # Factor 3: Use case (real utility = +0.2)
        use_case = launch.get('use_case', '').lower()
        if any(x in use_case for x in ['defi', 'gaming', 'infrastructure', 'layer1']):
            score += 0.2
        
        # Factor 4: Team (known team = +0.2)
        if launch.get('team_known', False):
            score += 0.2
        
        # Factor 5: Hype (social media buzz = +0.1)
        social_score = launch.get('social_score', 0)
        if social_score > 0.7:
            score += 0.1
        
        return score

    async def buy_launch(self, launch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Buy token at launch
        
        Args:
            launch: Launch info dict
            
        Returns:
            Position dict if successful, None otherwise
        """
        try:
            # Get position size
            position_size = self.capital.get_launch_position_size()
            
            if position_size < 0.50:
                logger.warning("Insufficient launch capital")
                return None
            
            # Get launch price
            launch_price = launch.get('launch_price', 0)
            
            if not launch_price or launch_price <= 0:
                logger.warning("Invalid launch price")
                return None
            
            # Calculate amount
            amount = position_size / launch_price
            
            # Place buy order
            symbol = launch.get('symbol', 'UNKNOWN')
            pair = f"{symbol}/USDT"

            order = await self.binance.place_order(
                symbol=pair,
                side='buy',
                amount=amount,
                order_type='market'
            )

            if not order:
                logger.warning(f"Launch buy order failed for {symbol}")
                return None

            # Update capital usage
            self.capital.launch_used += position_size

            # Create position record
            position = {
                'type': 'launch',
                'symbol': symbol,
                'pair': pair,
                'entry_price': launch_price,
                'amount': order.get('filled', amount),
                'entry_cost': position_size,
                'take_profit_levels': self.take_profit_levels.copy(),
                'stop_loss': launch_price * (1 - self.stop_loss),
                'opened_at': datetime.now(),
                'highest_price': launch_price
            }
            
            # Track this launch
            self.tracked_launches.append(launch)
            
            logger.info(f"🚀 LAUNCH: Bought {symbol}")
            logger.info(f"   Entry: ${launch_price:.6f}")
            logger.info(f"   Amount: {position['amount']:.2f}")
            logger.info(f"   Cost: ${position_size:.2f}")
            logger.info(f"   Stop Loss: ${position['stop_loss']:.6f}")
            logger.info(f"   Take Profits: {[f'{x}x' for x in self.take_profit_levels]}")
            
            return position
            
        except Exception as e:
            logger.error(f"Launch buy error: {e}")
            return None

    async def track_position(self, position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Track launch position and update stops
        
        Args:
            position: Position dict
            
        Returns:
            Exit signal if should exit, None otherwise
        """
        try:
            # Get current price
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
                    # Sell portion at this level
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

                        logger.info(f"💰 LAUNCH TAKE PROFIT @ {tp_level}x")
                        logger.info(f"   Sold {sell_amount:.2f} {position['symbol']} @ ${current_price:.6f}")
                        logger.info(f"   Profit: ${profit:.6f} ({profit_multiple:.1f}x)")

                        # Remove this take-profit level
                        position['take_profit_levels'].pop(i)

                        return {
                            'action': 'take_profit',
                            'profit': profit,
                            'profit_multiple': profit_multiple,
                            'level': tp_level
                        }

            # Check stop loss
            if current_price <= position.get('stop_loss', 0):
                # Sell all
                sell_order = await self.binance.place_order(
                    symbol=position['pair'],
                    side='sell',
                    amount=position['amount'],
                    order_type='market'
                )

                if sell_order:
                    loss = (current_price - position['entry_price']) * position['amount']
                    loss_percent = loss / position['entry_cost']

                    logger.warning(f"🛑 LAUNCH STOP LOSS")
                    logger.warning(f"   Sold @ ${current_price:.6f}")
                    logger.warning(f"   Loss: ${loss:.6f} ({loss_percent:.2%})")

                    return {
                        'action': 'stop_loss',
                        'loss': loss,
                        'loss_percent': loss_percent
                    }

            # Trail stop loss if up significantly
            if current_price >= position['entry_price'] * 5:
                # Move stop loss to breakeven + 10%
                new_stop = position['entry_price'] * 1.10
                
                if new_stop > position.get('stop_loss', 0):
                    position['stop_loss'] = new_stop
                    logger.info(f"   Trailing stop updated to ${new_stop:.6f}")
            
            if current_price >= position['entry_price'] * 20:
                # Aggressive trailing stop (lock in 70% of gains)
                new_stop = current_price * 0.70
                
                if new_stop > position.get('stop_loss', 0):
                    position['stop_loss'] = new_stop
                    logger.info(f"   Aggressive trailing stop: ${new_stop:.6f}")
            
            return None
            
        except Exception as e:
            logger.error(f"Position tracking error: {e}")
            return None

    async def monitor_launches(self):
        """Main monitoring loop (called periodically)"""
        # This is called from the main trading loop
        # Fetches and evaluates new launches
        pass
