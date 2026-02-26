"""Live trading executor for Polymarket.

This module provides the LiveTradingExecutor class that executes real trades
on Polymarket using the CLOB API.

Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.exceptions import TradingError, ValidationError
from src.models.position import PositionOutcome
from src.models.prediction import Recommendation
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.storage.repositories.trade_repo import TradeRepository
from src.utils.logger import OPERATION_EMOJIS, get_logger

if TYPE_CHECKING:
    from src.api.polymarket import PolymarketClient
    from src.core.state import ThreadSafeState
    from src.models.market import Market
    from src.models.position import Position
    from src.models.prediction import PredictionResult
    from src.trading.position_cache import PositionCacheService
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


@dataclass
class SellResult:
    """Result of a sell position execution.

    Story 10.1: 卖出执行器

    Attributes:
        trade: The executed sell trade record
        position: The updated position after sell
        realized_pnl: Realized profit/loss from this sale
        success: Whether the sell was successful
        error_message: Error message if sell failed
    """

    trade: Trade | None = None
    position: "Position | None" = None
    realized_pnl: float = 0.0
    success: bool = True
    error_message: str | None = None


class LiveTradingExecutor:
    """Executor for live trading on Polymarket.

    This executor places real orders on Polymarket using the CLOB API.
    It creates Trade records with mode=LIVE and links them to positions.

    Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源
        - Added cache_service for marking cache stale after trades
        - Uses get_position_by_market_from_api for trade validation

    Attributes:
        _client: PolymarketClient instance for API calls
        _trade_repo: Repository for trade records
        _position_manager: Manager for position lifecycle
        _state: Thread-safe state for capital tracking
        _cache_service: Optional cache service for marking stale

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
        cache_service: "PositionCacheService | None" = None,
    ) -> None:
        """Initialize live trading executor.

        Args:
            client: PolymarketClient instance for API calls
            trade_repo: Repository for trade records
            position_manager: Manager for position lifecycle
            state: Thread-safe state for capital tracking
            cache_service: Optional cache service for marking stale after trades
        """
        self._client = client
        self._trade_repo = trade_repo
        self._position_manager = position_manager
        self._state = state
        self._cache_service = cache_service
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
        # Try to get token IDs from market object first
        if market.clob_token_ids and len(market.clob_token_ids) >= 2:
            # clob_token_ids[0] = YES token, clob_token_ids[1] = NO token
            if trade_type == TradeType.BUY_YES:
                return market.clob_token_ids[0]
            else:
                return market.clob_token_ids[1]

        # Fallback: Fetch token IDs from Polymarket API
        token_ids = self._fetch_clob_token_ids(market.id)
        if not token_ids or len(token_ids) < 2:
            raise ValidationError(
                f"Market {market.id} does not have CLOB token IDs (not in DB and fetch failed)"
            )

        if trade_type == TradeType.BUY_YES:
            return token_ids[0]
        else:
            return token_ids[1]

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
        if trade_type in (TradeType.BUY_YES, TradeType.SELL_YES):
            if market.yes_price is None:
                raise ValidationError(f"Market {market.id} does not have YES price")
            return market.yes_price
        else:
            if market.no_price is None:
                raise ValidationError(f"Market {market.id} does not have NO price")
            return market.no_price

    def _get_sell_token_id(self, position: "Position", market: "Market") -> str:
        """Get the token ID for selling a position.

        Story 10.1: 卖出执行器

        Args:
            position: Position to sell
            market: Market for the position

        Returns:
            Token ID for the outcome

        Raises:
            ValidationError: If token IDs not available
        """
        # Try to get token IDs from market object first
        if market.clob_token_ids and len(market.clob_token_ids) >= 2:
            # Sell using the token corresponding to the position outcome
            # clob_token_ids[0] = YES token, clob_token_ids[1] = NO token
            if position.outcome == PositionOutcome.YES:
                return market.clob_token_ids[0]
            else:
                return market.clob_token_ids[1]

        # Fallback: Fetch token IDs from Polymarket API
        token_ids = self._fetch_clob_token_ids(market.id)
        if not token_ids or len(token_ids) < 2:
            raise ValidationError(
                f"Market {market.id} does not have CLOB token IDs (not in DB and fetch failed)"
            )

        if position.outcome == PositionOutcome.YES:
            return token_ids[0]
        else:
            return token_ids[1]

    def _fetch_clob_token_ids(self, market_id: str) -> list[str] | None:
        """Fetch CLOB token IDs from Polymarket API.

        Args:
            market_id: Market condition ID

        Returns:
            List of token IDs [YES, NO] or None if fetch failed
        """
        try:
            # Use the CLOB client to get market data
            market_data = self._client._client.get_market(market_id)
            if market_data:
                tokens = market_data.get("tokens", [])
                if len(tokens) >= 2:
                    # tokens[0] = YES, tokens[1] = NO
                    return [tokens[0].get("token_id"), tokens[1].get("token_id")]
            self._logger.warning(
                f"Failed to fetch CLOB token IDs for market {market_id[:10]}..."
            )
            return None
        except Exception as e:
            self._logger.warning(
                f"Error fetching CLOB token IDs for market {market_id[:10]}...: {e}"
            )
            return None

    def _get_sell_trade_type(self, position: "Position") -> TradeType:
        """Determine trade type based on position outcome.

        Story 10.1: 卖出执行器

        Args:
            position: Position to sell

        Returns:
            TradeType.SELL_YES or TradeType.SELL_NO
        """
        if position.outcome == PositionOutcome.YES:
            return TradeType.SELL_YES
        else:
            return TradeType.SELL_NO

    def _get_sell_price(self, position: "Position", market: "Market") -> float:
        """Get the current sell price for a position.

        Story 10.1: 卖出执行器

        To ensure quick execution in CLOB, sell price is set slightly below
        the current market price to match with existing buy orders.

        Args:
            position: Position to sell
            market: Market for the position

        Returns:
            Current sell price (0-1) with small discount for quick execution

        Raises:
            ValidationError: If price not available
        """
        # Discount factor to ensure quick sell execution in CLOB
        # Sell slightly below market price to match with buy orders
        SELL_PRICE_DISCOUNT = 0.02  # 2% discount

        if position.outcome == PositionOutcome.YES:
            if market.yes_price is None:
                raise ValidationError(f"Market {market.id} does not have YES price")
            # Apply discount for quick execution, minimum price is 0.01
            sell_price = market.yes_price * (1 - SELL_PRICE_DISCOUNT)
            return max(sell_price, 0.01)
        else:
            if market.no_price is None:
                raise ValidationError(f"Market {market.id} does not have NO price")
            # Apply discount for quick execution, minimum price is 0.01
            sell_price = market.no_price * (1 - SELL_PRICE_DISCOUNT)
            return max(sell_price, 0.01)

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

        Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源
            - Uses get_position_by_market_from_api for fresh position validation
            - Marks cache stale after successful trade

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
            # 0. Check for existing open position from API (prevent duplicate trades)
            # Tech-Spec: Use API to check for positions (fresh data)
            existing_position = await self._position_manager.get_position_by_market_from_api(market.id)
            if existing_position:
                self._logger.warning(
                    f"{OPERATION_EMOJIS['warning']} Skipping trade: open position already exists "
                    f"for market {market.id} (shares={existing_position.shares:.2f})"
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

            # 9. Mark cache as stale (Tech-Spec: Single Source of Truth)
            if self._cache_service:
                await self._cache_service.mark_stale()
                self._logger.debug(f"{OPERATION_EMOJIS['data']} Cache marked as stale after trade")

            self._logger.info(
                f"{OPERATION_EMOJIS['success']} Live trade completed: trade_id={saved_trade.id}, "
                f"position_id={position.id}, order_id={order_id}"
            )

            return LiveTradeResult(
                trade=saved_trade,
                position=position,
                order_id=order_id,
                success=True,
            )

        except (ValidationError, TradingError) as e:
            self._logger.error(f"{OPERATION_EMOJIS['error']} Live trade failed: {e}")
            return LiveTradeResult(
                trade=None,
                success=False,
                error_message=str(e),
            )
        except Exception as e:
            self._logger.error(f"{OPERATION_EMOJIS['error']} Unexpected error in live trade: {e}")
            return LiveTradeResult(
                trade=None,
                success=False,
                error_message=f"Unexpected error: {e}",
            )

    async def sell_position(
        self,
        position: "Position",
        market: "Market",
        shares: float | None = None,
        reason: str = "manual",
    ) -> SellResult:
        """Sell a position on Polymarket.

        Story 10.1: 卖出执行器
        Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源
            - Gets latest shares from API before selling
            - Marks cache stale after successful sell

        Places a sell order on Polymarket CLOB and records the trade.
        Supports both full and partial position sells.

        Args:
            position: Position to sell
            market: Market for the position
            shares: Number of shares to sell (None = sell all)
            reason: Reason for sell (manual, take_profit, stop_loss, signal)

        Returns:
            SellResult with trade, position, and realized PnL

        Example:
            >>> result = await executor.sell_position(position, market)
            >>> if result.success:
            ...     print(f"Realized PnL: ${result.realized_pnl:.2f}")
        """
        from py_clob_client.clob_types import OrderArgs

        try:
            # 0. Get fresh position data from API (Tech-Spec: Single Source of Truth)
            api_position = await self._position_manager.get_position_by_market_from_api(market.id)
            if api_position is None:
                return SellResult(
                    trade=None,
                    position=position,
                    success=False,
                    error_message=f"No position found on API for market {market.id}",
                )

            # Use API shares for actual sell amount
            actual_shares = api_position.shares
            self._logger.info(
                f"{OPERATION_EMOJIS['network']} API position: {actual_shares:.4f} shares "
                f"(local: {position.shares:.4f})"
            )

            # 1. Validate position
            if position.status != "OPEN":
                return SellResult(
                    trade=None,
                    position=position,
                    success=False,
                    error_message=f"Position {position.id} is not open (status={position.status})",
                )

            # 2. Determine shares to sell (use API shares)
            if shares is None:
                shares_to_sell = actual_shares  # Full sell using API shares
            else:
                if shares <= 0:
                    return SellResult(
                        trade=None,
                        position=position,
                        success=False,
                        error_message=f"Invalid shares amount: {shares}",
                    )
                if shares > actual_shares:
                    self._logger.warning(
                        f"{OPERATION_EMOJIS['warning']} Requested {shares:.4f} shares but API shows "
                        f"{actual_shares:.4f}, will sell {actual_shares:.4f}"
                    )
                    shares_to_sell = actual_shares  # Cap to actual shares
                else:
                    shares_to_sell = shares

            # 3. Get sell parameters
            token_id = self._get_sell_token_id(position, market)
            price = self._get_sell_price(position, market)
            trade_type = self._get_sell_trade_type(position)

            # Calculate proceeds
            sell_proceeds = shares_to_sell * price

            # Calculate realized PnL for this sale
            # PnL = (sell_price - avg_price) * shares_sold
            realized_pnl = (price - position.avg_price) * shares_to_sell

            self._logger.info(
                f"Placing sell order: {trade_type.value} {shares_to_sell:.4f} shares "
                f"@ ${price:.4f} = ${sell_proceeds:.2f} (reason={reason})"
            )

            # 4. Place sell order on Polymarket
            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=shares_to_sell,
                side="SELL",
            )

            result = self._client._client.create_and_post_order(order_args)
            self._logger.info(f"Sell order result: {result}")

            # Extract order ID from result
            if isinstance(result, dict):
                order_id = result.get("orderID") or result.get("order_id") or result.get("id")
                success = result.get("success", False)
                if not success:
                    error_msg = result.get("errorMsg", "Unknown error")
                    raise TradingError(f"Sell order failed: {error_msg}")
            elif isinstance(result, str):
                order_id = result
            else:
                order_id = str(result)

            self._logger.info(f"Sell order placed successfully: {order_id}")

            # 5. Create Trade record
            trade = Trade(
                id=0,
                market_id=position.market_id,
                trade_type=trade_type,
                mode=TradeMode.LIVE,
                amount=sell_proceeds,
                price=price,
                shares=shares_to_sell,
                status=TradeStatus.FILLED,
                position_id=position.id,
                polymarket_order_id=order_id,
            )

            # 6. Save trade
            saved_trade = await self._trade_repo.save(trade)
            self._logger.info(f"Sell trade saved: id={saved_trade.id}, order_id={order_id}")

            # 7. Update or close position
            is_full_sell = shares_to_sell >= actual_shares

            if is_full_sell:
                # Close position completely
                updated_position = await self._position_manager.close_position(
                    position_id=position.id,
                    final_price=price,
                    market=market,
                )
                self._logger.info(
                    f"Position closed: id={position.id}, realized_pnl=${realized_pnl:.2f}"
                )
            else:
                # Partial sell - update position shares and value
                remaining_shares = actual_shares - shares_to_sell
                remaining_value = remaining_shares * price

                # Update position directly in repository
                position.shares = remaining_shares
                position.current_value = remaining_value
                position.pnl = remaining_value - (remaining_shares * position.avg_price)

                updated_position = await self._position_manager._repo.update(position)

                self._logger.info(
                    f"Position reduced: id={position.id}, "
                    f"remaining_shares={remaining_shares:.4f}, "
                    f"realized_pnl=${realized_pnl:.2f}"
                )

            # 8. Update state capital (add proceeds from sale)
            await self._state.update_capital(sell_proceeds)

            # 9. Mark cache as stale (Tech-Spec: Single Source of Truth)
            if self._cache_service:
                await self._cache_service.mark_stale()
                self._logger.debug(f"{OPERATION_EMOJIS['data']} Cache marked as stale after sell")

            self._logger.info(
                f"{OPERATION_EMOJIS['success']} Sell completed: trade_id={saved_trade.id}, "
                f"proceeds=${sell_proceeds:.2f}, realized_pnl=${realized_pnl:.2f}"
            )

            return SellResult(
                trade=saved_trade,
                position=updated_position,
                realized_pnl=realized_pnl,
                success=True,
            )

        except (ValidationError, TradingError) as e:
            self._logger.error(f"{OPERATION_EMOJIS['error']} Sell position failed: {e}")
            return SellResult(
                trade=None,
                position=position,
                success=False,
                error_message=str(e),
            )
        except Exception as e:
            error_str = str(e)
            self._logger.error(f"{OPERATION_EMOJIS['error']} Unexpected error in sell position: {e}")

            # Check if market was resolved (orderbook no longer exists)
            if "orderbook" in error_str.lower() and "does not exist" in error_str.lower():
                self._logger.warning(
                    f"{OPERATION_EMOJIS['warning']} Market appears to be resolved "
                    f"(orderbook not found), closing position {position.id}"
                )
                # Close the position since the market is resolved and can't be traded
                try:
                    closed_position = await self._position_manager.close_position(
                        position_id=position.id,
                        final_price=position.current_value / position.shares if position.shares > 0 else 0,
                        market=market,
                    )
                    self._logger.info(
                        f"{OPERATION_EMOJIS['success']} Position {position.id} closed "
                        f"due to market resolution (orderbook not found)"
                    )
                    return SellResult(
                        trade=None,
                        position=closed_position,
                        realized_pnl=0.0,  # Can't determine PnL without market price
                        success=True,  # Position closed successfully
                        error_message="Market resolved - position closed without trade",
                    )
                except Exception as close_error:
                    self._logger.error(
                        f"{OPERATION_EMOJIS['error']} Failed to close position {position.id} "
                        f"after market resolution: {close_error}"
                    )

            return SellResult(
                trade=None,
                position=position,
                success=False,
                error_message=f"Unexpected error: {e}",
            )
