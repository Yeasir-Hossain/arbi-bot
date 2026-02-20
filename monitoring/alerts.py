"""
Alert System for AI Trading System
Sends alerts via Telegram, Email, and other channels
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
from loguru import logger
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

from config.config import config


class AlertLevel:
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert:
    """Alert message"""
    
    def __init__(
        self,
        title: str,
        message: str,
        level: str = AlertLevel.INFO,
        category: str = "general"
    ):
        self.title = title
        self.message = message
        self.level = level
        self.category = category
        self.timestamp = datetime.now()
    
    def __str__(self) -> str:
        emoji = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.ERROR: "❌",
            AlertLevel.CRITICAL: "🚨"
        }.get(self.level, "📢")
        
        return f"{emoji} [{self.level.upper()}] {self.title}: {self.message}"


class AlertManager:
    """
    Manage and send alerts through multiple channels
    
    Supported channels:
    - Telegram
    - Email
    - Log file
    """

    def __init__(
        self,
        telegram_bot_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        email_smtp_server: Optional[str] = None,
        email_smtp_port: Optional[int] = None,
        email_username: Optional[str] = None,
        email_password: Optional[str] = None,
        email_recipients: Optional[List[str]] = None
    ):
        """
        Initialize alert manager
        
        Args:
            telegram_bot_token: Telegram bot token
            telegram_chat_id: Telegram chat ID
            email_smtp_server: SMTP server address
            email_smtp_port: SMTP port
            email_username: Email username
            email_password: Email password
            email_recipients: List of email recipients
        """
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.email_smtp_server = email_smtp_server
        self.email_smtp_port = email_smtp_port
        self.email_username = email_username
        self.email_password = email_password
        self.email_recipients = email_recipients or []
        
        # Alert history
        self.alert_history: List[Alert] = []
        
        # Log directory
        self.log_dir = Path("./logs/alerts")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Alert Manager initialized")
        
        # Log configured channels
        if telegram_bot_token and telegram_chat_id:
            logger.info("  Telegram alerts: enabled")
        if email_smtp_server and email_recipients:
            logger.info(f"  Email alerts: enabled ({len(email_recipients)} recipients)")

    async def send_alert(
        self,
        title: str,
        message: str,
        level: str = AlertLevel.INFO,
        category: str = "general",
        channels: Optional[List[str]] = None
    ) -> bool:
        """
        Send an alert
        
        Args:
            title: Alert title
            message: Alert message
            level: Alert level
            category: Alert category
            channels: Specific channels to use (None for all enabled)
            
        Returns:
            True if sent successfully
        """
        alert = Alert(title, message, level, category)
        self.alert_history.append(alert)
        
        # Log alert
        self._log_alert(alert)
        
        # Determine channels
        if channels is None:
            channels = []
            if self.telegram_bot_token:
                channels.append('telegram')
            if self.email_smtp_server:
                channels.append('email')
        
        # Send to each channel
        results = []
        
        if 'telegram' in channels and self.telegram_bot_token:
            results.append(await self._send_telegram(alert))
        
        if 'email' in channels and self.email_smtp_server:
            results.append(await self._send_email(alert))
        
        return all(results) if results else True

    async def _send_telegram(self, alert: Alert) -> bool:
        """Send alert via Telegram"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return False
        
        try:
            emoji = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.ERROR: "❌",
                AlertLevel.CRITICAL: "🚨"
            }.get(alert.level, "📢")
            
            text = f"""
{emoji} *{alert.title}*

{alert.message}

_Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}_
_Category: {alert.category}_
_Level: {alert.level}_
"""
            
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(url, json=data, timeout=10)
            )
            
            if response.status_code == 200:
                logger.debug(f"Telegram alert sent: {alert.title}")
                return True
            else:
                logger.error(f"Telegram API error: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False

    async def _send_email(self, alert: Alert) -> bool:
        """Send alert via Email"""
        if not self.email_recipients:
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_username
            msg['To'] = ', '.join(self.email_recipients)
            msg['Subject'] = f"[{alert.level.upper()}] {alert.title}"
            
            # Email body
            body = f"""
AI Trading System Alert

{alert.title}

{alert.message}

---
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Category: {alert.category}
Level: {alert.level}
"""
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.email_smtp_server, self.email_smtp_port)
            server.starttls()
            server.login(self.email_username, self.email_password)
            server.send_message(msg)
            server.quit()
            
            logger.debug(f"Email alert sent: {alert.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

    def _log_alert(self, alert: Alert) -> None:
        """Log alert to file"""
        log_file = self.log_dir / f"alerts_{datetime.now().strftime('%Y%m%d')}.log"
        
        with open(log_file, 'a') as f:
            f.write(f"{alert.timestamp.isoformat()} | {alert.level} | {alert.category} | {alert.title} | {alert.message}\n")

    def get_alert_history(self, limit: int = 50) -> List[Alert]:
        """Get recent alert history"""
        return self.alert_history[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get alert manager status"""
        return {
            'channels': {
                'telegram': bool(self.telegram_bot_token and self.telegram_chat_id),
                'email': bool(self.email_smtp_server and self.email_recipients)
            },
            'alerts_sent': len(self.alert_history),
            'last_alert': self.alert_history[-1].timestamp.isoformat() if self.alert_history else None
        }


# Pre-built alert templates
class TradingAlerts:
    """Pre-built trading alert templates"""
    
    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
    
    async def trade_executed(self, action: str, pair: str, amount: float, price: float):
        """Alert when trade is executed"""
        await self.alert_manager.send_alert(
            title=f"Trade Executed: {action} {pair}",
            message=f"Executed {action} order for {amount} {pair} at ${price:,.2f}",
            level=AlertLevel.INFO,
            category="trade"
        )
    
    async def profit_target_hit(self, pair: str, pnl: float, pnl_percent: float):
        """Alert when profit target is hit"""
        await self.alert_manager.send_alert(
            title=f"🎯 Profit Target Hit: {pair}",
            message=f"Position closed with profit: ${pnl:,.2f} ({pnl_percent:+.2f}%)",
            level=AlertLevel.WARNING,
            category="profit"
        )
    
    async def stop_loss_hit(self, pair: str, pnl: float, pnl_percent: float):
        """Alert when stop loss is hit"""
        await self.alert_manager.send_alert(
            title=f"🛑 Stop Loss Hit: {pair}",
            message=f"Position closed with loss: ${pnl:,.2f} ({pnl_percent:+.2f}%)",
            level=AlertLevel.ERROR,
            category="loss"
        )
    
    async def daily_loss_limit(self, loss_percent: float):
        """Alert when daily loss limit is reached"""
        await self.alert_manager.send_alert(
            title="🚨 Daily Loss Limit Reached",
            message=f"Trading halted. Daily loss: {loss_percent:.2f}%",
            level=AlertLevel.CRITICAL,
            category="risk"
        )
    
    async def emergency_stop(self, reason: str):
        """Alert when emergency stop is activated"""
        await self.alert_manager.send_alert(
            title="🚨 EMERGENCY STOP ACTIVATED",
            message=f"All trading halted. Reason: {reason}",
            level=AlertLevel.CRITICAL,
            category="emergency"
        )
    
    async def withdrawal_completed(self, amount: float, currency: str, tx_id: str):
        """Alert when withdrawal is completed"""
        await self.alert_manager.send_alert(
            title=f"💸 Withdrawal Completed",
            message=f"Withdrew {amount} {currency}. TX: {tx_id}",
            level=AlertLevel.INFO,
            category="withdrawal"
        )
    
    async def system_error(self, error: str, component: str):
        """Alert on system error"""
        await self.alert_manager.send_alert(
            title=f"❌ System Error: {component}",
            message=f"Error: {error}",
            level=AlertLevel.ERROR,
            category="system"
        )


# Factory function
def create_alert_manager() -> AlertManager:
    """Create alert manager from config"""
    return AlertManager(
        telegram_bot_token=config.alerting.telegram_bot_token,
        telegram_chat_id=config.alerting.telegram_chat_id,
        email_smtp_server=config.alerting.email_smtp_server,
        email_smtp_port=config.alerting.email_smtp_port,
        email_username=config.alerting.email_username,
        email_password=config.alerting.email_password
    )
