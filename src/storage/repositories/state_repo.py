"""State repository for system state persistence.

This module provides the StateRepository class for managing
system state data in the SQLite database.

Story 8.4: Auto Recovery Mechanism

Usage:
    from src.storage.repositories.state_repo import StateRepository

    repo = StateRepository()
    await repo.save_state({"current_capital": 150.0, "trading_enabled": True})
    state = await repo.load_state()
"""

from __future__ import annotations

__all__ = ["StateRepository"]

from datetime import datetime
from typing import Any

import aiosqlite

from src.storage.database import get_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StateRepository:
    """Repository for system state persistence.

    Provides async methods for managing system state in the database.
    Uses key-value storage with serialization for complex types.

    Attributes:
        KEY_CAPITAL: Key for current capital
        KEY_DAILY_PNL: Key for daily profit/loss
        KEY_CONSECUTIVE_LOSSES: Key for consecutive loss count
        KEY_OPEN_POSITIONS: Key for open positions count
        KEY_TRADING_ENABLED: Key for trading enabled flag
        KEY_REDUCED_MODE: Key for reduced mode flag
        KEY_LAST_MARKET_FETCH: Key for last market fetch timestamp
        KEY_START_TIME: Key for system start time
        KEY_LAST_ERROR: Key for last error message

    Example:
        >>> repo = StateRepository()
        >>> await repo.save_state({"current_capital": 150.0})
        >>> state = await repo.load_state()
        >>> print(state["current_capital"])
        150.0
    """

    # State key constants
    KEY_CAPITAL = "current_capital"
    KEY_DAILY_PNL = "daily_pnl"
    KEY_CONSECUTIVE_LOSSES = "consecutive_losses"
    KEY_OPEN_POSITIONS = "open_positions_count"
    KEY_TRADING_ENABLED = "trading_enabled"
    KEY_REDUCED_MODE = "reduced_mode"
    KEY_LAST_MARKET_FETCH = "last_market_fetch"
    KEY_START_TIME = "start_time"
    KEY_LAST_ERROR = "last_error"

    def __init__(self) -> None:
        """Initialize the StateRepository."""
        pass

    async def save_state(self, state: dict[str, Any]) -> None:
        """Save system state to database.

        Serializes and stores all key-value pairs from the state dictionary.
        Uses UPSERT (INSERT OR REPLACE) to handle both insert and update.

        Args:
            state: Dictionary of state key-value pairs to save

        Example:
            >>> await repo.save_state({
            ...     "current_capital": 150.0,
            ...     "trading_enabled": True,
            ...     "consecutive_losses": 2,
            ... })
        """
        async with get_connection() as conn:
            for key, value in state.items():
                serialized_value = self._serialize_value(value)
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO system_state (key, value, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (key, serialized_value, datetime.utcnow().isoformat()),
                )
            await conn.commit()
        logger.debug(f"State saved: {len(state)} keys")

    async def load_state(self) -> dict[str, Any]:
        """Load system state from database.

        Retrieves all key-value pairs from the system_state table
        and deserializes them to their original types.

        Returns:
            Dictionary of all stored state key-value pairs

        Example:
            >>> state = await repo.load_state()
            >>> print(state.get("current_capital", 0))
            150.0
        """
        state: dict[str, Any] = {}
        async with get_connection() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT key, value, updated_at FROM system_state"
            )
            rows = await cursor.fetchall()

            for row in rows:
                key = row["key"]
                value = row["value"]
                state[key] = self._deserialize_value(value)

        logger.debug(f"State loaded: {len(state)} keys")
        return state

    async def get_state_value(self, key: str) -> Any | None:
        """Get a single state value by key.

        Args:
            key: The state key to retrieve

        Returns:
            The deserialized value if found, None otherwise

        Example:
            >>> capital = await repo.get_state_value("current_capital")
            >>> print(capital)
            150.0
        """
        async with get_connection() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT value FROM system_state WHERE key = ?", (key,)
            )
            row = await cursor.fetchone()

            if row:
                return self._deserialize_value(row["value"])
        return None

    async def set_state_value(self, key: str, value: Any) -> None:
        """Set a single state value by key.

        Args:
            key: The state key to set
            value: The value to store (will be serialized)

        Example:
            >>> await repo.set_state_value("current_capital", 150.0)
        """
        serialized_value = self._serialize_value(value)
        async with get_connection() as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO system_state (key, value, updated_at)
                VALUES (?, ?, ?)
                """,
                (key, serialized_value, datetime.utcnow().isoformat()),
            )
            await conn.commit()

    async def clear_state(self) -> None:
        """Clear all state from database.

        Removes all entries from the system_state table.
        Use with caution - this operation cannot be undone.

        Example:
            >>> await repo.clear_state()
        """
        async with get_connection() as conn:
            await conn.execute("DELETE FROM system_state")
            await conn.commit()
        logger.warning("State cleared")

    def _serialize_value(self, value: Any) -> str:
        """Serialize a value to string for database storage.

        Handles common Python types including None, bool, int, float,
        datetime, dict, and list.

        Args:
            value: The value to serialize

        Returns:
            String representation of the value
        """
        import json

        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, (dict, list)):
            return json.dumps(value)
        else:
            return str(value)

    def _deserialize_value(self, value: str) -> Any:
        """Deserialize a string value to its original type.

        Attempts to restore the original type based on the string format.
        Falls back to returning the string if type detection fails.

        Args:
            value: The string value to deserialize

        Returns:
            The deserialized value with its original type
        """
        import json

        if value == "null":
            return None
        elif value == "true":
            return True
        elif value == "false":
            return False
        elif value.startswith("{") or value.startswith("["):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        else:
            # Try to parse as number
            try:
                if "." in value:
                    return float(value)
                return int(value)
            except ValueError:
                return value
