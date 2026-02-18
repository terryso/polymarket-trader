"""Position data API routes.

This module provides REST API endpoints for position operations.

Story 7.3: 持仓与交易 API
Story 5.7: 同步实际持仓

Endpoints:
    GET /api/positions - Get list of open positions
    GET /api/positions/{position_id} - Get position details
    POST /api/positions/sync - Sync positions from Polymarket
    GET /api/positions/sync/status - Get sync status

Usage:
    from src.dashboard.routes.positions import router
    app.include_router(router, prefix="/api/positions", tags=["positions"])
"""

from __future__ import annotations

__all__ = ["router"]

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.models.api_response import ApiResponse, ErrorDetail, ErrorCode
from src.models.position_response import PositionListItem, PositionResponse
from src.storage.repositories.position_repo import PositionRepository

logger = logging.getLogger(__name__)

router = APIRouter()


def get_position_repository() -> PositionRepository:
    """Get PositionRepository instance.

    Returns:
        PositionRepository instance
    """
    return PositionRepository()


@router.get(
    "",
    response_model=ApiResponse[list[PositionListItem]],
    summary="Get open positions",
    description="Retrieve a list of all open positions.",
)
async def list_positions(
    repo: PositionRepository = Depends(get_position_repository),
) -> ApiResponse[list[PositionListItem]]:
    """Get list of open positions.

    Args:
        repo: PositionRepository dependency

    Returns:
        List of open positions

    Example:
        >>> # GET /api/positions
        >>> # Response: {"success": true, "data": [...]}
    """
    logger.info("💰 Listing open positions")

    positions = await repo.get_open_positions()

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

    logger.info(f"💰 Found {len(items)} open positions")
    return ApiResponse(success=True, data=items, error=None)


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


# ==================== Story 5.7: 持仓同步 ====================


class PositionSyncStatusResponse(BaseModel):
    """Position sync status response model."""

    last_sync_at: str | None = None
    is_syncing: bool = False
    can_sync: bool = False
    last_error: str | None = None
    total_positions: int = 0


class PositionSyncResultResponse(BaseModel):
    """Position sync result response model."""

    new_positions: int = 0
    updated_positions: int = 0
    closed_positions: int = 0
    unchanged_positions: int = 0
    total_fetched: int = 0
    last_sync_at: str
    error: str | None = None


@router.get(
    "/sync/status",
    response_model=ApiResponse[PositionSyncStatusResponse],
    summary="Get position sync status",
    description="Get the current position sync status.",
)
async def get_position_sync_status() -> ApiResponse[PositionSyncStatusResponse]:
    """Get current position sync status.

    Returns information about the last sync and whether sync is available.

    Returns:
        Sync status information
    """
    from src.trading.position_sync import PositionSyncService

    logger.info("💰 Getting position sync status")

    service = PositionSyncService()
    status = await service.get_sync_status()

    response = PositionSyncStatusResponse(
        last_sync_at=status.last_sync_at.isoformat() if status.last_sync_at else None,
        is_syncing=status.is_syncing,
        can_sync=status.can_sync,
        last_error=status.last_error,
        total_positions=status.total_positions,
    )

    return ApiResponse(success=True, data=response, error=None)


@router.post(
    "/sync",
    response_model=ApiResponse[PositionSyncResultResponse],
    summary="Sync positions from Polymarket",
    description="Synchronize wallet positions from Polymarket API to local database.",
)
async def sync_positions() -> ApiResponse[PositionSyncResultResponse]:
    """Sync positions from Polymarket API.

    Fetches position balances from Polymarket and syncs with local database.
    Requires API credentials to be configured.

    Returns:
        Sync result with statistics
    """
    from src.trading.position_sync import PositionSyncService

    logger.info("💰 Starting position sync")

    service = PositionSyncService()
    result = await service.sync_positions()

    response = PositionSyncResultResponse(
        new_positions=result.new_positions,
        updated_positions=result.updated_positions,
        closed_positions=result.closed_positions,
        unchanged_positions=result.unchanged_positions,
        total_fetched=result.total_fetched,
        last_sync_at=result.last_sync_at.isoformat(),
        error=result.error,
    )

    if result.is_success:
        logger.info(
            f"💰 Sync complete: {result.new_positions} new, "
            f"{result.updated_positions} updated, {result.closed_positions} closed"
        )
        return ApiResponse(success=True, data=response, error=None)
    else:
        logger.warning(f"💰 Sync failed: {result.error}")
        return ApiResponse(
            success=False,
            data=response,
            error=ErrorDetail(code=ErrorCode.TRADING_ERROR, message=result.error or "Unknown error"),
        )
