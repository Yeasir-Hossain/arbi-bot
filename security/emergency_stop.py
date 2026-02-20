"""
Emergency Stop Mechanism for AI Trading System
Immediately halts all trading activity when critical conditions are met
"""

import asyncio
from typing import Optional, Callable, List, Dict, Any
from datetime import datetime
from pathlib import Path
from enum import Enum
import json
from loguru import logger


class EmergencyReason(Enum):
    """Reasons for emergency stop"""
    MANUAL = "manual"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    SYSTEM_ERROR = "system_error"
    EXCHANGE_ERROR = "exchange_error"
    CONNECTION_LOST = "connection_lost"
    ABNORMAL_LOSS = "abnormal_loss"
    RISK_THRESHOLD = "risk_threshold"


class EmergencyState(Enum):
    """Emergency stop state"""
    ACTIVE = "active"
    INACTIVE = "inactive"


class EmergencyStop:
    """
    Emergency stop mechanism
    
    Features:
    - Immediate trading halt
    - Position closure option
    - Automatic triggers
    - Manual override
    - Event logging
    """

    def __init__(
        self,
        auto_close_positions: bool = False,
        notify_on_trigger: bool = True,
        cooldown_period: int = 300  # 5 minutes
    ):
        """
        Initialize emergency stop
        
        Args:
            auto_close_positions: Close all positions on trigger
            notify_on_trigger: Send alerts when triggered
            cooldown_period: Seconds before can be reactivated
        """
        self.auto_close_positions = auto_close_positions
        self.notify_on_trigger = notify_on_trigger
        self.cooldown_period = cooldown_period
        
        # State
        self.state = EmergencyState.INACTIVE
        self.triggered_at: Optional[datetime] = None
        self.reason: Optional[EmergencyReason] = None
        self.details: str = ""
        self.last_triggered: Optional[datetime] = None
        
        # Callbacks
        self._position_close_callback: Optional[Callable] = None
        self._alert_callback: Optional[Callable] = None
        self._trading_resume_callback: Optional[Callable] = None
        
        # Logging
        self.log_dir = Path("./logs/emergency")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Emergency Stop initialized")
        logger.info(f"  Auto-close positions: {auto_close_positions}")
        logger.info(f"  Cooldown period: {cooldown_period}s")

    def set_position_close_callback(self, callback: Callable) -> None:
        """Set callback for closing positions"""
        self._position_close_callback = callback

    def set_alert_callback(self, callback: Callable) -> None:
        """Set callback for sending alerts"""
        self._alert_callback = callback

    def set_resume_callback(self, callback: Callable) -> None:
        """Set callback for when trading resumes"""
        self._trading_resume_callback = callback

    def trigger(
        self,
        reason: EmergencyReason,
        details: str = "",
        force: bool = False
    ) -> bool:
        """
        Trigger emergency stop
        
        Args:
            reason: Reason for emergency stop
            details: Additional details
            force: Force trigger even during cooldown
            
        Returns:
            True if triggered successfully
        """
        # Check cooldown
        if not force and self._in_cooldown():
            elapsed = (datetime.now() - self.last_triggered).total_seconds()
            logger.warning(
                f"Emergency stop in cooldown. {self.cooldown_period - elapsed:.0f}s remaining"
            )
            return False
        
        # Activate
        self.state = EmergencyState.ACTIVE
        self.triggered_at = datetime.now()
        self.last_triggered = self.triggered_at
        self.reason = reason
        self.details = details
        
        logger.critical(f"🚨 EMERGENCY STOP TRIGGERED")
        logger.critical(f"   Reason: {reason.value}")
        logger.critical(f"   Details: {details}")
        
        # Log event
        self._log_event(reason, details)
        
        # Send alert
        if self.notify_on_trigger and self._alert_callback:
            asyncio.create_task(self._alert_callback(
                title="🚨 Emergency Stop Activated",
                message=f"Reason: {reason.value}. {details}",
                level="critical"
            ))
        
        # Close positions if configured
        if self.auto_close_positions and self._position_close_callback:
            asyncio.create_task(self._close_all_positions())
        
        return True

    async def _close_all_positions(self) -> bool:
        """Close all open positions"""
        logger.warning("Closing all positions...")
        
        try:
            if self._position_close_callback:
                result = await self._position_close_callback()
                logger.info(f"Positions closed: {result}")
                return True
        except Exception as e:
            logger.error(f"Failed to close positions: {e}")
            return False
        
        return False

    def reset(self, manual_confirmation: bool = True) -> bool:
        """
        Reset emergency stop
        
        Args:
            manual_confirmation: Require manual confirmation
            
        Returns:
            True if reset successfully
        """
        if self.state == EmergencyState.INACTIVE:
            return True
        
        if manual_confirmation:
            logger.warning("Manual confirmation required to reset emergency stop")
            logger.warning("Call reset(manual_confirmation=False) to confirm")
            return False
        
        logger.info("Emergency stop reset")
        self.state = EmergencyState.INACTIVE
        self.triggered_at = None
        self.reason = None
        self.details = ""
        
        # Notify resume
        if self._trading_resume_callback:
            asyncio.create_task(self._trading_resume_callback())
        
        return True

    def _in_cooldown(self) -> bool:
        """Check if in cooldown period"""
        if not self.last_triggered:
            return False
        
        elapsed = (datetime.now() - self.last_triggered).total_seconds()
        return elapsed < self.cooldown_period

    def _log_event(self, reason: EmergencyReason, details: str) -> None:
        """Log emergency stop event"""
        log_file = self.log_dir / "emergency_events.jsonl"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps({
                'timestamp': datetime.now().isoformat(),
                'reason': reason.value,
                'details': details,
                'state': self.state.value
            }) + '\n')

    def is_active(self) -> bool:
        """Check if emergency stop is active"""
        return self.state == EmergencyState.ACTIVE

    def can_trade(self) -> bool:
        """Check if trading is allowed"""
        return self.state == EmergencyState.INACTIVE

    def get_status(self) -> Dict[str, Any]:
        """Get emergency stop status"""
        return {
            'state': self.state.value,
            'active': self.is_active(),
            'can_trade': self.can_trade(),
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'reason': self.reason.value if self.reason else None,
            'details': self.details,
            'in_cooldown': self._in_cooldown(),
            'last_triggered': self.last_triggered.isoformat() if self.last_triggered else None,
            'auto_close_positions': self.auto_close_positions,
            'cooldown_period': self.cooldown_period
        }


class RiskMonitor:
    """
    Monitor risk metrics and trigger emergency stop if thresholds exceeded
    """

    def __init__(
        self,
        emergency_stop: EmergencyStop,
        daily_loss_limit: float = 0.05,  # 5%
        max_drawdown: float = 0.10,  # 10%
        abnormal_loss_threshold: float = 0.02,  # 2% in single trade
        check_interval: int = 60  # Check every 60 seconds
    ):
        """
        Initialize risk monitor
        
        Args:
            emergency_stop: Emergency stop instance
            daily_loss_limit: Daily loss limit (fraction)
            max_drawdown: Maximum drawdown (fraction)
            abnormal_loss_threshold: Abnormal loss threshold (fraction)
            check_interval: Check interval in seconds
        """
        self.emergency_stop = emergency_stop
        self.daily_loss_limit = daily_loss_limit
        self.max_drawdown = max_drawdown
        self.abnormal_loss_threshold = abnormal_loss_threshold
        self.check_interval = check_interval
        
        # State
        self.initial_balance = 0.0
        self.peak_balance = 0.0
        self.daily_start_balance = 0.0
        self._running = False
        
        logger.info("Risk Monitor initialized")

    def set_balance(self, current: float, daily_start: float) -> None:
        """Update balance tracking"""
        if self.initial_balance == 0:
            self.initial_balance = current
            self.peak_balance = current
        
        self.peak_balance = max(self.peak_balance, current)
        self.daily_start_balance = daily_start

    async def start_monitoring(self) -> None:
        """Start continuous risk monitoring"""
        self._running = True
        logger.info("Risk monitoring started")
        
        while self._running:
            await self._check_risk_metrics()
            await asyncio.sleep(self.check_interval)

    def stop_monitoring(self) -> None:
        """Stop risk monitoring"""
        self._running = False
        logger.info("Risk monitoring stopped")

    async def _check_risk_metrics(self) -> None:
        """Check risk metrics and trigger if needed"""
        if self.emergency_stop.is_active():
            return
        
        # Calculate metrics
        current_balance = self._get_current_balance()
        
        if current_balance <= 0:
            return
        
        # Daily loss check
        daily_loss = (self.daily_start_balance - current_balance) / self.daily_start_balance
        if daily_loss >= self.daily_loss_limit:
            logger.critical(f"Daily loss limit exceeded: {daily_loss:.2%}")
            self.emergency_stop.trigger(
                EmergencyReason.DAILY_LOSS_LIMIT,
                f"Daily loss: {daily_loss:.2%} (limit: {self.daily_loss_limit:.2%})"
            )
            return
        
        # Drawdown check
        drawdown = (self.peak_balance - current_balance) / self.peak_balance
        if drawdown >= self.max_drawdown:
            logger.critical(f"Maximum drawdown exceeded: {drawdown:.2%}")
            self.emergency_stop.trigger(
                EmergencyReason.ABNORMAL_LOSS,
                f"Drawdown: {drawdown:.2%} (limit: {self.max_drawdown:.2%})"
            )
            return

    def _get_current_balance(self) -> float:
        """Get current balance (override in subclass)"""
        # This should be implemented to fetch actual balance
        return self.daily_start_balance

    def record_trade_loss(self, loss_percent: float) -> None:
        """Record a trade loss and check for abnormal loss"""
        if abs(loss_percent) >= self.abnormal_loss_threshold:
            logger.warning(f"Abnormal trade loss detected: {loss_percent:.2%}")
            self.emergency_stop.trigger(
                EmergencyReason.ABNORMAL_LOSS,
                f"Trade loss: {loss_percent:.2%} (threshold: {self.abnormal_loss_threshold:.2%})"
            )


# Global emergency stop instance
_emergency_stop: Optional[EmergencyStop] = None


def get_emergency_stop() -> EmergencyStop:
    """Get or create global emergency stop"""
    global _emergency_stop
    if _emergency_stop is None:
        _emergency_stop = EmergencyStop()
    return _emergency_stop
