"""Position management for the Polymarket Trader application.

This module provides the PositionManager class that handles all
position lifecycle operations including opening, updating, and closing.

Story 4.5: 持仓管理

Example:
    >>> from src.trading.position_manager import PositionManager
    >>> from src.storage.repositories.position_repo import PositionRepository
    >>> from src.core.state import ThreadSafeState
    >>>
    >>> repo = PositionRepository()
    >>> state = ThreadSafeState(initial_capital=200.0)
    >>> manager = PositionManager(repo, state)
    >>>
    >>> # Open a position
    >>> position = await manager.open_position(
    ...     market_id="btc-100k",
    ...     outcome=PositionOutcome.YES,
    ...     shares=100.0,
    ...     price=0.45
    ... )
"""

from __future__ import annotations

__all__ = ["PositionManager"]

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.exceptions import TradingError, ValidationError
from src.models.position import Position, PositionOutcome, PositionStatus
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.core.state import ThreadSafeState
    from src.storage.repositories.position_repo import PositionRepository


logger = get_logger(__name__)


class PositionManager:
    """Position lifecycle manager.

    Manages the complete lifecycle of trading positions:
    - Opening new positions
    - Updating position values
    - Closing positions
    - Tracking total exposure

    Attributes:
        _repo: PositionRepository for database operations
        _state: ThreadSafeState for system state tracking

    Example:
        >>> manager = PositionManager(repo, state)
        >>> position = await manager.open_position(
        ...     "market-123", PositionOutcome.YES, 100.0, 0.45
        ... )
        >>> print(f"Opened position {position.id}")
    """

    def __init__(
        self,
        repository: "PositionRepository",
        state: "ThreadSafeState",
    ) -> None:
        """Initialize position manager.

        Args:
            repository: PositionRepository for database operations
            state: ThreadSafeState for system state tracking
        """
        self._repo = repository
        self._state = state
        self._logger = get_logger(__name__)
        self._logger.info("PositionManager initialized")

    async def open_position(
        self,
        market_id: str,
        outcome: PositionOutcome,
        shares: float,
        price: float,
    ) -> Position:
        """Open a new position.

        Args:
            market_id: Market identifier
            outcome: Position outcome (YES or NO)
            shares: Number of shares to purchase
            price: Purchase price per share (0-1)

        Returns:
            Created Position with assigned id

        Raises:
            ValidationError: If parameters are invalid
            TradingError: If position creation fails or position already exists

        Example:
            >>> position = await manager.open_position(
            ...     "btc-100k", PositionOutcome.YES, 100.0, 0.45
            ... )
        """
        # Validate parameters
        if shares <= 0:
            raise ValidationError(f"Shares must be positive, got {shares}")
        if not 0 < price < 1:
            raise ValidationError(f"Price must be between 0 and 1, got {price}")

        # Check for existing open position in this market
        existing = await self._repo.get_by_market(market_id, PositionStatus.OPEN)
        if existing:
            raise TradingError(
                f"Open position already exists for market {market_id}: "
                f"position_id={existing.id}"
            )

        # Calculate initial value
        initial_value = shares * price

        # Create position object
        now = datetime.now(timezone.utc)
        position = Position(
            id=0,  # Will be assigned by database
            market_id=market_id,
            outcome=outcome,
            shares=shares,
            avg_price=price,
            initial_value=initial_value,
            current_value=initial_value,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=now,
            closed_at=None,
        )

        # Save to database
        saved_position = await self._repo.save(position)

        # Update system state
        await self._state.increment_open_positions()

        self._logger.info(
            f"💰 Position opened: id={saved_position.id}, "
            f"market={market_id}, outcome={outcome.value}, "
            f"shares={shares:.2f}, price={price:.4f}, "
            f"value=${initial_value:.2f}"
        )

        return saved_position

    async def update_position_value(
        self,
        position_id: int,
        current_price: float,
    ) -> Position:
        """Update position's current value and PnL.

        Args:
            position_id: Position identifier
            current_price: Current market price (0-1)

        Returns:
            Updated Position

        Raises:
            ValidationError: If position not found or price invalid
            TradingError: If position is not OPEN

        Example:
            >>> position = await manager.update_position_value(1, 0.55)
            >>> print(f"PnL: ${position.pnl:.2f}")
        """
        if not 0 < current_price < 1:
            raise ValidationError(
                f"Current price must be between 0 and 1, got {current_price}"
            )

        # Get position
        position = await self._repo.get_by_id(position_id)
        if position is None:
            raise ValidationError(f"Position {position_id} not found")

        if position.status != PositionStatus.OPEN:
            raise TradingError(f"Cannot update closed position {position_id}")

        # Calculate new values
        current_value = position.shares * current_price
        pnl = current_value - (position.initial_value or 0)

        # Update position
        position.current_value = current_value
        position.pnl = pnl

        updated_position = await self._repo.update(position)

        self._logger.debug(
            f"📊 Position {position_id} updated: "
            f"current_value=${current_value:.2f}, pnl=${pnl:.2f}"
        )

        return updated_position

    async def close_position(
        self,
        position_id: int,
        final_price: float,
    ) -> Position:
        """Close an open position.

        Args:
            position_id: Position identifier
            final_price: Final market price at close (0-1)

        Returns:
            Closed Position with final PnL

        Raises:
            ValidationError: If position not found or price invalid
            TradingError: If position is not OPEN

        Example:
            >>> position = await manager.close_position(1, 0.60)
            >>> print(f"Final PnL: ${position.pnl:.2f}")
        """
        if not 0 < final_price < 1:
            raise ValidationError(
                f"Final price must be between 0 and 1, got {final_price}"
            )

        # Get position
        position = await self._repo.get_by_id(position_id)
        if position is None:
            raise ValidationError(f"Position {position_id} not found")

        if position.status != PositionStatus.OPEN:
            raise TradingError(f"Position {position_id} is already closed")

        # Calculate final values
        final_value = position.shares * final_price
        pnl = final_value - (position.initial_value or 0)

        # Update position
        now = datetime.now(timezone.utc)
        position.status = PositionStatus.CLOSED
        position.current_value = final_value
        position.pnl = pnl
        position.closed_at = now

        updated_position = await self._repo.update(position)

        # Update system state
        await self._state.decrement_open_positions()
        await self._state.update_capital(pnl)
        await self._state.record_trade_result(pnl > 0)

        result_emoji = "✅" if pnl >= 0 else "❌"
        self._logger.info(
            f"{result_emoji} Position closed: id={position_id}, "
            f"market={position.market_id}, "
            f"final_value=${final_value:.2f}, pnl=${pnl:.2f}"
        )

        return updated_position

    async def get_open_positions(self) -> list[Position]:
        """Get all open positions.

        Returns:
            List of all open positions

        Example:
            >>> positions = await manager.get_open_positions()
            >>> print(f"Open positions: {len(positions)}")
        """
        positions = await self._repo.get_open_positions()
        self._logger.debug(f"Retrieved {len(positions)} open positions")
        return positions

    async def get_total_exposure(self) -> float:
        """Calculate total exposure across all open positions.

        Returns:
            Total current value of all open positions in USD

        Example:
            >>> exposure = await manager.get_total_exposure()
            >>> print(f"Total exposure: ${exposure:.2f}")
        """
        positions = await self.get_open_positions()
        total = sum(p.current_value or 0 for p in positions)
        self._logger.debug(f"Total exposure: ${total:.2f}")
        return total

    async def get_position_by_market(self, market_id: str) -> Position | None:
        """Get open position for a specific market.

        Args:
            market_id: Market identifier

        Returns:
            Open position if exists, None otherwise

        Example:
            >>> position = await manager.get_position_by_market("btc-100k")
            >>> if position:
            ...     print(f"Position value: ${position.current_value}")
        """
        position = await self._repo.get_by_market(market_id, PositionStatus.OPEN)
        return position
