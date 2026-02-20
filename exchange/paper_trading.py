"""
Paper Trading Module
Simulates live trading without real money
Perfect for testing strategies safely
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from loguru import logger
import uuid

from config.config import config


@dataclass
class PaperOrder:
    """Simulated order for paper trading"""
    order_id: str
    symbol: str
    side: str
    type: str
    amount: float
    price: float
    status: str = "open"
    filled: float = 0.0
    avg_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None


@dataclass
class PaperPosition:
    """Simulated trading position"""
    symbol: str
    side: str
    amount: float
    entry_price: float
    current_price: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    opened_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None
    pnl: float = 0.0
    pnl_percent: float = 0.0


class PaperExchange:
    """
    Paper trading exchange simulator
    
    Features:
    - Simulated order execution
    - Virtual balance tracking
    - Position management
    - P&L calculation
    - Real-time price updates
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        trading_pair: str = "BTC/USDT"
    ):
        """
        Initialize paper exchange
        
        Args:
            initial_balance: Starting virtual balance (USDT)
            trading_pair: Primary trading pair
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.trading_pair = trading_pair
        
        # State
        self.orders: Dict[str, PaperOrder] = {}
        self.positions: Dict[str, PaperPosition] = {}
        self.order_history: List[PaperOrder] = []
        self.trade_history: List[Dict[str, Any]] = []
        
        # Current prices
        self.prices: Dict[str, float] = {}
        
        # Logging
        self.log_dir = Path("./logs/paper_trading")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📄 Paper Exchange initialized")
        logger.info(f"   Initial Balance: ${initial_balance:,.2f}")
        logger.info(f"   Trading Pair: {trading_pair}")

    def update_price(self, symbol: str, price: float) -> None:
        """
        Update current price for a symbol
        
        Args:
            symbol: Trading pair
            price: Current price
        """
        self.prices[symbol] = price
        
        # Update position P&L
        if symbol in self.positions:
            position = self.positions[symbol]
            position.current_price = price
            position.pnl = self._calculate_pnl(position)
            position.pnl_percent = position.pnl / (position.entry_price * position.amount)
            
            # Check stop loss / take profit
            self._check_exit_conditions(position)

    def _calculate_pnl(self, position: PaperPosition) -> float:
        """Calculate position P&L"""
        if position.side == 'buy':
            return (position.current_price - position.entry_price) * position.amount
        else:
            return (position.entry_price - position.current_price) * position.amount

    def _check_exit_conditions(self, position: PaperPosition) -> None:
        """Check and execute stop loss / take profit"""
        if position.closed_at:
            return
        
        # Check stop loss
        if position.stop_loss and position.current_price <= position.stop_loss:
            logger.info(f"🛑 Stop loss triggered for {position.symbol}")
            self._close_position(position, position.stop_loss, "stop_loss")
            return
        
        # Check take profit
        if position.take_profit and position.current_price >= position.take_profit:
            logger.info(f"🎯 Take profit triggered for {position.symbol}")
            self._close_position(position, position.take_profit, "take_profit")
            return

    async def place_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        order_type: str = "market",
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Optional[PaperOrder]:
        """
        Place a simulated order
        
        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Amount in base currency
            price: Price (optional for market orders)
            order_type: 'market' or 'limit'
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            PaperOrder or None
        """
        # Get current price
        current_price = self.prices.get(symbol, price or 0)
        
        if current_price == 0:
            logger.error(f"No price available for {symbol}")
            return None
        
        # Calculate order value
        order_value = amount * current_price
        
        # Check balance for buys
        if side == 'buy' and order_value > self.balance:
            logger.error(f"Insufficient balance: need ${order_value:.2f}, have ${self.balance:.2f}")
            return None
        
        # Create order
        order = PaperOrder(
            order_id=f"paper_{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            side=side,
            type=order_type,
            amount=amount,
            price=price or current_price
        )
        
        logger.info(f"📄 Paper Order: {order_type} {side} {amount} {symbol} @ ${current_price:,.2f}")
        
        # Execute immediately for market orders
        if order_type == "market":
            order.status = "filled"
            order.filled = amount
            order.avg_price = current_price
            order.filled_at = datetime.now()
            
            # Update balance
            if side == 'buy':
                self.balance -= order_value
                logger.info(f"💰 Spent: ${order_value:.2f}")
            else:
                self.balance += order_value
                logger.info(f"💰 Received: ${order_value:.2f}")
            
            # Create/update position
            self._update_position(symbol, side, amount, current_price, stop_loss, take_profit)
        
        # Store order
        self.orders[order.order_id] = order
        self.order_history.append(order)
        
        # Log trade
        self._log_trade(order)
        
        return order

    def _update_position(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> None:
        """Update or create position"""
        if symbol in self.positions:
            position = self.positions[symbol]
            
            # Add to existing position (same side)
            if position.side == side:
                avg_price = ((position.entry_price * position.amount) + (price * amount)) / (position.amount + amount)
                position.amount += amount
                position.entry_price = avg_price
                position.stop_loss = stop_loss
                position.take_profit = take_profit
            # Close/reverse position (opposite side)
            else:
                if amount >= position.amount:
                    # Fully close and potentially reverse
                    self._close_position(position, price, "close")
                    if amount > position.amount:
                        # Open reverse position
                        new_amount = amount - position.amount
                        self._open_position(symbol, side, new_amount, price, stop_loss, take_profit)
                else:
                    # Partially close
                    position.amount -= amount
        else:
            self._open_position(symbol, side, amount, price, stop_loss, take_profit)

    def _open_position(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> None:
        """Open new position"""
        self.positions[symbol] = PaperPosition(
            symbol=symbol,
            side=side,
            amount=amount,
            entry_price=price,
            current_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        logger.info(f"📈 Position opened: {side.upper()} {amount} {symbol} @ ${price:,.2f}")

    def _close_position(self, position: PaperPosition, exit_price: float, reason: str) -> None:
        """Close position"""
        # Calculate final P&L
        pnl = (exit_price - position.entry_price) * position.amount
        if position.side == 'sell':
            pnl = (position.entry_price - exit_price) * position.amount
        
        position.pnl = pnl
        position.pnl_percent = pnl / (position.entry_price * position.amount)
        position.closed_at = datetime.now()
        position.current_price = exit_price
        
        # Update balance
        if position.side == 'buy':
            self.balance += exit_price * position.amount
        else:
            self.balance -= exit_price * position.amount
        
        # Log
        emoji = "💰" if pnl > 0 else "📉"
        logger.info(f"{emoji} Position closed: {reason}")
        logger.info(f"   P&L: ${pnl:+,.2f} ({position.pnl_percent:+.2%})")
        
        # Record trade
        self.trade_history.append({
            'symbol': position.symbol,
            'side': position.side,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'amount': position.amount,
            'pnl': pnl,
            'pnl_percent': position.pnl_percent,
            'opened_at': position.opened_at.isoformat(),
            'closed_at': position.closed_at.isoformat(),
            'reason': reason
        })
        
        # Remove from open positions
        del self.positions[position.symbol]

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        if order.status != "open":
            return False
        
        order.status = "cancelled"
        logger.info(f"Order {order_id} cancelled")
        return True

    def get_portfolio(self) -> Dict[str, Any]:
        """Get current portfolio status"""
        total_value = self.balance
        
        # Add position values
        for symbol, position in self.positions.items():
            total_value += position.amount * position.current_price
        
        return {
            'balance': self.balance,
            'initial_balance': self.initial_balance,
            'total_value': total_value,
            'total_pnl': total_value - self.initial_balance,
            'total_pnl_percent': (total_value - self.initial_balance) / self.initial_balance,
            'open_positions': len(self.positions),
            'positions': [
                {
                    'symbol': p.symbol,
                    'side': p.side,
                    'amount': p.amount,
                    'entry_price': p.entry_price,
                    'current_price': p.current_price,
                    'pnl': p.pnl,
                    'pnl_percent': p.pnl_percent
                }
                for p in self.positions.values()
            ],
            'trades_today': len([t for t in self.trade_history if self._is_today(t['closed_at'])])
        }

    def _is_today(self, timestamp_str: str) -> bool:
        """Check if timestamp is today"""
        timestamp = datetime.fromisoformat(timestamp_str)
        return timestamp.date() == datetime.now().date()

    def _log_trade(self, order: PaperOrder) -> None:
        """Log trade to file"""
        log_file = self.log_dir / f"trades_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps({
                'order_id': order.order_id,
                'symbol': order.symbol,
                'side': order.side,
                'amount': order.amount,
                'price': order.price,
                'status': order.status,
                'timestamp': order.created_at.isoformat()
            }) + '\n')

    def get_status(self) -> Dict[str, Any]:
        """Get paper exchange status"""
        portfolio = self.get_portfolio()
        return {
            'mode': 'paper',
            'trading_pair': self.trading_pair,
            'portfolio': portfolio,
            'open_orders': len([o for o in self.orders.values() if o.status == 'open']),
            'total_trades': len(self.trade_history)
        }
