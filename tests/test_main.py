"""Unit tests for the main entry point module.

This module tests the Application class and main entry point functionality
including command-line argument parsing, startup/shutdown flows, and
signal handling.
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.main import (
    PID_FILE,
    Application,
    async_main,
    main,
    parse_args,
)


class TestParseArgs:
    """Tests for command-line argument parsing."""

    def test_default_args(self) -> None:
        """Test default argument values."""
        with patch.object(sys, "argv", ["main.py"]):
            args = parse_args()
            assert args.mode is None  # Default is None, uses env var
            assert args.config is None

    def test_live_mode(self) -> None:
        """Test live mode argument."""
        with patch.object(sys, "argv", ["main.py", "--mode", "live"]):
            args = parse_args()
            assert args.mode == "live"

    def test_paper_mode_explicit(self) -> None:
        """Test explicit paper mode argument."""
        with patch.object(sys, "argv", ["main.py", "--mode", "paper"]):
            args = parse_args()
            assert args.mode == "paper"

    def test_custom_config(self) -> None:
        """Test custom config file argument."""
        with patch.object(sys, "argv", ["main.py", "--config", "/path/to/config.env"]):
            args = parse_args()
            assert args.config == "/path/to/config.env"

    def test_all_args(self) -> None:
        """Test all arguments together."""
        with patch.object(
            sys, "argv", ["main.py", "--mode", "live", "--config", "/custom/.env"]
        ):
            args = parse_args()
            assert args.mode == "live"
            assert args.config == "/custom/.env"


class TestApplicationInit:
    """Tests for Application class initialization."""

    def test_default_initialization(self) -> None:
        """Test default Application initialization."""
        app = Application()
        assert app.mode == "paper"
        assert app.config_path is None
        assert app.state is None
        assert app.scheduler is None
        assert app._shutdown_event is None
        assert app._dashboard_task is None
        assert app._dashboard_server is None

    def test_custom_mode_initialization(self) -> None:
        """Test Application initialization with custom mode."""
        app = Application(mode="live")
        assert app.mode == "live"

    def test_custom_config_initialization(self) -> None:
        """Test Application initialization with custom config path."""
        app = Application(mode="paper", config_path="/path/to/.env")
        assert app.mode == "paper"
        assert app.config_path == "/path/to/.env"


class TestApplicationInitialize:
    """Tests for Application.initialize() method."""

    @pytest.mark.asyncio
    async def test_initialize_success(self) -> None:
        """Test successful initialization."""
        from src.core.recovery import RecoveryResult

        app = Application(mode="paper")

        # Create a mock recovery result
        mock_recovery_result = RecoveryResult(
            success=True,
            recovered_state={"current_capital": 200.0, "trading_enabled": True},
        )

        with patch("src.main.setup_logging") as mock_setup_logging, \
             patch("src.main.init_db", new_callable=AsyncMock) as mock_init_db, \
             patch("src.core.state.ThreadSafeState.load_from_storage", new_callable=AsyncMock) as mock_load, \
             patch("src.core.scheduler.Scheduler") as mock_scheduler_class:
            mock_load.return_value = mock_recovery_result
            mock_scheduler_class.return_value = MagicMock()

            await app.initialize()

            mock_setup_logging.assert_called_once()
            mock_init_db.assert_called_once()
            mock_load.assert_called_once()
            assert app.state is not None
            assert app.scheduler is not None

    @pytest.mark.asyncio
    async def test_initialize_database_failure(self) -> None:
        """Test initialization failure due to database error."""
        app = Application(mode="paper")

        with (
            patch("src.main.setup_logging"),
            patch(
                "src.main.init_db",
                new_callable=AsyncMock,
                side_effect=Exception("Database error"),
            ),
        ):
            with pytest.raises(Exception, match="Database error"):
                await app.initialize()


class TestApplicationStartDashboard:
    """Tests for Application.start_dashboard() method."""

    @pytest.mark.asyncio
    async def test_start_dashboard(self) -> None:
        """Test dashboard startup."""
        app = Application(mode="paper")

        with patch("uvicorn.Server") as mock_server_class, \
             patch("uvicorn.Config") as mock_config_class:
            mock_server = MagicMock()
            mock_server.serve = AsyncMock()
            mock_server_class.return_value = mock_server
            mock_config_class.return_value = MagicMock()

            await app.start_dashboard()

            assert app._dashboard_server is not None
            assert app._dashboard_task is not None


class TestApplicationRegisterScheduledTasks:
    """Tests for Application.register_scheduled_tasks() method."""

    @pytest.mark.asyncio
    async def test_register_tasks_no_scheduler(self) -> None:
        """Test task registration when scheduler is not initialized."""
        app = Application(mode="paper")
        app.scheduler = None

        # Should not raise an error
        await app.register_scheduled_tasks()

    @pytest.mark.asyncio
    async def test_register_tasks_success(self) -> None:
        """Test successful task registration."""
        app = Application(mode="paper")
        mock_scheduler = MagicMock()
        app.scheduler = mock_scheduler
        app.state = MagicMock()

        with patch("apscheduler.triggers.interval.IntervalTrigger") as mock_interval, \
             patch("apscheduler.triggers.cron.CronTrigger") as mock_cron:
            mock_interval.return_value = MagicMock()
            mock_cron.return_value = MagicMock()

            await app.register_scheduled_tasks()

            # Should have registered 6 tasks
            assert mock_scheduler.add_job.call_count == 6


class TestApplicationShutdown:
    """Tests for Application.shutdown() method."""

    @pytest.mark.asyncio
    async def test_shutdown_no_components(self) -> None:
        """Test shutdown with no initialized components."""
        app = Application(mode="paper")

        with patch("src.main.close_db", new_callable=AsyncMock):
            await app.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_with_scheduler(self) -> None:
        """Test shutdown with running scheduler."""
        app = Application(mode="paper")
        mock_scheduler = MagicMock()
        mock_scheduler.is_running = True
        mock_scheduler.shutdown = MagicMock()
        app.scheduler = mock_scheduler

        with patch("src.main.close_db", new_callable=AsyncMock):
            await app.shutdown()

            mock_scheduler.shutdown.assert_called_once_with(wait=True)

    @pytest.mark.asyncio
    async def test_shutdown_with_dashboard(self) -> None:
        """Test shutdown with running dashboard."""
        app = Application(mode="paper")
        app._dashboard_server = MagicMock()
        app._dashboard_server.should_exit = False

        mock_task = AsyncMock()
        mock_task.cancel = MagicMock()

        # Make await raise CancelledError
        async def raise_cancelled() -> None:
            raise asyncio.CancelledError()

        mock_task.side_effect = raise_cancelled
        app._dashboard_task = asyncio.create_task(
            asyncio.sleep(0)
        )  # Create a real task

        with patch("src.main.close_db", new_callable=AsyncMock):
            await app.shutdown()

            assert app._dashboard_server.should_exit is True

    @pytest.mark.asyncio
    async def test_shutdown_with_state(self) -> None:
        """Test shutdown persists state."""
        app = Application(mode="paper")
        mock_state = MagicMock()
        mock_state.persist = AsyncMock()
        app.state = mock_state

        with patch("src.main.close_db", new_callable=AsyncMock):
            await app.shutdown()

            mock_state.persist.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_state_persist_failure(self) -> None:
        """Test shutdown continues even if state persist fails."""
        app = Application(mode="paper")
        mock_state = MagicMock()
        mock_state.persist = AsyncMock(side_effect=Exception("Persist error"))
        app.state = mock_state

        with patch("src.main.close_db", new_callable=AsyncMock):
            # Should not raise an error
            await app.shutdown()


class TestApplicationPidFile:
    """Tests for PID file management."""

    def test_write_pid_file(self, tmp_path: Path) -> None:
        """Test PID file writing."""
        app = Application(mode="paper")

        with patch("src.main.PID_FILE", tmp_path / ".bot.pid"):
            app._write_pid_file()

            pid_file = tmp_path / ".bot.pid"
            assert pid_file.exists()
            content = pid_file.read_text()
            assert content == str(os.getpid())

    def test_remove_pid_file(self, tmp_path: Path) -> None:
        """Test PID file removal."""
        app = Application(mode="paper")
        pid_file = tmp_path / ".bot.pid"

        with patch("src.main.PID_FILE", pid_file):
            pid_file.write_text(str(os.getpid()))
            assert pid_file.exists()

            app._remove_pid_file()
            assert not pid_file.exists()

    def test_remove_pid_file_not_exists(self, tmp_path: Path) -> None:
        """Test PID file removal when file doesn't exist."""
        app = Application(mode="paper")
        pid_file = tmp_path / ".bot.pid"

        with patch("src.main.PID_FILE", pid_file):
            # Should not raise an error
            app._remove_pid_file()

    def test_check_existing_instance_no_file(self, tmp_path: Path) -> None:
        """Test instance check when no PID file exists."""
        app = Application(mode="paper")
        pid_file = tmp_path / ".bot.pid"

        with patch("src.main.PID_FILE", pid_file):
            # Should not raise an error
            app._check_existing_instance()

    def test_check_existing_instance_stale_file(self, tmp_path: Path) -> None:
        """Test instance check with stale PID file (non-existent process)."""
        app = Application(mode="paper")
        pid_file = tmp_path / ".bot.pid"

        with patch("src.main.PID_FILE", pid_file):
            # Write a PID that doesn't exist (999999 is unlikely to be running)
            pid_file.write_text("999999")

            # Should remove stale file and not raise error
            app._check_existing_instance()
            assert not pid_file.exists()

    def test_check_existing_instance_running(self, tmp_path: Path) -> None:
        """Test instance check when another instance is running."""
        from src.exceptions import BotError

        app = Application(mode="paper")
        pid_file = tmp_path / ".bot.pid"

        with patch("src.main.PID_FILE", pid_file):
            # Write current PID to simulate running instance
            pid_file.write_text(str(os.getpid()))

            with pytest.raises(BotError, match="Another instance is already running"):
                app._check_existing_instance()

    def test_check_existing_instance_invalid_content(self, tmp_path: Path) -> None:
        """Test instance check with invalid PID file content."""
        app = Application(mode="paper")
        pid_file = tmp_path / ".bot.pid"

        with patch("src.main.PID_FILE", pid_file):
            # Write invalid content
            pid_file.write_text("not-a-pid")

            # Should remove invalid file and not raise error
            app._check_existing_instance()
            assert not pid_file.exists()


class TestApplicationSignalHandling:
    """Tests for signal handling."""

    @pytest.mark.asyncio
    async def test_handle_signal(self) -> None:
        """Test signal handling triggers shutdown."""
        app = Application(mode="paper")
        app._shutdown_event = asyncio.Event()

        # Event should not be set initially
        assert not app._shutdown_event.is_set()

        await app._handle_signal(signal.SIGTERM)

        # Event should be set after signal
        assert app._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_handle_signal_no_event(self) -> None:
        """Test signal handling when no shutdown event exists."""
        app = Application(mode="paper")
        app._shutdown_event = None

        # Should not raise an error
        await app._handle_signal(signal.SIGTERM)


class TestApplicationStart:
    """Tests for Application.start() method."""

    @pytest.mark.asyncio
    async def test_start_creates_shutdown_event(self) -> None:
        """Test that start creates a shutdown event."""
        app = Application(mode="paper")

        async def trigger_shutdown() -> None:
            await asyncio.sleep(0.01)
            if app._shutdown_event:
                app._shutdown_event.set()

        with (
            patch.object(app, "_check_existing_instance"),
            patch.object(app, "initialize", new_callable=AsyncMock),
            patch.object(app, "_write_pid_file"),
            patch.object(app, "start_dashboard", new_callable=AsyncMock),
            patch.object(app, "register_scheduled_tasks", new_callable=AsyncMock),
            patch.object(app, "run_initial_analysis", new_callable=AsyncMock),
            patch.object(app, "_setup_signal_handlers"),
            patch.object(app, "shutdown", new_callable=AsyncMock),
        ):
            # Set scheduler to avoid None check
            app.scheduler = MagicMock()
            app.scheduler.is_running = False

            # Start shutdown trigger in background
            shutdown_task = asyncio.create_task(trigger_shutdown())

            await app.start()

            assert app._shutdown_event is not None
            await shutdown_task

    @pytest.mark.asyncio
    async def test_start_calls_all_methods(self) -> None:
        """Test that start calls all initialization methods."""
        app = Application(mode="paper")

        async def trigger_shutdown() -> None:
            await asyncio.sleep(0.01)
            if app._shutdown_event:
                app._shutdown_event.set()

        with patch.object(app, "_check_existing_instance") as mock_check, \
             patch.object(app, "initialize", new_callable=AsyncMock) as mock_init, \
             patch.object(app, "_write_pid_file") as mock_write_pid, \
             patch.object(app, "start_dashboard", new_callable=AsyncMock) as mock_dash, \
             patch.object(app, "register_scheduled_tasks", new_callable=AsyncMock) as mock_reg, \
             patch.object(app, "run_initial_analysis", new_callable=AsyncMock) as mock_analysis, \
             patch.object(app, "_setup_signal_handlers") as mock_signals, \
             patch.object(app, "shutdown", new_callable=AsyncMock):
            app.scheduler = MagicMock()
            app.scheduler.is_running = False
            app.scheduler.start = MagicMock()

            shutdown_task = asyncio.create_task(trigger_shutdown())

            await app.start()

            mock_check.assert_called_once()
            mock_init.assert_called_once()
            mock_write_pid.assert_called_once()
            mock_dash.assert_called_once()
            mock_reg.assert_called_once()
            mock_signals.assert_called_once()
            app.scheduler.start.assert_called_once()

            await shutdown_task


class TestAsyncMain:
    """Tests for async_main function."""

    @pytest.mark.asyncio
    async def test_async_main_creates_application(self) -> None:
        """Test that async_main creates Application with correct args."""
        with (
            patch("src.main.parse_args") as mock_parse,
            patch("src.main.Application") as mock_app_class,
        ):
            mock_parse.return_value = MagicMock(mode="paper", config=None)
            mock_app = MagicMock()
            mock_app.start = AsyncMock()
            mock_app_class.return_value = mock_app

            await async_main()

            mock_app_class.assert_called_once_with(mode="paper", config_path=None)
            mock_app.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_main_sets_trading_mode_env(self) -> None:
        """Test that async_main sets TRADING_MODE environment variable."""
        original_mode = os.environ.get("TRADING_MODE")

        try:
            with (
                patch("src.main.parse_args") as mock_parse,
                patch("src.main.Application") as mock_app_class,
            ):
                mock_parse.return_value = MagicMock(mode="live", config=None)
                mock_app = MagicMock()
                mock_app.start = AsyncMock()
                mock_app_class.return_value = mock_app

                await async_main()

                assert os.environ.get("TRADING_MODE") == "live"
        finally:
            # Restore original value
            if original_mode is not None:
                os.environ["TRADING_MODE"] = original_mode
            elif "TRADING_MODE" in os.environ:
                del os.environ["TRADING_MODE"]


class TestMain:
    """Tests for main() function."""

    def test_main_calls_asyncio_run(self) -> None:
        """Test that main calls asyncio.run."""
        with patch("src.main.asyncio.run") as mock_run:
            main()
            mock_run.assert_called_once()

    def test_main_keyboard_interrupt(self) -> None:
        """Test main handles KeyboardInterrupt."""
        with (
            patch("src.main.asyncio.run", side_effect=KeyboardInterrupt),
            patch("src.main.logger") as mock_logger,
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 130
            mock_logger.info.assert_called()

    def test_main_bot_error(self) -> None:
        """Test main handles BotError."""
        from src.exceptions import BotError

        with (
            patch("src.main.asyncio.run", side_effect=BotError("Test error")),
            patch("src.main.logger") as mock_logger,
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            mock_logger.error.assert_called()

    def test_main_configuration_error(self) -> None:
        """Test main handles ConfigurationError."""
        from src.exceptions import ConfigurationError

        with (
            patch(
                "src.main.asyncio.run",
                side_effect=ConfigurationError("Config error"),
            ),
            patch("src.main.logger") as mock_logger,
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            mock_logger.error.assert_called()

    def test_main_unexpected_error(self) -> None:
        """Test main handles unexpected exceptions."""
        with (
            patch("src.main.asyncio.run", side_effect=RuntimeError("Unexpected")),
            patch("src.main.logger") as mock_logger,
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            mock_logger.critical.assert_called()


class TestIntegration:
    """Integration tests for the main module."""

    pytestmark = pytest.mark.integration

    @pytest.mark.asyncio
    async def test_full_startup_shutdown_cycle(self) -> None:
        """Test complete startup and shutdown cycle."""
        app = Application(mode="paper")

        async def trigger_shutdown_after_delay() -> None:
            await asyncio.sleep(0.05)
            if app._shutdown_event:
                app._shutdown_event.set()

        # Mock the dashboard task creation
        mock_server = MagicMock()
        mock_server.serve = AsyncMock()

        with patch.object(app, "_check_existing_instance"), \
             patch("src.main.init_db", new_callable=AsyncMock), \
             patch("src.core.state.ThreadSafeState.restore", new_callable=AsyncMock) as mock_restore, \
             patch("src.core.scheduler.Scheduler") as mock_scheduler_class, \
             patch("uvicorn.Server", return_value=mock_server), \
             patch("uvicorn.Config"), \
             patch("src.main.close_db", new_callable=AsyncMock):
            # Setup mocks
            mock_restore.return_value = MagicMock()
            mock_restore.return_value.persist = AsyncMock()
            mock_scheduler = MagicMock()
            mock_scheduler.is_running = False
            mock_scheduler_class.return_value = mock_scheduler

            # Start shutdown task
            shutdown_task = asyncio.create_task(trigger_shutdown_after_delay())

            # Run start (should complete after shutdown is triggered)
            await app.start()

            # Verify shutdown was called
            await shutdown_task

    @pytest.mark.asyncio
    async def test_graceful_shutdown_preserves_state(self) -> None:
        """Test that graceful shutdown preserves state."""
        app = Application(mode="paper")
        mock_state = MagicMock()
        mock_state.persist = AsyncMock()
        app.state = mock_state
        app.scheduler = None

        with patch("src.main.close_db", new_callable=AsyncMock):
            await app.shutdown()

            mock_state.persist.assert_called_once()
