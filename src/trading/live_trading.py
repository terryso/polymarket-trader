"""Live trading executor for Polymarket.

This module provides the LiveTradingExecutor class that executes real trades
on Polymarket using the CLOB API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.config import settings
from src.exceptions import TradingError, ValidationError
from src.models.position import PositionOutcome
from src.models.prediction import Recommendation
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.storage.repositories.trade_repo import TradeRepository
from src.trading.paper_trading import PaperTradeResult
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from py_clob_client.clob_types import MarketOrderArgs

    from src.api.polymarket import PolymarketClient
    from src.core.state import ThreadSafeState
    from src.models.market import Market
    from src.models.prediction import PredictionResult
    from src.trading.position_manager import PositionManager


logger = get_logger(__name__)


@dataclass
class LiveTradeResult:
    """Result of a live trade execution.

    Attributes:
        trade: The executed trade record
        position: The opened position (if any)
        order_id: Polymarket order ID
        success: Whether the trade was successful
        error_message: Error message if trade failed
    """

    trade: Trade | None = None
    position: "Position | None" = None
    order_id: str | None = None
    success: bool = True
    error_message: str | None = None


class LiveTradingExecutor:
    """Executor for live trading on Polymarket.

    This executor places real orders on Polymarket using the CLOB API.
    It creates Trade records with mode=LIVE and links them to positions.

    Attributes:
        _client: PolymarketClient instance for API calls
        _trade_repo: Repository for trade records
        _position_manager: Manager for position lifecycle
        _state: Thread-safe state for capital tracking

    Example:
        >>> executor = LiveTradingExecutor(client, trade_repo, position_manager, state)
        >>> result = await executor.execute_trade(market, prediction, 50.0)
        >>> if result.success:
        ...     print(f"Order ID: {result.order_id}")
    """

    def __init__(
        self,
        client: "PolymarketClient",
        trade_repo: TradeRepository,
        position_manager: "PositionManager",
        state: "ThreadSafeState",
    ) -> None:
        """Initialize live trading executor.

        Args:
            client: PolymarketClient instance for API calls
            trade_repo: Repository for trade records
            position_manager: Manager for position lifecycle
            state: Thread-safe state for capital tracking
        """
        self._client = client
        self._trade_repo = trade_repo
        self._position_manager = position_manager
        self._state = state
        self._logger = get_logger(__name__)
        self._logger.info("LiveTradingExecutor initialized")

    def _get_trade_type(self, recommendation: Recommendation) -> TradeType:
        """Convert LLM recommendation to trade type.

        Args:
            recommendation: LLM recommendation

        Returns:
            TradeType enum value
        """
        if recommendation == Recommendation.BUY_YES:
            return TradeType.BUY_YES
        elif recommendation == Recommendation.BUY_NO:
            return TradeType.BUY_NO
        else:
            raise ValidationError(f"Cannot trade with recommendation: {recommendation}")

    def _get_token_id(self, market: "Market", trade_type: TradeType) -> str:
        """Get the token ID for the trade.

        Args:
            market: Market to trade
            trade_type: Type of trade (BUY_YES or BUY_NO)

        Returns:
            Token ID for the outcome

        Raises:
            ValidationError: If token IDs not available
        """
        if not market.clob_token_ids or len(market.clob_token_ids) < 2:
            raise ValidationError(
                f"Market {market.id} does not have CLOB token IDs"
            )

        # clob_token_ids[0] = YES token, clob_token_ids[1] = NO token
        if trade_type == TradeType.BUY_YES:
            return market.clob_token_ids[0]
        else:
            return market.clob_token_ids[1]

    def _get_price(self, market: "Market", trade_type: TradeType) -> float:
        """Get the current price for the trade.

        Args:
            market: Market to trade
            trade_type: Type of trade

        Returns:
            Current price (0-1)

        Raises:
            ValidationError: If price not available
        """
        if trade_type == TradeType.BUY_YES:
            if market.yes_price is None:
                raise ValidationError(f"Market {market.id} does not have YES price")
            return market.yes_price
        else:
            if market.no_price is None:
                raise ValidationError(f"Market {market.id} does not have NO price")
            return market.no_price

    def _calculate_shares(self, amount: float, price: float) -> float:
        """Calculate number of shares from amount and price.

        Args:
            amount: Trade amount in USD
            price: Price per share (0-1)

        Returns:
            Number of shares
        """
        if price <= 0:
            raise ValidationError(f"Invalid price: {price}")
        return amount / price

    async def execute_trade(
        self,
        market: "Market",
        prediction: "PredictionResult",
        amount: float,
        prediction_id: int | None = None,
    ) -> LiveTradeResult:
        """Execute a live trade on Polymarket.

        Places a real order on Polymarket CLOB and records the trade.

        Args:
            market: Market to trade
            prediction: LLM prediction with recommendation
            amount: Trade amount in USD
            prediction_id: Optional prediction database ID for linking

        Returns:
            LiveTradeResult with trade and order details

        Raises:
            ValidationError: If parameters are invalid
            TradingError: If trade execution fails
        """
        try:
            # 0. Check for existing open position (prevent duplicate trades)
            existing_position = await self._position_manager.get_position_by_market(market.id)
            if existing_position:
                self._logger.warning(
                    f"Skipping trade: open position already exists for market {market.id} "
                    f"(position_id={existing_position.id})"
                )
                return LiveTradeResult(
                    trade=None,
                    success=False,
                    error_message=f"Open position already exists for market {market.id}",
                )

            # 1. Validate inputs
            if amount <= 0:
                raise ValidationError(f"Invalid trade amount: {amount}")

            if prediction.recommendation == Recommendation.NO_TRADE:
                raise ValidationError("Cannot execute trade with NO_TRADE recommendation")

            # 2. Determine trade type and token
            trade_type = self._get_trade_type(prediction.recommendation)
            token_id = self._get_token_id(market, trade_type)
            price = self._get_price(market, trade_type)
            shares = self._calculate_shares(amount, price)

            self._logger.info(
                f"Placing live order: {trade_type.value} {shares:.4f} shares "
                f"@ ${price:.4f} = ${amount:.2f} on market {market.id}"
            )

            # 3. Place order on Polymarket using create_and_post_order
            from py_clob_client.clob_types import OrderArgs

            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=shares,
                side="BUY",
            )

            # Use the underlying ClobClient to create and post the order
            result = self._client._client.create_and_post_order(order_args)
            self._logger.info(f"Order result: {result}")

            # Extract order ID from result
            if isinstance(result, dict):
                order_id = result.get("orderID") or result.get("order_id") or result.get("id")
                success = result.get("success", False)
                if not success:
                    error_msg = result.get("errorMsg", "Unknown error")
                    raise TradingError(f"Order failed: {error_msg}")
            elif isinstance(result, str):
                order_id = result
            else:
                order_id = str(result)

            self._logger.info(f"Order placed successfully: {order_id}")

            # 4. Create Trade record
            trade = Trade(
                id=0,
                market_id=market.id,
                trade_type=trade_type,
                mode=TradeMode.LIVE,
                amount=amount,
                price=price,
                shares=shares,
                status=TradeStatus.FILLED,  # Market orders are immediately filled
                llm_prediction_id=prediction_id,
                position_id=None,
                polymarket_order_id=order_id,
            )

            # 5. Save trade
            saved_trade = await self._trade_repo.save(trade)
            self._logger.info(f"Trade saved: id={saved_trade.id}, order_id={order_id}")

            # 6. Create Position
            outcome = (
                PositionOutcome.YES
                if trade_type == TradeType.BUY_YES
                else PositionOutcome.NO
            )

            position = await self._position_manager.open_position(
                market_id=market.id,
                outcome=outcome,
                shares=shares,
                price=price,
            )

            # 7. Link trade to position
            saved_trade.position_id = position.id
            await self._trade_repo.save(saved_trade)

            # 8. Update state capital
            await self._state.update_capital(-amount)

            self._logger.info(
                f"Live trade completed: trade_id={saved_trade.id}, "
                f"position_id={position.id}, order_id={order_id}"
            )

            return LiveTradeResult(
                trade=saved_trade,
                position=position,
                order_id=order_id,
                success=True,
            )

        except (ValidationError, TradingError) as e:
            self._logger.error(f"Live trade failed: {e}")
            return LiveTradeResult(
                trade=None,
                success=False,
                error_message=str(e),
            )
        except Exception as e:
            self._logger.error(f"Unexpected error in live trade: {e}")
            return LiveTradeResult(
                trade=None,
                success=False,
                error_message=f"Unexpected error: {e}",
            )
