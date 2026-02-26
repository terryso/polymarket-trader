"""Position cache service.

This module provides functionality to manage position cache from
Polymarket API to the local database.

Story 5.7: 同步实际持仓
Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源
"""

from __future__ import annotations

__all__ = [
    "PositionCacheService",
    "CacheRefreshResult",
    "CacheStatus",
    # Deprecated aliases for backward compatibility
    "PositionSyncService",
    "PositionSyncResult",
    "PositionSyncStatus",
]

import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from src.api.polymarket import BalanceItem, BalanceResult, PolymarketClient
from src.config import settings
from src.models.position import CacheFreshness, Position, PositionOutcome, PositionStatus
from src.storage.repositories.position_repo import PositionRepository
from src.utils.logger import OPERATION_EMOJIS, get_logger

logger = get_logger(__name__)


@dataclass
class CacheRefreshResult:
    """Result of a cache refresh operation.

    Attributes:
        new_positions: Number of new positions added
        updated_positions: Number of existing positions updated
        closed_positions: Number of positions closed (not on chain anymore)
        unchanged_positions: Number of positions that matched existing records
        total_fetched: Total number of balances fetched from API
        refreshed_at: Timestamp of this refresh
        error: Error message if refresh failed
    """

    new_positions: int = 0
    updated_positions: int = 0
    closed_positions: int = 0
    unchanged_positions: int = 0
    total_fetched: int = 0
    refreshed_at: datetime = field(default_factory=datetime.now)
    error: str | None = None

    @property
    def is_success(self) -> bool:
        """Check if refresh was successful."""
        return self.error is None

    @property
    def total_processed(self) -> int:
        """Total number of positions processed."""
        return self.new_positions + self.updated_positions + self.unchanged_positions + self.closed_positions

    # Backward compatibility alias
    @property
    def last_sync_at(self) -> datetime | None:
        """Deprecated: Use refreshed_at instead."""
        return self.refreshed_at


@dataclass
class CacheStatus:
    """Current cache status.

    Attributes:
        cache_updated_at: Timestamp of last successful cache refresh
        cache_age_seconds: Age of cache in seconds
        cache_freshness: Current freshness state (FRESH, STALE, EXPIRED)
        is_refreshing: Whether a refresh is currently in progress
        can_refresh: Whether refresh is possible (requires API credentials)
        last_error: Last error message if refresh failed
        total_positions: Total number of open positions
    """

    cache_updated_at: datetime | None = None
    cache_age_seconds: int = 0
    cache_freshness: CacheFreshness = CacheFreshness.EXPIRED
    is_refreshing: bool = False
    can_refresh: bool = False
    last_error: str | None = None
    total_positions: int = 0

    # Backward compatibility alias
    @property
    def last_sync_at(self) -> datetime | None:
        """Deprecated: Use cache_updated_at instead."""
        return self.cache_updated_at


class PositionCacheService:
    """Service for managing position cache from Polymarket.

    Fetches position balances from Polymarket API and caches them
    in the local database. Polymarket is the single source of truth.

    Thread-safe: Uses asyncio.Lock to prevent concurrent refresh operations.

    Example:
        >>> service = PositionCacheService()
        >>> result = await service.refresh_cache()
        >>> if result.is_success:
        ...     print(f"Refreshed cache with {result.new_positions} new positions")
    """

    _instance: PositionCacheService | None = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls) -> PositionCacheService:
        """Singleton pattern to prevent multiple repository instances."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._position_repo = PositionRepository()
            cls._instance._refreshing = False
            cls._instance._refresh_lock = asyncio.Lock()
        return cls._instance

    def __init__(self) -> None:
        """Initialize the position cache service (idempotent due to singleton)."""
        # Initialization is done in __new__ to ensure singleton pattern works correctly
        pass

    @classmethod
    def _reset_instance(cls) -> None:
        """Reset the singleton instance. For testing purposes only."""
        cls._instance = None
        cls._lock = asyncio.Lock()

    @property
    def can_refresh(self) -> bool:
        """Check if refresh is possible (requires private key and proxy wallet)."""
        return bool(settings.polymarket.pk and settings.polymarket.proxy_wallet)

    @property
    def is_refreshing(self) -> bool:
        """Check if a refresh is currently in progress."""
        return self._refreshing

    async def get_cache_status(self) -> CacheStatus:
        """Get current cache status.

        Returns:
            CacheStatus with current cache information
        """
        # Get last cache time from database
        cache_updated_at = await self._get_cache_updated_time()
        open_positions = await self._position_repo.get_open_positions()

        # Calculate cache age and freshness
        cache_age_seconds = 0
        cache_freshness = CacheFreshness.EXPIRED

        if cache_updated_at:
            age_delta = datetime.now() - cache_updated_at
            cache_age_seconds = int(age_delta.total_seconds())

            if cache_age_seconds < settings.position_cache.ttl:
                cache_freshness = CacheFreshness.FRESH
            else:
                cache_freshness = CacheFreshness.STALE

        return CacheStatus(
            cache_updated_at=cache_updated_at,
            cache_age_seconds=cache_age_seconds,
            cache_freshness=cache_freshness,
            is_refreshing=self._refreshing,
            can_refresh=self.can_refresh,
            total_positions=len(open_positions),
        )

    async def refresh_cache(self) -> CacheRefreshResult:
        """Refresh position cache from Polymarket API.

        Fetches all position balances from Polymarket and caches them in local database.
        In Paper mode, returns an appropriate message without refreshing.

        Thread-safe: Uses asyncio.Lock to prevent concurrent refresh operations.

        Returns:
            CacheRefreshResult with refresh statistics
        """
        # Check for Paper mode
        if settings.trading_mode == "paper":
            return CacheRefreshResult(
                error="Paper 模式无真实持仓。请切换到 Live 模式以刷新实际持仓。",
            )

        # Use lock to prevent concurrent refreshes
        if self._refresh_lock.locked():
            return CacheRefreshResult(error="Refresh already in progress")

        if not self.can_refresh:
            return CacheRefreshResult(
                error="Private key and proxy wallet not configured. "
                "Please set PK and YOUR_PROXY_WALLET in your .env file."
            )

        # Check minimum refresh interval
        last_refresh = await self._get_cache_updated_time()
        if last_refresh:
            elapsed = (datetime.now() - last_refresh).total_seconds()
            if elapsed < settings.position_cache.min_refresh_interval:
                logger.warning(
                    f"{OPERATION_EMOJIS['warning']} Refresh throttled: "
                    f"{settings.position_cache.min_refresh_interval}s min interval"
                )
                return CacheRefreshResult(
                    error=f"Refresh throttled. Please wait {int(settings.position_cache.min_refresh_interval - elapsed)}s."
                )

        # Acquire lock for the entire refresh operation
        async with self._refresh_lock:
            self._refreshing = True
            logger.info(f"{OPERATION_EMOJIS['network']} Starting position cache refresh...")

            client = None
            try:
                result = CacheRefreshResult()
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

                # Update cache timestamp
                await self._set_cache_updated_time(result.refreshed_at)

                logger.info(
                    f"{OPERATION_EMOJIS['network']} Cache refresh complete: "
                    f"{result.new_positions} new, {result.updated_positions} updated, "
                    f"{result.unchanged_positions} unchanged, {result.closed_positions} closed"
                )

                return result

            except Exception as e:
                error_msg = str(e)
                logger.error(
                    f"{OPERATION_EMOJIS['network']} Cache refresh failed: {error_msg}"
                )
                return CacheRefreshResult(error=error_msg)

            finally:
                self._refreshing = False
                if client:
                    client.close()

    async def get_positions(
        self,
        force_refresh: bool = False
    ) -> tuple[list[Position], CacheFreshness]:
        """Get positions with cache.

        Returns positions from cache if fresh, otherwise refreshes from API.

        Args:
            force_refresh: Force refresh from API (ignores TTL, but respects min_interval)

        Returns:
            tuple of (positions, freshness) - freshness indicates cache state
        """
        # Check current cache status
        status = await self.get_cache_status()

        # Determine if refresh is needed
        need_refresh = force_refresh or status.cache_freshness != CacheFreshness.FRESH

        if need_refresh and not status.is_refreshing:
            # Try to refresh
            refresh_result = await self.refresh_cache()
            if refresh_result.is_success:
                status = await self.get_cache_status()
            elif status.cache_freshness == CacheFreshness.STALE:
                # API failed but we have stale data, use it
                logger.warning(
                    f"{OPERATION_EMOJIS['warning']} Using stale cache due to API error: {refresh_result.error}"
                )

        # Get positions from database (cache)
        positions = await self._position_repo.get_open_positions()

        return positions, status.cache_freshness

    async def mark_stale(self) -> None:
        """Mark cache as stale.

        Called after trade execution to indicate cache needs refresh.
        """
        from datetime import timedelta

        # Set cache_updated_at to a time that makes it stale
        stale_time = datetime.now() - timedelta(seconds=settings.position_cache.ttl + 1)
        await self._set_cache_updated_time(stale_time)
        logger.info(f"{OPERATION_EMOJIS['data']} Cache marked as stale")

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

    async def _get_cache_updated_time(self) -> datetime | None:
        """Get last cache updated time from system state."""
        from src.storage.database import get_connection

        async with get_connection() as conn:
            cursor = await conn.execute(
                "SELECT value FROM system_state WHERE key = 'cache_updated_at'"
            )
            row = await cursor.fetchone()
            if row:
                return datetime.fromisoformat(row[0])
            return None

    async def _set_cache_updated_time(self, updated_time: datetime) -> None:
        """Set cache updated time in system state."""
        from src.storage.database import get_connection

        async with get_connection() as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO system_state (key, value, updated_at)
                VALUES ('cache_updated_at', ?, ?)
                """,
                (updated_time.isoformat(), datetime.now().isoformat()),
            )
            await conn.commit()

    # ========================================================================
    # Backward compatibility methods (deprecated)
    # ========================================================================

    @property
    def can_sync(self) -> bool:
        """Deprecated: Use can_refresh instead."""
        return self.can_refresh

    @property
    def is_syncing(self) -> bool:
        """Deprecated: Use is_refreshing instead."""
        return self.is_refreshing

    async def get_sync_status(self) -> "CacheStatus":
        """Deprecated: Use get_cache_status instead."""
        return await self.get_cache_status()

    async def sync_positions(self) -> "CacheRefreshResult":
        """Deprecated: Use refresh_cache instead."""
        return await self.refresh_cache()


# =============================================================================
# Deprecated aliases for backward compatibility
# =============================================================================
PositionSyncService = PositionCacheService
PositionSyncResult = CacheRefreshResult
PositionSyncStatus = CacheStatus
