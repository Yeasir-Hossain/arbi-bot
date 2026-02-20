"""
Exchange Client for AI Trading System
Uses CCXT library to connect to 100+ cryptocurrency exchanges
"""

import ccxt
import ccxt.async_support as ccxt_async
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
import asyncio
from dataclasses import dataclass

from config.config import config


@dataclass
class OrderResult:
    """Result of an order execution"""
    order_id: str
    status: str
    side: str
    amount: float
    filled: float
    price: float
    avg_price: float
    fee: float
    fee_currency: str
    timestamp: datetime
    raw: Dict[str, Any]


class ExchangeClient:
    """
    Exchange client using CCXT library
    
    Features:
    - Connect to 100+ exchanges (Binance, Coinbase, Kraken, etc.)
    - Market and limit orders
    - Balance queries
    - Order management
    - Testnet support
    """

    def __init__(
        self,
        exchange_name: str = "binance",
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = True,
        sandbox_mode: bool = True
    ):
        """
        Initialize exchange client
        
        Args:
            exchange_name: Exchange name (binance, coinbase, kraken, etc.)
            api_key: Exchange API key
            api_secret: Exchange API secret
            testnet: Use testnet/sandbox
            sandbox_mode: Enable sandbox mode
        """
        self.exchange_name = exchange_name
        self.testnet = testnet
        self.sandbox_mode = sandbox_mode
        
        # Get exchange class
        try:
            exchange_class = getattr(ccxt_async, exchange_name)
        except AttributeError:
            raise ValueError(f"Unknown exchange: {exchange_name}")
        
        # Initialize exchange
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'test': testnet
            }
        })
        
        # Enable sandbox mode if available
        if sandbox_mode and hasattr(self.exchange, 'set_sandbox_mode'):
            self.exchange.set_sandbox_mode(True)
            logger.info(f"Using {exchange_name} SANDBOX/TESTNET mode")
        elif testnet:
            logger.warning(f"Testnet requested but {exchange_name} may not support it")
        
        logger.info(f"Exchange Client initialized: {exchange_name}")

    async def connect(self) -> bool:
        """
        Connect to exchange and load markets
        
        Returns:
            True if connection successful
        """
        try:
            logger.info(f"Connecting to {self.exchange_name}...")
            await self.exchange.load_markets()
            logger.info(f"✅ Connected to {self.exchange_name}")
            logger.info(f"   Markets loaded: {len(self.exchange.markets)}")
            return True
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Close exchange connection"""
        try:
            await self.exchange.close()
            logger.info("Exchange connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")

    async def get_balance(self, currency: str = None) -> Dict[str, float]:
        """
        Get account balance
        
        Args:
            currency: Specific currency (None for all)
            
        Returns:
            Balance dict
        """
        try:
            balance = await self.exchange.fetch_balance()
            
            if currency:
                return balance.get(currency, {}).get('free', 0.0)
            
            # Return all free balances
            return {
                curr: data['free'] 
                for curr, data in balance.items() 
                if isinstance(data, dict) and 'free' in data
            }
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return {}

    async def get_price(self, symbol: str) -> float:
        """
        Get current price for trading pair
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            
        Returns:
            Current price
        """
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return ticker.get('last', 0.0)
        except Exception as e:
            logger.error(f"Error fetching price: {e}")
            return 0.0

    async def get_orderbook(self, symbol: str, limit: int = 10) -> Dict[str, List]:
        """
        Get order book
        
        Args:
            symbol: Trading pair
            limit: Depth limit
            
        Returns:
            Order book with bids and asks
        """
        try:
            orderbook = await self.exchange.fetch_order_book(symbol, limit)
            return {
                'bids': orderbook.get('bids', []),
                'asks': orderbook.get('asks', []),
                'timestamp': orderbook.get('timestamp')
            }
        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return {'bids': [], 'asks': []}

    async def place_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Optional[OrderResult]:
        """
        Place an order
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            side: 'buy' or 'sell'
            amount: Amount in base currency
            price: Price (required for limit orders)
            order_type: 'market' or 'limit'
            
        Returns:
            OrderResult or None if failed
        """
        try:
            logger.info(f"📦 Placing {order_type} {side} order: {amount} {symbol}")
            
            # Create order
            if order_type == "market":
                order = await self.exchange.create_market_order(
                    symbol=symbol,
                    side=side,
                    amount=amount
                )
            else:
                if price is None:
                    logger.error("Price required for limit order")
                    return None
                    
                order = await self.exchange.create_limit_order(
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    price=price
                )
            
            # Parse result
            result = self._parse_order(order)
            
            logger.info(f"✅ Order placed: {result.order_id}")
            logger.info(f"   Status: {result.status}")
            logger.info(f"   Amount: {result.amount}")
            logger.info(f"   Price: ${result.price}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Order failed: {e}")
            return None

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an order
        
        Args:
            order_id: Order ID
            symbol: Trading pair
            
        Returns:
            True if cancelled
        """
        try:
            await self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Order {order_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False

    async def get_order_status(self, order_id: str, symbol: str) -> Optional[OrderResult]:
        """
        Get order status
        
        Args:
            order_id: Order ID
            symbol: Trading pair
            
        Returns:
            OrderResult or None
        """
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            return self._parse_order(order)
        except Exception as e:
            logger.error(f"Error fetching order: {e}")
            return None

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResult]:
        """
        Get open orders
        
        Args:
            symbol: Trading pair (None for all)
            
        Returns:
            List of open orders
        """
        try:
            orders = await self.exchange.fetch_open_orders(symbol)
            return [self._parse_order(o) for o in orders]
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return []

    def _parse_order(self, order: Dict[str, Any]) -> OrderResult:
        """Parse raw order to OrderResult"""
        return OrderResult(
            order_id=order.get('id', ''),
            status=order.get('status', 'unknown'),
            side=order.get('side', ''),
            amount=order.get('amount', 0),
            filled=order.get('filled', 0),
            price=order.get('price', 0),
            avg_price=order.get('average', 0),
            fee=order.get('fee', {}).get('cost', 0) if order.get('fee') else 0,
            fee_currency=order.get('fee', {}).get('currency', '') if order.get('fee') else '',
            timestamp=datetime.fromtimestamp(order.get('timestamp', 0) / 1000),
            raw=order
        )

    async def withdraw(
        self,
        currency: str,
        amount: float,
        address: str,
        tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Withdraw funds from exchange
        
        ⚠️ CRITICAL: This sends real money!
        
        Args:
            currency: Currency to withdraw
            amount: Amount to withdraw
            address: Destination wallet address
            tag: Memo/tag for certain currencies
            
        Returns:
            Withdrawal info
        """
        logger.warning(f"💸 WITHDRAWAL INITIATED: {amount} {currency} to {address[:10]}...")
        
        try:
            result = await self.exchange.withdraw(
                code=currency,
                amount=amount,
                address=address,
                tag=tag
            )
            
            logger.warning(f"💸 Withdrawal successful: {result.get('id')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Withdrawal failed: {e}")
            raise

    def get_supported_exchanges() -> List[str]:
        """Get list of supported exchanges"""
        return list(ccxt.exchanges)


# Example usage
async def main():
    """Example exchange client usage"""
    from config import setup_logging
    setup_logging()
    
    # Initialize with testnet credentials
    client = ExchangeClient(
        exchange_name="binance",
        api_key="your-testnet-key",
        api_secret="your-testnet-secret",
        testnet=True
    )
    
    # Connect
    if await client.connect():
        # Get balance
        balance = await client.get_balance('USDT')
        logger.info(f"USDT Balance: {balance}")
        
        # Get price
        price = await client.get_price('BTC/USDT')
        logger.info(f"BTC Price: ${price:,.2f}")
        
        # Disconnect
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
