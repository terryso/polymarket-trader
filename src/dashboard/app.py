"""FastAPI Dashboard Application.

This module provides the main FastAPI application for the Dashboard API,
including CORS configuration, exception handlers, and route registration.

Usage:
    # Run with uvicorn
    uvicorn src.dashboard.app:app --reload --host 0.0.0.0 --port 8000

    # Or import the app
    from src.dashboard.app import app
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
from src.models.api_response import ApiResponse, ErrorDetail, ErrorCode
from src.storage.database import close_db, init_db

logger = logging.getLogger(__name__)

# CORS configuration - allow frontend development servers
ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Alternative dev port
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

# Application metadata
APP_TITLE = "Polymarket Trader API"
APP_DESCRIPTION = "LLM 驱动的 Polymarket 自动交易系统 Dashboard API"
APP_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management.

    Handles startup and shutdown events for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("🚀 Starting Dashboard API...")
    await init_db()
    logger.info("✅ Database initialized")

    # Load state from storage to ensure correct capital values
    from src.core.state import get_state_manager
    state = get_state_manager()
    result = await state.load_from_storage()
    if result.success:
        logger.info("✅ State loaded from storage")
    else:
        logger.warning("⚠️ Failed to load state from storage, using defaults")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Dashboard API...")
    await close_db()
    logger.info("✅ Cleanup complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance.

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title=APP_TITLE,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register exception handlers
    _register_exception_handlers(app)

    # Register routers
    _register_routers(app)

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers for the application.

    All exceptions are converted to a unified error response format.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Handle request validation errors.

        Converts FastAPI validation errors to the unified error format.

        Args:
            request: The request that caused the error
            exc: The validation error

        Returns:
            JSONResponse with error details
        """
        errors = exc.errors()
        messages = [e.get("msg", str(e)) for e in errors]
        return JSONResponse(
            status_code=422,
            content=ApiResponse(
                success=False,
                data=None,
                error=ErrorDetail(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="; ".join(messages),
                ),
            ).model_dump(),
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        """Handle custom validation errors.

        Args:
            request: The request that caused the error
            exc: The validation error

        Returns:
            JSONResponse with error details
        """
        return JSONResponse(
            status_code=400,
            content=ApiResponse(
                success=False,
                data=None,
                error=ErrorDetail(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=str(exc),
                ),
            ).model_dump(),
        )

    @app.exception_handler(ConfigurationError)
    async def configuration_error_handler(
        request: Request,
        exc: ConfigurationError,
    ) -> JSONResponse:
        """Handle configuration errors.

        Args:
            request: The request that caused the error
            exc: The configuration error

        Returns:
            JSONResponse with error details
        """
        logger.error(f"❌ Configuration error: {exc}")
        return JSONResponse(
            status_code=500,
            content=ApiResponse(
                success=False,
                data=None,
                error=ErrorDetail(
                    code=ErrorCode.CONFIGURATION_ERROR,
                    message=str(exc),
                ),
            ).model_dump(),
        )

    @app.exception_handler(NetworkError)
    async def network_error_handler(
        request: Request,
        exc: NetworkError,
    ) -> JSONResponse:
        """Handle network errors.

        Args:
            request: The request that caused the error
            exc: The network error

        Returns:
            JSONResponse with error details
        """
        logger.error(f"❌ Network error: {exc}")
        return JSONResponse(
            status_code=503,
            content=ApiResponse(
                success=False,
                data=None,
                error=ErrorDetail(
                    code=ErrorCode.NETWORK_ERROR,
                    message=str(exc),
                ),
            ).model_dump(),
        )

    @app.exception_handler(RateLimitError)
    async def rate_limit_error_handler(
        request: Request,
        exc: RateLimitError,
    ) -> JSONResponse:
        """Handle rate limit errors.

        Args:
            request: The request that caused the error
            exc: The rate limit error

        Returns:
            JSONResponse with error details
        """
        logger.warning(f"⚠️ Rate limit exceeded: {exc}")
        return JSONResponse(
            status_code=429,
            content=ApiResponse(
                success=False,
                data=None,
                error=ErrorDetail(
                    code=ErrorCode.RATE_LIMIT_ERROR,
                    message=str(exc),
                ),
            ).model_dump(),
        )

    @app.exception_handler(TradingError)
    async def trading_error_handler(
        request: Request,
        exc: TradingError,
    ) -> JSONResponse:
        """Handle trading errors.

        Args:
            request: The request that caused the error
            exc: The trading error

        Returns:
            JSONResponse with error details
        """
        logger.error(f"❌ Trading error: {exc}")
        return JSONResponse(
            status_code=400,
            content=ApiResponse(
                success=False,
                data=None,
                error=ErrorDetail(
                    code=ErrorCode.TRADING_ERROR,
                    message=str(exc),
                ),
            ).model_dump(),
        )

    @app.exception_handler(InsufficientFundsError)
    async def insufficient_funds_error_handler(
        request: Request,
        exc: InsufficientFundsError,
    ) -> JSONResponse:
        """Handle insufficient funds errors.

        Args:
            request: The request that caused the error
            exc: The insufficient funds error

        Returns:
            JSONResponse with error details
        """
        logger.warning(f"⚠️ Insufficient funds: {exc}")
        return JSONResponse(
            status_code=400,
            content=ApiResponse(
                success=False,
                data=None,
                error=ErrorDetail(
                    code=ErrorCode.TRADING_ERROR,
                    message=str(exc),
                ),
            ).model_dump(),
        )

    @app.exception_handler(RiskLimitExceededError)
    async def risk_limit_error_handler(
        request: Request,
        exc: RiskLimitExceededError,
    ) -> JSONResponse:
        """Handle risk limit exceeded errors.

        Args:
            request: The request that caused the error
            exc: The risk limit exceeded error

        Returns:
            JSONResponse with error details
        """
        logger.warning(f"⚠️ Risk limit exceeded: {exc}")
        return JSONResponse(
            status_code=400,
            content=ApiResponse(
                success=False,
                data=None,
                error=ErrorDetail(
                    code=ErrorCode.TRADING_ERROR,
                    message=str(exc),
                ),
            ).model_dump(),
        )

    @app.exception_handler(DatabaseError)
    async def database_error_handler(
        request: Request,
        exc: DatabaseError,
    ) -> JSONResponse:
        """Handle database errors.

        Args:
            request: The request that caused the error
            exc: The database error

        Returns:
            JSONResponse with error details
        """
        logger.error(f"❌ Database error: {exc}")
        return JSONResponse(
            status_code=500,
            content=ApiResponse(
                success=False,
                data=None,
                error=ErrorDetail(
                    code=ErrorCode.DATABASE_ERROR,
                    message=str(exc),
                ),
            ).model_dump(),
        )

    @app.exception_handler(BotError)
    async def bot_error_handler(request: Request, exc: BotError) -> JSONResponse:
        """Handle generic bot errors.

        Args:
            request: The request that caused the error
            exc: The bot error

        Returns:
            JSONResponse with error details
        """
        logger.error(f"❌ Bot error: {exc}")
        return JSONResponse(
            status_code=400,
            content=ApiResponse(
                success=False,
                data=None,
                error=ErrorDetail(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=str(exc),
                ),
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unexpected exceptions.

        Args:
            request: The request that caused the error
            exc: The exception

        Returns:
            JSONResponse with error details
        """
        # Import asyncio locally to check for CancelledError
        import asyncio

        # Don't log CancelledError as an error - it's normal during shutdown
        if isinstance(exc, asyncio.CancelledError):
            logger.debug("Request cancelled (likely during shutdown)")
            # Return a simple response, though it may not be sent
            return JSONResponse(
                status_code=499,  # Client Closed Request (non-standard but commonly used)
                content={"detail": "Request cancelled"},
            )

        logger.exception(f"❌ Unexpected error: {exc}")
        return JSONResponse(
            status_code=500,
            content=ApiResponse(
                success=False,
                data=None,
                error=ErrorDetail(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="An unexpected error occurred",
                ),
            ).model_dump(),
        )


def _register_routers(app: FastAPI) -> None:
    """Register all API routers.

    Args:
        app: FastAPI application instance
    """
    from src.dashboard.routes import (
        activities,
        markets,
        positions,
        predictions,
        settings,
        statistics,
        trades,
    )

    app.include_router(markets.router, prefix="/api/markets", tags=["markets"])
    app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
    app.include_router(
        positions.router, prefix="/api/positions", tags=["positions"]
    )
    app.include_router(
        predictions.router, prefix="/api/predictions", tags=["predictions"]
    )
    app.include_router(
        statistics.router, prefix="/api/statistics", tags=["statistics"]
    )
    app.include_router(
        activities.router, prefix="/api/activities", tags=["activities"]
    )
    # Story 10.6: Dashboard 退出策略管理
    app.include_router(
        settings.router, prefix="/api/settings", tags=["settings"]
    )


# Create the application instance
app = create_app()


@app.get("/", response_model=ApiResponse[dict])
async def root() -> ApiResponse[dict]:
    """API root endpoint.

    Returns basic API information including available endpoints.

    Returns:
        ApiResponse with API information
    """
    return ApiResponse(
        success=True,
        data={
            "name": APP_TITLE,
            "version": APP_VERSION,
            "docs": "/docs",
            "health": "/health",
        },
        error=None,
    )


@app.get("/health", response_model=ApiResponse[dict])
async def health_check() -> ApiResponse[dict]:
    """Health check endpoint.

    Used for monitoring and load balancer health checks.

    Returns:
        ApiResponse with health status
    """
    return ApiResponse(
        success=True,
        data={
            "status": "healthy",
            "service": "dashboard-api",
        },
        error=None,
    )


__all__ = ["app", "create_app"]
