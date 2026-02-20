"""
Configuration Management for AI Trading System
Uses Pydantic for validation and environment variable loading
"""

import os
from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class APIConfig(BaseSettings):
    """AI API credentials"""
    model_config = SettingsConfigDict(env_prefix='ANTHROPIC_')
    
    anthropic_key: SecretStr = Field(default="", alias="ANTHROPIC_API_KEY")
    openai_key: Optional[SecretStr] = Field(default=None, alias="OPENAI_API_KEY")
    
    @property
    def anthropic_key_plain(self) -> str:
        return self.anthropic_key.get_secret_value() if self.anthropic_key else ""
    
    @property
    def openai_key_plain(self) -> Optional[str]:
        return self.openai_key.get_secret_value() if self.openai_key else None


class ExchangeConfig(BaseSettings):
    """
    Multi-exchange configuration
    
    Supports:
    - Primary exchange (required)
    - Secondary exchange (optional)
    - Tertiary exchange (optional)
    """
    model_config = SettingsConfigDict(env_prefix='')
    
    # Primary Exchange (Required)
    primary_exchange: str = Field(default="binance", alias="PRIMARY_EXCHANGE")
    primary_api_key: SecretStr = Field(default="", alias="PRIMARY_API_KEY")
    primary_api_secret: SecretStr = Field(default="", alias="PRIMARY_API_SECRET")
    primary_testnet: bool = Field(default=True, alias="PRIMARY_TESTNET")
    
    # Secondary Exchange (Optional)
    secondary_exchange: str = Field(default="coinbase", alias="SECONDARY_EXCHANGE")
    secondary_api_key: Optional[SecretStr] = Field(default=None, alias="SECONDARY_API_KEY")
    secondary_api_secret: Optional[SecretStr] = Field(default=None, alias="SECONDARY_API_SECRET")
    secondary_testnet: bool = Field(default=True, alias="SECONDARY_TESTNET")
    
    # Tertiary Exchange (Optional)
    tertiary_exchange: str = Field(default="kraken", alias="TERTIARY_EXCHANGE")
    tertiary_api_key: Optional[SecretStr] = Field(default=None, alias="TERTIARY_API_KEY")
    tertiary_api_secret: Optional[SecretStr] = Field(default=None, alias="TERTIARY_API_SECRET")
    tertiary_testnet: bool = Field(default=True, alias="TERTIARY_TESTNET")
    
    # Trading pairs (researched for 2026 maximum potential)
    # Tier 1: BTC, ETH (blue-chip)
    # Tier 2: SOL, RNDR, FET, ONDO (AI + RWA narrative - highest growth)
    # Tier 3: ARB, OP (Layer 2 growth)
    trading_pairs: str = Field(default="BTC/USDT,ETH/USDT,SOL/USDT,RNDR/USDT,FET/USDT,ONDO/USDT,ARB/USDT,OP/USDT", alias="TRADING_PAIRS")
    primary_trading_pair: str = Field(default="ETH/USDT", alias="PRIMARY_TRADING_PAIR")
    
    # Multi-exchange settings
    multi_exchange_trading: bool = Field(default=False, alias="MULTI_EXCHANGE_TRADING")
    monitor_exchanges: str = Field(default="binance,coinbase,kraken,okx,bybit", alias="MONITOR_EXCHANGES")
    
    # Properties for primary exchange
    @property
    def primary_api_key_plain(self) -> str:
        return self.primary_api_key.get_secret_value() if self.primary_api_key else ""
    
    @property
    def primary_api_secret_plain(self) -> str:
        return self.primary_api_secret.get_secret_value() if self.primary_api_secret else ""
    
    # Properties for secondary exchange
    @property
    def secondary_api_key_plain(self) -> Optional[str]:
        return self.secondary_api_key.get_secret_value() if self.secondary_api_key else None
    
    @property
    def secondary_api_secret_plain(self) -> Optional[str]:
        return self.secondary_api_secret.get_secret_value() if self.secondary_api_secret else None
    
    # Properties for tertiary exchange
    @property
    def tertiary_api_key_plain(self) -> Optional[str]:
        return self.tertiary_api_key.get_secret_value() if self.tertiary_api_key else None
    
    @property
    def tertiary_api_secret_plain(self) -> Optional[str]:
        return self.tertiary_api_secret.get_secret_value() if self.tertiary_api_secret else None
    
    def get_trading_pairs_list(self) -> list:
        """Get trading pairs as a list"""
        return [p.strip() for p in self.trading_pairs.split(',')]
    
    def get_monitor_exchanges_list(self) -> list:
        """Get monitored exchanges as a list"""
        return [e.strip() for e in self.monitor_exchanges.split(',')]


class BlockchainConfig(BaseSettings):
    """Local blockchain settings"""
    model_config = SettingsConfigDict(env_prefix='BLOCKCHAIN_')
    
    network_url: str = Field(default="http://localhost:8545", alias="BLOCKCHAIN_RPC_URL")
    chain_id: int = Field(default=1337, alias="BLOCKCHAIN_CHAIN_ID")
    gas_limit: int = 6721975
    gas_price: int = 20000000000  # 20 Gwei


class TradingConfig(BaseSettings):
    """Trading parameters and risk limits"""
    model_config = SettingsConfigDict(env_prefix='')
    
    # Position limits
    max_position_size: float = Field(default=0.15, alias="MAX_POSITION_SIZE")  # 15%
    max_daily_trades: int = Field(default=50, alias="MAX_DAILY_TRADES")
    
    # Stop loss / take profit
    stop_loss_percent: float = Field(default=0.05, alias="STOP_LOSS_PERCENT")  # 5%
    take_profit_percent: float = Field(default=0.10, alias="TAKE_PROFIT_PERCENT")  # 10%
    
    # Confidence thresholds
    min_confidence: float = Field(default=0.65, alias="MIN_CONFIDENCE")  # 65%
    
    # Daily limits
    daily_loss_limit: float = Field(default=0.08, alias="DAILY_LOSS_LIMIT")  # 8%
    
    # Profit withdrawal
    auto_withdraw_enabled: bool = Field(default=True, alias="AUTO_WITHDRAW_ENABLED")
    withdraw_percentage: float = Field(default=0.5, alias="WITHDRAW_PERCENTAGE")  # 50%
    withdraw_wallet_address: str = Field(default="", alias="WITHDRAW_WALLET_ADDRESS")
    min_withdraw_threshold: float = Field(default=100, alias="MIN_WITHDRAW_THRESHOLD")
    
    # Arbitrage settings
    shadow_arbitrage_enabled: bool = Field(default=True, alias="SHADOW_ARBITRAGE_ENABLED")
    arbitrage_min_confidence: float = Field(default=0.75, alias="ARBITRAGE_MIN_CONFIDENCE")


class DatabaseConfig(BaseSettings):
    """Database configuration"""
    model_config = SettingsConfigDict(env_prefix='')
    
    database_url: str = Field(default="sqlite:///./data/trading.db", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")


class SecurityConfig(BaseSettings):
    """Security configuration"""
    model_config = SettingsConfigDict(env_prefix='')
    
    encryption_key: Optional[SecretStr] = Field(default=None, alias="ENCRYPTION_KEY")
    jwt_secret: SecretStr = Field(default="change-me-in-production", alias="JWT_SECRET")
    
    @property
    def encryption_key_plain(self) -> Optional[str]:
        return self.encryption_key.get_secret_value() if self.encryption_key else None
    
    @property
    def jwt_secret_plain(self) -> str:
        return self.jwt_secret.get_secret_value()


class AlertingConfig(BaseSettings):
    """Alerting configuration"""
    model_config = SettingsConfigDict(env_prefix='')
    
    telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(default=None, alias="TELEGRAM_CHAT_ID")
    email_smtp_server: Optional[str] = Field(default=None, alias="EMAIL_SMTP_SERVER")
    email_smtp_port: Optional[int] = Field(default=None, alias="EMAIL_SMTP_PORT")
    email_username: Optional[str] = Field(default=None, alias="EMAIL_USERNAME")
    email_password: Optional[str] = Field(default=None, alias="EMAIL_PASSWORD")


class SystemConfig(BaseSettings):
    """Overall system configuration"""
    model_config = SettingsConfigDict(env_prefix='')
    
    log_level: str = "INFO"
    data_dir: str = "./data"
    log_dir: str = "./logs"
    
    # Nested configurations
    api: APIConfig = Field(default_factory=APIConfig)
    exchange: ExchangeConfig = Field(default_factory=ExchangeConfig)
    blockchain: BlockchainConfig = Field(default_factory=BlockchainConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    alerting: AlertingConfig = Field(default_factory=AlertingConfig)


# Global config instance
config = SystemConfig()


def get_config() -> SystemConfig:
    """Get the global configuration instance"""
    return config


def ensure_directories():
    """Ensure all required directories exist"""
    import os
    
    dirs = [
        config.data_dir,
        config.log_dir,
        "./config",
        "./logs/executions",
        "./logs/alerts",
    ]
    
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
