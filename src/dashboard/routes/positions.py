"""Position data API routes.

This module provides REST API endpoints for position operations.

Story 7.3: 持仓与交易 API

Endpoints:
    GET /api/positions - Get list of open positions
    GET /api/positions/{position_id} - Get position details

Usage:
    from src.dashboard.routes.positions import router
    app.include_router(router, prefix="/api/positions", tags=["positions"])
"""

from __future__ import annotations

__all__ = ["router"]

import logging
from fastapi import APIRouter, Depends, HTTPException

from src.models.api_response import ApiResponse, ErrorCode
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
