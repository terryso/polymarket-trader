"""Trading executor for the Polymarket Trader application.

This module provides the TradingExecutor class that orchestrates
the complete trading decision flow from LLM analysis to trade execution.

Story 5.3: 交易决策流程
Story 9.3: 交易事件通知集成

Example:
    >>> from src.trading.executor import TradingExecutor
    >>> from src.analysis.llm_analyzer import LLMAnalyzer
    >>> from src.trading.risk_control import RiskController
    >>> from src.trading.paper_trading import PaperTradingExecutor
    >>> from src.core.state import ThreadSafeState
    >>>
    >>> # Initialize components
    >>> llm_analyzer = LLMAnalyzer()
    >>> risk_controller = RiskController(state, circuit_breaker)
    >>> paper_executor = PaperTradingExecutor(trade_repo, position_manager, state)
    >>>
    >>> executor = TradingExecutor(
    ...     llm_analyzer=llm_analyzer,
    ...     risk_controller=risk_controller,
    ...     paper_executor=paper_executor,
    ...     state=state,
    ... )
    >>>
    >>> # Process a single market
    >>> decision = await executor.process_market(market)
    >>> if decision.success and decision.trade:
    ...     print(f"Trade executed: {decision.trade.id}")
"""

from __future__ import annotations

__all__ = ["TradingExecutor", "TradingDecision"]

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.config import settings
from src.exceptions import TradingError
from src.models.trade import Trade
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.analysis.llm_analyzer import LLMAnalyzer
    from src.core.state import ThreadSafeState
    from src.models.market import Market
    from src.models.position import Position
    from src.models.prediction import PredictionResult
    from src.notifications.telegram_notifier import TelegramNotifier
    from src.trading.paper_trading import PaperTradeResult, PaperTradingExecutor
    from src.trading.risk_control import RiskCheckResult, RiskController


logger = get_logger(__name__)


@dataclass
class TradingDecision:
    """Result of a trading decision for a single market.

    Attributes:
        market_id: ID of the processed market
        success: Whether the decision process completed successfully
        skipped: Whether the trade was skipped (e.g., risk check failed)
        trade: The executed trade (if any)
        position: The opened position (if any)
        prediction: The LLM prediction (if analysis was performed)
        prediction_id: Database ID of the saved prediction
        reason: Reason for skip or failure
        error_message: Error message if process failed
    """

    market_id: str
    success: bool = True
    skipped: bool = False
    trade: Trade | None = None
    position: "Position | None" = None
    prediction: "PredictionResult | None" = None
    prediction_id: int | None = None
    reason: str | None = None
    error_message: str | None = None


class TradingExecutor:
    """Trading executor that orchestrates the complete trading decision flow.

    Coordinates LLM analysis, risk checking, and trade execution to
    automatically process markets and make trading decisions.

    Story 9.3: Added Telegram notification support for trade events.

    The executor selects between paper and live trading based on TRADING_MODE:
    - TRADING_MODE=paper: Uses PaperTradingExecutor (simulation only)
    - TRADING_MODE=live: Uses LiveTradingExecutor (real Polymarket orders)

    Attributes:
        _llm_analyzer: LLMAnalyzer for market analysis
        _risk_controller: RiskController for risk checks
        _paper_executor: PaperTradingExecutor for paper trading
        _live_executor: LiveTradingExecutor for live trading (optional)
        _state: ThreadSafeState for capital tracking
        _notifier: Optional TelegramNotifier for trade notifications

    Example:
        >>> executor = TradingExecutor(
        ...     llm_analyzer=analyzer,
        ...     risk_controller=controller,
        ...     paper_executor=paper_exec,
        ...     live_executor=live_exec,  # Optional, for live trading
        ...     state=state,
        ... )
        >>> decision = await executor.process_market(market)
        >>> if decision.success and not decision.skipped:
        ...     print(f"Trade executed: {decision.trade.id}")
    """

    def __init__(
        self,
        llm_analyzer: "LLMAnalyzer",
        risk_controller: "RiskController",
        paper_executor: "PaperTradingExecutor",
        state: "ThreadSafeState",
        notifier: "TelegramNotifier | None" = None,
        live_executor: "LiveTradingExecutor | None" = None,
    ) -> None:
        """Initialize trading executor.

        Args:
            llm_analyzer: LLM analyzer for market predictions
            risk_controller: Risk controller for trade validation
            paper_executor: Paper trading executor for paper trading
            state: Thread-safe state for capital tracking
            notifier: Optional Telegram notifier for trade notifications
            live_executor: Optional live trading executor for real trades
        """
        self._llm_analyzer = llm_analyzer
        self._risk_controller = risk_controller
        self._paper_executor = paper_executor
        self._live_executor = live_executor
        self._state = state
        self._notifier = notifier
        self._logger = get_logger(__name__)

        # Lazy import to avoid circular dependency
        self._prediction_repo: "PredictionRepository | None" = None

        # Log trading mode
        trading_mode = settings.trading_mode.upper()
        if trading_mode == "LIVE" and live_executor:
            self._logger.info(
                f"TradingExecutor initialized (mode=LIVE, notifications={'enabled' if notifier else 'disabled'})"
            )
        else:
            self._logger.info(
                f"TradingExecutor initialized (mode=PAPER, notifications={'enabled' if notifier else 'disabled'})"
            )

    def _get_executor(self) -> "PaperTradingExecutor | LiveTradingExecutor":
        """Get the appropriate executor based on TRADING_MODE.

        Returns:
            PaperTradingExecutor for paper mode, LiveTradingExecutor for live mode
        """
        trading_mode = settings.trading_mode.upper()
        if trading_mode == "LIVE" and self._live_executor:
            return self._live_executor
        return self._paper_executor

    def _get_prediction_repo(self) -> "PredictionRepository":
        """Get or create PredictionRepository instance."""
        if self._prediction_repo is None:
            from src.storage.repositories.prediction_repo import PredictionRepository

            self._prediction_repo = PredictionRepository()
        return self._prediction_repo

    async def _save_prediction(
        self, market: "Market", prediction: "PredictionResult"
    ) -> int | None:
        """Save prediction to database.

        Args:
            market: Market that was analyzed
            prediction: LLM prediction result

        Returns:
            Prediction ID if saved successfully, None otherwise
        """
        try:
            from src.models.prediction import Prediction
            from src.storage.repositories.market_repo import MarketRepository

            # Ensure market exists in database before saving prediction
            # This is required for the foreign key constraint
            market_repo = MarketRepository()
            existing_market = await market_repo.get_market(market.id)
            if existing_market is None:
                self._logger.warning(
                    f"Market {market.id} not found in database, saving it first"
                )
                await market_repo.save_market(market)

            record = Prediction(
                market_id=market.id,
                predicted_probability=prediction.predicted_probability,
                confidence=prediction.confidence,
                reasoning=prediction.reasoning,
                key_assumptions=prediction.key_assumptions,
                model_used=getattr(prediction, "model_used", "unknown"),
                recommendation=prediction.recommendation.value,
                edge=prediction.edge,
            )
            prediction_id = await self._get_prediction_repo().save_prediction(record)
            self._logger.debug(f"Saved prediction {prediction_id} for market {market.id}")
            return prediction_id
        except Exception as e:
            self._logger.warning(f"Failed to save prediction for market {market.id}: {e}")
            return None

    async def process_market(self, market: "Market") -> TradingDecision:
        """Process a single market and make a trading decision.

        Executes the complete trading flow:
        1. LLM analysis -> get prediction
        2. Risk check -> validate trade allowed
        3. Position sizing -> calculate amount
        4. Trade execution -> execute paper trade

        Story 9.3: Added notification support for trade events.

        Args:
            market: Market to process

        Returns:
            TradingDecision with result of the trading decision

        Example:
            >>> decision = await executor.process_market(market)
            >>> if decision.success and decision.trade:
            ...     print(f"Trade ID: {decision.trade.id}")
        """
        self._logger.info(f"Processing market: {market.id} - {market.title}")

        try:
            # 1. LLM Analysis
            self._logger.debug(f"Analyzing market {market.id}...")
            prediction = await self._llm_analyzer.analyze_market(market)
            self._logger.info(
                f"LLM analysis complete: recommendation={prediction.recommendation.value}, "
                f"confidence={prediction.confidence:.2%}"
            )

            # 1.5. Save prediction to database (always save for accuracy tracking)
            prediction_id = await self._save_prediction(market, prediction)

            # 2. Risk Check
            self._logger.debug(f"Running risk check for market {market.id}...")
            risk_check = await self._risk_controller.check_trade_allowed(
                prediction, market
            )

            if not risk_check.allowed:
                reason = (
                    risk_check.reasons[0] if risk_check.reasons else "Unknown reason"
                )
                self._logger.info(f"Trade rejected for market {market.id}: {reason}")
                return TradingDecision(
                    market_id=market.id,
                    success=True,
                    skipped=True,
                    prediction=prediction,
                    reason=reason,
                    prediction_id=prediction_id,
                )

            # 3. Calculate Position Size
            amount = await self._calculate_position_size(risk_check.position_ratio)
            self._logger.info(
                f"Position size calculated: ${amount:.2f} "
                f"(ratio={risk_check.position_ratio:.2%})"
            )

            # 4. Execute Trade (Paper or Live based on TRADING_MODE)
            executor = self._get_executor()
            trading_mode = settings.trading_mode.upper()
            self._logger.debug(
                f"Executing {trading_mode} trade for market {market.id}..."
            )
            result = await executor.execute_trade(
                market=market,
                prediction=prediction,
                amount=amount,
                prediction_id=prediction_id,
            )

            if not result.success:
                self._logger.error(
                    f"Trade execution failed for market {market.id}: "
                    f"{result.error_message}"
                )

                # Story 9.3: Send failure notification
                await self._notify_trade_failed(
                    market=market,
                    error_message=result.error_message or "Unknown error",
                )

                return TradingDecision(
                    market_id=market.id,
                    success=False,
                    prediction=prediction,
                    error_message=result.error_message,
                )

            # 5. Log Success
            trade = result.trade
            assert trade is not None  # Type guard for mypy
            self._logger.info(
                f"Trade completed for market {market.id}: "
                f"{trade.trade_type.value} "
                f"{trade.shares:.2f} shares @ ${trade.price:.4f} "
                f"= ${amount:.2f}"
            )

            # Story 9.3: Send success notification
            await self._notify_trade_success(trade=trade, market=market)

            return TradingDecision(
                market_id=market.id,
                success=True,
                skipped=False,
                trade=result.trade,
                position=result.position,
                prediction=prediction,
            )

        except Exception as e:
            self._logger.error(f"Unexpected error processing market {market.id}: {e}")

            # Story 9.3: Send error notification
            await self._notify_trade_failed(
                market=market,
                error_message=f"Unexpected error: {e}",
            )

            return TradingDecision(
                market_id=market.id,
                success=False,
                error_message=f"Unexpected error: {e}",
            )

    async def process_markets(self, markets: list["Market"]) -> list[TradingDecision]:
        """Process multiple markets and make trading decisions.

        Args:
            markets: List of markets to process

        Returns:
            List of TradingDecision results for each market

        Example:
            >>> decisions = await executor.process_markets(markets)
            >>> successful = [d for d in decisions if d.success and d.trade]
            >>> print(f"Executed {len(successful)} trades")
        """
        self._logger.info(f"Processing {len(markets)} markets...")

        decisions: list[TradingDecision] = []

        for i, market in enumerate(markets, 1):
            self._logger.debug(f"Processing market {i}/{len(markets)}: {market.id}")
            decision = await self.process_market(market)
            decisions.append(decision)

        # Log summary
        successful = sum(1 for d in decisions if d.success and d.trade)
        skipped = sum(1 for d in decisions if d.skipped)
        failed = sum(1 for d in decisions if not d.success)

        self._logger.info(
            f"Batch processing complete: "
            f"{successful} trades executed, {skipped} skipped, {failed} failed"
        )

        return decisions

    async def _calculate_position_size(self, position_ratio: float) -> float:
        """Calculate position size based on ratio and current capital.

        Args:
            position_ratio: Ratio of capital to use (0-1)

        Returns:
            Position size in USD

        Raises:
            TradingError: If calculated amount is below minimum bet
        """
        state = await self._state.get_state()
        capital = state.current_capital

        # Calculate raw amount
        amount = capital * position_ratio

        # Apply constraints
        min_bet = settings.risk.min_bet
        max_amount = capital * settings.risk.max_single_ratio

        # Ensure minimum bet
        if amount < min_bet:
            self._logger.warning(
                f"Calculated amount ${amount:.2f} below minimum ${min_bet:.2f}, "
                f"adjusting to minimum"
            )
            amount = min_bet

        # Ensure maximum single ratio
        if amount > max_amount:
            self._logger.warning(
                f"Calculated amount ${amount:.2f} above maximum ${max_amount:.2f}, "
                f"adjusting to maximum"
            )
            amount = max_amount

        # Final validation
        if amount < min_bet:
            raise TradingError(
                f"Cannot meet minimum bet requirement: "
                f"capital=${capital:.2f}, min_bet=${min_bet:.2f}"
            )

        return amount

    async def _notify_trade_success(
        self,
        trade: Trade,
        market: "Market",
    ) -> None:
        """Send trade success notification.

        Story 9.3: 交易事件通知集成

        Args:
            trade: The executed trade
            market: The market for the trade
        """
        if not self._notifier:
            return

        try:
            success = await self._notifier.send_trade_notification(trade, market)
            if success:
                self._logger.debug(f"Trade notification sent for trade {trade.id}")
            else:
                self._logger.warning(
                    f"Failed to send trade notification for trade {trade.id}"
                )
        except Exception as e:
            # Don't let notification failure affect main flow
            self._logger.error(f"Error sending trade notification: {e}")

    async def _notify_trade_failed(
        self,
        market: "Market",
        error_message: str,
    ) -> None:
        """Send trade failure notification.

        Story 9.3: 交易事件通知集成

        Args:
            market: The market that failed
            error_message: The error message
        """
        if not self._notifier:
            return

        try:
            error_msg = f"Trade failed for {market.title}: {error_message}"
            success = await self._notifier.send_error_notification(error_msg)
            if success:
                self._logger.debug("Trade failure notification sent")
            else:
                self._logger.warning("Failed to send trade failure notification")
        except Exception as e:
            # Don't let notification failure affect main flow
            self._logger.error(f"Error sending trade failure notification: {e}")
