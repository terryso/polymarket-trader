"""Database repositories for data access.

This package provides repository classes for database operations
following the repository pattern.

Usage:
    from src.storage.repositories import (
        MarketRepository,
        PredictionRepository,
        PositionRepository,
        TradeRepository,
        StatisticsRepository,
        StateRepository,
    )

    market_repo = MarketRepository()
    await market_repo.save_market(market)

    prediction_repo = PredictionRepository()
    await prediction_repo.save_prediction(prediction)

    position_repo = PositionRepository()
    await position_repo.save(position)

    trade_repo = TradeRepository()
    await trade_repo.save(trade)

    stats_repo = StatisticsRepository()
    await stats_repo.save(stats)

    state_repo = StateRepository()
    await state_repo.save_state({"current_capital": 150.0})
"""

from __future__ import annotations

from src.storage.repositories.market_repo import MarketRepository
from src.storage.repositories.position_repo import PositionRepository
from src.storage.repositories.prediction_repo import PredictionRepository
from src.storage.repositories.state_repo import StateRepository
from src.storage.repositories.statistics_repo import StatisticsRepository
from src.storage.repositories.trade_repo import TradeRepository

__all__ = [
    "MarketRepository",
    "PredictionRepository",
    "PositionRepository",
    "TradeRepository",
    "StatisticsRepository",
    "StateRepository",
]
