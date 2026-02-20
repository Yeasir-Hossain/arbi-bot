"""
Smart Pair Selector
Automatically identifies most profitable trading pairs
Adjusts focus based on real performance data
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
from loguru import logger
from dataclasses import dataclass, field


@dataclass
class PairPerformance:
    """Performance metrics for a trading pair"""
    symbol: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    last_trade: datetime = None
    opportunities_seen: int = 0
    opportunities_taken: int = 0
    
    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades
    
    @property
    def profit_factor(self) -> float:
        if self.total_loss == 0:
            return float('inf') if self.total_profit > 0 else 0.0
        return abs(self.total_profit / self.total_loss)
    
    @property
    def avg_profit_per_trade(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return (self.total_profit - self.total_loss) / self.total_trades
    
    @property
    def opportunity_rate(self) -> float:
        if self.opportunities_seen == 0:
            return 0.0
        return self.opportunities_taken / self.opportunities_seen
    
    def score(self) -> float:
        """
        Calculate pair score (0-100)
        Higher = more profitable
        """
        if self.total_trades < 3:
            # Not enough data, use opportunity rate
            return self.opportunity_rate * 50
        
        # Scoring formula:
        # 40% win rate
        # 40% profit factor
        # 20% opportunity rate
        win_rate_score = min(self.win_rate * 100, 100) * 0.4
        profit_factor_score = min(self.profit_factor * 20, 100) * 0.4
        opportunity_score = min(self.opportunity_rate * 100, 100) * 0.2
        
        return win_rate_score + profit_factor_score + opportunity_score


class SmartPairSelector:
    """
    Automatically selects most profitable trading pairs
    
    Features:
    - Tracks performance per pair
    - Ranks pairs by profitability
    - Auto-adjusts focus to best performers
    - Drops underperforming pairs
    """
    
    def __init__(self, initial_pairs: List[str] = None):
        """
        Initialize smart pair selector
        
        Args:
            initial_pairs: List of pairs to start monitoring
        """
        self.pair_stats: Dict[str, PairPerformance] = {}
        self.start_time = datetime.now()
        
        # Initialize with pairs
        initial_pairs = initial_pairs or [
            'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT',
            'ARB/USDT', 'OP/USDT'
        ]
        
        for pair in initial_pairs:
            self.pair_stats[pair] = PairPerformance(symbol=pair)
        
        logger.info("Smart Pair Selector initialized")
        logger.info(f"  Monitoring {len(initial_pairs)} pairs")

    def record_opportunity(self, pair: str, taken: bool = False):
        """
        Record an opportunity (seen or taken)
        
        Args:
            pair: Trading pair symbol
            taken: Whether opportunity was taken
        """
        if pair not in self.pair_stats:
            self.pair_stats[pair] = PairPerformance(symbol=pair)
        
        self.pair_stats[pair].opportunities_seen += 1
        if taken:
            self.pair_stats[pair].opportunities_taken += 1

    def record_trade(self, pair: str, profit: float, is_winner: bool):
        """
        Record a completed trade
        
        Args:
            pair: Trading pair symbol
            profit: Profit/loss amount
            is_winner: Whether trade was profitable
        """
        if pair not in self.pair_stats:
            self.pair_stats[pair] = PairPerformance(symbol=pair)
        
        stats = self.pair_stats[pair]
        stats.total_trades += 1
        stats.last_trade = datetime.now()
        
        if profit > 0:
            stats.winning_trades += 1
            stats.total_profit += profit
        else:
            stats.losing_trades += 1
            stats.total_loss += abs(profit)
        
        logger.info(f"Pair {pair}: Trade recorded | Profit: ${profit:.4f} | {'WIN' if is_winner else 'LOSS'}")

    def get_ranked_pairs(self) -> List[str]:
        """
        Get pairs ranked by profitability (best first)
        
        Returns:
            List of pair symbols, best first
        """
        ranked = sorted(
            self.pair_stats.values(),
            key=lambda p: p.score(),
            reverse=True
        )
        return [p.symbol for p in ranked]

    def get_best_pair(self) -> str:
        """
        Get current best performing pair
        
        Returns:
            Best pair symbol
        """
        ranked = self.get_ranked_pairs()
        return ranked[0] if ranked else 'ETH/USDT'

    def get_worst_pair(self) -> str:
        """
        Get current worst performing pair
        
        Returns:
            Worst pair symbol
        """
        ranked = self.get_ranked_pairs()
        return ranked[-1] if ranked else 'ETH/USDT'

    def get_top_pairs(self, n: int = 3) -> List[str]:
        """
        Get top N performing pairs
        
        Args:
            n: Number of pairs to return
            
        Returns:
            List of top pair symbols
        """
        ranked = self.get_ranked_pairs()
        return ranked[:n]

    def should_drop_pair(self, pair: str, min_score: float = 20.0) -> bool:
        """
        Check if a pair should be dropped (underperforming)
        
        Args:
            pair: Pair symbol
            min_score: Minimum acceptable score
            
        Returns:
            True if should drop
        """
        if pair not in self.pair_stats:
            return False
        
        stats = self.pair_stats[pair]
        
        # Don't drop if not enough data
        if stats.total_trades < 5 and stats.opportunities_seen < 20:
            return False
        
        return stats.score() < min_score

    def get_performance_report(self) -> str:
        """
        Generate performance report
        
        Returns:
            Formatted report string
        """
        ranked = self.get_ranked_pairs()
        
        report = f"""
╔══════════════════════════════════════════════════════╗
║          PAIR PERFORMANCE REPORT                      ║
╠══════════════════════════════════════════════════════╣
║  Ranking by Profitability                             ║
╠══════════════════════════════════════════════════════╣
"""
        
        for i, pair in enumerate(ranked, 1):
            stats = self.pair_stats[pair]
            emoji = "📈" if stats.score() >= 60 else "📉" if stats.score() <= 30 else "➡️"
            
            report += f"║  {i}. {pair:<15} {emoji} Score: {stats.score():.1f}/100          ║\n"
            report += f"║     Trades: {stats.total_trades:<3} Win Rate: {stats.win_rate:.1%}  "
            report += f"Profit: ${stats.total_profit - stats.total_loss:+.2f}          ║\n"
        
        report += f"""╠══════════════════════════════════════════════════════╣
║  Best Pair:  {self.get_best_pair():<15}                          ║
║  Worst Pair: {self.get_worst_pair():<15}                          ║
╚══════════════════════════════════════════════════════╝
"""
        
        return report

    def get_status(self) -> Dict[str, Any]:
        """Get selector status"""
        return {
            'total_pairs': len(self.pair_stats),
            'best_pair': self.get_best_pair(),
            'worst_pair': self.get_worst_pair(),
            'top_3': self.get_top_pairs(3),
            'start_time': self.start_time.isoformat()
        }


# Global instance
_pair_selector = None


def get_pair_selector() -> SmartPairSelector:
    """Get or create global pair selector"""
    global _pair_selector
    if _pair_selector is None:
        _pair_selector = SmartPairSelector()
    return _pair_selector
