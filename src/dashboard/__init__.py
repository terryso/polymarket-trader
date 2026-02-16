"""FastAPI backend: app and routes.

This module provides the Dashboard API for the Polymarket Trader system.

Usage:
    from src.dashboard import app
    from src.dashboard.dependencies import get_db, get_state
"""

from src.dashboard.app import app, create_app
from src.dashboard.dependencies import get_db, get_state

__all__ = ["app", "create_app", "get_db", "get_state"]
