"""Exit condition checker for position management.

This module provides the ExitChecker class for checking whether positions
should be exited based on configured exit strategies (take profit, stop loss,
time exit, signal exit).

Story 10.3: 退出条件检查器

Usage:
    from src.trading.exit_checker import ExitChecker, ExitCheckResult, ExitReason

    checker = ExitChecker()
    result = await checker.check_exit_conditions(position, market)
    if result.should_exit:
        print(f"Position {result.position_id} should exit: {result.reason}")
"""

from __future__ import annotations

__all__ = ["ExitChecker", "ExitCheckResult", "ExitReason"]

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from src.config import ExitStrategySettings, settings
from src.models.position import Position, PositionOutcome, PositionStatus
from src.models.prediction import Recommendation
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.models.market import Market
    from src.models.prediction import Prediction

logger = get_logger(__name__)


class ExitReason(str, Enum):
    """Exit reason enumeration.

    Defines the possible reasons for exiting a position.

    Attributes:
        TAKE_PROFIT: Position reached take profit threshold
        STOP_LOSS: Position reached stop loss threshold
        TIME_EXIT: Position held longer than configured time limit
        SIGNAL_EXIT: LLM prediction signal reversed
    """

    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TIME_EXIT = "time_exit"
    SIGNAL_EXIT = "signal_exit"


@dataclass
class ExitCheckResult:
    """Exit check result data class.

    Contains the result of checking exit conditions for a position.

    Attributes:
        should_exit: Whether the position should be exited
        reason: Exit reason (take_profit, stop_loss, time_exit, signal_exit)
        priority: Priority level (lower = higher priority)
        position_id: ID of the position being checked
        pnl_pct: Current PnL percentage (optional)

    Priority Constants:
        PRIORITY_STOP_LOSS: 1 (highest priority - limit losses)
        PRIORITY_TAKE_PROFIT: 2 (lock in profits)
        PRIORITY_TIME_EXIT: 3 (capital rotation)
        PRIORITY_SIGNAL_EXIT: 4 (strategy adjustment)
    """

    should_exit: bool
    reason: str
    priority: int
    position_id: int
    pnl_pct: float | None = None

    # Priority constants
    PRIORITY_STOP_LOSS = 1
    PRIORITY_TAKE_PROFIT = 2
    PRIORITY_TIME_EXIT = 3
    PRIORITY_SIGNAL_EXIT = 4


class ExitChecker:
    """Check exit conditions for positions.

    Checks whether positions should be exited based on configured
    exit strategies: take profit, stop loss, time exit, and signal exit.

    Story 10.3: 退出条件检查器

    Attributes:
        config: Exit strategy configuration settings

    Example:
        >>> checker = ExitChecker()
        >>> result = await checker.check_exit_conditions(position, market)
        >>> if result.should_exit:
        ...     print(f"Exit {result.position_id}: {result.reason}")
    """

    def __init__(self, config: ExitStrategySettings | None = None) -> None:
        """Initialize ExitChecker.

        Args:
            config: Exit strategy settings. If None, uses global settings.
        """
        self.config = config or settings.exit_strategy
        self.logger = get_logger(__name__)

    async def check_exit_conditions(
        self,
        position: Position,
        market: Market,
        latest_prediction: Prediction | None = None,
    ) -> ExitCheckResult:
        """Check if a position should be exited.

        Checks exit conditions in priority order:
        1. Stop loss (priority 1) - limit losses first
        2. Take profit (priority 2) - lock in profits
        3. Time exit (priority 3) - capital rotation
        4. Signal exit (priority 4) - strategy adjustment

        Args:
            position: Position to check
            market: Market data for the position
            latest_prediction: Latest LLM prediction for signal exit check

        Returns:
            ExitCheckResult with exit decision and details

        Example:
            >>> result = await checker.check_exit_conditions(position, market)
            >>> if result.should_exit:
            ...     await executor.sell_position(position, result.reason)
        """
        self.logger.debug(
            f"🔍 Checking exit conditions for position {position.id} "
            f"(market: {position.market_id})"
        )

        # Calculate current PnL percentage using REAL-TIME market price
        # This ensures exit decisions are based on current prices, not stale cached values
        pnl_pct = self._calculate_pnl_pct_with_market(position, market)

        # Check in priority order - return immediately if any condition triggers
        # Priority 1: Stop Loss (highest priority - limit losses first)
        if self.config.stop_loss_enabled:
            result = self._check_stop_loss(position, pnl_pct)
            if result.should_exit:
                return result

        # Priority 2: Take Profit (lock in profits)
        if self.config.take_profit_enabled:
            result = self._check_take_profit(position, pnl_pct)
            if result.should_exit:
                return result

        # Priority 3: Time Exit (capital rotation)
        if self.config.time_exit_enabled:
            result = self._check_time_exit(position, pnl_pct)
            if result.should_exit:
                return result

        # Priority 4: Signal Exit (strategy adjustment)
        if self.config.signal_exit_enabled and latest_prediction is not None:
            result = self._check_signal_exit(position, latest_prediction, pnl_pct)
            if result.should_exit:
                return result

        # No exit condition triggered
        self.logger.debug(
            f"🔍 No exit conditions triggered for position {position.id}, "
            f"pnl_pct={pnl_pct:.2%}"
            if pnl_pct is not None
            else "pnl_pct=None"
        )
        return self._no_exit(position, pnl_pct)

    def _calculate_pnl_pct(self, position: Position) -> float | None:
        """Calculate PnL percentage for a position using cached current_value.

        PnL percentage is calculated as:
        pnl_pct = (current_value - initial_value) / initial_value

        WARNING: This uses position.current_value which may be stale.
        Prefer _calculate_pnl_pct_with_market() for real-time PnL calculation.

        Args:
            position: Position to calculate PnL for

        Returns:
            PnL percentage or None if values are not available
        """
        if position.initial_value is None or position.initial_value == 0:
            return None
        if position.current_value is None:
            return None
        return (
            position.current_value - position.initial_value
        ) / position.initial_value

    def _calculate_pnl_pct_with_market(
        self, position: Position, market: Market
    ) -> float | None:
        """Calculate PnL percentage using REAL-TIME market price.

        This is the preferred method for exit decisions because it uses
        the current market price rather than stale position.current_value.

        PnL percentage is calculated as:
        current_value = shares * current_market_price
        pnl_pct = (current_value - initial_value) / initial_value

        Args:
            position: Position to calculate PnL for
            market: Market with current prices

        Returns:
            PnL percentage or None if values are not available
        """
        if position.initial_value is None or position.initial_value == 0:
            self.logger.debug(
                f"Cannot calculate PnL: initial_value is {position.initial_value}"
            )
            return None

        # Get current market price based on position outcome
        if position.outcome == PositionOutcome.YES:
            current_price = market.yes_price
        else:
            current_price = market.no_price

        if current_price is None:
            self.logger.warning(
                f"🔍 Cannot calculate real-time PnL for position {position.id}: "
                f"market {market.id} has no {position.outcome.value} price"
            )
            # Fallback to cached current_value if available
            return self._calculate_pnl_pct(position)

        # Calculate real-time PnL
        current_value = position.shares * current_price
        pnl_pct = (current_value - position.initial_value) / position.initial_value

        self.logger.debug(
            f"🔍 Real-time PnL for position {position.id}: "
            f"shares={position.shares:.2f}, current_price={current_price:.4f}, "
            f"current_value=${current_value:.2f}, initial_value=${position.initial_value:.2f}, "
            f"pnl_pct={pnl_pct:.2%}"
        )

        return pnl_pct

    def _check_take_profit(
        self, position: Position, pnl_pct: float | None
    ) -> ExitCheckResult:
        """Check take profit condition.

        Args:
            position: Position to check
            pnl_pct: Current PnL percentage

        Returns:
            ExitCheckResult with take profit decision
        """
        if pnl_pct is None:
            return self._no_exit(position, pnl_pct)

        if pnl_pct >= self.config.take_profit_pct:
            self.logger.info(
                f"🔍 止盈触发: position_id={position.id}, "
                f"pnl_pct={pnl_pct:.2%}, threshold={self.config.take_profit_pct:.2%}"
            )
            return ExitCheckResult(
                should_exit=True,
                reason=ExitReason.TAKE_PROFIT.value,
                priority=ExitCheckResult.PRIORITY_TAKE_PROFIT,
                position_id=position.id,
                pnl_pct=pnl_pct,
            )

        return self._no_exit(position, pnl_pct)

    def _check_stop_loss(
        self, position: Position, pnl_pct: float | None
    ) -> ExitCheckResult:
        """Check stop loss condition.

        Args:
            position: Position to check
            pnl_pct: Current PnL percentage

        Returns:
            ExitCheckResult with stop loss decision
        """
        if pnl_pct is None:
            return self._no_exit(position, pnl_pct)

        if pnl_pct <= self.config.stop_loss_pct:
            self.logger.info(
                f"🔍 止损触发: position_id={position.id}, "
                f"pnl_pct={pnl_pct:.2%}, threshold={self.config.stop_loss_pct:.2%}"
            )
            return ExitCheckResult(
                should_exit=True,
                reason=ExitReason.STOP_LOSS.value,
                priority=ExitCheckResult.PRIORITY_STOP_LOSS,
                position_id=position.id,
                pnl_pct=pnl_pct,
            )

        return self._no_exit(position, pnl_pct)

    def _check_time_exit(
        self, position: Position, pnl_pct: float | None
    ) -> ExitCheckResult:
        """Check time-based exit condition.

        Args:
            position: Position to check
            pnl_pct: Current PnL percentage (for result)

        Returns:
            ExitCheckResult with time exit decision
        """
        if position.opened_at is None:
            return self._no_exit(position, pnl_pct)

        # Calculate hours held
        hours_held = (
            datetime.now(timezone.utc) - position.opened_at
        ).total_seconds() / 3600

        if hours_held >= self.config.time_exit_hours:
            self.logger.info(
                f"🔍 时间退出触发: position_id={position.id}, "
                f"hours_held={hours_held:.1f}h, threshold={self.config.time_exit_hours}h"
            )
            return ExitCheckResult(
                should_exit=True,
                reason=ExitReason.TIME_EXIT.value,
                priority=ExitCheckResult.PRIORITY_TIME_EXIT,
                position_id=position.id,
                pnl_pct=pnl_pct,
            )

        return self._no_exit(position, pnl_pct)

    def _check_signal_exit(
        self,
        position: Position,
        latest_prediction: Prediction,
        pnl_pct: float | None,
    ) -> ExitCheckResult:
        """Check signal reversal exit condition.

        Signal exit triggers when the latest LLM prediction recommends
        the opposite outcome from the current position.

        Args:
            position: Position to check
            latest_prediction: Latest LLM prediction for the market
            pnl_pct: Current PnL percentage (for result)

        Returns:
            ExitCheckResult with signal exit decision
        """
        # Check if prediction has a recommendation
        if latest_prediction.recommendation is None:
            return self._no_exit(position, pnl_pct)

        # Determine the predicted outcome from recommendation
        predicted_outcome: PositionOutcome | None = None
        if latest_prediction.recommendation == Recommendation.BUY_YES:
            predicted_outcome = PositionOutcome.YES
        elif latest_prediction.recommendation == Recommendation.BUY_NO:
            predicted_outcome = PositionOutcome.NO
        else:
            # NO_TRADE recommendation - no signal exit
            return self._no_exit(position, pnl_pct)

        # Check if prediction direction is opposite to position
        if predicted_outcome != position.outcome:
            self.logger.info(
                f"🔍 信号反转触发: position_id={position.id}, "
                f"position_outcome={position.outcome.value}, "
                f"predicted_outcome={predicted_outcome.value}"
            )
            return ExitCheckResult(
                should_exit=True,
                reason=ExitReason.SIGNAL_EXIT.value,
                priority=ExitCheckResult.PRIORITY_SIGNAL_EXIT,
                position_id=position.id,
                pnl_pct=pnl_pct,
            )

        return self._no_exit(position, pnl_pct)

    def _no_exit(self, position: Position, pnl_pct: float | None) -> ExitCheckResult:
        """Create a no-exit result.

        Args:
            position: Position being checked
            pnl_pct: Current PnL percentage

        Returns:
            ExitCheckResult indicating no exit
        """
        return ExitCheckResult(
            should_exit=False,
            reason="",
            priority=0,
            position_id=position.id,
            pnl_pct=pnl_pct,
        )

    async def check_all_positions(
        self,
        positions: list[Position],
        markets: dict[str, Market],
        predictions: dict[str, Prediction] | None = None,
    ) -> list[ExitCheckResult]:
        """Check exit conditions for all positions.

        Args:
            positions: List of positions to check
            markets: Dictionary mapping market_id to Market
            predictions: Optional dictionary mapping market_id to latest Prediction

        Returns:
            List of ExitCheckResult for positions that need attention
            (only includes positions with should_exit=True or errors)

        Example:
            >>> results = await checker.check_all_positions(positions, markets)
            >>> exit_results = [r for r in results if r.should_exit]
            >>> print(f"{len(exit_results)} positions need to exit")
        """
        results: list[ExitCheckResult] = []
        exit_count = 0
        checked_count = 0

        for position in positions:
            # Skip closed positions
            if position.status != PositionStatus.OPEN:
                continue

            checked_count += 1

            # Get market data
            market = markets.get(position.market_id)
            if market is None:
                self.logger.warning(
                    f"🔍 持仓 {position.id} 的市场 {position.market_id} 不存在"
                )
                continue

            # Get latest prediction if available
            latest_prediction = None
            if predictions is not None:
                latest_prediction = predictions.get(position.market_id)

            # Check exit conditions
            result = await self.check_exit_conditions(
                position, market, latest_prediction
            )
            results.append(result)

            if result.should_exit:
                exit_count += 1

        self.logger.info(
            f"🔍 批量检查完成: 检查 {checked_count} 个持仓, " f"{exit_count} 个触发退出"
        )

        return results
