"""Trade data API routes.

This module provides REST API endpoints for trade operations.

Story 7.3: 持仓与交易 API
Story 7.9: 交易历史按模式实时显示

Endpoints:
    GET /api/trades - Get trade history with pagination (mode determined by settings.trading_mode)
    GET /api/trades/{trade_id} - Get trade details

Query Parameters:
    page: Page number (default: 1)
    per_page: Items per page (default: 20, max: 100)

Note:
    Trading mode (paper/live) is now determined by TRADING_MODE environment variable,
    not by query parameter. See Story 7.9.

Usage:
    from src.dashboard.routes.trades import router
    app.include_router(router, prefix="/api/trades", tags=["trades"])
"""

from __future__ import annotations

__all__ = ["router"]

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.polymarket import OrderHistoryItem, OrderHistoryResult, PolymarketClient
from src.config import settings
from src.models.api_response import (
    ApiResponse,
    ErrorCode,
    ErrorDetail,
    PaginatedResponse,
    PaginationMeta,
)
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
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


def _convert_order_to_trade(order: OrderHistoryItem) -> Trade:
    """Convert OrderHistoryItem to Trade model.

    Args:
        order: Order history item from Polymarket API

    Returns:
        Trade model with data from order
    """
    # Determine trade type from side and outcome
    side = order.side.upper()
    outcome = order.outcome.upper()

    if side == "BUY" and outcome == "YES":
        trade_type = TradeType.BUY_YES
    elif side == "BUY" and outcome == "NO":
        trade_type = TradeType.BUY_NO
    elif side == "SELL" and outcome == "YES":
        trade_type = TradeType.SELL_YES
    else:
        trade_type = TradeType.SELL_NO

    return Trade(
        id=int(order.order_id) if order.order_id.isdigit() else 0,
        market_id=order.market_id,
        trade_type=trade_type,
        mode=TradeMode.LIVE,
        amount=order.size * order.price,  # USD amount
        price=order.price,
        shares=order.size,
        status=TradeStatus.FILLED,  # Order history only contains filled orders
        created_at=order.created_at,
    )


@router.get(
    "",
    response_model=PaginatedResponse[TradeListItem],
    summary="Get trade history",
    description="Retrieve trade history with pagination. Mode is determined by TRADING_MODE setting.",
)
async def list_trades(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    type_filter: Annotated[str | None, Query(description="Type filter (buy/sell)")] = None,
    repo: TradeRepository = Depends(get_trade_repository),
) -> PaginatedResponse[TradeListItem]:
    """Get trade history with pagination.

    Trading mode is determined by settings.trading_mode (TRADING_MODE env var):
    - Paper mode: Returns trades from local database (mode=PAPER)
    - Live mode: Returns trades from Polymarket API in real-time

    Args:
        page: Page number (1-based)
        per_page: Items per page (max 100)
        type_filter: Filter by trade type (buy/sell)
        repo: TradeRepository dependency

    Returns:
        Paginated list of trades

    Example:
        >>> # GET /api/trades?page=1&per_page=20&type_filter=buy
        >>> # Response: {"success": true, "data": [...], "meta": {"total": 50, "page": 1, "per_page": 20}}
    """
    trading_mode = settings.trading_mode
    logger.info(
        f"💰 Listing trades: page={page}, per_page={per_page}, "
        f"type_filter={type_filter}, mode={trading_mode}"
    )

    # Get trades based on trading mode from settings
    if trading_mode == "paper":
        # Paper mode: fetch from local database
        trades = await repo.get_by_mode(TradeMode.PAPER)
    else:
        # Live mode: fetch from Polymarket API
        client = PolymarketClient()
        result: OrderHistoryResult = client.get_order_history()

        if not result.is_success:
            logger.warning(f"💰 Failed to fetch order history: {result.error}")
            # Return empty list with error indication
            return PaginatedResponse(
                success=False,
                data=[],
                meta=PaginationMeta(total=0, page=page, per_page=per_page),
                error=ErrorDetail(
                    code=ErrorCode.NETWORK_ERROR,
                    message=result.error or "Failed to fetch order history",
                ),
            )

        # Convert OrderHistoryItem to Trade
        trades = [_convert_order_to_trade(order) for order in result.orders]

    # Apply type filter if specified
    if type_filter:
        type_lower = type_filter.lower()
        if type_lower == "buy":
            trades = [
                t
                for t in trades
                if t.trade_type in (TradeType.BUY_YES, TradeType.BUY_NO)
            ]
        elif type_lower == "sell":
            trades = [
                t
                for t in trades
                if t.trade_type in (TradeType.SELL_YES, TradeType.SELL_NO)
            ]

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
            exit_type=t.exit_type,
            created_at=t.created_at,
        )
        for t in paginated_trades
    ]

    logger.info(
        f"💰 Found {total} trades (mode={trading_mode}), returning page {page} with {len(items)} items"
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
        exit_type=trade.exit_type,
        created_at=trade.created_at,
    )

    logger.info(f"💰 Retrieved trade {trade_id}")
    return ApiResponse(success=True, data=response, error=None)


# ==================== Story 5.6: 交易历史同步 (DEPRECATED in Story 7.9) ====================
# NOTE: These endpoints are deprecated. Trading mode is now determined by TRADING_MODE setting.
# In live mode, trades are fetched in real-time from Polymarket API.
# These endpoints are kept for backward compatibility but may be removed in future versions.


class SyncStatusResponse(BaseModel):
    """Sync status response model (DEPRECATED)."""

    deprecated: bool = True
    message: str = "This endpoint is deprecated. Trading mode is now automatic."
    last_sync_at: str | None = None
    is_syncing: bool = False
    can_sync: bool = False
    last_error: str | None = None
    total_synced: int = 0


class SyncResultResponse(BaseModel):
    """Sync result response model (DEPRECATED)."""

    deprecated: bool = True
    message: str = "This endpoint is deprecated. Trading mode is now automatic."
    new_trades: int = 0
    updated_trades: int = 0
    consistent_trades: int = 0
    inconsistent_trades: int = 0
    total_fetched: int = 0
    last_sync_at: str
    error: str | None = None


@router.get(
    "/sync/status",
    response_model=ApiResponse[SyncStatusResponse],
    summary="[DEPRECATED] Get sync status",
    description="DEPRECATED: This endpoint is deprecated. Trading mode is now determined by TRADING_MODE setting.",
    deprecated=True,
)
async def get_sync_status() -> ApiResponse[SyncStatusResponse]:
    """Get current trade sync status (DEPRECATED).

    .. deprecated::
        This endpoint is deprecated as of Story 7.9.
        Trading mode is now determined by TRADING_MODE environment variable.
        In live mode, trades are fetched in real-time from Polymarket API.

    Returns:
        Sync status information with deprecation notice
    """
    from src.trading.trade_sync import TradeSyncService

    logger.warning("💰 DEPRECATED: get_sync_status endpoint called")

    service = TradeSyncService()
    status = await service.get_sync_status()

    response = SyncStatusResponse(
        last_sync_at=status.last_sync_at.isoformat() if status.last_sync_at else None,
        is_syncing=status.is_syncing,
        can_sync=status.can_sync,
        last_error=status.last_error,
        total_synced=status.total_synced,
    )

    return ApiResponse(success=True, data=response, error=None)


@router.post(
    "/sync",
    response_model=ApiResponse[SyncResultResponse],
    summary="[DEPRECATED] Sync trades from Polymarket",
    description="DEPRECATED: This endpoint is deprecated. Trading mode is now determined by TRADING_MODE setting.",
    deprecated=True,
)
async def sync_trades() -> ApiResponse[SyncResultResponse]:
    """Sync trades from Polymarket API (DEPRECATED).

    .. deprecated::
        This endpoint is deprecated as of Story 7.9.
        Trading mode is now determined by TRADING_MODE environment variable.
        In live mode, trades are fetched in real-time from Polymarket API.

    Returns:
        Sync result with statistics and deprecation notice
    """
    from src.trading.trade_sync import TradeSyncService

    logger.warning("💰 DEPRECATED: sync_trades endpoint called")

    service = TradeSyncService()
    result = await service.sync_trades()

    response = SyncResultResponse(
        new_trades=result.new_trades,
        updated_trades=result.updated_trades,
        consistent_trades=result.consistent_trades,
        inconsistent_trades=result.inconsistent_trades,
        total_fetched=result.total_fetched,
        last_sync_at=result.last_sync_at.isoformat(),
        error=result.error,
    )

    if result.is_success:
        logger.info(
            f"💰 Sync complete: {result.new_trades} new, "
            f"{result.updated_trades} updated"
        )
        return ApiResponse(success=True, data=response, error=None)
    else:
        logger.warning(f"💰 Sync failed: {result.error}")
        return ApiResponse(
            success=False,
            data=response,
            error=ErrorDetail(
                code=ErrorCode.TRADING_ERROR, message=result.error or "Unknown error"
            ),
        )
