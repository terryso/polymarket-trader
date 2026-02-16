"""FastAPI route modules.

This module exports all route modules for the Dashboard API.
"""

from src.dashboard.routes import markets, positions, predictions, statistics, trades

__all__ = ["markets", "trades", "positions", "predictions", "statistics"]
