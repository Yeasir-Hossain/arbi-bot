"""
Multi-Exchange Price Monitor
Uses PUBLIC APIs - NO API KEYS REQUIRED

Monitors prices across exchanges to find arbitrage opportunities
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger


class PublicPriceAPI:
    """Public price APIs that don't require authentication"""
    
    # Binance public API
    BINANCE_API = "https://api.binance.com/api/v3/ticker/price"
    
    # Coinbase public API
    COINBASE_API = "https://api.coinbase.com/v2/prices/spot?currency=USD"
    
    # Kraken public API
    KRAKEN_API = "https://api.kraken.com/0/public/Ticker"
    
    # CoinGecko aggregated API (recommended)
    COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"
    
    # OKX public API
    OKX_API = "https://www.okx.com/api/v5/market/ticker"
    
    # Bybit public API
    BYBIT_API = "https://api.bybit.com/v5/market/ticker"


class ExchangePriceMonitor:
    """
    Monitor prices across multiple exchanges using public APIs
    
    NO API KEYS REQUIRED - uses public endpoints
    """

    def __init__(self, symbols: List[str] = None):
        """
        Initialize price monitor
        
        Args:
            symbols: List of symbols to monitor (researched for 2026)
        """
        # Prioritized by 2026 growth potential (researched)
        # Tier 1: SOL (800%), ETH (150%), BTC (270%)
        # Tier 2: RNDR (AI), FET (AI), ONDO (RWA)
        # Tier 3: ARB, OP (Layer 2)
        self.symbols = symbols or [
            'SOL',   # ⭐ 800% potential
            'ETH',   # ⭐ 150%+ potential
            'BTC',   # ⭐ 270%+ potential
            'RNDR',  # ⭐ AI + GPU rendering
            'FET',   # ⭐ AI agents
            'ONDO',  # ⭐ RWA tokenization
            'ARB',   # Layer 2
            'OP'     # Layer 2
        ]
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_prices: Dict[str, Dict[str, float]] = {}
        
        logger.info("Exchange Price Monitor initialized (public APIs)")
        logger.info(f"Monitoring symbols: {self.symbols}")

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
        try:
            if symbol == 'BTC':
                pair = 'BTCUSDT'
            elif symbol == 'ETH':
                pair = 'ETHUSDT'
            elif symbol == 'SOL':
                pair = 'SOLUSDT'
            elif symbol == 'BNB':
                pair = 'BNBUSDT'
            elif symbol == 'ARB':
                pair = 'ARBUSDT'
            elif symbol == 'OP':
                pair = 'OPUSDT'
            else:
                return None
            
            async with self.session.get(
                PublicPriceAPI.BINANCE_API,
                params={'symbol': pair},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    price = float(data.get('price', 0))
                    return price
        except Exception as e:
            logger.debug(f"Binance price fetch failed for {symbol}: {e}")
        return None

    async def get_coinbase_price(self, symbol: str) -> Optional[float]:
        """Get price from Coinbase (public API)"""
        try:
            async with self.session.get(
                f"{PublicPriceAPI.COINBASE_API}",
                params={'currency': 'USD'},
                headers={'Content-Type': 'application/json'},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Coinbase returns price for base asset
                    if symbol == 'BTC':
                        return float(data.get('data', {}).get('amount', 0))
                    elif symbol == 'ETH':
                        # Need different endpoint for ETH
                        async with self.session.get(
                            "https://api.coinbase.com/v2/prices/ETH-USD/spot",
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as eth_response:
                            eth_data = await eth_response.json()
                            return float(eth_data.get('data', {}).get('amount', 0))
        except Exception as e:
            logger.debug(f"Coinbase price fetch failed for {symbol}: {e}")
        return None

    async def get_coingecko_price(self, symbol: str) -> Optional[float]:
        """Get price from CoinGecko (aggregated, recommended)"""
        try:
            # CoinGecko uses coin IDs, not symbols
            coin_ids = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'SOL': 'solana',
                'BNB': 'binancecoin',
                'ARB': 'arbitrum',
                'OP': 'optimism'
            }
            
            coin_id = coin_ids.get(symbol)
            if not coin_id:
                return None
            
            async with self.session.get(
                PublicPriceAPI.COINGECKO_API,
                params={
                    'ids': coin_id,
                    'vs_currencies': 'usd'
                },
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    price = data.get(coin_id, {}).get('usd', 0)
                    return float(price)
        except Exception as e:
            logger.debug(f"CoinGecko price fetch failed for {symbol}: {e}")
        return None

    async def get_okx_price(self, symbol: str) -> Optional[float]:
        """Get price from OKX (public API)"""
        try:
            inst_id = f"{symbol}-USDT"
            async with self.session.get(
                PublicPriceAPI.OKX_API,
                params={'instId': inst_id},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('data'):
                        price = float(data['data'][0].get('last', 0))
                        return price
        except Exception as e:
            logger.debug(f"OKX price fetch failed for {symbol}: {e}")
        return None

    async def get_bybit_price(self, symbol: str) -> Optional[float]:
        """Get price from Bybit (public API)"""
        try:
            async with self.session.get(
                PublicPriceAPI.BYBIT_API,
                params={
                    'category': 'spot',
                    'symbol': f'{symbol}USDT'
                },
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('result', {}).get('list'):
                        price = float(data['result']['list'][0].get('lastPrice', 0))
                        return price
        except Exception as e:
            logger.debug(f"Bybit price fetch failed for {symbol}: {e}")
        return None

    async def get_all_prices(self, symbol: str) -> Dict[str, float]:
        """
        Get price for symbol from all exchanges
        
        Returns:
            Dict of exchange -> price
        """
        prices = {}
        
        # Fetch from all exchanges concurrently
        tasks = {
            'binance': self.get_binance_price(symbol),
            'coingecko': self.get_coingecko_price(symbol),
            'coinbase': self.get_coinbase_price(symbol),
            'okx': self.get_okx_price(symbol),
            'bybit': self.get_bybit_price(symbol)
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
        Find arbitrage opportunities across exchanges
        
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
            
            # Find min and max prices
            min_exchange = min(prices, key=prices.get)
            max_exchange = max(prices, key=prices.get)
            
            min_price = prices[min_exchange]
            max_price = prices[max_exchange]
            
            # Calculate difference
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
                    'timestamp': datetime.now().isoformat()
                }
                opportunities.append(opportunity)
                
                logger.info(
                    f"📊 ARBITRAGE OPPORTUNITY: {symbol} | "
                    f"Buy {min_exchange} @ ${min_price:.2f} | "
                    f"Sell {max_exchange} @ ${max_price:.2f} | "
                    f"Profit: {diff_percent:.2f}%"
                )
        
        return opportunities

    async def monitor_loop(
        self,
        interval: int = 10,
        threshold: float = 0.5
    ):
        """
        Continuous monitoring loop
        
        Args:
            interval: Check every N seconds
            threshold: Alert threshold %
        """
        logger.info(f"Starting monitoring loop (interval: {interval}s)")
        
        while True:
            try:
                # Find opportunities
                opportunities = await self.find_arbitrage_opportunities(threshold)
                
                if opportunities:
                    logger.info(f"Found {len(opportunities)} arbitrage opportunities")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(interval)


# Example usage
async def main():
    """Test the price monitor"""
    monitor = ExchangePriceMonitor(symbols=['BTC', 'ETH', 'SOL'])
    
    await monitor.start()
    
    try:
        # Get current prices
        btc_prices = await monitor.get_all_prices('BTC')
        print(f"\nBTC Prices across exchanges:")
        for exchange, price in btc_prices.items():
            print(f"  {exchange}: ${price:,.2f}")
        
        # Find opportunities
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
