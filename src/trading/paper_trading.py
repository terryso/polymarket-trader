"""Paper Trading executor for the Polymarket Trader application.

This module provides the PaperTradingExecutor class that simulates
trade execution without placing real orders.

Story 5.2: Paper Trading 执行器
Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源

Example:
    >>> from src.trading.paper_trading import PaperTradingExecutor
    >>> from src.storage.repositories.trade_repo import TradeRepository
    >>> from src.trading.position_manager import PositionManager
    >>> from src.core.state import ThreadSafeState
    >>>
    >>> trade_repo = TradeRepository()
    >>> state = ThreadSafeState(initial_capital=200.0)
    >>> position_manager = PositionManager(position_repo, state)
    >>> executor = PaperTradingExecutor(trade_repo, position_manager, state)
    >>>
    >>> # Execute a paper trade
    >>> result = await executor.execute_trade(market, prediction, 50.0)
    >>> print(f"Trade ID: {result.trade.id}, Shares: {result.trade.shares}")
"""

from __future__ import annotations

__all__ = ["PaperTradingExecutor", "PaperTradeResult"]

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.exceptions import TradingError, ValidationError
from src.models.position import PositionOutcome
from src.models.prediction import Recommendation
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.utils.logger import OPERATION_EMOJIS, get_logger

if TYPE_CHECKING:
    from src.core.state import ThreadSafeState
    from src.models.market import Market
    from src.models.position import Position
    from src.models.prediction import PredictionResult
    from src.storage.repositories.trade_repo import TradeRepository
    from src.trading.position_sync import PositionCacheService
    from src.trading.position_manager import PositionManager


logger = get_logger(__name__)


@dataclass
class PaperTradeResult:
    """Result of a paper trade execution.

    Attributes:
        trade: The executed trade record
        position: The opened position (if any)
        success: Whether the trade was successful
        error_message: Error message if trade failed
    """

    trade: Trade | None = None
    position: "Position | None" = None
    success: bool = True
    error_message: str | None = None


class PaperTradingExecutor:
    """Paper trading executor that simulates trade execution.

    Executes trades in PAPER mode without connecting to real Polymarket API.
    Creates trade records and positions for tracking and analysis.

    Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源
        - Added cache_service for marking cache stale after trades
        - Uses get_position_by_market_from_api for consistency (returns local data in Paper mode)

    Attributes:
        _trade_repo: TradeRepository for saving trade records
        _position_manager: PositionManager for creating positions
        _state: ThreadSafeState for capital tracking
        _cache_service: Optional cache service for marking stale

    Example:
        >>> executor = PaperTradingExecutor(trade_repo, position_manager, state)
        >>> result = await executor.execute_trade(market, prediction, 50.0)
        >>> if result.success:
        ...     print(f"Trade executed: {result.trade.id}")
    """

    def __init__(
        self,
        trade_repo: "TradeRepository",
        position_manager: "PositionManager",
        state: "ThreadSafeState",
        cache_service: "PositionCacheService | None" = None,
    ) -> None:
        """Initialize paper trading executor.

        Args:
            trade_repo: Repository for trade records
            position_manager: Manager for position lifecycle
            state: Thread-safe state manager for capital tracking
            cache_service: Optional cache service for marking stale after trades
        """
        self._trade_repo = trade_repo
        self._position_manager = position_manager
        self._state = state
        self._cache_service = cache_service
        self._logger = get_logger(__name__)
        self._logger.info("PaperTradingExecutor initialized")

    async def execute_trade(
        self,
        market: "Market",
        prediction: "PredictionResult",
        amount: float,
        prediction_id: int | None = None,
    ) -> PaperTradeResult:
        """Execute a paper trade.

        Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源
            - Uses get_position_by_market_from_api for position validation (returns local in Paper)
            - Marks cache stale after successful trade

        Simulates trade execution by:
        1. Creating a Trade record (mode=PAPER, status=FILLED)
        2. Calculating shares based on amount and price
        3. Creating a Position via PositionManager
        4. Linking Trade to Position

        Args:
            market: Market to trade
            prediction: LLM prediction with recommendation
            amount: Trade amount in USD
            prediction_id: Optional prediction database ID for linking

        Returns:
            PaperTradeResult with trade and position details

        Raises:
            ValidationError: If parameters are invalid
            TradingError: If trade execution fails

        Example:
            >>> result = await executor.execute_trade(market, prediction, 50.0)
            >>> if result.success:
            ...     print(f"Bought {result.trade.shares:.2f} shares")
        """
        try:
            # 0. Check for existing position using API method (returns local in Paper mode)
            existing_position = (
                await self._position_manager.get_position_by_market_from_api(market.id)
            )
            if existing_position:
                self._logger.warning(
                    f"{OPERATION_EMOJIS['warning']} Skipping trade: open position already exists "
                    f"for market {market.id} (shares={existing_position.shares:.2f})"
                )
                return PaperTradeResult(
                    trade=None,
                    position=None,
                    success=False,
                    error_message=f"Open position already exists for market {market.id}",
                )

            # Validate inputs
            if amount <= 0:
                raise ValidationError(f"Trade amount must be positive, got {amount}")

            # 1. Determine trade type from recommendation
            trade_type = self._get_trade_type(prediction.recommendation)

            # 2. Get price from market
            price = self._get_price(market, trade_type)
            if price is None or price <= 0 or price >= 1:
                raise ValidationError(f"Invalid price for market {market.id}: {price}")

            # 3. Calculate shares
            shares = self._calculate_shares(amount, price)

            # 4. Create Trade record
            trade = Trade(
                id=0,
                market_id=market.id,
                trade_type=trade_type,
                mode=TradeMode.PAPER,
                amount=amount,
                price=price,
                shares=shares,
                status=TradeStatus.FILLED,  # Paper trades are immediately filled
                llm_prediction_id=prediction_id,
                position_id=None,  # Will be updated after position creation
            )

            # 5. Save trade
            saved_trade = await self._trade_repo.save(trade)
            self._logger.info(
                f"💰 PAPER TRADE created: id={saved_trade.id}, "
                f"type={trade_type.value}, {shares:.2f} shares @ {price:.4f} = ${amount:.2f}"
            )

            # 6. Create position
            outcome = self._determine_outcome(trade_type)
            position = await self._position_manager.open_position(
                market_id=market.id,
                outcome=outcome,
                shares=shares,
                price=price,
            )

            # 7. Update trade with position_id
            saved_trade.position_id = position.id
            # Note: We may need to add an update method to TradeRepository
            # For now, we can save again to update
            await self._trade_repo.save(saved_trade)

            # 8. Mark cache as stale (Tech-Spec: Single Source of Truth)
            if self._cache_service:
                await self._cache_service.mark_stale()
                self._logger.debug(
                    f"{OPERATION_EMOJIS['data']} Cache marked as stale after trade"
                )

            self._logger.info(
                f"{OPERATION_EMOJIS['success']} Paper trade completed: trade_id={saved_trade.id}, "
                f"position_id={position.id}"
            )

            return PaperTradeResult(
                trade=saved_trade,
                position=position,
                success=True,
            )

        except (ValidationError, TradingError) as e:
            self._logger.error(f"{OPERATION_EMOJIS['error']} Paper trade failed: {e}")
            return PaperTradeResult(
                trade=None,
                position=None,
                success=False,
                error_message=str(e),
            )
        except Exception as e:
            self._logger.error(
                f"{OPERATION_EMOJIS['error']} Unexpected error in paper trade: {e}"
            )
            return PaperTradeResult(
                trade=None,
                position=None,
                success=False,
                error_message=f"Unexpected error: {e}",
            )

    def _get_trade_type(self, recommendation: Recommendation) -> TradeType:
        """Convert LLM recommendation to trade type.

        Args:
            recommendation: LLM recommendation

        Returns:
            Corresponding TradeType

        Raises:
            TradingError: If recommendation is NO_TRADE
        """
        if recommendation == Recommendation.BUY_YES:
            return TradeType.BUY_YES
        elif recommendation == Recommendation.BUY_NO:
            return TradeType.BUY_NO
        else:
            raise TradingError(
                f"Cannot execute trade with recommendation: {recommendation.value}"
            )

    def _get_price(self, market: "Market", trade_type: TradeType) -> float | None:
        """Get price from market based on trade type.

        Args:
            market: Market to get price from
            trade_type: Type of trade

        Returns:
            Price (0-1) or None if not available
        """
        if trade_type == TradeType.BUY_YES:
            return market.yes_price
        else:  # BUY_NO
            return market.no_price

    def _calculate_shares(self, amount: float, price: float) -> float:
        """Calculate number of shares from amount and price.

        Args:
            amount: Trade amount in USD
            price: Price per share (0-1)

        Returns:
            Number of shares

        Raises:
            ValidationError: If price is not positive
        """
        if price <= 0:
            raise ValidationError(f"Price must be positive, got {price}")
        return amount / price

    def _determine_outcome(self, trade_type: TradeType) -> PositionOutcome:
        """Determine position outcome from trade type.

        Args:
            trade_type: Type of trade

        Returns:
            Corresponding PositionOutcome
        """
        if trade_type == TradeType.BUY_YES:
            return PositionOutcome.YES
        else:  # BUY_NO
            return PositionOutcome.NO
