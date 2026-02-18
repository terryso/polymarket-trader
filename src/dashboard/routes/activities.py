"""Activity API routes for recent activity display.

This module provides REST API endpoints for retrieving recent activities
including trades, predictions, and system events.

Story 7.7: 最近活动 API 与前端集成

Endpoints:
    GET /api/activities - Get recent activities

Query Parameters:
    limit: Maximum number of activities to return (default: 10, max: 50)

Usage:
    from src.dashboard.routes.activities import router
    app.include_router(router, prefix="/api/activities", tags=["activities"])
"""

from __future__ import annotations

__all__ = ["router"]

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.models.activity import ActivityItem, ActivityListResponse, ActivityType
from src.models.api_response import ApiResponse
from src.storage.repositories.prediction_repo import PredictionRepository
from src.storage.repositories.trade_repo import TradeRepository

logger = logging.getLogger(__name__)

router = APIRouter()


def get_trade_repository() -> TradeRepository:
    """Get TradeRepository instance for dependency injection.

    Returns:
        TradeRepository instance
    """
    return TradeRepository()


def get_prediction_repository() -> PredictionRepository:
    """Get PredictionRepository instance for dependency injection.

    Returns:
        PredictionRepository instance
    """
    return PredictionRepository()


# Aliases for backward compatibility with tests
trade_repo_dependency = get_trade_repository
prediction_repo_dependency = get_prediction_repository


def _format_trade_description(
    trade_type: str,
    market_title: str,
    price: float,
) -> str:
    """Format trade description for activity display.

    Args:
        trade_type: Trade type (BUY_YES, BUY_NO, SELL_YES, SELL_NO)
        market_title: Market title
        price: Trade price

    Returns:
        Formatted description string
    """
    # Determine action (buy/sell) and outcome (YES/NO)
    if trade_type in ("BUY_YES", "BUY_NO"):
        action = "买入"
    else:
        action = "卖出"

    outcome = "YES" if trade_type in ("BUY_YES", "SELL_YES") else "NO"

    # Truncate market title if too long
    if len(market_title) > 30:
        market_title = market_title[:27] + "..."

    return f"{action} {market_title} {outcome} @ ${price:.2f}"


def _format_prediction_description(
    market_title: str,
    confidence: float,
    recommendation: str | None,
) -> str:
    """Format prediction description for activity display.

    Args:
        market_title: Market title
        confidence: Confidence level (0-1)
        recommendation: LLM recommendation

    Returns:
        Formatted description string
    """
    # Truncate market title if too long
    if len(market_title) > 30:
        market_title = market_title[:27] + "..."

    confidence_pct = int(confidence * 100)
    rec_text = recommendation if recommendation else "NO_TRADE"

    return f"预测 {market_title} {confidence_pct}% {rec_text}"


def _format_time(dt: datetime | None) -> str:
    """Format datetime to HH:MM format for display.

    Args:
        dt: Datetime to format

    Returns:
        Formatted time string (HH:MM)
    """
    if dt is None:
        return "--:--"
    return dt.strftime("%H:%M")


@router.get(
    "",
    response_model=ApiResponse[ActivityListResponse],
    summary="Get recent activities",
    description="Retrieve recent activities including trades, predictions, and system events.",
)
async def get_activities(
    limit: Annotated[int, Query(ge=1, le=50, description="Max activities to return")] = 10,
    trade_repo: TradeRepository = Depends(get_trade_repository),
    prediction_repo: PredictionRepository = Depends(get_prediction_repository),
) -> ApiResponse[ActivityListResponse]:
    """Get recent activities from trades, predictions, and system events.

    Fetches recent trades, predictions, and system events,
    merges them by timestamp, and returns the most recent ones.

    Args:
        limit: Maximum number of activities to return (default: 10, max: 50)
        trade_repo: TradeRepository dependency
        prediction_repo: PredictionRepository dependency

    Returns:
        ApiResponse containing list of recent activities

    Example:
        >>> # GET /api/activities?limit=10
        >>> # Response: {"success": true, "data": {"items": [...], "total": 5}}
    """
    logger.info(f"📋 Getting recent activities, limit={limit}")

    activities: list[ActivityItem] = []

    # Get recent trades
    try:
        trades = await trade_repo.get_recent(limit=limit)
        logger.debug(f"📋 Found {len(trades)} recent trades")
        for trade in trades:
            # Get market title from market_id (simplified: just use market_id for now)
            # In a production system, we would join with markets table
            market_title = trade.market_id

            # Format description
            description = _format_trade_description(
                trade.trade_type.value,
                market_title,
                trade.price,
            )

            activities.append(
                ActivityItem(
                    id=f"trade-{trade.id}",
                    type=ActivityType.TRADE,
                    description=description,
                    time=_format_time(trade.created_at),
                    amount=trade.amount,
                    timestamp=trade.created_at,
                )
            )
    except Exception as e:
        logger.warning(f"📋 Failed to get trades: {e}")

    # Get recent predictions
    try:
        predictions = await prediction_repo.get_all(limit=limit)
        logger.debug(f"📋 Found {len(predictions)} recent predictions")
        for pred in predictions:
            # Get market title (simplified: use market_id)
            market_title = pred.market_id

            # Format description
            description = _format_prediction_description(
                market_title,
                pred.confidence,
                pred.recommendation.value if pred.recommendation else None,
            )

            activities.append(
                ActivityItem(
                    id=f"prediction-{pred.id}",
                    type=ActivityType.PREDICTION,
                    description=description,
                    time=_format_time(pred.created_at),
                    amount=None,  # Predictions don't have amount
                    timestamp=pred.created_at,
                )
            )
    except Exception as e:
        logger.warning(f"📋 Failed to get predictions: {e}")

    # Add system startup event (from system state)
    # For now, we'll add a simple system event if there are any activities
    # In a production system, we would track actual system events
    if len(activities) > 0:
        # Get current time for system event
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        # Add system startup event based on the earliest activity
        activities.append(
            ActivityItem(
                id="system-startup",
                type=ActivityType.SYSTEM,
                description="系统启动，开始扫描市场",
                time=current_time,
                amount=None,
                timestamp=now,
            )
        )

    # Sort by timestamp (most recent first), handling None values
    activities.sort(key=lambda x: x.timestamp or datetime.min, reverse=True)

    # Apply limit
    total = len(activities)
    activities = activities[:limit]

    logger.info(f"📋 Returning {len(activities)} activities (total: {total})")

    response = ActivityListResponse(
        items=activities,
        total=total,
    )

    return ApiResponse(success=True, data=response, error=None)
