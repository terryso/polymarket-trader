"""Database repositories for data access.

This package provides repository classes for database operations
following the repository pattern.

Usage:
    from src.storage.repositories import (
        MarketRepository,
        PredictionRepository,
        PositionRepository,
    )

    market_repo = MarketRepository()
    await market_repo.save_market(market)

    prediction_repo = PredictionRepository()
    await prediction_repo.save_prediction(prediction)

    position_repo = PositionRepository()
    await position_repo.save(position)
"""

from __future__ import annotations

from src.storage.repositories.market_repo import MarketRepository
from src.storage.repositories.position_repo import PositionRepository
from src.storage.repositories.prediction_repo import PredictionRepository

__all__ = ["MarketRepository", "PredictionRepository", "PositionRepository"]
