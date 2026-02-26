"""Position management for the Polymarket Trader application.

This module provides the PositionManager class that handles all
position lifecycle operations including opening, updating, and closing.
Also provides PnL calculation functionality for simulated positions.

Story 4.5: 持仓管理
Story 5.4: 模拟持仓 PnL 计算
Story 9.3: 交易事件通知集成
Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源

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
    >>>
    >>> # Calculate PnL
    >>> result = manager.calculate_pnl(position, current_price=0.55)
    >>> print(f"PnL: ${result.pnl:.2f} ({result.pnl_pct:.2%})")
"""

from __future__ import annotations

__all__ = ["PositionManager", "PnLResult", "TotalPnLResult"]

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.config import settings
from src.exceptions import TradingError, ValidationError
from src.models.position import Position, PositionOutcome, PositionStatus
from src.utils.logger import OPERATION_EMOJIS, get_logger

if TYPE_CHECKING:
    from src.api.polymarket import PolymarketClient
    from src.core.state import ThreadSafeState
    from src.models.market import Market
    from src.notifications.telegram_notifier import TelegramNotifier
    from src.storage.repositories.position_repo import PositionRepository


logger = get_logger(__name__)


@dataclass
class PnLResult:
    """Result of PnL calculation for a single position.

    Attributes:
        pnl: Absolute profit/loss in USD
        pnl_pct: Profit/loss percentage (0-1 range, negative for loss)
        current_value: Current market value in USD
    """

    pnl: float
    pnl_pct: float
    current_value: float


@dataclass
class TotalPnLResult:
    """Result of total PnL calculation across all positions.

    Attributes:
        total_pnl: Total profit/loss across all positions in USD
        positions_count: Number of positions included in calculation
        winning_count: Number of profitable positions (pnl > 0)
        losing_count: Number of losing positions (pnl < 0)
    """

    total_pnl: float
    positions_count: int
    winning_count: int
    losing_count: int


class PositionManager:
    """Position lifecycle manager.

    Manages the complete lifecycle of trading positions:
    - Opening new positions
    - Updating position values
    - Closing positions
    - Tracking total exposure

    Story 9.3: Added Telegram notification support for position events.

    Attributes:
        _repo: PositionRepository for database operations
        _state: ThreadSafeState for system state tracking
        _notifier: Optional TelegramNotifier for position notifications

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
        notifier: "TelegramNotifier | None" = None,
    ) -> None:
        """Initialize position manager.

        Args:
            repository: PositionRepository for database operations
            state: ThreadSafeState for system state tracking
            notifier: Optional Telegram notifier for position notifications
        """
        self._repo = repository
        self._state = state
        self._notifier = notifier
        self._logger = get_logger(__name__)

        # Log notification status
        if self._notifier:
            self._logger.info("PositionManager initialized (notifications=enabled)")
        else:
            self._logger.info("PositionManager initialized (notifications=disabled)")

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
        market: "Market | None" = None,
    ) -> Position:
        """Close an open position.

        Story 9.3: Added optional market parameter and notification support.

        Args:
            position_id: Position identifier
            final_price: Final market price at close (0-1)
            market: Optional market for notification (includes market title)

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

        # Calculate PnL percentage
        initial_value = position.initial_value or 0
        if initial_value > 0:
            pnl_pct = pnl / initial_value
        else:
            pnl_pct = 0.0

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

        # Story 9.3: Send position closed notification
        if self._notifier and market:
            await self._notify_position_closed(
                position=updated_position,
                market=market,
                pnl=pnl,
                pnl_pct=pnl_pct,
            )

        return updated_position

    async def _notify_position_closed(
        self,
        position: Position,
        market: "Market",
        pnl: float,
        pnl_pct: float,
    ) -> None:
        """Send position closed notification.

        Story 9.3: 交易事件通知集成

        Args:
            position: The closed position
            market: The market for the position
            pnl: Profit/loss amount in USD
            pnl_pct: Profit/loss percentage
        """
        if not self._notifier:
            return

        try:
            success = await self._notifier.send_position_closed_notification(
                position=position,
                market=market,
                pnl=pnl,
                pnl_pct=pnl_pct,
            )
            if success:
                self._logger.debug(
                    f"Position closed notification sent for position {position.id}"
                )
            else:
                self._logger.warning(
                    f"Failed to send position closed notification for position {position.id}"
                )
        except Exception as e:
            # Don't let notification failure affect main flow
            self._logger.error(f"Error sending position closed notification: {e}")

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

    def calculate_pnl(self, position: Position, current_price: float) -> PnLResult:
        """Calculate PnL for a single position.

        PnL calculation formula:
        - For both YES and NO outcomes: pnl = shares * (current_price - avg_price)
        - This works because we hold shares directly in the outcome type

        Args:
            position: Position to calculate PnL for
            current_price: Current market price for the outcome (0-1)

        Returns:
            PnLResult with pnl, pnl_pct, and current_value

        Raises:
            ValidationError: If current_price is not between 0 and 1

        Example:
            >>> # BUY_YES position with profit
            >>> result = manager.calculate_pnl(position, current_price=0.55)
            >>> print(f"PnL: ${result.pnl:.2f} ({result.pnl_pct:.2%})")
        """
        # Validate current_price
        if not 0 < current_price < 1:
            raise ValidationError(
                f"Current price must be between 0 and 1, got {current_price}"
            )

        # Calculate current value
        current_value = position.shares * current_price

        # Calculate PnL based on outcome
        # For both YES and NO, we use the same formula since we're
        # buying the outcome directly (YES shares or NO shares)
        pnl = position.shares * (current_price - position.avg_price)

        # Calculate PnL percentage
        initial_value = position.initial_value or 0
        if initial_value > 0:
            pnl_pct = pnl / initial_value
        else:
            pnl_pct = 0.0

        self._logger.debug(
            f"📊 PnL calculated for position {position.id}: "
            f"pnl=${pnl:.2f}, pnl_pct={pnl_pct:.2%}, "
            f"current_value=${current_value:.2f}"
        )

        return PnLResult(
            pnl=pnl,
            pnl_pct=pnl_pct,
            current_value=current_value,
        )

    async def calculate_total_pnl(self) -> TotalPnLResult:
        """Calculate total PnL across all open positions.

        Note: This method uses the pnl stored in each position,
        which should be updated via update_all_positions_value first.

        Returns:
            TotalPnLResult with aggregated PnL statistics

        Example:
            >>> result = await manager.calculate_total_pnl()
            >>> print(f"Total PnL: ${result.total_pnl:.2f}")
            >>> print(f"Winning: {result.winning_count}, Losing: {result.losing_count}")
        """
        positions = await self.get_open_positions()

        total_pnl = 0.0
        winning_count = 0
        losing_count = 0

        for position in positions:
            pnl = position.pnl or 0
            total_pnl += pnl

            if pnl > 0:
                winning_count += 1
            elif pnl < 0:
                losing_count += 1

        self._logger.info(
            f"📊 Total PnL: ${total_pnl:.2f} "
            f"({winning_count} winning, {losing_count} losing, "
            f"{len(positions)} total)"
        )

        return TotalPnLResult(
            total_pnl=total_pnl,
            positions_count=len(positions),
            winning_count=winning_count,
            losing_count=losing_count,
        )

    async def update_all_positions_value(
        self, market_prices: dict[str, float]
    ) -> list[Position]:
        """Update current value and PnL for all open positions.

        Args:
            market_prices: Dictionary mapping market_id to current price
                          for the outcome held (YES price for YES positions,
                          NO price for NO positions)

        Returns:
            List of updated positions

        Example:
            >>> prices = {"market-1": 0.55, "market-2": 0.40}
            >>> updated = await manager.update_all_positions_value(prices)
            >>> print(f"Updated {len(updated)} positions")
        """
        positions = await self.get_open_positions()
        updated_positions: list[Position] = []

        for position in positions:
            current_price = market_prices.get(position.market_id)

            if current_price is None:
                self._logger.warning(
                    f"⚠️ No price available for market {position.market_id}, "
                    f"skipping position {position.id}"
                )
                continue

            try:
                updated = await self.update_position_value(position.id, current_price)
                updated_positions.append(updated)
            except (ValidationError, TradingError) as e:
                self._logger.error(f"❌ Failed to update position {position.id}: {e}")

        self._logger.info(
            f"📊 Updated {len(updated_positions)}/{len(positions)} positions"
        )

        return updated_positions

    # ========================================================================
    # API Fetch Methods (Single Source of Truth)
    # Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源
    # ========================================================================

    async def fetch_positions_from_api(self) -> list[Position]:
        """Fetch positions directly from Polymarket API (no cache).

        This method bypasses the cache and fetches fresh data from the API.
        Paper mode returns local database positions.

        Used for trading decisions where fresh data is critical.

        Returns:
            List of current positions from API (or local database in Paper mode)

        Raises:
            TradingError: If API call fails in Live mode

        Example:
            >>> positions = await manager.fetch_positions_from_api()
            >>> print(f"Current positions: {len(positions)}")
        """
        # Paper mode: return local database positions
        if settings.trading_mode == "paper":
            self._logger.info(
                f"{OPERATION_EMOJIS['data']} Paper mode: returning local positions"
            )
            return await self._repo.get_open_positions()

        # Live mode: fetch from API
        from src.api.polymarket import PolymarketClient

        client = None
        try:
            client = PolymarketClient()

            # Fetch balances using asyncio.to_thread for sync API call
            balance_result = await asyncio.to_thread(client.get_balances)

            if not balance_result.is_success:
                raise TradingError(
                    f"Failed to fetch positions from API: {balance_result.error}"
                )

            # Convert balances to Position objects
            positions: list[Position] = []
            for balance in balance_result.balances:
                if balance.shares <= 0:
                    continue

                # Normalize outcome
                outcome_value = balance.outcome.upper()
                if outcome_value not in ("YES", "NO"):
                    outcome_value = "YES"

                avg_price = balance.avg_price if balance.avg_price is not None else 0.5
                current_value = balance.shares * avg_price

                position = Position(
                    id=0,  # Not from database
                    market_id=balance.condition_id,
                    outcome=PositionOutcome(outcome_value),
                    shares=balance.shares,
                    avg_price=avg_price,
                    initial_value=current_value,  # We don't have initial value from API
                    current_value=current_value,
                    pnl=0.0,
                    status=PositionStatus.OPEN,
                    opened_at=datetime.now(timezone.utc),
                )
                positions.append(position)

            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Fetched {len(positions)} positions from API"
            )
            return positions

        except Exception as e:
            error_msg = str(e)
            self._logger.error(
                f"{OPERATION_EMOJIS['network']} Failed to fetch positions: {error_msg}"
            )
            raise TradingError(f"Failed to fetch positions from API: {error_msg}") from e

        finally:
            if client:
                client.close()

    async def get_position_by_market_from_api(self, market_id: str) -> Position | None:
        """Fetch position for a specific market from API (no cache).

        This method bypasses the cache and fetches fresh data from the API.
        Paper mode queries the local database.

        Used for trading decisions where fresh data is critical.

        Args:
            market_id: Market identifier (condition_id)

        Returns:
            Position if exists, None otherwise

        Example:
            >>> position = await manager.get_position_by_market_from_api("btc-100k")
            >>> if position:
            ...     print(f"Holdings: {position.shares} shares")
        """
        # Paper mode: query local database
        if settings.trading_mode == "paper":
            self._logger.debug(
                f"{OPERATION_EMOJIS['data']} Paper mode: querying local position for {market_id}"
            )
            return await self._repo.get_by_market(market_id, PositionStatus.OPEN)

        # Live mode: fetch from API
        positions = await self.fetch_positions_from_api()

        # Find the position for this market
        for position in positions:
            if position.market_id == market_id and position.status == PositionStatus.OPEN:
                self._logger.debug(
                    f"{OPERATION_EMOJIS['data']} Found API position for {market_id}: "
                    f"{position.shares} shares"
                )
                return position

        self._logger.debug(
            f"{OPERATION_EMOJIS['data']} No API position found for {market_id}"
        )
        return None
