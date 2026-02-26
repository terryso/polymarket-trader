"""Position API response models.

This module defines Pydantic models for position API responses.

Story 7.3: 持仓与交易 API

Usage:
    from src.models.position_response import PositionListItem, PositionResponse

    item = PositionListItem(
        id=1,
        market_id="btc-100k-2026",
        outcome=PositionOutcome.YES,
        shares=222.22,
        avg_price=0.45,
        status=PositionStatus.OPEN,
    )
"""

from __future__ import annotations

__all__ = ["PositionListItem", "PositionResponse"]

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from src.models.position import PositionOutcome, PositionStatus


class PositionListItem(BaseModel):
    """Position list item for API list responses.

    Contains position fields for list display.
    Used in the position list endpoint.

    Attributes:
        id: Position unique identifier
        market_id: Reference to the market
        outcome: Position outcome type (YES/NO)
        shares: Number of shares held
        avg_price: Average purchase price per share
        current_value: Current position value in USD
        pnl: Profit/Loss in USD
        status: Current position status
        opened_at: Position opening timestamp

    Example:
        >>> PositionListItem(
        ...     id=1,
        ...     market_id="btc-100k-2026",
        ...     outcome=PositionOutcome.YES,
        ...     shares=222.22,
        ...     avg_price=0.45,
        ...     current_value=155.55,
        ...     pnl=55.55,
        ...     status=PositionStatus.OPEN,
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    id: int = Field(..., description="Position ID")
    market_id: str = Field(..., description="Market reference")
    outcome: PositionOutcome = Field(..., description="Position outcome")
    shares: float = Field(..., ge=0, description="Number of shares")
    avg_price: float = Field(..., ge=0, le=1, description="Average price (0-1)")
    cur_price: float | None = Field(None, ge=0, le=1, description="Current price (0-1)")
    current_value: float | None = Field(None, description="Current value (USD)")
    pnl: float | None = Field(None, description="Profit/Loss (USD)")
    status: PositionStatus = Field(..., description="Position status")
    opened_at: datetime | None = Field(None, description="Opening timestamp")

    @field_serializer("opened_at")
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


class PositionResponse(BaseModel):
    """Full position details for API detail responses.

    Contains all position fields for detailed view.
    Used in the position detail endpoint.

    Attributes:
        id: Position unique identifier
        market_id: Reference to the market
        outcome: Position outcome type (YES/NO)
        shares: Number of shares held
        avg_price: Average purchase price per share
        initial_value: Initial position value in USD
        current_value: Current position value in USD
        pnl: Profit/Loss in USD
        status: Current position status
        opened_at: Position opening timestamp
        closed_at: Position closing timestamp

    Example:
        >>> PositionResponse(
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

    id: int = Field(..., description="Position ID")
    market_id: str = Field(..., description="Market reference")
    outcome: PositionOutcome = Field(..., description="Position outcome")
    shares: float = Field(..., ge=0, description="Number of shares")
    avg_price: float = Field(..., ge=0, le=1, description="Average price (0-1)")
    initial_value: float | None = Field(None, description="Initial value (USD)")
    current_value: float | None = Field(None, description="Current value (USD)")
    pnl: float | None = Field(None, description="Profit/Loss (USD)")
    status: PositionStatus = Field(..., description="Position status")
    opened_at: datetime | None = Field(None, description="Opening timestamp")
    closed_at: datetime | None = Field(None, description="Closing timestamp")

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
