"""Global error handling for the Polymarket Trader application.

This module provides centralized error handling including:
- Global exception handler setup
- Task-level error handling with retry support
- Integration with the alerting system

Example:
    >>> from src.core.error_handler import setup_error_handler, get_error_handler
    >>> from src.core.alerting import AlertManager
    >>>
    >>> # Setup error handling with alerting
    >>> alert_manager = AlertManager()
    >>> handler = setup_error_handler(alert_manager=alert_manager)
    >>>
    >>> # Use task wrapper for retry support
    >>> @handler.task_wrapper("my_task")
    ... async def my_task():
    ...     pass
"""

from __future__ import annotations

__all__ = [
    "ErrorHandler",
    "get_error_handler",
    "setup_error_handler",
    "setup_global_exception_handler",
    "setup_async_exception_handler",
]

import asyncio
import sys
import traceback
from datetime import datetime
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable

from src.exceptions import BotError, NetworkError
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.core.alerting import AlertManager

logger = get_logger(__name__)


class ErrorHandler:
    """Central error handling and retry management.

    The ErrorHandler provides:
    - Exception logging with severity-based levels
    - Error statistics tracking
    - Task wrapping with automatic retry for transient failures
    - Integration with AlertManager for notifications

    Attributes:
        alert_manager: Optional alert manager for notifications
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries (with exponential backoff)

    Example:
        >>> handler = ErrorHandler(max_retries=3, retry_delay=1.0)
        >>> handler.handle_exception(ValueError("test"), {"task": "example"})
    """

    def __init__(
        self,
        alert_manager: AlertManager | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize the error handler.

        Args:
            alert_manager: Alert manager for notifications
            max_retries: Maximum retry attempts for transient failures
            retry_delay: Base delay in seconds between retries
        """
        self.alert_manager = alert_manager
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Error statistics
        self._error_counts: dict[str, int] = {}
        self._last_errors: dict[str, datetime] = {}

    def handle_exception(
        self,
        exception: Exception,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Handle an exception with logging and optional alerting.

        Records error statistics and triggers alerts if configured.
        Business exceptions are logged at ERROR level, unexpected exceptions
        at CRITICAL level.

        Args:
            exception: The exception to handle
            context: Additional context about where the error occurred
        """
        context = context or {}
        error_type = type(exception).__name__
        error_message = str(exception)

        # Record error statistics
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
        self._last_errors[error_type] = datetime.utcnow()

        # Log with appropriate severity
        if isinstance(exception, BotError):
            # Business exceptions - ERROR level (expected issues)
            logger.error(
                f"Business error: {error_type} - {error_message}",
                extra={"context": context},
            )
        else:
            # Unexpected exceptions - CRITICAL level
            logger.critical(
                f"Unhandled exception: {error_type} - {error_message}",
                extra={
                    "context": context,
                    "traceback": traceback.format_exc(),
                },
            )

        # Trigger alert if alert manager is configured
        if self.alert_manager:
            self.alert_manager.check_and_alert(exception, context)

    def task_wrapper(
        self,
        task_name: str,
        retry_exceptions: tuple[type[Exception], ...] = (NetworkError,),
    ) -> Callable:
        """Decorator to wrap async tasks with error handling and retry.

        Automatically retries on specified exception types with exponential
        backoff. Non-retryable exceptions are logged and re-raised immediately.

        Args:
            task_name: Name of the task for logging
            retry_exceptions: Tuple of exception types that should trigger retry

        Returns:
            Decorator function

        Example:
            >>> @error_handler.task_wrapper("fetch_data")
            ... async def fetch_data():
            ...     return await api.get_data()
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exception: Exception | None = None

                for attempt in range(self.max_retries):
                    try:
                        result = await func(*args, **kwargs)
                        # Task succeeded, reset failure count if alert manager exists
                        if self.alert_manager:
                            self.alert_manager.reset_failures(task_name)
                        return result
                    except retry_exceptions as e:
                        last_exception = e
                        logger.warning(
                            f"Task {task_name} failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                        )
                        if attempt < self.max_retries - 1:
                            # Exponential backoff
                            delay = self.retry_delay * (attempt + 1)
                            await asyncio.sleep(delay)
                    except Exception as e:
                        # Non-retryable exception, handle and re-raise
                        self.handle_exception(e, {"task": task_name})
                        if self.alert_manager:
                            self.alert_manager.record_failure(task_name)
                        raise

                # All retries exhausted
                if last_exception:
                    self.handle_exception(
                        last_exception,
                        {"task": task_name, "attempts": self.max_retries},
                    )
                    if self.alert_manager:
                        self.alert_manager.record_failure(task_name)
                    raise last_exception

            return wrapper

        return decorator

    def get_error_stats(self) -> dict[str, Any]:
        """Get current error statistics.

        Returns:
            Dictionary with error counts and last error timestamps
        """
        return {
            "error_counts": self._error_counts.copy(),
            "last_errors": {
                k: v.isoformat() for k, v in self._last_errors.items()
            },
        }

    def reset_counts(self) -> None:
        """Reset error statistics."""
        self._error_counts.clear()
        self._last_errors.clear()
        logger.info("Error statistics reset")


# Global error handler instance
_global_handler: ErrorHandler | None = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance.

    Creates a new instance if one doesn't exist.

    Returns:
        The global ErrorHandler instance
    """
    global _global_handler
    if _global_handler is None:
        _global_handler = ErrorHandler()
    return _global_handler


def setup_error_handler(
    alert_manager: AlertManager | None = None,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> ErrorHandler:
    """Set up the global error handler.

    Creates and configures the global error handler instance.

    Args:
        alert_manager: Alert manager for notifications
        max_retries: Maximum retry attempts
        retry_delay: Base delay between retries

    Returns:
        The configured ErrorHandler instance
    """
    global _global_handler
    _global_handler = ErrorHandler(
        alert_manager=alert_manager,
        max_retries=max_retries,
        retry_delay=retry_delay,
    )
    logger.info("Global error handler initialized")
    return _global_handler


def setup_global_exception_handler() -> None:
    """Set up the global exception handler for uncaught exceptions.

    Installs a sys.excepthook that logs uncaught exceptions through
    the error handler. KeyboardInterrupt is passed through to the
    default handler.
    """

    def handle_exception(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: Any,
    ) -> None:
        """Handle uncaught exceptions."""
        # Let KeyboardInterrupt through
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Get error handler and process
        error_handler = get_error_handler()
        error_handler.handle_exception(
            exc_value if isinstance(exc_value, Exception) else Exception(str(exc_value)),
            {
                "source": "global",
                "traceback": "".join(traceback.format_tb(exc_traceback)),
            },
        )

    sys.excepthook = handle_exception
    logger.info("Global exception handler installed")


def setup_async_exception_handler() -> None:
    """Set up the async exception handler for uncaught async exceptions.

    Installs an exception handler on the current event loop that logs
    uncaught async exceptions through the error handler.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, will be set up when loop starts
        logger.debug("No running event loop, async handler will be set up later")
        return

    def handle_loop_exception(loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
        """Handle async loop exceptions."""
        exception = context.get("exception")
        message = context.get("message", "Unknown async error")

        error_handler = get_error_handler()

        if exception and isinstance(exception, Exception):
            error_handler.handle_exception(
                exception,
                {
                    "source": "async_loop",
                    "message": message,
                },
            )
        else:
            logger.error(f"Async loop error: {context}")

    loop.set_exception_handler(handle_loop_exception)
    logger.info("Async exception handler installed")
