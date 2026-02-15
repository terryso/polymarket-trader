"""Tests for custom exception hierarchy.

This module tests the custom exceptions defined in src/exceptions.py.
"""

import pytest

from src.exceptions import TimeoutError  # Backward compatibility alias
from src.exceptions import (
    BotError,
    ConfigurationError,
    InsufficientFundsError,
    NetworkError,
    RateLimitError,
    RequestTimeoutError,
    RiskLimitExceededError,
    TradingError,
    ValidationError,
)


class TestBotError:
    """Tests for base BotError class."""

    def test_basic_error(self) -> None:
        """Test basic error creation."""
        error = BotError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.original_exception is None
        assert error.context == {}

    def test_error_with_original_exception(self) -> None:
        """Test error with original exception."""
        original = ValueError("Original error")
        error = BotError("Test error", original_exception=original)
        assert "Test error" in str(error)
        assert "Original error" in str(error)
        assert error.original_exception is original

    def test_error_with_context(self) -> None:
        """Test error with context."""
        error = BotError("Test error", user_id=123, action="trade")
        assert error.context == {"user_id": 123, "action": "trade"}

    def test_str_without_original(self) -> None:
        """Test string representation without original exception."""
        error = BotError("Simple error")
        assert str(error) == "Simple error"


class TestConfigurationError:
    """Tests for ConfigurationError class."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = ConfigurationError()
        assert "Configuration error" in str(error)

    def test_with_config_key(self) -> None:
        """Test error with config key."""
        error = ConfigurationError(config_key="API_KEY")
        assert "API_KEY" in str(error)
        assert error.config_key == "API_KEY"

    def test_custom_message_with_key(self) -> None:
        """Test custom message with config key."""
        error = ConfigurationError(message="Invalid config", config_key="TIMEOUT")
        assert "Invalid config" in str(error)
        assert "TIMEOUT" in str(error)

    def test_with_original_exception(self) -> None:
        """Test error with original exception."""
        original = ValueError("Missing env var")
        error = ConfigurationError(
            message="Config load failed",
            config_key="API_KEY",
            original_exception=original,
        )
        assert "Config load failed" in str(error)
        assert "API_KEY" in str(error)
        assert "Missing env var" in str(error)
        assert error.original_exception is original


class TestNetworkError:
    """Tests for NetworkError class."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = NetworkError()
        assert "Network error" in str(error)

    def test_with_endpoint(self) -> None:
        """Test error with endpoint."""
        error = NetworkError(endpoint="/api/trade")
        assert "/api/trade" in str(error)
        assert error.endpoint == "/api/trade"

    def test_with_status_code(self) -> None:
        """Test error with status code."""
        error = NetworkError(status_code=404)
        assert "404" in str(error)
        assert error.status_code == 404

    def test_with_all_details(self) -> None:
        """Test error with all details."""
        original = ConnectionError("Connection failed")
        error = NetworkError(
            message="API failed",
            endpoint="/api/markets",
            status_code=500,
            original_exception=original,
        )
        assert "API failed" in str(error)
        assert "/api/markets" in str(error)
        assert "500" in str(error)
        assert error.endpoint == "/api/markets"
        assert error.status_code == 500


class TestTradingError:
    """Tests for TradingError class."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = TradingError()
        assert "Trading error" in str(error)

    def test_with_market_id(self) -> None:
        """Test error with market ID."""
        error = TradingError(market_id="market-123")
        assert "market-123" in str(error)
        assert error.market_id == "market-123"

    def test_with_trade_type(self) -> None:
        """Test error with trade type."""
        error = TradingError(trade_type="BUY_YES")
        assert "BUY_YES" in str(error)
        assert error.trade_type == "BUY_YES"

    def test_with_all_details(self) -> None:
        """Test error with all details."""
        error = TradingError(
            message="Order failed",
            market_id="market-456",
            trade_type="SELL_NO",
        )
        assert "Order failed" in str(error)
        assert "market-456" in str(error)
        assert "SELL_NO" in str(error)


class TestValidationError:
    """Tests for ValidationError class."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = ValidationError()
        assert "Validation error" in str(error)

    def test_with_field(self) -> None:
        """Test error with field name."""
        error = ValidationError(field="amount")
        assert "amount" in str(error)
        assert error.field == "amount"

    def test_with_field_and_value(self) -> None:
        """Test error with field and invalid value."""
        error = ValidationError(
            message="Invalid value",
            field="price",
            value=-100,
        )
        assert "Invalid value" in str(error)
        assert "price" in str(error)
        assert error.field == "price"
        assert error.value == -100

    def test_with_original_exception(self) -> None:
        """Test error with original exception."""
        original = TypeError("Expected string")
        error = ValidationError(
            message="Type check failed",
            field="name",
            value=123,
            original_exception=original,
        )
        assert "Type check failed" in str(error)
        assert "name" in str(error)
        assert "Expected string" in str(error)
        assert error.original_exception is original


class TestRateLimitError:
    """Tests for RateLimitError class."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = RateLimitError()
        assert "Rate limit" in str(error)

    def test_with_retry_after(self) -> None:
        """Test error with retry after."""
        error = RateLimitError(retry_after=60)
        assert "60" in str(error)
        assert error.retry_after == 60

    def test_inherits_from_network_error(self) -> None:
        """Test RateLimitError inherits from NetworkError."""
        error = RateLimitError(endpoint="/api/trade")
        assert error.endpoint == "/api/trade"

    def test_with_original_exception(self) -> None:
        """Test error with original exception."""
        original = ConnectionError("Too many requests")
        error = RateLimitError(
            message="API rate limited",
            retry_after=120,
            endpoint="/api/markets",
            original_exception=original,
        )
        assert "API rate limited" in str(error)
        assert "120" in str(error)
        assert "Too many requests" in str(error)
        assert error.retry_after == 120
        assert error.original_exception is original


class TestRequestTimeoutError:
    """Tests for RequestTimeoutError class."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = RequestTimeoutError()
        assert "timed out" in str(error).lower()

    def test_with_timeout_seconds(self) -> None:
        """Test error with timeout seconds."""
        error = RequestTimeoutError(timeout_seconds=30.0)
        assert "30" in str(error)
        assert error.timeout_seconds == 30.0

    def test_inherits_from_network_error(self) -> None:
        """Test RequestTimeoutError inherits from NetworkError."""
        error = RequestTimeoutError(endpoint="/api/analyze")
        assert error.endpoint == "/api/analyze"

    def test_with_original_exception(self) -> None:
        """Test error with original exception."""
        original = TimeoutError("inner timeout")
        error = RequestTimeoutError(
            message="API timeout",
            timeout_seconds=30.0,
            original_exception=original,
        )
        assert "API timeout" in str(error)
        assert "inner timeout" in str(error)
        assert error.timeout_seconds == 30.0
        assert error.original_exception is original

    def test_backward_compatibility_alias(self) -> None:
        """Test TimeoutError is an alias for RequestTimeoutError."""
        # TimeoutError should be the same class as RequestTimeoutError
        assert TimeoutError is RequestTimeoutError
        # Should be able to create via alias
        error = TimeoutError(timeout_seconds=10.0)
        assert isinstance(error, RequestTimeoutError)
        assert error.timeout_seconds == 10.0


class TestInsufficientFundsError:
    """Tests for InsufficientFundsError class."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = InsufficientFundsError()
        assert "Insufficient funds" in str(error)

    def test_with_amounts(self) -> None:
        """Test error with required and available amounts."""
        error = InsufficientFundsError(required=100.0, available=50.0)
        assert "100" in str(error)
        assert "50" in str(error)
        assert error.required == 100.0
        assert error.available == 50.0

    def test_inherits_from_trading_error(self) -> None:
        """Test InsufficientFundsError inherits from TradingError."""
        error = InsufficientFundsError(market_id="market-789")
        assert error.market_id == "market-789"

    def test_with_original_exception(self) -> None:
        """Test error with original exception."""
        original = ValueError("Balance check failed")
        error = InsufficientFundsError(
            message="Cannot place order",
            required=500.0,
            available=200.0,
            market_id="market-999",
            original_exception=original,
        )
        assert "Cannot place order" in str(error)
        assert "500" in str(error)
        assert "200" in str(error)
        assert "Balance check failed" in str(error)
        assert error.required == 500.0
        assert error.available == 200.0
        assert error.original_exception is original


class TestRiskLimitExceededError:
    """Tests for RiskLimitExceededError class."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = RiskLimitExceededError()
        assert "Risk limit" in str(error)

    def test_with_limit_details(self) -> None:
        """Test error with limit details."""
        error = RiskLimitExceededError(
            limit_type="daily_loss",
            current=0.35,
            limit=0.30,
        )
        assert "daily_loss" in str(error)
        assert error.limit_type == "daily_loss"
        assert error.current == 0.35
        assert error.limit == 0.30

    def test_inherits_from_trading_error(self) -> None:
        """Test RiskLimitExceededError inherits from TradingError."""
        error = RiskLimitExceededError(market_id="market-101")
        assert error.market_id == "market-101"

    def test_with_original_exception(self) -> None:
        """Test error with original exception."""
        original = RuntimeError("Risk check service unavailable")
        error = RiskLimitExceededError(
            message="Position limit breach",
            limit_type="max_position",
            current=0.50,
            limit=0.30,
            market_id="market-202",
            original_exception=original,
        )
        assert "Position limit breach" in str(error)
        assert "max_position" in str(error)
        assert "Risk check service unavailable" in str(error)
        assert error.limit_type == "max_position"
        assert error.current == 0.50
        assert error.limit == 0.30
        assert error.original_exception is original
