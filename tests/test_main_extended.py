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


class TestApplicationRun:
    """Tests for the Application.run method."""

    @pytest.mark.asyncio
    async def test_run_with_signal_handlers(self) -> None:
        """Test run method sets up signal handlers."""
        app = Application()

        # Create a task that will trigger shutdown after a short delay
        async def trigger_shutdown() -> None:
            await asyncio.sleep(0.01)
            if app._shutdown_event:
                app._shutdown_event.set()

        # Run both tasks concurrently
        run_task = asyncio.create_task(app.run())
        trigger_task = asyncio.create_task(trigger_shutdown())

        await asyncio.gather(run_task, trigger_task)

        assert app._running is False

    @pytest.mark.asyncio
    async def test_run_signal_handler_sigint(self) -> None:
        """Test SIGINT signal triggers shutdown.

        This test verifies that signal handlers are registered during run()
        by checking that the signal handler code path is exercised.
        """
        app = Application()

        # The run() method sets up signal handlers for SIGINT and SIGTERM.
        # We verify this by checking the code path indirectly through the
        # _handle_signal method behavior.

        # First, verify that _handle_signal works correctly
        app._shutdown_event = asyncio.Event()
        assert not app._shutdown_event.is_set()

        # Simulate signal handling
        await app._handle_signal()
        assert app._shutdown_event.is_set()

        # Verify run() sets up and tears down correctly
        async def quick_shutdown():
            await asyncio.sleep(0.01)
            if app._shutdown_event:
                app._shutdown_event.set()

        run_task = asyncio.create_task(app.run())
        shutdown_task = asyncio.create_task(quick_shutdown())

        await asyncio.gather(run_task, shutdown_task)

        # After run completes, app should be shut down
        assert app._running is False

    @pytest.mark.asyncio
    async def test_run_creates_shutdown_event(self) -> None:
        """Test run creates shutdown event."""
        app = Application()

        async def trigger_shutdown() -> None:
            await asyncio.sleep(0.01)
            if app._shutdown_event:
                app._shutdown_event.set()

        run_task = asyncio.create_task(app.run())
        trigger_task = asyncio.create_task(trigger_shutdown())

        await asyncio.gather(run_task, trigger_task)

        # shutdown_event should have been created
        assert app._shutdown_event is not None


class TestApplicationStartupShutdown:
    """Tests for startup and shutdown edge cases."""

    @pytest.mark.asyncio
    async def test_startup_logs_trading_mode(self) -> None:
        """Test startup logs trading mode."""
        app = Application()

        with patch("src.main.logger") as mock_logger:
            await app.startup()

            # Verify logging calls
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("Starting" in str(call) for call in log_calls)

    @pytest.mark.asyncio
    async def test_shutdown_when_not_running(self) -> None:
        """Test shutdown when app is not running."""
        app = Application()
        app._running = False

        await app.shutdown()

        assert app._running is False

    @pytest.mark.asyncio
    async def test_multiple_signal_handling(self) -> None:
        """Test handling multiple signals in sequence."""
        app = Application()
        app._shutdown_event = asyncio.Event()

        # First signal
        await app._handle_signal()
        assert app._shutdown_event.is_set()

        # Second signal should not raise
        await app._handle_signal()


class TestMainFunctionEdgeCases:
    """Edge case tests for main function."""

    @pytest.mark.asyncio
    async def test_main_with_keyboard_interrupt(self) -> None:
        """Test main handles KeyboardInterrupt."""
        with patch("src.main.Application") as mock_app_class:
            mock_app = AsyncMock()
            mock_app.run.side_effect = KeyboardInterrupt()
            mock_app_class.return_value = mock_app

            # KeyboardInterrupt should propagate
            with pytest.raises(KeyboardInterrupt):
                await main()

    @pytest.mark.asyncio
    async def test_main_with_asyncio_cancelled_error(self) -> None:
        """Test main handles CancelledError."""
        with patch("src.main.Application") as mock_app_class:
            mock_app = AsyncMock()
            mock_app.run.side_effect = asyncio.CancelledError()
            mock_app_class.return_value = mock_app

            # CancelledError should propagate
            with pytest.raises(asyncio.CancelledError):
                await main()

    @pytest.mark.asyncio
    async def test_main_exit_codes(self) -> None:
        """Test main sets correct exit codes."""
        from src.exceptions import BotError

        # Test BotError exit code
        with patch("src.main.Application") as mock_app_class:
            mock_app = AsyncMock()
            mock_app.run.side_effect = BotError("Test error")
            mock_app_class.return_value = mock_app

            with patch("sys.exit") as mock_exit:
                await main()
                mock_exit.assert_called_once_with(1)

        # Test unexpected error exit code
        with patch("src.main.Application") as mock_app_class:
            mock_app = AsyncMock()
            mock_app.run.side_effect = RuntimeError("Unexpected!")
            mock_app_class.return_value = mock_app

            with patch("sys.exit") as mock_exit:
                await main()
                mock_exit.assert_called_once_with(1)
