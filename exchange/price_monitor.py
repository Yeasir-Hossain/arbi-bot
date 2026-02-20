"""
Multi-Exchange Price Monitor
Uses PUBLIC APIs - NO API KEYS REQUIRED

Monitors prices across exchanges to find arbitrage opportunities.
Includes per-source rate limiting to avoid 429 errors.

Working sources (verified from BD):
- Binance (200 OK)
- Coinbase (200 OK)
- Bybit (200 OK)
- KuCoin (200 OK)
- Kraken (200 OK)
- CoinGecko (batch, rate-limited)

Blocked: OKX (403 geo-blocked)
"""

import asyncio
import time
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger


class PublicPriceAPI:
    """Public price APIs that don't require authentication"""

    BINANCE_API = "https://api.binance.com/api/v3/ticker/price"
    COINBASE_API = "https://api.coinbase.com/v2/prices/{pair}/spot"
    COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"
    BYBIT_API = "https://api.bybit.com/v5/market/tickers"
    KUCOIN_API = "https://api.kucoin.com/api/v1/market/orderbook/level1"
    KRAKEN_API = "https://api.kraken.com/0/public/Ticker"


# Symbol → Binance pair mapping
BINANCE_PAIRS = {
    'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT', 'SOL': 'SOLUSDT',
    'BNB': 'BNBUSDT', 'ARB': 'ARBUSDT', 'OP': 'OPUSDT',
    'RNDR': 'RNDRUSDT', 'FET': 'FETUSDT', 'ONDO': 'ONDOUSDT',
}

# Symbol → CoinGecko ID mapping
COINGECKO_IDS = {
    'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana',
    'BNB': 'binancecoin', 'ARB': 'arbitrum', 'OP': 'optimism',
    'RNDR': 'render-token', 'FET': 'fetch-ai', 'ONDO': 'ondo-finance',
}

# Symbol → Coinbase pair mapping
COINBASE_PAIRS = {
    'BTC': 'BTC-USD', 'ETH': 'ETH-USD', 'SOL': 'SOL-USD',
    'ARB': 'ARB-USD', 'OP': 'OP-USD', 'RNDR': 'RNDR-USD',
    'FET': 'FET-USD', 'ONDO': 'ONDO-USD',
}

# Symbol → KuCoin pair mapping
KUCOIN_PAIRS = {
    'BTC': 'BTC-USDT', 'ETH': 'ETH-USDT', 'SOL': 'SOL-USDT',
    'BNB': 'BNB-USDT', 'ARB': 'ARB-USDT', 'OP': 'OP-USDT',
    'RNDR': 'RNDR-USDT', 'FET': 'FET-USDT', 'ONDO': 'ONDO-USDT',
}

# Symbol → Kraken pair mapping (Kraken uses weird pair names)
KRAKEN_PAIRS = {
    'BTC': 'XBTUSD', 'ETH': 'ETHUSD', 'SOL': 'SOLUSD',
    'ARB': 'ARBUSD', 'OP': 'OPUSD', 'FET': 'FETUSD',
    'ONDO': 'ONDOUSD',
}


class RateLimiter:
    """Simple per-source rate limiter based on minimum interval"""

    def __init__(self):
        self._last_request: Dict[str, float] = {}
        self._intervals = {
            'binance': 2.0,
            'coinbase': 2.0,
            'coingecko': 12.0,  # ~5 req/min — conservative for free tier
            'bybit': 2.0,
            'kucoin': 2.0,
            'kraken': 2.0,
        }

    async def wait(self, source: str):
        """Wait if needed to respect rate limit for source"""
        interval = self._intervals.get(source, 2.0)
        last = self._last_request.get(source, 0)
        elapsed = time.monotonic() - last
        if elapsed < interval:
            await asyncio.sleep(interval - elapsed)
        self._last_request[source] = time.monotonic()


class ExchangePriceMonitor:
    """
    Monitor prices across multiple exchanges using public APIs.
    NO API KEYS REQUIRED - uses public endpoints.
    """

    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or [
            'SOL', 'ETH', 'BTC', 'RNDR', 'FET', 'ONDO', 'ARB', 'OP'
        ]
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_prices: Dict[str, Dict[str, float]] = {}
        self._rate_limiter = RateLimiter()
        # Cache for CoinGecko batch results
        self._coingecko_cache: Dict[str, float] = {}
        self._coingecko_cache_time: float = 0

        logger.info("Exchange Price Monitor initialized (public APIs)")
        logger.info(f"Monitoring symbols: {self.symbols}")
        logger.info("Sources: Binance, Coinbase, Bybit, KuCoin, Kraken, CoinGecko")

    async def start(self):
        """Start the monitor"""
        self.session = aiohttp.ClientSession()
        logger.info("Price monitor started")

    async def stop(self):
        """Stop the monitor"""
        if self.session:
            await self.session.close()
            logger.info("Price monitor stopped")

    async def get_binance_price(self, symbol: str) -> Optional[float]:
        """Get price from Binance (public API)"""
        pair = BINANCE_PAIRS.get(symbol)
        if not pair:
            return None
        try:
            await self._rate_limiter.wait('binance')
            async with self.session.get(
                PublicPriceAPI.BINANCE_API,
                params={'symbol': pair},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data.get('price', 0))
        except Exception as e:
            logger.debug(f"Binance price fetch failed for {symbol}: {e}")
        return None

    async def get_coinbase_price(self, symbol: str) -> Optional[float]:
        """Get price from Coinbase (public API)"""
        pair = COINBASE_PAIRS.get(symbol)
        if not pair:
            return None
        try:
            await self._rate_limiter.wait('coinbase')
            url = PublicPriceAPI.COINBASE_API.format(pair=pair)
            async with self.session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data.get('data', {}).get('amount', 0))
        except Exception as e:
            logger.debug(f"Coinbase price fetch failed for {symbol}: {e}")
        return None

    async def _refresh_coingecko_batch(self):
        """Fetch all symbol prices from CoinGecko in a single batch request"""
        try:
            await self._rate_limiter.wait('coingecko')
            ids = ','.join(COINGECKO_IDS[s] for s in self.symbols if s in COINGECKO_IDS)
            async with self.session.get(
                PublicPriceAPI.COINGECKO_API,
                params={'ids': ids, 'vs_currencies': 'usd'},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    cache = {}
                    for symbol, coin_id in COINGECKO_IDS.items():
                        price = data.get(coin_id, {}).get('usd')
                        if price:
                            cache[symbol] = float(price)
                    self._coingecko_cache = cache
                    self._coingecko_cache_time = time.monotonic()
                elif response.status == 429:
                    logger.warning("CoinGecko rate limited (429)")
        except Exception as e:
            logger.debug(f"CoinGecko batch fetch failed: {e}")

    async def get_coingecko_price(self, symbol: str) -> Optional[float]:
        """Get price from CoinGecko (uses batch cache, refreshes every 12s)"""
        if symbol not in COINGECKO_IDS:
            return None
        if time.monotonic() - self._coingecko_cache_time > 12:
            await self._refresh_coingecko_batch()
        return self._coingecko_cache.get(symbol)

    async def get_bybit_price(self, symbol: str) -> Optional[float]:
        """Get price from Bybit (public API)"""
        try:
            await self._rate_limiter.wait('bybit')
            async with self.session.get(
                PublicPriceAPI.BYBIT_API,
                params={'category': 'spot', 'symbol': f'{symbol}USDT'},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result_list = data.get('result', {}).get('list', [])
                    if result_list:
                        return float(result_list[0].get('lastPrice', 0))
        except Exception as e:
            logger.debug(f"Bybit price fetch failed for {symbol}: {e}")
        return None

    async def get_kucoin_price(self, symbol: str) -> Optional[float]:
        """Get price from KuCoin (public API)"""
        pair = KUCOIN_PAIRS.get(symbol)
        if not pair:
            return None
        try:
            await self._rate_limiter.wait('kucoin')
            async with self.session.get(
                PublicPriceAPI.KUCOIN_API,
                params={'symbol': pair},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    price = data.get('data', {}).get('price')
                    if price:
                        return float(price)
        except Exception as e:
            logger.debug(f"KuCoin price fetch failed for {symbol}: {e}")
        return None

    async def get_kraken_price(self, symbol: str) -> Optional[float]:
        """Get price from Kraken (public API)"""
        pair = KRAKEN_PAIRS.get(symbol)
        if not pair:
            return None
        try:
            await self._rate_limiter.wait('kraken')
            async with self.session.get(
                PublicPriceAPI.KRAKEN_API,
                params={'pair': pair},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if not data.get('error'):
                        # Kraken returns data keyed by internal pair name
                        for pair_key, ticker in data.get('result', {}).items():
                            # 'c' = last trade closed [price, lot-volume]
                            return float(ticker['c'][0])
        except Exception as e:
            logger.debug(f"Kraken price fetch failed for {symbol}: {e}")
        return None

    async def get_all_prices(self, symbol: str) -> Dict[str, float]:
        """
        Get price for symbol from all exchanges.

        Returns:
            Dict of exchange -> price
        """
        prices = {}

        tasks = {
            'binance': self.get_binance_price(symbol),
            'coinbase': self.get_coinbase_price(symbol),
            'bybit': self.get_bybit_price(symbol),
            'kucoin': self.get_kucoin_price(symbol),
            'kraken': self.get_kraken_price(symbol),
            'coingecko': self.get_coingecko_price(symbol),
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for (exchange, _), result in zip(tasks.items(), results):
            if isinstance(result, (int, float)) and result > 0:
                prices[exchange] = result

        return prices

    async def find_arbitrage_opportunities(
        self,
        threshold_percent: float = 0.5
    ) -> List[Dict]:
        """
        Find arbitrage opportunities across exchanges.

        Args:
            threshold_percent: Minimum price difference % to report

        Returns:
            List of opportunities
        """
        opportunities = []

        for symbol in self.symbols:
            prices = await self.get_all_prices(symbol)

            if len(prices) < 2:
                continue

            min_exchange = min(prices, key=prices.get)
            max_exchange = max(prices, key=prices.get)

            min_price = prices[min_exchange]
            max_price = prices[max_exchange]

            diff_percent = ((max_price - min_price) / min_price) * 100

            if diff_percent >= threshold_percent:
                opportunity = {
                    'symbol': symbol,
                    'buy_exchange': min_exchange,
                    'buy_price': min_price,
                    'sell_exchange': max_exchange,
                    'sell_price': max_price,
                    'difference_percent': diff_percent,
                    'potential_profit_per_unit': max_price - min_price,
                    'all_prices': prices,
                    'timestamp': datetime.now().isoformat()
                }
                opportunities.append(opportunity)

                logger.info(
                    f"ARBITRAGE OPPORTUNITY: {symbol} | "
                    f"Buy {min_exchange} @ ${min_price:.2f} | "
                    f"Sell {max_exchange} @ ${max_price:.2f} | "
                    f"Profit: {diff_percent:.2f}%"
                )

        return opportunities


# Example usage
async def main():
    """Test the price monitor"""
    monitor = ExchangePriceMonitor(symbols=['BTC', 'ETH', 'SOL'])

    await monitor.start()

    try:
        btc_prices = await monitor.get_all_prices('BTC')
        print(f"\nBTC Prices across exchanges:")
        for exchange, price in btc_prices.items():
            print(f"  {exchange}: ${price:,.2f}")

        print("\nSearching for arbitrage opportunities...")
        opportunities = await monitor.find_arbitrage_opportunities(threshold=0.1)

        if opportunities:
            print(f"\nFound {len(opportunities)} opportunities:")
            for opp in opportunities:
                print(f"  {opp['symbol']}: Buy {opp['buy_exchange']} @ ${opp['buy_price']:.2f}, "
                      f"Sell {opp['sell_exchange']} @ ${opp['sell_price']:.2f} "
                      f"({opp['difference_percent']:.2f}%)")
        else:
            print("No significant opportunities found")

    finally:
        await monitor.stop()


if __name__ == "__main__":
    asyncio.run(main())
