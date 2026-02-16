"""Position repository for database operations.

This module provides the PositionRepository class for managing
position data in the SQLite database.

Story 4.5: 持仓管理

Usage:
    from src.storage.repositories import PositionRepository

    repo = PositionRepository()
    position = await repo.save(position)
    open_positions = await repo.get_open_positions()
"""

from __future__ import annotations

__all__ = ["PositionRepository"]

from datetime import datetime

import aiosqlite

from src.models.position import Position, PositionOutcome, PositionStatus
from src.storage.database import get_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PositionRepository:
    """Repository for Position CRUD operations.

    Provides async methods for managing positions in the database.

    Example:
        >>> repo = PositionRepository()
        >>> position = await repo.save(Position(...))
        >>> open_positions = await repo.get_open_positions()
    """

    def __init__(self) -> None:
        """Initialize the PositionRepository."""
        pass

    async def save(self, position: Position) -> Position:
        """Save a new position to the database.

        Args:
            position: Position to save (id will be assigned)

        Returns:
            Saved position with assigned id

        Raises:
            DatabaseError: If database operation fails

        Example:
            >>> position = Position(
            ...     id=0,
            ...     market_id="btc-100k",
            ...     outcome=PositionOutcome.YES,
            ...     shares=100.0,
            ...     avg_price=0.45,
            ...     status=PositionStatus.OPEN,
            ... )
            >>> saved = await repo.save(position)
            >>> saved.id
            1
        """
        async with get_connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO positions (
                    market_id, outcome, shares, avg_price,
                    initial_value, current_value, pnl, status,
                    opened_at, closed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position.market_id,
                    position.outcome.value,
                    position.shares,
                    position.avg_price,
                    position.initial_value,
                    position.current_value,
                    position.pnl,
                    position.status.value,
                    position.opened_at.isoformat() if position.opened_at else None,
                    position.closed_at.isoformat() if position.closed_at else None,
                ),
            )
            await conn.commit()
            position_id = cursor.lastrowid or 0

        logger.debug(f"💰 Saved position {position_id} for market {position.market_id}")
        return Position(id=position_id, **position.model_dump(exclude={"id"}))

    async def get_by_id(self, position_id: int) -> Position | None:
        """Get position by ID.

        Args:
            position_id: Position identifier

        Returns:
            Position if found, None otherwise

        Example:
            >>> position = await repo.get_by_id(1)
            >>> if position:
            ...     print(f"Market: {position.market_id}")
        """
        async with get_connection() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM positions WHERE id = ?", (position_id,)
            )
            row = await cursor.fetchone()

        if row is None:
            return None
        return self._row_to_position(row)

    async def get_by_market(
        self, market_id: str, status: PositionStatus | None = None
    ) -> Position | None:
        """Get position by market ID.

        Args:
            market_id: Market identifier
            status: Optional status filter

        Returns:
            Position if found, None otherwise

        Example:
            >>> position = await repo.get_by_market("btc-100k", PositionStatus.OPEN)
            >>> if position:
            ...     print(f"Shares: {position.shares}")
        """
        async with get_connection() as conn:
            conn.row_factory = aiosqlite.Row
            if status:
                cursor = await conn.execute(
                    "SELECT * FROM positions WHERE market_id = ? AND status = ?",
                    (market_id, status.value),
                )
            else:
                cursor = await conn.execute(
                    "SELECT * FROM positions WHERE market_id = ?", (market_id,)
                )
            row = await cursor.fetchone()

        if row is None:
            return None
        return self._row_to_position(row)

    async def get_open_positions(self) -> list[Position]:
        """Get all open positions.

        Returns:
            List of open positions ordered by opened_at descending

        Example:
            >>> positions = await repo.get_open_positions()
            >>> print(f"Open positions: {len(positions)}")
        """
        async with get_connection() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM positions WHERE status = ? ORDER BY opened_at DESC",
                (PositionStatus.OPEN.value,),
            )
            rows = await cursor.fetchall()

        return [self._row_to_position(row) for row in rows]

    async def update(self, position: Position) -> Position:
        """Update an existing position.

        Args:
            position: Position to update

        Returns:
            Updated position

        Raises:
            DatabaseError: If database operation fails

        Example:
            >>> position.current_value = 60.0
            >>> position.pnl = 15.0
            >>> updated = await repo.update(position)
        """
        async with get_connection() as conn:
            await conn.execute(
                """
                UPDATE positions SET
                    market_id = ?, outcome = ?, shares = ?, avg_price = ?,
                    initial_value = ?, current_value = ?, pnl = ?, status = ?,
                    opened_at = ?, closed_at = ?
                WHERE id = ?
                """,
                (
                    position.market_id,
                    position.outcome.value,
                    position.shares,
                    position.avg_price,
                    position.initial_value,
                    position.current_value,
                    position.pnl,
                    position.status.value,
                    position.opened_at.isoformat() if position.opened_at else None,
                    position.closed_at.isoformat() if position.closed_at else None,
                    position.id,
                ),
            )
            await conn.commit()

        logger.debug(f"📊 Updated position {position.id}")
        return position

    async def delete(self, position_id: int) -> bool:
        """Delete a position.

        Args:
            position_id: Position identifier

        Returns:
            True if deleted, False if not found

        Example:
            >>> deleted = await repo.delete(1)
            >>> assert deleted is True
        """
        async with get_connection() as conn:
            cursor = await conn.execute(
                "DELETE FROM positions WHERE id = ?", (position_id,)
            )
            await conn.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.debug(f"Deleted position {position_id}")
        return deleted

    def _row_to_position(self, row: aiosqlite.Row) -> Position:
        """Convert database row to Position model.

        Args:
            row: Database row

        Returns:
            Position model instance
        """
        opened_at: datetime | None = None
        if row["opened_at"]:
            try:
                opened_at = datetime.fromisoformat(row["opened_at"])
            except ValueError:
                opened_at = None

        closed_at: datetime | None = None
        if row["closed_at"]:
            try:
                closed_at = datetime.fromisoformat(row["closed_at"])
            except ValueError:
                closed_at = None

        return Position(
            id=row["id"],
            market_id=row["market_id"],
            outcome=PositionOutcome(row["outcome"]),
            shares=row["shares"],
            avg_price=row["avg_price"],
            initial_value=row["initial_value"],
            current_value=row["current_value"],
            pnl=row["pnl"],
            status=PositionStatus(row["status"]),
            opened_at=opened_at,
            closed_at=closed_at,
        )
