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
from src.api.polymarket import PolymarketClient
from src.trading.live_trading import LiveTradingExecutor
from src.trading.position_manager import PositionManager
from src.core.state import ThreadSafeState

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
            cur_price=p.cur_price,
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


# ==================== Cache Endpoints ====================


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
    "/cache/reset",
    response_model=ApiResponse[dict],
    summary="Reset stuck cache refresh state",
    description="Reset the refreshing flag and lock if a refresh operation is stuck.",
)
async def reset_cache_state() -> ApiResponse[dict]:
    """Reset stuck cache refresh state.

    Use this endpoint if a refresh operation is stuck (is_refreshing stays true).
    This can happen if the server was restarted during a refresh or due to an error.

    Returns:
        Success message
    """
    import asyncio
    from src.trading.position_sync import PositionCacheService

    logger.warning("📊 Resetting stuck cache refresh state")

    service = PositionCacheService()
    was_stuck = service._refreshing or service._refresh_lock.locked()

    # Reset both the flag and the lock
    service._refreshing = False
    if service._refresh_lock.locked():
        # Create a new lock to replace the stuck one
        service._refresh_lock = asyncio.Lock()

    if was_stuck:
        logger.info("📊 Cache refresh state reset successfully")
        return ApiResponse(
            success=True,
            data={"message": "Cache refresh state reset successfully"},
            error=None,
        )
    else:
        return ApiResponse(
            success=True,
            data={"message": "No stuck refresh state found"},
            error=None,
        )


@router.get(
    "/debug/trades",
    response_model=ApiResponse[dict],
    summary="[DEBUG] Get trades from Polymarket API",
    description="Debug endpoint to check what trades the Polymarket API returns.",
)
async def debug_get_trades() -> ApiResponse[dict]:
    """Debug endpoint to check Polymarket API trades.

    Returns:
        Trade information from Polymarket API
    """
    from src.api.polymarket import PolymarketClient
    from src.config import settings

    logger.info("📊 Debug: Fetching trades from Polymarket API")

    result = {
        "pk_configured": bool(settings.polymarket.pk),
        "proxy_wallet": settings.polymarket.proxy_wallet,
        "trades_count": 0,
        "trades_sample": [],
        "error": None,
    }

    try:
        client = PolymarketClient()
        trades = client._client.get_trades()
        result["trades_count"] = len(trades) if trades else 0

        if trades:
            for t in trades[:5]:
                result["trades_sample"].append({
                    "asset_id": str(t.get("asset_id", ""))[:30] + "...",
                    "outcome": t.get("outcome", ""),
                    "side": t.get("side", ""),
                    "size": t.get("size", 0),
                    "price": t.get("price", 0),
                    "market": str(t.get("market", ""))[:30] + "..." if t.get("market") else None,
                })

        client.close()
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"📊 Debug: Error fetching trades: {e}")

    return ApiResponse(success=True, data=result, error=None)


@router.get(
    "/debug/full-trades",
    response_model=ApiResponse[dict],
    summary="[DEBUG] Get full trades data with complete asset IDs",
    description="Debug endpoint to see complete trade information.",
)
async def debug_full_trades() -> ApiResponse[dict]:
    """Debug endpoint to get full trades data with complete asset IDs."""
    from src.api.polymarket import PolymarketClient
    from src.config import settings

    logger.info("📊 Debug: Fetching full trades data")

    result = {
        "wallet": settings.polymarket.proxy_wallet,
        "trades": [],
        "markets": {},
        "error": None,
    }

    try:
        client = PolymarketClient()
        trades = client._client.get_trades()

        if trades:
            # Get unique asset IDs and markets
            asset_ids = set()
            market_ids = set()
            for t in trades:
                if t.get("asset_id"):
                    asset_ids.add(str(t["asset_id"]))
                if t.get("market"):
                    market_ids.add(str(t["market"]))

            # Store full trades (first 10)
            for t in trades[:10]:
                result["trades"].append({
                    "asset_id": str(t.get("asset_id", "")),
                    "market": str(t.get("market", "")),
                    "outcome": t.get("outcome", ""),
                    "side": t.get("side", ""),
                    "size": t.get("size", ""),
                    "price": t.get("price", ""),
                })

            # Get market data for token IDs
            for market_id in list(market_ids)[:5]:
                try:
                    market_data = client._client.get_market(market_id)
                    if market_data:
                        tokens = market_data.get("tokens", [])
                        result["markets"][market_id] = {
                            "tokens": [
                                {
                                    "token_id": str(t.get("token_id", "")),
                                    "outcome": t.get("outcome", ""),
                                }
                                for t in tokens
                            ]
                        }
                except Exception as e:
                    result["markets"][market_id] = {"error": str(e)}

            result["unique_assets"] = len(asset_ids)
            result["unique_markets"] = len(market_ids)

        client.close()
    except Exception as e:
        result["error"] = str(e)

    return ApiResponse(success=True, data=result, error=None)


@router.get(
    "/debug/balance/{asset_id}",
    response_model=ApiResponse[dict],
    summary="[DEBUG] Get on-chain balance for an asset",
    description="Debug endpoint to check on-chain ERC-1155 balance.",
)
async def debug_get_balance(asset_id: str) -> ApiResponse[dict]:
    """Debug endpoint to check on-chain balance.

    Args:
        asset_id: Token/asset ID to query

    Returns:
        On-chain balance information
    """
    from src.api.polymarket import PolymarketClient
    from src.config import settings

    logger.info(f"📊 Debug: Fetching on-chain balance for asset {asset_id[:20]}...")

    result = {
        "asset_id": asset_id,
        "wallet": settings.polymarket.proxy_wallet,
        "balance": 0,
        "error": None,
    }

    try:
        client = PolymarketClient()
        balance = client._get_erc1155_balance(settings.polymarket.proxy_wallet, asset_id)
        result["balance"] = balance
        client.close()
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"📊 Debug: Error fetching balance: {e}")

    return ApiResponse(success=True, data=result, error=None)


@router.get(
    "/debug/contracts/{asset_id}",
    response_model=ApiResponse[dict],
    summary="[DEBUG] Check balance across all Polymarket contracts",
    description="Debug endpoint to check balance in different CTF contracts.",
)
async def debug_check_contracts(asset_id: str) -> ApiResponse[dict]:
    """Debug endpoint to check balance in different Polymarket contracts.

    Args:
        asset_id: Token/asset ID to query

    Returns:
        Balance information from different contracts
    """
    from web3 import Web3
    from src.config import settings

    logger.info(f"📊 Debug: Checking balance across contracts for asset {asset_id[:20]}...")

    # Polymarket contracts on Polygon
    CONTRACTS = {
        "CTF (Standard)": "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045",
        "Neg Risk CTF": "0xC5d563A36AE78145C45a50134d48A1215220f80a",
        "CTF Exchange": "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8ba2E",
        "Neg Risk Adapter": "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296",
    }

    POLYGON_RPCS = [
        "https://polygon-mainnet.g.alchemy.com/v2/ppWb_ez8qZohBDRTqZnX5lEMYtc-5iI6",
        "https://rpc.ankr.com/polygon",
        "https://polygon-bor-rpc.publicnode.com",
    ]

    ctf_abi = """[{
        "inputs": [
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "uint256", "name": "id", "type": "uint256"}
        ],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }]"""

    wallet = settings.polymarket.proxy_wallet
    results = {
        "asset_id": asset_id,
        "wallet": wallet,
        "balances": {},
        "errors": [],
    }

    for rpc_url in POLYGON_RPCS:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
            if not w3.is_connected():
                continue

            for name, address in CONTRACTS.items():
                try:
                    contract = w3.eth.contract(
                        address=Web3.to_checksum_address(address),
                        abi=ctf_abi,
                    )
                    balance_wei = contract.functions.balanceOf(
                        Web3.to_checksum_address(wallet),
                        int(asset_id),
                    ).call()
                    balance = balance_wei / 10**18
                    if balance > 0:
                        results["balances"][name] = {
                            "address": address,
                            "balance": balance,
                            "rpc": rpc_url.split("/")[2],
                        }
                except Exception as e:
                    pass  # Skip errors for individual contracts

            if results["balances"]:
                break  # Found balances, no need to try other RPCs

        except Exception as e:
            results["errors"].append(f"{rpc_url}: {str(e)}")

    return ApiResponse(success=True, data=results, error=None)


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
    description="Sell all shares of a position at current market price. In LIVE mode, executes real trade on Polymarket. In PAPER mode, simulates the exit.",
)
async def manual_exit_position(
    position_id: int,
    position_repo: PositionRepository = Depends(get_position_repository),
    trade_repo: TradeRepository = Depends(get_trade_repository),
) -> ApiResponse[ManualExitResponse]:
    """Manually exit a position.

    Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源
        - Marks cache as stale after exit

    Story 10.6: Dashboard 退出支持 Live Trading
        - In LIVE mode: executes real sell order on Polymarket
        - In PAPER mode: simulates exit in local database

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

    # Check trading mode
    is_live_mode = settings.trading_mode == "live"
    logger.info(f"💰 Trading mode: {'LIVE' if is_live_mode else 'PAPER'}")

    try:
        if is_live_mode:
            # ========== LIVE TRADING: Execute real sell on Polymarket ==========
            logger.info(f"💰 Executing LIVE sell for position {position_id}")

            # Get market data
            from src.storage.repositories.market_repo import MarketRepository

            market_repo = MarketRepository()
            market = await market_repo.get_market(position.market_id)

            if market is None:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "success": False,
                        "error": {
                            "code": ErrorCode.NOT_FOUND,
                            "message": f"Market not found: {position.market_id}",
                        },
                    },
                )

            # Initialize live trading executor
            from src.api.polymarket import PolymarketClient
            from src.trading.live_trading import LiveTradingExecutor
            from src.trading.position_manager import PositionManager
            from src.core.state import ThreadSafeState

            client = PolymarketClient()
            state = ThreadSafeState.get_instance()
            position_manager = PositionManager()

            executor = LiveTradingExecutor(
                client=client,
                trade_repo=trade_repo,
                position_manager=position_manager,
                state=state,
            )

            # Execute sell
            result = await executor.sell_position(
                position=position,
                market=market,
                reason="manual",
            )

            client.close()

            if not result.success:
                logger.error(f"💰 Live sell failed: {result.error_message}")
                raise HTTPException(
                    status_code=500,
                    detail={
                        "success": False,
                        "error": {
                            "code": ErrorCode.TRADING_ERROR,
                            "message": result.error_message or "Live sell failed",
                        },
                    },
                )

            # Build response from live result
            response = ManualExitResponse(
                success=True,
                position_id=position_id,
                market_id=position.market_id,
                shares_sold=position.shares,
                avg_price=result.trade.price if result.trade else position.avg_price,
                total_value=result.trade.amount if result.trade else 0,
                realized_pnl=result.realized_pnl,
                exit_type="manual",  # Live sell
            )

            logger.info(
                f"💰 Live sell successful for position {position_id}: "
                f"shares={position.shares:.2f}, pnl=${result.realized_pnl:.2f}"
            )

        else:
            # ========== PAPER TRADING: Simulate exit in database ==========
            logger.info(f"💰 Executing PAPER sell for position {position_id}")

            # Calculate exit values
            exit_price = position.avg_price
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
                mode=TradeMode.PAPER,
                amount=total_value,
                price=exit_price,
                shares=position.shares,
                status=TradeStatus.FILLED,
                position_id=position.id,
                exit_type="manual",
            )
            saved_trade = await trade_repo.save(trade)
            logger.info(f"💰 Created paper sell trade: id={saved_trade.id}")

            # Update position status to closed
            position.status = PositionStatus.CLOSED
            position.closed_at = datetime.now(timezone.utc)
            position.current_value = total_value
            position.pnl = realized_pnl if realized_pnl is not None else position.pnl
            await position_repo.update(position)
            logger.info(f"💰 Position {position_id} marked as closed (paper)")

            # Build response
            response = ManualExitResponse(
                success=True,
                position_id=position_id,
                market_id=position.market_id,
                shares_sold=position.shares,
                avg_price=exit_price,
                total_value=total_value,
                realized_pnl=realized_pnl,
                exit_type="manual",  # Paper sell
            )

            logger.info(
                f"💰 Paper sell successful for position {position_id}: "
                f"shares={position.shares:.2f}, value=${total_value:.2f}, "
                f"pnl=${realized_pnl:.2f}"
                if realized_pnl is not None
                else ""
            )

        # Mark cache as stale (Tech-Spec: Single Source of Truth)
        from src.trading.position_sync import PositionCacheService

        cache_service = PositionCacheService()
        await cache_service.mark_stale()
        logger.debug(f"📊 Cache marked as stale after manual exit")

        return ApiResponse(success=True, data=response, error=None)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
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
