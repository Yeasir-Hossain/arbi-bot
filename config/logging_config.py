"""
Logging Configuration for AI Trading System
Uses loguru for powerful, modern logging
"""

import sys
from pathlib import Path
from loguru import logger
from config.config import config


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure logging for the entire system
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Remove default handler
    logger.remove()
    
    # Ensure log directory exists
    log_dir = Path(config.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Console handler with color
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # File handler - main log (rotates daily)
    logger.add(
        log_dir / "trading_{time:YYYY-MM-DD}.log",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="00:00",  # Rotate at midnight
        retention="30 days",  # Keep 30 days of logs
        compression="zip",  # Compress old logs
        backtrace=True,
        diagnose=True,
    )
    
    # File handler - errors only
    logger.add(
        log_dir / "errors_{time:YYYY-MM-DD}.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="00:00",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
    )
    
    # File handler - trades only
    logger.add(
        log_dir / "trades_{time:YYYY-MM-DD}.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
        rotation="00:00",
        retention="90 days",  # Keep trade logs longer
        filter=lambda record: "trade" in record["function"].lower() or 
                             "order" in record["message"].lower(),
    )
    
    logger.info("Logging system initialized")


def get_logger(name: str = __name__):
    """
    Get a logger instance with a specific name
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logger.bind(name=name)


# Custom logging context for trades
class TradeLogger:
    """Specialized logger for trade events"""
    
    def __init__(self):
        self.logger = logger
    
    def log_trade_signal(self, action: str, pair: str, confidence: float, reason: str):
        """Log a trading signal"""
        self.logger.info(
            f"📊 SIGNAL | {action} {pair} | Confidence: {confidence:.2%} | {reason}"
        )
    
    def log_order_placed(self, order_id: str, action: str, pair: str, 
                         amount: float, price: float):
        """Log an order placement"""
        self.logger.info(
            f"📦 ORDER PLACED | ID: {order_id} | {action} {amount:.6f} {pair} @ ${price:,.2f}"
        )
    
    def log_order_filled(self, order_id: str, action: str, pair: str,
                         amount: float, avg_price: float, total: float):
        """Log an order fill"""
        self.logger.info(
            f"✅ ORDER FILLED | ID: {order_id} | {action} {amount:.6f} {pair} | "
            f"Avg: ${avg_price:,.2f} | Total: ${total:,.2f}"
        )
    
    def log_profit_loss(self, pair: str, pnl: float, pnl_percent: float, 
                        realized: bool = True):
        """Log profit/loss"""
        status = "REALIZED" if realized else "UNREALIZED"
        emoji = "💰" if pnl > 0 else "📉"
        self.logger.info(
            f"{emoji} P&L {status} | {pair} | ${pnl:+,.2f} ({pnl_percent:+.2%})"
        )
    
    def log_withdrawal(self, currency: str, amount: float, address: str, tx_hash: str):
        """Log a withdrawal"""
        self.logger.warning(
            f"💸 WITHDRAWAL | {amount:.6f} {currency} → {address[:10]}...{address[-8:]} | "
            f"TX: {tx_hash}"
        )
    
    def log_risk_event(self, event_type: str, details: str):
        """Log a risk-related event"""
        self.logger.warning(f"⚠️ RISK | {event_type} | {details}")
    
    def log_emergency_stop(self, reason: str):
        """Log emergency stop activation"""
        self.logger.critical(f"🚨 EMERGENCY STOP | {reason}")


# Global trade logger instance
trade_logger = TradeLogger()


# Decorator for logging function calls
def log_function_call(func):
    """Decorator to log function calls"""
    from functools import wraps
    
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger.debug(f"→ Calling {func.__name__}")
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"← {func.__name__} returned")
            return result
        except Exception as e:
            logger.error(f"✗ {func.__name__} raised: {e}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger.debug(f"→ Calling {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"← {func.__name__} returned")
            return result
        except Exception as e:
            logger.error(f"✗ {func.__name__} raised: {e}")
            raise
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
