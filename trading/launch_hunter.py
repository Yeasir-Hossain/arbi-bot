"""
Binance Listing Sniper
Detects new trading pairs on Binance and auto-buys high-confidence listings.

Strategy:
- Periodically load Binance markets and compare against known set
- When a new USDT pair appears, evaluate it (volume, spread, pair type)
- Auto-buy with launch pool capital if criteria met
- Also checks Binance announcements for upcoming listings
"""

import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Set
from loguru import logger


class LaunchHunter:
    """
    Binance new listing detector and sniper.

    Detects new trading pairs appearing on Binance and buys early
    on high-confidence listings using launch pool capital.
    """

    def __init__(self, capital_manager, binance_client):
        self.capital_manager = capital_manager
        self.binance_client = binance_client

        # Known markets (populated on first scan)
        self.known_markets: Set[str] = set()
        self.first_scan_done = False

        # Launch tracking
        self.tracked_launches: List[Dict] = []
        self.bought_launches: List[Dict] = []

        # Configuration
        self.max_position_percent = 0.50  # 50% of launch pool per listing
        self.min_score = 0.6
        self.scan_interval = 60  # Check every 60 seconds

        logger.info("Launch Hunter initialized (Binance listing sniper)")

    async def start_hunting(self):
        """Start hunting for new Binance listings"""
        logger.info("Launch Hunter starting — scanning for new Binance listings...")

        while True:
            try:
                await self._scan_for_new_markets()
                await asyncio.sleep(self.scan_interval)
            except Exception as e:
                logger.debug(f"Launch hunter scan error: {e}")
                await asyncio.sleep(self.scan_interval)

    async def _scan_for_new_markets(self):
        """Compare current Binance markets against known set"""
        try:
            exchange = self.binance_client.exchange
            if not exchange:
                return

            await exchange.load_markets(reload=True)
            current_markets = set(exchange.markets.keys())

            if not self.first_scan_done:
                # First scan — just populate known markets
                self.known_markets = current_markets
                self.first_scan_done = True
                logger.info(f"Launch Hunter: indexed {len(self.known_markets)} existing markets")
                return

            # Find new markets
            new_markets = current_markets - self.known_markets
            self.known_markets = current_markets

            if not new_markets:
                return

            # Filter for USDT pairs only
            new_usdt_pairs = [m for m in new_markets if m.endswith('/USDT')]

            if new_usdt_pairs:
                logger.info(f"NEW LISTINGS DETECTED: {new_usdt_pairs}")

            for pair in new_usdt_pairs:
                await self._evaluate_and_buy(pair)

        except Exception as e:
            logger.debug(f"Market scan error: {e}")

    async def _evaluate_and_buy(self, pair: str):
        """Evaluate a new listing and buy if score is high enough"""
        symbol = pair.split('/')[0]

        # Skip if already tracked
        if any(l.get('pair') == pair for l in self.tracked_launches):
            return

        score = await self.evaluate_launch({'pair': pair, 'symbol': symbol})

        launch_info = {
            'pair': pair,
            'symbol': symbol,
            'score': score,
            'detected_at': datetime.now().isoformat()
        }
        self.tracked_launches.append(launch_info)

        if score >= self.min_score:
            logger.info(f"NEW LISTING BUY: {pair} (score: {score:.2f})")
            await self.buy_launch(launch_info)
        else:
            logger.info(f"New listing skipped: {pair} (score: {score:.2f})")

    async def evaluate_launch(self, launch: Dict) -> float:
        """
        Evaluate a new Binance listing.

        Scoring (0-1):
        - Is it a USDT spot pair? (+0.3)
        - Can we fetch a price? (+0.2)
        - Market info looks healthy? (+0.2)
        - Not a leveraged/fan token? (+0.3)

        Returns:
            Score from 0 to 1
        """
        pair = launch.get('pair', '')
        symbol = launch.get('symbol', '')
        score = 0.0

        # USDT pair
        if pair.endswith('/USDT'):
            score += 0.3

        # Not a leveraged token or fan token
        bad_suffixes = ['UP', 'DOWN', 'BULL', 'BEAR', '3L', '3S']
        if not any(symbol.endswith(s) for s in bad_suffixes):
            score += 0.3

        # Try to get price (confirms it's tradeable)
        try:
            price = await self.binance_client.get_price(pair)
            if price and price > 0:
                score += 0.2
        except Exception:
            pass

        # Check market info
        try:
            exchange = self.binance_client.exchange
            if exchange and pair in exchange.markets:
                market = exchange.markets[pair]
                if market.get('active', False) and market.get('spot', False):
                    score += 0.2
        except Exception:
            pass

        return score

    async def buy_launch(self, launch: Dict) -> Optional[Dict]:
        """Buy a new Binance listing with launch pool capital"""
        pair = launch.get('pair', '')
        symbol = launch.get('symbol', '')

        # Calculate position size
        available = self.capital_manager.launch_pool - self.capital_manager.launch_used
        position_size = min(
            self.capital_manager.launch_pool * self.max_position_percent,
            available
        )

        if position_size < 0.50:
            logger.warning(f"Insufficient launch capital: ${position_size:.2f}")
            return None

        try:
            # Get current price
            price = await self.binance_client.get_price(pair)
            if not price or price <= 0:
                logger.warning(f"Cannot get price for {pair}")
                return None

            amount = position_size / price

            order = await self.binance_client.place_order(
                symbol=pair,
                side='buy',
                amount=amount,
                order_type='market'
            )

            if not order:
                logger.warning(f"Buy order failed for {pair}")
                return None

            self.capital_manager.launch_used += position_size

            position = {
                'type': 'launch',
                'symbol': symbol,
                'pair': pair,
                'entry_price': price,
                'amount': order.filled if hasattr(order, 'filled') else amount,
                'entry_cost': position_size,
                'take_profit_levels': [2, 5, 10],  # 2x, 5x, 10x
                'stop_loss': price * 0.50,  # 50% stop loss
                'opened_at': datetime.now(),
                'highest_price': price
            }

            self.bought_launches.append({
                'pair': pair,
                'symbol': symbol,
                'position_size': position_size,
                'price': price,
                'bought_at': datetime.now().isoformat()
            })

            logger.info(f"LAUNCH BUY: {symbol}")
            logger.info(f"   Price: ${price:.6f}")
            logger.info(f"   Amount: {position['amount']:.6f}")
            logger.info(f"   Cost: ${position_size:.2f}")

            return position

        except Exception as e:
            logger.error(f"Launch buy error for {pair}: {e}")
            return None

    async def scan_all_platforms(self) -> List[Dict]:
        """
        Scan for new listings (called from main loop).
        Returns list of new launches found since last call.
        """
        try:
            exchange = self.binance_client.exchange
            if not exchange:
                return []

            await exchange.load_markets(reload=True)
            current_markets = set(exchange.markets.keys())

            if not self.first_scan_done:
                self.known_markets = current_markets
                self.first_scan_done = True
                return []

            new_markets = current_markets - self.known_markets
            self.known_markets = current_markets

            new_usdt_pairs = [m for m in new_markets if m.endswith('/USDT')]

            results = []
            for pair in new_usdt_pairs:
                symbol = pair.split('/')[0]
                results.append({
                    'pair': pair,
                    'symbol': symbol,
                    'address': pair,  # Use pair as unique ID
                    'detected_at': datetime.now().isoformat()
                })

            return results

        except Exception as e:
            logger.debug(f"scan_all_platforms error: {e}")
            return []
