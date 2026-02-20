"""
Configuration Management for Arbi-Bot
Uses Pydantic for validation and environment variable loading
"""

import os
from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load .env file
load_dotenv()


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

    # Trading pairs
    trading_pairs: str = Field(default="BTC/USDT,ETH/USDT,SOL/USDT,RNDR/USDT,FET/USDT,ONDO/USDT,ARB/USDT,OP/USDT", alias="TRADING_PAIRS")
    primary_trading_pair: str = Field(default="ETH/USDT", alias="PRIMARY_TRADING_PAIR")

    # Multi-exchange settings
    multi_exchange_trading: bool = Field(default=False, alias="MULTI_EXCHANGE_TRADING")
    monitor_exchanges: str = Field(default="binance,coinbase,kraken,okx,bybit", alias="MONITOR_EXCHANGES")

    @property
    def primary_api_key_plain(self) -> str:
        return self.primary_api_key.get_secret_value() if self.primary_api_key else ""

    @property
    def primary_api_secret_plain(self) -> str:
        return self.primary_api_secret.get_secret_value() if self.primary_api_secret else ""

    @property
    def secondary_api_key_plain(self) -> Optional[str]:
        return self.secondary_api_key.get_secret_value() if self.secondary_api_key else None

    @property
    def secondary_api_secret_plain(self) -> Optional[str]:
        return self.secondary_api_secret.get_secret_value() if self.secondary_api_secret else None

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


class TradingConfig(BaseSettings):
    """Trading parameters and risk limits"""
    model_config = SettingsConfigDict(env_prefix='')

    # Position limits
    max_position_size: float = Field(default=0.15, alias="MAX_POSITION_SIZE")
    max_daily_trades: int = Field(default=50, alias="MAX_DAILY_TRADES")

    # Stop loss / take profit
    stop_loss_percent: float = Field(default=0.05, alias="STOP_LOSS_PERCENT")
    take_profit_percent: float = Field(default=0.10, alias="TAKE_PROFIT_PERCENT")

    # Confidence thresholds
    min_confidence: float = Field(default=0.65, alias="MIN_CONFIDENCE")

    # Daily limits
    daily_loss_limit: float = Field(default=0.08, alias="DAILY_LOSS_LIMIT")

    # Arbitrage settings
    shadow_arbitrage_enabled: bool = Field(default=True, alias="SHADOW_ARBITRAGE_ENABLED")
    arbitrage_min_confidence: float = Field(default=0.75, alias="ARBITRAGE_MIN_CONFIDENCE")
    min_arb_profit_percent: float = Field(default=0.03, alias="MIN_ARB_PROFIT_PERCENT")
    multi_exchange_trading: bool = Field(default=False, alias="MULTI_EXCHANGE_TRADING")

    # Profit management (profits stay on Binance for now)
    min_withdraw_threshold: float = Field(default=100.0)  # Log-only threshold


class DatabaseConfig(BaseSettings):
    """Database configuration"""
    model_config = SettingsConfigDict(env_prefix='')

    database_url: str = Field(default="sqlite:///./data/trading.db", alias="DATABASE_URL")


class SystemConfig(BaseSettings):
    """Overall system configuration"""
    model_config = SettingsConfigDict(env_prefix='')

    log_level: str = "INFO"
    data_dir: str = "./data"
    log_dir: str = "./logs"

    # Nested configurations
    exchange: ExchangeConfig = Field(default_factory=ExchangeConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)


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
    ]

    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
