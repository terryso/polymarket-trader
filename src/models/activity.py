"""Activity data model for recent activity API.

This module defines the ActivityItem model and ActivityType enumeration
for representing recent system activities (trades, predictions, system events).

Story 7.7: 最近活动 API 与前端集成

Usage:
    from src.models.activity import ActivityItem, ActivityType

    activity = ActivityItem(
        id="trade-1",
        type=ActivityType.TRADE,
        description="买入 特朗普胜选 YES @ $0.65",
        time="10:30",
        amount=10.0,
    )
"""

from __future__ import annotations

__all__ = ["ActivityItem", "ActivityType", "ActivityListResponse"]

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ActivityType(str, Enum):
    """Activity type enumeration.

    Defines the possible types of activities displayed in the dashboard.

    Attributes:
        TRADE: Trade activity (buy/sell)
        PREDICTION: LLM prediction activity
        SYSTEM: System event (startup, shutdown, etc.)
    """

    TRADE = "trade"
    PREDICTION = "prediction"
    SYSTEM = "system"


class ActivityItem(BaseModel):
    """Single activity item for dashboard display.

    Represents one activity record in the recent activity list.
    Each activity has a type, description, time, and optional amount.

    Attributes:
        id: Unique activity identifier (format: "{type}-{id}")
        type: Activity type (trade, prediction, system)
        description: Human-readable activity description
        time: Activity time in HH:MM format (for display)
        amount: Optional amount in USD (for trades)
        timestamp: Full timestamp for sorting (not displayed)

    Example:
        >>> activity = ActivityItem(
        ...     id="trade-1",
        ...     type=ActivityType.TRADE,
        ...     description="买入 特朗普胜选 YES @ $0.65",
        ...     time="10:30",
        ...     amount=10.0,
        ...     timestamp=datetime.now(),
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    id: str = Field(..., description="Activity unique identifier")
    type: ActivityType = Field(..., description="Activity type")
    description: str = Field(..., min_length=1, description="Activity description")
    time: str = Field(..., description="Activity time (HH:MM format)")
    amount: float | None = Field(
        default=None, ge=0, description="Amount in USD (optional)"
    )
    timestamp: datetime | None = Field(
        default=None, description="Full timestamp for sorting"
    )

    @field_serializer("timestamp")
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


class ActivityListResponse(BaseModel):
    """Activity list response model for API.

    Contains a list of activity items for the dashboard.

    Attributes:
        items: List of activity items
        total: Total number of activities available

    Example:
        >>> response = ActivityListResponse(
        ...     items=[activity1, activity2],
        ...     total=2,
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    items: list[ActivityItem] = Field(
        default_factory=list, description="List of activity items"
    )
    total: int = Field(..., ge=0, description="Total number of activities")
