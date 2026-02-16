"""Circuit breaker implementation for risk control.

This module provides a circuit breaker that monitors trading state
and triggers protective measures when risk thresholds are exceeded.

Example:
    >>> from src.core.circuit_breaker import CircuitBreaker
    >>> from src.core.state import ThreadSafeState
    >>>
    >>> state = ThreadSafeState(initial_capital=200.0)
    >>> breaker = CircuitBreaker(state)
    >>>
    >>> # Check if trading is allowed
    >>> result = await breaker.check_trading_allowed()
    >>> if result.allowed:
    ...     position_ratio = result.position_ratio
    ...     # Execute trade with position_ratio
"""

from __future__ import annotations

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerResult",
    "BreakerTrigger",
    "BreakerTriggerType",
]

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from src.config import settings
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.core.state import StateSnapshot, ThreadSafeState

logger = get_logger(__name__)


class BreakerTriggerType(str, Enum):
    """Types of circuit breaker triggers."""

    CONSECUTIVE_LOSSES = "consecutive_losses"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    CAPITAL_THRESHOLD = "capital_threshold"


@dataclass
class BreakerTrigger:
    """Record of a circuit breaker trigger event."""

    trigger_type: BreakerTriggerType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: str = ""


@dataclass
class CircuitBreakerResult:
    """Result of circuit breaker check.

    Attributes:
        allowed: Whether trading is allowed
        position_ratio: Suggested position ratio (0-1)
        reasons: List of reasons if trading is not allowed or restricted
        triggers: List of triggered breakers
    """

    allowed: bool
    position_ratio: float = 1.0
    reasons: list[str] = field(default_factory=list)
    triggers: list[BreakerTrigger] = field(default_factory=list)


class CircuitBreaker:
    """Circuit breaker for risk control.

    Monitors trading state and triggers protective measures when
    risk thresholds are exceeded.

    The circuit breaker checks three conditions:
    1. Consecutive losses: Reduces position size after 3+ consecutive losses
    2. Daily loss limit: Stops trading when daily loss exceeds 30%
    3. Capital threshold: Reduces position size when capital falls below $100

    Attributes:
        _state: ThreadSafeState instance to monitor
        _consecutive_losses_limit: Threshold for consecutive loss breaker
        _reduce_ratio_after_losses: Position ratio after consecutive losses
        _daily_loss_limit: Daily loss percentage threshold
        _capital_threshold: Low capital threshold
        _reduce_ratio_low_capital: Position ratio for low capital
        _initial_capital: Initial capital for percentage calculations
        _triggered_breakers: List of triggered breaker events

    Example:
        >>> state = ThreadSafeState(initial_capital=200.0)
        >>> breaker = CircuitBreaker(state)
        >>> result = await breaker.check_trading_allowed()
        >>> print(f"Allowed: {result.allowed}, Ratio: {result.position_ratio}")
    """

    def __init__(
        self,
        state: "ThreadSafeState",
        consecutive_losses_limit: int | None = None,
        reduce_ratio_after_losses: float | None = None,
        daily_loss_limit: float | None = None,
        capital_threshold: float | None = None,
        reduce_ratio_low_capital: float | None = None,
        initial_capital: float | None = None,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            state: ThreadSafeState instance to monitor
            consecutive_losses_limit: Override config value (for testing)
            reduce_ratio_after_losses: Override config value (for testing)
            daily_loss_limit: Override config value (for testing)
            capital_threshold: Override config value (for testing)
            reduce_ratio_low_capital: Override config value (for testing)
            initial_capital: Override config value (for testing)
        """
        self._state = state
        self._consecutive_losses_limit = (
            consecutive_losses_limit
            if consecutive_losses_limit is not None
            else settings.risk.consecutive_losses_limit
        )
        self._reduce_ratio_after_losses = (
            reduce_ratio_after_losses
            if reduce_ratio_after_losses is not None
            else settings.risk.reduce_ratio_after_losses
        )
        self._daily_loss_limit = (
            daily_loss_limit
            if daily_loss_limit is not None
            else settings.risk.daily_loss_limit
        )
        self._capital_threshold = (
            capital_threshold
            if capital_threshold is not None
            else settings.risk.capital_threshold
        )
        self._reduce_ratio_low_capital = (
            reduce_ratio_low_capital
            if reduce_ratio_low_capital is not None
            else settings.risk.reduce_ratio_low_capital
        )
        self._initial_capital = (
            initial_capital if initial_capital is not None else settings.initial_capital
        )
        self._triggered_breakers: list[BreakerTrigger] = []

    async def check_trading_allowed(self) -> CircuitBreakerResult:
        """Check if trading is allowed and get position ratio.

        Runs all circuit breaker checks and returns the result.

        Returns:
            CircuitBreakerResult with allowed status, position ratio, and reasons

        Example:
            >>> result = await breaker.check_trading_allowed()
            >>> if not result.allowed:
            ...     print(f"Trading stopped: {result.reasons}")
        """
        reasons: list[str] = []
        triggers: list[BreakerTrigger] = []
        position_ratio = 1.0
        allowed = True

        # Get current state
        state_snapshot = await self._state.get_state()

        # Check daily loss limit first (most severe)
        daily_loss_trigger = await self._check_daily_loss(state_snapshot)
        if daily_loss_trigger:
            triggers.append(daily_loss_trigger)
            reasons.append(
                f"Daily loss limit exceeded: {abs(state_snapshot.daily_pnl):.2f} / "
                f"{self._initial_capital * self._daily_loss_limit:.2f}"
            )
            allowed = False
            # Daily loss is the most severe, return immediately
            self._triggered_breakers.extend(triggers)
            return CircuitBreakerResult(
                allowed=False,
                position_ratio=0.0,
                reasons=reasons,
                triggers=triggers,
            )

        # Check consecutive losses
        consecutive_trigger = await self._check_consecutive_losses(state_snapshot)
        if consecutive_trigger:
            triggers.append(consecutive_trigger)
            reasons.append(
                f"Consecutive losses exceeded: {state_snapshot.consecutive_losses} / "
                f"{self._consecutive_losses_limit}"
            )
            position_ratio = min(position_ratio, self._reduce_ratio_after_losses)

        # Check capital threshold
        capital_trigger = await self._check_capital_threshold(state_snapshot)
        if capital_trigger:
            triggers.append(capital_trigger)
            reasons.append(
                f"Capital below threshold: ${state_snapshot.current_capital:.2f} < "
                f"${self._capital_threshold:.2f}"
            )
            position_ratio = min(position_ratio, self._reduce_ratio_low_capital)

        # Update state if in reduced mode
        if position_ratio < 1.0 and not state_snapshot.reduced_mode:
            await self._state.set_reduced_mode(True)

        # Log if trading is restricted
        if reasons:
            logger.warning(f"Circuit breaker triggered: {reasons}")

        # Store triggers
        self._triggered_breakers.extend(triggers)

        return CircuitBreakerResult(
            allowed=allowed,
            position_ratio=position_ratio,
            reasons=reasons,
            triggers=triggers,
        )

    async def _check_consecutive_losses(
        self, state_snapshot: "StateSnapshot"
    ) -> BreakerTrigger | None:
        """Check consecutive losses breaker.

        Args:
            state_snapshot: Current state snapshot

        Returns:
            BreakerTrigger if triggered, None otherwise
        """
        if state_snapshot.consecutive_losses >= self._consecutive_losses_limit:
            logger.warning(
                f"Consecutive losses breaker triggered: "
                f"{state_snapshot.consecutive_losses} losses"
            )
            return BreakerTrigger(
                trigger_type=BreakerTriggerType.CONSECUTIVE_LOSSES,
                details=f"Consecutive losses: {state_snapshot.consecutive_losses}",
            )
        return None

    async def _check_daily_loss(
        self, state_snapshot: "StateSnapshot"
    ) -> BreakerTrigger | None:
        """Check daily loss limit breaker.

        Args:
            state_snapshot: Current state snapshot

        Returns:
            BreakerTrigger if triggered, None otherwise
        """
        # Only check if there's a loss (negative daily_pnl)
        if state_snapshot.daily_pnl >= 0:
            return None

        loss_ratio = abs(state_snapshot.daily_pnl) / self._initial_capital
        if loss_ratio >= self._daily_loss_limit:
            logger.critical(
                f"Daily loss limit breaker triggered: "
                f"{loss_ratio * 100:.1f}% loss (limit: {self._daily_loss_limit * 100:.1f}%)"
            )
            await self._state.set_trading_enabled(False)
            return BreakerTrigger(
                trigger_type=BreakerTriggerType.DAILY_LOSS_LIMIT,
                details=f"Daily loss: {loss_ratio * 100:.1f}%",
            )
        return None

    async def _check_capital_threshold(
        self, state_snapshot: "StateSnapshot"
    ) -> BreakerTrigger | None:
        """Check capital threshold breaker.

        Args:
            state_snapshot: Current state snapshot

        Returns:
            BreakerTrigger if triggered, None otherwise
        """
        if state_snapshot.current_capital < self._capital_threshold:
            logger.warning(
                f"Capital threshold breaker triggered: "
                f"${state_snapshot.current_capital:.2f} < ${self._capital_threshold:.2f}"
            )
            return BreakerTrigger(
                trigger_type=BreakerTriggerType.CAPITAL_THRESHOLD,
                details=f"Capital: ${state_snapshot.current_capital:.2f}",
            )
        return None

    async def get_position_ratio(self) -> float:
        """Get current suggested position ratio.

        This is a convenience method that calls check_trading_allowed()
        and returns only the position ratio.

        Returns:
            float: Suggested position ratio (0-1)

        Example:
            >>> ratio = await breaker.get_position_ratio()
            >>> trade_amount = capital * ratio
        """
        result = await self.check_trading_allowed()
        return result.position_ratio

    async def record_loss(self, amount: float) -> None:
        """Record a loss and update state.

        This method updates the capital and records the trade result.
        The circuit breaker checks will be performed on the next
        check_trading_allowed() call.

        Args:
            amount: Loss amount (positive value)

        Example:
            >>> await breaker.record_loss(10.0)  # Record $10 loss
        """
        await self._state.update_capital(-abs(amount))
        await self._state.record_trade_result(is_win=False)

    def reset(self) -> None:
        """Reset circuit breaker state.

        Clears all triggered breaker records. Does not reset ThreadSafeState.

        Example:
            >>> breaker.reset()
        """
        self._triggered_breakers.clear()
        logger.info("Circuit breaker reset")

    def get_triggered_breakers(self) -> list[BreakerTrigger]:
        """Get list of triggered breakers.

        Returns:
            List of BreakerTrigger records

        Example:
            >>> triggers = breaker.get_triggered_breakers()
            >>> for trigger in triggers:
            ...     print(f"{trigger.trigger_type}: {trigger.details}")
        """
        return list(self._triggered_breakers)
