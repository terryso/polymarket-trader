"""Dashboard middleware modules."""

from src.dashboard.middleware.error_middleware import ErrorMiddleware, setup_exception_handlers

__all__ = ["ErrorMiddleware", "setup_exception_handlers"]
