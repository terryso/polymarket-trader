"""Statistics data model.

This module defines the Statistics and DailyStats models for
representing trading performance statistics.

Usage:
    from src.models.statistics import Statistics, DailyStats
    from src.models.trade import TradeMode

    stats = Statistics(
        id=1,
        date=date(2026, 2, 15),
        mode=TradeMode.PAPER,
        starting_capital=10000.0,
        ending_capital=10150.0,
        total_pnl=150.0,
        total_trades=5,
        winning_trades=3,
        losing_trades=2,
        win_rate=0.6,
    )
"""

from __future__ import annotations

__all__ = ["Statistics", "DailyStats"]

import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from src.models.trade import TradeMode


class Statistics(BaseModel):
    """Trading statistics data model.

    Represents daily trading performance statistics.
    All fields align with the database schema in the statistics table.

    Attributes:
        id: Unique statistics identifier (auto-generated)
        date: Statistics date
        mode: Trading mode (PAPER or LIVE)
        starting_capital: Starting capital for the day (USD)
        ending_capital: Ending capital for the day (USD)
        total_pnl: Total profit/loss for the day (USD)
        total_trades: Total number of trades
        winning_trades: Number of winning trades
        losing_trades: Number of losing trades
        win_rate: Win rate (0-1)
        created_at: Record creation timestamp

    Example:
        >>> stats = Statistics(
        ...     id=1,
        ...     date=date(2026, 2, 15),
        ...     mode=TradeMode.PAPER,
        ...     starting_capital=10000.0,
        ...     ending_capital=10150.0,
        ...     total_pnl=150.0,
        ...     total_trades=5,
        ...     winning_trades=3,
        ...     losing_trades=2,
        ...     win_rate=0.6,
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    id: int = Field(..., description="Statistics unique identifier")
    date: datetime.date = Field(..., description="Statistics date")
    mode: TradeMode = Field(..., description="Trading mode")
    starting_capital: float = Field(..., ge=0, description="Starting capital (USD)")
    ending_capital: float | None = Field(
        default=None, description="Ending capital (USD)"
    )
    total_pnl: float | None = Field(default=None, description="Total profit/loss (USD)")
    total_trades: int = Field(..., ge=0, description="Total trades")
    winning_trades: int = Field(..., ge=0, description="Winning trades")
    losing_trades: int = Field(..., ge=0, description="Losing trades")
    win_rate: float | None = Field(
        default=None, ge=0, le=1, description="Win rate (0-1)"
    )
    created_at: datetime.datetime | None = Field(
        default=None, description="Creation timestamp"
    )

    @field_serializer("date")
    def serialize_date(self, d: datetime.date, _info: Any) -> str:
        """Serialize date to ISO 8601 format.

        Args:
            d: The date value to serialize
            _info: Field serializer info (unused)

        Returns:
            ISO 8601 formatted date string (YYYY-MM-DD)
        """
        return d.isoformat()

    @field_serializer("created_at")
    def serialize_datetime(
        self, dt: datetime.datetime | None, _info: Any
    ) -> str | None:
        """Serialize datetime to ISO 8601 format.

        Args:
            dt: The datetime value to serialize
            _info: Field serializer info (unused)

        Returns:
            ISO 8601 formatted string or None
        """
        if dt is None:
            return None
        return dt.isoformat()


class DailyStats(BaseModel):
    """Daily statistics summary model.

    A convenience model for displaying daily trading statistics.
    This is an alias/extension for Statistics with computed fields.

    Attributes:
        date: Statistics date
        mode: Trading mode
        starting_capital: Starting capital
        ending_capital: Ending capital
        daily_pnl: Daily profit/loss
        daily_return_pct: Daily return percentage
        trades_count: Number of trades
        win_count: Number of winning trades
        loss_count: Number of losing trades
        win_rate_pct: Win rate percentage

    Example:
        >>> daily = DailyStats(
        ...     date=date(2026, 2, 15),
        ...     mode=TradeMode.PAPER,
        ...     starting_capital=10000.0,
        ...     ending_capital=10150.0,
        ...     daily_pnl=150.0,
        ...     daily_return_pct=1.5,
        ...     trades_count=5,
        ...     win_count=3,
        ...     loss_count=2,
        ...     win_rate_pct=60.0,
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    date: datetime.date = Field(..., description="Statistics date")
    mode: TradeMode = Field(..., description="Trading mode")
    starting_capital: float = Field(..., ge=0, description="Starting capital (USD)")
    ending_capital: float | None = Field(
        default=None, description="Ending capital (USD)"
    )
    daily_pnl: float | None = Field(default=None, description="Daily profit/loss (USD)")
    daily_return_pct: float | None = Field(default=None, description="Daily return (%)")
    trades_count: int = Field(..., ge=0, description="Number of trades")
    win_count: int = Field(..., ge=0, description="Winning trades")
    loss_count: int = Field(..., ge=0, description="Losing trades")
    win_rate_pct: float | None = Field(
        default=None, ge=0, le=100, description="Win rate (%)"
    )

    @field_serializer("date")
    def serialize_date(self, d: datetime.date, _info: Any) -> str:
        """Serialize date to ISO 8601 format.

        Args:
            d: The date value to serialize
            _info: Field serializer info (unused)

        Returns:
            ISO 8601 formatted date string (YYYY-MM-DD)
        """
        return d.isoformat()

    @classmethod
    def from_statistics(cls, stats: Statistics) -> "DailyStats":
        """Create DailyStats from Statistics model.

        Args:
            stats: Statistics model instance

        Returns:
            DailyStats instance with computed fields
        """
        daily_return_pct: float | None = None
        if stats.ending_capital is not None and stats.starting_capital > 0:
            daily_return_pct = (
                (stats.ending_capital - stats.starting_capital) / stats.starting_capital
            ) * 100

        win_rate_pct: float | None = None
        if stats.win_rate is not None:
            win_rate_pct = stats.win_rate * 100

        return cls(
            date=stats.date,
            mode=stats.mode,
            starting_capital=stats.starting_capital,
            ending_capital=stats.ending_capital,
            daily_pnl=stats.total_pnl,
            daily_return_pct=daily_return_pct,
            trades_count=stats.total_trades,
            win_count=stats.winning_trades,
            loss_count=stats.losing_trades,
            win_rate_pct=win_rate_pct,
        )
