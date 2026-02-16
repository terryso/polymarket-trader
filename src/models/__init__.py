"""Pydantic data models for the application.

This module exports all public models and enumerations for use
throughout the application.

Usage:
    from src.models import Market, MarketCategory, Trade, TradeType

    # Or import all
    from src.models import *
"""

from __future__ import annotations

from src.models.api_response import (
    ApiResponse,
    ErrorDetail,
    ErrorCode,
    PaginatedResponse,
    PaginationMeta,
)
from src.models.market import Market, MarketCategory
from src.models.market_response import MarketListItem, MarketListQueryParams, MarketResponse
from src.models.position import Position, PositionOutcome, PositionStatus
from src.models.position_response import PositionListItem, PositionResponse
from src.models.prediction import Prediction, PredictionResult, Recommendation
from src.models.statistics import DailyStats, Statistics
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.models.trade_response import (
    TradeListItem,
    TradeListQueryParams,
    TradeResponse,
)

__all__ = [
    # API Response
    "ApiResponse",
    "ErrorDetail",
    "ErrorCode",
    "PaginationMeta",
    "PaginatedResponse",
    # Market
    "Market",
    "MarketCategory",
    # Market Response (API models)
    "MarketListItem",
    "MarketResponse",
    "MarketListQueryParams",
    # Trade
    "Trade",
    "TradeType",
    "TradeMode",
    "TradeStatus",
    # Prediction
    "Prediction",
    "PredictionResult",
    "Recommendation",
    # Position
    "Position",
    "PositionStatus",
    "PositionOutcome",
    # Position Response (API models)
    "PositionListItem",
    "PositionResponse",
    # Trade Response (API models)
    "TradeListItem",
    "TradeResponse",
    "TradeListQueryParams",
    # Statistics
    "Statistics",
    "DailyStats",
]
