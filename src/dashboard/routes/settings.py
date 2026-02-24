"""Settings API routes.

This module provides REST API endpoints for settings operations,
including exit strategy configuration.

Story 10.6: Dashboard 退出策略管理

Endpoints:
    GET /api/settings/exit-strategy - Get exit strategy configuration
    PUT /api/settings/exit-strategy - Update exit strategy configuration

Usage:
    from src.dashboard.routes.settings import router
    app.include_router(router, prefix="/api/settings", tags=["settings"])
"""

from __future__ import annotations

__all__ = ["router"]

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.config import settings
from src.models.api_response import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter()


class ExitStrategyConfigResponse(BaseModel):
    """Exit strategy configuration response.

    Attributes:
        take_profit_enabled: Whether take profit is enabled
        take_profit_pct: Take profit percentage threshold (e.g., 0.50 = 50%)
        stop_loss_enabled: Whether stop loss is enabled
        stop_loss_pct: Stop loss percentage threshold (e.g., -0.30 = -30%)
        time_exit_enabled: Whether time exit is enabled
        time_exit_hours: Hours after which to exit position
        signal_exit_enabled: Whether signal exit is enabled
        exit_check_interval_minutes: Interval in minutes for checking exit conditions
    """

    take_profit_enabled: bool
    take_profit_pct: float
    stop_loss_enabled: bool
    stop_loss_pct: float
    time_exit_enabled: bool
    time_exit_hours: int
    signal_exit_enabled: bool
    exit_check_interval_minutes: int


class ExitStrategyConfigRequest(BaseModel):
    """Exit strategy configuration update request.

    All fields are optional - only provided fields will be updated.

    Attributes:
        take_profit_enabled: Enable/disable take profit
        take_profit_pct: Take profit percentage threshold (0-1)
        stop_loss_enabled: Enable/disable stop loss
        stop_loss_pct: Stop loss percentage threshold (-1 to 0)
        time_exit_enabled: Enable/disable time exit
        time_exit_hours: Hours after which to exit (minimum 1)
        signal_exit_enabled: Enable/disable signal exit
        exit_check_interval_minutes: Interval in minutes (minimum 1)
    """

    take_profit_enabled: bool | None = None
    take_profit_pct: float | None = Field(default=None, ge=0, le=1)
    stop_loss_enabled: bool | None = None
    stop_loss_pct: float | None = Field(default=None, ge=-1, le=0)
    time_exit_enabled: bool | None = None
    time_exit_hours: int | None = Field(default=None, ge=1)
    signal_exit_enabled: bool | None = None
    exit_check_interval_minutes: int | None = Field(default=None, ge=1)


@router.get(
    "/exit-strategy",
    response_model=ApiResponse[ExitStrategyConfigResponse],
    summary="Get exit strategy configuration",
    description="Get current exit strategy configuration including take profit, stop loss, time exit, and signal exit settings.",
)
async def get_exit_strategy_config() -> ApiResponse[ExitStrategyConfigResponse]:
    """Get current exit strategy configuration.

    Returns:
        ApiResponse containing the current exit strategy configuration

    Example:
        >>> # GET /api/settings/exit-strategy
        >>> # Response: {"success": true, "data": {...}, "error": null}
    """
    logger.info("💰 Getting exit strategy configuration")

    config = settings.exit_strategy
    response = ExitStrategyConfigResponse(
        take_profit_enabled=config.take_profit_enabled,
        take_profit_pct=config.take_profit_pct,
        stop_loss_enabled=config.stop_loss_enabled,
        stop_loss_pct=config.stop_loss_pct,
        time_exit_enabled=config.time_exit_enabled,
        time_exit_hours=config.time_exit_hours,
        signal_exit_enabled=config.signal_exit_enabled,
        exit_check_interval_minutes=config.exit_check_interval_minutes,
    )

    logger.info("💰 Exit strategy configuration retrieved successfully")
    return ApiResponse(success=True, data=response, error=None)


@router.put(
    "/exit-strategy",
    response_model=ApiResponse[ExitStrategyConfigResponse],
    summary="Update exit strategy configuration",
    description="Update exit strategy configuration. Note: This updates runtime settings only. For persistent changes, update the .env file.",
)
async def update_exit_strategy_config(
    request: ExitStrategyConfigRequest,
) -> ApiResponse[ExitStrategyConfigResponse]:
    """Update exit strategy configuration.

    Updates runtime settings. For persistent changes, update the .env file.

    Args:
        request: Configuration update request with fields to update

    Returns:
        ApiResponse containing the updated exit strategy configuration

    Example:
        >>> # PUT /api/settings/exit-strategy
        >>> # Body: {"take_profit_pct": 0.60}
        >>> # Response: {"success": true, "data": {...}, "error": null}
    """
    logger.info("💰 Updating exit strategy configuration")

    config = settings.exit_strategy
    update_data = request.model_dump(exclude_unset=True)

    # Update only provided fields
    for key, value in update_data.items():
        if value is not None and hasattr(config, key):
            setattr(config, key, value)
            logger.debug(f"💰 Updated {key} to {value}")

    response = ExitStrategyConfigResponse(
        take_profit_enabled=config.take_profit_enabled,
        take_profit_pct=config.take_profit_pct,
        stop_loss_enabled=config.stop_loss_enabled,
        stop_loss_pct=config.stop_loss_pct,
        time_exit_enabled=config.time_exit_enabled,
        time_exit_hours=config.time_exit_hours,
        signal_exit_enabled=config.signal_exit_enabled,
        exit_check_interval_minutes=config.exit_check_interval_minutes,
    )

    logger.info(
        f"💰 Exit strategy configuration updated: {len(update_data)} fields changed"
    )
    return ApiResponse(success=True, data=response, error=None)
