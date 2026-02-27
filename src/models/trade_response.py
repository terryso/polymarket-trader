"""Trade API response models.

This module defines Pydantic models for trade API responses.

Story 7.3: 持仓与交易 API

Usage:
    from src.models.trade_response import TradeListItem, TradeResponse, TradeListQueryParams

    item = TradeListItem(
        id=1,
        market_id="btc-100k-2026",
        trade_type=TradeType.BUY_YES,
        mode=TradeMode.PAPER,
        amount=100.0,
        price=0.45,
        status=TradeStatus.FILLED,
    )
"""

from __future__ import annotations

__all__ = ["TradeListItem", "TradeResponse", "TradeListQueryParams"]

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from src.models.trade import TradeMode, TradeStatus, TradeType


class TradeListItem(BaseModel):
    """Trade list item for API list responses.

    Contains trade fields for list display.
    Used in the trade list endpoint.

    Story 10.6: Added exit_type field for displaying exit reason in trade history.

    Attributes:
        id: Trade unique identifier
        market_id: Reference to the market
        trade_type: Type of trade
        mode: Trading mode
        amount: Trade amount in USD
        price: Price per share
        shares: Number of shares traded
        status: Trade status
        exit_type: Type of exit (take_profit, stop_loss, time_exit, signal_exit, manual, or None)
        created_at: Trade creation timestamp

    Example:
        >>> TradeListItem(
        ...     id=1,
        ...     market_id="btc-100k-2026",
        ...     trade_type=TradeType.BUY_YES,
        ...     mode=TradeMode.PAPER,
        ...     amount=100.0,
        ...     price=0.45,
        ...     shares=222.22,
        ...     status=TradeStatus.FILLED,
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    id: int = Field(..., description="Trade ID")
    market_id: str = Field(..., description="Market reference")
    trade_type: TradeType = Field(..., description="Trade type")
    mode: TradeMode = Field(..., description="Trading mode")
    amount: float = Field(..., ge=0, description="Trade amount (USD)")
    price: float = Field(..., ge=0, le=1, description="Price per share (0-1)")
    shares: float | None = Field(None, ge=0, description="Number of shares")
    status: TradeStatus = Field(..., description="Trade status")
    exit_type: str | None = Field(
        None,
        description="Exit type (take_profit, stop_loss, time_exit, signal_exit, manual)",
    )
    created_at: datetime | None = Field(None, description="Creation timestamp")

    @field_serializer("created_at")
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


class TradeResponse(BaseModel):
    """Full trade details for API detail responses.

    Contains all trade fields for detailed view.
    Used in the trade detail endpoint.

    Story 10.6: Added exit_type field for displaying exit reason in trade history.

    Attributes:
        id: Trade unique identifier
        market_id: Reference to the market
        trade_type: Type of trade
        mode: Trading mode
        amount: Trade amount in USD
        price: Price per share
        shares: Number of shares traded
        status: Trade status
        llm_prediction_id: Reference to LLM prediction
        position_id: Reference to position
        exit_type: Type of exit (take_profit, stop_loss, time_exit, signal_exit, manual, or None)
        created_at: Trade creation timestamp

    Example:
        >>> TradeResponse(
        ...     id=1,
        ...     market_id="btc-100k-2026",
        ...     trade_type=TradeType.BUY_YES,
        ...     mode=TradeMode.PAPER,
        ...     amount=100.0,
        ...     price=0.45,
        ...     shares=222.22,
        ...     status=TradeStatus.FILLED,
        ...     llm_prediction_id=10,
        ...     position_id=5,
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    id: int = Field(..., description="Trade ID")
    market_id: str = Field(..., description="Market reference")
    trade_type: TradeType = Field(..., description="Trade type")
    mode: TradeMode = Field(..., description="Trading mode")
    amount: float = Field(..., ge=0, description="Trade amount (USD)")
    price: float = Field(..., ge=0, le=1, description="Price per share (0-1)")
    shares: float | None = Field(None, ge=0, description="Number of shares")
    status: TradeStatus = Field(..., description="Trade status")
    llm_prediction_id: int | None = Field(None, description="LLM prediction reference")
    position_id: int | None = Field(None, description="Position reference")
    exit_type: str | None = Field(
        None,
        description="Exit type (take_profit, stop_loss, time_exit, signal_exit, manual)",
    )
    created_at: datetime | None = Field(None, description="Creation timestamp")

    @field_serializer("created_at")
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


class TradeListQueryParams(BaseModel):
    """Query parameters for trade list endpoint.

    Attributes:
        page: Page number (1-based)
        per_page: Items per page (max 100)
        mode: Filter by trading mode

    Example:
        >>> params = TradeListQueryParams(page=1, per_page=20)
        >>> params = TradeListQueryParams(page=1, mode=TradeMode.PAPER)
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    mode: TradeMode | None = Field(default=None, description="Mode filter")
