"""
Performance Tracker for AI Trading System
Tracks and analyzes trading performance metrics
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from loguru import logger
import pandas as pd


@dataclass
class TradeRecord:
    """Record of a single trade"""
    timestamp: datetime
    action: str
    pair: str
    amount: float
    price: float
    pnl: float = 0.0
    pnl_percent: float = 0.0
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceTracker:
    """
    Track and analyze trading performance
    
    Metrics tracked:
    - Total P&L
    - Win rate
    - Average win/loss
    - Sharpe ratio
    - Max drawdown
    - Trade count
    """

    def __init__(self, data_dir: str = "./data"):
        """
        Initialize performance tracker
        
        Args:
            data_dir: Directory for storing trade data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.trades_file = self.data_dir / "trades.jsonl"
        self.metrics_file = self.data_dir / "metrics.json"
        self.daily_file = self.data_dir / "daily_pnl.jsonl"
        
        # In-memory cache
        self.trades: List[TradeRecord] = []
        self.daily_pnl: Dict[str, float] = {}
        
        logger.info("Performance Tracker initialized")

    def record_trade(
        self,
        action: str,
        pair: str,
        amount: float,
        price: float,
        pnl: float = 0.0,
        pnl_percent: float = 0.0,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a trade
        
        Args:
            action: BUY or SELL
            pair: Trading pair
            amount: Trade amount
            price: Trade price
            pnl: Profit/loss (realized)
            pnl_percent: P&L percentage
            reason: Trade reason
            metadata: Additional data
        """
        trade = TradeRecord(
            timestamp=datetime.now(),
            action=action,
            pair=pair,
            amount=amount,
            price=price,
            pnl=pnl,
            pnl_percent=pnl_percent,
            reason=reason,
            metadata=metadata or {}
        )
        
        self.trades.append(trade)
        
        # Save to file
        self._save_trade(trade)
        
        # Update daily P&L
        self._update_daily_pnl(pnl)
        
        logger.info(f"📊 Trade recorded: {action} {pair} | P&L: ${pnl:+,.2f}")

    def _save_trade(self, trade: TradeRecord) -> None:
        """Save trade to JSONL file"""
        with open(self.trades_file, 'a') as f:
            f.write(json.dumps({
                'timestamp': trade.timestamp.isoformat(),
                'action': trade.action,
                'pair': trade.pair,
                'amount': trade.amount,
                'price': trade.price,
                'pnl': trade.pnl,
                'pnl_percent': trade.pnl_percent,
                'reason': trade.reason,
                'metadata': trade.metadata
            }) + '\n')

    def _update_daily_pnl(self, pnl: float) -> None:
        """Update daily P&L tracking"""
        today = datetime.now().strftime('%Y-%m-%d')
        self.daily_pnl[today] = self.daily_pnl.get(today, 0.0) + pnl
        
        # Save daily P&L
        with open(self.daily_file, 'a') as f:
            f.write(json.dumps({
                'date': today,
                'pnl': pnl,
                'total': self.daily_pnl[today]
            }) + '\n')

    def load_trades(self, days: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load trades from file
        
        Args:
            days: Number of days to load (None for all)
            
        Returns:
            List of trade records
        """
        if not self.trades_file.exists():
            return []
        
        trades = []
        cutoff = datetime.now() - timedelta(days=days) if days else None
        
        with open(self.trades_file, 'r') as f:
            for line in f:
                trade = json.loads(line)
                trade_time = datetime.fromisoformat(trade['timestamp'])
                
                if cutoff and trade_time < cutoff:
                    continue
                
                trades.append(trade)
        
        return trades

    def calculate_metrics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics
        
        Returns:
            Metrics dictionary
        """
        trades = self.load_trades()
        
        if not trades:
            return self._empty_metrics()
        
        # Basic metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        
        # P&L metrics
        total_pnl = sum(t['pnl'] for t in trades)
        total_pnl_percent = sum(t['pnl_percent'] for t in trades) / total_trades if total_trades > 0 else 0
        
        avg_win = sum(t['pnl'] for t in winning_trades) / win_count if win_count > 0 else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / loss_count if loss_count > 0 else 0
        
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown(trades)
        
        # Sharpe ratio (simplified)
        sharpe_ratio = self._calculate_sharpe_ratio(trades)
        
        # Trade breakdown
        buy_trades = [t for t in trades if t['action'] == 'BUY']
        sell_trades = [t for t in trades if t['action'] == 'SELL']
        
        metrics = {
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_pnl_percent': total_pnl_percent,
            'average_win': avg_win,
            'average_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'first_trade': trades[0]['timestamp'] if trades else None,
            'last_trade': trades[-1]['timestamp'] if trades else None,
        }
        
        # Save metrics
        with open(self.metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)
        
        return metrics

    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'total_pnl_percent': 0.0,
            'average_win': 0.0,
            'average_loss': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'buy_trades': 0,
            'sell_trades': 0,
        }

    def _calculate_max_drawdown(self, trades: List[Dict]) -> float:
        """Calculate maximum drawdown percentage"""
        if not trades:
            return 0.0
        
        cumulative_pnl = 0
        peak_pnl = 0
        max_drawdown = 0
        
        for trade in trades:
            cumulative_pnl += trade['pnl']
            peak_pnl = max(peak_pnl, cumulative_pnl)
            drawdown = (peak_pnl - cumulative_pnl) / peak_pnl if peak_pnl > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown * 100

    def _calculate_sharpe_ratio(self, trades: List[Dict]) -> float:
        """Calculate Sharpe ratio (simplified)"""
        if len(trades) < 2:
            return 0.0
        
        returns = [t['pnl_percent'] for t in trades]
        
        try:
            df = pd.DataFrame(returns)
            mean_return = df.mean().iloc[0]
            std_return = df.std().iloc[0]
            
            if std_return == 0:
                return 0.0
            
            # Annualize (assuming daily returns)
            sharpe = (mean_return / std_return) * (252 ** 0.5)
            return sharpe
        except Exception:
            return 0.0

    def get_daily_performance(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get daily performance for last N days
        
        Args:
            days: Number of days
            
        Returns:
            List of daily performance records
        """
        if not self.daily_file.exists():
            return []
        
        daily = []
        cutoff = datetime.now() - timedelta(days=days)
        
        with open(self.daily_file, 'r') as f:
            seen_dates = set()
            for line in f:
                record = json.loads(line)
                date = record['date']
                
                if date in seen_dates:
                    continue
                
                record_date = datetime.strptime(date, '%Y-%m-%d')
                if record_date >= cutoff:
                    seen_dates.add(date)
                    daily.append(record)
        
        return sorted(daily, key=lambda x: x['date'], reverse=True)

    def generate_report(self, days: int = 30) -> str:
        """
        Generate performance report
        
        Args:
            days: Number of days to include
            
        Returns:
            Formatted report string
        """
        metrics = self.calculate_metrics()
        daily = self.get_daily_performance(7)
        
        report = f"""
╔══════════════════════════════════════════════════════╗
║          AI TRADING PERFORMANCE REPORT               ║
╠══════════════════════════════════════════════════════╣
║  Period: Last {days} days                              ║
╠══════════════════════════════════════════════════════╣

📊 TRADING STATISTICS
├─ Total Trades:     {metrics['total_trades']}
├─ Winning Trades:   {metrics['winning_trades']}
├─ Losing Trades:    {metrics['losing_trades']}
└─ Win Rate:         {metrics['win_rate']:.1f}%

💰 PROFIT & LOSS
├─ Total P&L:        ${metrics['total_pnl']:+,.2f}
├─ Total P&L %:      {metrics['total_pnl_percent']:+.2f}%
├─ Average Win:      ${metrics['average_win']:+,.2f}
├─ Average Loss:     ${metrics['average_loss']:+,.2f}
└─ Profit Factor:    {metrics['profit_factor']:.2f}

📈 RISK METRICS
├─ Max Drawdown:     {metrics['max_drawdown']:.2f}%
└─ Sharpe Ratio:     {metrics['sharpe_ratio']:.2f}

📅 RECENT DAILY PERFORMANCE
"""
        
        for day in daily[:5]:
            pnl = day['pnl']
            emoji = "💰" if pnl > 0 else "📉"
            report += f"├─ {day['date']}: {emoji} ${pnl:+,.2f}\n"
        
        report += """
╚══════════════════════════════════════════════════════╝
"""
        
        return report

    def get_status(self) -> Dict[str, Any]:
        """Get current tracker status"""
        return {
            'total_trades': len(self.trades),
            'trades_file': str(self.trades_file),
            'metrics_file': str(self.metrics_file),
            'last_updated': datetime.now().isoformat()
        }
