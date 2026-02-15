"""Data storage modules: database, repositories, and market fetching.

This package provides database initialization, connection management,
repository pattern for data access, and market data fetching service.

Usage:
    from src.storage import init_db, get_connection, MarketFetcher

    # Initialize database
    await init_db()

    # Fetch and store markets
    fetcher = MarketFetcher()
    count = await fetcher.fetch_and_store_markets()
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
from src.storage.repositories import MarketRepository

__all__ = [
    # Database
    "DatabaseConfig",
    "DatabaseManager",
    "get_connection",
    "get_db_manager",
    "init_db",
    # Repositories
    "MarketRepository",
    # Services
    "MarketFetcher",
]
