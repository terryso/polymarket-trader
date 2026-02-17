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
    from src.core.alerting import AlertManager
    from src.core.scheduler import Scheduler
    from src.core.state import ThreadSafeState
    from uvicorn import Server

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
        self._shutdown_event: asyncio.Event | None = None
        self._dashboard_task: asyncio.Task | None = None
        self._dashboard_server: Server | None = None

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
        from src.core.alerting import AlertManager, AlertLevel, LogAlertChannel
        from src.core.error_handler import (
            setup_error_handler,
            setup_global_exception_handler,
            setup_async_exception_handler,
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
            logger.warning("State manager initialized with fresh state (recovery failed)")

        # 4. Initialize scheduler
        from src.core.scheduler import Scheduler

        self.scheduler = Scheduler()
        logger.info("Scheduler initialized")

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

    async def register_scheduled_tasks(self) -> None:
        """Register all scheduled tasks with the scheduler.

        This method registers the following tasks:
        - Fetch markets (interval-based)
        - Check positions (interval-based)
        - Daily statistics (cron-based)
        - Validate predictions (cron-based)
        - Reset daily state (cron-based)
        - Persist state (interval-based)
        """
        if not self.scheduler:
            logger.warning("Scheduler not initialized, skipping task registration")
            return

        # APScheduler lacks type stubs, ignore import-untyped errors
        from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]
        from apscheduler.triggers.interval import IntervalTrigger  # type: ignore[import-untyped]

        from src.config import settings as app_settings

        # Import task functions
        # Note: These imports are placed here to avoid circular imports
        # and to allow the tasks to be mocked in tests

        # Task 1: Fetch markets periodically
        async def fetch_markets_task() -> None:
            """Fetch and store markets from Polymarket."""
            try:
                from src.api.polymarket import PolymarketClient

                client = PolymarketClient()
                markets = client.get_markets()
                logger.info(f"Fetched {len(markets)} markets")
            except Exception as e:
                logger.error(f"Failed to fetch markets: {e}")

        self.scheduler.add_job(
            fetch_markets_task,
            IntervalTrigger(hours=app_settings.task_schedule.fetch_markets_interval_hours),
            id="fetch_markets",
            name="Fetch Markets",
        )

        # Task 2: Check open positions periodically
        async def check_positions_task() -> None:
            """Check and update open positions."""
            try:
                logger.debug("Checking open positions...")
                # TODO: Implement position checking logic in Story 8.4
            except Exception as e:
                logger.error(f"Failed to check positions: {e}")

        self.scheduler.add_job(
            check_positions_task,
            IntervalTrigger(seconds=app_settings.task_schedule.check_positions_interval_seconds),
            id="check_positions",
            name="Check Positions",
        )

        # Task 3: Generate daily statistics
        async def daily_statistics_task() -> None:
            """Generate daily trading statistics."""
            try:
                logger.info("Generating daily statistics...")
                # TODO: Implement daily statistics logic
            except Exception as e:
                logger.error(f"Failed to generate daily statistics: {e}")

        self.scheduler.add_job(
            daily_statistics_task,
            CronTrigger(hour=app_settings.task_schedule.daily_statistics_hour, minute=0),
            id="daily_statistics",
            name="Daily Statistics",
        )

        # Task 4: Validate predictions
        async def validate_predictions_task() -> None:
            """Validate past predictions against actual outcomes."""
            try:
                logger.info("Validating predictions...")
                # TODO: Implement prediction validation logic
            except Exception as e:
                logger.error(f"Failed to validate predictions: {e}")

        self.scheduler.add_job(
            validate_predictions_task,
            CronTrigger(hour=app_settings.task_schedule.validate_predictions_hour, minute=0),
            id="validate_predictions",
            name="Validate Predictions",
        )

        # Task 5: Reset daily state
        async def reset_daily_state_task() -> None:
            """Reset daily state (PnL, consecutive losses)."""
            try:
                if self.state:
                    await self.state.reset_daily()
                    logger.info("Daily state reset complete")
            except Exception as e:
                logger.error(f"Failed to reset daily state: {e}")

        self.scheduler.add_job(
            reset_daily_state_task,
            CronTrigger(hour=app_settings.task_schedule.reset_daily_state_hour, minute=0),
            id="reset_daily_state",
            name="Reset Daily State",
        )

        # Task 6: Persist state periodically
        async def persist_state_task() -> None:
            """Persist state to database."""
            try:
                if self.state:
                    await self.state.persist()
                    logger.debug("State persisted to database")
            except Exception as e:
                logger.error(f"Failed to persist state: {e}")

        self.scheduler.add_job(
            persist_state_task,
            IntervalTrigger(minutes=app_settings.task_schedule.state_persist_interval_minutes),
            id="persist_state",
            name="Persist State",
        )

        logger.info("All scheduled tasks registered")

    async def start(self) -> None:
        """Start all application components.

        This method orchestrates the complete startup sequence:
        1. Check for existing instance (PID file)
        2. Initialize components
        3. Write PID file
        4. Start Dashboard
        5. Register and start scheduler
        6. Register signal handlers
        7. Wait for shutdown signal
        8. Perform graceful shutdown

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
        default="paper",
        help="Trading mode: paper (simulation) or live (real trading). Default: paper",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configuration file (.env format). Default: use .env in current directory",
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

    # Override trading mode from command line
    if args.mode:
        os.environ["TRADING_MODE"] = args.mode

    # Load custom config file if specified
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {args.config}")
        # Settings will be reloaded with the new config via environment

    app = Application(mode=args.mode, config_path=args.config)
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
