"""Trade data API routes.

This module provides REST API endpoints for trade operations.

Story 7.3: 持仓与交易 API

Endpoints:
    GET /api/trades - Get trade history with pagination
    GET /api/trades/{trade_id} - Get trade details

Query Parameters:
    page: Page number (default: 1)
    per_page: Items per page (default: 20, max: 100)
    mode: Filter by trading mode (paper/live)

Usage:
    from src.dashboard.routes.trades import router
    app.include_router(router, prefix="/api/trades", tags=["trades"])
"""

from __future__ import annotations

__all__ = ["router"]

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.models.api_response import (
    ApiResponse,
    ErrorCode,
    PaginatedResponse,
    PaginationMeta,
)
from src.models.trade import TradeMode
from src.models.trade_response import TradeListItem, TradeResponse
from src.storage.repositories.trade_repo import TradeRepository

logger = logging.getLogger(__name__)

router = APIRouter()


def get_trade_repository() -> TradeRepository:
    """Get TradeRepository instance.

    Returns:
        TradeRepository instance
    """
    return TradeRepository()


@router.get(
    "",
    response_model=PaginatedResponse[TradeListItem],
    summary="Get trade history",
    description="Retrieve trade history with pagination and optional filtering by mode.",
)
async def list_trades(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    mode: Annotated[str | None, Query(description="Mode filter (paper/live)")] = None,
    repo: TradeRepository = Depends(get_trade_repository),
) -> PaginatedResponse[TradeListItem]:
    """Get trade history with pagination and filtering.

    Args:
        page: Page number (1-based)
        per_page: Items per page (max 100)
        mode: Mode filter (paper/live)
        repo: TradeRepository dependency

    Returns:
        Paginated list of trades

    Example:
        >>> # GET /api/trades?page=1&per_page=20&mode=paper
        >>> # Response: {"success": true, "data": [...], "meta": {"total": 50, "page": 1, "per_page": 20}}
    """
    logger.info(f"💰 Listing trades: page={page}, per_page={per_page}, mode={mode}")

    # TODO: [LOW Priority] Consider database-level pagination for better performance.
    # Current implementation fetches up to 1000 records and paginates in memory.
    # For large datasets, this should be optimized to use OFFSET/LIMIT at the SQL level
    # by adding a paginated query method to TradeRepository (e.g., get_paginated(page, per_page, mode)).
    # See NFR4: Response time should be < 2 seconds.

    # Get trades based on mode filter
    if mode:
        try:
            mode_enum = TradeMode(mode.upper())
            trades = await repo.get_by_mode(mode_enum)
        except ValueError:
            # Invalid mode, return empty list
            logger.warning(f"💰 Invalid mode filter: {mode}")
            trades = []
    else:
        trades = await repo.get_recent(limit=1000)  # Get all for pagination

    # Calculate pagination
    total = len(trades)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_trades = trades[start:end]

    # Convert to response models
    items = [
        TradeListItem(
            id=t.id,
            market_id=t.market_id,
            trade_type=t.trade_type,
            mode=t.mode,
            amount=t.amount,
            price=t.price,
            shares=t.shares,
            status=t.status,
            created_at=t.created_at,
        )
        for t in paginated_trades
    ]

    logger.info(
        f"💰 Found {total} trades, returning page {page} with {len(items)} items"
    )

    return PaginatedResponse(
        success=True,
        data=items,
        meta=PaginationMeta(total=total, page=page, per_page=per_page),
    )


@router.get(
    "/{trade_id}",
    response_model=ApiResponse[TradeResponse],
    summary="Get trade details",
    description="Retrieve detailed information about a specific trade.",
)
async def get_trade(
    trade_id: int,
    repo: TradeRepository = Depends(get_trade_repository),
) -> ApiResponse[TradeResponse]:
    """Get trade details by ID.

    Args:
        trade_id: Trade ID
        repo: TradeRepository dependency

    Returns:
        Trade details

    Raises:
        HTTPException: If trade not found (404)

    Example:
        >>> # GET /api/trades/1
        >>> # Response: {"success": true, "data": {...}}
    """
    logger.info(f"💰 Getting trade: {trade_id}")

    trade = await repo.get_by_id(trade_id)

    if trade is None:
        logger.warning(f"💰 Trade not found: {trade_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": ErrorCode.NOT_FOUND,
                    "message": f"Trade not found: {trade_id}",
                },
            },
        )

    response = TradeResponse(
        id=trade.id,
        market_id=trade.market_id,
        trade_type=trade.trade_type,
        mode=trade.mode,
        amount=trade.amount,
        price=trade.price,
        shares=trade.shares,
        status=trade.status,
        llm_prediction_id=trade.llm_prediction_id,
        position_id=trade.position_id,
        created_at=trade.created_at,
    )

    logger.info(f"💰 Retrieved trade {trade_id}")
    return ApiResponse(success=True, data=response, error=None)
