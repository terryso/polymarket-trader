"""Pydantic data models for the application.

This module exports all public models and enumerations for use
throughout the application.

Usage:
    from src.models import Market, MarketCategory, Trade, TradeType

    # Or import all
    from src.models import *
"""

from __future__ import annotations

from src.models.market import Market, MarketCategory
from src.models.position import Position, PositionOutcome, PositionStatus
from src.models.prediction import Prediction, PredictionResult, Recommendation
from src.models.statistics import DailyStats, Statistics
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType

__all__ = [
    # Market
    "Market",
    "MarketCategory",
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
    # Statistics
    "Statistics",
    "DailyStats",
]
