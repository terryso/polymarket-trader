"""FastAPI dependency injection for the Dashboard API.

This module provides dependency injection functions for FastAPI routes,
including database connections and state management.

Usage:
    from fastapi import Depends
    from src.dashboard.dependencies import get_db, get_state

    @router.get("/markets")
    async def list_markets(
        db: aiosqlite.Connection = Depends(get_db),
        state: ThreadSafeState = Depends(get_state)
    ):
        ...
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

import aiosqlite

from src.core.state import ThreadSafeState, get_state_manager
from src.storage.database import get_connection

logger = logging.getLogger(__name__)

# Global state instance (lazy initialization)
_state: ThreadSafeState | None = None


def get_state() -> ThreadSafeState:
    """Get the system state manager.

    Returns the singleton ThreadSafeState instance for accessing
    and managing trading state (capital, PnL, positions, etc.).

    Thread Safety:
        The returned ThreadSafeState instance uses asyncio.Lock for
        thread-safe access. All state access methods are async and
        properly synchronized.

    Returns:
        ThreadSafeState: The state manager instance

    Example:
        >>> @router.get("/status")
        ... async def get_status(state: ThreadSafeState = Depends(get_state)):
        ...     snapshot = await state.get_state()
        ...     return {"capital": snapshot.current_capital}
    """
    global _state
    if _state is None:
        _state = get_state_manager()
    return _state


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Get a database connection.

    Provides an async context manager that yields a database connection
    and ensures proper cleanup after the request.

    Yields:
        aiosqlite.Connection: Database connection

    Example:
        >>> @router.get("/markets")
        ... async def list_markets(db: aiosqlite.Connection = Depends(get_db)):
        ...     cursor = await db.execute("SELECT * FROM markets")
        ...     rows = await cursor.fetchall()
        ...     return rows
    """
    async with get_connection() as conn:
        yield conn


__all__ = ["get_state", "get_db"]
