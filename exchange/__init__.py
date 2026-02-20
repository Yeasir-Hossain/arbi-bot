"""Exchange Integration package"""

from exchange.client import ExchangeClient, OrderResult
from exchange.paper_trading import PaperExchange, PaperOrder, PaperPosition
from exchange.live_bridge import LiveTradingBridge
from exchange.price_monitor import ExchangePriceMonitor
from exchange.multi_exchange import MultiExchangeManager, create_exchange_manager

__all__ = [
    # Exchange Client
    "ExchangeClient",
    "OrderResult",
    
    # Paper Trading
    "PaperExchange",
    "PaperOrder",
    "PaperPosition",
    
    # Live Bridge
    "LiveTradingBridge",
    
    # Price Monitor (Public APIs - No Keys Needed)
    "ExchangePriceMonitor",
    
    # Multi-Exchange Manager
    "MultiExchangeManager",
    "create_exchange_manager",
]
