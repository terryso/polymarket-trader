"""Position synchronization service.

This module provides functionality to synchronize wallet positions from
Polymarket API to the local database.

Story 5.7: 同步实际持仓
"""

from __future__ import annotations

__all__ = ["PositionSyncService", "PositionSyncResult", "PositionSyncStatus"]

import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from src.api.polymarket import BalanceItem, BalanceResult, PolymarketClient
from src.config import settings
from src.models.position import Position, PositionOutcome, PositionStatus
from src.storage.repositories.position_repo import PositionRepository
from src.utils.logger import OPERATION_EMOJIS, get_logger

logger = get_logger(__name__)


@dataclass
class PositionSyncResult:
    """Result of a position sync operation.

    Attributes:
        new_positions: Number of new positions added
        updated_positions: Number of existing positions updated
        closed_positions: Number of positions closed (not on chain anymore)
        unchanged_positions: Number of positions that matched existing records
        total_fetched: Total number of balances fetched from API
        last_sync_at: Timestamp of this sync
        error: Error message if sync failed
    """

    new_positions: int = 0
    updated_positions: int = 0
    closed_positions: int = 0
    unchanged_positions: int = 0
    total_fetched: int = 0
    last_sync_at: datetime = field(default_factory=datetime.now)
    error: str | None = None

    @property
    def is_success(self) -> bool:
        """Check if sync was successful."""
        return self.error is None

    @property
    def total_processed(self) -> int:
        """Total number of positions processed."""
        return self.new_positions + self.updated_positions + self.unchanged_positions + self.closed_positions


@dataclass
class PositionSyncStatus:
    """Current sync status.

    Attributes:
        last_sync_at: Timestamp of last successful sync
        is_syncing: Whether a sync is currently in progress
        can_sync: Whether sync is possible (requires API credentials)
        last_error: Last error message if sync failed
        total_positions: Total number of open positions
    """

    last_sync_at: datetime | None = None
    is_syncing: bool = False
    can_sync: bool = False
    last_error: str | None = None
    total_positions: int = 0


class PositionSyncService:
    """Service for synchronizing wallet positions from Polymarket.

    Fetches position balances from Polymarket API and synchronizes them
    with the local database.

    Example:
        >>> service = PositionSyncService()
        >>> result = await service.sync_positions()
        >>> if result.is_success:
        ...     print(f"Synced {result.new_positions} new positions")
    """

    def __init__(self) -> None:
        """Initialize the position sync service."""
        self._position_repo = PositionRepository()
        self._syncing = False

    @property
    def can_sync(self) -> bool:
        """Check if sync is possible (requires private key and proxy wallet)."""
        return bool(settings.polymarket.pk and settings.polymarket.proxy_wallet)

    @property
    def is_syncing(self) -> bool:
        """Check if a sync is currently in progress."""
        return self._syncing

    async def get_sync_status(self) -> PositionSyncStatus:
        """Get current sync status.

        Returns:
            PositionSyncStatus with current sync information
        """
        # Get last sync time from database
        last_sync = await self._get_last_sync_time()
        open_positions = await self._position_repo.get_open_positions()

        return PositionSyncStatus(
            last_sync_at=last_sync,
            is_syncing=self._syncing,
            can_sync=self.can_sync,
            total_positions=len(open_positions),
        )

    async def sync_positions(self) -> PositionSyncResult:
        """Synchronize positions from Polymarket API.

        Fetches all position balances from Polymarket and syncs them with local database.
        In Paper mode, returns an appropriate message without syncing.

        Returns:
            PositionSyncResult with sync statistics
        """
        # Check for Paper mode
        if settings.trading_mode == "paper":
            return PositionSyncResult(
                error="Paper 模式无真实持仓。请切换到 Live 模式以同步实际持仓。",
            )

        if self._syncing:
            return PositionSyncResult(error="Sync already in progress")

        if not self.can_sync:
            return PositionSyncResult(
                error="Private key and proxy wallet not configured. "
                "Please set PK and YOUR_PROXY_WALLET in your .env file."
            )

        self._syncing = True
        logger.info(f"{OPERATION_EMOJIS['network']} Starting position sync...")

        client = None
        try:
            result = PositionSyncResult()
            client = PolymarketClient()

            # Fetch all balances using asyncio.to_thread for sync API call
            balance_result: BalanceResult = await asyncio.to_thread(client.get_balances)

            if not balance_result.is_success:
                result.error = balance_result.error
                return result

            all_balances = balance_result.balances
            result.total_fetched = len(all_balances)

            logger.info(
                f"{OPERATION_EMOJIS['network']} Fetched {len(all_balances)} balances from API"
            )

            # Get all local open positions
            local_positions = await self._position_repo.get_open_positions()
            local_by_market_outcome = {
                (p.market_id, p.outcome.value): p for p in local_positions
            }

            # Track which local positions were found on chain
            found_keys: set[tuple[str, str]] = set()

            # Sync each balance with local database
            for balance in all_balances:
                if balance.shares <= 0:
                    # Skip zero balances
                    continue

                sync_result = await self._sync_single_balance(balance, local_by_market_outcome)
                if sync_result == "new":
                    result.new_positions += 1
                elif sync_result == "updated":
                    result.updated_positions += 1
                elif sync_result == "unchanged":
                    result.unchanged_positions += 1

                # Mark as found
                outcome_key = balance.outcome.upper()
                if outcome_key not in ("YES", "NO"):
                    outcome_key = "YES"  # Default fallback
                found_keys.add((balance.condition_id, outcome_key))

            # Close positions not found on chain (sold/settled)
            for key, position in local_by_market_outcome.items():
                if key not in found_keys:
                    await self._close_position(position)
                    result.closed_positions += 1

            # Update last sync time
            await self._set_last_sync_time(result.last_sync_at)

            logger.info(
                f"{OPERATION_EMOJIS['network']} Sync complete: "
                f"{result.new_positions} new, {result.updated_positions} updated, "
                f"{result.unchanged_positions} unchanged, {result.closed_positions} closed"
            )

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"{OPERATION_EMOJIS['network']} Position sync failed: {error_msg}"
            )
            return PositionSyncResult(error=error_msg)

        finally:
            self._syncing = False
            if client:
                client.close()

    async def _sync_single_balance(
        self,
        balance: BalanceItem,
        local_positions: dict[tuple[str, str], Position],
    ) -> str:
        """Sync a single balance with the database.

        Args:
            balance: Balance from Polymarket API
            local_positions: Dictionary of local positions by (market_id, outcome)

        Returns:
            "new", "updated", or "unchanged"
        """
        # Ensure the market exists in local database (required for foreign key constraint)
        await self._ensure_market_exists(balance.condition_id)

        # Normalize outcome
        outcome_value = balance.outcome.upper()
        if outcome_value not in ("YES", "NO"):
            outcome_value = "YES"  # Default fallback

        key = (balance.condition_id, outcome_value)

        if key in local_positions:
            # Update existing position
            existing = local_positions[key]

            # Check if shares changed (with tolerance for float comparison)
            if abs(existing.shares - balance.shares) < 0.0001:
                return "unchanged"

            # Update shares
            existing.shares = balance.shares
            existing.current_value = balance.shares * existing.avg_price
            if existing.initial_value:
                existing.pnl = existing.current_value - existing.initial_value

            await self._position_repo.update(existing)
            return "updated"
        else:
            # Create new position
            # Use avg_price from balance if available, otherwise default to 0.5
            avg_price = balance.avg_price if balance.avg_price is not None else 0.5

            new_position = Position(
                id=0,  # Will be assigned by database
                market_id=balance.condition_id,
                outcome=PositionOutcome(outcome_value),
                shares=balance.shares,
                avg_price=avg_price,
                initial_value=balance.shares * avg_price,
                current_value=balance.shares * avg_price,
                pnl=0.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(),
            )
            await self._position_repo.save(new_position)
            return "new"

    async def _close_position(self, position: Position) -> None:
        """Close a position that is no longer on chain.

        Args:
            position: Position to close
        """
        position.status = PositionStatus.CLOSED
        position.closed_at = datetime.now()
        await self._position_repo.update(position)
        logger.info(
            f"{OPERATION_EMOJIS['data']} Closed position {position.id} for market {position.market_id}"
        )

    async def _ensure_market_exists(self, market_id: str) -> None:
        """Ensure market exists in local database for foreign key constraint.

        Args:
            market_id: Market condition ID
        """
        from src.storage.database import get_connection

        async with get_connection() as conn:
            # Check if market exists
            cursor = await conn.execute(
                "SELECT id FROM markets WHERE id = ?", (market_id,)
            )
            row = await cursor.fetchone()

            if row is None:
                # Create a placeholder market record
                logger.info(
                    f"{OPERATION_EMOJIS['data']} Creating placeholder market: "
                    f"{market_id[:10]}..."
                )
                await conn.execute(
                    """
                    INSERT OR IGNORE INTO markets (id, title, category, liquidity, deadline)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        market_id,
                        f"Synced Market {market_id[:8]}",
                        "Unknown",
                        0.0,
                        None,
                    ),
                )
                await conn.commit()

    async def _get_last_sync_time(self) -> datetime | None:
        """Get last sync time from system state."""
        from src.storage.database import get_connection

        async with get_connection() as conn:
            cursor = await conn.execute(
                "SELECT value FROM system_state WHERE key = 'last_position_sync'"
            )
            row = await cursor.fetchone()
            if row:
                return datetime.fromisoformat(row[0])
            return None

    async def _set_last_sync_time(self, sync_time: datetime) -> None:
        """Set last sync time in system state."""
        from src.storage.database import get_connection

        async with get_connection() as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO system_state (key, value, updated_at)
                VALUES ('last_position_sync', ?, ?)
                """,
                (sync_time.isoformat(), datetime.now().isoformat()),
            )
            await conn.commit()
