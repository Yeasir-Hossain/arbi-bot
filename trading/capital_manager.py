"""
Capital Manager for Hybrid Trading Bot
Manages allocation between arbitrage and token launches
"""

from typing import Dict, Any
from loguru import logger


class CapitalManager:
    """
    Manages capital allocation for hybrid trading
    
    Allocation:
    - 90% Arbitrage (steady income)
    - 10% Token Launches (moonshot potential)
    """

    def __init__(
        self,
        total_capital: float,
        arb_allocation: float = 0.90,
        launch_allocation: float = 0.10
    ):
        """
        Initialize capital manager
        
        Args:
            total_capital: Total capital in USDT
            arb_allocation: Fraction for arbitrage (0.90 = 90%)
            launch_allocation: Fraction for launches (0.10 = 10%)
        """
        self.total_capital = total_capital
        self.arb_allocation = arb_allocation
        self.launch_allocation = launch_allocation
        
        # Calculate pools
        self.arbitrage_pool = total_capital * arb_allocation
        self.launch_pool = total_capital * launch_allocation
        
        # Track usage
        self.arb_used = 0.0
        self.launch_used = 0.0
        
        # Track reserves
        self.reserve_pool = 0.0
        
        logger.info(f"Capital Manager initialized")
        logger.info(f"  Total: ${total_capital:.2f}")
        logger.info(f"  Arb Pool: ${self.arbitrage_pool:.2f}")
        logger.info(f"  Launch Pool: ${self.launch_pool:.2f}")

    def get_arb_position_size(self) -> float:
        """
        Get position size for arbitrage trade

        Returns:
            Position size in USDT (minimum $10 for Binance)
        """
        available = self.arbitrage_pool - self.arb_used

        # Use 50% of available per trade
        position = available * 0.50

        # Minimum $10 (Binance minimum order value)
        # Maximum available
        return max(10.0, min(position, available))

    def get_launch_position_size(self) -> float:
        """
        Get position size for token launch
        
        Returns:
            Position size in USDT (fixed small amount)
        """
        available = self.launch_pool - self.launch_used
        
        # Use fixed amount per launch (max $1.50)
        position = min(1.50, available)
        
        return max(0.50, position)  # Minimum $0.50

    def update_after_profit(self, profit: float, source: str) -> Dict[str, float]:
        """
        Update capital after profit
        
        Distribution:
        - 50% Reinvest (compound growth)
        - 30% Withdraw (pay bills)
        - 20% Reserve (emergency fund)
        
        Args:
            profit: Profit amount in USDT
            source: 'arbitrage' or 'launch'
            
        Returns:
            Distribution dict
        """
        # Calculate distribution
        reinvest = profit * 0.50
        withdraw = profit * 0.30
        reserve = profit * 0.20
        
        # Update pools
        if source == 'arbitrage':
            self.arb_used = 0.0  # Reset usage
            self.arbitrage_pool += reinvest
        elif source == 'launch':
            self.launch_used = 0.0
            self.launch_pool += reinvest
        
        # Update total and reserve
        self.total_capital += profit
        self.reserve_pool += reserve
        
        logger.info(f"Profit distributed: ${profit:.4f}")
        logger.info(f"  Reinvest: ${reinvest:.4f}")
        logger.info(f"  Withdraw: ${withdraw:.4f}")
        logger.info(f"  Reserve: ${reserve:.4f}")
        
        return {
            'reinvest': reinvest,
            'withdraw': withdraw,
            'reserve': reserve
        }

    def update_after_loss(self, loss: float, source: str) -> None:
        """
        Update capital after loss
        
        Args:
            loss: Loss amount in USDT
            source: 'arbitrage' or 'launch'
        """
        if source == 'arbitrage':
            self.arb_used = 0.0
            self.arbitrage_pool = max(0, self.arbitrage_pool - loss)
        elif source == 'launch':
            self.launch_used = 0.0
            self.launch_pool = max(0, self.launch_pool - loss)
        
        self.total_capital = max(0, self.total_capital - loss)
        
        logger.warning(f"Loss recorded: ${loss:.4f} from {source}")

    def add_capital(self, amount: float) -> None:
        """
        Add capital to the system
        
        Args:
            amount: Amount to add in USDT
        """
        self.total_capital += amount
        self.arbitrage_pool += amount * self.arb_allocation
        self.launch_pool += amount * self.launch_allocation
        
        logger.info(f"Added ${amount:.2f} to capital")

    def withdraw(self, amount: float) -> bool:
        """
        Withdraw from reserve pool
        
        Args:
            amount: Amount to withdraw in USDT
            
        Returns:
            True if successful
        """
        if amount <= self.reserve_pool:
            self.reserve_pool -= amount
            self.total_capital -= amount
            logger.info(f"Withdrew ${amount:.2f} from reserve")
            return True
        
        logger.warning(f"Insufficient reserve for withdrawal: ${amount:.2f}")
        return False

    def get_status(self) -> Dict[str, Any]:
        """Get capital manager status"""
        return {
            'total_capital': self.total_capital,
            'arbitrage_pool': self.arbitrage_pool,
            'launch_pool': self.launch_pool,
            'reserve_pool': self.reserve_pool,
            'arb_available': self.arbitrage_pool - self.arb_used,
            'launch_available': self.launch_pool - self.launch_used,
            'arb_used': self.arb_used,
            'launch_used': self.launch_used
        }

    def get_available_capital(self) -> float:
        """Get total available capital (not in use)"""
        return (self.arbitrage_pool - self.arb_used) + \
               (self.launch_pool - self.launch_used)
