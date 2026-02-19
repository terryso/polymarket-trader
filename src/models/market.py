"""Market data model.

This module defines the Market model and MarketCategory enum for
representing prediction market data.

Usage:
    from src.models.market import Market, MarketCategory

    market = Market(
        id="market-123",
        title="Will X happen by Y date?",
        category=MarketCategory.POLITICS,
        yes_price=0.65,
        no_price=0.35,
    )
"""

from __future__ import annotations

__all__ = ["Market", "MarketCategory"]

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class MarketCategory(str, Enum):
    """Market category enumeration.

    Defines the possible categories for prediction markets.

    Attributes:
        POLITICS: Political events and elections
        BUSINESS: Business and corporate events
        TECHNOLOGY: Technology and tech industry events
        ECONOMICS: Economic indicators and financial events
        CRYPTO: Cryptocurrency and blockchain events
    """

    POLITICS = "politics"
    BUSINESS = "business"
    TECHNOLOGY = "technology"
    ECONOMICS = "economics"
    CRYPTO = "crypto"


class Market(BaseModel):
    """Market data model.

    Represents a prediction market with its metadata and current state.
    All fields align with the database schema in the markets table.

    Attributes:
        id: Unique market identifier (primary key)
        title: Market title/question
        description: Optional market description
        category: Market category classification
        yes_price: Current YES outcome price (0-1 range)
        no_price: Current NO outcome price (0-1 range)
        liquidity: Available liquidity in USD
        deadline: Market deadline/resolution date
        resolution_status: Current resolution status
        resolution_outcome: Final resolution result
        created_at: Record creation timestamp
        updated_at: Record last update timestamp

    Example:
        >>> market = Market(
        ...     id="btc-100k-2026",
        ...     title="Will Bitcoin reach $100k by end of 2026?",
        ...     category=MarketCategory.CRYPTO,
        ...     yes_price=0.45,
        ...     no_price=0.55,
        ...     liquidity=50000.0,
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    id: str = Field(..., description="Market unique identifier")
    title: str = Field(..., min_length=1, description="Market title")
    slug: str | None = Field(default=None, description="Market slug for URL")
    description: str | None = Field(default=None, description="Market description")
    category: MarketCategory | None = Field(default=None, description="Market category")
    yes_price: float | None = Field(
        default=None, ge=0, le=1, description="YES price (0-1)"
    )
    no_price: float | None = Field(
        default=None, ge=0, le=1, description="NO price (0-1)"
    )
    liquidity: float | None = Field(default=None, ge=0, description="Liquidity (USD)")
    deadline: datetime | None = Field(default=None, description="Market deadline")
    resolution_status: str | None = Field(default=None, description="Resolution status")
    resolution_outcome: str | None = Field(
        default=None, description="Resolution outcome"
    )
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Update timestamp")

    @field_serializer("deadline", "created_at", "updated_at")
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
