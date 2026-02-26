"""Position data API routes.

This module provides REST API endpoints for position operations.

Story 7.3: 持仓与交易 API
Story 5.7: 同步实际持仓
Story 10.6: Dashboard 退出策略管理 - 手动退出持仓
Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源

Endpoints:
    GET /api/positions - Get list of open positions (with cache)
    GET /api/positions/{position_id} - Get position details
    POST /api/positions/refresh - Refresh position cache from Polymarket
    GET /api/positions/cache/status - Get cache status
    POST /api/positions/sync - (Deprecated) Sync positions from Polymarket
    GET /api/positions/sync/status - (Deprecated) Get sync status
    POST /api/positions/{position_id}/exit - Manually exit a position

Usage:
    from src.dashboard.routes.positions import router
    app.include_router(router, prefix="/api/positions", tags=["positions"])
"""

from __future__ import annotations

__all__ = ["router"]

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.config import settings
from src.models.api_response import ApiResponse, ErrorCode, ErrorDetail
from src.models.position import CacheFreshness, PositionStatus
from src.models.position_response import PositionListItem, PositionResponse
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.storage.repositories.position_repo import PositionRepository
from src.storage.repositories.trade_repo import TradeRepository

logger = logging.getLogger(__name__)

router = APIRouter()


def get_position_repository() -> PositionRepository:
    """Get PositionRepository instance.

    Returns:
        PositionRepository instance
    """
    return PositionRepository()


# ==================== Tech-Spec: 持仓缓存响应模型 ====================


class PositionListItemWithCache(PositionListItem):
    """Position list item with cache freshness info."""

    pass


class PositionListResponse(BaseModel):
    """Position list response with cache info.

    Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源

    Attributes:
        positions: List of position items with market and share info
        cache_freshness: Current cache freshness state (FRESH/STALE/EXPIRED)
        cache_age_seconds: Age of cached data in seconds (0 if no cache)
        total_count: Total number of positions returned
    """

    positions: list[PositionListItem]
    cache_freshness: CacheFreshness
    cache_age_seconds: int = 0
    total_count: int


@router.get(
    "",
    response_model=ApiResponse[PositionListResponse],
    summary="Get open positions",
    description="Retrieve a list of all open positions with cache status.",
)
async def list_positions(
    force_refresh: bool = Query(
        False,
        description=(
            "Force refresh from API. "
            "When true, bypasses TTL cache but still respects min_refresh_interval. "
            "Use sparingly to avoid API rate limiting."
        ),
    ),
) -> ApiResponse[PositionListResponse]:
    """Get list of open positions with cache.

    Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源
        - Uses PositionCacheService for data
        - Returns cache_freshness indicator
        - Cache TTL: controlled by POSITION_CACHE_TTL (default 60s)
        - Min refresh interval: controlled by POSITION_CACHE_MIN_INTERVAL (default 10s)

    Args:
        force_refresh: When True, forces API refresh (bypasses TTL, respects min_interval)

    Returns:
        List of open positions with cache status

    Example:
        >>> # GET /api/positions
        >>> # Response: {"success": true, "data": {"positions": [...], "cache_freshness": "fresh"}}
        >>> # GET /api/positions?force_refresh=true
        >>> # Forces refresh from API (use sparingly)
    """
    from src.trading.position_sync import PositionCacheService

    logger.info(f"📊 Listing open positions (force_refresh={force_refresh})")

    cache_service = PositionCacheService()
    positions, freshness = await cache_service.get_positions(force_refresh=force_refresh)

    # Get cache status for additional info
    cache_status = await cache_service.get_cache_status()

    items = [
        PositionListItem(
            id=p.id,
            market_id=p.market_id,
            outcome=p.outcome,
            shares=p.shares,
            avg_price=p.avg_price,
            current_value=p.current_value,
            pnl=p.pnl,
            status=p.status,
            opened_at=p.opened_at,
        )
        for p in positions
    ]

    response = PositionListResponse(
        positions=items,
        cache_freshness=freshness,
        cache_age_seconds=cache_status.cache_age_seconds,
        total_count=len(items),
    )

    logger.info(
        f"📊 Found {len(items)} open positions (freshness={freshness.value}, "
        f"age={cache_status.cache_age_seconds}s)"
    )
    return ApiResponse(success=True, data=response, error=None)


@router.get(
    "/{position_id}",
    response_model=ApiResponse[PositionResponse],
    summary="Get position details",
    description="Retrieve detailed information about a specific position.",
)
async def get_position(
    position_id: int,
    repo: PositionRepository = Depends(get_position_repository),
) -> ApiResponse[PositionResponse]:
    """Get position details by ID.

    Args:
        position_id: Position ID
        repo: PositionRepository dependency

    Returns:
        Position details

    Raises:
        HTTPException: If position not found (404)

    Example:
        >>> # GET /api/positions/1
        >>> # Response: {"success": true, "data": {...}}
    """
    logger.info(f"💰 Getting position: {position_id}")

    position = await repo.get_by_id(position_id)

    if position is None:
        logger.warning(f"💰 Position not found: {position_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": ErrorCode.NOT_FOUND,
                    "message": f"Position not found: {position_id}",
                },
            },
        )

    response = PositionResponse(
        id=position.id,
        market_id=position.market_id,
        outcome=position.outcome,
        shares=position.shares,
        avg_price=position.avg_price,
        initial_value=position.initial_value,
        current_value=position.current_value,
        pnl=position.pnl,
        status=position.status,
        opened_at=position.opened_at,
        closed_at=position.closed_at,
    )

    logger.info(f"💰 Retrieved position {position_id}")
    return ApiResponse(success=True, data=response, error=None)


# ==================== Tech-Spec: 持仓缓存管理 ====================


class CacheStatusResponse(BaseModel):
    """Cache status response model.

    Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源

    Attributes:
        cache_updated_at: ISO timestamp of last successful cache refresh
        cache_age_seconds: Age of cached data in seconds (0 if no cache)
        cache_freshness: Current freshness state (FRESH < TTL, STALE >= TTL, EXPIRED = no cache)
        is_refreshing: Whether a refresh operation is currently in progress
        can_refresh: Whether refresh is possible (requires API credentials in live mode)
        last_error: Last error message if refresh failed, None if successful
        total_positions: Total number of open positions in cache
    """

    cache_updated_at: str | None = None
    cache_age_seconds: int = 0
    cache_freshness: CacheFreshness
    is_refreshing: bool = False
    can_refresh: bool = False
    last_error: str | None = None
    total_positions: int = 0


class CacheRefreshResultResponse(BaseModel):
    """Cache refresh result response model.

    Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源

    Attributes:
        new_positions: Number of new positions discovered from API
        updated_positions: Number of existing positions with changed share counts
        closed_positions: Number of positions closed (not found on chain)
        unchanged_positions: Number of positions unchanged
        total_fetched: Total balances fetched from Polymarket API
        refreshed_at: ISO timestamp of this refresh operation
        error: Error message if refresh failed, None if successful
    """

    new_positions: int = 0
    updated_positions: int = 0
    closed_positions: int = 0
    unchanged_positions: int = 0
    total_fetched: int = 0
    refreshed_at: str
    error: str | None = None


# ==================== Story 5.7: 持仓同步 (Deprecated) ====================


class PositionSyncStatusResponse(BaseModel):
    """Position sync status response model.

    Deprecated: Use CacheStatusResponse instead.
    """

    last_sync_at: str | None = None
    is_syncing: bool = False
    can_sync: bool = False
    last_error: str | None = None
    total_positions: int = 0


class PositionSyncResultResponse(BaseModel):
    """Position sync result response model.

    Deprecated: Use CacheRefreshResultResponse instead.
    """

    new_positions: int = 0
    updated_positions: int = 0
    closed_positions: int = 0
    unchanged_positions: int = 0
    total_fetched: int = 0
    last_sync_at: str
    error: str | None = None


# ==================== New Cache Endpoints ====================


@router.get(
    "/cache/status",
    response_model=ApiResponse[CacheStatusResponse],
    summary="Get position cache status",
    description="Get the current position cache status with freshness indicator.",
)
async def get_cache_status() -> ApiResponse[CacheStatusResponse]:
    """Get current position cache status.

    Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源

    Returns:
        Cache status information with freshness indicator
    """
    from src.trading.position_sync import PositionCacheService

    logger.info("📊 Getting position cache status")

    service = PositionCacheService()
    status = await service.get_cache_status()

    response = CacheStatusResponse(
        cache_updated_at=status.cache_updated_at.isoformat()
        if status.cache_updated_at
        else None,
        cache_age_seconds=status.cache_age_seconds,
        cache_freshness=status.cache_freshness,
        is_refreshing=status.is_refreshing,
        can_refresh=status.can_refresh,
        last_error=status.last_error,
        total_positions=status.total_positions,
    )

    return ApiResponse(success=True, data=response, error=None)


@router.post(
    "/refresh",
    response_model=ApiResponse[CacheRefreshResultResponse],
    summary="Refresh position cache",
    description="Refresh position cache from Polymarket API.",
)
async def refresh_cache() -> ApiResponse[CacheRefreshResultResponse]:
    """Refresh position cache from Polymarket API.

    Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源

    Fetches position balances from Polymarket and updates the local cache.
    Requires API credentials to be configured.

    Returns:
        Refresh result with statistics
    """
    from src.trading.position_sync import PositionCacheService

    logger.info("📊 Starting position cache refresh")

    service = PositionCacheService()
    result = await service.refresh_cache()

    response = CacheRefreshResultResponse(
        new_positions=result.new_positions,
        updated_positions=result.updated_positions,
        closed_positions=result.closed_positions,
        unchanged_positions=result.unchanged_positions,
        total_fetched=result.total_fetched,
        refreshed_at=result.refreshed_at.isoformat(),
        error=result.error,
    )

    if result.is_success:
        logger.info(
            f"📊 Cache refresh complete: {result.new_positions} new, "
            f"{result.updated_positions} updated, {result.closed_positions} closed"
        )
        return ApiResponse(success=True, data=response, error=None)
    else:
        logger.warning(f"📊 Cache refresh failed: {result.error}")
        return ApiResponse(
            success=False,
            data=response,
            error=ErrorDetail(
                code=ErrorCode.TRADING_ERROR, message=result.error or "Unknown error"
            ),
        )


# ==================== Deprecated Sync Endpoints ====================


@router.get(
    "/sync/status",
    response_model=ApiResponse[PositionSyncStatusResponse],
    summary="[DEPRECATED] Get position sync status",
    description="DEPRECATED: Use /api/positions/cache/status instead.",
    deprecated=True,
)
async def get_position_sync_status() -> ApiResponse[PositionSyncStatusResponse]:
    """Get current position sync status.

    Deprecated: Use get_cache_status instead.

    Returns:
        Sync status information
    """
    from src.trading.position_sync import PositionCacheService

    logger.warning(
        "⚠️ DEPRECATED: /sync/status endpoint is deprecated. Use /cache/status instead."
    )

    service = PositionCacheService()
    status = await service.get_cache_status()

    response = PositionSyncStatusResponse(
        last_sync_at=status.cache_updated_at.isoformat()
        if status.cache_updated_at
        else None,
        is_syncing=status.is_refreshing,
        can_sync=status.can_refresh,
        last_error=status.last_error,
        total_positions=status.total_positions,
    )

    return ApiResponse(success=True, data=response, error=None)


@router.post(
    "/sync",
    response_model=ApiResponse[PositionSyncResultResponse],
    summary="[DEPRECATED] Sync positions from Polymarket",
    description="DEPRECATED: Use POST /api/positions/refresh instead.",
    deprecated=True,
)
async def sync_positions() -> ApiResponse[PositionSyncResultResponse]:
    """Sync positions from Polymarket API.

    Deprecated: Use refresh_cache instead.

    Returns:
        Sync result with statistics
    """
    from src.trading.position_sync import PositionCacheService

    logger.warning(
        "⚠️ DEPRECATED: /sync endpoint is deprecated. Use /refresh instead."
    )

    service = PositionCacheService()
    result = await service.refresh_cache()

    response = PositionSyncResultResponse(
        new_positions=result.new_positions,
        updated_positions=result.updated_positions,
        closed_positions=result.closed_positions,
        unchanged_positions=result.unchanged_positions,
        total_fetched=result.total_fetched,
        last_sync_at=result.refreshed_at.isoformat(),
        error=result.error,
    )

    if result.is_success:
        logger.info(
            f"📊 Sync complete: {result.new_positions} new, "
            f"{result.updated_positions} updated, {result.closed_positions} closed"
        )
        return ApiResponse(success=True, data=response, error=None)
    else:
        logger.warning(f"📊 Sync failed: {result.error}")
        return ApiResponse(
            success=False,
            data=response,
            error=ErrorDetail(
                code=ErrorCode.TRADING_ERROR, message=result.error or "Unknown error"
            ),
        )


# ==================== Story 10.6: 手动退出持仓 ====================


class ManualExitResponse(BaseModel):
    """Manual exit response model.

    Attributes:
        success: Whether the exit was successful
        position_id: ID of the position
        market_id: Market ID
        shares_sold: Number of shares sold
        avg_price: Average price at which shares were sold
        total_value: Total value of the sale
        realized_pnl: Realized profit/loss (optional)
        exit_type: Type of exit (always "manual" for this endpoint)
    """

    success: bool
    position_id: int
    market_id: str
    shares_sold: float
    avg_price: float
    total_value: float
    realized_pnl: float | None = None
    exit_type: str = "manual"


def get_trade_repository() -> TradeRepository:
    """Get TradeRepository instance.

    Returns:
        TradeRepository instance
    """
    return TradeRepository()


@router.post(
    "/{position_id}/exit",
    response_model=ApiResponse[ManualExitResponse],
    summary="Manually exit a position",
    description="Sell all shares of a position at current market price. This is a simplified paper trading exit - for live trading, use the trading bot directly.",
)
async def manual_exit_position(
    position_id: int,
    position_repo: PositionRepository = Depends(get_position_repository),
    trade_repo: TradeRepository = Depends(get_trade_repository),
) -> ApiResponse[ManualExitResponse]:
    """Manually exit a position.

    Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源
        - Marks cache as stale after exit

    This endpoint provides a simplified manual exit for paper trading mode.
    It marks the position as closed and creates a sell trade record.

    For live trading, the actual order execution should be handled by
    the trading bot using LiveTradingExecutor.

    Args:
        position_id: Position ID to exit
        position_repo: PositionRepository dependency
        trade_repo: TradeRepository dependency

    Returns:
        Exit result with sale details

    Raises:
        HTTPException: If position not found (404) or not open (400)

    Example:
        >>> # POST /api/positions/1/exit
        >>> # Response: {"success": true, "data": {...}}
    """
    logger.info(f"💰 Manual exit requested for position {position_id}")

    # Get position
    position = await position_repo.get_by_id(position_id)
    if position is None:
        logger.warning(f"💰 Position not found: {position_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": ErrorCode.NOT_FOUND,
                    "message": f"Position not found: {position_id}",
                },
            },
        )

    # Check position status
    if position.status != PositionStatus.OPEN:
        logger.warning(
            f"💰 Position {position_id} is not open (status: {position.status})"
        )
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {
                    "code": ErrorCode.VALIDATION_ERROR,
                    "message": f"Position {position_id} is not open (status: {position.status.value})",
                },
            },
        )

    try:
        # Calculate exit values
        # Use current_value if available, otherwise use avg_price * shares
        exit_price = position.avg_price  # Simplified: use avg_price as exit price
        if position.current_value is not None and position.shares > 0:
            exit_price = position.current_value / position.shares

        total_value = position.shares * exit_price

        # Calculate realized PnL
        realized_pnl = None
        if position.initial_value is not None:
            realized_pnl = total_value - position.initial_value

        # Determine trade type based on position outcome
        from src.models.position import PositionOutcome

        if position.outcome == PositionOutcome.YES:
            trade_type = TradeType.SELL_YES
        else:
            trade_type = TradeType.SELL_NO

        # Create sell trade record
        trade = Trade(
            id=0,
            market_id=position.market_id,
            trade_type=trade_type,
            mode=TradeMode.PAPER,  # Manual exit via dashboard is always paper mode
            amount=total_value,
            price=exit_price,
            shares=position.shares,
            status=TradeStatus.FILLED,
            position_id=position.id,
            exit_type="manual",  # Story 10.6: Mark as manual exit
        )
        saved_trade = await trade_repo.save(trade)
        logger.info(f"💰 Created sell trade: id={saved_trade.id}")

        # Update position status to closed
        position.status = PositionStatus.CLOSED
        position.closed_at = datetime.now(timezone.utc)
        position.current_value = total_value
        position.pnl = realized_pnl if realized_pnl is not None else position.pnl
        updated_position = await position_repo.update(position)
        logger.info(f"💰 Position {position_id} marked as closed")

        # Mark cache as stale (Tech-Spec: Single Source of Truth)
        from src.trading.position_sync import PositionCacheService

        cache_service = PositionCacheService()
        await cache_service.mark_stale()
        logger.debug(f"📊 Cache marked as stale after manual exit")

        # Build response
        response = ManualExitResponse(
            success=True,
            position_id=position_id,
            market_id=position.market_id,
            shares_sold=position.shares,
            avg_price=exit_price,
            total_value=total_value,
            realized_pnl=realized_pnl,
            exit_type="manual",
        )

        logger.info(
            f"💰 Manual exit successful for position {position_id}: "
            f"shares={position.shares:.2f}, value=${total_value:.2f}, "
            f"pnl=${realized_pnl:.2f}"
            if realized_pnl is not None
            else ""
        )

        return ApiResponse(success=True, data=response, error=None)

    except Exception as e:
        logger.error(f"💰 Manual exit error for position {position_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": str(e),
                },
            },
        )
