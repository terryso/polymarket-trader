"""Database repositories for data access.

This package provides repository classes for database operations
following the repository pattern.

Usage:
    from src.storage.repositories import MarketRepository

    repo = MarketRepository()
    await repo.save_market(market)
"""

from __future__ import annotations

from src.storage.repositories.market_repo import MarketRepository

__all__ = ["MarketRepository"]
