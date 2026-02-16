"""Market data repository for database operations.

This module provides CRUD operations for market data using
the repository pattern.

Usage:
    from src.storage.repositories import MarketRepository
    from src.models import Market

    repo = MarketRepository()
    market = Market(id="test", title="Test Market")
    await repo.save_market(market)
"""

from __future__ import annotations

__all__ = ["MarketRepository"]

from datetime import datetime

import aiosqlite

from src.exceptions import DatabaseError
from src.models import Market, MarketCategory
from src.storage.database import get_connection
from src.utils.logger import OPERATION_EMOJIS, get_logger

logger = get_logger(__name__)


class MarketRepository:
    """Repository for market data operations.

    Provides methods to save, retrieve, and manage market data
    in the SQLite database.

    Example:
        >>> repo = MarketRepository()
        >>> market = Market(id="test", title="Test Market")
        >>> await repo.save_market(market)
    """

    async def save_market(self, market: Market) -> Market:
        """Save a single market to the database.

        Uses UPSERT (INSERT OR REPLACE) to handle duplicates.

        Args:
            market: Market model to save

        Returns:
            The saved Market model

        Raises:
            DatabaseError: If save operation fails
        """
        now = datetime.utcnow().isoformat()

        try:
            async with get_connection() as conn:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO markets (
                        id, title, description, category,
                        yes_price, no_price, liquidity, deadline,
                        resolution_status, resolution_outcome,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._market_to_tuple(market, now),
                )
                await conn.commit()

            logger.info(f"{OPERATION_EMOJIS['data']} Saved market: {market.id}")
            return market
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to save market {market.id}: {e}"
            )
            raise DatabaseError(
                message=f"Failed to save market: {market.id}",
                operation="save_market",
                original_exception=e,
            ) from e

    async def save_markets(self, markets: list[Market]) -> int:
        """Save multiple markets to the database.

        Uses UPSERT (INSERT OR REPLACE) to handle duplicates.
        Processes markets individually to ensure isolation - one market
        failure does not affect others.

        Args:
            markets: List of Market models to save

        Returns:
            Number of markets successfully saved

        Raises:
            DatabaseError: If database operation fails
        """
        if not markets:
            return 0

        saved_count = 0
        now = datetime.utcnow().isoformat()

        try:
            async with get_connection() as conn:
                for market in markets:
                    try:
                        await conn.execute(
                            """
                            INSERT OR REPLACE INTO markets (
                                id, title, description, category,
                                yes_price, no_price, liquidity, deadline,
                                resolution_status, resolution_outcome,
                                created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                market.id,
                                market.title,
                                market.description,
                                market.category.value if market.category else None,
                                market.yes_price,
                                market.no_price,
                                market.liquidity,
                                (
                                    market.deadline.isoformat()
                                    if market.deadline
                                    else None
                                ),
                                market.resolution_status,
                                market.resolution_outcome,
                                (
                                    market.created_at.isoformat()
                                    if market.created_at
                                    else now
                                ),
                                now,
                            ),
                        )
                        saved_count += 1
                    except aiosqlite.Error as e:
                        logger.warning(
                            f"{OPERATION_EMOJIS['data']} Skipped market {market.id}: {e}"
                        )
                        continue

                await conn.commit()

            logger.info(
                f"{OPERATION_EMOJIS['data']} ✅ Saved {saved_count}/{len(markets)} markets"
            )
            return saved_count
        except aiosqlite.Error as e:
            logger.error(f"{OPERATION_EMOJIS['data']} Failed to save markets: {e}")
            raise DatabaseError(
                message="Failed to save markets",
                operation="save_markets",
                original_exception=e,
            ) from e

    async def update_last_fetch_time(self) -> None:
        """Update the last market fetch timestamp in system_state.

        Raises:
            DatabaseError: If update operation fails
        """
        now = datetime.utcnow().isoformat()

        try:
            async with get_connection() as conn:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO system_state (key, value, updated_at)
                    VALUES ('last_market_fetch', ?, ?)
                    """,
                    (now, now),
                )
                await conn.commit()

            logger.debug(f"{OPERATION_EMOJIS['data']} Updated last fetch time: {now}")
        except aiosqlite.Error as e:
            logger.error(f"{OPERATION_EMOJIS['data']} Failed to update fetch time: {e}")
            raise DatabaseError(
                message="Failed to update last fetch time",
                operation="update_last_fetch_time",
                original_exception=e,
            ) from e

    async def get_market(self, market_id: str) -> Market | None:
        """Get a single market by ID.

        Args:
            market_id: The market ID to look up

        Returns:
            Market model if found, None otherwise

        Raises:
            DatabaseError: If query fails
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    "SELECT * FROM markets WHERE id = ?", (market_id,)
                )
                row = await cursor.fetchone()

                if row is None:
                    return None

                return self._row_to_market(row)
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to get market {market_id}: {e}"
            )
            raise DatabaseError(
                message=f"Failed to get market: {market_id}",
                operation="get_market",
                original_exception=e,
            ) from e

    async def get_all_markets(self, limit: int | None = None) -> list[Market]:
        """Get all markets from the database.

        Args:
            limit: Optional limit on number of markets to return

        Returns:
            List of Market models

        Raises:
            DatabaseError: If query fails
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                if limit is not None:
                    cursor = await conn.execute(
                        "SELECT * FROM markets ORDER BY updated_at DESC LIMIT ?",
                        (limit,),
                    )
                else:
                    cursor = await conn.execute(
                        "SELECT * FROM markets ORDER BY updated_at DESC"
                    )
                rows = await cursor.fetchall()

                return [self._row_to_market(row) for row in rows]
        except aiosqlite.Error as e:
            logger.error(f"{OPERATION_EMOJIS['data']} Failed to get all markets: {e}")
            raise DatabaseError(
                message="Failed to get all markets",
                operation="get_all_markets",
                original_exception=e,
            ) from e

    async def get_last_fetch_time(self) -> datetime | None:
        """Get the last market fetch timestamp from system_state.

        Returns:
            datetime of last fetch if set, None otherwise

        Raises:
            DatabaseError: If query fails
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    "SELECT value FROM system_state WHERE key = 'last_market_fetch'"
                )
                row = await cursor.fetchone()

                if row is None or row["value"] is None:
                    return None

                return datetime.fromisoformat(row["value"])
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to get last fetch time: {e}"
            )
            raise DatabaseError(
                message="Failed to get last fetch time",
                operation="get_last_fetch_time",
                original_exception=e,
            ) from e

    def _row_to_market(self, row: aiosqlite.Row) -> Market:
        """Convert a database row to a Market model.

        Args:
            row: Database row

        Returns:
            Market model instance
        """
        # Parse category
        category: MarketCategory | None = None
        if row["category"]:
            try:
                category = MarketCategory(row["category"])
            except ValueError:
                category = None

        # Parse datetime fields
        deadline: datetime | None = None
        if row["deadline"]:
            try:
                deadline = datetime.fromisoformat(row["deadline"])
            except ValueError:
                deadline = None

        created_at: datetime | None = None
        if row["created_at"]:
            try:
                created_at = datetime.fromisoformat(row["created_at"])
            except ValueError:
                created_at = None

        updated_at: datetime | None = None
        if row["updated_at"]:
            try:
                updated_at = datetime.fromisoformat(row["updated_at"])
            except ValueError:
                updated_at = None

        return Market(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            category=category,
            yes_price=row["yes_price"],
            no_price=row["no_price"],
            liquidity=row["liquidity"],
            deadline=deadline,
            resolution_status=row["resolution_status"],
            resolution_outcome=row["resolution_outcome"],
            created_at=created_at,
            updated_at=updated_at,
        )

    def _market_to_tuple(self, market: Market, now: str) -> tuple[object, ...]:
        """Convert a Market model to a database tuple.

        Args:
            market: Market model to convert
            now: Current timestamp for created_at/updated_at

        Returns:
            Tuple of values for database insert
        """
        return (
            market.id,
            market.title,
            market.description,
            market.category.value if market.category else None,
            market.yes_price,
            market.no_price,
            market.liquidity,
            market.deadline.isoformat() if market.deadline else None,
            market.resolution_status,
            market.resolution_outcome,
            market.created_at.isoformat() if market.created_at else now,
            now,
        )

    async def get_active_markets(self) -> list[Market]:
        """Get all active (unresolved) markets.

        Returns markets where resolution_status IS NULL,
        ordered by deadline ascending.

        Returns:
            List of active Market models

        Raises:
            DatabaseError: If query fails
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT * FROM markets
                    WHERE resolution_status IS NULL
                    ORDER BY deadline ASC
                    """)
                rows = await cursor.fetchall()
                markets = [self._row_to_market(row) for row in rows]
                logger.info(
                    f"{OPERATION_EMOJIS['data']} Found {len(markets)} active markets"
                )
                return markets
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to get active markets: {e}"
            )
            raise DatabaseError(
                message="Failed to get active markets",
                operation="get_active_markets",
                original_exception=e,
            ) from e

    async def get_markets_by_category(
        self, category: MarketCategory | str
    ) -> list[Market]:
        """Get markets filtered by category.

        Args:
            category: Category to filter by (MarketCategory enum or string)

        Returns:
            List of Market models in the category

        Raises:
            DatabaseError: If query fails
        """
        category_str = category.value if hasattr(category, "value") else category

        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    "SELECT * FROM markets WHERE category = ?", (category_str,)
                )
                rows = await cursor.fetchall()
                markets = [self._row_to_market(row) for row in rows]
                logger.info(
                    f"{OPERATION_EMOJIS['data']} Found {len(markets)} markets "
                    f"in category: {category_str}"
                )
                return markets
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to get markets by category: {e}"
            )
            raise DatabaseError(
                message=f"Failed to get markets by category: {category_str}",
                operation="get_markets_by_category",
                original_exception=e,
            ) from e

    async def update_market_resolution(self, market_id: str, outcome: str) -> bool:
        """Update market resolution status and outcome.

        Args:
            market_id: Market ID to update
            outcome: Resolution outcome (e.g., "YES", "NO")

        Returns:
            True if update succeeded, False if market not found

        Raises:
            DatabaseError: If update operation fails
        """
        now = datetime.utcnow().isoformat()

        try:
            async with get_connection() as conn:
                cursor = await conn.execute(
                    """
                    UPDATE markets
                    SET resolution_status = 'RESOLVED',
                        resolution_outcome = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (outcome, now, market_id),
                )
                await conn.commit()

                if cursor.rowcount == 0:
                    logger.warning(
                        f"{OPERATION_EMOJIS['data']} Market not found: {market_id}"
                    )
                    return False

                logger.info(
                    f"{OPERATION_EMOJIS['data']} Updated resolution for market: {market_id}"
                )
                return True
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to update market resolution: {e}"
            )
            raise DatabaseError(
                message=f"Failed to update market resolution: {market_id}",
                operation="update_market_resolution",
                original_exception=e,
            ) from e
