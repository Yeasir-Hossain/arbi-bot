"""
CLI Dashboard for AI Trading System
Real-time monitoring dashboard in terminal
"""

import asyncio
import os
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger


class Dashboard:
    """
    Real-time CLI monitoring dashboard
    
    Displays:
    - System status
    - Portfolio value
    - Open positions
    - Recent trades
    - Performance metrics
    """

    def __init__(
        self,
        refresh_interval: int = 5,
        trading_system: Optional[Any] = None
    ):
        """
        Initialize dashboard
        
        Args:
            refresh_interval: Screen refresh interval in seconds
            trading_system: Reference to trading system for data
        """
        self.refresh_interval = refresh_interval
        self.trading_system = trading_system
        self.running = False
        
        logger.info(f"Dashboard initialized (refresh: {refresh_interval}s)")

    async def run(self) -> None:
        """Run the dashboard loop"""
        self.running = True

        while self.running:
            try:
                self._clear_screen()
                self._render()
                await asyncio.sleep(self.refresh_interval)
            except KeyboardInterrupt:
                self.running = False
            except BrokenPipeError:
                # Terminal pipe closed - not an error, just stop dashboard
                logger.debug("Dashboard stopped (terminal closed)")
                self.running = False
            except Exception as e:
                logger.error(f"Dashboard error: {e}")
                await asyncio.sleep(self.refresh_interval)

    def stop(self) -> None:
        """Stop the dashboard"""
        self.running = False

    def _clear_screen(self) -> None:
        """Clear terminal screen"""
        os.system('clear' if os.name != 'nt' else 'cls')

    def _render(self) -> None:
        """Render the dashboard"""
        # Get system data
        data = self._get_system_data()
        
        # Render header
        print(self._render_header())
        
        # Render sections
        print(self._render_portfolio(data.get('portfolio', {})))
        print(self._render_positions(data.get('positions', [])))
        print(self._render_metrics(data.get('metrics', {})))
        print(self._render_status(data.get('status', {})))
        
        # Footer
        print(self._render_footer())

    def _get_system_data(self) -> Dict[str, Any]:
        """Get current system data"""
        if not self.trading_system:
            return {
                'portfolio': {'balance': 0, 'value': 0, 'pnl': 0},
                'positions': [],
                'metrics': {'total_trades': 0, 'win_rate': 0},
                'status': {'mode': 'offline', 'agents': []}
            }
        
        try:
            return {
                'portfolio': self.trading_system.get_portfolio(),
                'positions': self.trading_system.get_positions(),
                'metrics': self.trading_system.get_metrics(),
                'status': self.trading_system.get_status()
            }
        except Exception as e:
            logger.error(f"Error getting system data: {e}")
            return {}

    def _render_header(self) -> str:
        """Render dashboard header"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return f"""
╔══════════════════════════════════════════════════════════════════╗
║                    AI TRADING DASHBOARD                           ║
║                    {now}                      ║
╠══════════════════════════════════════════════════════════════════╣
"""

    def _render_portfolio(self, portfolio: Dict[str, Any]) -> str:
        """Render portfolio section"""
        balance = portfolio.get('balance', 0)
        value = portfolio.get('total_value', 0)
        pnl = portfolio.get('total_pnl', 0)
        pnl_pct = portfolio.get('total_pnl_percent', 0)
        
        pnl_emoji = "💰" if pnl >= 0 else "📉"
        
        return f"""
┌──────────────────────────────────────────────────────────────────┐
│ 💼 PORTFOLIO                                                      │
├──────────────────────────────────────────────────────────────────┤
│  Balance:      ${balance:>12,.2f}                                 │
│  Total Value:  ${value:>12,.2f}                                 │
│  Total P&L:    {pnl_emoji} ${pnl:>10,.2f} ({pnl_pct:>+.2f}%)                  │
└──────────────────────────────────────────────────────────────────┘
"""

    def _render_positions(self, positions: list) -> str:
        """Render positions section"""
        if not positions:
            return """
┌──────────────────────────────────────────────────────────────────┐
│ 📊 OPEN POSITIONS: None                                          │
└──────────────────────────────────────────────────────────────────┘
"""
        
        lines = ["┌──────────────────────────────────────────────────────────────────┐",
                 "│ 📊 OPEN POSITIONS                                                 │"]
        
        for pos in positions[:5]:  # Show max 5 positions
            symbol = pos.get('symbol', 'N/A')
            side = pos.get('side', 'N/A')
            amount = pos.get('amount', 0)
            pnl = pos.get('pnl', 0)
            pnl_pct = pos.get('pnl_percent', 0)
            
            pnl_emoji = "💰" if pnl >= 0 else "📉"
            
            lines.append(f"│  {symbol:<10} {side:<4} {amount:>10.4f}  {pnl_emoji} ${pnl:>10,.2f} ({pnl_pct:>+.2f}%)    │")
        
        lines.append("└──────────────────────────────────────────────────────────────────┘")
        
        return "\n".join(lines)

    def _render_metrics(self, metrics: Dict[str, Any]) -> str:
        """Render performance metrics section"""
        total_trades = metrics.get('total_trades', 0)
        win_rate = metrics.get('win_rate', 0)
        total_pnl = metrics.get('total_pnl', 0)
        sharpe = metrics.get('sharpe_ratio', 0)
        
        return f"""
┌──────────────────────────────────────────────────────────────────┐
│ 📈 PERFORMANCE METRICS                                            │
├──────────────────────────────────────────────────────────────────┤
│  Total Trades:   {total_trades:>10}                               │
│  Win Rate:       {win_rate:>10.1f}%                              │
│  Total P&L:      ${total_pnl:>10,.2f}                            │
│  Sharpe Ratio:   {sharpe:>10.2f}                               │
└──────────────────────────────────────────────────────────────────┘
"""

    def _render_status(self, status: Dict[str, Any]) -> str:
        """Render system status section"""
        mode = status.get('mode', 'unknown')
        emergency = status.get('emergency_stop', False)
        agents = status.get('agents', [])
        
        mode_emoji = "🔴 LIVE" if mode == 'live' else "📄 PAPER" if mode == 'paper' else "⚪ TEST"
        emergency_status = "🚨 ACTIVE" if emergency else "✓ OK"
        
        return f"""
┌──────────────────────────────────────────────────────────────────┐
│ ⚙️  SYSTEM STATUS                                                 │
├──────────────────────────────────────────────────────────────────┤
│  Mode:           {mode_emoji:<10}                                │
│  Emergency Stop: {emergency_status:<10}                                │
│  Active Agents:  {len(agents):>10}                               │
└──────────────────────────────────────────────────────────────────┘
"""

    def _render_footer(self) -> str:
        """Render dashboard footer"""
        return f"""
┌──────────────────────────────────────────────────────────────────┐
│  Press Ctrl+C to exit  │  Refresh: {self.refresh_interval}s                       │
└──────────────────────────────────────────────────────────────────┘
"""


# Standalone dashboard with mock data for testing
class MockTradingSystem:
    """Mock trading system for dashboard testing"""
    
    def get_portfolio(self) -> Dict[str, Any]:
        return {
            'balance': 10523.45,
            'total_value': 12847.32,
            'total_pnl': 2847.32,
            'total_pnl_percent': 28.47
        }
    
    def get_positions(self) -> list:
        return [
            {'symbol': 'BTC/USDT', 'side': 'buy', 'amount': 0.15, 'pnl': 450.00, 'pnl_percent': 12.5},
            {'symbol': 'ETH/USDT', 'side': 'buy', 'amount': 2.5, 'pnl': -125.50, 'pnl_percent': -3.2},
        ]
    
    def get_metrics(self) -> Dict[str, Any]:
        return {
            'total_trades': 47,
            'win_rate': 68.1,
            'total_pnl': 2847.32,
            'sharpe_ratio': 1.85
        }
    
    def get_status(self) -> Dict[str, Any]:
        return {
            'mode': 'paper',
            'emergency_stop': False,
            'agents': ['mayor', 'researcher', 'trader', 'risk_manager']
        }


async def main():
    """Run dashboard with mock data"""
    from config import setup_logging
    setup_logging()
    
    mock_system = MockTradingSystem()
    dashboard = Dashboard(refresh_interval=3, trading_system=mock_system)
    
    print("Starting dashboard with mock data...")
    await dashboard.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
