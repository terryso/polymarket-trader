"""Statistics API routes.

This module provides REST API endpoints for statistics operations.

Story 7.4: 预测与统计 API
Story 7.5: 系统状态 API
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.config import settings
from src.core.state import ThreadSafeState, get_state_manager
from src.models.api_response import ApiResponse, PaginatedResponse, PaginationMeta
from src.models.statistics_response import (
    CapitalHistoryPoint,
    DailyStatsItem,
    OverviewStats,
    PerformanceData,
    TradesByDayPoint,
    WinRateHistoryPoint,
)
from src.models.system_status import SanitizedSettings, SystemStatus
from src.models.trade import TradeMode, TradeStatus
from src.api.polymarket import PolymarketClient
from src.storage.database import get_connection
from src.storage.repositories.position_repo import PositionRepository
from src.storage.repositories.statistics_repo import StatisticsRepository
from src.storage.repositories.trade_repo import TradeRepository

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level variable for tracking application start time
_app_start_time: float = time.time()


def get_statistics_repository() -> StatisticsRepository:
    """Get StatisticsRepository instance.

    Returns:
        StatisticsRepository instance
    """
    return StatisticsRepository()


def get_trade_repository() -> TradeRepository:
    """Get TradeRepository instance.

    Returns:
        TradeRepository instance
    """
    return TradeRepository()


def get_position_repository() -> PositionRepository:
    """Get PositionRepository instance.

    Returns:
        PositionRepository instance
    """
    return PositionRepository()


def get_state() -> ThreadSafeState:
    """Get ThreadSafeState singleton instance.

    Returns the singleton ThreadSafeState instance for accessing
    and managing trading state (capital, PnL, positions, etc.).

    Returns:
        ThreadSafeState: The singleton state manager instance
    """
    return get_state_manager()


@router.get("/overview", response_model=ApiResponse[OverviewStats])
async def get_overview(
    stats_repo: StatisticsRepository = Depends(get_statistics_repository),
    trade_repo: TradeRepository = Depends(get_trade_repository),
    position_repo: PositionRepository = Depends(get_position_repository),
    state: ThreadSafeState = Depends(get_state),
) -> ApiResponse[OverviewStats]:
    """Get system overview statistics.

    Aggregates data from multiple sources for dashboard overview.

    Args:
        stats_repo: StatisticsRepository dependency
        trade_repo: TradeRepository dependency
        position_repo: PositionRepository dependency
        state: ThreadSafeState dependency

    Returns:
        System overview statistics
    """
    logger.info("📊 Getting system overview statistics")

    # Get current state
    state_snapshot = await state.get_state()

    # Get all trades for statistics
    all_trades = await trade_repo.get_recent(limit=10000)
    total_trades = len(all_trades)

    # Calculate win/loss counts
    # Note: This is simplified - in production, you'd calculate from trade results
    winning_trades = sum(
        1 for t in all_trades if t.status == TradeStatus.FILLED
    )  # Placeholder
    losing_trades = total_trades - winning_trades
    win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

    # Get open positions count
    open_positions = await position_repo.get_open_positions()
    open_positions_count = len(open_positions)

    # Calculate P&L
    initial_capital = settings.initial_capital
    current_capital = state_snapshot.current_capital
    total_pnl = current_capital - initial_capital
    total_pnl_pct = total_pnl / initial_capital if initial_capital > 0 else 0.0

    # Fetch real wallet balance from Polymarket
    wallet_balance: float | None = None
    wallet_balance_error: str | None = None
    try:
        client = PolymarketClient()
        balance_result = client.get_wallet_balance()
        if balance_result.is_success:
            wallet_balance = balance_result.usdc_balance
        else:
            wallet_balance_error = balance_result.error
    except Exception as e:
        logger.warning(f"Failed to fetch wallet balance: {e}")
        wallet_balance_error = str(e)

    overview = OverviewStats(
        current_capital=current_capital,
        initial_capital=initial_capital,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        win_rate=win_rate,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        open_positions=open_positions_count,
        trading_enabled=state_snapshot.trading_enabled,
        mode=settings.trading_mode.upper(),
        wallet_balance=wallet_balance,
        wallet_balance_error=wallet_balance_error,
    )

    return ApiResponse(success=True, data=overview, error=None)


@router.get("/daily", response_model=PaginatedResponse[DailyStatsItem])
async def get_daily_stats(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    repo: StatisticsRepository = Depends(get_statistics_repository),
) -> PaginatedResponse[DailyStatsItem]:
    """Get daily statistics with pagination.

    Args:
        page: Page number (1-based)
        per_page: Items per page (max 100)
        repo: StatisticsRepository dependency

    Returns:
        Paginated daily statistics
    """
    logger.info(f"📊 Getting daily statistics: page={page}, per_page={per_page}")

    # Get all daily stats
    all_stats = await repo.get_all(limit=1000)

    # Sort by date descending
    all_stats.sort(key=lambda s: s.date, reverse=True)

    # Calculate pagination
    total = len(all_stats)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_stats = all_stats[start:end]

    # Convert to response models
    items = [
        DailyStatsItem(
            date=s.date,
            starting_capital=s.starting_capital,
            ending_capital=s.ending_capital,
            total_pnl=s.total_pnl,
            total_trades=s.total_trades,
            winning_trades=s.winning_trades,
            losing_trades=s.losing_trades,
            win_rate=s.win_rate,
        )
        for s in paginated_stats
    ]

    return PaginatedResponse(
        success=True,
        data=items,
        meta=PaginationMeta(total=total, page=page, per_page=per_page),
    )


@router.get("/performance", response_model=ApiResponse[PerformanceData])
async def get_performance(
    days: Annotated[int, Query(ge=1, le=365, description="Number of days")] = 30,
    repo: StatisticsRepository = Depends(get_statistics_repository),
) -> ApiResponse[PerformanceData]:
    """Get performance data for charts.

    Args:
        days: Number of days to include
        repo: StatisticsRepository dependency

    Returns:
        Performance data for visualizations
    """
    logger.info(f"📊 Getting performance data: days={days}")

    # Get date range
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Get stats for date range
    stats = await repo.get_by_date_range(start_date, end_date, TradeMode.PAPER)

    # Build time series data
    capital_history: list[CapitalHistoryPoint] = []
    win_rate_history: list[WinRateHistoryPoint] = []
    trades_by_day: list[TradesByDayPoint] = []

    # Create a lookup by date
    stats_by_date = {s.date: s for s in stats}

    # Fill in all dates in range
    current_date = start_date
    cumulative_trades = 0
    cumulative_wins = 0

    while current_date <= end_date:
        date_str = current_date.isoformat()

        if current_date in stats_by_date:
            s = stats_by_date[current_date]
            capital_history.append(
                CapitalHistoryPoint(
                    date=date_str,
                    capital=s.ending_capital or s.starting_capital,
                )
            )
            trades_by_day.append(
                TradesByDayPoint(
                    date=date_str,
                    count=s.total_trades,
                )
            )
            cumulative_trades += s.total_trades
            cumulative_wins += s.winning_trades
            cumulative_win_rate = (
                cumulative_wins / cumulative_trades if cumulative_trades > 0 else 0.0
            )
            win_rate_history.append(
                WinRateHistoryPoint(
                    date=date_str,
                    win_rate=cumulative_win_rate,
                )
            )
        else:
            # No data for this date, use previous day's values
            if capital_history:
                capital_history.append(
                    CapitalHistoryPoint(
                        date=date_str,
                        capital=capital_history[-1].capital,
                    )
                )
            if win_rate_history:
                win_rate_history.append(
                    WinRateHistoryPoint(
                        date=date_str,
                        win_rate=win_rate_history[-1].win_rate,
                    )
                )
            trades_by_day.append(
                TradesByDayPoint(
                    date=date_str,
                    count=0,
                )
            )

        current_date += timedelta(days=1)

    performance = PerformanceData(
        capital_history=capital_history,
        win_rate_history=win_rate_history,
        trades_by_day=trades_by_day,
    )

    return ApiResponse(success=True, data=performance, error=None)


# ============================================================================
# System Status Endpoints (Story 7.5)
# ============================================================================


async def get_last_market_fetch() -> datetime | None:
    """Get last market fetch timestamp from database.

    Returns:
        datetime | None: Last market fetch timestamp or None
    """
    try:
        async with get_connection() as conn:
            cursor = await conn.execute(
                "SELECT value, updated_at FROM system_state WHERE key = ?",
                ("last_market_fetch",),
            )
            row = await cursor.fetchone()
            if row and row[1]:
                return datetime.fromisoformat(row[1])
    except Exception as e:
        logger.warning(f"Failed to get last market fetch: {e}")
    return None


@router.get("/status", response_model=ApiResponse[SystemStatus])
async def get_system_status(
    state: ThreadSafeState = Depends(get_state),
) -> ApiResponse[SystemStatus]:
    """Get system running status.

    Returns real-time system status for monitoring including
    trading state, capital, and performance metrics.

    Args:
        state: ThreadSafeState dependency

    Returns:
        System status data
    """
    logger.info("📊 Getting system status")

    # Get current state
    state_snapshot = await state.get_state()

    # Get last market fetch time
    last_market_fetch = await get_last_market_fetch()

    # Calculate uptime
    uptime_hours = (time.time() - _app_start_time) / 3600

    # Fetch real wallet balance from Polymarket
    wallet_balance: float | None = None
    wallet_balance_error: str | None = None
    try:
        client = PolymarketClient()
        balance_result = client.get_wallet_balance()
        if balance_result.is_success:
            wallet_balance = balance_result.usdc_balance
        else:
            wallet_balance_error = balance_result.error
    except Exception as e:
        logger.warning(f"Failed to fetch wallet balance: {e}")
        wallet_balance_error = str(e)

    status = SystemStatus(
        trading_enabled=state_snapshot.trading_enabled,
        mode=settings.trading_mode.upper(),
        current_capital=state_snapshot.current_capital,
        daily_pnl=state_snapshot.daily_pnl,
        open_positions=state_snapshot.open_positions_count,
        consecutive_losses=state_snapshot.consecutive_losses,
        reduced_mode=state_snapshot.reduced_mode,
        last_market_fetch=last_market_fetch,
        uptime_hours=round(uptime_hours, 2),
        wallet_balance=wallet_balance,
        wallet_balance_error=wallet_balance_error,
    )

    return ApiResponse(success=True, data=status, error=None)


def mask_api_key(key: str) -> str:
    """Mask API key, showing only first 4 characters.

    Args:
        key: API key to mask

    Returns:
        Masked API key (e.g., "sk-x****xxxx")

    Example:
        >>> mask_api_key("sk-1234567890abcdef")
        'sk-1****'
    """
    if not key:
        return "[NOT_SET]"
    if len(key) <= 4:
        return key[:4] + "****"
    return key[:4] + "****"


def mask_private_key() -> str:
    """Return fully masked private key indicator.

    Returns:
        Always returns "[REDACTED]"
    """
    return "[REDACTED]"


def mask_wallet_address(address: str) -> str:
    """Mask wallet address, showing first 6 and last 4 characters.

    Args:
        address: Wallet address to mask

    Returns:
        Masked address (e.g., "0x1234...5678")

    Example:
        >>> mask_wallet_address("0x1234567890abcdef1234")
        '0x1234...1234'
    """
    if not address:
        return "[NOT_SET]"
    if len(address) <= 10:
        return address[:6] + "..." if len(address) >= 6 else address + "..."
    return f"{address[:6]}...{address[-4:]}"


@router.get("/settings", response_model=ApiResponse[SanitizedSettings])
async def get_settings_sanitized() -> ApiResponse[SanitizedSettings]:
    """Get sanitized system settings.

    Returns configuration values with sensitive data masked
    for secure display in the dashboard.

    Returns:
        Sanitized settings data
    """
    logger.info("📊 Getting sanitized settings")

    sanitized = SanitizedSettings(
        trading_mode=settings.trading_mode.upper(),
        initial_capital=settings.initial_capital,
        trade_unit=settings.trading.trade_unit,
        max_single_ratio=settings.risk.max_single_ratio,
        min_confidence=settings.risk.min_confidence,
        min_edge=settings.risk.min_edge,
        daily_loss_limit=settings.risk.daily_loss_limit,
        max_open_markets=settings.risk.max_open_markets,
        llm_model=settings.llm.model,
        llm_api_base=settings.llm.api_base,
        llm_api_key=mask_api_key(settings.llm.api_key),
        polymarket_pk=mask_private_key(),
        proxy_wallet=mask_wallet_address(settings.polymarket.proxy_wallet),
    )

    return ApiResponse(success=True, data=sanitized, error=None)


__all__ = ["router"]
