"""Pre-trade risk control for the Polymarket Trader application.

This module provides the RiskController class that performs comprehensive
risk checks before each trade is executed.

Story 4.4: 交易前风险检查

Example:
    >>> from src.trading.risk_control import RiskController
    >>> from src.core.circuit_breaker import CircuitBreaker
    >>> from src.core.state import ThreadSafeState
    >>>
    >>> state = ThreadSafeState(initial_capital=200.0)
    >>> circuit_breaker = CircuitBreaker(state)
    >>> controller = RiskController(state, circuit_breaker)
    >>>
    >>> # Check if trade is allowed
    >>> result = await controller.check_trade_allowed(prediction, market)
    >>> if result.allowed:
    ...     print(f"Trade allowed with position ratio: {result.position_ratio}")
"""

from __future__ import annotations

__all__ = ["RiskController", "RiskCheckResult", "RiskCheckFailure"]

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from src.config import settings
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.core.circuit_breaker import CircuitBreaker
    from src.core.state import ThreadSafeState
    from src.models.market import Market
    from src.models.prediction import PredictionResult


class RiskCheckFailure(str, Enum):
    """Types of risk check failures."""

    LOW_CONFIDENCE = "low_confidence"
    LOW_EDGE = "low_edge"
    NO_TRADE_RECOMMENDATION = "no_trade_recommendation"
    MAX_POSITION_PER_MARKET = "max_position_per_market"
    MAX_OPEN_MARKETS = "max_open_markets"
    TRADE_TOO_LARGE = "trade_too_large"
    TRADE_TOO_SMALL = "trade_too_small"
    INSUFFICIENT_CAPITAL = "insufficient_capital"
    TRADING_DISABLED = "trading_disabled"
    CIRCUIT_BREAKER = "circuit_breaker"


@dataclass
class RiskCheckResult:
    """Result of pre-trade risk check.

    Attributes:
        allowed: Whether the trade is allowed
        position_ratio: Suggested position ratio (0-1)
        trade_amount: Calculated trade amount in USD
        reasons: List of reasons if trade is not allowed
        failures: List of specific failure types
    """

    allowed: bool
    position_ratio: float = 1.0
    trade_amount: float = 0.0
    reasons: list[str] = field(default_factory=list)
    failures: list[RiskCheckFailure] = field(default_factory=list)


class RiskController:
    """Pre-trade risk controller.

    Performs comprehensive risk checks before each trade:
    1. Confidence check: LLM confidence >= MIN_CONFIDENCE (75%)
    2. Edge check: Edge >= MIN_EDGE (10%)
    3. Position limits: Single market <= 40%, Max 3 open positions
    4. Capital check: Trade amount within limits

    Attributes:
        _state: ThreadSafeState instance
        _circuit_breaker: CircuitBreaker instance
        _min_confidence: Minimum LLM confidence threshold (0-1)
        _min_edge: Minimum edge threshold (0-1)
        _max_position_per_market: Maximum position ratio per market (0-1)
        _max_open_markets: Maximum number of open positions
        _max_single_ratio: Maximum single trade ratio (0-1)
        _min_bet: Minimum bet amount (USD)
        _market_positions: Dict tracking position values per market

    Example:
        >>> state = ThreadSafeState(initial_capital=200.0)
        >>> circuit_breaker = CircuitBreaker(state)
        >>> controller = RiskController(state, circuit_breaker)
        >>> result = await controller.check_trade_allowed(prediction, market)
    """

    def __init__(
        self,
        state: "ThreadSafeState",
        circuit_breaker: "CircuitBreaker",
        min_confidence: float | None = None,
        min_edge: float | None = None,
        max_position_per_market: float | None = None,
        max_open_markets: int | None = None,
        max_single_ratio: float | None = None,
        min_bet: float | None = None,
    ) -> None:
        """Initialize risk controller.

        Args:
            state: ThreadSafeState instance
            circuit_breaker: CircuitBreaker instance
            min_confidence: Override config value (for testing)
            min_edge: Override config value (for testing)
            max_position_per_market: Override config value (for testing)
            max_open_markets: Override config value (for testing)
            max_single_ratio: Override config value (for testing)
            min_bet: Override config value (for testing)
        """
        self._state = state
        self._circuit_breaker = circuit_breaker
        self._logger = get_logger(__name__)

        # Load from config or use overrides
        self._min_confidence = (
            min_confidence
            if min_confidence is not None
            else settings.risk.min_confidence
        )
        self._min_edge = min_edge if min_edge is not None else settings.risk.min_edge
        self._max_position_per_market = (
            max_position_per_market
            if max_position_per_market is not None
            else settings.risk.max_position_per_market
        )
        self._max_open_markets = (
            max_open_markets
            if max_open_markets is not None
            else settings.risk.max_open_markets
        )
        self._max_single_ratio = (
            max_single_ratio
            if max_single_ratio is not None
            else settings.risk.max_single_ratio
        )
        self._min_bet = min_bet if min_bet is not None else settings.risk.min_bet

        # Track positions per market (market_id -> position_value)
        self._market_positions: dict[str, float] = {}

        self._logger.info(
            f"RiskController initialized: "
            f"min_confidence={self._min_confidence}, "
            f"min_edge={self._min_edge}, "
            f"max_position_per_market={self._max_position_per_market}, "
            f"max_open_markets={self._max_open_markets}, "
            f"max_single_ratio={self._max_single_ratio}, "
            f"min_bet={self._min_bet}"
        )

    async def check_trade_allowed(
        self,
        prediction: "PredictionResult",
        market: "Market",
        current_position_value: float | None = None,
    ) -> RiskCheckResult:
        """Check if trade is allowed based on risk rules.

        Performs comprehensive risk checks:
        1. Circuit breaker check (trading enabled, position ratio)
        2. Confidence check (LLM confidence >= min_confidence)
        3. Edge check (edge >= min_edge)
        4. No-trade recommendation check
        5. Position limit check (single market <= max_position_per_market)
        6. Open positions check (count < max_open_markets)
        7. Trade size check (within capital limits)

        Args:
            prediction: LLM prediction result
            market: Market to trade
            current_position_value: Current position value in this market (if any)

        Returns:
            RiskCheckResult with allowed status, position ratio, and reasons

        Example:
            >>> result = await controller.check_trade_allowed(prediction, market)
            >>> if result.allowed:
            ...     print(f"Trade amount: ${result.trade_amount:.2f}")
        """
        reasons: list[str] = []
        failures: list[RiskCheckFailure] = []
        position_ratio = 1.0

        # Get current state
        state_snapshot = await self._state.get_state()

        # 1. Check circuit breaker first
        breaker_result = await self._circuit_breaker.check_trading_allowed()
        if not breaker_result.allowed:
            reasons.extend(breaker_result.reasons)
            failures.append(RiskCheckFailure.CIRCUIT_BREAKER)
            self._logger.warning(
                f"Risk check failed for market {market.id}: circuit breaker triggered"
            )
            return RiskCheckResult(
                allowed=False,
                position_ratio=0.0,
                trade_amount=0.0,
                reasons=reasons,
                failures=failures,
            )

        # Apply circuit breaker position ratio
        position_ratio = min(position_ratio, breaker_result.position_ratio)

        # Check if trading is disabled in state
        if not state_snapshot.trading_enabled:
            reasons.append("Trading is disabled in system state")
            failures.append(RiskCheckFailure.TRADING_DISABLED)

        # 2. Check confidence
        if prediction.confidence < self._min_confidence:
            reasons.append(
                f"Confidence too low: {prediction.confidence:.2%} < "
                f"{self._min_confidence:.2%}"
            )
            failures.append(RiskCheckFailure.LOW_CONFIDENCE)

        # 3. Check edge
        edge = prediction.edge if prediction.edge is not None else 0.0
        if edge < self._min_edge:
            reasons.append(f"Edge too low: {edge:.2%} < {self._min_edge:.2%}")
            failures.append(RiskCheckFailure.LOW_EDGE)

        # 4. Check recommendation (NO_TRADE is not allowed)
        from src.models.prediction import Recommendation

        if prediction.recommendation == Recommendation.NO_TRADE:
            reasons.append("LLM recommendation is NO_TRADE")
            failures.append(RiskCheckFailure.NO_TRADE_RECOMMENDATION)

        # Early return if confidence/edge/recommendation checks failed
        if failures:
            self._logger.warning(f"Risk check failed for market {market.id}: {reasons}")
            return RiskCheckResult(
                allowed=False,
                position_ratio=position_ratio,
                trade_amount=0.0,
                reasons=reasons,
                failures=failures,
            )

        # 5. Check position limit per market
        current_position = current_position_value or self._market_positions.get(
            market.id, 0.0
        )
        if current_position > 0:
            current_ratio = current_position / state_snapshot.current_capital
            if current_ratio >= self._max_position_per_market:
                reasons.append(
                    f"Position limit reached for market {market.id}: "
                    f"{current_ratio:.2%} >= {self._max_position_per_market:.2%}"
                )
                failures.append(RiskCheckFailure.MAX_POSITION_PER_MARKET)

        # 6. Check open positions count
        if state_snapshot.open_positions_count >= self._max_open_markets:
            # Only fail if this is a new market (not already held)
            if current_position == 0:
                reasons.append(
                    f"Max open markets reached: "
                    f"{state_snapshot.open_positions_count} >= {self._max_open_markets}"
                )
                failures.append(RiskCheckFailure.MAX_OPEN_MARKETS)

        # Early return if position limit checks failed
        if failures:
            self._logger.warning(f"Risk check failed for market {market.id}: {reasons}")
            return RiskCheckResult(
                allowed=False,
                position_ratio=position_ratio,
                trade_amount=0.0,
                reasons=reasons,
                failures=failures,
            )

        # 7. Calculate trade amount and check size limits
        max_trade_amount = (
            state_snapshot.current_capital * self._max_single_ratio * position_ratio
        )

        # Ensure trade amount is within limits
        trade_amount = max_trade_amount
        if trade_amount < self._min_bet:
            reasons.append(
                f"Trade amount too small: ${trade_amount:.2f} < ${self._min_bet:.2f}"
            )
            failures.append(RiskCheckFailure.TRADE_TOO_SMALL)

        if trade_amount > state_snapshot.current_capital:
            reasons.append(
                f"Insufficient capital: ${trade_amount:.2f} > "
                f"${state_snapshot.current_capital:.2f}"
            )
            failures.append(RiskCheckFailure.INSUFFICIENT_CAPITAL)

        # Final decision
        allowed = len(failures) == 0

        if allowed:
            self._logger.info(
                f"Risk check passed for market {market.id}: "
                f"trade_amount=${trade_amount:.2f}, "
                f"position_ratio={position_ratio:.2%}"
            )
        else:
            self._logger.warning(f"Risk check failed for market {market.id}: {reasons}")

        return RiskCheckResult(
            allowed=allowed,
            position_ratio=position_ratio,
            trade_amount=trade_amount if allowed else 0.0,
            reasons=reasons,
            failures=failures,
        )

    def update_market_position(self, market_id: str, position_value: float) -> None:
        """Update tracked position value for a market.

        This method should be called when a position is opened or updated
        to keep the risk controller's internal tracking accurate.

        Args:
            market_id: Market identifier
            position_value: Current position value in USD

        Example:
            >>> controller.update_market_position("market-123", 50.0)
        """
        self._market_positions[market_id] = position_value
        self._logger.debug(
            f"Updated position tracking: {market_id}=${position_value:.2f}"
        )

    def remove_market_position(self, market_id: str) -> None:
        """Remove position tracking for a market.

        Called when a position is closed.

        Args:
            market_id: Market identifier

        Example:
            >>> controller.remove_market_position("market-123")
        """
        if market_id in self._market_positions:
            del self._market_positions[market_id]
            self._logger.debug(f"Removed position tracking: {market_id}")

    def get_market_position(self, market_id: str) -> float:
        """Get tracked position value for a market.

        Args:
            market_id: Market identifier

        Returns:
            Position value in USD (0 if not tracked)

        Example:
            >>> value = controller.get_market_position("market-123")
        """
        return self._market_positions.get(market_id, 0.0)

    def get_total_position_value(self) -> float:
        """Get total value of all tracked positions.

        Returns:
            Total position value in USD

        Example:
            >>> total = controller.get_total_position_value()
        """
        return sum(self._market_positions.values())

    def reset(self) -> None:
        """Reset position tracking.

        Clears all tracked market positions.
        Does not reset ThreadSafeState or CircuitBreaker.

        Example:
            >>> controller.reset()
        """
        self._market_positions.clear()
        self._logger.info("RiskController position tracking reset")

    @property
    def market_positions(self) -> dict[str, float]:
        """Get copy of market positions dict.

        Returns:
            Dict mapping market_id to position value
        """
        return dict(self._market_positions)
