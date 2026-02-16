"""Integration tests for CircuitBreaker with real ThreadSafeState.

These tests verify the integration between CircuitBreaker and ThreadSafeState
components, testing the actual state transitions and risk control behavior.

Run with: pytest tests/integration/ -v -m integration

To skip these tests during normal development:
    pytest tests/ -v -m "not integration"

Note: These tests use real ThreadSafeState instances but do not require
external API calls or network access.
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from src.config import settings
from src.core.circuit_breaker import (
    BreakerTrigger,
    BreakerTriggerType,
    CircuitBreaker,
    CircuitBreakerResult,
)
from src.core.state import StateSnapshot, ThreadSafeState

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def fresh_state() -> ThreadSafeState:
    """Create a fresh ThreadSafeState instance for testing.

    Uses a higher initial capital to avoid triggering capital threshold
    breaker during normal test scenarios.

    Returns:
        ThreadSafeState: Fresh state instance with initial capital of 200.0
    """
    return ThreadSafeState(initial_capital=200.0)


@pytest_asyncio.fixture
async def circuit_breaker(fresh_state: ThreadSafeState) -> CircuitBreaker:
    """Create a CircuitBreaker instance with default settings.

    Args:
        fresh_state: Fresh ThreadSafeState fixture

    Returns:
        CircuitBreaker: CircuitBreaker instance connected to the state
    """
    return CircuitBreaker(
        state=fresh_state,
        consecutive_losses_limit=3,
        reduce_ratio_after_losses=0.5,
        daily_loss_limit=0.30,
        capital_threshold=100.0,
        reduce_ratio_low_capital=0.5,
        initial_capital=200.0,
    )


@pytest_asyncio.fixture
async def high_capital_state() -> ThreadSafeState:
    """Create a ThreadSafeState with high capital for capital threshold tests.

    Uses $1000 initial capital so we can test capital threshold without
    triggering daily loss limit.

    Returns:
        ThreadSafeState: Fresh state instance with initial capital of 1000.0
    """
    return ThreadSafeState(initial_capital=1000.0)


@pytest_asyncio.fixture
async def capital_threshold_breaker(
    high_capital_state: ThreadSafeState,
) -> CircuitBreaker:
    """Create a CircuitBreaker for capital threshold tests.

    Uses higher initial capital and high daily loss limit so we can reduce
    capital below threshold without triggering daily loss limit.

    Args:
        high_capital_state: ThreadSafeState with $1000 capital

    Returns:
        CircuitBreaker: CircuitBreaker configured for capital threshold testing
    """
    return CircuitBreaker(
        state=high_capital_state,
        consecutive_losses_limit=3,
        reduce_ratio_after_losses=0.5,
        daily_loss_limit=1.0,  # 100% - effectively disable for capital threshold tests
        capital_threshold=100.0,
        reduce_ratio_low_capital=0.5,
        initial_capital=1000.0,
    )


class TestCircuitBreakerWithRealState:
    """Integration tests for CircuitBreaker with real ThreadSafeState."""

    async def test_circuit_breaker_with_real_state(
        self, circuit_breaker: CircuitBreaker, fresh_state: ThreadSafeState
    ) -> None:
        """Test CircuitBreaker integration with real ThreadSafeState.

        Verifies that:
        - CircuitBreaker can read state from ThreadSafeState
        - Trading is allowed under normal conditions
        - Position ratio is 1.0 when no breakers are triggered
        """
        # Initial state should allow trading
        result = await circuit_breaker.check_trading_allowed()

        assert isinstance(result, CircuitBreakerResult)
        assert result.allowed is True
        assert result.position_ratio == 1.0
        assert len(result.reasons) == 0
        assert len(result.triggers) == 0

        # Verify state snapshot matches expected values
        state_snapshot = await fresh_state.get_state()
        assert state_snapshot.current_capital == 200.0
        assert state_snapshot.daily_pnl == 0.0
        assert state_snapshot.consecutive_losses == 0
        assert state_snapshot.trading_enabled is True

    async def test_state_snapshot_is_immutable(
        self, fresh_state: ThreadSafeState
    ) -> None:
        """Test that StateSnapshot is immutable (frozen)."""
        snapshot = await fresh_state.get_state()

        # StateSnapshot should be frozen
        assert snapshot.model_config.get("frozen") is True

        # Attempting to modify should raise error
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            snapshot.current_capital = 999.0

    async def test_concurrent_state_access(self, fresh_state: ThreadSafeState) -> None:
        """Test that ThreadSafeState handles concurrent access safely.

        This test verifies the asyncio.Lock mechanism works correctly
        when multiple coroutines access state simultaneously.
        """
        import asyncio

        async def update_and_read(amount: float) -> float:
            await fresh_state.update_capital(amount)
            snapshot = await fresh_state.get_state()
            return snapshot.current_capital

        # Run multiple concurrent updates
        results = await asyncio.gather(
            update_and_read(10.0),
            update_and_read(20.0),
            update_and_read(30.0),
        )

        # All operations should complete successfully
        # Final capital should be 200 + 10 + 20 + 30 = 260
        final_snapshot = await fresh_state.get_state()
        assert final_snapshot.current_capital == 260.0


class TestDailyLossDisablesTrading:
    """Integration tests for daily loss limit circuit breaker."""

    async def test_daily_loss_disables_trading_in_state(
        self, circuit_breaker: CircuitBreaker, fresh_state: ThreadSafeState
    ) -> None:
        """Test that exceeding daily loss limit disables trading in state.

        Verifies that:
        - Daily loss triggers the breaker when limit is exceeded
        - Trading is disabled in ThreadSafeState
        - Position ratio is set to 0.0
        - Correct trigger type is recorded
        """
        # Simulate daily loss exceeding 30% of 200 = $60
        await fresh_state.update_capital(-70.0)  # 35% loss

        result = await circuit_breaker.check_trading_allowed()

        assert result.allowed is False
        assert result.position_ratio == 0.0
        assert len(result.reasons) == 1
        assert "Daily loss limit exceeded" in result.reasons[0]

        # Verify correct trigger type
        assert len(result.triggers) == 1
        assert result.triggers[0].trigger_type == BreakerTriggerType.DAILY_LOSS_LIMIT

        # Verify state was updated
        state_snapshot = await fresh_state.get_state()
        assert state_snapshot.trading_enabled is False

    async def test_daily_loss_exact_threshold(
        self, circuit_breaker: CircuitBreaker, fresh_state: ThreadSafeState
    ) -> None:
        """Test daily loss at exact threshold triggers breaker.

        When loss equals exactly the threshold (30%), trading should be disabled.
        """
        # Exactly 30% loss = $60
        await fresh_state.update_capital(-60.0)

        result = await circuit_breaker.check_trading_allowed()

        assert result.allowed is False
        assert result.triggers[0].trigger_type == BreakerTriggerType.DAILY_LOSS_LIMIT

    async def test_daily_loss_below_threshold(
        self, circuit_breaker: CircuitBreaker, fresh_state: ThreadSafeState
    ) -> None:
        """Test daily loss below threshold does not trigger breaker."""
        # 25% loss = $50 (below 30% threshold)
        await fresh_state.update_capital(-50.0)

        result = await circuit_breaker.check_trading_allowed()

        assert result.allowed is True
        assert len(result.triggers) == 0

    async def test_daily_gain_does_not_trigger(
        self, circuit_breaker: CircuitBreaker, fresh_state: ThreadSafeState
    ) -> None:
        """Test that daily gains (positive PnL) never trigger daily loss breaker."""
        # Large gain
        await fresh_state.update_capital(100.0)

        result = await circuit_breaker.check_trading_allowed()

        assert result.allowed is True
        assert len(result.triggers) == 0


class TestConsecutiveLossesTrigger:
    """Integration tests for consecutive losses circuit breaker."""

    async def test_consecutive_losses_triggers_reduced_mode(
        self, circuit_breaker: CircuitBreaker, fresh_state: ThreadSafeState
    ) -> None:
        """Test that consecutive losses trigger reduced mode in state.

        Verifies that:
        - After 3 consecutive losses, position ratio is reduced
        - Reduced mode is activated in ThreadSafeState
        - Correct trigger type is recorded
        """
        # Record 3 consecutive losses (at the limit)
        for _ in range(3):
            await fresh_state.record_trade_result(is_win=False)

        result = await circuit_breaker.check_trading_allowed()

        # Trading should still be allowed but with reduced ratio
        assert result.allowed is True
        assert result.position_ratio == 0.5  # reduce_ratio_after_losses

        # Verify trigger
        assert len(result.triggers) == 1
        assert result.triggers[0].trigger_type == BreakerTriggerType.CONSECUTIVE_LOSSES

        # Verify reduced mode was activated in state
        state_snapshot = await fresh_state.get_state()
        assert state_snapshot.reduced_mode is True

    async def test_consecutive_losses_below_limit(
        self, circuit_breaker: CircuitBreaker, fresh_state: ThreadSafeState
    ) -> None:
        """Test that losses below limit do not trigger reduced mode."""
        # Only 2 losses (below limit of 3)
        for _ in range(2):
            await fresh_state.record_trade_result(is_win=False)

        result = await circuit_breaker.check_trading_allowed()

        assert result.allowed is True
        assert result.position_ratio == 1.0
        assert len(result.triggers) == 0

        # Reduced mode should NOT be activated
        state_snapshot = await fresh_state.get_state()
        assert state_snapshot.reduced_mode is False

    async def test_win_resets_consecutive_losses(
        self, circuit_breaker: CircuitBreaker, fresh_state: ThreadSafeState
    ) -> None:
        """Test that a winning trade resets consecutive loss counter."""
        # Record 2 losses
        await fresh_state.record_trade_result(is_win=False)
        await fresh_state.record_trade_result(is_win=False)

        # Record a win
        await fresh_state.record_trade_result(is_win=True)

        # Verify counter was reset
        state_snapshot = await fresh_state.get_state()
        assert state_snapshot.consecutive_losses == 0

        # Check breaker result
        result = await circuit_breaker.check_trading_allowed()
        assert result.allowed is True
        assert result.position_ratio == 1.0

    async def test_record_loss_updates_state(
        self, circuit_breaker: CircuitBreaker, fresh_state: ThreadSafeState
    ) -> None:
        """Test that record_loss method updates both capital and trade result."""
        initial_snapshot = await fresh_state.get_state()
        initial_capital = initial_snapshot.current_capital

        # Record a loss using circuit breaker method
        await circuit_breaker.record_loss(25.0)

        # Verify capital was reduced
        snapshot = await fresh_state.get_state()
        assert snapshot.current_capital == initial_capital - 25.0
        assert snapshot.consecutive_losses == 1


class TestCapitalThreshold:
    """Integration tests for capital threshold circuit breaker."""

    async def test_capital_threshold_reduces_position_ratio(
        self,
        capital_threshold_breaker: CircuitBreaker,
        high_capital_state: ThreadSafeState,
    ) -> None:
        """Test that low capital triggers reduced position ratio.

        Verifies that:
        - When capital falls below threshold, position ratio is reduced
        - Reduced mode is activated in ThreadSafeState
        - Correct trigger type is recorded

        Note: Uses high initial capital ($1000) to avoid triggering daily loss
        limit while testing capital threshold (reduce by $910 leaves $90, which
        is only 9.1% daily loss, well under the 30% limit).
        """
        # Reduce capital below threshold (100) without triggering daily loss
        # $1000 - $910 = $90 (below threshold of $100)
        # Daily loss = $910 / $1000 = 9.1% (well under 30% limit)
        await high_capital_state.update_capital(-910.0)

        result = await capital_threshold_breaker.check_trading_allowed()

        # Trading should still be allowed but with reduced ratio
        assert result.allowed is True
        assert result.position_ratio == 0.5  # reduce_ratio_low_capital

        # Verify trigger
        assert len(result.triggers) == 1
        assert result.triggers[0].trigger_type == BreakerTriggerType.CAPITAL_THRESHOLD

        # Verify reduced mode was activated
        state_snapshot = await high_capital_state.get_state()
        assert state_snapshot.reduced_mode is True

    async def test_capital_above_threshold(
        self, circuit_breaker: CircuitBreaker, fresh_state: ThreadSafeState
    ) -> None:
        """Test that capital above threshold does not trigger breaker."""
        # Capital is $200 (above threshold of $100)
        result = await circuit_breaker.check_trading_allowed()

        assert result.position_ratio == 1.0
        assert len(result.triggers) == 0

    async def test_capital_at_exact_threshold(
        self,
        capital_threshold_breaker: CircuitBreaker,
        high_capital_state: ThreadSafeState,
    ) -> None:
        """Test capital at exact threshold does not trigger breaker.

        Capital equal to threshold should not trigger (only below triggers).

        Note: Uses high initial capital ($1000) to test exact threshold without
        triggering daily loss limit.
        """
        # Set capital to exactly $100 (threshold)
        # $1000 - $900 = $100 (at threshold)
        # Daily loss = $900 / $1000 = 9% (well under 30% limit)
        await high_capital_state.update_capital(-900.0)

        result = await capital_threshold_breaker.check_trading_allowed()

        # At threshold, breaker should NOT trigger (only below triggers)
        assert result.position_ratio == 1.0
        assert len(result.triggers) == 0


class TestMultipleBreakersTrigger:
    """Integration tests for multiple circuit breakers triggering simultaneously."""

    async def test_multiple_breakers_can_trigger(
        self,
        capital_threshold_breaker: CircuitBreaker,
        high_capital_state: ThreadSafeState,
    ) -> None:
        """Test that multiple breakers can trigger at the same time.

        This test simulates both consecutive losses and low capital
        conditions simultaneously.

        Note: Uses high initial capital ($1000) to avoid triggering daily loss
        limit while testing multiple breakers.
        """
        # Trigger consecutive losses (3+ losses)
        for _ in range(3):
            await high_capital_state.record_trade_result(is_win=False)

        # Trigger low capital (below $100) without triggering daily loss
        # $1000 - $910 = $90 (below threshold of $100)
        # Daily loss = $910 / $1000 = 9.1% (well under 30% limit)
        await high_capital_state.update_capital(-910.0)

        result = await capital_threshold_breaker.check_trading_allowed()

        # Trading should still be allowed (daily loss not triggered)
        assert result.allowed is True

        # Both breakers should trigger
        assert len(result.triggers) == 2
        trigger_types = {t.trigger_type for t in result.triggers}
        assert BreakerTriggerType.CONSECUTIVE_LOSSES in trigger_types
        assert BreakerTriggerType.CAPITAL_THRESHOLD in trigger_types

        # Position ratio should be minimum of both reductions (0.5 * 0.5 = 0.25)
        # Since both reduce to 0.5, min(0.5, 0.5) = 0.5
        assert result.position_ratio == 0.5

        # Both reasons should be present
        assert len(result.reasons) == 2

    async def test_daily_loss_takes_precedence(
        self, circuit_breaker: CircuitBreaker, fresh_state: ThreadSafeState
    ) -> None:
        """Test that daily loss breaker takes precedence over others.

        When daily loss limit is exceeded, trading should be disabled
        regardless of other breaker states.
        """
        # Trigger all three conditions
        for _ in range(3):
            await fresh_state.record_trade_result(is_win=False)
        await fresh_state.update_capital(-80.0)  # 40% daily loss, capital at $120

        result = await circuit_breaker.check_trading_allowed()

        # Daily loss should take precedence and disable trading
        assert result.allowed is False
        assert result.position_ratio == 0.0

        # Only daily loss trigger should be returned (early exit)
        assert len(result.triggers) == 1
        assert result.triggers[0].trigger_type == BreakerTriggerType.DAILY_LOSS_LIMIT

    async def test_triggered_breakers_are_stored(
        self, circuit_breaker: CircuitBreaker, fresh_state: ThreadSafeState
    ) -> None:
        """Test that triggered breakers are stored and can be retrieved."""
        # Trigger consecutive losses
        for _ in range(3):
            await fresh_state.record_trade_result(is_win=False)

        await circuit_breaker.check_trading_allowed()

        # Verify triggers are stored
        stored_triggers = circuit_breaker.get_triggered_breakers()
        assert len(stored_triggers) >= 1
        assert any(
            t.trigger_type == BreakerTriggerType.CONSECUTIVE_LOSSES
            for t in stored_triggers
        )

    async def test_reset_clears_triggered_breakers(
        self, circuit_breaker: CircuitBreaker, fresh_state: ThreadSafeState
    ) -> None:
        """Test that reset() clears stored triggers but not state."""
        # Trigger a breaker
        for _ in range(3):
            await fresh_state.record_trade_result(is_win=False)
        await circuit_breaker.check_trading_allowed()

        # Reset circuit breaker
        circuit_breaker.reset()

        # Triggers should be cleared
        stored_triggers = circuit_breaker.get_triggered_breakers()
        assert len(stored_triggers) == 0

        # But state should NOT be reset
        state_snapshot = await fresh_state.get_state()
        assert state_snapshot.consecutive_losses == 3


class TestStatePersistence:
    """Integration tests for state persistence with circuit breaker."""

    async def test_state_can_be_persisted(self, fresh_state: ThreadSafeState) -> None:
        """Test that state can be persisted to database.

        Note: This test uses an in-memory database via the test configuration.
        """
        # Modify state
        await fresh_state.update_capital(50.0)
        await fresh_state.record_trade_result(is_win=False)
        await fresh_state.set_reduced_mode(True)

        # Persist
        await fresh_state.persist()

        # Verify persistence succeeded (no exception)
        # The actual persistence is tested in state integration tests

    async def test_get_position_ratio_convenience_method(
        self, circuit_breaker: CircuitBreaker, fresh_state: ThreadSafeState
    ) -> None:
        """Test get_position_ratio convenience method."""
        # Normal conditions
        ratio = await circuit_breaker.get_position_ratio()
        assert ratio == 1.0

        # Trigger consecutive losses
        for _ in range(3):
            await fresh_state.record_trade_result(is_win=False)

        ratio = await circuit_breaker.get_position_ratio()
        assert ratio == 0.5


class TestCircuitBreakerResultDataclass:
    """Tests for CircuitBreakerResult dataclass behavior."""

    def test_result_default_values(self) -> None:
        """Test CircuitBreakerResult has correct defaults."""
        result = CircuitBreakerResult(allowed=True)

        assert result.allowed is True
        assert result.position_ratio == 1.0
        assert result.reasons == []
        assert result.triggers == []

    def test_result_can_be_modified(self) -> None:
        """Test CircuitBreakerResult is mutable (not frozen)."""
        result = CircuitBreakerResult(allowed=True)

        # Should be able to modify
        result.reasons.append("Test reason")
        result.position_ratio = 0.5

        assert len(result.reasons) == 1
        assert result.position_ratio == 0.5


class TestBreakerTriggerDataclass:
    """Tests for BreakerTrigger dataclass behavior."""

    def test_trigger_timestamp_auto_generated(self) -> None:
        """Test BreakerTrigger auto-generates timestamp."""
        from datetime import datetime

        trigger = BreakerTrigger(trigger_type=BreakerTriggerType.CONSECUTIVE_LOSSES)

        assert trigger.timestamp is not None
        assert isinstance(trigger.timestamp, datetime)

    def test_trigger_with_custom_details(self) -> None:
        """Test BreakerTrigger with custom details."""
        trigger = BreakerTrigger(
            trigger_type=BreakerTriggerType.DAILY_LOSS_LIMIT,
            details="Daily loss: 35%",
        )

        assert trigger.details == "Daily loss: 35%"
