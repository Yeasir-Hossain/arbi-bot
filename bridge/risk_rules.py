"""
Risk Assessment Rules for AI Trading System
Defines risk limits and validation logic for trading signals
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum
from loguru import logger


class RiskLevel(Enum):
    """Risk levels for trades"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskAssessment:
    """Result of risk assessment"""
    approved: bool
    risk_level: RiskLevel
    reasons: list
    suggested_modifications: Optional[Dict[str, Any]] = None


class RiskRules:
    """
    Risk assessment rules for validating trading signals
    
    Rules enforced:
    - Position size limits
    - Daily loss limits
    - Confidence thresholds
    - Portfolio exposure limits
    - Stop loss requirements
    """

    def __init__(
        self,
        max_position_size: float = 0.10,      # 10% of portfolio per trade
        max_daily_trades: int = 10,
        daily_loss_limit: float = 0.05,       # 5% of portfolio
        min_confidence: float = 0.70,         # 70% confidence
        max_portfolio_exposure: float = 0.50, # 50% max in open positions
        stop_loss_required: bool = True,
        stop_loss_percent: float = 0.05,      # 5% stop loss
        take_profit_percent: float = 0.10,    # 10% take profit
    ):
        """
        Initialize risk rules
        
        Args:
            max_position_size: Maximum position size as fraction of portfolio
            max_daily_trades: Maximum number of trades per day
            daily_loss_limit: Maximum daily loss as fraction of portfolio
            min_confidence: Minimum AI confidence for trades
            max_portfolio_exposure: Maximum portfolio exposure in open positions
            stop_loss_required: Whether stop loss is required
            stop_loss_percent: Stop loss percentage
            take_profit_percent: Take profit percentage
        """
        self.max_position_size = max_position_size
        self.max_daily_trades = max_daily_trades
        self.daily_loss_limit = daily_loss_limit
        self.min_confidence = min_confidence
        self.max_portfolio_exposure = max_portfolio_exposure
        self.stop_loss_required = stop_loss_required
        self.stop_loss_percent = stop_loss_percent
        self.take_profit_percent = take_profit_percent
        
        # State tracking
        self.trades_today = 0
        self.daily_pnl = 0.0
        self.open_positions = []
        
        logger.info("Risk Rules initialized")
        logger.info(f"  Max position size: {max_position_size:.1%}")
        logger.info(f"  Max daily trades: {max_daily_trades}")
        logger.info(f"  Daily loss limit: {daily_loss_limit:.1%}")
        logger.info(f"  Min confidence: {min_confidence:.1%}")

    def assess_signal(
        self,
        signal: Dict[str, Any],
        portfolio_value: float,
        current_position: float = 0.0
    ) -> RiskAssessment:
        """
        Assess risk of a trading signal
        
        Args:
            signal: Trading signal dict with action, confidence, amount, etc.
            portfolio_value: Total portfolio value
            current_position: Current position size in the asset
            
        Returns:
            RiskAssessment with approval decision
        """
        reasons = []
        suggested_modifications = {}
        risk_score = 0  # Higher = more risk
        
        # Rule 1: Check daily trade limit
        if self.trades_today >= self.max_daily_trades:
            return RiskAssessment(
                approved=False,
                risk_level=RiskLevel.CRITICAL,
                reasons=[f"Daily trade limit reached ({self.trades_today}/{self.max_daily_trades})"]
            )
        
        # Rule 2: Check daily loss limit
        if self.daily_pnl <= -self.daily_loss_limit * portfolio_value:
            return RiskAssessment(
                approved=False,
                risk_level=RiskLevel.CRITICAL,
                reasons=[f"Daily loss limit reached ({self.daily_pnl:.2%})"]
            )
        
        # Rule 3: Check minimum confidence
        confidence = signal.get('confidence', 0)
        if confidence < self.min_confidence:
            return RiskAssessment(
                approved=False,
                risk_level=RiskLevel.HIGH,
                reasons=[f"Confidence too low ({confidence:.1%} < {self.min_confidence:.1%})"]
            )
        
        # Rule 4: Check position size
        proposed_amount = signal.get('amount', 0)
        proposed_value = proposed_amount * signal.get('price', 1)
        position_fraction = proposed_value / portfolio_value if portfolio_value > 0 else 1
        
        if position_fraction > self.max_position_size:
            reasons.append(f"Position size too large ({position_fraction:.1%} > {self.max_position_size:.1%})")
            suggested_modifications['amount'] = (portfolio_value * self.max_position_size) / signal.get('price', 1)
            risk_score += 2
        else:
            reasons.append(f"Position size OK ({position_fraction:.1%})")
        
        # Rule 5: Check portfolio exposure
        total_exposure = sum(pos.get('value', 0) for pos in self.open_positions)
        new_exposure = total_exposure + proposed_value
        exposure_fraction = new_exposure / portfolio_value if portfolio_value > 0 else 1
        
        if exposure_fraction > self.max_portfolio_exposure:
            reasons.append(f"Portfolio exposure too high ({exposure_fraction:.1%} > {self.max_portfolio_exposure:.1%})")
            risk_score += 2
        else:
            reasons.append(f"Portfolio exposure OK ({exposure_fraction:.1%})")
        
        # Rule 6: Check for over-concentration
        if current_position > 0:
            new_position = current_position + proposed_amount
            new_position_fraction = (new_position * signal.get('price', 1)) / portfolio_value
            if new_position_fraction > self.max_position_size * 2:
                reasons.append(f"Over-concentration risk ({new_position_fraction:.1%})")
                risk_score += 1
        
        # Rule 7: Validate signal has required fields
        if 'action' not in signal or signal['action'] not in ['BUY', 'SELL']:
            return RiskAssessment(
                approved=False,
                risk_level=RiskLevel.HIGH,
                reasons=["Invalid or missing action"]
            )
        
        # Rule 8: Check stop loss is planned
        if self.stop_loss_required:
            if 'stop_loss' not in signal:
                suggested_modifications['stop_loss'] = signal.get('price', 1) * (1 - self.stop_loss_percent)
                reasons.append(f"Stop loss added at {suggested_modifications['stop_loss']:.2f}")
        
        # Rule 9: Check take profit is planned
        if 'take_profit' not in signal:
            suggested_modifications['take_profit'] = signal.get('price', 1) * (1 + self.take_profit_percent)
        
        # Determine risk level
        if risk_score == 0:
            risk_level = RiskLevel.LOW
        elif risk_score == 1:
            risk_level = RiskLevel.MEDIUM
        elif risk_score == 2:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.CRITICAL
        
        # Final decision
        approved = risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
        
        if approved and suggested_modifications:
            reasons.append(f"Suggested modifications: {suggested_modifications}")
        
        return RiskAssessment(
            approved=approved,
            risk_level=risk_level,
            reasons=reasons,
            suggested_modifications=suggested_modifications if approved else None
        )

    def record_trade(self, trade: Dict[str, Any]) -> None:
        """Record a executed trade for tracking"""
        self.trades_today += 1
        self.open_positions.append({
            'action': trade['action'],
            'amount': trade['amount'],
            'price': trade['price'],
            'value': trade.get('value', trade['amount'] * trade['price']),
            'timestamp': trade.get('timestamp')
        })
        logger.info(f"Trade recorded. Trades today: {self.trades_today}")

    def update_pnl(self, pnl: float) -> None:
        """Update daily P&L"""
        self.daily_pnl = pnl
        logger.info(f"Daily P&L updated: {pnl:.2%}")

    def close_position(self, trade: Dict[str, Any], pnl: float) -> None:
        """Record a closed position"""
        # Remove from open positions (simplified - matches by action)
        self.open_positions = [
            pos for pos in self.open_positions 
            if pos.get('action') != trade.get('action')
        ]
        self.update_pnl(pnl)
        logger.info(f"Position closed. P&L: {pnl:.2%}")

    def reset_daily(self) -> None:
        """Reset daily counters"""
        self.trades_today = 0
        logger.info("Daily counters reset")

    def get_status(self) -> Dict[str, Any]:
        """Get current risk status"""
        return {
            'trades_today': self.trades_today,
            'max_daily_trades': self.max_daily_trades,
            'daily_pnl': self.daily_pnl,
            'daily_loss_limit': self.daily_loss_limit,
            'open_positions': len(self.open_positions),
            'total_exposure': sum(pos.get('value', 0) for pos in self.open_positions),
            'risk_limits': {
                'max_position_size': self.max_position_size,
                'min_confidence': self.min_confidence,
                'max_portfolio_exposure': self.max_portfolio_exposure,
            }
        }
