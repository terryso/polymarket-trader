"""Statistics repository for database operations.

This module provides the StatisticsRepository class for managing
daily trading statistics in the SQLite database.

Story 5.5: 统计数据记录

Usage:
    from src.storage.repositories import StatisticsRepository
    from src.models.statistics import Statistics
    from src.models.trade import TradeMode

    repo = StatisticsRepository()
    stats = await repo.save(Statistics(
        id=0,
        date=date.today(),
        mode=TradeMode.PAPER,
        starting_capital=200.0,
        ending_capital=210.0,
        total_pnl=10.0,
        total_trades=5,
        winning_trades=3,
        losing_trades=2,
        win_rate=0.6,
    ))
"""

from __future__ import annotations

__all__ = ["StatisticsRepository"]

from datetime import date, datetime

import aiosqlite

from src.exceptions import DatabaseError
from src.models.statistics import Statistics
from src.models.trade import TradeMode
from src.storage.database import get_connection
from src.utils.logger import OPERATION_EMOJIS, get_logger

logger = get_logger(__name__)


class StatisticsRepository:
    """Repository for Statistics CRUD operations.

    Provides async methods for managing daily statistics in the database.

    Example:
        >>> repo = StatisticsRepository()
        >>> stats = await repo.save(Statistics(...))
        >>> daily = await repo.get_by_date(date.today(), TradeMode.PAPER)
    """

    def __init__(self) -> None:
        """Initialize the StatisticsRepository."""
        pass

    async def save(self, stats: Statistics) -> Statistics:
        """Save a statistics record to the database.

        Uses INSERT OR REPLACE to handle upsert based on date+mode unique
        constraint.

        Args:
            stats: Statistics to save (id will be assigned if 0)

        Returns:
            Saved statistics with assigned id

        Raises:
            DatabaseError: If database operation fails

        Example:
            >>> stats = Statistics(
            ...     id=0,
            ...     date=date.today(),
            ...     mode=TradeMode.PAPER,
            ...     starting_capital=200.0,
            ...     ending_capital=210.0,
            ...     total_pnl=10.0,
            ...     total_trades=5,
            ...     winning_trades=3,
            ...     losing_trades=2,
            ...     win_rate=0.6,
            ... )
            >>> saved = await repo.save(stats)
        """
        logger.info(
            f"{OPERATION_EMOJIS['data']} Saving statistics: "
            f"date={stats.date}, mode={stats.mode.value}"
        )

        try:
            async with get_connection() as conn:
                # Use INSERT OR REPLACE for upsert
                cursor = await conn.execute(
                    """
                    INSERT OR REPLACE INTO statistics (
                        date, mode, starting_capital, ending_capital,
                        total_pnl, total_trades, winning_trades,
                        losing_trades, win_rate, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        stats.date.isoformat(),
                        stats.mode.value,
                        stats.starting_capital,
                        stats.ending_capital,
                        stats.total_pnl,
                        stats.total_trades,
                        stats.winning_trades,
                        stats.losing_trades,
                        stats.win_rate,
                        datetime.utcnow().isoformat(),
                    ),
                )
                await conn.commit()
                stats_id = cursor.lastrowid or 0

            logger.info(
                f"{OPERATION_EMOJIS['data']} Statistics saved with ID: {stats_id}"
            )

            return Statistics(id=stats_id, **stats.model_dump(exclude={"id"}))
        except aiosqlite.Error as e:
            logger.error(f"{OPERATION_EMOJIS['data']} Failed to save statistics: {e}")
            raise DatabaseError(
                message=f"Failed to save statistics for date: {stats.date}",
                operation="save_statistics",
                original_exception=e,
            ) from e

    async def get_by_date(
        self, target_date: date, mode: TradeMode
    ) -> Statistics | None:
        """Get statistics for a specific date and mode.

        Args:
            target_date: Date to query
            mode: Trading mode

        Returns:
            Statistics if found, None otherwise

        Raises:
            DatabaseError: If database operation fails

        Example:
            >>> stats = await repo.get_by_date(date.today(), TradeMode.PAPER)
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    """
                    SELECT * FROM statistics
                    WHERE date = ? AND mode = ?
                    """,
                    (target_date.isoformat(), mode.value),
                )
                row = await cursor.fetchone()

            if row is None:
                return None
            return self._row_to_statistics(row)
        except aiosqlite.Error as e:
            logger.error(f"Failed to get statistics for date {target_date}: {e}")
            raise DatabaseError(
                message=f"Failed to get statistics for date: {target_date}",
                operation="get_statistics_by_date",
                original_exception=e,
            ) from e

    async def get_by_date_range(
        self, start: date, end: date, mode: TradeMode
    ) -> list[Statistics]:
        """Get statistics for a date range.

        Args:
            start: Start date (inclusive)
            end: End date (inclusive)
            mode: Trading mode

        Returns:
            List of statistics, ordered by date ascending

        Raises:
            DatabaseError: If database operation fails

        Example:
            >>> from datetime import date, timedelta
            >>> end_date = date.today()
            >>> start_date = end_date - timedelta(days=7)
            >>> stats_list = await repo.get_by_date_range(
            ...     start_date, end_date, TradeMode.PAPER
            ... )
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    """
                    SELECT * FROM statistics
                    WHERE date >= ? AND date <= ? AND mode = ?
                    ORDER BY date ASC
                    """,
                    (start.isoformat(), end.isoformat(), mode.value),
                )
                rows = await cursor.fetchall()

            stats_list = [self._row_to_statistics(row) for row in rows]
            logger.info(
                f"{OPERATION_EMOJIS['data']} Found {len(stats_list)} statistics "
                f"records from {start} to {end}"
            )
            return stats_list
        except aiosqlite.Error as e:
            logger.error(f"Failed to get statistics for range {start} to {end}: {e}")
            raise DatabaseError(
                message=f"Failed to get statistics for range: {start} to {end}",
                operation="get_statistics_by_date_range",
                original_exception=e,
            ) from e

    async def get_latest(self, mode: TradeMode, limit: int = 30) -> list[Statistics]:
        """Get most recent statistics.

        Args:
            mode: Trading mode
            limit: Maximum number of records (default: 30)

        Returns:
            List of recent statistics, ordered by date descending

        Raises:
            DatabaseError: If database operation fails

        Example:
            >>> recent_stats = await repo.get_latest(TradeMode.PAPER, limit=7)
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    """
                    SELECT * FROM statistics
                    WHERE mode = ?
                    ORDER BY date DESC
                    LIMIT ?
                    """,
                    (mode.value, limit),
                )
                rows = await cursor.fetchall()

            stats_list = [self._row_to_statistics(row) for row in rows]
            logger.info(
                f"{OPERATION_EMOJIS['data']} Retrieved {len(stats_list)} "
                f"recent statistics records"
            )
            return stats_list
        except aiosqlite.Error as e:
            logger.error(f"Failed to get latest statistics: {e}")
            raise DatabaseError(
                message="Failed to get latest statistics",
                operation="get_latest_statistics",
                original_exception=e,
            ) from e

    def _row_to_statistics(self, row: aiosqlite.Row) -> Statistics:
        """Convert a database row to a Statistics model.

        Args:
            row: Database row from statistics table

        Returns:
            Statistics model instance
        """
        # Parse date
        stats_date: date
        if row["date"]:
            try:
                stats_date = date.fromisoformat(row["date"])
            except ValueError:
                stats_date = date.today()
        else:
            stats_date = date.today()

        # Parse created_at
        created_at: datetime | None = None
        if row["created_at"]:
            try:
                created_at = datetime.fromisoformat(row["created_at"])
            except ValueError:
                created_at = None

        return Statistics(
            id=row["id"],
            date=stats_date,
            mode=TradeMode(row["mode"]),
            starting_capital=row["starting_capital"],
            ending_capital=row["ending_capital"],
            total_pnl=row["total_pnl"],
            total_trades=row["total_trades"],
            winning_trades=row["winning_trades"],
            losing_trades=row["losing_trades"],
            win_rate=row["win_rate"],
            created_at=created_at,
        )
