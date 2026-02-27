"""Position data model.

This module defines the Position model and related enumerations for
representing trading positions.

Usage:
    from src.models.position import Position, PositionStatus, PositionOutcome

    position = Position(
        id=1,
        market_id="market-123",
        outcome=PositionOutcome.YES,
        shares=100.0,
        avg_price=0.45,
        status=PositionStatus.OPEN,
    )
"""

from __future__ import annotations

__all__ = ["Position", "PositionStatus", "PositionOutcome", "CacheFreshness"]

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class PositionStatus(str, Enum):
    """Position status enumeration.

    Defines the possible states of a position.

    Attributes:
        OPEN: Position is currently open
        CLOSED: Position has been closed
    """

    OPEN = "OPEN"
    CLOSED = "CLOSED"


class PositionOutcome(str, Enum):
    """Position outcome enumeration.

    Defines the outcome type of a position.

    Attributes:
        YES: Position is on YES outcome
        NO: Position is on NO outcome
    """

    YES = "YES"
    NO = "NO"


class CacheFreshness(str, Enum):
    """Cache freshness enumeration.

    Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源

    Defines the freshness state of cached position data.

    Attributes:
        FRESH: Cache is valid and within TTL
        STALE: Cache is expired but API failed, using old data
        EXPIRED: Cache is expired and no data available
    """

    FRESH = "fresh"
    STALE = "stale"
    EXPIRED = "expired"


class Position(BaseModel):
    """Position data model.

    Represents a trading position with profit/loss tracking.
    All fields align with the database schema in the positions table.

    Attributes:
        id: Unique position identifier (auto-generated)
        market_id: Reference to the market
        outcome: Position outcome type (YES or NO)
        shares: Number of shares held
        avg_price: Average purchase price per share
        initial_value: Initial position value in USD
        current_value: Current position value in USD
        pnl: Profit/Loss in USD
        status: Current position status
        opened_at: Position opening timestamp
        closed_at: Position closing timestamp

    Example:
        >>> position = Position(
        ...     id=1,
        ...     market_id="btc-100k-2026",
        ...     outcome=PositionOutcome.YES,
        ...     shares=222.22,
        ...     avg_price=0.45,
        ...     initial_value=100.0,
        ...     current_value=155.55,
        ...     pnl=55.55,
        ...     status=PositionStatus.OPEN,
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    id: int = Field(..., description="Position unique identifier")
    market_id: str = Field(..., description="Market reference")
    outcome: PositionOutcome = Field(..., description="Position outcome type")
    shares: float = Field(..., ge=0, description="Number of shares")
    avg_price: float = Field(..., ge=0, le=1, description="Average price (0-1)")
    cur_price: float | None = Field(
        default=None, ge=0, le=1, description="Current price (0-1)"
    )
    initial_value: float | None = Field(default=None, description="Initial value (USD)")
    current_value: float | None = Field(default=None, description="Current value (USD)")
    pnl: float | None = Field(default=None, description="Profit/Loss (USD)")
    status: PositionStatus = Field(..., description="Position status")
    opened_at: datetime | None = Field(default=None, description="Opening timestamp")
    closed_at: datetime | None = Field(default=None, description="Closing timestamp")

    @field_serializer("opened_at", "closed_at")
    def serialize_datetime(self, dt: datetime | None, _info: Any) -> str | None:
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
