#!/usr/bin/env python3
"""
Web Dashboard for AI Trading Bot
Reads stats from database with caching - minimal impact on bot performance
"""

from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '/home/yeasir/projects/ai-exp')

app = Flask(__name__)

# Cache for dashboard data (2 second cache to avoid DB load)
dashboard_cache = {
    'data': None,
    'timestamp': None,
    'cache_duration': 2  # seconds
}

def get_dashboard_data():
    """Get dashboard data from database with caching"""
    now = datetime.now()
    
    # Return cached data if still valid
    if dashboard_cache['data'] and dashboard_cache['timestamp']:
        age = (now - dashboard_cache['timestamp']).total_seconds()
        if age < dashboard_cache['cache_duration']:
            return dashboard_cache['data']
    
    # Fetch fresh data from database
    try:
        from trading.state_manager import get_state_manager
        sm = get_state_manager()
        
        # Get data from database
        capital = sm.get_capital()
        profit_stats = sm.get_profit_stats()
        trades = sm.get_trade_history(limit=10)
        positions = sm.get_open_positions()
        
        # Calculate totals
        total_trades = len(sm.get_trade_history(limit=1000))
        winning_trades = sum(1 for t in sm.get_trade_history(limit=1000) if t.get('pnl', 0) > 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Build dashboard data
        data = {
            'total_profit': profit_stats.get('total_profit', 0),
            'today_profit': profit_stats.get('total_profit', 0),  # Same as total for now
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': round(win_rate, 2),
            'capital': capital.get('total', 15.0),
            'arb_pool': capital.get('arb_pool', 13.5),
            'arb_used': capital.get('arb_used', 0),
            'arb_available': capital.get('arb_pool', 13.5) - capital.get('arb_used', 0),
            'launch_pool': capital.get('launch_pool', 1.5),
            'launch_used': capital.get('launch_used', 0),
            'launch_available': capital.get('launch_pool', 1.5) - capital.get('launch_used', 0),
            'open_positions': len(positions),
            'last_update': now.isoformat()
        }
        
        # Update cache
        dashboard_cache['data'] = data
        dashboard_cache['timestamp'] = now
        
        return data
        
    except Exception as e:
        # Return default data on error
        return {
            'total_profit': 0.0,
            'today_profit': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'win_rate': 0,
            'capital': 15.0,
            'arb_pool': 13.5,
            'arb_used': 0.0,
            'arb_available': 13.5,
            'launch_pool': 1.5,
            'launch_used': 0.0,
            'launch_available': 1.5,
            'open_positions': 0,
            'last_update': now.isoformat(),
            'error': str(e)
        }

@app.route('/')
def dashboard():
    """Serve the HTML dashboard"""
    return render_template('dashboard.html')

@app.route('/api/stats')
def get_stats():
    """Get stats from database (with caching)"""
    return jsonify(get_dashboard_data())

@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/api/trades')
def get_trades():
    """Get recent trades"""
    try:
        from trading.state_manager import get_state_manager
        sm = get_state_manager()
        trades = sm.get_trade_history(limit=50)
        return jsonify(trades)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/positions')
def get_positions():
    """Get open positions"""
    try:
        from trading.state_manager import get_state_manager
        sm = get_state_manager()
        positions = sm.get_open_positions()
        return jsonify(positions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════╗")
    print("║     AI Trading Bot - Web Dashboard                    ║")
    print("╚═══════════════════════════════════════════════════════╝")
    print("")
    print("📊 Dashboard URL: http://localhost:8080")
    print("⚡ Reads from database (2 second cache)")
    print("")
    print("Press Ctrl+C to stop")
    print("")
    
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
