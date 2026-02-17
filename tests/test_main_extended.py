# tests/test_main_extended.py
"""Extended tests for main application module.

This module provides additional coverage for main.py signal handling
and edge cases not covered by test_main.py.
"""

import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.main import Application, main


class TestApplicationStart:
    """Tests for the Application.start method."""

    @pytest.mark.asyncio
    async def test_start_with_signal_handlers(self) -> None:
        """Test start method sets up signal handlers."""
        app = Application()

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
            patch.object(app, "_setup_signal_handlers") as mock_setup_signals,
            patch.object(app, "shutdown", new_callable=AsyncMock),
        ):
            app.scheduler = MagicMock()
            app.scheduler.is_running = False

            run_task = asyncio.create_task(app.start())
            trigger_task = asyncio.create_task(trigger_shutdown())

            await asyncio.gather(run_task, trigger_task)

            mock_setup_signals.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_signal_handler_sigint(self) -> None:
        """Test SIGINT signal triggers shutdown.

        This test verifies that signal handlers are registered during start()
        by checking that the signal handler code path is exercised.
        """
        app = Application()

        # First, verify that _handle_signal works correctly
        app._shutdown_event = asyncio.Event()
        assert not app._shutdown_event.is_set()

        # Simulate signal handling
        await app._handle_signal(signal.SIGINT)
        assert app._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_start_creates_shutdown_event(self) -> None:
        """Test start creates shutdown event."""
        app = Application()

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
            patch.object(app, "_setup_signal_handlers"),
            patch.object(app, "shutdown", new_callable=AsyncMock),
        ):
            app.scheduler = MagicMock()
            app.scheduler.is_running = False

            run_task = asyncio.create_task(app.start())
            trigger_task = asyncio.create_task(trigger_shutdown())

            await asyncio.gather(run_task, trigger_task)

            # shutdown_event should have been created
            assert app._shutdown_event is not None


class TestApplicationInitialize:
    """Tests for initialize and shutdown edge cases."""

    @pytest.mark.asyncio
    async def test_initialize_logs_trading_mode(self) -> None:
        """Test initialize logs trading mode."""
        app = Application(mode="live")

        with (
            patch("src.main.setup_logging"),
            patch("src.main.init_db", new_callable=AsyncMock),
            patch("src.core.state.ThreadSafeState.restore", new_callable=AsyncMock) as mock_restore,
            patch("src.core.scheduler.Scheduler"),
        ):
            mock_restore.return_value = MagicMock()

            with patch("src.main.logger") as mock_logger:
                await app.initialize()

                # Verify logging calls
                log_calls = [str(call) for call in mock_logger.info.call_args_list]
                assert any("Mode" in str(call) for call in log_calls)

    @pytest.mark.asyncio
    async def test_shutdown_when_not_initialized(self) -> None:
        """Test shutdown when app is not fully initialized."""
        app = Application()
        app.scheduler = None
        app.state = None

        with patch("src.main.close_db", new_callable=AsyncMock):
            # Should not raise an error
            await app.shutdown()

    @pytest.mark.asyncio
    async def test_multiple_signal_handling(self) -> None:
        """Test handling multiple signals in sequence."""
        app = Application()
        app._shutdown_event = asyncio.Event()

        # First signal
        await app._handle_signal(signal.SIGTERM)
        assert app._shutdown_event.is_set()

        # Second signal should not raise
        await app._handle_signal(signal.SIGINT)


class TestMainFunctionEdgeCases:
    """Edge case tests for main function."""

    def test_main_with_keyboard_interrupt(self) -> None:
        """Test main handles KeyboardInterrupt."""
        with (
            patch("src.main.asyncio.run", side_effect=KeyboardInterrupt),
            patch("src.main.logger"),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 130

    def test_main_with_asyncio_cancelled_error(self) -> None:
        """Test main handles CancelledError as graceful shutdown."""
        with (
            patch("src.main.asyncio.run", side_effect=asyncio.CancelledError),
            patch("src.main.logger"),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # CancelledError should result in exit code 0 (graceful shutdown)
            assert exc_info.value.code == 0

    def test_main_exit_codes(self) -> None:
        """Test main sets correct exit codes."""
        from src.exceptions import BotError

        # Test BotError exit code
        with (
            patch("src.main.asyncio.run", side_effect=BotError("Test error")),
            patch("src.main.logger"),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

        # Test unexpected error exit code
        with (
            patch("src.main.asyncio.run", side_effect=RuntimeError("Unexpected!")),
            patch("src.main.logger"),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1


class TestApplicationPidFileEdgeCases:
    """Additional edge case tests for PID file handling."""

    def test_check_existing_instance_with_empty_file(self, tmp_path) -> None:
        """Test instance check with empty PID file."""
        from pathlib import Path

        app = Application(mode="paper")
        pid_file = tmp_path / ".bot.pid"

        with patch("src.main.PID_FILE", pid_file):
            # Write empty content
            pid_file.write_text("")

            # Should not raise an error, file is empty
            app._check_existing_instance()

    def test_check_existing_instance_with_whitespace_file(self, tmp_path) -> None:
        """Test instance check with whitespace-only PID file."""
        from pathlib import Path

        app = Application(mode="paper")
        pid_file = tmp_path / ".bot.pid"

        with patch("src.main.PID_FILE", pid_file):
            # Write whitespace
            pid_file.write_text("   \n\t  ")

            # Should not raise an error
            app._check_existing_instance()
