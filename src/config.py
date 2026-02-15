"""Configuration management for the Polymarket Trader application.

This module handles loading and validating configuration from environment
variables using Pydantic BaseSettings for type safety.
"""

import os
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
        gt=0,
        description="API timeout in seconds"
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key format (non-empty in production)."""
        # In production (TRADING_MODE=live), API key should be set
        trading_mode = os.getenv("TRADING_MODE", "paper")
        if trading_mode == "live" and not v:
            raise ValueError("LLM_API_KEY is required when TRADING_MODE=live")
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
    def validate_pk(cls, v: str) -> str:
        """Validate private key is provided in live mode."""
        trading_mode = os.getenv("TRADING_MODE", "paper")
        if trading_mode == "live" and not v:
            raise ValueError("PK (private key) is required when TRADING_MODE=live")
        return v

    @field_validator("proxy_wallet")
    @classmethod
    def validate_proxy_wallet(cls, v: str) -> str:
        """Validate proxy wallet is provided in live mode."""
        trading_mode = os.getenv("TRADING_MODE", "paper")
        if trading_mode == "live" and not v:
            raise ValueError("YOUR_PROXY_WALLET is required when TRADING_MODE=live")
        return v

    @field_validator("trader_address")
    @classmethod
    def validate_trader_address(cls, v: str) -> str:
        """Validate trader address is provided in live mode."""
        trading_mode = os.getenv("TRADING_MODE", "paper")
        if trading_mode == "live" and not v:
            raise ValueError("BOT_TRADER_ADDRESS is required when TRADING_MODE=live")
        return v


class TradingSettings(BaseSettings):
    """Trading parameters configuration."""

    model_config = SettingsConfigDict(env_prefix="")

    trade_unit: float = Field(
        default=10.0,
        alias="TRADE_UNIT",
        gt=0,
        description="Base trade unit in USD"
    )
    slippage_tolerance: float = Field(
        default=0.02,
        alias="SLIPPAGE_TOLERANCE",
        ge=0,
        le=1,
        description="Slippage tolerance (0-1)"
    )
    pct_profit: float = Field(
        default=0.03,
        alias="PCT_PROFIT",
        ge=0,
        le=1,
        description="Profit taking threshold (0-1)"
    )
    pct_loss: float = Field(
        default=-0.025,
        alias="PCT_LOSS",
        ge=-1,
        le=0,
        description="Stop loss threshold (negative value, -1 to 0)"
    )
    initial_capital: float = Field(
        default=200.0,
        alias="INITIAL_CAPITAL",
        gt=0,
        description="Initial capital in USD"
    )


class RiskControlSettings(BaseSettings):
    """Risk control parameters configuration."""

    model_config = SettingsConfigDict(env_prefix="")

    max_single_ratio: float = Field(
        default=0.20,
        alias="MAX_SINGLE_RATIO",
        ge=0,
        le=1,
        description="Maximum single trade ratio of capital (0-1)"
    )
    min_confidence: float = Field(
        default=0.75,
        alias="MIN_CONFIDENCE",
        ge=0,
        le=1,
        description="Minimum LLM confidence to trade (0-1)"
    )
    min_edge: float = Field(
        default=0.10,
        alias="MIN_EDGE",
        ge=0,
        le=1,
        description="Minimum edge (price gap) to trade (0-1)"
    )
    max_concurrent_trades: int = Field(
        default=3,
        alias="MAX_CONCURRENT_TRADES",
        gt=0,
        description="Maximum number of concurrent positions"
    )
    daily_loss_limit: float = Field(
        default=0.30,
        alias="DAILY_LOSS_LIMIT",
        ge=0,
        le=1,
        description="Daily loss limit to stop trading (0-1)"
    )
    consecutive_losses_limit: int = Field(
        default=3,
        alias="CONSECUTIVE_LOSSES_LIMIT",
        gt=0,
        description="Consecutive losses before reducing position"
    )
    capital_threshold: float = Field(
        default=100.0,
        alias="CAPITAL_THRESHOLD",
        gt=0,
        description="Capital threshold for reduced mode"
    )


class MarketFilterSettings(BaseSettings):
    """Market filter parameters configuration."""

    model_config = SettingsConfigDict(env_prefix="")

    min_liquidity: float = Field(
        default=10000.0,
        alias="MIN_LIQUIDITY",
        gt=0,
        description="Minimum market liquidity in USD"
    )
    min_deadline_days: int = Field(
        default=7,
        alias="MIN_DEADLINE_DAYS",
        gt=0,
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
    data_dir: str = Field(
        default="data",
        description="Directory for data storage (database, etc.)"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid Python logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(
                f"LOG_LEVEL must be one of {valid_levels}, got '{v}'"
            )
        return v_upper

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
