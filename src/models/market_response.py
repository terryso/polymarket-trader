"""Market API response models.

This module defines Pydantic models for market API responses,
optimized for list and detail endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from src.models.market import MarketCategory


class MarketListItem(BaseModel):
    """Market list item for API list responses.

    Contains a subset of market fields optimized for list display.
    This is a lightweight model for efficient list operations.

    Attributes:
        id: Market unique identifier
        title: Market title/question
        category: Market category classification
        yes_price: YES outcome price (0-1)
        no_price: NO outcome price (0-1)
        liquidity: Available liquidity in USD
        deadline: Market deadline/resolution date
        resolution_status: Resolution status (if resolved)

    Example:
        >>> item = MarketListItem(
        ...     id="market-123",
        ...     title="Will X happen by Y date?",
        ...     category=MarketCategory.POLITICS,
        ...     yes_price=0.65,
        ...     no_price=0.35,
        ...     liquidity=50000.0,
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    id: str = Field(..., description="Market ID")
    title: str = Field(..., description="Market title")
    category: MarketCategory | None = Field(None, description="Market category")
    yes_price: float | None = Field(None, description="YES price (0-1)")
    no_price: float | None = Field(None, description="NO price (0-1)")
    liquidity: float | None = Field(None, description="Liquidity (USD)")
    deadline: datetime | None = Field(None, description="Market deadline")
    resolution_status: str | None = Field(None, description="Resolution status")

    @field_serializer("deadline")
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


class MarketResponse(BaseModel):
    """Full market details for API detail responses.

    Contains all market fields for detailed view, including
    description, resolution outcome, and timestamps.

    Attributes:
        id: Market unique identifier
        title: Market title/question
        description: Market description with details
        category: Market category classification
        yes_price: YES outcome price (0-1)
        no_price: NO outcome price (0-1)
        liquidity: Available liquidity in USD
        deadline: Market deadline/resolution date
        resolution_status: Resolution status
        resolution_outcome: Resolution outcome (if resolved)
        created_at: Record creation timestamp
        updated_at: Record last update timestamp

    Example:
        >>> response = MarketResponse(
        ...     id="market-123",
        ...     title="Will X happen by Y date?",
        ...     description="Detailed description of the market...",
        ...     category=MarketCategory.POLITICS,
        ...     yes_price=0.65,
        ...     no_price=0.35,
        ...     liquidity=50000.0,
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    id: str = Field(..., description="Market ID")
    title: str = Field(..., description="Market title")
    description: str | None = Field(None, description="Market description")
    category: MarketCategory | None = Field(None, description="Market category")
    yes_price: float | None = Field(None, description="YES price (0-1)")
    no_price: float | None = Field(None, description="NO price (0-1)")
    liquidity: float | None = Field(None, description="Liquidity (USD)")
    deadline: datetime | None = Field(None, description="Market deadline")
    resolution_status: str | None = Field(None, description="Resolution status")
    resolution_outcome: str | None = Field(None, description="Resolution outcome")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Update timestamp")

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


class MarketListQueryParams(BaseModel):
    """Query parameters for market list endpoint.

    Validates and provides defaults for pagination and filtering
    parameters used in the market list endpoint.

    Attributes:
        page: Page number (1-based indexing)
        per_page: Items per page (1-100)
        status: Status filter (active/resolved/all)
        category: Category filter

    Example:
        >>> params = MarketListQueryParams(page=1, per_page=20, status="active")
        >>> params = MarketListQueryParams(category=MarketCategory.POLITICS)
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    per_page: int = Field(
        default=20, ge=1, le=100, description="Items per page (max 100)"
    )
    status: str = Field(
        default="all", description="Status filter (active/resolved/all)"
    )
    category: MarketCategory | None = Field(default=None, description="Category filter")


__all__ = ["MarketListItem", "MarketResponse", "MarketListQueryParams"]
