"""API response models for the Dashboard API.

This module provides unified response models for consistent API responses
across all endpoints.

Usage:
    from src.models.api_response import ApiResponse, PaginatedResponse, ErrorCode

    # Success response
    return ApiResponse(success=True, data={"id": 123})

    # Error response
    return ApiResponse(success=False, error=ErrorDetail(code=ErrorCode.NOT_FOUND, message="Not found"))
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Error detail for API error responses.

    Attributes:
        code: Error code identifier
        message: Human-readable error message
    """

    code: str = Field(..., description="Error code identifier")
    message: str = Field(..., description="Human-readable error message")


class ApiResponse(BaseModel, Generic[T]):
    """Unified API response format.

    This model wraps all API responses in a consistent structure
    with success flag, data, and optional error details.

    Attributes:
        success: Whether the request was successful
        data: Response data (present on success)
        error: Error details (present on failure)

    Example:
        >>> ApiResponse(success=True, data={"id": 1, "name": "Test"})
        >>> ApiResponse(success=False, error=ErrorDetail(code="NOT_FOUND", message="Resource not found"))
    """

    success: bool = Field(..., description="Whether the request was successful")
    data: T | None = Field(None, description="Response data (present on success)")
    error: ErrorDetail | None = Field(
        None, description="Error details (present on failure)"
    )


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses.

    Attributes:
        total: Total number of records
        page: Current page number (1-indexed)
        per_page: Number of records per page
    """

    total: int = Field(..., description="Total number of records")
    page: int = Field(..., description="Current page number (1-indexed)")
    per_page: int = Field(..., description="Number of records per page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response format.

    This model wraps list responses with pagination metadata.

    Attributes:
        success: Whether the request was successful (always True for paginated responses)
        data: List of items
        meta: Pagination metadata

    Example:
        >>> PaginatedResponse(
        ...     data=[{"id": 1}, {"id": 2}],
        ...     meta=PaginationMeta(total=100, page=1, per_page=20)
        ... )
    """

    success: bool = Field(
        default=True, description="Whether the request was successful"
    )
    data: list[T] = Field(default_factory=list, description="List of items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")


class ErrorCode:
    """Error code constants for API responses.

    These codes categorize errors for consistent error handling on the client side.
    """

    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    TRADING_ERROR = "TRADING_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"


__all__ = [
    "ErrorDetail",
    "ApiResponse",
    "PaginationMeta",
    "PaginatedResponse",
    "ErrorCode",
]
