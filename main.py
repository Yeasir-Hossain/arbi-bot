#!/usr/bin/env python3
"""
HYBRID TRADING BOT - Main Entry Point
90% Arbitrage + 10% Token Launches
Starting Capital: $15

Run with:
    python main.py --mode testnet --strategy hybrid
    python main.py --mode live --strategy hybrid --capital 15
"""

import asyncio
import signal
import sys
import argparse
from datetime import datetime
from pathlib import Path
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import config, setup_logging, ensure_directories
from exchange import ExchangeClient, ExchangePriceMonitor, MultiExchangeManager
from trading.capital_manager import CapitalManager
from trading.arbitrage_engine import ArbitrageEngine
from trading.launch_monitor import LaunchMonitor
from trading.launch_hunter import LaunchHunter
from trading.smart_pair_selector import SmartPairSelector, get_pair_selector
from trading.state_manager import StateManager, get_state_manager
from monitoring import PerformanceTracker, Dashboard
import json

# Dashboard stats (in-memory, instant access - no DB delay)
dashboard_stats = {
    'total_profit': 0.0,
    'today_profit': 0.0,
    'total_trades': 0,
    'winning_trades': 0,
    'capital': 15.0,
    'last_update': None,
    'arb_pool': 13.5,
    'arb_used': 0.0,
    'arb_available': 13.5,
    'launch_pool': 1.5,
    'launch_used': 0.0,
    'launch_available': 1.5
}

# Dashboard stats file (backup)
DASHBOARD_STATS_FILE = Path(__file__).parent / "data" / "dashboard_stats.json"

def update_dashboard_stats_sync(capital_manager, starting_capital=15.0):
    """Update dashboard stats SYNCHRONOUSLY (no await, no delay)"""
    try:
        # Calculate current profit from capital
        current_profit = capital_manager.total_capital - starting_capital
        
        # Update stats dict (in-memory, instant)
        dashboard_stats['total_profit'] = current_profit
        dashboard_stats['today_profit'] = current_profit
        dashboard_stats['capital'] = capital_manager.total_capital
        dashboard_stats['last_update'] = datetime.now().isoformat()
        
        # Add capital allocation (synchronous, no await)
        if capital_manager:
            dashboard_stats['arb_pool'] = capital_manager.arbitrage_pool
            dashboard_stats['arb_used'] = capital_manager.arb_used
            dashboard_stats['arb_available'] = capital_manager.arbitrage_pool - capital_manager.arb_used
            dashboard_stats['launch_pool'] = capital_manager.launch_pool
            dashboard_stats['launch_used'] = capital_manager.launch_used
            dashboard_stats['launch_available'] = capital_manager.launch_pool - capital_manager.launch_used
        
        # Write to file as backup (synchronous)
        try:
            DASHBOARD_STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(DASHBOARD_STATS_FILE, 'w') as f:
                json.dump(dashboard_stats, f, indent=2)
        except:
            pass  # File write failed, but stats are in memory
            
    except Exception as e:
        logger.debug(f"Failed to update dashboard stats: {e}")


class HybridTradingBot:
    """
    Hybrid Trading Bot: Arbitrage + Token Launches
    
    Capital Allocation:
    - 90% Arbitrage (steady income)
    - 10% Token Launches (moonshot potential)
    """

    def __init__(
        self,
        mode: str = "testnet",
        initial_capital: float = 15.0,
        trading_pair: str = "ETH/USDT"
    ):
        """
        Initialize hybrid trading bot
        
        Args:
            mode: Trading mode (testnet, live)
            initial_capital: Starting capital in USDT
            trading_pair: Primary trading pair
        """
        self.mode = mode
        self.initial_capital = initial_capital
        self.trading_pair = trading_pair
        
        # Setup
        ensure_directories()
        setup_logging(config.log_level)
        
        self.logger = logger
        self.running = False
        self.iteration = 0
        
        # Components (initialized in initialize())
        self.capital_manager = None
        self.binance_client = None
        self.price_monitor = None
        self.arb_engine = None
        self.launch_monitor = None
        self.performance_tracker = None
        self.dashboard = None
        
        # State
        self.positions = []
        self.total_profit = 0.0
        self.total_loss = 0.0
        self.trades_today = 0
        self.launches_attempted = 0

    async def initialize(self) -> bool:
        """Initialize all components"""
        try:
            self.logger.info("=" * 60)
            self.logger.info("HYBRID TRADING BOT INITIALIZING")
            self.logger.info("=" * 60)
            self.logger.info(f"Mode: {self.mode.upper()}")
            self.logger.info(f"Initial Capital: ${self.initial_capital}")
            self.logger.info(f"Trading Pair: {self.trading_pair}")
            
            # Initialize capital manager
            self.logger.info("Initializing Capital Manager...")
            self.capital_manager = CapitalManager(
                total_capital=self.initial_capital,
                arb_allocation=0.90,
                launch_allocation=0.10
            )
            self.logger.info(f"  Arb Pool: ${self.capital_manager.arbitrage_pool:.2f}")
            self.logger.info(f"  Launch Pool: ${self.capital_manager.launch_pool:.2f}")
            
            # Initialize Binance client
            self.logger.info("Initializing Binance Client...")
            self.binance_client = ExchangeClient(
                exchange_name="binance",
                api_key=config.exchange.primary_api_key_plain,
                api_secret=config.exchange.primary_api_secret_plain,
                testnet=(self.mode == "testnet")
            )
            
            # Connect to Binance
            if await self.binance_client.connect():
                self.logger.info("✓ Binance connected")
            else:
                self.logger.error("✗ Binance connection failed")
                return False
            
            # Initialize price monitor
            self.logger.info("Initializing Price Monitor...")
            self.price_monitor = ExchangePriceMonitor()
            await self.price_monitor.start()
            self.logger.info("✓ Price monitor started")
            
            # Initialize arbitrage engine
            self.logger.info("Initializing Arbitrage Engine...")
            self.arb_engine = ArbitrageEngine(
                capital_manager=self.capital_manager,
                binance_client=self.binance_client,
                price_monitor=self.price_monitor,
                min_profit_threshold=config.trading.min_arb_profit_percent,  # From .env
                max_position_percent=config.trading.max_position_size,
                stop_loss_percent=config.trading.stop_loss_percent
            )
            self.logger.info(f"✓ Arbitrage engine ready (threshold: {config.trading.min_arb_profit_percent:.1%})")
            
            # Initialize launch monitor
            self.logger.info("Initializing Launch Monitor...")
            self.launch_monitor = LaunchMonitor(
                capital_manager=self.capital_manager,
                binance_client=self.binance_client
            )
            self.logger.info("✓ Launch monitor ready")
            
            # Initialize launch hunter (for CLANKER-style launches)
            self.logger.info("🎯 Initializing Launch Hunter...")
            self.launch_hunter = LaunchHunter(
                capital_manager=self.capital_manager,
                binance_client=self.binance_client
            )
            # Start launch hunting in background (non-blocking)
            asyncio.create_task(self.launch_hunter.start_hunting())
            self.logger.info("✓ Launch hunter ready (hunting for moonshots!)")
            
            # Initialize smart pair selector (auto-selects best pairs)
            self.logger.info("Initializing Smart Pair Selector...")
            self.pair_selector = SmartPairSelector(
                initial_pairs=config.exchange.get_trading_pairs_list()
            )
            self.logger.info(f"✓ Pair selector ready (monitoring {len(self.pair_selector.pair_stats)} pairs)")
            self.logger.info(f"  Will auto-focus on most profitable pairs")

            # Initialize state manager (loads saved state)
            self.logger.info("Initializing State Manager...")
            self.state_manager = get_state_manager()
            
            # Restore capital from saved state
            saved_capital = self.state_manager.get_capital()
            if saved_capital['total'] > 0:
                self.capital_manager.total_capital = saved_capital['total']
                self.capital_manager.arbitrage_pool = saved_capital['arb_pool']
                self.capital_manager.launch_pool = saved_capital['launch_pool']
                self.capital_manager.arb_used = saved_capital['arb_used']
                self.capital_manager.launch_used = saved_capital['launch_used']
                self.logger.info(f"✓ State restored from previous session")
                self.logger.info(f"  Total: ${self.capital_manager.total_capital:.2f}")
                self.logger.info(f"  Arb used: ${self.capital_manager.arb_used:.2f}")
                self.logger.info(f"  Open positions: {self.state_manager.get_position_count()}")
            else:
                self.logger.info("✓ Starting fresh (no saved state)")
            
            # Restore open positions
            open_positions = self.state_manager.get_open_positions()
            if open_positions:
                self.positions.extend(open_positions)
                self.logger.info(f"  Restored {len(open_positions)} open positions")

            # Initialize performance tracker
            self.performance_tracker = PerformanceTracker()

            # Initialize dashboard
            self.dashboard = Dashboard(
                refresh_interval=5,
                trading_system=self
            )
            
            self.logger.info("=" * 60)
            self.logger.info("ALL COMPONENTS INITIALIZED")
            self.logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False

    async def run(self) -> None:
        """Run the hybrid trading bot"""
        if not await self.initialize():
            self.logger.error("Failed to initialize bot")
            return
        
        self.running = True
        
        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self.shutdown())
            )
        
        self.logger.info("🚀 HYBRID TRADING BOT STARTED")
        self.logger.info(f"💰 Capital: ${self.initial_capital}")
        self.logger.info(f"   ├─ Arbitrage: ${self.capital_manager.arbitrage_pool:.2f}")
        self.logger.info(f"   └─ Launches: ${self.capital_manager.launch_pool:.2f}")
        self.logger.info("")
        self.logger.info("Press Ctrl+C to stop")
        
        # Save initial balance to database
        try:
            self.state_manager.save_initial_balance(self.initial_capital)
            self.logger.info(f"✓ Initial balance saved: ${self.initial_capital:.2f}")
        except Exception as e:
            self.logger.warning(f"Failed to save initial balance: {e}")
        
        try:
            # Run main trading loop and dashboard in parallel
            await asyncio.gather(
                self.trading_loop(),
                self.dashboard.run()
            )
        except KeyboardInterrupt:
            self.logger.info("\nShutdown requested...")
        finally:
            await self.shutdown()

    async def trading_loop(self) -> None:
        """Main trading loop"""
        self.logger.info("Starting trading loop...")
        
        while self.running:
            try:
                self.iteration += 1
                
                # === ARBITRAGE TRADING (Every 10 seconds) ===
                # Get best performing pairs from selector
                best_pairs = self.pair_selector.get_top_pairs(3)
                
                arb_opportunity = await self.arb_engine.find_and_execute(pairs_to_scan=best_pairs)
                
                if arb_opportunity:
                    self.positions.append(arb_opportunity)
                    self.trades_today += 1
                    
                    # Record opportunity for pair selector
                    self.pair_selector.record_opportunity(
                        arb_opportunity['pair'],
                        taken=True
                    )

                    self.logger.info(f"📊 ARB TRADE #{self.trades_today}")
                    self.logger.info(f"   Pair: {arb_opportunity['pair']}")
                    self.logger.info(f"   Bought @ ${arb_opportunity['buy_price']:.2f}")
                    self.logger.info(f"   Target: ${arb_opportunity['target_price']:.2f}")
                    self.logger.info(f"   Expected: {arb_opportunity['expected_profit']:.2%}")

                    # Save state with new position
                    self.state_manager.add_position(arb_opportunity)
                    
                    # Record BUY trade in history
                    self.state_manager.add_trade({
                        'type': 'arb',
                        'symbol': arb_opportunity['symbol'],
                        'action': 'BUY',
                        'amount': arb_opportunity['amount'],
                        'price': arb_opportunity['buy_price'],
                        'pnl': 0,
                        'pnl_percent': 0,
                        'data': {
                            'target_price': arb_opportunity['target_price'],
                            'stop_price': arb_opportunity.get('stop_price', 0),
                            'entry_cost': arb_opportunity.get('entry_cost', 0)
                        }
                    })
                    
                    self.state_manager.update_capital({
                        'arb_used': self.capital_manager.arb_used,
                        'total': self.capital_manager.total_capital
                    })
                
                # Check exits for existing arbitrage positions
                for position in self.positions[:]:
                    if position.get('type') == 'arbitrage':
                        exit_signal = await self.arb_engine.check_exit(position)
                        
                        if exit_signal:
                            self.positions.remove(position)
                            
                            if exit_signal['action'] == 'sell':
                                profit = exit_signal['profit']
                                self.total_profit += profit
                                
                                distribution = self.capital_manager.update_after_profit(
                                    profit, 'arbitrage'
                                )
                                
                                # Record trade performance for pair selector
                                self.pair_selector.record_trade(
                                    position['pair'],
                                    profit,
                                    is_winner=True
                                )

                                self.logger.info(f"💰 ARB PROFIT: ${profit:.6f}")
                                self.logger.info(f"   Reinvest: ${distribution['reinvest']:.6f} (stays in bot)")

                                # Check if withdrawal threshold is met
                                total_profit = self.state_manager.get_total_profit()
                                if total_profit >= config.trading.min_withdraw_threshold:
                                    self.logger.info(f"   Withdraw: ${distribution['withdraw']:.6f} (WILL BE SENT TO WALLET)")
                                else:
                                    self.logger.info(f"   Withdraw: ${distribution['withdraw']:.6f} (LOGGED ONLY - threshold not met: ${total_profit:.2f}/${config.trading.min_withdraw_threshold:.2f})")

                                self.logger.info(f"   Reserve: ${distribution['reserve']:.6f} (logged)")

                                # Save total profit to database
                                self.state_manager.update_profit(profit)

                                # Save trade to history
                                self.state_manager.add_trade({
                                    'type': 'arb',
                                    'symbol': position['symbol'],
                                    'action': 'SELL',
                                    'amount': position['amount'],
                                    'price': exit_signal.get('exit_price', 0),
                                    'pnl': profit,
                                    'pnl_percent': exit_signal.get('profit_percent', 0),
                                    'data': {
                                        'buy_price': position['buy_price'],
                                        'target_price': position['target_price'],
                                        'entry_cost': position.get('entry_cost', 0)
                                    }
                                })

                                # Update dashboard stats SYNCHRONOUSLY (instant, no delay)
                                update_dashboard_stats_sync(self.capital_manager, starting_capital=15.0)

                                # Record in performance tracker
                                self.performance_tracker.record_trade(
                                    action='ARB',
                                    pair=self.trading_pair,
                                    amount=position['amount'],
                                    price=position['buy_price'],
                                    pnl=profit,
                                    pnl_percent=exit_signal.get('profit_percent', 0)
                                )
                            
                            elif exit_signal['action'] == 'stop_loss':
                                loss = exit_signal['loss']
                                self.total_loss += loss
                                
                                self.logger.warning(f"🛑 ARB STOP LOSS: ${loss:.4f}")
                
                # === LAUNCH MONITORING (Every 5 minutes) ===
                if self.iteration % 30 == 0:  # Every 5 minutes (30 × 10s)
                    await self.launch_monitor.monitor_launches()
                    
                    # Check for new launch opportunities
                    launches = await self.launch_monitor.get_upcoming_launches()
                    
                    if launches:
                        self.logger.info(f"🚀 Found {len(launches)} upcoming launches")
                        
                        for launch in launches:
                            if not launch.get('tracked', False):
                                score = await self.launch_monitor.evaluate_launch(launch)
                                
                                if score > 0.7:  # High confidence
                                    self.logger.info(f"   ✓ Buying: {launch['symbol']} (score: {score:.2f})")
                                    position = await self.launch_monitor.buy_launch(launch)
                                    
                                    if position:
                                        self.positions.append(position)
                                        self.launches_attempted += 1
                                        launch['tracked'] = True
                                else:
                                    self.logger.info(f"   ✗ Skipping: {launch['symbol']} (score: {score:.2f})")
                
                # === LAUNCH HUNTING (Every 2 minutes) - CLANKER HUNTER ===
                if self.iteration % 12 == 0:  # Every 2 minutes (12 × 10s)
                    try:
                        # Scan for new launches on Base, Pump.fun, Uniswap
                        new_launches = await self.launch_hunter.scan_all_platforms()
                        
                        if new_launches:
                            self.logger.info(f"🎯 Launch Hunter found {len(new_launches)} new launches")
                            
                            for launch in new_launches:
                                # Skip if already tracked
                                if any(l.get('address') == launch.get('address') 
                                      for l in self.launch_hunter.tracked_launches):
                                    continue
                                
                                # Evaluate launch
                                score = await self.launch_hunter.evaluate_launch(launch)
                                
                                if score >= self.launch_hunter.min_score:
                                    self.logger.info(f"   🚀 BUYING: {launch.get('symbol')} @ ${score:.2f} score")
                                    position = await self.launch_hunter.buy_launch(launch)
                                    
                                    if position:
                                        self.positions.append(position)
                                        self.launches_attempted += 1
                                        self.launch_hunter.tracked_launches.append(launch)
                                else:
                                    if score > 0.4:  # Log near-misses
                                        self.logger.info(f"   ⏸️ Skipping: {launch.get('symbol')} (score: {score:.2f})")
                        
                    except Exception as e:
                        self.logger.debug(f"Launch hunter error: {e}")
                
                # === STATUS REPORT (Every hour) ===
                if self.iteration % 360 == 0:  # Every hour (360 × 10s)
                    self.logger.info("")
                    self.logger.info("=" * 50)
                    self.logger.info("📈 HOURLY STATUS")
                    self.logger.info("=" * 50)
                    self.logger.info(f"Total Capital: ${self.capital_manager.total_capital:.2f}")
                    self.logger.info(f"Arb Pool: ${self.capital_manager.arbitrage_pool:.2f}")
                    self.logger.info(f"Launch Pool: ${self.capital_manager.launch_pool:.2f}")
                    self.logger.info(f"Open Positions: {len(self.positions)}")
                    self.logger.info(f"Trades Today: {self.trades_today}")
                    self.logger.info(f"Launches Attempted: {self.launches_attempted}")
                    self.logger.info(f"Total Profit: ${self.total_profit:.4f}")
                    self.logger.info(f"Total Loss: ${self.total_loss:.4f}")
                    self.logger.info(f"Net P&L: ${self.total_profit - self.total_loss:.4f}")
                    
                    # Show pair performance
                    self.logger.info("")
                    self.logger.info(self.pair_selector.get_performance_report())
                    self.logger.info("=" * 50)
                    self.logger.info("")
                
                await asyncio.sleep(10)  # 10 second loop
                
            except Exception as e:
                self.logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(5)

    def get_portfolio(self) -> dict:
        """Get current portfolio status"""
        return {
            'total_capital': self.capital_manager.total_capital if self.capital_manager else 0,
            'arb_pool': self.capital_manager.arbitrage_pool if self.capital_manager else 0,
            'launch_pool': self.capital_manager.launch_pool if self.capital_manager else 0,
            'open_positions': len(self.positions),
            'total_profit': self.total_profit,
            'total_loss': self.total_loss,
            'net_pnl': self.total_profit - self.total_loss
        }

    def get_positions(self) -> list:
        """Get open positions"""
        return self.positions

    def get_metrics(self) -> dict:
        """Get performance metrics"""
        return self.performance_tracker.calculate_metrics() if self.performance_tracker else {}

    def get_status(self) -> dict:
        """Get system status"""
        return {
            'mode': self.mode,
            'running': self.running,
            'iteration': self.iteration,
            'trades_today': self.trades_today,
            'launches_attempted': self.launches_attempted,
            'capital': self.capital_manager.total_capital if self.capital_manager else 0
        }

    async def shutdown(self) -> None:
        """Graceful shutdown"""
        if not self.running:
            return
        
        self.logger.info("Shutting down...")
        self.running = False
        
        # Close all positions (optional - can comment out to keep positions open)
        self.logger.info(f"Closing {len(self.positions)} open positions...")
        for position in self.positions[:]:
            if position.get('type') == 'arbitrage':
                await self.binance_client.close_position(position)
        
        # Disconnect from exchanges
        await self.binance_client.disconnect()
        await self.price_monitor.stop()
        
        # Generate final report
        if self.performance_tracker:
            report = self.performance_tracker.generate_report()
            self.logger.info(report)
        
        self.logger.info("=" * 60)
        self.logger.info("BOT SHUTDOWN COMPLETE")
        self.logger.info(f"Final Capital: ${self.capital_manager.total_capital:.2f}")
        self.logger.info(f"Total Profit: ${self.total_profit:.4f}")
        self.logger.info(f"Total Loss: ${self.total_loss:.4f}")
        self.logger.info(f"Net P&L: ${self.total_profit - self.total_loss:.4f}")
        self.logger.info("=" * 60)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Hybrid Trading Bot')
    parser.add_argument(
        '--mode',
        choices=['testnet', 'live'],
        default='testnet',
        help='Trading mode (default: testnet)'
    )
    parser.add_argument(
        '--capital',
        type=float,
        default=15.0,
        help='Initial capital in USDT (default: 15)'
    )
    parser.add_argument(
        '--pair',
        default='ETH/USDT',
        help='Primary trading pair (default: ETH/USDT)'
    )
    
    args = parser.parse_args()
    
    bot = HybridTradingBot(
        mode=args.mode,
        initial_capital=args.capital,
        trading_pair=args.pair
    )
    
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
