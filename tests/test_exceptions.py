"""Tests for custom exception hierarchy.

This module tests the custom exceptions defined in src/exceptions.py.
"""

import pytest

from src.exceptions import (
    BotError,
    ConfigurationError,
    NetworkError,
    TradingError,
    ValidationError,
    RateLimitError,
    TimeoutError,
    InsufficientFundsError,
    RiskLimitExceededError,
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


class TestTimeoutError:
    """Tests for TimeoutError class."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = TimeoutError()
        assert "timed out" in str(error).lower()

    def test_with_timeout_seconds(self) -> None:
        """Test error with timeout seconds."""
        error = TimeoutError(timeout_seconds=30.0)
        assert "30" in str(error)
        assert error.timeout_seconds == 30.0

    def test_inherits_from_network_error(self) -> None:
        """Test TimeoutError inherits from NetworkError."""
        error = TimeoutError(endpoint="/api/analyze")
        assert error.endpoint == "/api/analyze"


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
