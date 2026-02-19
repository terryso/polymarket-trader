"""Configuration management for the Polymarket Trader application.

This module handles loading and validating configuration from environment
variables using Pydantic BaseSettings for type safety.
"""

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_env_file() -> str | None:
    """Get .env file path, or None if running tests.

    Returns None during pytest to ensure unit tests use default values
    instead of reading from .env file.
    """
    # Check if running under pytest
    if "PYTEST_CURRENT_TEST" in os.environ or "PYTEST_VERSION" in os.environ:
        return None
    return ".env"


class LLMSettings(BaseSettings):
    """LLM API configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_base: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4", description="LLM API base URL"
    )
    api_key: str = Field(default="", description="LLM API key")
    model: str = Field(default="glm-4", description="LLM model name")
    timeout: int = Field(
        default=600, gt=0, description="API timeout in seconds (default 10 min)"
    )
    thinking_enabled: bool = Field(
        default=True,
        alias="THINKING_ENABLED",
        description="Enable GLM thinking mode for better reasoning (default: True for GLM-5)",
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

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    pk: str = Field(default="", description="Polymarket private key")
    proxy_wallet: str = Field(
        default="", alias="YOUR_PROXY_WALLET", description="Proxy wallet address"
    )
    trader_address: str = Field(
        default="", alias="BOT_TRADER_ADDRESS", description="Bot trader address"
    )

    # API Credentials for Level 2 authentication (required for order history sync)
    api_key: str = Field(
        default="", alias="POLYMARKET_API_KEY", description="Polymarket API key"
    )
    api_secret: str = Field(
        default="", alias="POLYMARKET_API_SECRET", description="Polymarket API secret"
    )
    api_passphrase: str = Field(
        default="",
        alias="POLYMARKET_API_PASSPHRASE",
        description="Polymarket API passphrase",
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

    @property
    def has_api_credentials(self) -> bool:
        """Check if all API credentials are configured."""
        return bool(self.api_key and self.api_secret and self.api_passphrase)


class TradingSettings(BaseSettings):
    """Trading parameters configuration."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    trade_unit: float = Field(
        default=10.0, alias="TRADE_UNIT", gt=0, description="Base trade unit in USD"
    )
    slippage_tolerance: float = Field(
        default=0.02,
        alias="SLIPPAGE_TOLERANCE",
        ge=0,
        le=1,
        description="Slippage tolerance (0-1)",
    )
    pct_profit: float = Field(
        default=0.03,
        alias="PCT_PROFIT",
        ge=0,
        le=1,
        description="Profit taking threshold (0-1)",
    )
    pct_loss: float = Field(
        default=-0.025,
        alias="PCT_LOSS",
        ge=-1,
        le=0,
        description="Stop loss threshold (negative value, -1 to 0)",
    )
    initial_capital: float = Field(
        default=200.0,
        alias="INITIAL_CAPITAL",
        gt=0,
        description="Initial capital in USD",
    )


class RiskControlSettings(BaseSettings):
    """Risk control parameters configuration.

    风险控制参数配置，包括资金管理、熔断机制、置信度门槛和持仓限制。

    Attributes:
        max_single_ratio: 单笔交易最大资金比例 (0-1)
        min_bet: 最小交易金额 (USD)
        consecutive_losses_limit: 连续亏损次数触发熔断
        reduce_ratio_after_losses: 连续亏损后降级比例 (0-1)
        daily_loss_limit: 日亏损停止门槛 (0-1)
        capital_threshold: 低资金门槛 (USD)
        reduce_ratio_low_capital: 低资金时降级比例 (0-1)
        min_confidence: 最小 LLM 置信度门槛 (0-1)
        min_edge: 最小 Edge 门槛 (0-1)
        max_position_per_market: 单市场最大持仓比例 (0-1)
        max_open_markets: 最大同时持仓数量

    Example:
        >>> from src.config import settings
        >>> settings.risk.min_confidence
        0.75
        >>> settings.risk.max_position_per_market
        0.40
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 资金管理
    max_single_ratio: float = Field(
        default=0.20,
        alias="MAX_SINGLE_RATIO",
        ge=0,
        le=1,
        description="Maximum single trade ratio of capital (0-1)",
    )
    min_bet: float = Field(
        default=1.0,
        alias="MIN_BET",
        gt=0,
        description="Minimum bet amount in USD",
    )

    # 熔断机制
    consecutive_losses_limit: int = Field(
        default=3,
        alias="CONSECUTIVE_LOSSES_LIMIT",
        gt=0,
        description="Consecutive losses before reducing position",
    )
    reduce_ratio_after_losses: float = Field(
        default=0.10,
        alias="REDUCE_RATIO_AFTER_LOSSES",
        ge=0,
        le=1,
        description="Position ratio after consecutive losses (0-1)",
    )
    daily_loss_limit: float = Field(
        default=0.30,
        alias="DAILY_LOSS_LIMIT",
        ge=0,
        le=1,
        description="Daily loss limit to stop trading (0-1)",
    )
    capital_threshold: float = Field(
        default=100.0,
        alias="CAPITAL_THRESHOLD",
        gt=0,
        description="Capital threshold for reduced mode",
    )
    reduce_ratio_low_capital: float = Field(
        default=0.10,
        alias="REDUCE_RATIO_LOW_CAPITAL",
        ge=0,
        le=1,
        description="Position ratio when capital below threshold (0-1)",
    )

    # 置信度门槛
    min_confidence: float = Field(
        default=0.75,
        alias="MIN_CONFIDENCE",
        ge=0,
        le=1,
        description="Minimum LLM confidence to trade (0-1)",
    )
    min_edge: float = Field(
        default=0.10,
        alias="MIN_EDGE",
        ge=0,
        le=1,
        description="Minimum edge (price gap) to trade (0-1)",
    )

    # 持仓限制
    max_position_per_market: float = Field(
        default=0.40,
        alias="MAX_POSITION_PER_MARKET",
        ge=0,
        le=1,
        description="Maximum position ratio per market (0-1)",
    )
    max_open_markets: int = Field(
        default=3,
        alias="MAX_OPEN_MARKETS",
        gt=0,
        description="Maximum number of open positions",
    )
    # Backward compatibility alias
    max_concurrent_trades: int = Field(
        default=3,
        alias="MAX_CONCURRENT_TRADES",
        gt=0,
        description="Maximum number of concurrent positions (deprecated: use max_open_markets)",
    )

    @field_validator("max_open_markets")
    @classmethod
    def validate_max_open_markets(cls, v: int) -> int:
        """Validate max_open_markets is reasonable."""
        if v > 20:
            raise ValueError(
                "MAX_OPEN_MARKETS should not exceed 20 for risk management"
            )
        return v


class TelegramSettings(BaseSettings):
    """Telegram Bot configuration settings.

    Story 9.1: Telegram Bot 配置与初始化
    Story 9.4: LLM 分析结果通知 - 添加 notify_all_analyses 配置

    Attributes:
        bot_token: Telegram Bot Token (from @BotFather)
        chat_id: Authorized user Chat ID for commands
        enabled: Enable Telegram notifications and commands
        notify_all_analyses: Notify all analyses (not just tradeable signals)

    Example:
        >>> from src.config import settings
        >>> settings.telegram.enabled
        False
        >>> settings.telegram.bot_token
        None
    """

    model_config = SettingsConfigDict(
        env_prefix="TELEGRAM_",
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str | None = Field(
        default=None,
        description="Telegram Bot Token (from @BotFather)",
    )
    chat_id: str | None = Field(
        default=None,
        description="Authorized user Chat ID for commands",
    )
    enabled: bool = Field(
        default=False,
        description="Enable Telegram notifications and commands",
    )
    notify_all_analyses: bool = Field(
        default=False,
        description="Notify all analyses (not just tradeable signals)",
    )

    @field_validator("enabled")
    @classmethod
    def validate_enabled(cls, v: bool) -> bool:
        """If enabled, bot_token must be set.

        Logs a warning and returns False if enabled but token is not set.
        """
        if v:
            import warnings

            warnings.warn(
                "Telegram is enabled but TELEGRAM_BOT_TOKEN is not set. "
                "Telegram features will be disabled.",
                UserWarning,
                stacklevel=2,
            )
        return v


class MarketFilterSettings(BaseSettings):
    """Market filter parameters configuration."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    min_liquidity: float = Field(
        default=10000.0,
        alias="MIN_LIQUIDITY",
        gt=0,
        description="Minimum market liquidity in USD",
    )
    min_deadline_hours: int = Field(
        default=1,
        alias="MIN_DEADLINE_HOURS",
        gt=0,
        description="Minimum hours until market deadline",
    )
    excluded_keywords: list[str] = Field(
        default=["price", "USD", "tomorrow"],
        alias="EXCLUDED_KEYWORDS",
        description="Keywords to exclude from market titles (word boundary match)",
    )
    controversial_keywords: list[str] = Field(
        default=[],
        alias="CONTROVERSIAL_KEYWORDS",
        description="Controversial keywords to exclude from market descriptions",
    )


class SchedulerSettings(BaseSettings):
    """Scheduler configuration settings.

    调度器配置，包括时区、任务存储和执行器设置。

    Attributes:
        timezone: 调度器时区 (默认 UTC)
        jobstores_db: (保留供未来使用) SQLite 任务存储数据库路径
            - 当前使用 MemoryJobStore，此配置暂未生效
            - 未来如需持久化任务，可用于 SQLite 或 SQLAlchemy jobstore
        executors_pool_size: 线程池执行器大小
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    timezone: str = Field(
        default="UTC",
        alias="SCHEDULER_TIMEZONE",
        description="Scheduler timezone",
    )
    jobstores_db: str = Field(
        default="data/scheduler.db",
        alias="SCHEDULER_JOBSTORES_DB",
        description="SQLite jobstore database path (reserved for future use)",
    )
    executors_pool_size: int = Field(
        default=10,
        alias="SCHEDULER_EXECUTORS_DEFAULT_POOL_SIZE",
        gt=0,
        description="Thread pool executor size",
    )


class TaskScheduleSettings(BaseSettings):
    """Task schedule configuration settings.

    定时任务频率配置，定义各个定时任务的执行间隔。

    Story 8.2: 定时任务配置

    Attributes:
        fetch_markets_interval_hours: 市场获取间隔 (小时)
        check_positions_interval_seconds: 持仓检查间隔 (秒)
        daily_statistics_hour: 每日统计执行时间 (小时, 0-23)
        validate_predictions_hour: 预测验证执行时间 (小时, 0-23)
        reset_daily_state_hour: 每日状态重置时间 (小时, 0-23)
        state_persist_interval_minutes: 状态持久化间隔 (分钟)
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    fetch_markets_interval_hours: int = Field(
        default=2,
        alias="SCHEDULE_FETCH_MARKETS_INTERVAL_HOURS",
        gt=0,
        description="Interval in hours for fetching markets from Polymarket",
    )
    check_positions_interval_seconds: int = Field(
        default=60,
        alias="SCHEDULE_CHECK_POSITIONS_INTERVAL_SECONDS",
        gt=0,
        description="Interval in seconds for checking open positions",
    )
    daily_statistics_hour: int = Field(
        default=0,
        alias="SCHEDULE_DAILY_STATISTICS_HOUR",
        ge=0,
        le=23,
        description="Hour of day (0-23) to run daily statistics",
    )
    validate_predictions_hour: int = Field(
        default=6,
        alias="SCHEDULE_VALIDATE_PREDICTIONS_HOUR",
        ge=0,
        le=23,
        description="Hour of day (0-23) to validate predictions",
    )
    reset_daily_state_hour: int = Field(
        default=0,
        alias="SCHEDULE_RESET_DAILY_STATE_HOUR",
        ge=0,
        le=23,
        description="Hour of day (0-23) to reset daily state",
    )
    state_persist_interval_minutes: int = Field(
        default=5,
        alias="SCHEDULE_STATE_PERSIST_INTERVAL_MINUTES",
        gt=0,
        description="Interval in minutes for persisting state to database",
    )


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application settings
    trading_mode: Literal["paper", "live"] = Field(
        default="paper", description="Trading mode: paper or live"
    )
    log_level: str = Field(default="INFO", description="Logging level")
    data_dir: str = Field(
        default="data", description="Directory for data storage (database, etc.)"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid Python logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}, got '{v}'")
        return v_upper

    # Nested settings
    llm: LLMSettings = Field(default_factory=LLMSettings)
    polymarket: PolymarketSettings = Field(default_factory=PolymarketSettings)
    trading: TradingSettings = Field(default_factory=TradingSettings)
    risk: RiskControlSettings = Field(default_factory=RiskControlSettings)
    market_filter: MarketFilterSettings = Field(default_factory=MarketFilterSettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    task_schedule: TaskScheduleSettings = Field(default_factory=TaskScheduleSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)

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
