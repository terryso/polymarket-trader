"""Custom exception hierarchy for the Polymarket Trader application.

This module defines custom exceptions used throughout the application
following the architecture specification.
"""

from typing import Any, Optional


class BotError(Exception):
    """Base exception for all Polymarket Trader errors."""

    def __init__(
        self,
        message: str,
        original_exception: Optional[Exception] = None,
        **context: Any
    ) -> None:
        """Initialize the exception.

        Args:
            message: Error message
            original_exception: The original exception that caused this error
            **context: Additional context information
        """
        super().__init__(message)
        self.message = message
        self.original_exception = original_exception
        self.context = context

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.original_exception:
            return f"{self.message} (caused by: {self.original_exception})"
        return self.message


class ConfigurationError(BotError):
    """Raised when there is a configuration error."""

    def __init__(
        self,
        message: str = "Configuration error",
        config_key: Optional[str] = None,
        **context: Any
    ) -> None:
        """Initialize configuration error.

        Args:
            message: Error message
            config_key: The configuration key that caused the error
            **context: Additional context information
        """
        if config_key:
            message = f"{message} (key: {config_key})"
        super().__init__(message, **context)
        self.config_key = config_key


class NetworkError(BotError):
    """Raised when there is a network/API communication error."""

    def __init__(
        self,
        message: str = "Network error",
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        original_exception: Optional[Exception] = None,
        **context: Any
    ) -> None:
        """Initialize network error.

        Args:
            message: Error message
            endpoint: The API endpoint that failed
            status_code: HTTP status code if applicable
            original_exception: The original exception
            **context: Additional context information
        """
        details = []
        if endpoint:
            details.append(f"endpoint={endpoint}")
        if status_code:
            details.append(f"status={status_code}")
        if details:
            message = f"{message} ({', '.join(details)})"
        super().__init__(message, original_exception, **context)
        self.endpoint = endpoint
        self.status_code = status_code


class TradingError(BotError):
    """Raised when there is a trading-related error."""

    def __init__(
        self,
        message: str = "Trading error",
        market_id: Optional[str] = None,
        trade_type: Optional[str] = None,
        original_exception: Optional[Exception] = None,
        **context: Any
    ) -> None:
        """Initialize trading error.

        Args:
            message: Error message
            market_id: The market ID involved in the error
            trade_type: The type of trade that failed
            original_exception: The original exception
            **context: Additional context information
        """
        details = []
        if market_id:
            details.append(f"market={market_id}")
        if trade_type:
            details.append(f"type={trade_type}")
        if details:
            message = f"{message} ({', '.join(details)})"
        super().__init__(message, original_exception, **context)
        self.market_id = market_id
        self.trade_type = trade_type


class ValidationError(BotError):
    """Raised when there is a data validation error."""

    def __init__(
        self,
        message: str = "Validation error",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **context: Any
    ) -> None:
        """Initialize validation error.

        Args:
            message: Error message
            field: The field that failed validation
            value: The invalid value
            **context: Additional context information
        """
        if field:
            message = f"{message} (field: {field})"
        super().__init__(message, **context)
        self.field = field
        self.value = value


class RateLimitError(NetworkError):
    """Raised when API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        **context: Any
    ) -> None:
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            **context: Additional context information
        """
        if retry_after:
            message = f"{message} (retry after {retry_after}s)"
        super().__init__(message, **context)
        self.retry_after = retry_after


class TimeoutError(NetworkError):
    """Raised when an API request times out."""

    def __init__(
        self,
        message: str = "Request timed out",
        timeout_seconds: Optional[float] = None,
        **context: Any
    ) -> None:
        """Initialize timeout error.

        Args:
            message: Error message
            timeout_seconds: The timeout duration
            **context: Additional context information
        """
        if timeout_seconds:
            message = f"{message} (timeout: {timeout_seconds}s)"
        super().__init__(message, **context)
        self.timeout_seconds = timeout_seconds


class InsufficientFundsError(TradingError):
    """Raised when there are insufficient funds for a trade."""

    def __init__(
        self,
        message: str = "Insufficient funds",
        required: Optional[float] = None,
        available: Optional[float] = None,
        **context: Any
    ) -> None:
        """Initialize insufficient funds error.

        Args:
            message: Error message
            required: Required amount
            available: Available amount
            **context: Additional context information
        """
        if required is not None and available is not None:
            message = f"{message} (required: ${required:.2f}, available: ${available:.2f})"
        super().__init__(message, **context)
        self.required = required
        self.available = available


class RiskLimitExceededError(TradingError):
    """Raised when a trade would exceed risk limits."""

    def __init__(
        self,
        message: str = "Risk limit exceeded",
        limit_type: Optional[str] = None,
        current: Optional[float] = None,
        limit: Optional[float] = None,
        **context: Any
    ) -> None:
        """Initialize risk limit exceeded error.

        Args:
            message: Error message
            limit_type: Type of limit exceeded
            current: Current value
            limit: Limit value
            **context: Additional context information
        """
        if limit_type and current is not None and limit is not None:
            message = f"{message} ({limit_type}: {current:.2%} > {limit:.2%})"
        super().__init__(message, **context)
        self.limit_type = limit_type
        self.current = current
        self.limit = limit
