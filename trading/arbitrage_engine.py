"""
Arbitrage Engine for Hybrid Trading Bot
Finds and executes arbitrage opportunities
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger


class ArbitrageEngine:
    """
    Arbitrage trading engine
    
    Strategy:
    - Monitor prices across exchanges
    - Find price differences > 0.3%
    - Execute on Binance (where we have API keys)
    - Wait for convergence, then sell
    """

    def __init__(
        self,
        capital_manager,
        binance_client,
        price_monitor,
        min_profit_threshold: float = 0.0001,  # 0.01% - VERY LOW for testing
        max_position_percent: float = 0.50,   # 50% of arb pool (increased for minimum order)
        stop_loss_percent: float = 0.02       # 2% stop loss
    ):
        """
        Initialize arbitrage engine
        
        Args:
            capital_manager: Capital manager instance
            binance_client: Binance exchange client
            price_monitor: Price monitor instance
            min_profit_threshold: Minimum profit % to execute
            max_position_percent: Max % of arb pool per trade
            stop_loss_percent: Stop loss percentage
        """
        self.capital = capital_manager
        self.binance = binance_client
        self.monitor = price_monitor
        
        self.min_profit_threshold = min_profit_threshold
        self.max_position_percent = max_position_percent
        self.stop_loss_percent = stop_loss_percent
        
        # Trading pairs to monitor (researched for 2026 potential)
        # Priority: SOL (800% potential), ETH (150%+), BTC (270%+), BNB (130%+)
        self.pairs = [
            'SOL/USDT',   # ⭐ Highest potential: $82 → $180-750
            'ETH/USDT',   # ⭐ Must-have: $1,980 → $3,500-8,000
            'BTC/USDT',   # ⭐ Blue-chip: $67k → $100k-250k
            'BNB/USDT',   # ⭐ Ecosystem: $300 → $500-800
            'ARB/USDT',   # Layer 2 growth
            'OP/USDT'     # Layer 2 growth
        ]
        
        logger.info("Arbitrage Engine initialized")
        logger.info(f"  Min profit threshold: {min_profit_threshold:.2%}")
        logger.info(f"  Stop loss: {stop_loss_percent:.2%}")

    async def find_and_execute(self, pairs_to_scan: List[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find arbitrage opportunity and execute
        
        Args:
            pairs_to_scan: List of pairs to scan (None = use default self.pairs)
            
        Returns:
            Position dict if executed, None otherwise
        """
        try:
            # Use provided pairs or default
            pairs = pairs_to_scan or self.pairs
            
            # Check each trading pair
            for pair in pairs:
                symbol = pair.split('/')[0]  # ETH from ETH/USDT
                
                # Get prices from all exchanges
                prices = await self.monitor.get_all_prices(symbol)
                
                if not prices or len(prices) < 2:
                    continue
                
                # Find best opportunity
                min_exchange = min(prices, key=prices.get)
                max_exchange = max(prices, key=prices.get)
                
                buy_price = prices[min_exchange]
                sell_price = prices[max_exchange]
                
                # Calculate profit percentage
                profit_percent = (sell_price - buy_price) / buy_price
                
                # Check if profitable enough
                if profit_percent < self.min_profit_threshold:
                    continue
                
                # We can only trade on Binance
                # So Binance must be the low exchange for us to buy
                if min_exchange != 'binance':
                    continue
                
                # Calculate position size
                position_size_usd = self.capital.get_arb_position_size()
                
                if position_size_usd < 1:  # Minimum $1
                    continue
                
                # Calculate amount to buy
                amount = position_size_usd / buy_price
                
                # Execute buy on Binance
                order = await self.binance.place_order(
                    symbol=pair,
                    side='buy',
                    amount=amount,
                    order_type='market'
                )

                if not order:
                    logger.warning(f"Order failed on Binance")
                    continue

                # Calculate target price (entry + minimum profit)
                target_price = buy_price * (1 + self.min_profit_threshold)

                # Update capital usage
                self.capital.arb_used += position_size_usd

                # Create position record
                position = {
                    'type': 'arbitrage',
                    'symbol': symbol,
                    'pair': pair,
                    'buy_exchange': min_exchange,
                    'buy_price': buy_price,
                    'target_price': target_price,
                    'stop_price': buy_price * (1 - self.stop_loss_percent),
                    'amount': order.filled if hasattr(order, 'filled') else amount,
                    'entry_cost': position_size_usd,
                    'expected_profit': profit_percent,
                    'opened_at': datetime.now()
                }
                
                logger.info(f"📊 ARB: {symbol} @ ${buy_price:.2f}")
                logger.info(f"   Exchange: {min_exchange}")
                logger.info(f"   Amount: {position['amount']:.6f}")
                logger.info(f"   Target: ${target_price:.2f}")
                logger.info(f"   Stop: ${position['stop_price']:.2f}")
                logger.info(f"   Expected: {profit_percent:.2%}")
                
                return position
            
            return None
            
        except Exception as e:
            logger.error(f"Arbitrage execution error: {e}")
            return None

    async def check_exit(self, position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check if we should exit position
        
        Args:
            position: Position dict
            
        Returns:
            Exit signal dict if should exit, None otherwise
        """
        try:
            # Get current price
            current_price = await self.binance.get_price(position['pair'])
            
            if not current_price or current_price <= 0:
                return None
            
            # Check take profit
            if current_price >= position['target_price']:
                # Check if already sold
                if position.get('sold'):
                    return None  # Already sold, skip
                    
                # Sell
                sell_order = await self.binance.place_order(
                    symbol=position['pair'],
                    side='sell',
                    amount=position['amount'],
                    order_type='market'
                )

                if sell_order and getattr(sell_order, 'status', None) == 'closed':
                    # Calculate profit
                    profit = (current_price - position['buy_price']) * position['amount']
                    profit_percent = profit / position['entry_cost']

                    logger.info(f"💰 ARB TAKE PROFIT")
                    logger.info(f"   Sold @ ${current_price:.2f}")
                    logger.info(f"   Profit: ${profit:.4f} ({profit_percent:.2%})")
                    
                    # Mark as sold
                    position['sold'] = True

                    return {
                        'action': 'sell',
                        'profit': profit,
                        'profit_percent': profit_percent,
                        'exit_price': current_price
                    }
                else:
                    # Order failed or still open
                    logger.warning(f"⚠️ Sell order failed: {sell_order}")
                    
                    # Mark position for removal after 3 failed attempts
                    fail_count = position.get('sell_failures', 0) + 1
                    position['sell_failures'] = fail_count
                    
                    if fail_count >= 3:
                        logger.warning(f"❌ Removing position after {fail_count} failed sell attempts: {position.get('symbol')}")
                        position['sold'] = True  # Mark as sold to stop trying
                    
                    return None

            # Check stop loss
            if current_price <= position['stop_price']:
                # Check if already sold
                if position.get('sold'):
                    return None  # Already sold, skip

                # Sell (stop loss)
                sell_order = await self.binance.place_order(
                    symbol=position['pair'],
                    side='sell',
                    amount=position['amount'],
                    order_type='market'
                )

                if sell_order and getattr(sell_order, 'status', None) == 'closed':
                    # Calculate loss
                    loss = (current_price - position['buy_price']) * position['amount']
                    loss_percent = loss / position.get('entry_cost', 1)

                    logger.warning(f"🛑 ARB STOP LOSS")
                    logger.warning(f"   Sold @ ${current_price:.2f}")
                    logger.warning(f"   Loss: ${loss:.6f} ({loss_percent:.2%})")

                    # Mark as sold
                    position['sold'] = True

                    return {
                        'action': 'stop_loss',
                        'loss': loss,
                        'loss_percent': loss_percent,
                        'exit_price': current_price
                    }
                else:
                    logger.warning(f"⚠️ Stop loss order failed: {sell_order}")
                    
                    # Mark for removal after 3 failures
                    fail_count = position.get('sell_failures', 0) + 1
                    position['sell_failures'] = fail_count
                    
                    if fail_count >= 3:
                        logger.warning(f"❌ Removing position after {fail_count} failed stop-loss attempts: {position.get('symbol')}")
                        position['sold'] = True
                    
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Exit check error: {e}")
            return None

    async def get_opportunities(self) -> List[Dict[str, Any]]:
        """
        Get current arbitrage opportunities
        
        Returns:
            List of opportunities
        """
        opportunities = []
        
        for pair in self.pairs:
            symbol = pair.split('/')[0]
            prices = await self.monitor.get_all_prices(symbol)
            
            if not prices:
                continue
            
            min_exchange = min(prices, key=prices.get)
            max_exchange = max(prices, key=prices.get)
            
            buy_price = prices[min_exchange]
            sell_price = prices[max_exchange]
            
            profit_percent = (sell_price - buy_price) / buy_price
            
            if profit_percent > 0.001:  # Show opportunities > 0.1%
                opportunities.append({
                    'symbol': symbol,
                    'buy_exchange': min_exchange,
                    'sell_exchange': max_exchange,
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'profit_percent': profit_percent
                })
        
        return sorted(opportunities, key=lambda x: x['profit_percent'], reverse=True)
