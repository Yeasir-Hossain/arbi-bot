"""
Arbitrage Engine for Arbi-Bot
Mean-reversion strategy: buy on Binance when price is below cross-exchange average,
sell when price reverts to or above average.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger


class ArbitrageEngine:
    """
    Mean-reversion arbitrage engine.

    Strategy:
    - Get prices from multiple exchanges
    - Calculate cross-exchange average price
    - If Binance price is X% below average, buy on Binance
    - Set target to the average price (mean reversion)
    - Sell when Binance price reaches or exceeds the average
    """

    def __init__(
        self,
        capital_manager,
        binance_client,
        price_monitor,
        min_profit_threshold: float = 0.03,
        max_position_percent: float = 0.50,
        stop_loss_percent: float = 0.02
    ):
        self.capital = capital_manager
        self.binance = binance_client
        self.monitor = price_monitor

        self.min_profit_threshold = min_profit_threshold
        self.max_position_percent = max_position_percent
        self.stop_loss_percent = stop_loss_percent

        self.pairs = [
            'SOL/USDT', 'ETH/USDT', 'BTC/USDT',
            'RNDR/USDT', 'FET/USDT', 'ONDO/USDT',
            'ARB/USDT', 'OP/USDT'
        ]

        logger.info("Arbitrage Engine initialized (mean-reversion)")
        logger.info(f"  Min profit threshold: {min_profit_threshold:.2%}")
        logger.info(f"  Stop loss: {stop_loss_percent:.2%}")

    async def find_and_execute(self, pairs_to_scan: List[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find mean-reversion opportunity and execute.

        Buys on Binance when its price is significantly below the
        cross-exchange average. Target is the average price.
        """
        try:
            pairs = pairs_to_scan or self.pairs

            for pair in pairs:
                symbol = pair.split('/')[0]

                prices = await self.monitor.get_all_prices(symbol)

                if not prices or len(prices) < 2:
                    continue

                binance_price = prices.get('binance')
                if not binance_price:
                    continue

                # Calculate cross-exchange average (excluding Binance)
                other_prices = [p for ex, p in prices.items() if ex != 'binance']
                if not other_prices:
                    continue

                avg_price = sum(other_prices) / len(other_prices)

                # How far is Binance below the average?
                deviation = (avg_price - binance_price) / avg_price

                if deviation >= self.min_profit_threshold:
                    logger.info(f"SPREAD: {symbol} Binance=${binance_price:.2f} avg=${avg_price:.2f} dev={deviation:+.3%} ({len(other_prices)} src)")

                if deviation < self.min_profit_threshold:
                    continue

                # Binance is X% below average — buy opportunity
                position_size_usd = self.capital.get_arb_position_size()

                if position_size_usd < 10:
                    continue

                amount = position_size_usd / binance_price

                order = await self.binance.place_order(
                    symbol=pair,
                    side='buy',
                    amount=amount,
                    order_type='market'
                )

                if not order:
                    logger.warning(f"Order failed on Binance for {pair}")
                    continue

                target_price = avg_price
                stop_price = binance_price * (1 - self.stop_loss_percent)

                self.capital.arb_used += position_size_usd

                position = {
                    'type': 'arbitrage',
                    'symbol': symbol,
                    'pair': pair,
                    'buy_exchange': 'binance',
                    'buy_price': binance_price,
                    'target_price': target_price,
                    'stop_price': stop_price,
                    'amount': order.filled if hasattr(order, 'filled') else amount,
                    'entry_cost': position_size_usd,
                    'expected_profit': deviation,
                    'avg_price_at_entry': avg_price,
                    'prices_at_entry': prices,
                    'opened_at': datetime.now()
                }

                logger.info(f"ARB: {symbol} @ ${binance_price:.2f} (avg: ${avg_price:.2f}, dev: {deviation:.2%})")
                logger.info(f"   Amount: {position['amount']:.6f}")
                logger.info(f"   Target: ${target_price:.2f}")
                logger.info(f"   Stop: ${stop_price:.2f}")

                return position

            return None

        except Exception as e:
            logger.error(f"Arbitrage execution error: {e}")
            return None

    async def check_exit(self, position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if we should exit position"""
        try:
            current_price = await self.binance.get_price(position['pair'])

            if not current_price or current_price <= 0:
                return None

            # Check take profit (price reverted to or above target)
            if current_price >= position['target_price']:
                if position.get('sold'):
                    return None

                sell_order = await self.binance.place_order(
                    symbol=position['pair'],
                    side='sell',
                    amount=position['amount'],
                    order_type='market'
                )

                if sell_order and getattr(sell_order, 'status', None) == 'closed':
                    profit = (current_price - position['buy_price']) * position['amount']
                    profit_percent = profit / position['entry_cost']

                    logger.info(f"ARB TAKE PROFIT: {position['symbol']}")
                    logger.info(f"   Sold @ ${current_price:.2f}")
                    logger.info(f"   Profit: ${profit:.4f} ({profit_percent:.2%})")

                    position['sold'] = True

                    return {
                        'action': 'sell',
                        'profit': profit,
                        'profit_percent': profit_percent,
                        'exit_price': current_price
                    }
                else:
                    logger.warning(f"Sell order failed: {sell_order}")
                    fail_count = position.get('sell_failures', 0) + 1
                    position['sell_failures'] = fail_count
                    if fail_count >= 3:
                        logger.warning(f"Removing position after {fail_count} failed sell attempts: {position.get('symbol')}")
                        position['sold'] = True
                    return None

            # Check stop loss
            if current_price <= position['stop_price']:
                if position.get('sold'):
                    return None

                sell_order = await self.binance.place_order(
                    symbol=position['pair'],
                    side='sell',
                    amount=position['amount'],
                    order_type='market'
                )

                if sell_order and getattr(sell_order, 'status', None) == 'closed':
                    loss = (current_price - position['buy_price']) * position['amount']
                    loss_percent = loss / position.get('entry_cost', 1)

                    logger.warning(f"ARB STOP LOSS: {position['symbol']}")
                    logger.warning(f"   Sold @ ${current_price:.2f}")
                    logger.warning(f"   Loss: ${loss:.6f} ({loss_percent:.2%})")

                    position['sold'] = True

                    return {
                        'action': 'stop_loss',
                        'loss': loss,
                        'loss_percent': loss_percent,
                        'exit_price': current_price
                    }
                else:
                    logger.warning(f"Stop loss order failed: {sell_order}")
                    fail_count = position.get('sell_failures', 0) + 1
                    position['sell_failures'] = fail_count
                    if fail_count >= 3:
                        logger.warning(f"Removing position after {fail_count} failed stop-loss attempts: {position.get('symbol')}")
                        position['sold'] = True
                    return None

            return None

        except Exception as e:
            logger.error(f"Exit check error: {e}")
            return None

    async def get_opportunities(self) -> List[Dict[str, Any]]:
        """Get current mean-reversion opportunities"""
        opportunities = []

        for pair in self.pairs:
            symbol = pair.split('/')[0]
            prices = await self.monitor.get_all_prices(symbol)

            if not prices or 'binance' not in prices:
                continue

            binance_price = prices['binance']
            other_prices = [p for ex, p in prices.items() if ex != 'binance']
            if not other_prices:
                continue

            avg_price = sum(other_prices) / len(other_prices)
            deviation = (avg_price - binance_price) / avg_price

            if deviation > 0.001:
                opportunities.append({
                    'symbol': symbol,
                    'binance_price': binance_price,
                    'avg_price': avg_price,
                    'deviation': deviation,
                    'all_prices': prices
                })

        return sorted(opportunities, key=lambda x: x['deviation'], reverse=True)
