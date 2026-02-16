"""Data storage modules: database, repositories, and market fetching.

This package provides database initialization, connection management,
repository pattern for data access, and market data fetching service.

Usage:
    from src.storage import init_db, get_connection, MarketFetcher, PredictionRepository

    # Initialize database
    await init_db()

    # Fetch and store markets
    fetcher = MarketFetcher()
    count = await fetcher.fetch_and_store_markets()

    # Save prediction
    prediction_repo = PredictionRepository()
    await prediction_repo.save_prediction(prediction)
"""

from __future__ import annotations

from src.storage.database import (
    DatabaseConfig,
    DatabaseManager,
    get_connection,
    get_db_manager,
    init_db,
)
from src.storage.market_fetcher import MarketFetcher
from src.storage.repositories import MarketRepository, PredictionRepository

__all__ = [
    # Database
    "DatabaseConfig",
    "DatabaseManager",
    "get_connection",
    "get_db_manager",
    "init_db",
    # Repositories
    "MarketRepository",
    "PredictionRepository",
    # Services
    "MarketFetcher",
]
