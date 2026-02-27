"""Recovery manager for system state restoration.

This module provides the RecoveryManager class for recovering
system state after crashes or restarts.

Story 8.4: Auto Recovery Mechanism

Usage:
    from src.core.recovery import RecoveryManager, RecoveryResult
    from src.storage.repositories.state_repo import StateRepository

    repo = StateRepository()
    manager = RecoveryManager(state_repo=repo, initial_capital=200.0)
    result = await manager.recover()
    if result.success:
        print(f"Recovered state: {result.recovered_state}")
"""

from __future__ import annotations

__all__ = ["RecoveryResult", "RecoveryManager"]

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.config import settings
from src.storage.repositories.position_repo import PositionRepository
from src.storage.repositories.state_repo import StateRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RecoveryResult:
    """Result of a state recovery operation.

    Attributes:
        success: Whether recovery was successful
        recovered_state: The recovered state dictionary
        warnings: List of warning messages during recovery
        errors: List of error messages during recovery

    Example:
        >>> result = RecoveryResult(success=True)
        >>> result.recovered_state["current_capital"] = 150.0
        >>> if result.warnings:
        ...     print(f"Warnings: {result.warnings}")
    """

    success: bool
    recovered_state: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class RecoveryManager:
    """System state recovery manager.

    Handles state recovery from database, position validation,
    and consistency checking. Provides safe defaults when
    recovery fails or state is inconsistent.

    Attributes:
        DEFAULT_SAFE_STATE: Default safe state values

    Example:
        >>> manager = RecoveryManager(state_repo=repo, initial_capital=200.0)
        >>> result = await manager.recover()
        >>> if result.success:
        ...     state = result.recovered_state
    """

    # Default safe state - trading disabled for safety
    DEFAULT_SAFE_STATE: dict[str, Any] = {
        "current_capital": 0.0,
        "daily_pnl": 0.0,
        "consecutive_losses": 0,
        "open_positions_count": 0,
        "trading_enabled": False,  # Safe default
        "reduced_mode": False,
        "last_market_fetch": None,
        "start_time": None,
        "last_error": None,
    }

    def __init__(
        self,
        state_repo: StateRepository,
        position_repo: PositionRepository | None = None,
        initial_capital: float | None = None,
    ) -> None:
        """Initialize the RecoveryManager.

        Args:
            state_repo: Repository for state persistence
            position_repo: Optional repository for position validation
            initial_capital: Initial capital amount (defaults to settings.initial_capital)
        """
        self.state_repo = state_repo
        self.position_repo = position_repo
        self.initial_capital = initial_capital or settings.initial_capital

    async def recover(self) -> RecoveryResult:
        """Execute system recovery.

        Performs the following steps:
        1. Load saved state from database
        2. Merge with default values
        3. Sync capital from Polymarket (LIVE mode only)
        4. Validate position consistency
        5. Check state consistency
        6. Return recovery result

        Returns:
            RecoveryResult with recovered state, warnings, and errors

        Example:
            >>> result = await manager.recover()
            >>> if result.success:
            ...     print(f"Capital: {result.recovered_state['current_capital']}")
        """
        logger.info("Starting system recovery...")
        result = RecoveryResult(success=True)

        try:
            # 1. Load state from database
            saved_state = await self.state_repo.load_state()
            logger.info(f"Loaded {len(saved_state)} state keys from database")

            # 2. Merge with defaults
            result.recovered_state = self._merge_with_defaults(saved_state)

            # 3. Sync capital from Polymarket in LIVE mode
            if settings.trading_mode == "live":
                actual_capital = await self._sync_capital_from_polymarket()
                if actual_capital is not None:
                    old_capital = result.recovered_state.get("current_capital", 0)
                    result.recovered_state["current_capital"] = actual_capital
                    # Reset reduced_mode if capital is now above threshold
                    if actual_capital >= settings.risk.capital_threshold:
                        result.recovered_state["reduced_mode"] = False
                    logger.info(
                        f"Capital synced from Polymarket: ${actual_capital:.2f} "
                        f"(was ${old_capital:.2f})"
                    )
                    result.warnings.append(
                        f"Capital synced from Polymarket: ${actual_capital:.2f}"
                    )

            # 3. Validate positions if repository available
            if self.position_repo:
                position_warnings = await self._validate_positions(result.recovered_state)
                result.warnings.extend(position_warnings)

            # 4. Check consistency
            consistency_errors = self._check_consistency(result.recovered_state)
            if consistency_errors:
                result.errors.extend(consistency_errors)
                # Disable trading on inconsistency for safety
                result.recovered_state["trading_enabled"] = False
                result.warnings.append(
                    "State inconsistency detected, trading disabled for safety"
                )

            # 5. Log recovery result
            logger.info(
                f"Recovery complete: {len(result.warnings)} warnings, "
                f"{len(result.errors)} errors"
            )

        except Exception as e:
            result.success = False
            result.errors.append(f"Recovery failed: {str(e)}")
            logger.error(f"Recovery failed: {e}")
            # Return safe default state
            result.recovered_state = self.DEFAULT_SAFE_STATE.copy()
            result.recovered_state["current_capital"] = self.initial_capital

        return result

    def _merge_with_defaults(self, saved_state: dict[str, Any]) -> dict[str, Any]:
        """Merge saved state with default values.

        Ensures all expected keys are present by filling in defaults
        for missing keys.

        Args:
            saved_state: State loaded from database

        Returns:
            Complete state dictionary with all keys
        """
        merged = self.DEFAULT_SAFE_STATE.copy()

        for key, value in saved_state.items():
            merged[key] = value

        # Ensure current_capital has a valid value
        if merged["current_capital"] == 0.0:
            merged["current_capital"] = self.initial_capital

        return merged

    async def _sync_capital_from_polymarket(self) -> float | None:
        """Sync capital from Polymarket wallet balance.

        Fetches the actual USDC balance from Polymarket and returns it.
        This ensures the system's capital tracking matches reality after
        manual trades or external changes.

        Returns:
            Actual USDC balance from Polymarket, or None if fetch failed
        """
        try:
            import asyncio

            from src.api.polymarket import PolymarketClient

            client = PolymarketClient()
            try:
                # Use asyncio.to_thread since get_wallet_balance is sync
                balance_result = await asyncio.to_thread(client.get_wallet_balance)
                if balance_result.is_success:
                    balance = balance_result.usdc_balance
                    logger.info(f"Fetched Polymarket wallet balance: ${balance:.2f} USDC")
                    return balance
                else:
                    logger.warning(f"Failed to get wallet balance: {balance_result.error}")
                    return None
            finally:
                client.close()
        except Exception as e:
            logger.warning(f"Failed to sync capital from Polymarket: {e}")
            return None

    async def _validate_positions(self, state: dict[str, Any]) -> list[str]:
        """Validate position data consistency.

        Compares the recorded open positions count with the actual
        count in the database.

        Args:
            state: State dictionary to validate (may be modified)

        Returns:
            List of warning messages
        """
        warnings: list[str] = []

        if not self.position_repo:
            return warnings

        try:
            # Get actual open positions from database
            open_positions = await self.position_repo.get_open_positions()
            actual_count = len(open_positions)
            recorded_count = state.get("open_positions_count", 0)

            if actual_count != recorded_count:
                warning = (
                    f"Position count mismatch: "
                    f"database={actual_count}, state={recorded_count}"
                )
                warnings.append(warning)
                logger.warning(warning)

                # Update state to match reality
                state["open_positions_count"] = actual_count

        except Exception as e:
            warning = f"Failed to validate positions: {str(e)}"
            warnings.append(warning)
            logger.error(f"Position validation error: {e}")

        return warnings

    def _check_consistency(self, state: dict[str, Any]) -> list[str]:
        """Check state consistency.

        Validates that state values are reasonable and consistent.

        Args:
            state: State dictionary to check

        Returns:
            List of error messages (empty if consistent)
        """
        errors: list[str] = []

        # Check for negative capital
        if state.get("current_capital", 0) < 0:
            errors.append(f"Negative capital: {state['current_capital']}")

        # Check for negative consecutive losses
        if state.get("consecutive_losses", 0) < 0:
            errors.append(f"Negative consecutive losses: {state['consecutive_losses']}")

        # Note: We don't check if daily_pnl exceeds capital because:
        # - daily_pnl tracks cumulative P&L for the day
        # - capital reflects current available funds after losses
        # - It's valid to have daily_pnl=-71 and capital=32 (started with ~103, lost 71)

        return errors

    async def save_state_snapshot(self, state: dict[str, Any]) -> None:
        """Save a state snapshot to database.

        Args:
            state: State dictionary to save

        Example:
            >>> await manager.save_state_snapshot({"current_capital": 150.0})
        """
        await self.state_repo.save_state(state)
        logger.debug("State snapshot saved")

    async def reset_to_safe_state(self) -> dict[str, Any]:
        """Reset system to safe default state.

        Creates a new safe state with trading disabled and saves it
        to the database.

        Returns:
            The safe state dictionary

        Example:
            >>> safe_state = await manager.reset_to_safe_state()
            >>> print(safe_state["trading_enabled"])  # False
        """
        safe_state = self.DEFAULT_SAFE_STATE.copy()
        safe_state["current_capital"] = self.initial_capital
        safe_state["start_time"] = datetime.utcnow().isoformat()

        await self.state_repo.save_state(safe_state)
        logger.warning("Reset to safe state")

        return safe_state
