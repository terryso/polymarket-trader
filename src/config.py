"""Configuration management for the Polymarket Trader application.

This module handles loading and validating configuration from environment
variables using Pydantic BaseSettings for type safety.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM API configuration settings."""

    model_config = SettingsConfigDict(env_prefix="LLM_")

    api_base: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4",
        description="LLM API base URL"
    )
    api_key: str = Field(
        default="",
        description="LLM API key"
    )
    model: str = Field(
        default="glm-4",
        description="LLM model name"
    )
    timeout: int = Field(
        default=30,
        description="API timeout in seconds"
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key is not empty in production."""
        # Allow empty for development/testing
        return v


class PolymarketSettings(BaseSettings):
    """Polymarket configuration settings."""

    model_config = SettingsConfigDict(env_prefix="")

    pk: str = Field(
        default="",
        description="Polymarket private key"
    )
    proxy_wallet: str = Field(
        default="",
        alias="YOUR_PROXY_WALLET",
        description="Proxy wallet address"
    )
    trader_address: str = Field(
        default="",
        alias="BOT_TRADER_ADDRESS",
        description="Bot trader address"
    )

    @field_validator("pk")
    @classmethod
    def mask_private_key(cls, v: str) -> str:
        """Private key should not be logged."""
        return v


class TradingSettings(BaseSettings):
    """Trading parameters configuration."""

    model_config = SettingsConfigDict(env_prefix="")

    trade_unit: float = Field(
        default=10.0,
        alias="TRADE_UNIT",
        description="Base trade unit in USD"
    )
    slippage_tolerance: float = Field(
        default=0.02,
        alias="SLIPPAGE_TOLERANCE",
        description="Slippage tolerance (0-1)"
    )
    pct_profit: float = Field(
        default=0.03,
        alias="PCT_PROFIT",
        description="Profit taking threshold (0-1)"
    )
    pct_loss: float = Field(
        default=-0.025,
        alias="PCT_LOSS",
        description="Stop loss threshold (negative value)"
    )
    initial_capital: float = Field(
        default=200.0,
        alias="INITIAL_CAPITAL",
        description="Initial capital in USD"
    )


class RiskControlSettings(BaseSettings):
    """Risk control parameters configuration."""

    model_config = SettingsConfigDict(env_prefix="")

    max_single_ratio: float = Field(
        default=0.20,
        alias="MAX_SINGLE_RATIO",
        description="Maximum single trade ratio of capital (0-1)"
    )
    min_confidence: float = Field(
        default=0.75,
        alias="MIN_CONFIDENCE",
        description="Minimum LLM confidence to trade (0-1)"
    )
    min_edge: float = Field(
        default=0.10,
        alias="MIN_EDGE",
        description="Minimum edge (price gap) to trade (0-1)"
    )
    max_concurrent_trades: int = Field(
        default=3,
        alias="MAX_CONCURRENT_TRADES",
        description="Maximum number of concurrent positions"
    )
    daily_loss_limit: float = Field(
        default=0.30,
        alias="DAILY_LOSS_LIMIT",
        description="Daily loss limit to stop trading (0-1)"
    )
    consecutive_losses_limit: int = Field(
        default=3,
        description="Consecutive losses before reducing position"
    )
    capital_threshold: float = Field(
        default=100.0,
        description="Capital threshold for reduced mode"
    )


class MarketFilterSettings(BaseSettings):
    """Market filter parameters configuration."""

    model_config = SettingsConfigDict(env_prefix="")

    min_liquidity: float = Field(
        default=10000.0,
        alias="MIN_LIQUIDITY",
        description="Minimum market liquidity in USD"
    )
    min_deadline_days: int = Field(
        default=7,
        alias="MIN_DEADLINE_DAYS",
        description="Minimum days until market deadline"
    )


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application settings
    trading_mode: Literal["paper", "live"] = Field(
        default="paper",
        description="Trading mode: paper or live"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )

    # Nested settings
    llm: LLMSettings = Field(default_factory=LLMSettings)
    polymarket: PolymarketSettings = Field(default_factory=PolymarketSettings)
    trading: TradingSettings = Field(default_factory=TradingSettings)
    risk: RiskControlSettings = Field(default_factory=RiskControlSettings)
    market_filter: MarketFilterSettings = Field(default_factory=MarketFilterSettings)

    # Convenience properties for common settings
    @property
    def initial_capital(self) -> float:
        """Get initial capital from trading settings."""
        return self.trading.initial_capital

    @property
    def min_confidence(self) -> float:
        """Get minimum confidence from risk settings."""
        return self.risk.min_confidence


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance for convenience
settings = get_settings()
