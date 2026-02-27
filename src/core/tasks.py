"""Scheduled task configuration module.

Story 8.2: 定时任务配置

This module provides functionality to register and execute all scheduled tasks,
including market data fetching, LLM analysis, position checking, and state management.

The task system uses APScheduler (configured in Story 8.1) and integrates with:
- Market data repository (Epic 2)
- LLM analyzer (Epic 3)
- Position manager (Epic 4)
- State manager (Epic 4)
- Prediction tracker (Epic 6)
- Statistics repository (Epic 5)

Example:
    >>> from src.core.tasks import TaskManager, task_manager
    >>> from src.core.scheduler import scheduler
    >>>
    >>> # Register all tasks
    >>> task_manager.register_all_tasks(scheduler)
    >>>
    >>> # Or use individual registration functions
    >>> register_fetch_markets_job(scheduler, polymarket_client)
"""

from __future__ import annotations

__all__ = [
    "TaskManager",
    "task_manager",
    "register_all_tasks",
    "register_fetch_markets_job",
    "register_check_positions_job",
    "register_daily_statistics_job",
    "register_validate_predictions_job",
    "register_reset_daily_state_job",
    "register_persist_state_job",
    "register_refresh_position_cache_job",
    "prewarm_position_cache",
]

import asyncio
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.config import settings
from src.core.scheduler import Scheduler
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.analysis.llm_analyzer import LLMAnalyzer
    from src.analysis.market_filter import MarketFilter
    from src.analysis.prediction_tracker import PredictionTracker
    from src.api.polymarket import PolymarketClient
    from src.core.state import ThreadSafeState
    from src.storage.repositories.statistics_repo import StatisticsRepository
    from src.trading.position_manager import PositionManager

logger = get_logger(__name__)


class TaskManager:
    """Manager for scheduled tasks.

    Provides a centralized way to register and manage all scheduled tasks
    in the trading system.

    Attributes:
        _tasks: Dictionary of registered task functions
        _dependencies: Dictionary of task dependencies

    Example:
        >>> manager = TaskManager()
        >>> manager.register_all_tasks(scheduler, client, analyzer, position_mgr, state)
        >>> scheduler.start()
    """

    def __init__(self) -> None:
        """Initialize the TaskManager."""
        self._tasks: dict[str, Callable[..., Any]] = {}
        self._logger = get_logger(__name__)
        self._logger.info("TaskManager initialized")

    def register_all_tasks(
        self,
        scheduler: Scheduler,
        polymarket_client: "PolymarketClient",
        llm_analyzer: "LLMAnalyzer",
        position_manager: "PositionManager",
        state: "ThreadSafeState",
        market_filter: "MarketFilter | None" = None,
        prediction_tracker: "PredictionTracker | None" = None,
        statistics_repo: "StatisticsRepository | None" = None,
    ) -> list[str]:
        """Register all scheduled tasks.

        Args:
            scheduler: The scheduler instance to register tasks with
            polymarket_client: Polymarket API client for market data
            llm_analyzer: LLM analyzer for market analysis
            position_manager: Position manager for checking positions
            state: Thread-safe state manager
            market_filter: Optional market filter (will be created if None)
            prediction_tracker: Optional prediction tracker (will be created if None)
            statistics_repo: Optional statistics repository (will be created if None)

        Returns:
            List of registered job IDs

        Example:
            >>> job_ids = manager.register_all_tasks(
            ...     scheduler, client, analyzer, position_mgr, state
            ... )
            >>> print(f"Registered {len(job_ids)} tasks")
        """
        self._logger.info("Registering all scheduled jobs...")

        job_ids: list[str] = []

        # Register market fetching task
        job_ids.append(
            register_fetch_markets_job(
                scheduler,
                polymarket_client,
                llm_analyzer,
                market_filter,
            )
        )

        # Register position checking task
        job_ids.append(register_check_positions_job(scheduler, position_manager))

        # Register daily statistics task
        job_ids.append(register_daily_statistics_job(scheduler, state, statistics_repo))

        # Register prediction validation task
        job_ids.append(register_validate_predictions_job(scheduler, prediction_tracker))

        # Register daily state reset task
        job_ids.append(register_reset_daily_state_job(scheduler, state))

        # Register state persistence task
        job_ids.append(register_persist_state_job(scheduler, state))

        # Register position cache refresh task (Tech-Spec: Single Source of Truth)
        job_ids.append(register_refresh_position_cache_job(scheduler))

        self._logger.info(f"All jobs registered: {job_ids}")
        return job_ids


def register_all_tasks(
    scheduler: Scheduler,
    polymarket_client: "PolymarketClient",
    llm_analyzer: "LLMAnalyzer",
    position_manager: "PositionManager",
    state: "ThreadSafeState",
    market_filter: "MarketFilter | None" = None,
    prediction_tracker: "PredictionTracker | None" = None,
    statistics_repo: "StatisticsRepository | None" = None,
) -> list[str]:
    """Register all scheduled tasks (convenience function).

    Args:
        scheduler: The scheduler instance to register tasks with
        polymarket_client: Polymarket API client for market data
        llm_analyzer: LLM analyzer for market analysis
        position_manager: Position manager for checking positions
        state: Thread-safe state manager
        market_filter: Optional market filter (will be created if None)
        prediction_tracker: Optional prediction tracker (will be created if None)
        statistics_repo: Optional statistics repository (will be created if None)

    Returns:
        List of registered job IDs

    Example:
        >>> job_ids = register_all_tasks(
        ...     scheduler, client, analyzer, position_mgr, state
        ... )
    """
    return task_manager.register_all_tasks(
        scheduler,
        polymarket_client,
        llm_analyzer,
        position_manager,
        state,
        market_filter,
        prediction_tracker,
        statistics_repo,
    )


def register_fetch_markets_job(
    scheduler: Scheduler,
    client: "PolymarketClient",
    llm_analyzer: "LLMAnalyzer",
    market_filter: "MarketFilter | None" = None,
) -> str:
    """Register the market fetching task.

    This task fetches markets from Polymarket and triggers analysis.

    Args:
        scheduler: The scheduler instance
        client: Polymarket API client
        llm_analyzer: LLM analyzer for market analysis
        market_filter: Optional market filter (will be created if None)

    Returns:
        The registered job ID

    Example:
        >>> job_id = register_fetch_markets_job(scheduler, client, analyzer)
    """
    trigger = IntervalTrigger(hours=settings.task_schedule.fetch_markets_interval_hours)

    job_id = scheduler.add_job(
        func=lambda: asyncio.run(
            _fetch_markets_task(client, llm_analyzer, market_filter)
        ),
        trigger=trigger,
        id="fetch_markets",
        name="Fetch Markets from Polymarket",
    )

    logger.info(
        f"Job 'fetch_markets' registered with interval: "
        f"{settings.task_schedule.fetch_markets_interval_hours}h"
    )

    return job_id


async def _fetch_markets_task(
    client: "PolymarketClient",
    llm_analyzer: "LLMAnalyzer",
    market_filter: "MarketFilter | None" = None,
) -> None:
    """Execute market fetching task.

    Fetches markets from Polymarket, filters them, and triggers LLM analysis.

    Args:
        client: Polymarket API client
        llm_analyzer: LLM analyzer for market analysis
        market_filter: Optional market filter (will be created if None)
    """
    start_time = time.time()
    logger.info("Job 'fetch_markets' started")

    try:
        # Import here to avoid circular imports
        from src.analysis.market_filter import MarketFilter

        # Get markets from Polymarket
        # Note: get_markets is synchronous in the current implementation
        markets = client.get_markets()

        if not markets:
            elapsed = time.time() - start_time
            logger.info(f"Job 'fetch_markets' completed: 0 markets in {elapsed:.2f}s")
            return

        elapsed_fetch = time.time() - start_time
        logger.info(f"Fetched {len(markets)} markets in {elapsed_fetch:.2f}s")

        # Create market filter if not provided
        if market_filter is None:
            market_filter = MarketFilter()

        # Filter markets
        filter_result = market_filter.filter_markets(markets)
        filtered_markets = filter_result.markets

        logger.info(
            f"Filtered markets: {len(filtered_markets)}/{len(markets)} "
            f"(stats: {filter_result.statistics})"
        )

        # Trigger analysis task for filtered markets
        if filtered_markets:
            await _analyze_markets_task(filtered_markets, llm_analyzer)

        elapsed = time.time() - start_time
        logger.info(
            f"Job 'fetch_markets' completed: {len(markets)} markets fetched, "
            f"{len(filtered_markets)} filtered in {elapsed:.2f}s"
        )

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"Job 'fetch_markets' failed after {elapsed:.2f}s: {e}",
            exc_info=True,
        )


async def _analyze_markets_task(
    markets: list[Any],
    llm_analyzer: "LLMAnalyzer",
) -> None:
    """Execute market analysis task.

    Analyzes filtered markets using LLM.

    Args:
        markets: List of filtered markets to analyze
        llm_analyzer: LLM analyzer instance
    """
    start_time = time.time()
    logger.info(f"Job 'analyze_markets' started for {len(markets)} markets")

    try:
        analyzed_count = 0
        error_count = 0

        for market in markets:
            try:
                prediction = await llm_analyzer.analyze_market(market)
                analyzed_count += 1

                logger.info(
                    f"Market analyzed: {market.id[:8]}... "
                    f"prediction={prediction.predicted_probability:.2%} "
                    f"confidence={prediction.confidence:.2%} "
                    f"recommendation={prediction.recommendation.value}"
                )

            except Exception as e:
                error_count += 1
                logger.warning(f"Failed to analyze market {market.id}: {e}")

        elapsed = time.time() - start_time
        logger.info(
            f"Job 'analyze_markets' completed: {analyzed_count} analyzed, "
            f"{error_count} errors in {elapsed:.2f}s"
        )

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"Job 'analyze_markets' failed after {elapsed:.2f}s: {e}",
            exc_info=True,
        )


def register_check_positions_job(
    scheduler: Scheduler,
    manager: "PositionManager",
) -> str:
    """Register the position checking task.

    This task checks all open positions and updates their PnL.

    Args:
        scheduler: The scheduler instance
        manager: Position manager instance

    Returns:
        The registered job ID

    Example:
        >>> job_id = register_check_positions_job(scheduler, position_manager)
    """
    trigger = IntervalTrigger(
        seconds=settings.task_schedule.check_positions_interval_seconds
    )

    job_id = scheduler.add_job(
        func=lambda: asyncio.run(_check_positions_task(manager)),
        trigger=trigger,
        id="check_positions",
        name="Check Positions and Update PnL",
    )

    logger.info(
        f"Job 'check_positions' registered with interval: "
        f"{settings.task_schedule.check_positions_interval_seconds}s"
    )

    return job_id


async def _check_positions_task(manager: "PositionManager") -> None:
    """Execute position checking task.

    Checks all open positions and updates their current values.

    Args:
        manager: Position manager instance
    """
    start_time = time.time()
    logger.debug("Job 'check_positions' started")

    try:
        # Get all open positions
        positions = await manager.get_open_positions()

        if not positions:
            elapsed = time.time() - start_time
            logger.debug(
                f"Job 'check_positions' completed: 0 positions in {elapsed:.2f}s"
            )
            return

        # Note: In a real implementation, we would fetch current prices
        # from the market and call update_all_positions_value with the prices.
        # For now, we just log the positions count.
        # This is a placeholder for the actual price update logic.

        elapsed = time.time() - start_time
        logger.debug(
            f"Job 'check_positions' completed: {len(positions)} positions "
            f"checked in {elapsed:.2f}s"
        )

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"Job 'check_positions' failed after {elapsed:.2f}s: {e}",
            exc_info=True,
        )


def register_daily_statistics_job(
    scheduler: Scheduler,
    state: "ThreadSafeState",
    statistics_repo: "StatisticsRepository | None" = None,
) -> str:
    """Register the daily statistics task.

    This task records daily trading statistics to the database.

    Args:
        scheduler: The scheduler instance
        state: Thread-safe state manager
        statistics_repo: Optional statistics repository (will be created if None)

    Returns:
        The registered job ID

    Example:
        >>> job_id = register_daily_statistics_job(scheduler, state)
    """
    trigger = CronTrigger(
        hour=settings.task_schedule.daily_statistics_hour,
        minute=0,
    )

    job_id = scheduler.add_job(
        func=lambda: asyncio.run(_daily_statistics_task(state, statistics_repo)),
        trigger=trigger,
        id="daily_statistics",
        name="Daily Statistics Update",
    )

    logger.info(
        f"Job 'daily_statistics' registered at hour: "
        f"{settings.task_schedule.daily_statistics_hour}"
    )

    return job_id


async def _daily_statistics_task(
    state: "ThreadSafeState",
    statistics_repo: "StatisticsRepository | None" = None,
) -> None:
    """Execute daily statistics task.

    Records daily trading statistics to the database.

    Args:
        state: Thread-safe state manager
        statistics_repo: Optional statistics repository (will be created if None)
    """
    start_time = time.time()
    logger.info("Job 'daily_statistics' started")

    try:
        # Import here to avoid circular imports
        from src.models.statistics import Statistics
        from src.models.trade import TradeMode
        from src.storage.repositories.statistics_repo import StatisticsRepository

        # Create repository if not provided
        if statistics_repo is None:
            statistics_repo = StatisticsRepository()

        # Get current state
        current_state = await state.get_state()

        # Calculate win rate
        # Note: In the current state implementation, we track daily_pnl but not
        # individual wins/losses. We'll set default values for these.
        daily_trades = 0  # Placeholder - would need to track this in state
        daily_wins = 0
        daily_losses = 0
        win_rate = 0.0

        # Create statistics record
        stats = Statistics(
            id=0,  # Will be assigned by database
            date=datetime.now().date(),
            mode=(
                TradeMode.PAPER if settings.trading_mode == "paper" else TradeMode.LIVE
            ),
            starting_capital=settings.initial_capital,
            ending_capital=current_state.current_capital,
            total_pnl=current_state.daily_pnl,
            total_trades=daily_trades,
            winning_trades=daily_wins,
            losing_trades=daily_losses,
            win_rate=win_rate,
        )

        # Save to database
        await statistics_repo.save(stats)

        elapsed = time.time() - start_time
        logger.info(
            f"Job 'daily_statistics' completed: "
            f"capital=${current_state.current_capital:.2f}, "
            f"daily_pnl=${current_state.daily_pnl:.2f} in {elapsed:.2f}s"
        )

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"Job 'daily_statistics' failed after {elapsed:.2f}s: {e}",
            exc_info=True,
        )


def register_validate_predictions_job(
    scheduler: Scheduler,
    prediction_tracker: "PredictionTracker | None" = None,
) -> str:
    """Register the prediction validation task.

    This task validates predictions against resolved market outcomes.

    Args:
        scheduler: The scheduler instance
        prediction_tracker: Optional prediction tracker (will be created if None)

    Returns:
        The registered job ID

    Example:
        >>> job_id = register_validate_predictions_job(scheduler)
    """
    trigger = CronTrigger(
        hour=settings.task_schedule.validate_predictions_hour,
        minute=0,
    )

    job_id = scheduler.add_job(
        func=lambda: asyncio.run(_validate_predictions_task(prediction_tracker)),
        trigger=trigger,
        id="validate_predictions",
        name="Validate Predictions against Resolved Markets",
    )

    logger.info(
        f"Job 'validate_predictions' registered at hour: "
        f"{settings.task_schedule.validate_predictions_hour}"
    )

    return job_id


async def _validate_predictions_task(
    prediction_tracker: "PredictionTracker | None" = None,
) -> None:
    """Execute prediction validation task.

    Validates predictions against resolved market outcomes.

    Args:
        prediction_tracker: Optional prediction tracker (will be created if None)
    """
    start_time = time.time()
    logger.info("Job 'validate_predictions' started")

    try:
        # Import here to avoid circular imports
        from src.analysis.prediction_tracker import PredictionTracker
        from src.storage.repositories.market_repo import MarketRepository
        from src.storage.repositories.prediction_repo import PredictionRepository

        # Create tracker if not provided
        if prediction_tracker is None:
            market_repo = MarketRepository()
            prediction_repo = PredictionRepository()
            prediction_tracker = PredictionTracker(market_repo, prediction_repo)

        # Check resolved markets and validate predictions
        results = await prediction_tracker.check_resolved_markets()

        elapsed = time.time() - start_time
        validated_count = len([r for r in results if r.is_validated])
        correct_count = len([r for r in results if r.is_correct])

        logger.info(
            f"Job 'validate_predictions' completed: {validated_count} predictions "
            f"validated ({correct_count} correct) in {elapsed:.2f}s"
        )

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"Job 'validate_predictions' failed after {elapsed:.2f}s: {e}",
            exc_info=True,
        )


def register_reset_daily_state_job(
    scheduler: Scheduler,
    state: "ThreadSafeState",
) -> str:
    """Register the daily state reset task.

    This task resets daily state variables (daily_pnl, consecutive_losses).

    Args:
        scheduler: The scheduler instance
        state: Thread-safe state manager

    Returns:
        The registered job ID

    Example:
        >>> job_id = register_reset_daily_state_job(scheduler, state)
    """
    trigger = CronTrigger(
        hour=settings.task_schedule.reset_daily_state_hour,
        minute=0,
    )

    job_id = scheduler.add_job(
        func=lambda: asyncio.run(_reset_daily_state_task(state)),
        trigger=trigger,
        id="reset_daily_state",
        name="Reset Daily State",
    )

    logger.info(
        f"Job 'reset_daily_state' registered at hour: "
        f"{settings.task_schedule.reset_daily_state_hour}"
    )

    return job_id


async def _reset_daily_state_task(state: "ThreadSafeState") -> None:
    """Execute daily state reset task.

    Resets daily state variables.

    Args:
        state: Thread-safe state manager
    """
    start_time = time.time()
    logger.info("Job 'reset_daily_state' started")

    try:
        # Reset daily state
        await state.reset_daily()

        elapsed = time.time() - start_time
        logger.info(f"Job 'reset_daily_state' completed in {elapsed:.2f}s")

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"Job 'reset_daily_state' failed after {elapsed:.2f}s: {e}",
            exc_info=True,
        )


def register_persist_state_job(
    scheduler: Scheduler,
    state: "ThreadSafeState",
) -> str:
    """Register the state persistence task.

    This task periodically persists the current state to the database.

    Args:
        scheduler: The scheduler instance
        state: Thread-safe state manager

    Returns:
        The registered job ID

    Example:
        >>> job_id = register_persist_state_job(scheduler, state)
    """
    trigger = IntervalTrigger(
        minutes=settings.task_schedule.state_persist_interval_minutes
    )

    job_id = scheduler.add_job(
        func=lambda: asyncio.run(_persist_state_task(state)),
        trigger=trigger,
        id="persist_state",
        name="Persist State to Database",
    )

    logger.info(
        f"Job 'persist_state' registered with interval: "
        f"{settings.task_schedule.state_persist_interval_minutes}min"
    )

    return job_id


async def _persist_state_task(state: "ThreadSafeState") -> None:
    """Execute state persistence task.

    Persists current state to the database.

    Args:
        state: Thread-safe state manager
    """
    start_time = time.time()
    logger.debug("Job 'persist_state' started")

    try:
        # Persist state to database
        await state.persist()

        elapsed = time.time() - start_time
        logger.debug(f"Job 'persist_state' completed in {elapsed:.2f}s")

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"Job 'persist_state' failed after {elapsed:.2f}s: {e}",
            exc_info=True,
        )


# ==================== Tech-Spec: 持仓缓存刷新任务 ====================


def register_refresh_position_cache_job(
    scheduler: Scheduler,
    interval_seconds: int | None = None,
) -> str:
    """Register the position cache refresh task.

    Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源

    This task periodically refreshes the position cache from Polymarket API
    to ensure data freshness for the dashboard.

    Args:
        scheduler: The scheduler instance
        interval_seconds: Refresh interval in seconds.
            Default: settings.position_cache.ttl * 5 (5x TTL for optimal balance)
            Should be greater than position_cache.ttl (default 60s)

    Returns:
        The registered job ID

    Example:
        >>> job_id = register_refresh_position_cache_job(scheduler)
    """
    # Use settings-based default interval (5x TTL)
    if interval_seconds is None:
        interval_seconds = settings.position_cache.ttl * 5

    trigger = IntervalTrigger(seconds=interval_seconds)

    job_id = scheduler.add_job(
        func=_refresh_position_cache_task_sync,
        trigger=trigger,
        id="refresh_position_cache",
        name="Refresh Position Cache",
    )

    logger.info(
        f"Job 'refresh_position_cache' registered with interval: {interval_seconds}s"
    )

    return job_id


def _refresh_position_cache_task_sync() -> None:
    """Synchronous wrapper for position cache refresh task.

    Handles event loop management properly to avoid asyncio.run() issues
    in scheduled contexts.
    """
    try:
        # Check if there's already a running event loop
        loop = asyncio.get_running_loop()
        # If we're here, there's a running loop - create task
        asyncio.create_task(_refresh_position_cache_task())
    except RuntimeError:
        # No running loop - create one
        asyncio.run(_refresh_position_cache_task())


async def _refresh_position_cache_task() -> None:
    """Execute position cache refresh task.

    Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源

    Refreshes position cache from Polymarket API.
    """
    start_time = time.time()
    logger.debug("Job 'refresh_position_cache' started")

    try:
        from src.trading.position_sync import PositionCacheService

        cache_service = PositionCacheService()
        result = await cache_service.refresh_cache()

        elapsed = time.time() - start_time
        if result.is_success:
            logger.debug(
                f"Job 'refresh_position_cache' completed: "
                f"{result.new_positions} new, {result.updated_positions} updated, "
                f"{result.closed_positions} closed in {elapsed:.2f}s"
            )
        else:
            logger.warning(
                f"Job 'refresh_position_cache' completed with error: {result.error}"
            )

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"Job 'refresh_position_cache' failed after {elapsed:.2f}s: {e}",
            exc_info=True,
        )


async def prewarm_position_cache() -> bool:
    """Prewarm position cache on application startup.

    Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源

    This function should be called during application initialization
    to populate the position cache with fresh data.

    Returns:
        True if prewarming succeeded, False otherwise
    """
    logger.info("🔄 Prewarming position cache...")

    try:
        from src.trading.position_sync import PositionCacheService

        cache_service = PositionCacheService()
        result = await cache_service.refresh_cache()

        if result.is_success:
            logger.info(
                f"✅ Position cache prewarmed: "
                f"{result.new_positions} new, {result.updated_positions} updated, "
                f"{result.total_fetched} fetched"
            )
            return True
        else:
            # Prewarming failed, but app can still run with empty cache
            logger.warning(
                f"⚠️ Position cache prewarming failed: {result.error}. "
                "App will continue with empty cache."
            )
            return False

    except Exception as e:
        logger.error(f"❌ Position cache prewarming error: {e}")
        return False


# Module-level singleton
task_manager = TaskManager()
