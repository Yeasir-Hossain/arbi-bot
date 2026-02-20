"""
Signal Validator & Bridge
Validates AI trading signals and optionally executes on live exchange
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from loguru import logger
from enum import Enum

from bridge.risk_rules import RiskRules, RiskAssessment, RiskLevel
from config.config import config


class SignalStatus(Enum):
    """Status of a trading signal"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    EXECUTED = "executed"
    FAILED = "failed"


@dataclass
class TradingSignal:
    """A trading signal from AI"""
    action: str  # BUY or SELL
    pair: str
    confidence: float
    price: float
    amount: float
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)
    status: SignalStatus = SignalStatus.PENDING
    risk_assessment: Optional[RiskAssessment] = None
    execution_result: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'action': self.action,
            'pair': self.pair,
            'confidence': self.confidence,
            'price': self.price,
            'amount': self.amount,
            'reason': self.reason,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status.value,
        }


class SignalValidator:
    """
    Validates and processes trading signals from AI agents
    
    Features:
    - Risk assessment using configurable rules
    - Signal queue management
    - Manual approval workflow
    - Execution logging
    """

    def __init__(
        self,
        risk_rules: Optional[RiskRules] = None,
        auto_execute: bool = False,
        require_manual_approval: bool = True,
        portfolio_value_func: Optional[Callable[[], float]] = None
    ):
        """
        Initialize signal validator
        
        Args:
            risk_rules: Risk rules configuration (uses defaults if None)
            auto_execute: Automatically execute approved signals
            require_manual_approval: Require human approval before execution
            portfolio_value_func: Function to get current portfolio value
        """
        self.risk_rules = risk_rules or RiskRules()
        self.auto_execute = auto_execute
        self.require_manual_approval = require_manual_approval
        self.portfolio_value_func = portfolio_value_func
        
        # Signal queues
        self.pending_signals: List[TradingSignal] = []
        self.executed_signals: List[TradingSignal] = []
        self.rejected_signals: List[TradingSignal] = []
        
        # Execution callback (set by exchange connector)
        self.execution_callback: Optional[Callable] = None
        
        # Logging
        self.log_dir = Path("./logs/signals")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Signal Validator initialized")
        logger.info(f"  Auto-execute: {auto_execute}")
        logger.info(f"  Manual approval required: {require_manual_approval}")

    def set_execution_callback(self, callback: Callable) -> None:
        """Set callback function for trade execution"""
        self.execution_callback = callback
        logger.info("Execution callback set")

    def receive_signal(self, signal_data: Dict[str, Any]) -> TradingSignal:
        """
        Receive a trading signal from AI
        
        Args:
            signal_data: Signal data from AI agent
            
        Returns:
            Created TradingSignal
        """
        # Create signal object
        signal = TradingSignal(
            action=signal_data.get('action', 'HOLD'),
            pair=signal_data.get('pair', 'UNKNOWN'),
            confidence=signal_data.get('confidence', 0),
            price=signal_data.get('price', 0),
            amount=signal_data.get('amount', 0),
            reason=signal_data.get('reason', 'No reason provided')
        )
        
        logger.info(f"📨 Signal received: {signal.action} {signal.pair}")
        logger.info(f"   Confidence: {signal.confidence:.1%}")
        logger.info(f"   Price: ${signal.price:,.2f}")
        logger.info(f"   Amount: {signal.amount}")
        logger.info(f"   Reason: {signal.reason[:100]}...")
        
        # Add to pending queue
        self.pending_signals.append(signal)
        
        # Validate signal
        assessment = self._validate_signal(signal)
        signal.risk_assessment = assessment
        
        if not assessment.approved:
            signal.status = SignalStatus.REJECTED
            self.rejected_signals.append(signal)
            self.pending_signals.remove(signal)
            
            logger.warning(f"❌ Signal REJECTED: {assessment.reasons}")
            self._log_signal(signal)
            return signal
        
        # Signal approved
        signal.status = SignalStatus.APPROVED
        
        if self.require_manual_approval:
            logger.info("⏸️  Signal queued for manual approval")
        elif self.auto_execute:
            logger.info("⚡ Auto-executing signal...")
            asyncio.create_task(self.execute_signal(signal))
        else:
            logger.info("✓ Signal approved, awaiting execution trigger")
        
        self._log_signal(signal)
        return signal

    def _validate_signal(self, signal: TradingSignal) -> RiskAssessment:
        """Validate signal against risk rules"""
        # Get portfolio value
        portfolio_value = 100000  # Default
        if self.portfolio_value_func:
            portfolio_value = self.portfolio_value_func()
        
        # Run risk assessment
        assessment = self.risk_rules.assess_signal(
            signal={
                'action': signal.action,
                'confidence': signal.confidence,
                'amount': signal.amount,
                'price': signal.price
            },
            portfolio_value=portfolio_value
        )
        
        logger.info(f"🛡️  Risk Assessment: {assessment.risk_level.value}")
        for reason in assessment.reasons:
            logger.info(f"   • {reason}")
        
        return assessment

    async def execute_signal(self, signal: TradingSignal) -> bool:
        """
        Execute an approved signal
        
        Args:
            signal: Signal to execute
            
        Returns:
            True if execution successful
        """
        if signal.status != SignalStatus.APPROVED:
            logger.warning(f"Cannot execute signal with status: {signal.status}")
            return False
        
        signal.status = SignalStatus.EXECUTING
        
        try:
            # Apply suggested modifications if any
            if signal.risk_assessment and signal.risk_assessment.suggested_modifications:
                mods = signal.risk_assessment.suggested_modifications
                if 'amount' in mods:
                    signal.amount = mods['amount']
                    logger.info(f"Modified amount to: {signal.amount}")
                if 'stop_loss' in mods:
                    signal_data = signal.to_dict()
                    signal_data['stop_loss'] = mods['stop_loss']
            
            # Execute via callback
            if self.execution_callback:
                result = await self.execution_callback(signal.to_dict())
                signal.execution_result = result
                signal.status = SignalStatus.EXECUTED
                
                # Record in risk rules
                self.risk_rules.record_trade({
                    'action': signal.action,
                    'amount': signal.amount,
                    'price': signal.price,
                    'value': signal.amount * signal.price,
                    'timestamp': datetime.now()
                })
                
                logger.info(f"✅ Signal EXECUTED successfully")
                
                # Move to executed list
                self.executed_signals.append(signal)
                if signal in self.pending_signals:
                    self.pending_signals.remove(signal)
                
                self._log_signal(signal)
                return True
            else:
                logger.warning("No execution callback set - signal not executed")
                signal.status = SignalStatus.FAILED
                return False
                
        except Exception as e:
            logger.error(f"❌ Signal execution failed: {e}")
            signal.status = SignalStatus.FAILED
            signal.execution_result = {'error': str(e)}
            self._log_signal(signal)
            return False

    def approve_signal(self, signal_index: int) -> bool:
        """
        Manually approve a pending signal
        
        Args:
            signal_index: Index in pending signals list
            
        Returns:
            True if approval successful
        """
        if signal_index < 0 or signal_index >= len(self.pending_signals):
            logger.error(f"Invalid signal index: {signal_index}")
            return False
        
        signal = self.pending_signals[signal_index]
        
        if signal.risk_assessment and not signal.risk_assessment.approved:
            logger.error("Cannot approve a rejected signal")
            return False
        
        logger.info(f"✓ Manual approval granted for signal {signal_index}")
        
        if self.auto_execute:
            asyncio.create_task(self.execute_signal(signal))
        
        return True

    def reject_signal(self, signal_index: int) -> bool:
        """
        Manually reject a pending signal
        
        Args:
            signal_index: Index in pending signals list
            
        Returns:
            True if rejection successful
        """
        if signal_index < 0 or signal_index >= len(self.pending_signals):
            logger.error(f"Invalid signal index: {signal_index}")
            return False
        
        signal = self.pending_signals[signal_index]
        signal.status = SignalStatus.REJECTED
        
        self.rejected_signals.append(signal)
        self.pending_signals.remove(signal)
        
        logger.info(f"❌ Signal {signal_index} rejected manually")
        self._log_signal(signal)
        
        return True

    def get_pending_signals(self) -> List[Dict[str, Any]]:
        """Get all pending signals"""
        return [s.to_dict() for s in self.pending_signals]

    def get_status(self) -> Dict[str, Any]:
        """Get validator status"""
        return {
            'pending': len(self.pending_signals),
            'executed': len(self.executed_signals),
            'rejected': len(self.rejected_signals),
            'risk_status': self.risk_rules.get_status(),
            'auto_execute': self.auto_execute,
            'manual_approval_required': self.require_manual_approval
        }

    def _log_signal(self, signal: TradingSignal) -> None:
        """Log signal to file"""
        log_file = self.log_dir / f"signals_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(signal.to_dict()) + '\n')

    def reset_daily(self) -> None:
        """Reset daily counters"""
        self.risk_rules.reset_daily()
        logger.info("Signal validator daily reset complete")


class SignalBridge:
    """
    Bridge between AI signals and exchange execution
    
    Combines SignalValidator with exchange connectivity
    """

    def __init__(
        self,
        validator: SignalValidator,
        exchange_connector: Optional[Any] = None,
        trading_pair: str = "BTC/USDT"
    ):
        """
        Initialize signal bridge
        
        Args:
            validator: Signal validator instance
            exchange_connector: Exchange connector for execution
            trading_pair: Primary trading pair
        """
        self.validator = validator
        self.exchange_connector = exchange_connector
        self.trading_pair = trading_pair
        
        # Set execution callback
        if exchange_connector:
            self.validator.set_execution_callback(self._execute_on_exchange)
        
        logger.info(f"Signal Bridge initialized for {trading_pair}")

    async def _execute_on_exchange(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Execute signal on connected exchange"""
        if not self.exchange_connector:
            raise RuntimeError("No exchange connector configured")
        
        # Call exchange connector
        if signal['action'] == 'BUY':
            result = await self.exchange_connector.place_order(
                symbol=self.trading_pair,
                side='buy',
                amount=signal['amount'],
                price=signal.get('price')
            )
        else:
            result = await self.exchange_connector.place_order(
                symbol=self.trading_pair,
                side='sell',
                amount=signal['amount'],
                price=signal.get('price')
            )
        
        return result

    def receive_ai_signal(self, signal: Dict[str, Any]) -> TradingSignal:
        """Receive signal from AI and process through bridge"""
        return self.validator.receive_signal(signal)

    def get_status(self) -> Dict[str, Any]:
        """Get bridge status"""
        return {
            'trading_pair': self.trading_pair,
            'validator_status': self.validator.get_status(),
            'exchange_connected': self.exchange_connector is not None
        }
