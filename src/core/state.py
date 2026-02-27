"""Thread-safe state management for the Polymarket Trader application.

This module provides a thread-safe state manager that handles trading state
including capital, PnL, and risk control flags.

Example:
    >>> from src.core.state import ThreadSafeState, get_state_manager
    >>>
    >>> # Get singleton instance
    >>> state = get_state_manager()
    >>>
    >>> # Get current state snapshot
    >>> snapshot = await state.get_state()
    >>> print(f"Capital: ${snapshot.current_capital:.2f}")
    >>>
    >>> # Update capital
    >>> await state.update_capital(10.0)
    >>>
    >>> # Persist state to database
    >>> await state.persist()
"""

from __future__ import annotations

__all__ = ["StateSnapshot", "ThreadSafeState", "get_state_manager"]

import asyncio
import json
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from src.config import settings
from src.storage.database import get_connection
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.core.recovery import RecoveryResult

logger = get_logger(__name__)


class StateSnapshot(BaseModel):
    """Immutable snapshot of trading state.

    This model represents a point-in-time snapshot of the trading state.
    It is frozen (immutable) to prevent accidental modification of state
    outside of the ThreadSafeState manager.

    Attributes:
        current_capital: Current capital in USD
        daily_pnl: Daily profit/loss
        consecutive_losses: Number of consecutive losing trades
        open_positions_count: Number of currently open positions
        trading_enabled: Whether trading is enabled
        reduced_mode: Whether system is in reduced position mode
        updated_at: Timestamp of last update

    Example:
        >>> snapshot = StateSnapshot(current_capital=200.0)
        >>> snapshot.current_capital
        200.0
        >>> snapshot.daily_pnl
        0.0
    """

    model_config = ConfigDict(frozen=True)

    current_capital: float
    daily_pnl: float = 0.0
    consecutive_losses: int = 0
    open_positions_count: int = 0
    trading_enabled: bool = True
    reduced_mode: bool = False
    updated_at: datetime | None = None

    def to_dict(self) -> dict:
        """Serialize snapshot to a JSON-compatible dictionary.

        Returns:
            dict: Dictionary representation of the snapshot

        Example:
            >>> snapshot = StateSnapshot(current_capital=200.0, daily_pnl=10.0)
            >>> data = snapshot.to_dict()
            >>> data["current_capital"]
            200.0
        """
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> "StateSnapshot":
        """Create a StateSnapshot from a dictionary.

        Args:
            data: Dictionary containing snapshot data

        Returns:
            StateSnapshot: New snapshot instance

        Example:
            >>> data = {"current_capital": 200.0, "daily_pnl": 10.0}
            >>> snapshot = StateSnapshot.from_dict(data)
            >>> snapshot.current_capital
            200.0
        """
        return cls(**data)


class ThreadSafeState:
    """Thread-safe state manager for trading state.

    Uses asyncio.Lock to ensure safe concurrent access to state.
    Supports persistence to database for recovery.

    All state access methods are async and use the lock to ensure
    thread safety in an async environment.

    Attributes:
        _capital: Current capital
        _daily_pnl: Daily profit/loss
        _consecutive_losses: Consecutive loss count
        _open_positions_count: Open positions count
        _trading_enabled: Trading enabled flag
        _reduced_mode: Reduced mode flag
        _lock: Async lock for thread safety

    Example:
        >>> state = ThreadSafeState(initial_capital=200.0)
        >>> snapshot = await state.get_state()
        >>> snapshot.current_capital
        200.0
        >>> await state.update_capital(50.0)
        >>> snapshot = await state.get_state()
        >>> snapshot.current_capital
        250.0
    """

    def __init__(self, initial_capital: float | None = None) -> None:
        """Initialize state manager.

        Args:
            initial_capital: Initial capital amount (defaults to settings.initial_capital)
        """
        self._capital: float = (
            initial_capital if initial_capital is not None else settings.initial_capital
        )
        self._daily_pnl: float = 0.0
        self._consecutive_losses: int = 0
        self._open_positions_count: int = 0
        self._trading_enabled: bool = True
        self._reduced_mode: bool = False
        # Lock is created lazily to handle different event loops
        self._lock: asyncio.Lock | None = None
        self._lock_loop_id: int | None = None

    def _get_lock(self) -> asyncio.Lock:
        """Get or create lock for current event loop.

        This ensures the lock is always bound to the current event loop,
        which is necessary when using asyncio.run() in scheduled tasks.

        Returns:
            asyncio.Lock bound to current event loop
        """
        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)
            if self._lock is None or self._lock_loop_id != loop_id:
                self._lock = asyncio.Lock()
                self._lock_loop_id = loop_id
            return self._lock
        except RuntimeError:
            # No running loop, create a new lock
            if self._lock is None:
                self._lock = asyncio.Lock()
            return self._lock

    async def get_state(self) -> StateSnapshot:
        """Get current state snapshot.

        Returns an immutable copy of the current state, safe to use
        without affecting the internal state.

        Returns:
            StateSnapshot: Immutable copy of current state

        Example:
            >>> snapshot = await state.get_state()
            >>> snapshot.current_capital
            200.0
        """
        async with self._get_lock():
            return StateSnapshot(
                current_capital=self._capital,
                daily_pnl=self._daily_pnl,
                consecutive_losses=self._consecutive_losses,
                open_positions_count=self._open_positions_count,
                trading_enabled=self._trading_enabled,
                reduced_mode=self._reduced_mode,
                updated_at=datetime.utcnow(),
            )

    async def update_capital(self, amount: float) -> None:
        """Update capital and daily PnL.

        Adds the specified amount to both current capital and daily PnL.
        Positive amounts represent gains, negative amounts represent losses.

        Args:
            amount: Amount to add (positive) or subtract (negative)

        Example:
            >>> await state.update_capital(10.0)  # Gain $10
            >>> await state.update_capital(-5.0)  # Loss $5
        """
        async with self._get_lock():
            self._capital += amount
            self._daily_pnl += amount
            logger.info(
                f"Capital updated: ${self._capital:.2f} (daily PnL: ${self._daily_pnl:.2f})"
            )

    async def record_trade_result(self, is_win: bool) -> None:
        """Record trade result for consecutive loss tracking.

        When a winning trade is recorded, consecutive losses are reset to 0.
        When a losing trade is recorded, consecutive losses are incremented.

        Args:
            is_win: Whether the trade was profitable

        Example:
            >>> await state.record_trade_result(True)   # Win, reset losses
            >>> await state.record_trade_result(False)  # Loss, increment
        """
        async with self._get_lock():
            if is_win:
                self._consecutive_losses = 0
                logger.info("Trade result: WIN, consecutive losses reset to 0")
            else:
                self._consecutive_losses += 1
                logger.warning(
                    f"Trade result: LOSS, consecutive losses: {self._consecutive_losses}"
                )

    async def reset_daily(self) -> None:
        """Reset daily state (called at market open or day start).

        Resets daily_pnl and consecutive_losses to their initial values.
        Does NOT reset current_capital.

        Example:
            >>> await state.reset_daily()
        """
        async with self._get_lock():
            self._daily_pnl = 0.0
            self._consecutive_losses = 0
            logger.info("Daily state reset: daily_pnl=0, consecutive_losses=0")

    async def set_trading_enabled(self, enabled: bool) -> None:
        """Set trading enabled flag.

        When trading is disabled, no new trades should be executed.

        Args:
            enabled: Whether trading should be enabled

        Example:
            >>> await state.set_trading_enabled(False)  # Disable trading
        """
        async with self._get_lock():
            self._trading_enabled = enabled
            status = "enabled" if enabled else "DISABLED"
            logger.info(f"Trading {status}")

    async def set_mode(self, paper_trading: bool) -> None:
        """Set trading mode.

        Story 9.11: Telegram 命令处理 - 远程控制

        Args:
            paper_trading: True for Paper Trading, False for Live Trading

        Example:
            >>> await state.set_mode(paper_trading=True)  # Switch to Paper
        """
        async with self._get_lock():
            # Update settings (runtime)
            settings.trading_mode = "paper" if paper_trading else "live"  # type: ignore[attr-defined]
            mode = "PAPER" if paper_trading else "LIVE"
            logger.info(f"Trading mode set to {mode}")

    async def set_reduced_mode(self, reduced: bool) -> None:
        """Set reduced mode flag.

        When reduced mode is active, position sizes should be reduced
        according to risk control settings.

        Args:
            reduced: Whether to enter reduced mode

        Example:
            >>> await state.set_reduced_mode(True)  # Enter reduced mode
        """
        async with self._get_lock():
            self._reduced_mode = reduced
            status = "ENTERING" if reduced else "EXITING"
            logger.warning(f"{status} reduced mode")

    async def increment_open_positions(self) -> None:
        """Increment open positions count.

        Called when a new position is opened.

        Example:
            >>> await state.increment_open_positions()
        """
        async with self._get_lock():
            self._open_positions_count += 1
            logger.info(f"Open positions: {self._open_positions_count}")

    async def decrement_open_positions(self) -> None:
        """Decrement open positions count.

        Called when a position is closed. Will not decrement below 0.

        Example:
            >>> await state.decrement_open_positions()
        """
        async with self._get_lock():
            self._open_positions_count = max(0, self._open_positions_count - 1)
            logger.info(f"Open positions: {self._open_positions_count}")

    async def persist(self) -> None:
        """Persist current state to database.

        Saves the current state to the system_state table for recovery
        on application restart.

        Example:
            >>> await state.persist()

        Raises:
            DatabaseError: If persistence fails
        """
        snapshot = await self.get_state()
        state_dict = snapshot.model_dump(mode="json")

        async with get_connection() as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO system_state (key, value, updated_at)
                VALUES (?, ?, ?)
                """,
                (
                    "trading_state",
                    json.dumps(state_dict),
                    datetime.utcnow().isoformat(),
                ),
            )
            await conn.commit()
            logger.info("State persisted to database")

    async def load_from_storage(self) -> "RecoveryResult":
        """Load state from storage using RecoveryManager.

        Uses the RecoveryManager to properly recover state with
        validation and consistency checks.

        Returns:
            RecoveryResult with recovery status and any warnings/errors

        Example:
            >>> result = await state.load_from_storage()
            >>> if result.success:
            ...     print("State loaded successfully")
        """
        from src.core.recovery import RecoveryManager
        from src.storage.repositories.position_repo import PositionRepository
        from src.storage.repositories.state_repo import StateRepository

        state_repo = StateRepository()
        position_repo = PositionRepository()

        recovery_manager = RecoveryManager(
            state_repo=state_repo,
            position_repo=position_repo,
            initial_capital=self._capital,
        )

        result = await recovery_manager.recover()

        if result.success:
            async with self._get_lock():
                self._capital = result.recovered_state.get(
                    "current_capital", self._capital
                )
                self._daily_pnl = result.recovered_state.get("daily_pnl", 0.0)
                self._consecutive_losses = result.recovered_state.get(
                    "consecutive_losses", 0
                )
                self._open_positions_count = result.recovered_state.get(
                    "open_positions_count", 0
                )
                self._trading_enabled = result.recovered_state.get(
                    "trading_enabled", True
                )
                self._reduced_mode = result.recovered_state.get("reduced_mode", False)

            for warning in result.warnings:
                logger.warning(warning)

            for error in result.errors:
                logger.error(error)

            logger.info("State loaded from storage")

        return result

    @classmethod
    async def restore(cls, initial_capital: float | None = None) -> "ThreadSafeState":
        """Restore state from database.

        Attempts to restore state from the system_state table. If no
        saved state exists or restoration fails, returns a new instance
        with default values.

        Args:
            initial_capital: Fallback initial capital if no state in database

        Returns:
            ThreadSafeState: Restored state manager instance

        Example:
            >>> state = await ThreadSafeState.restore()
            >>> snapshot = await state.get_state()
            >>> print(f"Restored capital: ${snapshot.current_capital:.2f}")
        """
        instance = cls(initial_capital)

        try:
            async with get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT value FROM system_state WHERE key = ?",
                    ("trading_state",),
                )
                row = await cursor.fetchone()

                if row:
                    state_dict = json.loads(row[0])
                    instance._capital = state_dict.get(
                        "current_capital", instance._capital
                    )
                    instance._daily_pnl = state_dict.get("daily_pnl", 0.0)
                    instance._consecutive_losses = state_dict.get(
                        "consecutive_losses", 0
                    )
                    instance._open_positions_count = state_dict.get(
                        "open_positions_count", 0
                    )
                    instance._trading_enabled = state_dict.get("trading_enabled", True)
                    instance._reduced_mode = state_dict.get("reduced_mode", False)
                    logger.info(
                        f"State restored from database: capital=${instance._capital:.2f}"
                    )
                else:
                    logger.info("No saved state found, using defaults")
        except Exception as e:
            logger.warning(f"Failed to restore state: {e}, using defaults")

        return instance


# Module-level singleton
_state_manager: ThreadSafeState | None = None


def get_state_manager() -> ThreadSafeState:
    """Get state manager singleton instance.

    Returns the global state manager instance, creating it if necessary.
    For persistence, use ThreadSafeState.restore() instead.

    Note: The state is initialized with default values. To load persisted
    state, call load_from_storage() after getting the manager.

    Returns:
        ThreadSafeState: The state manager instance

    Example:
        >>> state = get_state_manager()
        >>> await state.load_from_storage()  # Load persisted state
        >>> snapshot = await state.get_state()
    """
    global _state_manager
    if _state_manager is None:
        _state_manager = ThreadSafeState()
    return _state_manager


async def get_state_manager_with_recovery() -> ThreadSafeState:
    """Get state manager singleton instance with recovery.

    Returns the global state manager instance, creating it if necessary.
    If creating a new instance, it will load persisted state from storage.

    Returns:
        ThreadSafeState: The state manager instance with recovered state

    Example:
        >>> state = await get_state_manager_with_recovery()
        >>> snapshot = await state.get_state()
    """
    global _state_manager
    if _state_manager is None:
        _state_manager = ThreadSafeState()
        await _state_manager.load_from_storage()
    return _state_manager
