"""Trade history synchronization service.

This module provides functionality to synchronize trade history from
Polymarket API to the local database.

Story 5.6: 交易历史同步
"""

from __future__ import annotations

__all__ = ["TradeSyncService", "SyncResult", "SyncStatus"]

from dataclasses import dataclass, field
from datetime import datetime

from src.api.polymarket import OrderHistoryItem, OrderHistoryResult, PolymarketClient
from src.config import settings
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.storage.repositories.trade_repo import TradeRepository
from src.utils.logger import OPERATION_EMOJIS, get_logger

logger = get_logger(__name__)


@dataclass
class SyncResult:
    """Result of a trade sync operation.

    Attributes:
        new_trades: Number of new trades added
        updated_trades: Number of existing trades updated
        consistent_trades: Number of trades that matched existing records
        inconsistent_trades: Number of trades with discrepancies
        total_fetched: Total number of orders fetched from API
        last_sync_at: Timestamp of this sync
        error: Error message if sync failed
    """

    new_trades: int = 0
    updated_trades: int = 0
    consistent_trades: int = 0
    inconsistent_trades: int = 0
    total_fetched: int = 0
    last_sync_at: datetime = field(default_factory=datetime.now)
    error: str | None = None

    @property
    def is_success(self) -> bool:
        """Check if sync was successful."""
        return self.error is None

    @property
    def total_processed(self) -> int:
        """Total number of trades processed."""
        return self.new_trades + self.updated_trades + self.consistent_trades


@dataclass
class SyncStatus:
    """Current sync status.

    Attributes:
        last_sync_at: Timestamp of last successful sync
        is_syncing: Whether a sync is currently in progress
        can_sync: Whether sync is possible (requires API credentials)
        last_error: Last error message if sync failed
        total_synced: Total number of trades synced
    """

    last_sync_at: datetime | None = None
    is_syncing: bool = False
    can_sync: bool = False
    last_error: str | None = None
    total_synced: int = 0


class TradeSyncService:
    """Service for synchronizing trade history from Polymarket.

    Fetches order history from Polymarket API and synchronizes it
    with the local database.

    Example:
        >>> service = TradeSyncService()
        >>> result = await service.sync_trades()
        >>> if result.is_success:
        ...     print(f"Synced {result.new_trades} new trades")
    """

    def __init__(self) -> None:
        """Initialize the trade sync service."""
        self._trade_repo = TradeRepository()
        self._syncing = False

    @property
    def can_sync(self) -> bool:
        """Check if sync is possible (requires private key and proxy wallet)."""
        return bool(settings.polymarket.pk and settings.polymarket.proxy_wallet)

    @property
    def is_syncing(self) -> bool:
        """Check if a sync is currently in progress."""
        return self._syncing

    async def get_sync_status(self) -> SyncStatus:
        """Get current sync status.

        Returns:
            SyncStatus with current sync information
        """
        # Get last sync time from database
        last_sync = await self._get_last_sync_time()
        total_synced = await self._trade_repo.count_by_mode(TradeMode.LIVE)

        return SyncStatus(
            last_sync_at=last_sync,
            is_syncing=self._syncing,
            can_sync=self.can_sync,
            total_synced=total_synced,
        )

    async def sync_trades(self) -> SyncResult:
        """Synchronize trades from Polymarket API.

        Fetches all orders from Polymarket and syncs them with local database.

        Returns:
            SyncResult with sync statistics
        """
        if self._syncing:
            return SyncResult(error="Sync already in progress")

        if not self.can_sync:
            return SyncResult(
                error="Private key and proxy wallet not configured. "
                "Please set PK and YOUR_PROXY_WALLET in your .env file."
            )

        self._syncing = True
        logger.info(f"{OPERATION_EMOJIS['network']} Starting trade sync...")

        client = None
        try:
            result = SyncResult()
            client = PolymarketClient()

            # Fetch all orders with pagination
            cursor = None
            all_orders: list[OrderHistoryItem] = []

            while True:
                order_result: OrderHistoryResult = client.get_order_history(
                    cursor=cursor
                )

                if not order_result.is_success:
                    result.error = order_result.error
                    return result

                all_orders.extend(order_result.orders)
                result.total_fetched = len(all_orders)

                if not order_result.has_more:
                    break

                cursor = order_result.next_cursor

            logger.info(
                f"{OPERATION_EMOJIS['network']} Fetched {len(all_orders)} orders from API"
            )

            # Sync each order with local database
            for order in all_orders:
                sync_result = await self._sync_single_order(order)
                if sync_result == "new":
                    result.new_trades += 1
                elif sync_result == "updated":
                    result.updated_trades += 1
                elif sync_result == "consistent":
                    result.consistent_trades += 1
                elif sync_result == "inconsistent":
                    result.inconsistent_trades += 1

            # Update last sync time
            await self._set_last_sync_time(result.last_sync_at)

            logger.info(
                f"{OPERATION_EMOJIS['network']} Sync complete: "
                f"{result.new_trades} new, {result.updated_trades} updated, "
                f"{result.consistent_trades} consistent, {result.inconsistent_trades} inconsistent"
            )

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"{OPERATION_EMOJIS['network']} Trade sync failed: {error_msg}"
            )
            return SyncResult(error=error_msg)

        finally:
            self._syncing = False
            if client:
                client.close()

    async def _sync_single_order(self, order: OrderHistoryItem) -> str:
        """Sync a single order with the database.

        Args:
            order: Order from Polymarket API

        Returns:
            "new", "updated", "consistent", or "inconsistent"
        """
        # Ensure the market exists in local database (required for foreign key constraint)
        if order.market_id:
            await self._ensure_market_exists(order.market_id)

        # Convert order to Trade model
        trade = self._order_to_trade(order)

        # Check if trade already exists
        existing = await self._trade_repo.get_by_polymarket_order_id(order.order_id)

        if existing is None:
            # New trade - save it
            await self._trade_repo.save(trade)
            return "new"

        # Compare and update if needed
        if self._trades_match(existing, trade):
            return "consistent"

        # Update existing trade
        trade.id = existing.id
        await self._trade_repo.save(trade)
        return "updated"

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

    def _order_to_trade(self, order: OrderHistoryItem) -> Trade:
        """Convert OrderHistoryItem to Trade model.

        Args:
            order: Order from Polymarket API

        Returns:
            Trade model
        """
        # Determine trade type from order side and outcome
        if order.side == "BUY":
            trade_type = (
                TradeType.BUY_YES if order.outcome == "YES" else TradeType.BUY_NO
            )
        else:
            trade_type = TradeType.SELL

        # Determine status
        # Polymarket trades API returns: CONFIRMED (filled), LIVE (pending), CANCELED
        status_map = {
            "LIVE": TradeStatus.PENDING,
            "MATCHED": TradeStatus.FILLED,
            "CONFIRMED": TradeStatus.FILLED,  # Confirmed trades are filled
            "CANCELED": TradeStatus.CANCELLED,
            "PARTIALLY_MATCHED": TradeStatus.PENDING,
        }
        status = status_map.get(order.status, TradeStatus.PENDING)

        return Trade(
            id=0,  # Will be assigned by database
            market_id=order.market_id or "",
            trade_type=trade_type,
            mode=TradeMode.LIVE,  # Synced trades are always LIVE mode
            amount=order.size * order.price,  # Calculate amount from size and price
            price=order.price,
            shares=order.size,
            status=status,
            created_at=order.created_at or datetime.now(),
            polymarket_order_id=order.order_id,
        )

    def _trades_match(self, local: Trade, remote: Trade) -> bool:
        """Check if two trades match.

        Args:
            local: Trade from local database
            remote: Trade from remote API

        Returns:
            True if trades match
        """
        return (
            local.market_id == remote.market_id
            and local.trade_type == remote.trade_type
            and abs(local.price - remote.price) < 0.001
            and abs(local.shares - remote.shares) < 0.001
            and local.status == remote.status
        )

    async def _get_last_sync_time(self) -> datetime | None:
        """Get last sync time from system state."""
        from src.storage.database import get_connection

        async with get_connection() as conn:
            cursor = await conn.execute(
                "SELECT value FROM system_state WHERE key = 'last_trade_sync'"
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
                VALUES ('last_trade_sync', ?, ?)
                """,
                (sync_time.isoformat(), datetime.now().isoformat()),
            )
            await conn.commit()
