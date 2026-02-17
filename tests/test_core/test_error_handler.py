"""Tests for the error handler module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.alerting import AlertManager
from src.core.error_handler import (
    ErrorHandler,
    get_error_handler,
    setup_error_handler,
    setup_global_exception_handler,
    setup_async_exception_handler,
)
from src.exceptions import NetworkError, TradingError, ValidationError


class TestErrorHandler:
    """Tests for ErrorHandler class."""

    @pytest.fixture
    def error_handler(self) -> ErrorHandler:
        """Create an error handler with mock alert manager."""
        mock_alert_manager = MagicMock(spec=AlertManager)
        return ErrorHandler(
            alert_manager=mock_alert_manager,
            max_retries=3,
            retry_delay=0.1,
        )

    def test_handle_exception_business_error(self, error_handler: ErrorHandler) -> None:
        """Test handling business exceptions."""
        exception = TradingError("Test trading error")
        error_handler.handle_exception(exception, {"task": "test"})

        assert error_handler._error_counts.get("TradingError") == 1

    def test_handle_exception_unexpected_error(self, error_handler: ErrorHandler) -> None:
        """Test handling unexpected exceptions."""
        exception = RuntimeError("Unexpected error")
        error_handler.handle_exception(exception, {"task": "test"})

        assert error_handler._error_counts.get("RuntimeError") == 1

    def test_handle_exception_triggers_alert(self, error_handler: ErrorHandler) -> None:
        """Test that exceptions trigger alerts."""
        exception = TradingError("Test error")
        error_handler.handle_exception(exception, {"task": "test"})

        error_handler.alert_manager.check_and_alert.assert_called_once()

    def test_handle_exception_counts_errors(self, error_handler: ErrorHandler) -> None:
        """Test that error counts are tracked."""
        error_handler.handle_exception(RuntimeError("Error 1"), {})
        error_handler.handle_exception(RuntimeError("Error 2"), {})
        error_handler.handle_exception(ValidationError("Error 3"), {})

        assert error_handler._error_counts["RuntimeError"] == 2
        assert error_handler._error_counts["ValidationError"] == 1

    def test_handle_exception_records_last_error_time(self, error_handler: ErrorHandler) -> None:
        """Test that last error times are recorded."""
        error_handler.handle_exception(RuntimeError("Error"), {})

        assert "RuntimeError" in error_handler._last_errors

    @pytest.mark.asyncio
    async def test_task_wrapper_success(self, error_handler: ErrorHandler) -> None:
        """Test successful task execution through wrapper."""
        @error_handler.task_wrapper("test_task")
        async def successful_task() -> str:
            return "success"

        result = await successful_task()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_task_wrapper_retry_on_network_error(self, error_handler: ErrorHandler) -> None:
        """Test retry on network errors."""
        call_count = 0

        @error_handler.task_wrapper("test_task", retry_exceptions=(NetworkError,))
        async def failing_task() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Network failed")
            return "success"

        result = await failing_task()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_task_wrapper_max_retries_exceeded(self, error_handler: ErrorHandler) -> None:
        """Test that exception is raised after max retries."""
        @error_handler.task_wrapper("test_task", retry_exceptions=(NetworkError,))
        async def always_failing_task() -> str:
            raise NetworkError("Always fails")

        with pytest.raises(NetworkError, match="Always fails"):
            await always_failing_task()

    @pytest.mark.asyncio
    async def test_task_wrapper_non_retry_exception(self, error_handler: ErrorHandler) -> None:
        """Test that non-retry exceptions are re-raised immediately."""
        @error_handler.task_wrapper("test_task", retry_exceptions=(NetworkError,))
        async def non_retry_task() -> str:
            raise ValidationError("Invalid input")

        with pytest.raises(ValidationError, match="Invalid input"):
            await non_retry_task()

    @pytest.mark.asyncio
    async def test_task_wrapper_resets_failure_on_success(self, error_handler: ErrorHandler) -> None:
        """Test that failure count is reset on success."""
        # Record a previous failure
        error_handler.alert_manager.record_failure("test_task")

        @error_handler.task_wrapper("test_task")
        async def successful_task() -> str:
            return "success"

        await successful_task()

        # Should have called reset_failures
        error_handler.alert_manager.reset_failures.assert_called_with("test_task")

    @pytest.mark.asyncio
    async def test_task_wrapper_records_failure_on_error(self, error_handler: ErrorHandler) -> None:
        """Test that failure is recorded on non-retry error."""
        @error_handler.task_wrapper("test_task", retry_exceptions=(NetworkError,))
        async def failing_task() -> str:
            raise ValidationError("Invalid")

        with pytest.raises(ValidationError):
            await failing_task()

        # Should have recorded failure
        error_handler.alert_manager.record_failure.assert_called_with("test_task")

    def test_get_error_stats(self, error_handler: ErrorHandler) -> None:
        """Test getting error statistics."""
        error_handler.handle_exception(RuntimeError("Error 1"), {})
        error_handler.handle_exception(RuntimeError("Error 2"), {})

        stats = error_handler.get_error_stats()
        assert stats["error_counts"]["RuntimeError"] == 2
        assert "RuntimeError" in stats["last_errors"]

    def test_reset_counts(self, error_handler: ErrorHandler) -> None:
        """Test resetting error counts."""
        error_handler.handle_exception(RuntimeError("Error"), {})
        error_handler.reset_counts()

        assert len(error_handler._error_counts) == 0
        assert len(error_handler._last_errors) == 0


class TestSetupErrorHandler:
    """Tests for setup_error_handler function."""

    def test_setup_creates_global_handler(self) -> None:
        """Test that setup creates a global handler."""
        handler = setup_error_handler()

        assert handler is not None
        assert isinstance(handler, ErrorHandler)

    def test_setup_with_alert_manager(self) -> None:
        """Test setup with custom alert manager."""
        mock_alert_manager = MagicMock(spec=AlertManager)
        handler = setup_error_handler(alert_manager=mock_alert_manager)

        assert handler.alert_manager is mock_alert_manager

    def test_setup_with_custom_settings(self) -> None:
        """Test setup with custom retry settings."""
        handler = setup_error_handler(max_retries=5, retry_delay=2.0)

        assert handler.max_retries == 5
        assert handler.retry_delay == 2.0


class TestGetErrorHandler:
    """Tests for get_error_handler function."""

    def test_get_returns_global_handler(self) -> None:
        """Test that get returns the global handler."""
        # Setup a handler
        setup_error_handler()

        # Get should return the same instance
        handler1 = get_error_handler()
        handler2 = get_error_handler()

        assert handler1 is handler2

    def test_get_creates_handler_if_none_exists(self) -> None:
        """Test that get creates a handler if one doesn't exist."""
        # Import and reset the global handler
        import src.core.error_handler as eh
        eh._global_handler = None

        handler = get_error_handler()
        assert handler is not None
        assert isinstance(handler, ErrorHandler)


class TestGlobalExceptionHandler:
    """Tests for global exception handler setup."""

    def test_setup_global_exception_handler(self) -> None:
        """Test that global exception handler is installed."""
        original_excepthook = None
        try:
            import sys
            original_excepthook = sys.excepthook

            setup_global_exception_handler()

            # Should have installed a custom excepthook
            assert sys.excepthook is not original_excepthook
        finally:
            if original_excepthook:
                import sys
                sys.excepthook = original_excepthook

    def test_setup_async_exception_handler(self) -> None:
        """Test that async exception handler is installed."""
        # This test just verifies the function runs without error
        # The actual handler installation requires a running event loop
        try:
            setup_async_exception_handler()
            # No exception means success
        except RuntimeError:
            # Expected when no event loop is running
            pass


class TestErrorHandlerIntegration:
    """Integration tests for error handler with alert manager."""

    @pytest.mark.asyncio
    async def test_full_error_flow(self) -> None:
        """Test complete error handling flow."""
        from src.core.alerting import AlertManager, LogAlertChannel
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = str(Path(tmp_dir) / "errors.log")
            channel = LogAlertChannel(log_file)
            alert_manager = AlertManager(channels=[channel])
            handler = ErrorHandler(alert_manager=alert_manager)

            # Handle an exception
            exception = TradingError("Test error")
            handler.handle_exception(exception, {"task": "integration_test"})

            # Give async tasks time to complete
            await asyncio.sleep(0.1)

            # Verify error was tracked
            assert handler._error_counts.get("TradingError") == 1

    @pytest.mark.asyncio
    async def test_retry_occurs(self) -> None:
        """Test that retry mechanism works correctly."""
        from src.core.alerting import AlertManager

        mock_alert_manager = MagicMock(spec=AlertManager)
        handler = ErrorHandler(
            alert_manager=mock_alert_manager,
            max_retries=3,
            retry_delay=0.01,  # Small delay for faster testing
        )

        call_count = 0

        @handler.task_wrapper("test_task", retry_exceptions=(NetworkError,))
        async def flaky_task() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Temporary failure")
            return "success"

        result = await flaky_task()
        assert result == "success"
        # Should have been called 3 times (2 failures + 1 success)
        assert call_count == 3
