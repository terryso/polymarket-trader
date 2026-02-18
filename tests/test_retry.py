"""Tests for the retry decorator module.

This module tests the retry decorator functionality including:
- RetryConfig configuration
- Synchronous function retry
- Asynchronous function retry
- Exponential backoff delay calculation
- Logging of retry attempts
"""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.exceptions import NetworkError, RateLimitError, RequestTimeoutError
from src.utils.retry import RetryConfig, retry


class TestRetryConfig:
    """Test RetryConfig configuration class."""

    def test_default_values(self) -> None:
        """Test that default values match specification."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_backoff is True
        assert config.exceptions == (Exception,)
        assert config.jitter == 0.0

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=60.0,
            exponential_backoff=False,
            exceptions=(NetworkError, RateLimitError),
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 60.0
        assert config.exponential_backoff is False
        assert config.exceptions == (NetworkError, RateLimitError)

    def test_calculate_delay_linear(self) -> None:
        """Test linear delay calculation (no exponential backoff)."""
        config = RetryConfig(base_delay=1.0, exponential_backoff=False)
        assert config.calculate_delay(0) == 1.0
        assert config.calculate_delay(1) == 1.0
        assert config.calculate_delay(2) == 1.0

    def test_calculate_delay_exponential(self) -> None:
        """Test exponential backoff delay calculation.

        Expected delays based on formula: delay = base_delay * (2 ** attempt)
        - attempt 0: 1 * 2^0 = 1s
        - attempt 1: 1 * 2^1 = 2s
        - attempt 2: 1 * 2^2 = 4s
        """
        config = RetryConfig(base_delay=1.0, exponential_backoff=True)
        assert config.calculate_delay(0) == 1.0  # 1 * 2^0 = 1
        assert config.calculate_delay(1) == 2.0  # 1 * 2^1 = 2
        assert config.calculate_delay(2) == 4.0  # 1 * 2^2 = 4

    def test_calculate_delay_respects_max(self) -> None:
        """Test that delay is capped at max_delay."""
        config = RetryConfig(base_delay=10.0, max_delay=30.0, exponential_backoff=True)
        # 10 * 2^0 = 10
        assert config.calculate_delay(0) == 10.0
        # 10 * 2^1 = 20
        assert config.calculate_delay(1) == 20.0
        # 10 * 2^2 = 40, capped at 30
        assert config.calculate_delay(2) == 30.0
        # 10 * 2^3 = 80, capped at 30
        assert config.calculate_delay(3) == 30.0

    def test_calculate_delay_with_jitter(self) -> None:
        """Test that jitter adds randomization to delay."""
        config = RetryConfig(base_delay=1.0, jitter=0.5)

        # With jitter=0.5, delay should be between 0.5 and 1.5
        delays = [config.calculate_delay(0) for _ in range(100)]
        assert all(0.5 <= d <= 1.5 for d in delays), f"Delays out of range: {delays}"
        # Should have some variation (not all exactly 1.0)
        assert len(set(delays)) > 1, "Jitter should produce varying delays"


class TestRetryConfigValidation:
    """Test RetryConfig parameter validation."""

    def test_max_attempts_zero_raises_error(self) -> None:
        """Test that max_attempts=0 raises ValueError."""
        with pytest.raises(ValueError, match="max_attempts must be >= 1"):
            RetryConfig(max_attempts=0)

    def test_max_attempts_negative_raises_error(self) -> None:
        """Test that negative max_attempts raises ValueError."""
        with pytest.raises(ValueError, match="max_attempts must be >= 1"):
            RetryConfig(max_attempts=-1)

    def test_base_delay_negative_raises_error(self) -> None:
        """Test that negative base_delay raises ValueError."""
        with pytest.raises(ValueError, match="base_delay must be >= 0"):
            RetryConfig(base_delay=-1.0)

    def test_max_delay_negative_raises_error(self) -> None:
        """Test that negative max_delay raises ValueError."""
        with pytest.raises(ValueError, match="max_delay must be >= 0"):
            RetryConfig(max_delay=-1.0)

    def test_max_delay_less_than_base_delay_raises_error(self) -> None:
        """Test that max_delay < base_delay raises ValueError."""
        with pytest.raises(ValueError, match="max_delay .* must be >= base_delay"):
            RetryConfig(base_delay=10.0, max_delay=5.0)

    def test_jitter_out_of_range_raises_error(self) -> None:
        """Test that jitter outside 0.0-1.0 raises ValueError."""
        with pytest.raises(ValueError, match="jitter must be between 0.0 and 1.0"):
            RetryConfig(jitter=-0.1)
        with pytest.raises(ValueError, match="jitter must be between 0.0 and 1.0"):
            RetryConfig(jitter=1.1)

    def test_retry_decorator_validates_params(self) -> None:
        """Test that retry decorator validates parameters."""

        with pytest.raises(ValueError, match="max_attempts must be >= 1"):

            @retry(max_attempts=0)
            def func() -> str:
                return "test"

    def test_retry_decorator_negative_delay_raises_error(self) -> None:
        """Test that retry decorator validates base_delay."""

        with pytest.raises(ValueError, match="base_delay must be >= 0"):

            @retry(base_delay=-1.0)
            def func() -> str:
                return "test"


class TestRetrySync:
    """Test synchronous function retry."""

    def test_no_retry_on_success(self) -> None:
        """Test that successful function is not retried."""
        call_count = 0

        @retry()
        def success_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_exception(self) -> None:
        """Test that function is retried on configured exception."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, exceptions=(NetworkError,))
        def failing_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Connection failed")
            return "success"

        result = failing_func()
        assert result == "success"
        assert call_count == 3

    def test_max_attempts_reached(self) -> None:
        """Test that exception is raised after max attempts."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, exceptions=(NetworkError,))
        def always_failing() -> str:
            nonlocal call_count
            call_count += 1
            raise NetworkError("Always fails")

        with pytest.raises(NetworkError) as exc_info:
            always_failing()

        assert call_count == 3
        assert "Always fails" in str(exc_info.value)

    def test_only_configured_exceptions_trigger_retry(self) -> None:
        """Test that non-configured exceptions are not retried."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, exceptions=(NetworkError,))
        def wrong_exception() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Not a NetworkError")

        with pytest.raises(ValueError):
            wrong_exception()

        # Should not retry for non-configured exception
        assert call_count == 1

    def test_success_after_retry(self) -> None:
        """Test successful return after retries."""
        call_count = 0

        @retry(max_attempts=5, base_delay=0.01, exceptions=(NetworkError,))
        def eventual_success() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise NetworkError(f"Attempt {call_count} failed")
            return "finally success"

        result = eventual_success()
        assert result == "finally success"
        assert call_count == 4

    def test_retry_with_multiple_exception_types(self) -> None:
        """Test retry with multiple configured exception types."""
        call_count = 0

        @retry(
            max_attempts=5,
            base_delay=0.01,
            exceptions=(NetworkError, RateLimitError, RequestTimeoutError),
        )
        def various_failures() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise NetworkError("Network failed")
            if call_count == 2:
                raise RateLimitError("Rate limited")
            if call_count == 3:
                raise RequestTimeoutError("Timeout")
            return "success"

        result = various_failures()
        assert result == "success"
        assert call_count == 4


class TestRetryAsync:
    """Test asynchronous function retry."""

    @pytest.mark.asyncio
    async def test_no_retry_on_success(self) -> None:
        """Test that successful async function is not retried."""
        call_count = 0

        @retry()
        async def success_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = await success_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_exception(self) -> None:
        """Test that async function is retried on configured exception."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, exceptions=(NetworkError,))
        async def failing_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Connection failed")
            return "success"

        result = await failing_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_attempts_reached(self) -> None:
        """Test that exception is raised after max attempts for async."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, exceptions=(NetworkError,))
        async def always_failing() -> str:
            nonlocal call_count
            call_count += 1
            raise NetworkError("Always fails")

        with pytest.raises(NetworkError) as exc_info:
            await always_failing()

        assert call_count == 3
        assert "Always fails" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_success_after_retry(self) -> None:
        """Test successful return after retries for async."""
        call_count = 0

        @retry(max_attempts=5, base_delay=0.01, exceptions=(NetworkError,))
        async def eventual_success() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise NetworkError(f"Attempt {call_count} failed")
            return "finally success"

        result = await eventual_success()
        assert result == "finally success"
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_only_configured_exceptions_trigger_retry(self) -> None:
        """Test that non-configured exceptions are not retried for async."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, exceptions=(NetworkError,))
        async def wrong_exception() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Not a NetworkError")

        with pytest.raises(ValueError):
            await wrong_exception()

        assert call_count == 1


class TestRetryLogging:
    """Test retry logging behavior."""

    def test_logs_retry_attempt(self, capfd: pytest.CaptureFixture) -> None:
        """Test that retry attempts are logged with emoji."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, exceptions=(NetworkError,))
        def failing_once() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise NetworkError("First failure")
            return "success"

        result = failing_once()
        assert result == "success"

        # Check that retry was logged with emoji (captured from stderr)
        captured = capfd.readouterr()
        assert "🔄" in captured.err
        assert "Retrying" in captured.err

    def test_logs_success_after_retry(self, capfd: pytest.CaptureFixture) -> None:
        """Test that success after retry is logged with emoji."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, exceptions=(NetworkError,))
        def failing_once() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise NetworkError("First failure")
            return "success"

        result = failing_once()
        assert result == "success"

        # Check that success was logged (captured from stderr)
        captured = capfd.readouterr()
        assert "✅" in captured.err

    def test_logs_final_failure_emoji_format(self) -> None:
        """Test that final failure uses correct emoji (💥 not double emoji)."""
        # Verify the emoji constants are correct
        from src.utils.retry import RETRY_EMOJIS

        assert RETRY_EMOJIS["failure"] == "💥"
        assert RETRY_EMOJIS["retry"] == "🔄"
        assert RETRY_EMOJIS["success"] == "✅"

    def test_logs_final_failure_behavior(self) -> None:
        """Test that final failure raises after all retries exhausted."""
        call_count = 0

        @retry(max_attempts=2, base_delay=0.01, exceptions=(NetworkError,))
        def always_failing() -> str:
            nonlocal call_count
            call_count += 1
            raise NetworkError(f"Failure #{call_count}")

        with pytest.raises(NetworkError) as exc_info:
            always_failing()

        # Should have tried exactly 2 times
        assert call_count == 2
        assert "Failure #2" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_logs_async_retry(self, capfd: pytest.CaptureFixture) -> None:
        """Test that async retry attempts are logged."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, exceptions=(NetworkError,))
        async def failing_once() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise NetworkError("First failure")
            return "success"

        result = await failing_once()
        assert result == "success"

        # Check that retry was logged (captured from stderr)
        captured = capfd.readouterr()
        assert "🔄" in captured.err


class TestRetryPreservesFunctionMetadata:
    """Test that retry decorator preserves function metadata."""

    def test_preserves_function_name(self) -> None:
        """Test that decorated function preserves __name__."""

        @retry()
        def my_function() -> str:
            """My docstring."""
            return "result"

        assert my_function.__name__ == "my_function"

    def test_preserves_docstring(self) -> None:
        """Test that decorated function preserves __doc__."""

        @retry()
        def my_function() -> str:
            """My docstring."""
            return "result"

        assert my_function.__doc__ == "My docstring."

    @pytest.mark.asyncio
    async def test_preserves_async_function_name(self) -> None:
        """Test that decorated async function preserves __name__."""

        @retry()
        async def my_async_function() -> str:
            """My async docstring."""
            return "result"

        assert my_async_function.__name__ == "my_async_function"
