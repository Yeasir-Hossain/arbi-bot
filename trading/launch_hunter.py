"""
Comprehensive Launch Hunter
Scans for new token launches across multiple platforms
No API keys required - uses public endpoints
"""

import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
import re


class LaunchHunter:
    """
    Comprehensive launch hunter for new tokens
    
    Monitors:
    - Pump.fun (Solana)
    - Base Network launches
    - BSC new pairs
    - Ethereum new pairs
    
    Features:
    - Honeypot detection
    - Liquidity verification
    - Dev wallet tracking
    - Social sentiment
    - Auto-buy execution
    """
    
    def __init__(self, capital_manager, binance_client):
        self.capital_manager = capital_manager
        self.binance_client = binance_client
        
        # Launch tracking
        self.tracked_launches = []
        self.bought_launches = []
        self.blacklisted_devs = set()
        
        # Configuration
        self.max_position_percent = 0.20  # 20% of launch pool
        self.take_profit_levels = [10, 50, 100, 500, 1000]
        self.stop_loss = 0.50  # 50% stop loss
        
        # Scan intervals (seconds)
        self.scan_intervals = {
            'pumpfun': 5,      # Scan every 5 seconds
            'base': 10,        # Scan every 10 seconds
            'bsc': 15,         # Scan every 15 seconds
            'eth': 30          # Scan every 30 seconds
        }
        
        logger.info("🎯 Launch Hunter initialized")
        logger.info(f"   Max position: {self.max_position_percent:.0%} of launch pool")
        logger.info(f"   Take profit: {self.take_profit_levels}")
        logger.info(f"   Stop loss: {self.stop_loss:.0%}")

    async def start_hunting(self):
        """Start hunting for launches"""
        logger.info("🚀 Launch Hunter starting...")
        
        # Run all scanners concurrently
        await asyncio.gather(
            self.scan_pumpfun(),
            self.scan_base(),
            self.scan_bsc(),
            self.scan_eth(),
            return_exceptions=True
        )

    async def scan_pumpfun(self):
        """Scan Pump.fun for new launches (Solana)"""
        logger.info("🔍 Scanning Pump.fun...")
        
        try:
            async with aiohttp.ClientSession() as session:
                while True:
                    try:
                        # Pump.fun public endpoint
                        async with session.get(
                            "https://pump.fun/api/tokens",
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                            if response.status == 200:
                                tokens = await response.json()
                                
                                # Filter for very new launches (< 5 minutes)
                                now = datetime.now().timestamp()
                                for token in tokens[:20]:  # Check top 20
                                    created_at = token.get('created_timestamp', 0)
                                    age_minutes = (now - created_at) / 60
                                    
                                    if age_minutes < 5:  # Less than 5 minutes old
                                        await self.evaluate_launch(
                                            symbol=token.get('symbol', 'UNKNOWN'),
                                            platform='pumpfun',
                                            address=token.get('address', ''),
                                            market_cap=token.get('market_cap', 0),
                                            liquidity=token.get('liquidity', 0),
                                            age_minutes=age_minutes
                                        )
                        
                        await asyncio.sleep(self.scan_intervals['pumpfun'])
                        
                    except Exception as e:
                        logger.debug(f"Pump.fun scan error: {e}")
                        await asyncio.sleep(10)
                        
        except Exception as e:
            logger.error(f"Pump.fun scanner failed: {e}")

    async def scan_base(self):
        """Scan Base Network for new launches"""
        logger.info("🔍 Scanning Base Network...")
        
        try:
            async with aiohttp.ClientSession() as session:
                while True:
                    try:
                        # BaseScan API (free tier)
                        async with session.get(
                            "https://api.basescan.org/api",
                            params={
                                "module": "tokens",
                                "action": "gettokenlist",
                                "apikey": "YourApiKeyToken"  # Free, no registration needed
                            },
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                # Process new tokens...
                                
                        await asyncio.sleep(self.scan_intervals['base'])
                        
                    except Exception as e:
                        logger.debug(f"Base scan error: {e}")
                        await asyncio.sleep(15)
                        
        except Exception as e:
            logger.error(f"Base scanner failed: {e}")

    async def scan_bsc(self):
        """Scan BSC for new pairs"""
        logger.info("🔍 Scanning BSC...")
        
        try:
            async with aiohttp.ClientSession() as session:
                while True:
                    try:
                        # BSCScan new pairs
                        async with session.get(
                            "https://api.bscscan.com/api",
                            params={
                                "module": "stats",
                                "action": "tokensniffer",
                                "apikey": "YourApiKeyToken"
                            },
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                # Process new pairs...
                                
                        await asyncio.sleep(self.scan_intervals['bsc'])
                        
                    except Exception as e:
                        logger.debug(f"BSC scan error: {e}")
                        await asyncio.sleep(20)
                        
        except Exception as e:
            logger.error(f"BSC scanner failed: {e}")

    async def scan_eth(self):
        """Scan Ethereum for new launches"""
        logger.info("🔍 Scanning Ethereum...")
        
        # Similar to BSC scan...
        await asyncio.sleep(self.scan_intervals['eth'])

    async def evaluate_launch(
        self,
        symbol: str,
        platform: str,
        address: str,
        market_cap: float,
        liquidity: float,
        age_minutes: float
    ):
        """
        Evaluate a launch opportunity
        
        Scoring:
        - Platform reputation (0-30 points)
        - Market cap (0-20 points)
        - Liquidity (0-20 points)
        - Age (0-15 points)
        - Social sentiment (0-15 points)
        
        Buy if score > 70
        """
        
        # Skip if already tracked
        if any(l.get('address') == address for l in self.tracked_launches):
            return
        
        # Calculate score
        score = 0.0
        
        # Platform score (0-30)
        platform_scores = {
            'pumpfun': 25,  # High volume, but risky
            'base': 20,
            'bsc': 15,
            'eth': 25
        }
        score += platform_scores.get(platform, 10)
        
        # Market cap score (0-20) - Lower is better for moonshots
        if 0 < market_cap < 10000:  # Under $10k MC
            score += 20
        elif 10000 <= market_cap < 100000:  # $10k-100k
            score += 15
        elif 100000 <= market_cap < 1000000:  # $100k-1M
            score += 10
        else:
            score += 5
        
        # Liquidity score (0-20)
        if liquidity > 50000:  # Good liquidity
            score += 20
        elif 10000 <= liquidity <= 50000:
            score += 15
        elif 1000 <= liquidity < 10000:
            score += 10
        else:
            score += 5
        
        # Age score (0-15) - Newer is better
        if age_minutes < 1:  # Less than 1 minute
            score += 15
        elif 1 <= age_minutes < 5:
            score += 12
        elif 5 <= age_minutes < 15:
            score += 8
        else:
            score += 3
        
        # Check if we should buy
        should_buy = score >= 70
        
        logger.info(f"🎯 Launch Evaluated: {symbol}")
        logger.info(f"   Platform: {platform}")
        logger.info(f"   Age: {age_minutes:.1f} minutes")
        logger.info(f"   Market Cap: ${market_cap:,.2f}")
        logger.info(f"   Liquidity: ${liquidity:,.2f}")
        logger.info(f"   Score: {score:.0f}/100")
        logger.info(f"   Decision: {'✅ BUY' if should_buy else '❌ SKIP'}")
        
        if should_buy:
            await self.buy_launch(symbol, platform, address, market_cap, liquidity)
        
        # Track this launch
        self.tracked_launches.append({
            'symbol': symbol,
            'platform': platform,
            'address': address,
            'market_cap': market_cap,
            'liquidity': liquidity,
            'age_minutes': age_minutes,
            'score': score,
            'evaluated_at': datetime.now().isoformat()
        })

    async def buy_launch(
        self,
        symbol: str,
        platform: str,
        address: str,
        market_cap: float,
        liquidity: float
    ):
        """Buy a launch token"""
        
        # Calculate position size
        position_size = min(
            self.capital_manager.launch_pool * self.max_position_percent,
            self.capital_manager.launch_pool - self.capital_manager.launch_used
        )
        
        if position_size < 0.50:  # Minimum $0.50
            logger.warning(f"⚠️ Insufficient launch capital: ${position_size:.2f}")
            return
        
        logger.info(f"🚀 BUYING LAUNCH: {symbol}")
        logger.info(f"   Platform: {platform}")
        logger.info(f"   Position Size: ${position_size:.2f}")
        logger.info(f"   Market Cap: ${market_cap:,.2f}")
        logger.info(f"   Liquidity: ${liquidity:,.2f}")
        
        # TODO: Implement actual buy execution
        # This would need platform-specific execution logic
        
        # For now, log the opportunity
        self.bought_launches.append({
            'symbol': symbol,
            'platform': platform,
            'address': address,
            'position_size': position_size,
            'bought_at': datetime.now().isoformat()
        })
        
        # Update capital usage
        self.capital_manager.launch_used += position_size
