"""System status API response models.

This module defines Pydantic models for system status API responses.

Story 7.5: 系统状态 API
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer


class SystemStatus(BaseModel):
    """System running status for monitoring.

    Contains real-time system status for dashboard monitoring.

    Attributes:
        trading_enabled: Whether trading is currently enabled
        mode: Current trading mode (PAPER/LIVE)
        current_capital: Current capital in USD
        daily_pnl: Daily profit/loss
        open_positions: Number of open positions
        consecutive_losses: Consecutive losing trades count
        reduced_mode: Whether system is in reduced position mode
        last_market_fetch: Timestamp of last market data fetch
        uptime_hours: System uptime in hours
    """

    trading_enabled: bool = Field(..., description="Trading enabled status")
    mode: str = Field(..., description="Trading mode (PAPER/LIVE)")
    current_capital: float = Field(..., description="Current capital (USD)")
    daily_pnl: float = Field(..., description="Daily P&L (USD)")
    open_positions: int = Field(..., description="Open positions count")
    consecutive_losses: int = Field(..., description="Consecutive losses")
    reduced_mode: bool = Field(..., description="Reduced mode active")
    last_market_fetch: datetime | None = Field(
        None, description="Last market fetch timestamp"
    )
    uptime_hours: float | None = Field(None, description="System uptime (hours)")

    @field_serializer("last_market_fetch")
    def serialize_datetime(self, dt: datetime | None, _info: Any) -> str | None:
        """Serialize datetime to ISO 8601 format."""
        if dt is None:
            return None
        return dt.isoformat()


class SanitizedSettings(BaseModel):
    """Sanitized settings for API response.

    Contains configuration values with sensitive data masked.

    Attributes:
        trading_mode: Current trading mode
        initial_capital: Initial capital amount
        trade_unit: Base trade unit amount
        max_single_ratio: Maximum single position ratio
        min_confidence: Minimum LLM confidence threshold
        min_edge: Minimum edge requirement
        daily_loss_limit: Daily loss limit percentage
        max_open_markets: Maximum concurrent markets
        llm_model: LLM model name
        llm_api_base: LLM API base URL
        llm_api_key: Masked API key (first 4 chars only)
        polymarket_pk: Masked private key (fully hidden)
        proxy_wallet: Masked wallet address (first 6 + last 4)
    """

    trading_mode: str = Field(..., description="Trading mode (PAPER/LIVE)")
    initial_capital: float = Field(..., description="Initial capital (USD)")
    trade_unit: float = Field(..., description="Trade unit amount")
    max_single_ratio: float = Field(..., description="Max single position ratio")
    min_confidence: float = Field(..., description="Min confidence threshold")
    min_edge: float = Field(..., description="Min edge requirement")
    daily_loss_limit: float = Field(..., description="Daily loss limit")
    max_open_markets: int = Field(..., description="Max open markets")
    llm_model: str = Field(..., description="LLM model name")
    llm_api_base: str = Field(..., description="LLM API base URL")
    llm_api_key: str = Field(..., description="Masked LLM API key")
    polymarket_pk: str = Field(..., description="Masked private key")
    proxy_wallet: str = Field(..., description="Masked wallet address")


__all__ = ["SystemStatus", "SanitizedSettings"]
