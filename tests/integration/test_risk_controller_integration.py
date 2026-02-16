"""Integration tests for RiskController with CircuitBreaker integration.

These tests verify the end-to-end integration of RiskController,
CircuitBreaker, and ThreadSafeState components.

Run with: pytest tests/integration/ -v -m integration

To skip these tests during normal development:
    pytest tests/ -v -m "not integration"

Note: These tests do not require external API calls, but test the
full integration of risk control components.
"""

from __future__ import annotations

import pytest

from src.core.circuit_breaker import (
    BreakerTriggerType,
    CircuitBreaker,
    CircuitBreakerResult,
)
from src.core.state import StateSnapshot, ThreadSafeState
from src.models.market import Market, MarketCategory
from src.models.prediction import PredictionResult, Recommendation
from src.trading.risk_control import (
    RiskCheckFailure,
    RiskCheckResult,
    RiskController,
)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def state() -> ThreadSafeState:
    """Create a fresh ThreadSafeState instance for testing.

    Returns:
        ThreadSafeState: Fresh state instance with default capital.
    """
    return ThreadSafeState(initial_capital=200.0)


@pytest.fixture
def circuit_breaker(state: ThreadSafeState) -> CircuitBreaker:
    """Create a CircuitBreaker instance with default settings.

    Args:
        state: ThreadSafeState fixture

    Returns:
        CircuitBreaker: Circuit breaker instance
    """
    return CircuitBreaker(
        state,
        consecutive_losses_limit=3,
        reduce_ratio_after_losses=0.10,
        daily_loss_limit=0.30,
        capital_threshold=100.0,
        reduce_ratio_low_capital=0.10,
        initial_capital=200.0,
    )


@pytest.fixture
def risk_controller(
    state: ThreadSafeState,
    circuit_breaker: CircuitBreaker,
) -> RiskController:
    """Create a RiskController instance with default settings.

    Args:
        state: ThreadSafeState fixture
        circuit_breaker: CircuitBreaker fixture

    Returns:
        RiskController: Risk controller instance
    """
    return RiskController(
        state,
        circuit_breaker,
        min_confidence=0.75,
        min_edge=0.10,
        max_position_per_market=0.40,
        max_open_markets=3,
        max_single_ratio=0.20,
        min_bet=5.0,
    )


@pytest.fixture
def market() -> Market:
    """Create a sample Market instance for testing.

    Returns:
        Market: Sample market with default test values
    """
    return Market(
        id="test-market-001",
        title="Will Bitcoin reach $100k by end of 2026?",
        description="A prediction market about Bitcoin price",
        category=MarketCategory.CRYPTO,
        yes_price=0.55,
        no_price=0.45,
        liquidity=50000.0,
    )


@pytest.fixture
def valid_prediction() -> PredictionResult:
    """Create a valid PredictionResult that should pass risk checks.

    Returns:
        PredictionResult: Prediction with high confidence and edge
    """
    return PredictionResult(
        predicted_probability=0.75,
        confidence=0.85,
        reasoning="Strong technical indicators support this prediction",
        key_assumptions=["Market trend continues", "No major regulatory changes"],
        recommendation=Recommendation.BUY_YES,
        edge=0.20,
    )


@pytest.fixture
def low_confidence_prediction() -> PredictionResult:
    """Create a PredictionResult with low confidence.

    Returns:
        PredictionResult: Prediction with confidence below threshold
    """
    return PredictionResult(
        predicted_probability=0.55,
        confidence=0.60,  # Below 0.75 threshold
        reasoning="Uncertain market conditions",
        key_assumptions=["Market volatility expected"],
        recommendation=Recommendation.BUY_YES,
        edge=0.15,
    )


@pytest.fixture
def low_edge_prediction() -> PredictionResult:
    """Create a PredictionResult with low edge.

    Returns:
        PredictionResult: Prediction with edge below threshold
    """
    return PredictionResult(
        predicted_probability=0.58,
        confidence=0.80,
        reasoning="Small edge detected",
        key_assumptions=["Limited upside potential"],
        recommendation=Recommendation.BUY_YES,
        edge=0.05,  # Below 0.10 threshold
    )


# ============================================================================
# P1 Tests: Core Integration Scenarios
# ============================================================================


class TestRiskControllerCircuitBreakerIntegration:
    """Integration tests for RiskController with CircuitBreaker."""

    @pytest.mark.asyncio
    async def test_risk_check_with_circuit_breaker_integration(
        self,
        risk_controller: RiskController,
        valid_prediction: PredictionResult,
        market: Market,
    ) -> None:
        """Test risk check integrates correctly with CircuitBreaker.

        Verifies that:
        - CircuitBreaker is consulted during risk check
        - Position ratio from CircuitBreaker is respected
        - Full integration chain works end-to-end
        """
        result = await risk_controller.check_trade_allowed(valid_prediction, market)

        assert isinstance(result, RiskCheckResult)
        assert result.allowed is True
        assert result.position_ratio == 1.0  # No restrictions initially
        assert result.trade_amount > 0
        assert len(result.reasons) == 0
        assert len(result.failures) == 0

    @pytest.mark.asyncio
    async def test_trade_allowed_happy_path(
        self,
        risk_controller: RiskController,
        valid_prediction: PredictionResult,
        market: Market,
    ) -> None:
        """Test normal trade passes all risk checks.

        A trade with high confidence (85%) and high edge (20%) should
        pass all checks and be allowed.
        """
        result = await risk_controller.check_trade_allowed(valid_prediction, market)

        # Verify trade is allowed
        assert result.allowed is True

        # Verify calculated trade amount
        # With capital=200, max_single_ratio=0.20, position_ratio=1.0
        # Expected: 200 * 0.20 * 1.0 = 40.0
        assert result.trade_amount == pytest.approx(40.0, rel=0.01)

        # Verify no failure reasons
        assert len(result.failures) == 0
        assert len(result.reasons) == 0

    @pytest.mark.asyncio
    async def test_trade_blocked_by_circuit_breaker(
        self,
        state: ThreadSafeState,
        market: Market,
        valid_prediction: PredictionResult,
    ) -> None:
        """Test trade blocked when CircuitBreaker is triggered.

        When daily loss limit is exceeded, CircuitBreaker should
        block all trading.
        """
        circuit_breaker = CircuitBreaker(
            state,
            daily_loss_limit=0.30,
            initial_capital=200.0,
        )
        risk_controller = RiskController(state, circuit_breaker)

        # Simulate exceeding daily loss limit (70 USD loss = 35% of 200)
        await state.update_capital(-70.0)

        result = await risk_controller.check_trade_allowed(valid_prediction, market)

        # Trade should be blocked
        assert result.allowed is False
        assert RiskCheckFailure.CIRCUIT_BREAKER in result.failures
        assert result.position_ratio == 0.0
        assert result.trade_amount == 0.0

        # Check reason mentions daily loss
        assert any("daily loss" in reason.lower() for reason in result.reasons)

    @pytest.mark.asyncio
    async def test_trade_blocked_by_low_confidence(
        self,
        risk_controller: RiskController,
        low_confidence_prediction: PredictionResult,
        market: Market,
    ) -> None:
        """Test trade blocked when confidence is below threshold.

        A prediction with confidence of 60% should be blocked
        when min_confidence is 75%.
        """
        result = await risk_controller.check_trade_allowed(
            low_confidence_prediction, market
        )

        assert result.allowed is False
        assert RiskCheckFailure.LOW_CONFIDENCE in result.failures
        assert any("confidence" in reason.lower() for reason in result.reasons)
        assert result.trade_amount == 0.0

    @pytest.mark.asyncio
    async def test_trade_blocked_by_low_edge(
        self,
        risk_controller: RiskController,
        low_edge_prediction: PredictionResult,
        market: Market,
    ) -> None:
        """Test trade blocked when edge is below threshold.

        A prediction with edge of 5% should be blocked
        when min_edge is 10%.
        """
        result = await risk_controller.check_trade_allowed(low_edge_prediction, market)

        assert result.allowed is False
        assert RiskCheckFailure.LOW_EDGE in result.failures
        assert any("edge" in reason.lower() for reason in result.reasons)
        assert result.trade_amount == 0.0

    @pytest.mark.asyncio
    async def test_trade_blocked_by_max_positions(
        self,
        state: ThreadSafeState,
        circuit_breaker: CircuitBreaker,
        valid_prediction: PredictionResult,
        market: Market,
    ) -> None:
        """Test trade blocked when max open positions limit reached.

        When open_positions_count >= max_open_markets (3),
        new positions should be blocked.
        """
        risk_controller = RiskController(
            state,
            circuit_breaker,
            max_open_markets=3,
        )

        # Simulate 3 open positions
        for _ in range(3):
            await state.increment_open_positions()

        result = await risk_controller.check_trade_allowed(valid_prediction, market)

        assert result.allowed is False
        assert RiskCheckFailure.MAX_OPEN_MARKETS in result.failures
        assert any("max open" in reason.lower() for reason in result.reasons)

    @pytest.mark.asyncio
    async def test_position_ratio_from_circuit_breaker(
        self,
        state: ThreadSafeState,
        market: Market,
        valid_prediction: PredictionResult,
    ) -> None:
        """Test that CircuitBreaker affects position ratio.

        When consecutive losses trigger CircuitBreaker,
        position ratio should be reduced.
        """
        circuit_breaker = CircuitBreaker(
            state,
            consecutive_losses_limit=3,
            reduce_ratio_after_losses=0.10,  # 10% of normal position
            initial_capital=200.0,
        )
        risk_controller = RiskController(
            state,
            circuit_breaker,
            max_single_ratio=0.50,  # Higher ratio so trade amount stays above min_bet
            min_bet=5.0,
        )

        # Simulate 3 consecutive losses
        for _ in range(3):
            await state.record_trade_result(is_win=False)

        result = await risk_controller.check_trade_allowed(valid_prediction, market)

        # Trade should still be allowed (not blocked by consecutive losses)
        assert result.allowed is True

        # But position ratio should be reduced to 10%
        assert result.position_ratio == pytest.approx(0.10, rel=0.01)

        # Trade amount should be reduced accordingly
        # 200 * 0.50 * 0.10 = 10.0 (which is above min_bet of 5.0)
        assert result.trade_amount == pytest.approx(10.0, rel=0.01)


# ============================================================================
# Additional Integration Tests
# ============================================================================


class TestRiskControllerEdgeCases:
    """Edge case tests for RiskController integration."""

    @pytest.mark.asyncio
    async def test_trade_blocked_by_no_trade_recommendation(
        self,
        risk_controller: RiskController,
        market: Market,
    ) -> None:
        """Test trade blocked when LLM recommends NO_TRADE."""
        no_trade_prediction = PredictionResult(
            predicted_probability=0.52,
            confidence=0.80,
            reasoning="Edge too small to trade",
            key_assumptions=[],
            recommendation=Recommendation.NO_TRADE,
            edge=0.02,
        )

        result = await risk_controller.check_trade_allowed(no_trade_prediction, market)

        assert result.allowed is False
        assert RiskCheckFailure.NO_TRADE_RECOMMENDATION in result.failures

    @pytest.mark.asyncio
    async def test_trade_blocked_by_insufficient_capital(
        self,
        state: ThreadSafeState,
        circuit_breaker: CircuitBreaker,
        valid_prediction: PredictionResult,
        market: Market,
    ) -> None:
        """Test trade blocked when capital is too low."""
        # Set very low capital
        low_capital_state = ThreadSafeState(initial_capital=3.0)
        low_capital_breaker = CircuitBreaker(low_capital_state)

        risk_controller = RiskController(
            low_capital_state,
            low_capital_breaker,
            min_bet=5.0,
            max_single_ratio=0.20,
        )

        result = await risk_controller.check_trade_allowed(valid_prediction, market)

        # Trade amount would be 3.0 * 0.20 = 0.6, which is below min_bet
        assert result.allowed is False
        assert RiskCheckFailure.TRADE_TOO_SMALL in result.failures

    @pytest.mark.asyncio
    async def test_trade_blocked_by_position_per_market_limit(
        self,
        risk_controller: RiskController,
        valid_prediction: PredictionResult,
        market: Market,
    ) -> None:
        """Test trade blocked when position limit per market reached."""
        # Set up existing position at 40% of capital
        risk_controller.update_market_position(market.id, 80.0)  # 40% of 200

        result = await risk_controller.check_trade_allowed(
            valid_prediction,
            market,
            current_position_value=80.0,
        )

        assert result.allowed is False
        assert RiskCheckFailure.MAX_POSITION_PER_MARKET in result.failures

    @pytest.mark.asyncio
    async def test_multiple_breaker_triggers(
        self,
        state: ThreadSafeState,
        valid_prediction: PredictionResult,
        market: Market,
    ) -> None:
        """Test multiple breaker triggers are tracked.

        Note: Daily loss limit is checked first in CircuitBreaker and
        returns early if triggered. To test multiple triggers, we need
        to trigger both consecutive losses and capital threshold without
        triggering daily loss limit.
        """
        circuit_breaker = CircuitBreaker(
            state,
            consecutive_losses_limit=2,
            capital_threshold=180.0,  # High threshold so it triggers
            daily_loss_limit=0.50,  # Higher limit to avoid daily loss trigger
            initial_capital=200.0,
        )
        risk_controller = RiskController(state, circuit_breaker)

        # Trigger consecutive losses breaker
        await state.record_trade_result(is_win=False)
        await state.record_trade_result(is_win=False)

        # Trigger capital threshold breaker (small loss to stay under daily limit)
        await state.update_capital(
            -25.0
        )  # Capital now 175, daily_pnl = -25 (12.5% of 200)

        breaker_result = await circuit_breaker.check_trading_allowed()

        # Both breakers should be triggered (consecutive losses and capital threshold)
        assert len(breaker_result.triggers) == 2
        trigger_types = {t.trigger_type for t in breaker_result.triggers}
        assert BreakerTriggerType.CONSECUTIVE_LOSSES in trigger_types
        assert BreakerTriggerType.CAPITAL_THRESHOLD in trigger_types

    @pytest.mark.asyncio
    async def test_reduced_mode_flag_set(
        self,
        state: ThreadSafeState,
        valid_prediction: PredictionResult,
        market: Market,
    ) -> None:
        """Test that reduced_mode flag is set when breakers trigger."""
        circuit_breaker = CircuitBreaker(
            state,
            consecutive_losses_limit=2,
            reduce_ratio_after_losses=0.10,
            initial_capital=200.0,
        )
        risk_controller = RiskController(state, circuit_breaker)

        # Trigger consecutive losses
        await state.record_trade_result(is_win=False)
        await state.record_trade_result(is_win=False)

        # Check trade - this should set reduced_mode
        await risk_controller.check_trade_allowed(valid_prediction, market)

        # Verify reduced_mode is set in state
        snapshot = await state.get_state()
        assert snapshot.reduced_mode is True


class TestRiskControllerStateIntegration:
    """Tests for RiskController interaction with ThreadSafeState."""

    @pytest.mark.asyncio
    async def test_trading_disabled_in_state(
        self,
        state: ThreadSafeState,
        valid_prediction: PredictionResult,
        market: Market,
    ) -> None:
        """Test trade blocked when trading is disabled in state."""
        circuit_breaker = CircuitBreaker(state)
        risk_controller = RiskController(state, circuit_breaker)

        # Disable trading
        await state.set_trading_enabled(False)

        result = await risk_controller.check_trade_allowed(valid_prediction, market)

        assert result.allowed is False
        assert RiskCheckFailure.TRADING_DISABLED in result.failures

    @pytest.mark.asyncio
    async def test_position_tracking(
        self,
        risk_controller: RiskController,
    ) -> None:
        """Test market position tracking in risk controller."""
        # Track positions
        risk_controller.update_market_position("market-1", 50.0)
        risk_controller.update_market_position("market-2", 30.0)

        # Verify tracking
        assert risk_controller.get_market_position("market-1") == 50.0
        assert risk_controller.get_market_position("market-2") == 30.0
        assert risk_controller.get_total_position_value() == 80.0

        # Remove position
        risk_controller.remove_market_position("market-1")
        assert risk_controller.get_market_position("market-1") == 0.0
        assert risk_controller.get_total_position_value() == 30.0

    @pytest.mark.asyncio
    async def test_state_snapshot_reflects_changes(
        self,
        state: ThreadSafeState,
    ) -> None:
        """Test that state snapshots reflect recent changes."""
        # Initial state
        snapshot = await state.get_state()
        assert snapshot.current_capital == 200.0
        assert snapshot.daily_pnl == 0.0
        assert snapshot.consecutive_losses == 0

        # Make changes
        await state.update_capital(-20.0)
        await state.record_trade_result(is_win=False)
        await state.increment_open_positions()

        # Verify snapshot reflects changes
        snapshot = await state.get_state()
        assert snapshot.current_capital == 180.0
        assert snapshot.daily_pnl == -20.0
        assert snapshot.consecutive_losses == 1
        assert snapshot.open_positions_count == 1


class TestCircuitBreakerIntegration:
    """Tests for CircuitBreaker standalone behavior."""

    @pytest.mark.asyncio
    async def test_check_trading_allowed_returns_result(
        self,
        circuit_breaker: CircuitBreaker,
    ) -> None:
        """Test check_trading_allowed returns proper result."""
        result = await circuit_breaker.check_trading_allowed()

        assert isinstance(result, CircuitBreakerResult)
        assert result.allowed is True
        assert result.position_ratio == 1.0
        assert len(result.reasons) == 0
        assert len(result.triggers) == 0

    @pytest.mark.asyncio
    async def test_get_position_ratio_convenience_method(
        self,
        circuit_breaker: CircuitBreaker,
    ) -> None:
        """Test get_position_ratio convenience method."""
        ratio = await circuit_breaker.get_position_ratio()

        assert isinstance(ratio, float)
        assert ratio == 1.0  # No restrictions

    @pytest.mark.asyncio
    async def test_record_loss_updates_state(
        self,
        circuit_breaker: CircuitBreaker,
        state: ThreadSafeState,
    ) -> None:
        """Test record_loss updates state correctly."""
        await circuit_breaker.record_loss(25.0)

        snapshot = await state.get_state()
        assert snapshot.current_capital == 175.0  # 200 - 25
        assert snapshot.daily_pnl == -25.0
        assert snapshot.consecutive_losses == 1

    @pytest.mark.asyncio
    async def test_triggered_breakers_tracking(
        self,
        state: ThreadSafeState,
    ) -> None:
        """Test that triggered breakers are tracked.

        Note: We use a higher daily loss limit to ensure capital threshold
        is triggered instead of daily loss limit (which is checked first).
        """
        circuit_breaker = CircuitBreaker(
            state,
            capital_threshold=150.0,
            daily_loss_limit=0.50,  # Higher limit to avoid daily loss trigger
            initial_capital=200.0,
        )

        # Trigger capital threshold (small loss to stay under daily limit)
        await state.update_capital(
            -55.0
        )  # Capital now 145, daily_pnl = -55 (27.5% of 200)

        await circuit_breaker.check_trading_allowed()

        triggers = circuit_breaker.get_triggered_breakers()
        assert len(triggers) == 1
        assert triggers[0].trigger_type == BreakerTriggerType.CAPITAL_THRESHOLD

        # Reset and verify
        circuit_breaker.reset()
        assert len(circuit_breaker.get_triggered_breakers()) == 0
