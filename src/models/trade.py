"""Trade data model.

This module defines the Trade model and related enumerations for
representing trade records.

Usage:
    from src.models.trade import Trade, TradeType, TradeMode, TradeStatus

    trade = Trade(
        id=1,
        market_id="market-123",
        trade_type=TradeType.BUY_YES,
        mode=TradeMode.PAPER,
        amount=100.0,
        price=0.65,
        status=TradeStatus.FILLED,
    )
"""

from __future__ import annotations

__all__ = ["Trade", "TradeType", "TradeMode", "TradeStatus"]

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class TradeType(str, Enum):
    """Trade type enumeration.

    Defines the possible types of trades.

    Attributes:
        BUY_YES: Buy YES outcome shares
        BUY_NO: Buy NO outcome shares
        SELL_YES: Sell YES outcome shares
        SELL_NO: Sell NO outcome shares
        SELL: Generic sell (deprecated, for backwards compatibility)
    """

    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    SELL_YES = "SELL_YES"
    SELL_NO = "SELL_NO"
    SELL = "SELL"  # Backwards compatibility for old trades


class TradeMode(str, Enum):
    """Trade mode enumeration.

    Defines the trading mode (simulation vs live).

    Attributes:
        PAPER: Paper trading (simulation)
        LIVE: Live trading (real money)
    """

    PAPER = "PAPER"
    LIVE = "LIVE"


class TradeStatus(str, Enum):
    """Trade status enumeration.

    Defines the possible states of a trade.

    Attributes:
        PENDING: Trade is pending execution
        FILLED: Trade has been executed
        CANCELLED: Trade was cancelled
    """

    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    CANCELED = "CANCELED"  # Alternative spelling


class Trade(BaseModel):
    """Trade data model.

    Represents a trade record with all associated metadata.
    All fields align with the database schema in the trades table.

    Story 10.6: Added exit_type field for tracking exit reason.

    Attributes:
        id: Unique trade identifier (auto-generated)
        market_id: Reference to the market
        trade_type: Type of trade (BUY_YES, BUY_NO, SELL)
        mode: Trading mode (PAPER or LIVE)
        amount: Trade amount in USD
        price: Price per share (0-1 range)
        shares: Number of shares traded
        status: Current trade status
        llm_prediction_id: Reference to LLM prediction (if any)
        position_id: Reference to position (if any)
        exit_type: Type of exit (take_profit, stop_loss, time_exit, signal_exit, manual)
        created_at: Trade creation timestamp

    Example:
        >>> trade = Trade(
        ...     id=1,
        ...     market_id="btc-100k-2026",
        ...     trade_type=TradeType.BUY_YES,
        ...     mode=TradeMode.PAPER,
        ...     amount=100.0,
        ...     price=0.45,
        ...     status=TradeStatus.FILLED,
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    id: int = Field(..., description="Trade unique identifier")
    market_id: str = Field(..., description="Market reference")
    trade_type: TradeType = Field(..., description="Trade type")
    mode: TradeMode = Field(..., description="Trading mode")
    amount: float = Field(..., ge=0, description="Trade amount (USD)")
    price: float = Field(..., ge=0, le=1, description="Price per share (0-1)")
    shares: float | None = Field(default=None, ge=0, description="Number of shares")
    status: TradeStatus = Field(..., description="Trade status")
    llm_prediction_id: int | None = Field(
        default=None, description="LLM prediction reference"
    )
    position_id: int | None = Field(default=None, description="Position reference")
    polymarket_order_id: str | None = Field(
        default=None, description="Polymarket order ID (for synced trades)"
    )
    exit_type: str | None = Field(
        default=None,
        description="Exit type (take_profit, stop_loss, time_exit, signal_exit, manual)",
    )
    created_at: datetime | None = Field(default=None, description="Creation timestamp")

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
