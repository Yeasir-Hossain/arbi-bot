"""
Basic tests for AI Trading System
Run with: pytest tests/ -v
"""

import pytest
import asyncio
from datetime import datetime


class TestRiskRules:
    """Test risk assessment rules"""

    def test_position_size_limit(self):
        """Test position size validation"""
        from bridge import RiskRules
        
        rules = RiskRules(max_position_size=0.10)
        
        assessment = rules.assess_signal(
            signal={'action': 'BUY', 'confidence': 0.8, 'amount': 100, 'price': 50},
            portfolio_value=10000
        )
        
        assert assessment.approved is True
        assert assessment.risk_level.value in ['low', 'medium']

    def test_confidence_threshold(self):
        """Test minimum confidence requirement"""
        from bridge import RiskRules
        
        rules = RiskRules(min_confidence=0.70)
        
        assessment = rules.assess_signal(
            signal={'action': 'BUY', 'confidence': 0.5, 'amount': 100, 'price': 50},
            portfolio_value=10000
        )
        
        assert assessment.approved is False

    def test_daily_trade_limit(self):
        """Test daily trade limit"""
        from bridge import RiskRules
        
        rules = RiskRules(max_daily_trades=5)
        rules.trades_today = 5
        
        assessment = rules.assess_signal(
            signal={'action': 'BUY', 'confidence': 0.9, 'amount': 100, 'price': 50},
            portfolio_value=10000
        )
        
        assert assessment.approved is False


class TestPaperExchange:
    """Test paper trading exchange"""

    @pytest.mark.asyncio
    async def test_place_order(self):
        """Test placing paper order"""
        from exchange import PaperExchange
        
        exchange = PaperExchange(initial_balance=10000)
        exchange.update_price('BTC/USDT', 50000)
        
        order = await exchange.place_order(
            symbol='BTC/USDT',
            side='buy',
            amount=0.1,
            order_type='market'
        )
        
        assert order is not None
        assert order.side == 'buy'
        assert order.amount == 0.1

    @pytest.mark.asyncio
    async def test_insufficient_balance(self):
        """Test order with insufficient balance"""
        from exchange import PaperExchange
        
        exchange = PaperExchange(initial_balance=1000)
        exchange.update_price('BTC/USDT', 50000)
        
        order = await exchange.place_order(
            symbol='BTC/USDT',
            side='buy',
            amount=1.0,  # Would cost $50,000
            order_type='market'
        )
        
        assert order is None

    def test_portfolio_calculation(self):
        """Test portfolio value calculation"""
        from exchange import PaperExchange
        
        exchange = PaperExchange(initial_balance=10000)
        
        portfolio = exchange.get_portfolio()
        
        assert portfolio['balance'] == 10000
        assert portfolio['initial_balance'] == 10000


class TestSignalValidator:
    """Test signal validation"""

    def test_receive_valid_signal(self):
        """Test receiving valid signal"""
        from bridge import SignalValidator, RiskRules
        
        validator = SignalValidator(risk_rules=RiskRules())
        
        signal = validator.receive_signal({
            'action': 'BUY',
            'pair': 'BTC/USDT',
            'confidence': 0.85,
            'price': 50000,
            'amount': 0.1,
            'reason': 'Test signal'
        })
        
        assert signal.status.value == 'approved'

    def test_receive_low_confidence_signal(self):
        """Test receiving low confidence signal"""
        from bridge import SignalValidator, RiskRules
        
        validator = SignalValidator(risk_rules=RiskRules(min_confidence=0.70))
        
        signal = validator.receive_signal({
            'action': 'BUY',
            'pair': 'BTC/USDT',
            'confidence': 0.50,
            'price': 50000,
            'amount': 0.1,
            'reason': 'Low confidence'
        })
        
        assert signal.status.value == 'rejected'


class TestPerformanceTracker:
    """Test performance tracking"""

    def test_record_trade(self):
        """Test trade recording"""
        from monitoring import PerformanceTracker
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(data_dir=tmpdir)
            
            tracker.record_trade(
                action='BUY',
                pair='BTC/USDT',
                amount=0.1,
                price=50000,
                pnl=0,
                pnl_percent=0
            )
            
            trades = tracker.load_trades()
            assert len(trades) == 1

    def test_calculate_metrics(self):
        """Test metrics calculation"""
        from monitoring import PerformanceTracker
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(data_dir=tmpdir)
            
            # Record some trades
            tracker.record_trade('BUY', 'BTC/USDT', 0.1, 50000, pnl=500, pnl_percent=0.05)
            tracker.record_trade('SELL', 'BTC/USDT', 0.1, 50000, pnl=-200, pnl_percent=-0.02)
            
            metrics = tracker.calculate_metrics()
            
            assert metrics['total_trades'] == 2
            assert metrics['winning_trades'] == 1
            assert metrics['losing_trades'] == 1


class TestEmergencyStop:
    """Test emergency stop mechanism"""

    def test_trigger_emergency_stop(self):
        """Test triggering emergency stop"""
        from security import EmergencyStop, EmergencyReason
        
        stop = EmergencyStop()
        result = stop.trigger(
            EmergencyReason.MANUAL,
            "Test trigger"
        )
        
        assert result is True
        assert stop.is_active() is True

    def test_emergency_stop_cooldown(self):
        """Test emergency stop cooldown"""
        from security import EmergencyStop, EmergencyReason
        
        stop = EmergencyStop(cooldown_period=60)
        stop.trigger(EmergencyReason.MANUAL, "Test")
        
        # Should fail due to cooldown
        result = stop.trigger(EmergencyReason.MANUAL, "Test 2")
        
        assert result is False

    def test_reset_emergency_stop(self):
        """Test resetting emergency stop"""
        from security import EmergencyStop, EmergencyReason
        
        stop = EmergencyStop()
        stop.trigger(EmergencyReason.MANUAL, "Test")
        stop.reset(manual_confirmation=False)
        
        assert stop.is_active() is False


class TestConfig:
    """Test configuration loading"""

    def test_config_loading(self):
        """Test configuration loads correctly"""
        from config import config
        
        assert config.trading.max_position_size > 0
        assert config.trading.min_confidence > 0
        assert config.trading.min_confidence <= 1


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
