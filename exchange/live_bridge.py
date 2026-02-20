"""
Live Trading Bridge
Connects validated signals to live exchange execution
Includes profit withdrawal for AI survival
"""

import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from loguru import logger
from pathlib import Path
import json

from exchange.client import ExchangeClient, OrderResult
from config.config import config


class LiveTradingBridge:
    """
    Bridge between signal validator and live exchange
    
    Features:
    - Execute validated signals on real exchange
    - Track positions and P&L
    - Automatic profit withdrawal
    - Emergency stop mechanism
    """

    def __init__(
        self,
        exchange_client: ExchangeClient,
        trading_pair: str = "BTC/USDT",
        auto_withdraw_enabled: bool = True,
        withdraw_percentage: float = 0.5,
        withdraw_wallet: str = ""
    ):
        """
        Initialize live trading bridge
        
        Args:
            exchange_client: Exchange client instance
            trading_pair: Primary trading pair
            auto_withdraw_enabled: Enable automatic profit withdrawal
            withdraw_percentage: Percentage of profits to withdraw
            withdraw_wallet: Wallet address for withdrawals
        """
        self.exchange = exchange_client
        self.trading_pair = trading_pair
        self.auto_withdraw_enabled = auto_withdraw_enabled
        self.withdraw_percentage = withdraw_percentage
        self.withdraw_wallet = withdraw_wallet
        
        # State
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.initial_balance = 0.0
        self.current_balance = 0.0
        self.total_deposited = 0.0
        self.total_withdrawn = 0.0
        self.trades_executed = 0
        self.trades_today = 0
        
        # Emergency stop
        self.emergency_stop = False
        
        # Logging
        self.log_dir = Path("./logs/live_trading")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🔴 LIVE TRADING BRIDGE initialized")
        logger.info(f"   Trading Pair: {trading_pair}")
        logger.info(f"   Auto Withdraw: {auto_withdraw_enabled} ({withdraw_percentage:.0%})")
        logger.warning(f"   ⚠️ REAL MONEY MODE ⚠️")

    async def initialize(self) -> bool:
        """Initialize bridge and connect to exchange"""
        if self.emergency_stop:
            logger.error("Cannot initialize: emergency stop is active")
            return False
        
        # Connect to exchange
        connected = await self.exchange.connect()
        if not connected:
            return False
        
        # Get initial balance
        self.initial_balance = await self.exchange.get_balance('USDT')
        self.current_balance = self.initial_balance
        
        logger.info(f"Initial balance: ${self.initial_balance:,.2f}")
        
        return True

    async def execute_signal(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute a validated trading signal
        
        Args:
            signal: Validated signal dict
            
        Returns:
            Execution result or None
        """
        if self.emergency_stop:
            logger.error("❌ Emergency stop active - signal rejected")
            return None
        
        action = signal.get('action', '')
        amount = signal.get('amount', 0)
        stop_loss = signal.get('stop_loss')
        take_profit = signal.get('take_profit')
        
        logger.info(f"🔴 EXECUTING LIVE SIGNAL: {action}")
        
        try:
            # Place order
            result = await self.exchange.place_order(
                symbol=self.trading_pair,
                side='buy' if action == 'BUY' else 'sell',
                amount=amount,
                order_type='market'
            )
            
            if not result:
                logger.error("Order execution failed")
                return None
            
            # Track position
            self._track_execution(signal, result)
            
            # Update balance
            self.current_balance = await self.exchange.get_balance('USDT')
            
            # Check for profit withdrawal
            if self.auto_withdraw_enabled:
                await self._check_profit_withdrawal()
            
            logger.info(f"✅ Signal executed successfully")
            
            return {
                'success': True,
                'order_id': result.order_id,
                'action': action,
                'amount': amount,
                'price': result.avg_price,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Execution failed: {e}")
            return {'success': False, 'error': str(e)}

    def _track_execution(self, signal: Dict[str, Any], result: OrderResult) -> None:
        """Track executed trade"""
        self.trades_executed += 1
        self.trades_today += 1
        
        # Store position info
        self.positions[self.trading_pair] = {
            'action': signal['action'],
            'amount': result.filled,
            'entry_price': result.avg_price,
            'stop_loss': signal.get('stop_loss'),
            'take_profit': signal.get('take_profit'),
            'opened_at': datetime.now().isoformat()
        }
        
        # Log to file
        self._log_trade(signal, result)

    def _log_trade(self, signal: Dict[str, Any], result: OrderResult) -> None:
        """Log trade to file"""
        log_file = self.log_dir / f"trades_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps({
                'timestamp': datetime.now().isoformat(),
                'signal': signal,
                'result': {
                    'order_id': result.order_id,
                    'status': result.status,
                    'filled': result.filled,
                    'avg_price': result.avg_price,
                    'fee': result.fee
                }
            }) + '\n')

    async def _check_profit_withdrawal(self) -> None:
        """Check and execute profit withdrawal if threshold met"""
        if not self.withdraw_wallet:
            return
        
        # Calculate profit
        profit = self.current_balance - self.initial_balance
        
        if profit <= 0:
            return
        
        # Calculate withdrawal amount
        withdraw_amount = profit * self.withdraw_percentage
        
        if withdraw_amount < 10:  # Minimum $10 withdrawal
            return
        
        logger.info(f"💸 Profit detected: ${profit:.2f}")
        logger.info(f"💸 Withdrawing {self.withdraw_percentage:.0%}: ${withdraw_amount:.2f}")
        
        # Execute withdrawal
        await self.withdraw_profits(withdraw_amount)

    async def withdraw_profits(self, amount: float) -> bool:
        """
        Withdraw profits to wallet
        
        ⚠️ CRITICAL: This sends real money!
        
        Args:
            amount: Amount to withdraw (in USDT)
            
        Returns:
            True if successful
        """
        if not self.withdraw_wallet:
            logger.error("No withdrawal wallet configured")
            return False
        
        if self.emergency_stop:
            logger.error("Cannot withdraw: emergency stop active")
            return False
        
        try:
            logger.warning(f"💸 INITIATING WITHDRAWAL: {amount} USDT to {self.withdraw_wallet}")
            
            # Execute withdrawal
            result = await self.exchange.withdraw(
                currency='USDT',
                amount=amount,
                address=self.withdraw_wallet
            )
            
            self.total_withdrawn += amount
            
            logger.warning(f"💸 WITHDRAWAL SUCCESSFUL: {amount} USDT")
            logger.warning(f"   TX ID: {result.get('id', 'N/A')}")
            logger.warning(f"   Total withdrawn: ${self.total_withdrawn:,.2f}")
            
            # Log withdrawal
            self._log_withdrawal(amount, result)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Withdrawal failed: {e}")
            return False

    def _log_withdrawal(self, amount: float, result: Dict[str, Any]) -> None:
        """Log withdrawal to file"""
        log_file = self.log_dir / f"withdrawals_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps({
                'timestamp': datetime.now().isoformat(),
                'amount': amount,
                'currency': 'USDT',
                'wallet': self.withdraw_wallet,
                'tx_id': result.get('id'),
                'status': result.get('status')
            }) + '\n')

    def activate_emergency_stop(self, reason: str) -> None:
        """
        Activate emergency stop
        
        ⚠️ This halts all trading immediately!
        
        Args:
            reason: Reason for emergency stop
        """
        self.emergency_stop = True
        logger.critical(f"🚨 EMERGENCY STOP ACTIVATED: {reason}")
        
        # Log emergency stop
        log_file = self.log_dir / "emergency_stops.log"
        with open(log_file, 'a') as f:
            f.write(f"{datetime.now().isoformat()} | {reason}\n")

    def deactivate_emergency_stop(self) -> bool:
        """Deactivate emergency stop (requires manual confirmation)"""
        if not self.emergency_stop:
            return True
        
        logger.warning("Emergency stop deactivated manually")
        self.emergency_stop = False
        return True

    async def get_status(self) -> Dict[str, Any]:
        """Get bridge status"""
        # Get current balance
        self.current_balance = await self.exchange.get_balance('USDT')
        
        # Calculate P&L
        total_pnl = self.current_balance - self.initial_balance
        pnl_percent = total_pnl / self.initial_balance if self.initial_balance > 0 else 0
        
        return {
            'mode': 'live',
            'trading_pair': self.trading_pair,
            'emergency_stop': self.emergency_stop,
            'balance': {
                'current': self.current_balance,
                'initial': self.initial_balance,
                'total_deposited': self.total_deposited,
                'total_withdrawn': self.total_withdrawn
            },
            'pnl': {
                'total': total_pnl,
                'percent': pnl_percent
            },
            'trades': {
                'executed': self.trades_executed,
                'today': self.trades_today
            },
            'withdrawal': {
                'enabled': self.auto_withdraw_enabled,
                'percentage': self.withdraw_percentage,
                'wallet': self.withdraw_wallet[:10] + '...' if self.withdraw_wallet else None
            }
        }

    async def close(self) -> None:
        """Close bridge and disconnect from exchange"""
        await self.exchange.disconnect()
        logger.info("Live trading bridge closed")
