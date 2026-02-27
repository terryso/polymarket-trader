"""Tests for RiskController - Story 4.4: Pre-trade Risk Check.

This module tests the RiskController class which performs comprehensive
risk checks before each trade is executed.

Test Categories:
    1. Confidence check: LLM confidence >= MIN_CONFIDENCE (75%)
    2. Edge check: Edge >= MIN_EDGE (10%)
    3. No-trade recommendation check
    4. Position limit check: Single market <= 40%
    5. Open positions check: Count < MAX_OPEN_MARKETS (3)
    6. Trade size check: Within capital limits
    7. Circuit breaker integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.trading.risk_control import (
    RiskCheckFailure,
    RiskCheckResult,
    RiskController,
)
from src.models.prediction import PredictionResult, Recommendation
from src.models.market import Market, MarketCategory


# Helper function to create test fixtures
def create_prediction(
    confidence: float = 0.85,
    edge: float = 0.15,
    recommendation: Recommendation = Recommendation.BUY_YES,
) -> PredictionResult:
    """Create a PredictionResult for testing."""
    return PredictionResult(
        predicted_probability=0.80,
        confidence=confidence,
        reasoning="Test reasoning",
        key_assumptions=["Test assumption"],
        recommendation=recommendation,
        edge=edge,
    )


def create_market(
    market_id: str = "test-market-001",
    yes_price: float = 0.65,
) -> Market:
    """Create a Market for testing."""
    return Market(
        id=market_id,
        title="Will X happen by 2026?",
        description="A test prediction market",
        category=MarketCategory.POLITICS,
        yes_price=yes_price,
        no_price=1 - yes_price,
        liquidity=50000.0,
    )


def create_mock_state(
    current_capital: float = 200.0,
    trading_enabled: bool = True,
    open_positions_count: int = 0,
    reduced_mode: bool = False,
) -> MagicMock:
    """Create a mock ThreadSafeState."""
    state = MagicMock()
    state.get_state = AsyncMock()
    state.get_state.return_value = MagicMock(
        current_capital=current_capital,
        daily_pnl=0.0,
        consecutive_losses=0,
        open_positions_count=open_positions_count,
        trading_enabled=trading_enabled,
        reduced_mode=reduced_mode,
    )
    return state


def create_mock_circuit_breaker(
    allowed: bool = True,
    position_ratio: float = 1.0,
    reasons: list = None,
) -> MagicMock:
    """Create a mock CircuitBreaker."""
    breaker = MagicMock()
    breaker.check_trading_allowed = AsyncMock()
    breaker.check_trading_allowed.return_value = MagicMock(
        allowed=allowed,
        position_ratio=position_ratio,
        reasons=reasons or [],
        triggers=[],
    )
    return breaker


class TestRiskCheckResult:
    """Tests for RiskCheckResult dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        result = RiskCheckResult(allowed=True)
        assert result.allowed is True
        assert result.position_ratio == 1.0
        assert result.trade_amount == 0.0
        assert result.reasons == []
        assert result.failures == []

    def test_with_values(self):
        """Test with custom values."""
        result = RiskCheckResult(
            allowed=False,
            position_ratio=0.5,
            trade_amount=20.0,
            reasons=["Test reason"],
            failures=[RiskCheckFailure.LOW_CONFIDENCE],
        )
        assert result.allowed is False
        assert result.position_ratio == 0.5
        assert result.trade_amount == 20.0
        assert result.reasons == ["Test reason"]
        assert result.failures == [RiskCheckFailure.LOW_CONFIDENCE]


class TestRiskControllerInit:
    """Tests for RiskController initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default config values."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker()

        controller = RiskController(mock_state, mock_breaker)

        # Default values from config
        assert controller._min_confidence == 0.75
        assert controller._min_edge == 0.10
        assert controller._max_position_per_market == 0.40
        assert controller._max_open_markets == 3
        assert controller._max_single_ratio == 0.20
        assert controller._min_bet == 1.0

    def test_init_with_overrides(self):
        """Test initialization with custom override values."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker()

        controller = RiskController(
            mock_state,
            mock_breaker,
            min_confidence=0.80,
            min_edge=0.15,
            max_position_per_market=0.30,
            max_open_markets=5,
            max_single_ratio=0.15,
            min_bet=10.0,
        )

        assert controller._min_confidence == 0.80
        assert controller._min_edge == 0.15
        assert controller._max_position_per_market == 0.30
        assert controller._max_open_markets == 5
        assert controller._max_single_ratio == 0.15
        assert controller._min_bet == 10.0


class TestConfidenceCheck:
    """Tests for confidence threshold check."""

    @pytest.mark.asyncio
    async def test_confidence_below_threshold(self):
        """Test that low confidence fails the check."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker, min_confidence=0.75)

        prediction = create_prediction(confidence=0.65)  # Below 0.75
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        assert result.allowed is False
        assert RiskCheckFailure.LOW_CONFIDENCE in result.failures
        assert "Confidence too low" in result.reasons[0]

    @pytest.mark.asyncio
    async def test_confidence_at_threshold(self):
        """Test that confidence at threshold passes."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker, min_confidence=0.75)

        prediction = create_prediction(confidence=0.75)  # Exactly at threshold
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        assert RiskCheckFailure.LOW_CONFIDENCE not in result.failures

    @pytest.mark.asyncio
    async def test_confidence_above_threshold(self):
        """Test that high confidence passes the check."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker, min_confidence=0.75)

        prediction = create_prediction(confidence=0.85)  # Above 0.75
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        assert result.allowed is True
        assert RiskCheckFailure.LOW_CONFIDENCE not in result.failures


class TestEdgeCheck:
    """Tests for edge threshold check."""

    @pytest.mark.asyncio
    async def test_edge_below_threshold(self):
        """Test that low edge fails the check."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker, min_edge=0.10)

        prediction = create_prediction(edge=0.05)  # Below 0.10
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        assert result.allowed is False
        assert RiskCheckFailure.LOW_EDGE in result.failures
        assert "Edge too low" in result.reasons[0]

    @pytest.mark.asyncio
    async def test_edge_at_threshold(self):
        """Test that edge at threshold passes."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker, min_edge=0.10)

        prediction = create_prediction(edge=0.10)  # Exactly at threshold
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        assert RiskCheckFailure.LOW_EDGE not in result.failures

    @pytest.mark.asyncio
    async def test_edge_above_threshold(self):
        """Test that high edge passes the check."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker, min_edge=0.10)

        prediction = create_prediction(edge=0.15)  # Above 0.10
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        assert result.allowed is True
        assert RiskCheckFailure.LOW_EDGE not in result.failures

    @pytest.mark.asyncio
    async def test_edge_none_fails(self):
        """Test that None edge fails the check."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker, min_edge=0.10)

        prediction = create_prediction(edge=None)
        # Recreate to have None edge
        prediction = PredictionResult(
            predicted_probability=0.80,
            confidence=0.85,
            reasoning="Test reasoning",
            key_assumptions=["Test assumption"],
            recommendation=Recommendation.BUY_YES,
            edge=None,
        )
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        assert result.allowed is False
        assert RiskCheckFailure.LOW_EDGE in result.failures


class TestRecommendationCheck:
    """Tests for recommendation check."""

    @pytest.mark.asyncio
    async def test_no_trade_recommendation_fails(self):
        """Test that NO_TRADE recommendation fails."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker)

        prediction = create_prediction(recommendation=Recommendation.NO_TRADE)
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        assert result.allowed is False
        assert RiskCheckFailure.NO_TRADE_RECOMMENDATION in result.failures

    @pytest.mark.asyncio
    async def test_buy_yes_recommendation_passes(self):
        """Test that BUY_YES recommendation passes."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker)

        prediction = create_prediction(recommendation=Recommendation.BUY_YES)
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        assert result.allowed is True
        assert RiskCheckFailure.NO_TRADE_RECOMMENDATION not in result.failures

    @pytest.mark.asyncio
    async def test_buy_no_recommendation_passes(self):
        """Test that BUY_NO recommendation passes."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker)

        prediction = create_prediction(recommendation=Recommendation.BUY_NO)
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        assert result.allowed is True
        assert RiskCheckFailure.NO_TRADE_RECOMMENDATION not in result.failures


class TestPositionLimitCheck:
    """Tests for position limit checks."""

    @pytest.mark.asyncio
    async def test_max_position_per_market_exceeded(self):
        """Test that exceeding max position per market fails."""
        mock_state = create_mock_state(current_capital=200.0)
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(
            mock_state, mock_breaker, max_position_per_market=0.40
        )

        prediction = create_prediction()
        market = create_market()

        # Current position at 45% of capital (> 40% limit)
        current_position = 90.0  # 45% of $200

        result = await controller.check_trade_allowed(
            prediction, market, current_position_value=current_position
        )

        assert result.allowed is False
        assert RiskCheckFailure.MAX_POSITION_PER_MARKET in result.failures

    @pytest.mark.asyncio
    async def test_position_within_limit_passes(self):
        """Test that position within limit passes."""
        mock_state = create_mock_state(current_capital=200.0)
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(
            mock_state, mock_breaker, max_position_per_market=0.40
        )

        prediction = create_prediction()
        market = create_market()

        # Current position at 30% of capital (< 40% limit)
        current_position = 60.0  # 30% of $200

        result = await controller.check_trade_allowed(
            prediction, market, current_position_value=current_position
        )

        assert result.allowed is True
        assert RiskCheckFailure.MAX_POSITION_PER_MARKET not in result.failures

    @pytest.mark.asyncio
    async def test_max_open_markets_exceeded(self):
        """Test that exceeding max open markets fails for new market."""
        mock_state = create_mock_state(open_positions_count=3)
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker, max_open_markets=3)

        prediction = create_prediction()
        market = create_market()  # New market (no existing position)

        result = await controller.check_trade_allowed(prediction, market)

        assert result.allowed is False
        assert RiskCheckFailure.MAX_OPEN_MARKETS in result.failures

    @pytest.mark.asyncio
    async def test_max_open_markets_allows_existing_position(self):
        """Test that existing position can be increased even at max markets."""
        mock_state = create_mock_state(open_positions_count=3)
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker, max_open_markets=3)

        prediction = create_prediction()
        market = create_market()

        # Already have a position in this market
        current_position = 50.0

        result = await controller.check_trade_allowed(
            prediction, market, current_position_value=current_position
        )

        # Should pass because it's an existing position
        assert RiskCheckFailure.MAX_OPEN_MARKETS not in result.failures


class TestTradeSizeCheck:
    """Tests for trade size checks."""

    @pytest.mark.asyncio
    async def test_trade_amount_calculated_correctly(self):
        """Test that trade amount is calculated based on position ratio."""
        mock_state = create_mock_state(current_capital=200.0)
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(
            mock_state, mock_breaker, max_single_ratio=0.20, min_bet=5.0
        )

        prediction = create_prediction()
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        # Trade amount should be: 200 * 0.20 * 1.0 = 40.0
        assert result.allowed is True
        assert result.trade_amount == pytest.approx(40.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_trade_too_small(self):
        """Test that trade below minimum bet fails."""
        # Small capital that results in trade below minimum
        mock_state = create_mock_state(current_capital=20.0)
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(
            mock_state, mock_breaker, max_single_ratio=0.20, min_bet=5.0
        )

        prediction = create_prediction()
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        # Trade amount would be: 20 * 0.20 = 4.0 < 5.0 minimum
        assert result.allowed is False
        assert RiskCheckFailure.TRADE_TOO_SMALL in result.failures

    @pytest.mark.asyncio
    async def test_very_low_capital_scenario(self):
        """Test behavior with very low capital."""
        # With very low capital, even max_single_ratio results in small trades
        mock_state = create_mock_state(current_capital=10.0)
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(
            mock_state, mock_breaker, max_single_ratio=0.20, min_bet=5.0
        )

        prediction = create_prediction()
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        # Trade amount would be: 10 * 0.20 = 2.0 < 5.0 minimum
        assert result.allowed is False
        assert RiskCheckFailure.TRADE_TOO_SMALL in result.failures


class TestCircuitBreakerIntegration:
    """Tests for circuit breaker integration."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_stops_trade(self):
        """Test that circuit breaker can stop trades."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker(
            allowed=False, reasons=["Daily loss limit exceeded"]
        )
        controller = RiskController(mock_state, mock_breaker)

        prediction = create_prediction()
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        assert result.allowed is False
        assert RiskCheckFailure.CIRCUIT_BREAKER in result.failures
        assert "Daily loss limit exceeded" in result.reasons

    @pytest.mark.asyncio
    async def test_circuit_breaker_reduces_position_ratio(self):
        """Test that circuit breaker can reduce position ratio."""
        mock_state = create_mock_state(current_capital=200.0)
        mock_breaker = create_mock_circuit_breaker(allowed=True, position_ratio=0.5)
        controller = RiskController(
            mock_state, mock_breaker, max_single_ratio=0.20, min_bet=5.0
        )

        prediction = create_prediction()
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        assert result.allowed is True
        assert result.position_ratio == 0.5
        # Trade amount should be reduced: 200 * 0.20 * 0.5 = 20.0
        assert result.trade_amount == pytest.approx(20.0, rel=0.01)


class TestTradingDisabled:
    """Tests for trading disabled state."""

    @pytest.mark.asyncio
    async def test_trading_disabled_in_state(self):
        """Test that disabled trading fails the check."""
        mock_state = create_mock_state(trading_enabled=False)
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker)

        prediction = create_prediction()
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        assert RiskCheckFailure.TRADING_DISABLED in result.failures


class TestPositionTracking:
    """Tests for position tracking methods."""

    def test_update_market_position(self):
        """Test updating market position tracking."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker)

        controller.update_market_position("market-1", 50.0)
        assert controller.get_market_position("market-1") == 50.0

        controller.update_market_position("market-1", 75.0)
        assert controller.get_market_position("market-1") == 75.0

    def test_remove_market_position(self):
        """Test removing market position tracking."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker)

        controller.update_market_position("market-1", 50.0)
        assert controller.get_market_position("market-1") == 50.0

        controller.remove_market_position("market-1")
        assert controller.get_market_position("market-1") == 0.0

    def test_get_total_position_value(self):
        """Test getting total position value."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker)

        controller.update_market_position("market-1", 50.0)
        controller.update_market_position("market-2", 30.0)

        assert controller.get_total_position_value() == 80.0

    def test_reset_clears_positions(self):
        """Test that reset clears all position tracking."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker)

        controller.update_market_position("market-1", 50.0)
        controller.update_market_position("market-2", 30.0)

        controller.reset()

        assert controller.get_total_position_value() == 0.0
        assert controller.market_positions == {}

    def test_market_positions_property_returns_copy(self):
        """Test that market_positions property returns a copy."""
        mock_state = create_mock_state()
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(mock_state, mock_breaker)

        controller.update_market_position("market-1", 50.0)
        positions = controller.market_positions
        positions["market-2"] = 100.0  # Modify the copy

        # Original should not be affected
        assert "market-2" not in controller.market_positions


class TestCombinedChecks:
    """Tests for combined risk checks."""

    @pytest.mark.asyncio
    async def test_all_checks_pass(self):
        """Test that all checks passing results in allowed trade."""
        mock_state = create_mock_state(current_capital=200.0, open_positions_count=0)
        mock_breaker = create_mock_circuit_breaker(allowed=True, position_ratio=1.0)
        controller = RiskController(
            mock_state,
            mock_breaker,
            min_confidence=0.75,
            min_edge=0.10,
            max_position_per_market=0.40,
            max_open_markets=3,
            max_single_ratio=0.20,
            min_bet=5.0,
        )

        # Good prediction: high confidence, good edge, BUY_YES
        prediction = create_prediction(confidence=0.85, edge=0.15)
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        assert result.allowed is True
        assert result.trade_amount == pytest.approx(40.0, rel=0.01)
        assert result.position_ratio == 1.0
        assert result.failures == []

    @pytest.mark.asyncio
    async def test_multiple_failures(self):
        """Test that multiple failures are all reported."""
        mock_state = create_mock_state(open_positions_count=3)
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(
            mock_state,
            mock_breaker,
            min_confidence=0.75,
            min_edge=0.10,
            max_open_markets=3,
        )

        # Bad prediction: low confidence, low edge, NO_TRADE
        prediction = create_prediction(
            confidence=0.50,  # Low
            edge=0.02,  # Low
            recommendation=Recommendation.NO_TRADE,
        )
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        assert result.allowed is False
        # Should have all three failures reported
        assert RiskCheckFailure.LOW_CONFIDENCE in result.failures
        assert RiskCheckFailure.LOW_EDGE in result.failures
        assert RiskCheckFailure.NO_TRADE_RECOMMENDATION in result.failures
        # MAX_OPEN_MARKETS should NOT be checked because earlier checks failed
        assert RiskCheckFailure.MAX_OPEN_MARKETS not in result.failures


class TestInsufficientCapital:
    """Tests for insufficient capital check."""

    @pytest.mark.asyncio
    async def test_insufficient_capital_when_trade_exceeds_capital(self):
        """Test that trade amount exceeding capital fails."""
        # Set up a scenario where max_single_ratio results in trade > capital
        # This is an edge case that should rarely happen in practice
        mock_state = create_mock_state(current_capital=5.0)  # Very low capital
        mock_breaker = create_mock_circuit_breaker()
        controller = RiskController(
            mock_state,
            mock_breaker,
            max_single_ratio=2.0,
            min_bet=1.0,  # Allow 200% ratio to trigger the check
        )

        prediction = create_prediction()
        market = create_market()

        result = await controller.check_trade_allowed(prediction, market)

        # Trade amount would be: 5 * 2.0 = 10.0 > 5.0 capital
        assert result.allowed is False
        assert RiskCheckFailure.INSUFFICIENT_CAPITAL in result.failures
        assert "Insufficient capital" in result.reasons[0]


class TestRiskCheckFailureEnum:
    """Tests for RiskCheckFailure enum."""

    def test_enum_values(self):
        """Test that all expected enum values exist."""
        expected = [
            "low_confidence",
            "low_edge",
            "no_trade_recommendation",
            "max_position_per_market",
            "max_total_position",
            "max_open_markets",
            "trade_too_large",
            "trade_too_small",
            "insufficient_capital",
            "trading_disabled",
            "circuit_breaker",
        ]
        actual = [e.value for e in RiskCheckFailure]
        assert set(expected) == set(actual)
