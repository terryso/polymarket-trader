"""Statistics API response models.

This module defines Pydantic models for statistics API responses.

Story 7.4: 预测与统计 API
"""

from __future__ import annotations

from datetime import date as DateType
from typing import Any

from pydantic import BaseModel, Field, field_serializer


class OverviewStats(BaseModel):
    """System overview statistics.

    Aggregated view of trading system status and performance.

    Attributes:
        initial_capital: Starting capital in USD (from .env)
        wallet_balance: Real USDC balance from wallet (None if fetch failed)
        position_value: Total current value of open positions
        position_pnl: Unrealized PnL from open positions
        current_capital: Current capital = wallet_balance + position_value
        total_pnl: Total profit/loss = current_capital - initial_capital
        total_pnl_pct: Total profit/loss as percentage
        win_rate: Overall win rate (0-1)
        total_trades: Total number of trades
        winning_trades: Number of winning trades
        losing_trades: Number of losing trades
        open_positions: Number of open positions
        trading_enabled: Whether trading is enabled
        mode: Current trading mode
        wallet_balance_error: Error message if wallet balance fetch failed
    """

    initial_capital: float = Field(..., description="Initial capital (USD)")
    wallet_balance: float | None = Field(
        None, description="Real USDC balance from wallet"
    )
    position_value: float = Field(0.0, description="Total position value (USD)")
    position_pnl: float = Field(0.0, description="Unrealized PnL from positions")
    current_capital: float = Field(..., description="Current capital (USD)")
    total_pnl: float = Field(..., description="Total P&L (USD)")
    total_pnl_pct: float = Field(..., description="Total P&L percentage")
    win_rate: float = Field(..., description="Win rate (0-1)")
    total_trades: int = Field(..., description="Total trades")
    winning_trades: int = Field(..., description="Winning trades")
    losing_trades: int = Field(..., description="Losing trades")
    open_positions: int = Field(..., description="Open positions count")
    trading_enabled: bool = Field(..., description="Trading enabled")
    mode: str = Field(..., description="Trading mode (PAPER/LIVE)")
    wallet_balance_error: str | None = Field(
        None, description="Error message if wallet balance fetch failed"
    )


class DailyStatsItem(BaseModel):
    """Daily statistics item for API list responses.

    Contains statistics for a single trading day.

    Attributes:
        date: Trading date
        starting_capital: Capital at start of day
        ending_capital: Capital at end of day
        total_pnl: Daily profit/loss
        total_trades: Number of trades
        winning_trades: Number of winning trades
        losing_trades: Number of losing trades
        win_rate: Daily win rate (0-1)
    """

    date: DateType = Field(..., description="Trading date")
    starting_capital: float = Field(..., description="Starting capital (USD)")
    ending_capital: float | None = Field(None, description="Ending capital (USD)")
    total_pnl: float | None = Field(None, description="Daily P&L (USD)")
    total_trades: int = Field(..., description="Total trades")
    winning_trades: int = Field(..., description="Winning trades")
    losing_trades: int = Field(..., description="Losing trades")
    win_rate: float | None = Field(None, description="Win rate (0-1)")

    @field_serializer("date")
    def serialize_date(self, d: DateType, _info: Any) -> str:
        """Serialize date to ISO format.

        Args:
            d: The date value to serialize
            _info: Field serializer info (unused)

        Returns:
            ISO formatted date string (YYYY-MM-DD)
        """
        return d.isoformat()


class CapitalHistoryPoint(BaseModel):
    """Capital history data point.

    Attributes:
        date: Date of data point
        capital: Capital value
    """

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    capital: float = Field(..., description="Capital (USD)")


class WinRateHistoryPoint(BaseModel):
    """Win rate history data point.

    Attributes:
        date: Date of data point
        win_rate: Cumulative win rate
    """

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    win_rate: float = Field(..., description="Win rate (0-1)")


class TradesByDayPoint(BaseModel):
    """Trades by day data point.

    Attributes:
        date: Date of data point
        count: Number of trades
    """

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    count: int = Field(..., description="Trade count")


class PerformanceData(BaseModel):
    """Performance data for charts.

    Contains time series data for dashboard visualizations.

    Attributes:
        capital_history: Capital over time
        win_rate_history: Win rate over time
        trades_by_day: Trade count by day
    """

    capital_history: list[CapitalHistoryPoint] = Field(
        default_factory=list, description="Capital history"
    )
    win_rate_history: list[WinRateHistoryPoint] = Field(
        default_factory=list, description="Win rate history"
    )
    trades_by_day: list[TradesByDayPoint] = Field(
        default_factory=list, description="Trades by day"
    )


__all__ = [
    "OverviewStats",
    "DailyStatsItem",
    "CapitalHistoryPoint",
    "WinRateHistoryPoint",
    "TradesByDayPoint",
    "PerformanceData",
]
