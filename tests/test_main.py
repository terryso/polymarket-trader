"""Tests for main application module.

This module tests the Application class and main entry point.
"""

import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.main import Application, main


class TestApplication:
    """Tests for the Application class."""

    def test_init(self) -> None:
        """Test Application initialization."""
        app = Application()

        assert app._shutdown_event is None
        assert app._running is False

    @pytest.mark.asyncio
    async def test_startup(self) -> None:
        """Test application startup sets running flag."""
        app = Application()

        await app.startup()

        assert app._running is True

    @pytest.mark.asyncio
    async def test_shutdown(self) -> None:
        """Test application shutdown clears running flag."""
        app = Application()
        app._running = True

        await app.shutdown()

        assert app._running is False

    @pytest.mark.asyncio
    async def test_handle_signal_sets_shutdown_event(self) -> None:
        """Test signal handler sets shutdown event."""
        app = Application()
        app._shutdown_event = asyncio.Event()

        await app._handle_signal()

        assert app._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_handle_signal_without_event(self) -> None:
        """Test signal handler works when no event exists."""
        app = Application()

        # Should not raise an error
        await app._handle_signal()

    @pytest.mark.asyncio
    async def test_run_flow_integration(self) -> None:
        """Test that run orchestrates startup and shutdown correctly."""
        # This test verifies the flow without actually running the event loop
        app = Application()

        # Test startup changes state
        await app.startup()
        assert app._running is True

        # Test shutdown changes state
        await app.shutdown()
        assert app._running is False


class TestMainFunction:
    """Tests for the main entry point function."""

    @pytest.mark.asyncio
    async def test_main_creates_application(self) -> None:
        """Test main function creates and runs Application."""
        with patch("src.main.Application") as mock_app_class:
            mock_app = AsyncMock()
            mock_app_class.return_value = mock_app

            await main()

            mock_app_class.assert_called_once()
            mock_app.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_handles_bot_error(self) -> None:
        """Test main function handles BotError exceptions."""
        from src.exceptions import BotError

        with patch("src.main.Application") as mock_app_class:
            mock_app = AsyncMock()
            mock_app.run.side_effect = BotError("Test error")
            mock_app_class.return_value = mock_app

            with patch("sys.exit") as mock_exit:
                await main()
                mock_exit.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_main_handles_unexpected_error(self) -> None:
        """Test main function handles unexpected exceptions."""
        with patch("src.main.Application") as mock_app_class:
            mock_app = AsyncMock()
            mock_app.run.side_effect = RuntimeError("Unexpected!")
            mock_app_class.return_value = mock_app

            with patch("sys.exit") as mock_exit:
                await main()
                mock_exit.assert_called_once_with(1)
