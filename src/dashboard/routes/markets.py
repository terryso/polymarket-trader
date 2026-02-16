"""Market data API routes.

This module provides REST API endpoints for market data operations,
including list and detail endpoints with pagination and filtering.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from src.models.api_response import (
    ApiResponse,
    ErrorCode,
    PaginatedResponse,
    PaginationMeta,
)
from src.models.market import MarketCategory
from src.models.market_response import MarketListItem, MarketListQueryParams, MarketResponse
from src.storage.repositories.market_repo import MarketRepository

logger = logging.getLogger(__name__)

router = APIRouter()


def get_market_repository() -> MarketRepository:
    """Get MarketRepository instance.

    Factory function for dependency injection of MarketRepository.

    Returns:
        MarketRepository instance
    """
    return MarketRepository()


@router.get("", response_model=PaginatedResponse[MarketListItem])
async def list_markets(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
    status: str = Query(default="all", description="Status filter (active/resolved/all)"),
    category: MarketCategory | None = Query(default=None, description="Category filter"),
    repo: MarketRepository = Depends(get_market_repository),
) -> PaginatedResponse[MarketListItem]:
    """Get market list with pagination and filtering.

    Returns a paginated list of markets with optional filtering by
    status (active/resolved/all) and category.

    Uses MarketListQueryParams for parameter validation and leverages
    database-level filtering via get_markets_by_category for better
    performance when category filter is specified.

    Args:
        page: Page number (1-based indexing)
        per_page: Items per page (max 100)
        status: Status filter - "active" for unresolved markets,
            "resolved" for resolved markets, "all" for all markets
        category: Category filter - one of politics, business,
            technology, economics, crypto
        repo: MarketRepository dependency

    Returns:
        PaginatedResponse containing list of MarketListItem and pagination metadata

    Example:
        GET /api/markets?page=1&per_page=20&status=active&category=politics
    """
    # Use MarketListQueryParams for validation (ensures consistency with model)
    params = MarketListQueryParams(page=page, per_page=per_page, status=status, category=category)

    logger.info(
        f"📊 Listing markets: page={params.page}, per_page={params.per_page}, "
        f"status={params.status}, category={params.category}"
    )

    # Get markets with efficient database-level filtering
    # When category is specified with status="all", use get_markets_by_category
    # for database-level filtering instead of in-memory filtering
    if params.category is not None and params.status == "all":
        # Database-level filtering for category when status is "all"
        markets = await repo.get_markets_by_category(params.category)
    elif params.status == "active":
        markets = await repo.get_active_markets()
        # Apply category filter in-memory only when combined with status filter
        # (repository doesn't have get_active_markets_by_category method)
        if params.category is not None:
            markets = [m for m in markets if m.category == params.category]
    elif params.status == "resolved":
        markets = await repo.get_resolved_markets()
        # Apply category filter in-memory only when combined with status filter
        if params.category is not None:
            markets = [m for m in markets if m.category == params.category]
    else:
        markets = await repo.get_all_markets()

    # Calculate pagination
    total = len(markets)
    start = (params.page - 1) * params.per_page
    end = start + params.per_page
    paginated_markets = markets[start:end]

    # Convert to response models
    items = [
        MarketListItem(
            id=m.id,
            title=m.title,
            category=m.category,
            yes_price=m.yes_price,
            no_price=m.no_price,
            liquidity=m.liquidity,
            deadline=m.deadline,
            resolution_status=m.resolution_status,
        )
        for m in paginated_markets
    ]

    logger.info(f"📊 Returning {len(items)} markets (total: {total})")

    return PaginatedResponse(
        success=True,
        data=items,
        meta=PaginationMeta(total=total, page=params.page, per_page=params.per_page),
    )


@router.get("/{market_id}", response_model=ApiResponse[MarketResponse])
async def get_market(
    market_id: str,
    repo: MarketRepository = Depends(get_market_repository),
) -> ApiResponse[MarketResponse]:
    """Get market details by ID.

    Returns full market details including description, resolution outcome,
    and timestamps.

    Args:
        market_id: Market unique identifier
        repo: MarketRepository dependency

    Returns:
        ApiResponse containing MarketResponse with full market details

    Raises:
        HTTPException: 404 if market not found

    Example:
        GET /api/markets/market-123
    """
    logger.info(f"📊 Getting market: {market_id}")

    market = await repo.get_market(market_id)

    if market is None:
        logger.warning(f"📊 Market not found: {market_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": ErrorCode.NOT_FOUND,
                    "message": f"Market not found: {market_id}",
                },
            },
        )

    response = MarketResponse(
        id=market.id,
        title=market.title,
        description=market.description,
        category=market.category,
        yes_price=market.yes_price,
        no_price=market.no_price,
        liquidity=market.liquidity,
        deadline=market.deadline,
        resolution_status=market.resolution_status,
        resolution_outcome=market.resolution_outcome,
        created_at=market.created_at,
        updated_at=market.updated_at,
    )

    logger.info(f"📊 Returning market: {market_id}")

    return ApiResponse(success=True, data=response, error=None)


__all__ = ["router"]
