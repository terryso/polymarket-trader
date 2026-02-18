"""Trade repository for database operations.

This module provides the TradeRepository class for managing
trade records in the SQLite database.

Story 5.1: 交易记录数据模型

Usage:
    from src.storage.repositories import TradeRepository
    from src.models.trade import Trade, TradeType, TradeMode, TradeStatus

    repo = TradeRepository()
    trade = await repo.save(Trade(
        id=0,
        market_id="btc-100k",
        trade_type=TradeType.BUY_YES,
        mode=TradeMode.PAPER,
        amount=100.0,
        price=0.45,
        status=TradeStatus.FILLED,
    ))
"""

from __future__ import annotations

__all__ = ["TradeRepository"]

from datetime import date, datetime

import aiosqlite

from src.exceptions import DatabaseError
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.storage.database import get_connection
from src.utils.logger import OPERATION_EMOJIS, get_logger

logger = get_logger(__name__)


class TradeRepository:
    """Repository for Trade CRUD operations.

    Provides async methods for managing trade records in the database.

    Example:
        >>> repo = TradeRepository()
        >>> trade = await repo.save(Trade(...))
        >>> trades = await repo.get_by_market("market-123")
    """

    def __init__(self) -> None:
        """Initialize the TradeRepository."""
        pass

    async def save(self, trade: Trade) -> Trade:
        """Save a trade record to the database.

        Args:
            trade: Trade to save (id will be assigned if 0)

        Returns:
            Saved trade with assigned id

        Raises:
            DatabaseError: If database operation fails

        Example:
            >>> trade = Trade(
            ...     id=0,
            ...     market_id="btc-100k",
            ...     trade_type=TradeType.BUY_YES,
            ...     mode=TradeMode.PAPER,
            ...     amount=100.0,
            ...     price=0.45,
            ...     status=TradeStatus.FILLED,
            ... )
            >>> saved = await repo.save(trade)
        """
        logger.info(
            f"{OPERATION_EMOJIS['trade']} Saving trade: "
            f"market={trade.market_id}, type={trade.trade_type.value}, "
            f"mode={trade.mode.value}"
        )

        try:
            async with get_connection() as conn:
                # Check if this is an update or insert
                if trade.id > 0:
                    # Update existing trade
                    await conn.execute(
                        """
                        UPDATE trades SET
                            market_id = ?, trade_type = ?, mode = ?, amount = ?,
                            price = ?, shares = ?, status = ?, llm_prediction_id = ?,
                            position_id = ?, polymarket_order_id = ?, created_at = ?
                        WHERE id = ?
                        """,
                        (
                            trade.market_id,
                            trade.trade_type.value,
                            trade.mode.value,
                            trade.amount,
                            trade.price,
                            trade.shares,
                            trade.status.value,
                            trade.llm_prediction_id,
                            trade.position_id,
                            trade.polymarket_order_id,
                            trade.created_at.isoformat() if trade.created_at else None,
                            trade.id,
                        ),
                    )
                    trade_id = trade.id
                else:
                    # Insert new trade
                    cursor = await conn.execute(
                        """
                        INSERT INTO trades (
                            market_id, trade_type, mode, amount, price, shares,
                            status, llm_prediction_id, position_id, polymarket_order_id, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            trade.market_id,
                            trade.trade_type.value,
                            trade.mode.value,
                            trade.amount,
                            trade.price,
                            trade.shares,
                            trade.status.value,
                            trade.llm_prediction_id,
                            trade.position_id,
                            trade.polymarket_order_id,
                            trade.created_at.isoformat() if trade.created_at else None,
                        ),
                    )
                    trade_id = cursor.lastrowid or 0

                await conn.commit()

            logger.info(f"{OPERATION_EMOJIS['trade']} Trade saved with ID: {trade_id}")

            return Trade(id=trade_id, **trade.model_dump(exclude={"id"}))
        except aiosqlite.Error as e:
            logger.error(f"{OPERATION_EMOJIS['trade']} Failed to save trade: {e}")
            raise DatabaseError(
                message=f"Failed to save trade for market: {trade.market_id}",
                operation="save_trade",
                original_exception=e,
            ) from e

    async def get_by_id(self, trade_id: int) -> Trade | None:
        """Get a trade by its ID.

        Args:
            trade_id: Trade identifier

        Returns:
            Trade if found, None otherwise

        Example:
            >>> trade = await repo.get_by_id(1)
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    "SELECT * FROM trades WHERE id = ?",
                    (trade_id,),
                )
                row = await cursor.fetchone()

            if row is None:
                return None
            return self._row_to_trade(row)
        except aiosqlite.Error as e:
            logger.error(f"Failed to get trade {trade_id}: {e}")
            raise DatabaseError(
                message=f"Failed to get trade with id: {trade_id}",
                operation="get_trade_by_id",
                original_exception=e,
            ) from e

    async def get_by_market(self, market_id: str) -> list[Trade]:
        """Get all trades for a specific market.

        Args:
            market_id: Market identifier

        Returns:
            List of trades, ordered by created_at descending

        Example:
            >>> trades = await repo.get_by_market("btc-100k")
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    """
                    SELECT * FROM trades
                    WHERE market_id = ?
                    ORDER BY created_at DESC
                    """,
                    (market_id,),
                )
                rows = await cursor.fetchall()

            trades = [self._row_to_trade(row) for row in rows]
            logger.info(
                f"{OPERATION_EMOJIS['data']} Found {len(trades)} trades "
                f"for market: {market_id}"
            )
            return trades
        except aiosqlite.Error as e:
            logger.error(f"Failed to get trades for market {market_id}: {e}")
            raise DatabaseError(
                message=f"Failed to get trades for market: {market_id}",
                operation="get_trades_by_market",
                original_exception=e,
            ) from e

    async def get_by_mode(self, mode: TradeMode) -> list[Trade]:
        """Get all trades for a specific trading mode.

        Args:
            mode: Trading mode (PAPER or LIVE)

        Returns:
            List of trades, ordered by created_at descending

        Example:
            >>> paper_trades = await repo.get_by_mode(TradeMode.PAPER)
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    """
                    SELECT * FROM trades
                    WHERE mode = ?
                    ORDER BY created_at DESC
                    """,
                    (mode.value,),
                )
                rows = await cursor.fetchall()

            trades = [self._row_to_trade(row) for row in rows]
            logger.info(
                f"{OPERATION_EMOJIS['data']} Found {len(trades)} trades "
                f"for mode: {mode.value}"
            )
            return trades
        except aiosqlite.Error as e:
            logger.error(f"Failed to get trades for mode {mode}: {e}")
            raise DatabaseError(
                message=f"Failed to get trades for mode: {mode.value}",
                operation="get_trades_by_mode",
                original_exception=e,
            ) from e

    async def get_recent(self, limit: int = 50) -> list[Trade]:
        """Get most recent trades.

        Args:
            limit: Maximum number of trades to return (default: 50)

        Returns:
            List of recent trades, ordered by created_at descending

        Example:
            >>> recent_trades = await repo.get_recent(10)
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    """
                    SELECT * FROM trades
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = await cursor.fetchall()

            trades = [self._row_to_trade(row) for row in rows]
            logger.info(
                f"{OPERATION_EMOJIS['data']} Retrieved {len(trades)} recent trades"
            )
            return trades
        except aiosqlite.Error as e:
            logger.error(f"Failed to get recent trades: {e}")
            raise DatabaseError(
                message="Failed to get recent trades",
                operation="get_recent_trades",
                original_exception=e,
            ) from e

    async def get_by_date_range(
        self,
        start_date: date,
        end_date: date,
        mode: TradeMode | None = None,
    ) -> list[Trade]:
        """Get trades within a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            mode: Optional trading mode filter

        Returns:
            List of trades within the date range, ordered by created_at descending

        Raises:
            DatabaseError: If database operation fails

        Example:
            >>> from datetime import date, timedelta
            >>> end_date = date.today()
            >>> start_date = end_date - timedelta(days=7)
            >>> trades = await repo.get_by_date_range(
            ...     start_date, end_date, TradeMode.PAPER
            ... )
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row

                if mode is not None:
                    cursor = await conn.execute(
                        """
                        SELECT * FROM trades
                        WHERE date(created_at) >= ?
                        AND date(created_at) <= ?
                        AND mode = ?
                        ORDER BY created_at DESC
                        """,
                        (start_date.isoformat(), end_date.isoformat(), mode.value),
                    )
                else:
                    cursor = await conn.execute(
                        """
                        SELECT * FROM trades
                        WHERE date(created_at) >= ?
                        AND date(created_at) <= ?
                        ORDER BY created_at DESC
                        """,
                        (start_date.isoformat(), end_date.isoformat()),
                    )
                rows = await cursor.fetchall()

            trades = [self._row_to_trade(row) for row in rows]
            logger.info(
                f"{OPERATION_EMOJIS['data']} Found {len(trades)} trades "
                f"from {start_date} to {end_date}"
            )
            return trades
        except aiosqlite.Error as e:
            logger.error(
                f"Failed to get trades for range {start_date} to {end_date}: {e}"
            )
            raise DatabaseError(
                message=f"Failed to get trades for range: {start_date} to {end_date}",
                operation="get_trades_by_date_range",
                original_exception=e,
            ) from e

    # ==================== Story 6.3: 学习日志生成 ====================

    async def get_trades_by_date(self, report_date: date) -> list[Trade]:
        """Get all trades for a specific date.

        Story 6.3: 学习日志生成

        Args:
            report_date: The date to get trades for

        Returns:
            List of trades executed on the given date, ordered by created_at descending

        Raises:
            DatabaseError: If database operation fails

        Example:
            >>> from datetime import date
            >>> trades = await repo.get_trades_by_date(date.today())
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    """
                    SELECT * FROM trades
                    WHERE date(created_at) = ?
                    ORDER BY created_at DESC
                    """,
                    (report_date.isoformat(),),
                )
                rows = await cursor.fetchall()

            trades = [self._row_to_trade(row) for row in rows]
            logger.info(
                f"{OPERATION_EMOJIS['data']} Found {len(trades)} trades "
                f"for date {report_date}"
            )
            return trades
        except aiosqlite.Error as e:
            logger.error(f"Failed to get trades for date {report_date}: {e}")
            raise DatabaseError(
                message=f"Failed to get trades for date: {report_date}",
                operation="get_trades_by_date",
                original_exception=e,
            ) from e

    def _row_to_trade(self, row: aiosqlite.Row) -> Trade:
        """Convert a database row to a Trade model.

        Args:
            row: Database row from trades table

        Returns:
            Trade model instance
        """
        # Parse created_at
        created_at: datetime | None = None
        if row["created_at"]:
            try:
                created_at = datetime.fromisoformat(row["created_at"])
            except ValueError:
                created_at = None

        # Handle polymarket_order_id (may not exist in older rows)
        polymarket_order_id = None
        try:
            polymarket_order_id = row["polymarket_order_id"]
        except (KeyError, IndexError):
            pass

        return Trade(
            id=row["id"],
            market_id=row["market_id"],
            trade_type=TradeType(row["trade_type"]),
            mode=TradeMode(row["mode"]),
            amount=row["amount"],
            price=row["price"],
            shares=row["shares"],
            status=TradeStatus(row["status"]),
            llm_prediction_id=row["llm_prediction_id"],
            position_id=row["position_id"],
            polymarket_order_id=polymarket_order_id,
            created_at=created_at,
        )

    # ==================== Story 5.6: 交易历史同步 ====================

    async def get_by_polymarket_order_id(self, order_id: str) -> Trade | None:
        """Get a trade by its Polymarket order ID.

        Story 5.6: 交易历史同步

        Args:
            order_id: Polymarket order ID

        Returns:
            Trade if found, None otherwise

        Example:
            >>> trade = await repo.get_by_polymarket_order_id("0x123...")
        """
        if not order_id:
            return None

        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    "SELECT * FROM trades WHERE polymarket_order_id = ?",
                    (order_id,),
                )
                row = await cursor.fetchone()

            if row is None:
                return None
            return self._row_to_trade(row)
        except aiosqlite.Error as e:
            logger.error(f"Failed to get trade by order_id {order_id}: {e}")
            raise DatabaseError(
                message=f"Failed to get trade by order_id: {order_id}",
                operation="get_trade_by_polymarket_order_id",
                original_exception=e,
            ) from e

    async def count_by_mode(self, mode: TradeMode) -> int:
        """Count trades by trading mode.

        Story 5.6: 交易历史同步

        Args:
            mode: Trading mode (PAPER or LIVE)

        Returns:
            Number of trades in the specified mode

        Example:
            >>> count = await repo.count_by_mode(TradeMode.LIVE)
        """
        try:
            async with get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM trades WHERE mode = ?",
                    (mode.value,),
                )
                row = await cursor.fetchone()
                return row[0] if row else 0
        except aiosqlite.Error as e:
            logger.error(f"Failed to count trades for mode {mode}: {e}")
            raise DatabaseError(
                message=f"Failed to count trades for mode: {mode.value}",
                operation="count_trades_by_mode",
                original_exception=e,
            ) from e
