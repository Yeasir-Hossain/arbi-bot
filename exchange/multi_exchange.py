"""
Multi-Exchange Manager
Handles multiple exchanges (primary, secondary, tertiary)
Starts with just primary, expands when you add more keys
"""

from typing import Dict, List, Optional, Any
from loguru import logger
from config.config import config


class MultiExchangeManager:
    """
    Manage multiple exchange connections
    
    Features:
    - Primary exchange (required)
    - Secondary exchange (optional)
    - Tertiary exchange (optional)
    - Unified interface for all exchanges
    """

    def __init__(self):
        """Initialize exchange manager"""
        self.exchanges: Dict[str, Any] = {}
        self.primary_exchange: Optional[str] = None
        
        logger.info("Multi-Exchange Manager initialized")

    def add_exchange(
        self,
        name: str,
        api_key: str,
        api_secret: str,
        testnet: bool = True,
        is_primary: bool = False
    ) -> bool:
        """
        Add an exchange connection
        
        Args:
            name: Exchange name (binance, coinbase, kraken)
            api_key: API key
            api_secret: API secret
            testnet: Use testnet
            is_primary: Is this the primary exchange?
            
        Returns:
            True if successful
        """
        try:
            from exchange.client import ExchangeClient
            
            client = ExchangeClient(
                exchange_name=name,
                api_key=api_key,
                api_secret=api_secret,
                testnet=testnet
            )
            
            self.exchanges[name] = {
                'client': client,
                'testnet': testnet,
                'primary': is_primary
            }
            
            if is_primary:
                self.primary_exchange = name
            
            logger.info(f"Added exchange: {name} (primary: {is_primary})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add exchange {name}: {e}")
            return False

    def get_primary_exchange(self) -> Optional[str]:
        """Get primary exchange name"""
        return self.primary_exchange

    def get_primary_client(self) -> Optional[Any]:
        """Get primary exchange client"""
        if self.primary_exchange:
            return self.exchanges.get(self.primary_exchange, {}).get('client')
        return None

    def get_exchange_client(self, name: str) -> Optional[Any]:
        """Get client for specific exchange"""
        return self.exchanges.get(name, {}).get('client')

    def get_all_exchanges(self) -> List[str]:
        """Get list of all connected exchanges"""
        return list(self.exchanges.keys())

    def is_multi_exchange(self) -> bool:
        """Check if multiple exchanges are connected"""
        return len(self.exchanges) > 1

    async def connect_all(self) -> bool:
        """Connect to all configured exchanges"""
        success_count = 0
        
        for name, exchange_data in self.exchanges.items():
            client = exchange_data['client']
            if await client.connect():
                success_count += 1
                logger.info(f"✓ Connected to {name}")
            else:
                logger.warning(f"✗ Failed to connect to {name}")
        
        logger.info(f"Connected to {success_count}/{len(self.exchanges)} exchanges")
        return success_count > 0

    async def disconnect_all(self) -> None:
        """Disconnect from all exchanges"""
        for name, exchange_data in self.exchanges.items():
            client = exchange_data['client']
            await client.disconnect()
            logger.info(f"Disconnected from {name}")

    def get_status(self) -> Dict[str, Any]:
        """Get exchange manager status"""
        return {
            'exchanges': list(self.exchanges.keys()),
            'primary': self.primary_exchange,
            'multi_exchange': self.is_multi_exchange(),
            'count': len(self.exchanges)
        }


# Factory function to create manager from config
def create_exchange_manager() -> MultiExchangeManager:
    """
    Create exchange manager from configuration
    
    Returns:
        Configured MultiExchangeManager
    """
    manager = MultiExchangeManager()
    
    # Add primary exchange (required)
    if config.exchange.primary_exchange and config.exchange.primary_api_key:
        manager.add_exchange(
            name=config.exchange.primary_exchange,
            api_key=config.exchange.primary_api_key,
            api_secret=config.exchange.primary_api_secret,
            testnet=config.exchange.primary_testnet,
            is_primary=True
        )
    
    # Add secondary exchange (optional)
    if config.exchange.secondary_exchange and config.exchange.secondary_api_key:
        manager.add_exchange(
            name=config.exchange.secondary_exchange,
            api_key=config.exchange.secondary_api_key,
            api_secret=config.exchange.secondary_api_secret,
            testnet=config.exchange.secondary_testnet,
            is_primary=False
        )
    
    # Add tertiary exchange (optional)
    if config.exchange.tertiary_exchange and config.exchange.tertiary_api_key:
        manager.add_exchange(
            name=config.exchange.tertiary_exchange,
            api_key=config.exchange.tertiary_api_key,
            api_secret=config.exchange.tertiary_api_secret,
            testnet=config.exchange.tertiary_testnet,
            is_primary=False
        )
    
    return manager


__all__ = [
    "MultiExchangeManager",
    "create_exchange_manager"
]
