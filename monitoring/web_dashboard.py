"""
Lightweight aiohttp web dashboard for Arbi-Bot.
Runs inside the same asyncio event loop as the bot.
"""

import json
from datetime import datetime
from aiohttp import web
from loguru import logger


def create_app(bot=None) -> web.Application:
    """Create and return the aiohttp web application."""
    app = web.Application()
    app['bot'] = bot
    app['start_time'] = datetime.now()

    app.router.add_get('/', handle_index)
    app.router.add_get('/health', handle_health)
    app.router.add_get('/api/status', handle_status)
    app.router.add_get('/api/portfolio', handle_portfolio)
    app.router.add_get('/api/trades', handle_trades)

    return app


async def handle_health(request: web.Request) -> web.Response:
    """Health check endpoint for Docker/podman"""
    return web.json_response({'status': 'ok'})


async def handle_status(request: web.Request) -> web.Response:
    """Bot status endpoint"""
    bot = request.app.get('bot')
    start_time = request.app.get('start_time', datetime.now())
    uptime = (datetime.now() - start_time).total_seconds()

    data = {
        'uptime_seconds': int(uptime),
        'started_at': start_time.isoformat(),
    }

    if bot:
        data.update(bot.get_status())

    return web.json_response(data)


async def handle_portfolio(request: web.Request) -> web.Response:
    """Portfolio / capital endpoint"""
    bot = request.app.get('bot')

    if bot:
        data = bot.get_portfolio()
        data['positions'] = [
            {k: (v.isoformat() if isinstance(v, datetime) else v)
             for k, v in p.items()}
            for p in bot.get_positions()
        ]
    else:
        data = {'error': 'bot not initialized'}

    return web.json_response(data)


async def handle_trades(request: web.Request) -> web.Response:
    """Recent trade history"""
    bot = request.app.get('bot')

    if bot and hasattr(bot, 'state_manager') and bot.state_manager:
        try:
            trades = bot.state_manager.get_trade_history(limit=50)
            return web.json_response({'trades': trades})
        except Exception as e:
            return web.json_response({'error': str(e)})

    return web.json_response({'trades': []})


async def handle_index(request: web.Request) -> web.Response:
    """Simple HTML status page"""
    bot = request.app.get('bot')
    start_time = request.app.get('start_time', datetime.now())
    uptime = (datetime.now() - start_time).total_seconds()
    hours, remainder = divmod(int(uptime), 3600)
    minutes, seconds = divmod(remainder, 60)

    status = bot.get_status() if bot else {}
    portfolio = bot.get_portfolio() if bot else {}

    html = f"""<!DOCTYPE html>
<html><head><title>Arbi-Bot</title>
<style>body{{font-family:monospace;background:#1a1a2e;color:#e0e0e0;padding:20px;max-width:600px;margin:0 auto}}
h1{{color:#00d4ff}}table{{width:100%;border-collapse:collapse}}td{{padding:4px 8px}}
td:first-child{{color:#888}}.green{{color:#00ff88}}.red{{color:#ff4444}}</style>
<meta http-equiv="refresh" content="10"></head><body>
<h1>Arbi-Bot Dashboard</h1>
<table>
<tr><td>Mode</td><td>{status.get('mode', 'N/A')}</td></tr>
<tr><td>Uptime</td><td>{hours}h {minutes}m {seconds}s</td></tr>
<tr><td>Iteration</td><td>{status.get('iteration', 0)}</td></tr>
<tr><td>Trades Today</td><td>{status.get('trades_today', 0)}</td></tr>
<tr><td>Capital</td><td>${portfolio.get('total_capital', 0):.2f}</td></tr>
<tr><td>Arb Pool</td><td>${portfolio.get('arb_pool', 0):.2f}</td></tr>
<tr><td>Launch Pool</td><td>${portfolio.get('launch_pool', 0):.2f}</td></tr>
<tr><td>Open Positions</td><td>{portfolio.get('open_positions', 0)}</td></tr>
<tr><td>Net P&L</td><td class="{'green' if portfolio.get('net_pnl', 0) >= 0 else 'red'}">${portfolio.get('net_pnl', 0):.4f}</td></tr>
</table>
<p style="color:#555;font-size:0.8em">Auto-refreshes every 10s &bull; <a href="/api/status" style="color:#00d4ff">/api/status</a> &bull; <a href="/api/portfolio" style="color:#00d4ff">/api/portfolio</a> &bull; <a href="/api/trades" style="color:#00d4ff">/api/trades</a></p>
</body></html>"""

    return web.Response(text=html, content_type='text/html')


async def start_web_dashboard(bot=None, host='0.0.0.0', port=8080):
    """Start the web dashboard as an asyncio task (non-blocking)."""
    app = create_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"Web dashboard running on http://{host}:{port}")

    # Keep running forever (this is awaited in asyncio.gather)
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await runner.cleanup()


# Need asyncio for start_web_dashboard
import asyncio
