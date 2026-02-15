"""Retry decorator with exponential backoff for the Polymarket Trader application.

This module provides a retry decorator that supports both synchronous and
asynchronous functions, with configurable exponential backoff and exception
handling.

Usage:
    from src.utils.retry import retry
    from src.exceptions import NetworkError

    @retry(max_attempts=3, base_delay=1.0, exceptions=(NetworkError,))
    async def call_api():
        ...
"""

from __future__ import annotations

__all__ = ["RetryConfig", "retry"]

import asyncio
import functools
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, TypeVar, cast

R = TypeVar("R")

# Retry-specific emojis for logging
# Note: Don't use ❌ for failure as logger.py adds ERROR emoji automatically
RETRY_EMOJIS = {
    "retry": "🔄",
    "success": "✅",
    "failure": "💥",  # Different from LOG_EMOJIS["ERROR"] = "❌" to avoid double emoji
}


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of retry attempts (default: 3, must be >= 1)
        base_delay: Base delay in seconds between retries (default: 1.0, must be >= 0)
        max_delay: Maximum delay cap in seconds (default: 30.0, must be >= 0)
        exponential_backoff: Whether to use exponential backoff (default: True)
        exceptions: Tuple of exception types to retry on (default: (Exception,))
        jitter: Random jitter factor to add to delays (default: 0.0, 0.0-1.0)

    Raises:
        ValueError: If any parameter value is invalid
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_backoff: bool = True
    exceptions: tuple[type[Exception], ...] = (Exception,)
    jitter: float = 0.0

    def __post_init__(self) -> None:
        """Validate configuration parameters after initialization."""
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {self.max_attempts}")
        if self.base_delay < 0:
            raise ValueError(f"base_delay must be >= 0, got {self.base_delay}")
        if self.max_delay < 0:
            raise ValueError(f"max_delay must be >= 0, got {self.max_delay}")
        if self.max_delay < self.base_delay:
            raise ValueError(
                f"max_delay ({self.max_delay}) must be >= base_delay ({self.base_delay})"
            )
        if not 0.0 <= self.jitter <= 1.0:
            raise ValueError(f"jitter must be between 0.0 and 1.0, got {self.jitter}")

    def calculate_delay(self, attempt: int) -> float:
        """Calculate the delay for a given retry attempt.

        Args:
            attempt: The attempt number (0-indexed)

        Returns:
            Delay in seconds for this attempt (with jitter applied if configured)
        """
        import random

        if not self.exponential_backoff:
            delay = self.base_delay
        else:
            # Formula: delay = base_delay * (2 ** attempt)
            delay = self.base_delay * (2**attempt)

        # Apply cap
        delay = float(min(delay, self.max_delay))

        # Apply jitter: delay * (1 - jitter) <= actual_delay <= delay * (1 + jitter)
        if self.jitter > 0:
            jitter_factor = 1.0 + (random.random() * 2 - 1) * self.jitter
            delay = delay * jitter_factor

        return delay


def _get_logger(name: str) -> logging.Logger:
    """Get a logger instance for retry operations.

    Uses the project's logging configuration if available,
    otherwise creates a basic logger.

    Args:
        name: Logger name (typically the module name)

    Returns:
        Configured logger instance
    """
    try:
        from src.utils.logger import get_logger

        return get_logger(name)
    except ImportError:
        # Fallback to basic logger if project logger not available
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)-8s | %(threadName)-12s | "
                    "%(name)s | %(message)s"
                )
            )
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_backoff: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    jitter: float = 0.0,
) -> Callable[[Callable[..., R]], Callable[..., R]]:
    """Unified retry decorator that supports both sync and async functions.

    This decorator automatically detects whether the decorated function is
    synchronous or asynchronous and applies the appropriate retry logic.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3, must be >= 1)
        base_delay: Base delay in seconds between retries (default: 1.0, must be >= 0)
        max_delay: Maximum delay cap in seconds (default: 30.0, must be >= 0)
        exponential_backoff: Whether to use exponential backoff (default: True)
        exceptions: Tuple of exception types to retry on (default: (Exception,))
        jitter: Random jitter factor (0.0-1.0) to add variation to delays (default: 0.0)

    Returns:
        Decorated function with retry logic

    Raises:
        ValueError: If any parameter value is invalid

    Example:
        @retry(max_attempts=3, base_delay=1.0, exceptions=(NetworkError,))
        async def call_api():
            ...

        @retry(max_attempts=5, exceptions=(ConnectionError,), jitter=0.1)
        def sync_call():
            ...
    """

    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_backoff=exponential_backoff,
        exceptions=exceptions,
        jitter=jitter,
    )

    def decorator(func: Callable[..., R]) -> Callable[..., R]:
        logger = _get_logger(f"{func.__module__}.{func.__name__}")
        func_name = func.__name__

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> R:
                last_exception: Exception | None = None

                for attempt in range(config.max_attempts):
                    try:
                        result = cast(R, await func(*args, **kwargs))
                        # Log success if we had retries
                        if attempt > 0:
                            logger.info(
                                "%s %s succeeded after %d retries",
                                RETRY_EMOJIS["success"],
                                func_name,
                                attempt,
                            )
                        return result
                    except config.exceptions as e:
                        last_exception = e

                        # Check if this was the last attempt
                        if attempt + 1 >= config.max_attempts:
                            logger.error(
                                "%s %s failed after %d attempts: %s",
                                RETRY_EMOJIS["failure"],
                                func_name,
                                config.max_attempts,
                                type(e).__name__,
                            )
                            raise

                        delay = config.calculate_delay(attempt)
                        logger.warning(
                            "%s Retrying %s (attempt %d/%d) after %.1fs: %s",
                            RETRY_EMOJIS["retry"],
                            func_name,
                            attempt + 1,
                            config.max_attempts,
                            delay,
                            type(e).__name__,
                        )
                        await asyncio.sleep(delay)

                # This should never be reached, but satisfies type checker
                if last_exception:
                    raise last_exception
                raise RuntimeError(f"Unexpected state in retry for {func_name}")

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> R:
                last_exception: Exception | None = None

                for attempt in range(config.max_attempts):
                    try:
                        result = func(*args, **kwargs)
                        # Log success if we had retries
                        if attempt > 0:
                            logger.info(
                                "%s %s succeeded after %d retries",
                                RETRY_EMOJIS["success"],
                                func_name,
                                attempt,
                            )
                        return result
                    except config.exceptions as e:
                        last_exception = e

                        # Check if this was the last attempt
                        if attempt + 1 >= config.max_attempts:
                            logger.error(
                                "%s %s failed after %d attempts: %s",
                                RETRY_EMOJIS["failure"],
                                func_name,
                                config.max_attempts,
                                type(e).__name__,
                            )
                            raise

                        delay = config.calculate_delay(attempt)
                        logger.warning(
                            "%s Retrying %s (attempt %d/%d) after %.1fs: %s",
                            RETRY_EMOJIS["retry"],
                            func_name,
                            attempt + 1,
                            config.max_attempts,
                            delay,
                            type(e).__name__,
                        )
                        time.sleep(delay)

                # This should never be reached, but satisfies type checker
                if last_exception:
                    raise last_exception
                raise RuntimeError(f"Unexpected state in retry for {func_name}")

            return sync_wrapper

    return decorator
