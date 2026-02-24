"""Tests for CircuitBreaker.

This module tests the circuit breaker functionality including
consecutive losses, daily loss limit, and capital threshold breakers.
"""

from __future__ import annotations

import pytest

from src.core.circuit_breaker import (
    BreakerTrigger,
    BreakerTriggerType,
    CircuitBreaker,
    CircuitBreakerResult,
)
from src.core.state import ThreadSafeState


class TestCircuitBreaker:
    """Test CircuitBreaker."""

    @pytest.fixture
    def state(self) -> ThreadSafeState:
        """Create a test state manager."""
        return ThreadSafeState(initial_capital=200.0)

    @pytest.fixture
    def breaker(self, state: ThreadSafeState) -> CircuitBreaker:
        """Create a test circuit breaker."""
        return CircuitBreaker(
            state,
            consecutive_losses_limit=3,
            reduce_ratio_after_losses=0.10,
            daily_loss_limit=0.30,
            capital_threshold=100.0,
            reduce_ratio_low_capital=0.10,
            initial_capital=200.0,
            disable_circuit_breaker=False,
        )

    @pytest.mark.asyncio
    async def test_initial_state_no_breaker(self, breaker: CircuitBreaker) -> None:
        """Test initial state with no breaker triggered."""
        result = await breaker.check_trading_allowed()
        assert result.allowed is True
        assert result.position_ratio == 1.0
        assert len(result.reasons) == 0
        assert len(result.triggers) == 0

    @pytest.mark.asyncio
    async def test_consecutive_losses_trigger(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test consecutive losses breaker triggers."""
        # Simulate 3 consecutive losses
        for _ in range(3):
            await state.record_trade_result(False)

        result = await breaker.check_trading_allowed()
        assert result.allowed is True  # Can still trade, but reduced position
        assert result.position_ratio == 0.10
        assert BreakerTriggerType.CONSECUTIVE_LOSSES in [
            t.trigger_type for t in result.triggers
        ]
        assert any("Consecutive losses exceeded" in r for r in result.reasons)

    @pytest.mark.asyncio
    async def test_consecutive_losses_below_limit(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test that consecutive losses below limit don't trigger breaker."""
        # Simulate 2 losses (below limit of 3)
        for _ in range(2):
            await state.record_trade_result(False)

        result = await breaker.check_trading_allowed()
        assert result.allowed is True
        assert result.position_ratio == 1.0
        assert len(result.triggers) == 0

    @pytest.mark.asyncio
    async def test_daily_loss_limit_trigger(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test daily loss limit breaker triggers and stops trading."""
        # Simulate daily loss of 30%+ ($60+)
        await state.update_capital(-70.0)

        result = await breaker.check_trading_allowed()
        assert result.allowed is False  # Trading stopped
        assert result.position_ratio == 0.0
        assert BreakerTriggerType.DAILY_LOSS_LIMIT in [
            t.trigger_type for t in result.triggers
        ]
        assert any("Daily loss limit exceeded" in r for r in result.reasons)

    @pytest.mark.asyncio
    async def test_daily_loss_limit_exact_threshold(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test daily loss limit triggers at exactly 30%."""
        # Simulate daily loss of exactly 30% ($60)
        await state.update_capital(-60.0)

        result = await breaker.check_trading_allowed()
        assert result.allowed is False
        assert BreakerTriggerType.DAILY_LOSS_LIMIT in [
            t.trigger_type for t in result.triggers
        ]

    @pytest.mark.asyncio
    async def test_daily_loss_limit_below_threshold(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test daily loss limit doesn't trigger below 30%."""
        # Simulate daily loss of 29% ($58)
        await state.update_capital(-58.0)

        result = await breaker.check_trading_allowed()
        assert result.allowed is True
        assert BreakerTriggerType.DAILY_LOSS_LIMIT not in [
            t.trigger_type for t in result.triggers
        ]

    @pytest.mark.asyncio
    async def test_daily_loss_doesnt_trigger_on_profit(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test daily loss limit doesn't trigger on profit."""
        # Simulate profit
        await state.update_capital(100.0)

        result = await breaker.check_trading_allowed()
        assert result.allowed is True
        assert BreakerTriggerType.DAILY_LOSS_LIMIT not in [
            t.trigger_type for t in result.triggers
        ]

    @pytest.mark.asyncio
    async def test_capital_threshold_trigger(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test capital threshold breaker triggers."""
        # Simulate capital below $100 but not triggering daily loss
        # Start with fresh state (daily_pnl = 0), then reduce capital
        # $80 < $100 threshold, but loss is $120 which is 60% - too much
        # Instead reduce capital by exactly enough to get below threshold
        # but keep daily loss below 30%
        # Use initial_capital of 200, to get to $99, lose $101 (50.5% daily loss is too much)
        # We need to use a different approach - use initial capital that's smaller
        pass  # Skip - see test_capital_threshold_trigger_isolated below

    @pytest.mark.asyncio
    async def test_capital_threshold_trigger_isolated(self) -> None:
        """Test capital threshold breaker triggers (isolated test)."""
        # Create state with smaller initial capital to avoid triggering daily loss
        state = ThreadSafeState(initial_capital=200.0)
        breaker = CircuitBreaker(
            state,
            consecutive_losses_limit=3,
            reduce_ratio_after_losses=0.10,
            daily_loss_limit=0.99,  # Set high to avoid triggering daily loss
            capital_threshold=100.0,
            reduce_ratio_low_capital=0.10,
            initial_capital=200.0,
            disable_circuit_breaker=False,
        )

        # Simulate capital below $100
        await state.update_capital(-120.0)

        result = await breaker.check_trading_allowed()
        assert result.allowed is True  # Can still trade, but reduced position
        assert result.position_ratio == 0.10
        assert BreakerTriggerType.CAPITAL_THRESHOLD in [
            t.trigger_type for t in result.triggers
        ]
        assert any("Capital below threshold" in r for r in result.reasons)

    @pytest.mark.asyncio
    async def test_capital_threshold_above_limit(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test capital threshold doesn't trigger above $100."""
        # Capital at $150 (above $100 threshold)
        await state.update_capital(-50.0)

        result = await breaker.check_trading_allowed()
        assert result.allowed is True
        assert result.position_ratio == 1.0
        assert BreakerTriggerType.CAPITAL_THRESHOLD not in [
            t.trigger_type for t in result.triggers
        ]

    @pytest.mark.asyncio
    async def test_multiple_breakers_trigger(self) -> None:
        """Test multiple breakers trigger together."""
        # Create state with high daily loss limit to avoid triggering it
        state = ThreadSafeState(initial_capital=200.0)
        breaker = CircuitBreaker(
            state,
            consecutive_losses_limit=3,
            reduce_ratio_after_losses=0.10,
            daily_loss_limit=0.99,  # Set high to avoid triggering daily loss
            capital_threshold=100.0,
            reduce_ratio_low_capital=0.10,
            initial_capital=200.0,
            disable_circuit_breaker=False,
        )

        # Simulate consecutive losses
        for _ in range(3):
            await state.record_trade_result(False)
        # Simulate capital below threshold
        await state.update_capital(-120.0)

        result = await breaker.check_trading_allowed()
        assert result.allowed is True  # Can still trade, but reduced position
        assert result.position_ratio == 0.10  # Minimum ratio
        assert len(result.triggers) == 2
        trigger_types = [t.trigger_type for t in result.triggers]
        assert BreakerTriggerType.CONSECUTIVE_LOSSES in trigger_types
        assert BreakerTriggerType.CAPITAL_THRESHOLD in trigger_types

    @pytest.mark.asyncio
    async def test_daily_loss_takes_priority(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test that daily loss takes priority over other breakers."""
        # Simulate consecutive losses AND daily loss
        for _ in range(3):
            await state.record_trade_result(False)
        await state.update_capital(-70.0)  # 35% loss

        result = await breaker.check_trading_allowed()
        assert result.allowed is False
        assert result.position_ratio == 0.0
        # Only daily loss should be in triggers (early return)
        assert len(result.triggers) == 1
        assert result.triggers[0].trigger_type == BreakerTriggerType.DAILY_LOSS_LIMIT

    @pytest.mark.asyncio
    async def test_record_loss(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test recording a loss."""
        await breaker.record_loss(50.0)
        snapshot = await state.get_state()
        assert snapshot.current_capital == 150.0
        assert snapshot.consecutive_losses == 1

    @pytest.mark.asyncio
    async def test_record_loss_multiple(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test recording multiple losses."""
        await breaker.record_loss(30.0)
        await breaker.record_loss(20.0)
        snapshot = await state.get_state()
        assert snapshot.current_capital == 150.0  # 200 - 30 - 20
        assert snapshot.consecutive_losses == 2

    @pytest.mark.asyncio
    async def test_record_loss_negative_amount(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test recording loss with negative amount (should still work)."""
        await breaker.record_loss(-30.0)  # Negative should be treated as loss
        snapshot = await state.get_state()
        assert snapshot.current_capital == 170.0
        assert snapshot.consecutive_losses == 1

    @pytest.mark.asyncio
    async def test_reset_clears_triggers(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test reset clears triggered breaker records."""
        # Trigger breaker
        for _ in range(3):
            await state.record_trade_result(False)
        await breaker.check_trading_allowed()
        assert len(breaker.get_triggered_breakers()) == 1

        # Reset
        breaker.reset()
        assert len(breaker.get_triggered_breakers()) == 0

    @pytest.mark.asyncio
    async def test_reset_does_not_reset_state(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test reset doesn't reset ThreadSafeState."""
        # Trigger breaker
        for _ in range(3):
            await state.record_trade_result(False)
        await breaker.check_trading_allowed()

        # Reset breaker
        breaker.reset()

        # State should still have consecutive losses
        snapshot = await state.get_state()
        assert snapshot.consecutive_losses == 3

    @pytest.mark.asyncio
    async def test_get_position_ratio(self, breaker: CircuitBreaker) -> None:
        """Test get_position_ratio convenience method."""
        ratio = await breaker.get_position_ratio()
        assert ratio == 1.0

    @pytest.mark.asyncio
    async def test_get_position_ratio_reduced(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test get_position_ratio returns reduced ratio."""
        # Trigger consecutive losses
        for _ in range(3):
            await state.record_trade_result(False)

        ratio = await breaker.get_position_ratio()
        assert ratio == 0.10

    @pytest.mark.asyncio
    async def test_get_triggered_breakers_returns_copy(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test get_triggered_breakers returns a copy."""
        # Trigger breaker
        for _ in range(3):
            await state.record_trade_result(False)
        await breaker.check_trading_allowed()

        triggers1 = breaker.get_triggered_breakers()
        triggers2 = breaker.get_triggered_breakers()
        assert triggers1 is not triggers2  # Different list objects
        assert len(triggers1) == len(triggers2)

    @pytest.mark.asyncio
    async def test_reduced_mode_set_on_trigger(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test that reduced mode is set when breaker triggers."""
        # Verify initial state
        snapshot = await state.get_state()
        assert snapshot.reduced_mode is False

        # Trigger consecutive losses
        for _ in range(3):
            await state.record_trade_result(False)
        await breaker.check_trading_allowed()

        # Verify reduced mode is set
        snapshot = await state.get_state()
        assert snapshot.reduced_mode is True

    @pytest.mark.asyncio
    async def test_trading_disabled_on_daily_loss(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """Test that trading is disabled when daily loss limit triggers."""
        # Simulate daily loss
        await state.update_capital(-70.0)
        await breaker.check_trading_allowed()

        # Verify trading is disabled
        snapshot = await state.get_state()
        assert snapshot.trading_enabled is False


class TestCircuitBreakerWithDefaults:
    """Test CircuitBreaker with default configuration."""

    @pytest.fixture
    def state(self) -> ThreadSafeState:
        """Create a test state manager."""
        return ThreadSafeState(initial_capital=200.0)

    @pytest.fixture
    def breaker(self, state: ThreadSafeState) -> CircuitBreaker:
        """Create a circuit breaker with default config."""
        return CircuitBreaker(state)

    @pytest.mark.asyncio
    async def test_uses_config_defaults(self, breaker: CircuitBreaker) -> None:
        """Test that breaker uses configuration defaults."""
        assert breaker._consecutive_losses_limit == 3
        assert breaker._reduce_ratio_after_losses == 0.10
        assert breaker._daily_loss_limit == 0.30
        assert breaker._capital_threshold == 100.0
        assert breaker._reduce_ratio_low_capital == 0.10
        assert breaker._initial_capital == 200.0


class TestCircuitBreakerResult:
    """Test CircuitBreakerResult dataclass."""

    def test_default_values(self) -> None:
        """Test default values for CircuitBreakerResult."""
        result = CircuitBreakerResult(allowed=True)
        assert result.allowed is True
        assert result.position_ratio == 1.0
        assert result.reasons == []
        assert result.triggers == []

    def test_custom_values(self) -> None:
        """Test custom values for CircuitBreakerResult."""
        from src.core.circuit_breaker import BreakerTrigger

        trigger = BreakerTrigger(
            trigger_type=BreakerTriggerType.CONSECUTIVE_LOSSES,
            details="Test trigger",
        )
        result = CircuitBreakerResult(
            allowed=False,
            position_ratio=0.10,
            reasons=["Test reason"],
            triggers=[trigger],
        )
        assert result.allowed is False
        assert result.position_ratio == 0.10
        assert result.reasons == ["Test reason"]
        assert len(result.triggers) == 1


class TestBreakerTrigger:
    """Test BreakerTrigger dataclass."""

    def test_default_timestamp(self) -> None:
        """Test that timestamp is auto-generated."""
        from datetime import datetime

        trigger = BreakerTrigger(trigger_type=BreakerTriggerType.CONSECUTIVE_LOSSES)
        assert isinstance(trigger.timestamp, datetime)

    def test_custom_details(self) -> None:
        """Test custom details."""
        trigger = BreakerTrigger(
            trigger_type=BreakerTriggerType.DAILY_LOSS_LIMIT,
            details="Daily loss: 35%",
        )
        assert trigger.details == "Daily loss: 35%"


class TestBreakerTriggerType:
    """Test BreakerTriggerType enum."""

    def test_enum_values(self) -> None:
        """Test enum values."""
        assert BreakerTriggerType.CONSECUTIVE_LOSSES.value == "consecutive_losses"
        assert BreakerTriggerType.DAILY_LOSS_LIMIT.value == "daily_loss_limit"
        assert BreakerTriggerType.CAPITAL_THRESHOLD.value == "capital_threshold"

    def test_enum_is_string(self) -> None:
        """Test that enum values are strings."""
        assert isinstance(BreakerTriggerType.CONSECUTIVE_LOSSES, str)
