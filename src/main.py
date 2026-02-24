"""Main entry point for the Polymarket Trader application.

This module provides the main entry point for starting the trading system,
including command-line argument parsing, component initialization, and
graceful shutdown handling.

Usage:
    # Run with default settings (paper mode)
    python -m src.main

    # Run in live mode
    python -m src.main --mode live

    # Run with custom config file
    python -m src.main --config /path/to/config.env

    # Using the installed command (after pip install -e .)
    polymarket-trader --mode paper
"""

from __future__ import annotations

__all__ = ["Application", "parse_args", "async_main", "main"]

import argparse
import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from src.config import settings
from src.exceptions import BotError, ConfigurationError
from src.storage.database import close_db, init_db
from src.utils.logger import get_logger, setup_logging

if TYPE_CHECKING:
    from uvicorn import Server

    from src.api.telegram import TelegramClient
    from src.core.alerting import AlertManager
    from src.core.scheduler import Scheduler
    from src.core.state import ThreadSafeState

logger = get_logger(__name__)

# PID file path
PID_FILE = Path(".bot.pid")


class Application:
    """Main application class for Polymarket Trader.

    This class encapsulates all startup and shutdown logic, providing
    a clean interface for managing the application lifecycle.

    Attributes:
        mode: Trading mode ('paper' or 'live').
        config_path: Optional path to configuration file.
        state: Thread-safe state manager instance.
        scheduler: Task scheduler instance.
        _shutdown_event: Event triggered when shutdown is requested.
        _dashboard_task: Background task for the FastAPI dashboard.
        _dashboard_server: Uvicorn server instance for graceful shutdown.

    Example:
        >>> app = Application(mode="paper")
        >>> await app.start()  # Blocks until shutdown
    """

    def __init__(self, mode: str = "paper", config_path: str | None = None) -> None:
        """Initialize the application.

        Args:
            mode: Trading mode, either 'paper' (simulation) or 'live' (real trading).
            config_path: Optional path to configuration file.
        """
        self.mode = mode
        self.config_path = config_path
        self.state: ThreadSafeState | None = None
        self.scheduler: Scheduler | None = None
        self.alert_manager: AlertManager | None = None
        self.telegram_client: "TelegramClient | None" = None
        self._shutdown_event: asyncio.Event | None = None
        self._dashboard_task: asyncio.Task | None = None
        self._dashboard_server: Server | None = None
        self._telegram_task: asyncio.Task | None = None

    async def initialize(self) -> None:
        """Initialize all application components.

        This method performs the following initialization steps:
        1. Setup logging with configuration
        2. Setup error handling and alerting
        3. Initialize the database
        4. Restore or create state manager with recovery
        5. Initialize the scheduler

        Raises:
            ConfigurationError: If configuration is invalid.
            DatabaseError: If database initialization fails.
        """
        logger.info("Initializing application...")
        logger.info(f"Mode: {self.mode}")
        logger.info(f"Initial Capital: ${settings.initial_capital:.2f}")

        # 1. Setup logging
        setup_logging(log_level=settings.log_level, log_dir="logs")
        logger.debug("Logging configured")

        # 2. Setup error handling and alerting
        from src.core.alerting import AlertLevel, AlertManager, LogAlertChannel
        from src.core.error_handler import (
            setup_async_exception_handler,
            setup_error_handler,
            setup_global_exception_handler,
        )

        self.alert_manager = AlertManager(
            channels=[LogAlertChannel()],
            min_level=AlertLevel.WARNING,
            consecutive_failure_threshold=3,
        )
        setup_error_handler(alert_manager=self.alert_manager)
        setup_global_exception_handler()
        setup_async_exception_handler()
        logger.info("Error handling and alerting initialized")

        # 3. Initialize database
        await init_db()
        logger.info("Database initialized")

        # 4. Initialize state manager with recovery from database
        from src.core.state import ThreadSafeState

        self.state = ThreadSafeState(initial_capital=settings.initial_capital)
        recovery_result = await self.state.load_from_storage()

        if recovery_result.success:
            logger.info("State manager initialized with recovered state")
            if recovery_result.warnings:
                logger.warning(
                    f"Recovery completed with {len(recovery_result.warnings)} warnings"
                )
            if recovery_result.errors:
                logger.error(
                    f"Recovery completed with {len(recovery_result.errors)} errors - "
                    "trading may be disabled for safety"
                )
        else:
            logger.warning(
                "State manager initialized with fresh state (recovery failed)"
            )

        # 4. Initialize scheduler
        from src.core.scheduler import Scheduler

        self.scheduler = Scheduler()
        logger.info("Scheduler initialized")

        # 5. Initialize Telegram client
        from src.api.telegram import TelegramClient

        if settings.telegram.enabled:
            try:
                self.telegram_client = TelegramClient()
                await self.telegram_client.initialize()
                if self.telegram_client.is_enabled and self.state:
                    await self.telegram_client.setup_commands(self.state)
                    logger.info("Telegram client initialized with command handlers")
            except Exception as e:
                logger.warning(f"Telegram initialization failed: {e}")
                self.telegram_client = None
        else:
            logger.info("Telegram disabled in configuration")

    async def start_dashboard(self) -> None:
        """Start the FastAPI Dashboard as a background task.

        The dashboard runs on http://0.0.0.0:8000 by default.
        """
        import uvicorn

        from src.dashboard.app import app

        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=False,
        )
        self._dashboard_server = uvicorn.Server(config)

        # Run in background
        self._dashboard_task = asyncio.create_task(self._dashboard_server.serve())
        logger.info("Dashboard started on http://0.0.0.0:8000")

        # Give Dashboard time to start serving before blocking operations
        await asyncio.sleep(0.5)

    async def run_initial_analysis(self) -> None:
        """Run initial market analysis and trading on startup.

        This method triggers an immediate analysis when the application starts,
        before the scheduled tasks begin their regular intervals.
        Uses Gamma API to get active markets with liquidity data.
        Uses TradingExecutor to analyze, check risks, and execute trades.

        Story 5.3: 交易决策流程
        """
        logger.info("Running initial market analysis on startup...")

        try:
            # Fetch active markets using Gamma API with pagination
            # Use server-side deadline filtering to only get markets with
            # enough time remaining. This is more efficient than fetching
            # all and filtering locally
            from datetime import datetime, timedelta, timezone

            from src.analysis.market_filter import MarketFilter
            from src.api.polymarket import PolymarketClient
            from src.core.circuit_breaker import CircuitBreaker
            from src.storage.repositories.market_repo import MarketRepository
            from src.storage.repositories.position_repo import PositionRepository
            from src.storage.repositories.trade_repo import TradeRepository
            from src.trading.executor import TradingExecutor
            from src.trading.paper_trading import PaperTradingExecutor
            from src.trading.position_manager import PositionManager
            from src.trading.risk_control import RiskController

            client = PolymarketClient()
            min_deadline_hours = settings.market_filter.min_deadline_hours
            end_date_min = datetime.now(timezone.utc) + timedelta(
                hours=min_deadline_hours
            )

            gamma_markets = client.get_all_active_markets(
                total_limit=200,
                page_size=50,
                order_by="volume24hr",  # Sort by volume (most liquid first)
                ascending=False,
                end_date_min=end_date_min,  # Server-side deadline filter
            )
            logger.info(
                f"Fetched {len(gamma_markets)} active markets for initial analysis"
            )

            if not gamma_markets:
                logger.info("No markets found, skipping initial analysis")
                return

            # Convert GammaMarket to Market model
            markets = [gm.to_market() for gm in gamma_markets]

            # Filter markets
            market_filter = MarketFilter()
            filter_result = market_filter.filter_markets(markets)
            filtered_markets = filter_result.markets

            logger.info(
                f"Filtered markets: {len(filtered_markets)}/{len(markets)} "
                f"(stats: {filter_result.statistics})"
            )

            if not filtered_markets:
                logger.info("No markets passed filter, skipping initial analysis")
                return

            # Initialize trading components
            if not self.state:
                logger.warning("State not initialized, skipping trading")
                return

            market_repo = MarketRepository()
            trade_repo = TradeRepository()
            position_repo = PositionRepository()
            circuit_breaker = CircuitBreaker(self.state)
            risk_controller = RiskController(self.state, circuit_breaker)

            # Initialize LLM analyzer lazily to avoid import issues
            from src.analysis.llm_analyzer import LLMAnalyzer

            llm_analyzer = LLMAnalyzer()

            # Create position manager first
            position_manager = PositionManager(
                repository=position_repo,
                state=self.state,
            )

            paper_executor = PaperTradingExecutor(
                trade_repo=trade_repo,
                position_manager=position_manager,
                state=self.state,
            )

            # Create live executor if in live mode
            live_executor = None
            if settings.trading_mode.lower() == "live":
                from src.trading.live_trading import LiveTradingExecutor

                live_executor = LiveTradingExecutor(
                    client=client,
                    trade_repo=trade_repo,
                    position_manager=position_manager,
                    state=self.state,
                )
                logger.info("Live trading executor initialized")

            executor = TradingExecutor(
                llm_analyzer=llm_analyzer,
                risk_controller=risk_controller,
                paper_executor=paper_executor,
                state=self.state,
                live_executor=live_executor,
            )

            # Process each market through the complete trading flow
            analyzed_count = 0
            traded_count = 0
            skipped_count = 0
            error_count = 0

            for market in filtered_markets:
                try:
                    # Save market to database first (required for FK constraint)
                    await market_repo.save_market(market)

                    # Process market through complete trading flow
                    decision = await executor.process_market(market)
                    analyzed_count += 1

                    if decision.success:
                        if decision.skipped:
                            skipped_count += 1
                            logger.info(
                                f"Market {market.id[:8]}... skipped: {decision.reason}"
                            )
                        elif decision.trade:
                            traded_count += 1
                            logger.info(
                                f"Market {market.id[:8]}... traded: "
                                f"{decision.trade.trade_type.value} "
                                f"${decision.trade.amount:.2f}"
                            )
                    else:
                        error_count += 1
                        logger.warning(
                            f"Market {market.id[:8]}... error: {decision.error_message}"
                        )

                except Exception as e:
                    error_count += 1
                    logger.warning(f"Failed to process market {market.id}: {e}")

            logger.info(
                f"Initial analysis complete: {analyzed_count} analyzed, "
                f"{traded_count} traded, {skipped_count} skipped, "
                f"{error_count} errors"
            )

        except Exception as e:
            logger.error(f"Initial analysis failed: {e}", exc_info=True)

    async def register_scheduled_tasks(self) -> None:
        """Register all scheduled tasks with the scheduler.

        This method registers the following tasks:
        - Fetch markets (interval-based)
        - Check positions (interval-based)
        - Daily statistics (cron-based)
        - Validate predictions (cron-based)
        - Reset daily state (cron-based)
        - Persist state (interval-based)
        - Check exit strategies (interval-based) - Story 10.4
        """
        if not self.scheduler:
            logger.warning("Scheduler not initialized, skipping task registration")
            return

        # APScheduler lacks type stubs
        from apscheduler.triggers.cron import CronTrigger  # type: ignore
        from apscheduler.triggers.interval import IntervalTrigger  # type: ignore

        from src.config import settings as app_settings

        # Import task functions
        # Note: These imports are placed here to avoid circular imports
        # and to allow the tasks to be mocked in tests
        # Task 1: Analyze markets and execute trades periodically
        async def _analyze_and_trade_async() -> None:
            """Fetch, filter, analyze markets and execute trades.

            Story 5.3: 交易决策流程
            """
            try:
                # Fetch active markets using Gamma API with pagination
                # Use server-side deadline filtering to only get markets
                # with enough time remaining
                from datetime import datetime, timedelta, timezone

                from src.analysis.llm_analyzer import LLMAnalyzer
                from src.analysis.market_filter import MarketFilter
                from src.api.polymarket import PolymarketClient
                from src.core.circuit_breaker import CircuitBreaker
                from src.storage.repositories.market_repo import MarketRepository
                from src.storage.repositories.position_repo import PositionRepository
                from src.storage.repositories.trade_repo import TradeRepository
                from src.trading.executor import TradingExecutor
                from src.trading.paper_trading import PaperTradingExecutor
                from src.trading.position_manager import PositionManager
                from src.trading.risk_control import RiskController

                client = PolymarketClient()
                min_deadline_hours = app_settings.market_filter.min_deadline_hours
                end_date_min = datetime.now(timezone.utc) + timedelta(
                    hours=min_deadline_hours
                )

                gamma_markets = client.get_all_active_markets(
                    total_limit=200,
                    page_size=50,
                    order_by="volume24hr",  # Sort by volume (most liquid first)
                    ascending=False,
                    end_date_min=end_date_min,  # Server-side deadline filter
                )
                logger.info(f"Fetched {len(gamma_markets)} active markets")

                if not gamma_markets or not self.state:
                    return

                # Convert and filter
                markets = [gm.to_market() for gm in gamma_markets]
                market_filter = MarketFilter()
                filter_result = market_filter.filter_markets(markets)
                filtered_markets = filter_result.markets

                logger.info(f"Filtered: {len(filtered_markets)}/{len(markets)} markets")

                if not filtered_markets:
                    return

                # Initialize trading components
                market_repo = MarketRepository()
                trade_repo = TradeRepository()
                position_repo = PositionRepository()
                circuit_breaker = CircuitBreaker(self.state)
                risk_controller = RiskController(self.state, circuit_breaker)
                llm_analyzer = LLMAnalyzer()
                position_manager = PositionManager(
                    repository=position_repo,
                    state=self.state,
                )
                paper_executor = PaperTradingExecutor(
                    trade_repo=trade_repo,
                    position_manager=position_manager,
                    state=self.state,
                )

                # Create live executor if in live mode
                live_executor = None
                if app_settings.trading_mode.lower() == "live":
                    from src.trading.live_trading import LiveTradingExecutor

                    live_executor = LiveTradingExecutor(
                        client=client,
                        trade_repo=trade_repo,
                        position_manager=position_manager,
                        state=self.state,
                    )

                executor = TradingExecutor(
                    llm_analyzer=llm_analyzer,
                    risk_controller=risk_controller,
                    paper_executor=paper_executor,
                    state=self.state,
                    live_executor=live_executor,
                )

                # Process each market
                traded = 0
                for market in filtered_markets:
                    try:
                        await market_repo.save_market(market)
                        decision = await executor.process_market(market)
                        if decision.success and decision.trade:
                            traded += 1
                    except Exception as e:
                        logger.warning(f"Failed to process {market.id}: {e}")

                logger.info(f"Analysis complete: {traded} trades executed")

            except Exception as e:
                logger.error(f"Failed to analyze and trade: {e}")

        def analyze_and_trade_task() -> None:
            """Sync wrapper for the async analyze_and_trade function."""
            asyncio.run(_analyze_and_trade_async())

        self.scheduler.add_job(
            analyze_and_trade_task,
            IntervalTrigger(
                hours=app_settings.task_schedule.fetch_markets_interval_hours
            ),
            id="analyze_and_trade",
            name="Analyze Markets & Trade",
        )

        # Task 2: Check open positions periodically
        async def _check_positions_task_async() -> None:
            """Check and update open positions."""
            try:
                logger.debug("Checking open positions...")
                # TODO: Implement position checking logic in Story 8.4
            except Exception as e:
                logger.error(f"Failed to check positions: {e}")

        def check_positions_task() -> None:
            """Sync wrapper for the async check_positions function."""
            asyncio.run(_check_positions_task_async())

        self.scheduler.add_job(
            check_positions_task,
            IntervalTrigger(
                seconds=app_settings.task_schedule.check_positions_interval_seconds
            ),
            id="check_positions",
            name="Check Positions",
        )

        # Task 3: Generate daily statistics
        async def _daily_statistics_task_async() -> None:
            """Generate daily trading statistics."""
            try:
                logger.info("Generating daily statistics...")
                # TODO: Implement daily statistics logic
            except Exception as e:
                logger.error(f"Failed to generate daily statistics: {e}")

        def daily_statistics_task() -> None:
            """Sync wrapper for the async daily_statistics function."""
            asyncio.run(_daily_statistics_task_async())

        self.scheduler.add_job(
            daily_statistics_task,
            CronTrigger(
                hour=app_settings.task_schedule.daily_statistics_hour, minute=0
            ),
            id="daily_statistics",
            name="Daily Statistics",
        )

        # Task 4: Validate predictions
        async def _validate_predictions_task_async() -> None:
            """Validate past predictions against actual outcomes."""
            try:
                logger.info("Validating predictions...")
                # TODO: Implement prediction validation logic
            except Exception as e:
                logger.error(f"Failed to validate predictions: {e}")

        def validate_predictions_task() -> None:
            """Sync wrapper for the async validate_predictions function."""
            asyncio.run(_validate_predictions_task_async())

        self.scheduler.add_job(
            validate_predictions_task,
            CronTrigger(
                hour=app_settings.task_schedule.validate_predictions_hour, minute=0
            ),
            id="validate_predictions",
            name="Validate Predictions",
        )

        # Task 5: Reset daily state
        async def _reset_daily_state_task_async() -> None:
            """Reset daily state (PnL, consecutive losses)."""
            try:
                if self.state:
                    await self.state.reset_daily()
                    logger.info("Daily state reset complete")
            except Exception as e:
                logger.error(f"Failed to reset daily state: {e}")

        def reset_daily_state_task() -> None:
            """Sync wrapper for the async reset_daily_state function."""
            asyncio.run(_reset_daily_state_task_async())

        self.scheduler.add_job(
            reset_daily_state_task,
            CronTrigger(
                hour=app_settings.task_schedule.reset_daily_state_hour, minute=0
            ),
            id="reset_daily_state",
            name="Reset Daily State",
        )

        # Task 6: Persist state periodically
        async def _persist_state_task_async() -> None:
            """Persist state to database."""
            try:
                if self.state:
                    await self.state.persist()
                    logger.debug("State persisted to database")
            except Exception as e:
                logger.error(f"Failed to persist state: {e}")

        def persist_state_task() -> None:
            """Sync wrapper for the async persist_state function."""
            asyncio.run(_persist_state_task_async())

        self.scheduler.add_job(
            persist_state_task,
            IntervalTrigger(
                minutes=app_settings.task_schedule.state_persist_interval_minutes
            ),
            id="persist_state",
            name="Persist State",
        )

        # Task 7: Check exit strategies periodically
        # Story 10.4: 退出策略调度
        # Story 10.5: 退出通知集成
        async def _check_exit_strategies_async() -> None:
            """定期检查并执行退出策略.

            Story 10.4: 退出策略调度
            Story 10.5: 退出通知集成

            检查所有未平仓持仓，如果触发退出条件则执行卖出。
            """
            try:
                from src.api.polymarket import PolymarketClient
                from src.notifications.telegram_notifier import TelegramNotifier
                from src.storage.repositories.market_repo import MarketRepository
                from src.storage.repositories.position_repo import PositionRepository
                from src.storage.repositories.trade_repo import TradeRepository
                from src.trading.exit_checker import ExitChecker
                from src.trading.live_trading import LiveTradingExecutor
                from src.trading.position_manager import PositionManager

                if not self.state:
                    logger.warning(
                        "State not initialized, skipping exit strategy check"
                    )
                    return

                # 初始化组件
                position_repo = PositionRepository()
                market_repo = MarketRepository()
                trade_repo = TradeRepository()
                position_manager = PositionManager(
                    repository=position_repo,
                    state=self.state,
                )
                exit_checker = ExitChecker()

                # 初始化 Telegram 通知器 (Story 10.5)
                notifier: TelegramNotifier | None = None
                if (
                    self.telegram_client
                    and self.telegram_client.is_enabled
                    and settings.telegram.enabled
                ):
                    notifier = TelegramNotifier(self.telegram_client, use_queue=True)
                    await notifier.start()
                    logger.debug("Exit strategy: Telegram notifier initialized")

                # 获取所有未平仓持仓
                open_positions = await position_manager.get_open_positions()

                if not open_positions:
                    logger.debug("🔍 No open positions to check for exit")
                    return

                logger.info(
                    f"🔍 Checking exit strategies for "
                    f"{len(open_positions)} open positions"
                )

                # 统计变量
                checked_count = 0
                exit_count = 0
                fail_count = 0

                # 遍历检查每个持仓
                for position in open_positions:
                    try:
                        checked_count += 1

                        # 获取市场信息
                        market = await market_repo.get_market(position.market_id)
                        if not market:
                            logger.warning(
                                f"🔍 Market {position.market_id} not found "
                                f"for position {position.id}"
                            )
                            continue

                        # 检查退出条件
                        result = await exit_checker.check_exit_conditions(
                            position, market
                        )

                        if result.should_exit:
                            pnl_pct_str = (
                                f"{result.pnl_pct:.2%}"
                                if result.pnl_pct is not None
                                else "N/A"
                            )
                            logger.info(
                                f"🔍 Exit triggered for position {position.id}: "
                                f"reason={result.reason}, pnl_pct={pnl_pct_str}"
                            )

                            # 执行卖出 (仅 live 模式)
                            if app_settings.trading_mode.lower() == "live":
                                client = PolymarketClient()
                                live_executor = LiveTradingExecutor(
                                    client=client,
                                    trade_repo=trade_repo,
                                    position_manager=position_manager,
                                    state=self.state,
                                )

                                sell_result = await live_executor.sell_position(
                                    position=position,
                                    market=market,
                                    reason=result.reason,
                                )

                                if sell_result.success:
                                    exit_count += 1
                                    logger.info(
                                        f"💰 Exit executed: position {position.id}, "
                                        f"realized_pnl=${sell_result.realized_pnl:.2f}"
                                    )

                                    # Story 10.5: 发送退出成功通知
                                    if notifier and result.pnl_pct is not None:
                                        try:
                                            await notifier.send_exit_notification(
                                                position=position,
                                                market=market,
                                                pnl=sell_result.realized_pnl,
                                                pnl_pct=result.pnl_pct,
                                                exit_reason=result.reason,
                                            )
                                            logger.debug(
                                                f"Exit notification sent for "
                                                f"position {position.id}"
                                            )
                                        except Exception as notify_error:
                                            # 通知发送失败不影响主流程
                                            logger.warning(
                                                f"Failed to send exit notification: "
                                                f"{notify_error}"
                                            )
                                else:
                                    fail_count += 1
                                    logger.error(
                                        f"❌ Exit failed for position {position.id}: "
                                        f"{sell_result.error_message}"
                                    )
                                    # 记录失败到 AlertManager
                                    if self.alert_manager:
                                        self.alert_manager.record_failure(
                                            f"exit_strategy:{position.id}"
                                        )

                                    # Story 10.5: 发送退出失败通知
                                    if notifier:
                                        try:
                                            error_msg = (
                                                f"Exit failed for {market.title} "
                                                f"(position {position.id}): "
                                                f"{sell_result.error_message}"
                                            )
                                            await notifier.send_error_notification(
                                                error_msg
                                            )
                                        except Exception as notify_error:
                                            logger.warning(
                                                f"Failed to send exit error "
                                                f"notification: {notify_error}"
                                            )
                            else:
                                # Paper 模式下只记录日志
                                exit_count += 1
                                logger.info(
                                    f"📝 Paper mode: Would exit position {position.id} "
                                    f"due to {result.reason}"
                                )

                    except Exception as e:
                        fail_count += 1
                        logger.error(
                            f"❌ Failed to check/exit position {position.id}: {e}"
                        )
                        # 记录失败到 AlertManager
                        if self.alert_manager:
                            self.alert_manager.record_failure(
                                f"exit_strategy:{position.id}"
                            )
                        # 继续处理其他持仓

                # 记录摘要
                logger.info(
                    f"🔍 Exit strategy check complete: "
                    f"checked={checked_count}, exited={exit_count}, failed={fail_count}"
                )

                # 如果有任何成功的退出，重置失败计数
                if exit_count > 0 and self.alert_manager:
                    self.alert_manager.reset_failures("exit_strategy")

                # Story 10.5: 停止通知器
                if notifier:
                    await notifier.stop()

            except Exception as e:
                logger.error(f"❌ Exit strategy check task failed: {e}")
                # 记录整体任务失败
                if self.alert_manager:
                    self.alert_manager.record_failure("exit_strategy_task")

        def check_exit_strategies_task() -> None:
            """Sync wrapper for exit strategy check."""
            asyncio.run(_check_exit_strategies_async())

        self.scheduler.add_job(
            check_exit_strategies_task,
            IntervalTrigger(
                minutes=app_settings.exit_strategy.exit_check_interval_minutes
            ),
            id="check_exit_strategies",
            name="Check Exit Strategies",
        )
        logger.info("Exit strategy task registered")

        logger.info("All scheduled tasks registered")

    async def start(self) -> None:
        """Start all application components.

        This method orchestrates the complete startup sequence:
        1. Check for existing instance (PID file)
        2. Initialize components
        3. Write PID file
        4. Start Dashboard
        5. Register scheduled tasks
        6. Run initial market analysis
        7. Start scheduler
        8. Register signal handlers
        9. Wait for shutdown signal
        10. Perform graceful shutdown

        Raises:
            BotError: If another instance is already running.
            ConfigurationError: If configuration is invalid.
        """
        try:
            # Check for existing instance
            self._check_existing_instance()

            # Initialize
            await self.initialize()

            # Write PID file
            self._write_pid_file()

            # Start Dashboard
            await self.start_dashboard()

            # Register scheduled tasks
            await self.register_scheduled_tasks()

            # Start scheduler
            if self.scheduler:
                self.scheduler.start()
                logger.info("Scheduler started")

            # Start Telegram polling
            if self.telegram_client and self.telegram_client.is_enabled:
                self._telegram_task = asyncio.create_task(
                    self.telegram_client.start_polling()
                )
                logger.info("Telegram bot started polling")

            # Run initial analysis in background (non-blocking)
            asyncio.create_task(self.run_initial_analysis())
            logger.info("Initial analysis started in background")

            # Setup signal handlers
            self._setup_signal_handlers()

            logger.info(f"Application started in {self.mode} mode")

            # Create shutdown event and wait
            self._shutdown_event = asyncio.Event()
            await self._shutdown_event.wait()

        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            raise
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Perform graceful shutdown of all components.

        This method performs the following shutdown steps:
        1. Shutdown scheduler (wait for running jobs)
        2. Shutdown Dashboard server
        3. Persist state to database
        4. Close database connections
        5. Remove PID file
        """
        logger.info("Shutting down application...")

        # 1. Shutdown scheduler
        if self.scheduler and self.scheduler.is_running:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler shutdown complete")

        # 2. Shutdown Dashboard
        if self._dashboard_server:
            self._dashboard_server.should_exit = True
            logger.info("Dashboard shutdown initiated")

        if self._dashboard_task:
            self._dashboard_task.cancel()
            try:
                await self._dashboard_task
            except asyncio.CancelledError:
                pass
            logger.info("Dashboard shutdown complete")

        # 2.5 Shutdown Telegram
        if self._telegram_task:
            self._telegram_task.cancel()
            try:
                await self._telegram_task
            except asyncio.CancelledError:
                pass
            logger.info("Telegram polling stopped")

        if self.telegram_client:
            await self.telegram_client.shutdown()
            logger.info("Telegram client shutdown complete")

        # 3. Persist state
        if self.state:
            try:
                await self.state.persist()
                logger.info("State persisted to database")
            except Exception as e:
                logger.warning(f"Failed to persist state during shutdown: {e}")

        # 4. Close database connections
        await close_db()
        logger.info("Database connections closed")

        # 5. Remove PID file
        self._remove_pid_file()

        logger.info("Application shutdown complete")

    def _check_existing_instance(self) -> None:
        """Check if another instance is already running.

        Raises:
            BotError: If another instance is already running.
        """
        if PID_FILE.exists():
            try:
                pid_str = PID_FILE.read_text().strip()
                if pid_str:
                    pid = int(pid_str)
                    # Check if process is running
                    try:
                        os.kill(pid, 0)  # Signal 0 doesn't kill, just checks
                        raise BotError(
                            f"Another instance is already running (PID: {pid}). "
                            f"If this is incorrect, delete {PID_FILE} and try again."
                        )
                    except ProcessLookupError:
                        # Process not running, stale PID file
                        logger.warning(f"Removing stale PID file (PID: {pid})")
                        self._remove_pid_file()
            except ValueError:
                # Invalid PID file content
                logger.warning("Invalid PID file content, removing")
                self._remove_pid_file()

    def _write_pid_file(self) -> None:
        """Write PID file to prevent multiple instances."""
        pid = os.getpid()
        PID_FILE.write_text(str(pid))
        logger.debug(f"PID file written: {pid}")

    def _remove_pid_file(self) -> None:
        """Remove PID file if it exists."""
        if PID_FILE.exists():
            PID_FILE.unlink()
            logger.debug("PID file removed")

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        loop = asyncio.get_running_loop()

        def make_handler(sig: signal.Signals) -> None:
            """Create a signal handler that triggers shutdown."""
            asyncio.create_task(self._handle_signal(sig))

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, make_handler, sig)

    async def _handle_signal(self, sig: signal.Signals) -> None:
        """Handle shutdown signal.

        Args:
            sig: The signal that was received.
        """
        logger.info(f"Received signal {sig.name}, initiating graceful shutdown...")
        if self._shutdown_event:
            self._shutdown_event.set()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace with 'mode' and 'config' attributes.

    Example:
        >>> args = parse_args()
        >>> print(args.mode)
        'paper'
    """
    parser = argparse.ArgumentParser(
        description="Polymarket Trader - LLM-powered automated trading system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run in paper trading mode (default, safe simulation)
    polymarket-trader

    # Run in live trading mode (real money!)
    polymarket-trader --mode live

    # Use a custom configuration file
    polymarket-trader --config /path/to/.env
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["paper", "live"],
        default=None,
        help=(
            "Trading mode: paper (simulation) or live (real trading). "
            "Default: from TRADING_MODE env or paper"
        ),
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help=(
            "Path to configuration file (.env format). "
            "Default: use .env in current directory"
        ),
    )
    return parser.parse_args()


async def async_main() -> None:
    """Async main entry point.

    This function:
    1. Parses command-line arguments
    2. Creates the Application instance
    3. Starts the application (blocks until shutdown)

    Raises:
        SystemExit: On application error or shutdown.
    """
    args = parse_args()

    # Determine trading mode: CLI arg > env var > default
    if args.mode:
        # Override trading mode from command line
        os.environ["TRADING_MODE"] = args.mode
        mode = args.mode
    else:
        # Use mode from settings (which reads from env/.env)
        mode = settings.trading_mode

    # Load custom config file if specified
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {args.config}")
        # Settings will be reloaded with the new config via environment

    app = Application(mode=mode, config_path=args.config)
    await app.start()


def main() -> None:
    """Synchronous entry point for command-line usage.

    This function is the main entry point referenced in pyproject.toml.
    It handles top-level exception handling and ensures proper exit codes.

    Exit codes:
        0: Normal shutdown
        1: Error during execution
        130: Interrupted by Ctrl+C (SIGINT)
    """
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        logger.info("Interrupted by user")
        sys.exit(130)
    except asyncio.CancelledError:
        # Handle async cancellation as graceful shutdown
        logger.info("Application cancelled")
        sys.exit(0)
    except BotError as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
