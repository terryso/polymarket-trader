"""Error handling middleware for the FastAPI Dashboard.

This module provides middleware and exception handlers for unified
error responses across the API. It ensures:
- Consistent error response format
- Appropriate HTTP status codes
- No sensitive information leakage
- Proper error logging

Example:
    >>> from fastapi import FastAPI
    >>> from src.dashboard.middleware.error_middleware import ErrorMiddleware, setup_exception_handlers
    >>>
    >>> app = FastAPI()
    >>> app.add_middleware(ErrorMiddleware)
    >>> setup_exception_handlers(app)
"""

from __future__ import annotations

__all__ = ["ErrorMiddleware", "setup_exception_handlers"]

import traceback
from typing import Any, Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.exceptions import (
    BotError,
    ConfigurationError,
    DatabaseError,
    InsufficientFundsError,
    NetworkError,
    RateLimitError,
    RiskLimitExceededError,
    TradingError,
    ValidationError,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ErrorMiddleware(BaseHTTPMiddleware):
    """Middleware for handling uncaught exceptions in API requests.

    This middleware catches any exception that wasn't handled by
    FastAPI's exception handlers and converts it to a unified
    error response format.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process the request and handle any uncaught exceptions.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Either the normal response or an error response
        """
        try:
            return await call_next(request)
        except Exception as e:
            return self._handle_error(request, e)

    def _handle_error(self, request: Request, error: Exception) -> JSONResponse:
        """Handle an exception and return an appropriate response.

        Args:
            request: The request that caused the error
            error: The exception that was raised

        Returns:
            JSONResponse with error details
        """
        # Collect request info for logging
        request_info = {
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else None,
        }

        # Determine response based on exception type
        if isinstance(error, ValidationError):
            status_code = 400
            error_code = "VALIDATION_ERROR"
            message = str(error)
            log_level = "warning"
        elif isinstance(error, ConfigurationError):
            status_code = 500
            error_code = "CONFIGURATION_ERROR"
            # Don't expose config details
            message = "Configuration error"
            log_level = "error"
        elif isinstance(error, NetworkError):
            status_code = 503
            error_code = "NETWORK_ERROR"
            # Don't expose internal network details
            message = "Network error, please retry"
            log_level = "error"
        elif isinstance(error, RateLimitError):
            status_code = 429
            error_code = "RATE_LIMIT_ERROR"
            message = str(error)
            log_level = "warning"
        elif isinstance(error, InsufficientFundsError):
            status_code = 400
            error_code = "INSUFFICIENT_FUNDS"
            message = str(error)
            log_level = "warning"
        elif isinstance(error, RiskLimitExceededError):
            status_code = 400
            error_code = "RISK_LIMIT_EXCEEDED"
            message = str(error)
            log_level = "warning"
        elif isinstance(error, TradingError):
            status_code = 400
            error_code = "TRADING_ERROR"
            message = str(error)
            log_level = "warning"
        elif isinstance(error, DatabaseError):
            status_code = 500
            error_code = "DATABASE_ERROR"
            # Don't expose database details
            message = "Database error"
            log_level = "error"
        elif isinstance(error, BotError):
            status_code = 500
            error_code = "BUSINESS_ERROR"
            # Generic message for unknown business errors
            message = "Business error occurred"
            log_level = "error"
        else:
            status_code = 500
            error_code = "INTERNAL_ERROR"
            # Never expose internal error details
            message = "Internal server error"
            log_level = "critical"

        # Log the error with context
        log_data = {
            "request": request_info,
            "error": str(error),
            "error_type": type(error).__name__,
            "traceback": traceback.format_exc(),
        }

        if log_level == "warning":
            logger.warning(f"API error: {error_code} - {error}", extra=log_data)
        elif log_level == "error":
            logger.error(f"API error: {error_code} - {error}", extra=log_data)
        else:
            logger.critical(f"API error: {error_code} - {error}", extra=log_data)

        # Return unified error response
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": error_code,
                    "message": message,
                },
            },
        )


def setup_exception_handlers(app: Any) -> None:
    """Set up exception handlers for the FastAPI application.

    This function registers exception handlers for custom exception types
    to ensure consistent error responses throughout the API.

    Args:
        app: The FastAPI application instance
    """

    @app.exception_handler(BotError)
    async def bot_error_handler(request: Request, exc: BotError) -> JSONResponse:
        """Handle BotError and its subclasses.

        Args:
            request: The request that caused the error
            exc: The BotError exception

        Returns:
            JSONResponse with error details
        """
        logger.error(f"BotError: {exc}")
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": type(exc).__name__.upper(),
                    "message": str(exc),
                },
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle any unhandled exception.

        This is the catch-all handler that ensures no internal details
        are leaked to the client.

        Args:
            request: The request that caused the error
            exc: The exception

        Returns:
            JSONResponse with generic error message
        """
        logger.critical(
            f"Unhandled exception: {exc}",
            extra={"traceback": traceback.format_exc()},
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                },
            },
        )
