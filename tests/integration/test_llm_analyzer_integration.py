"""Integration tests for LLMAnalyzer with real GLM API calls.

These tests make actual HTTP requests to the GLM API.
Run with: pytest tests/integration/ -v -m integration

To skip these tests during normal development:
    pytest tests/ -v -m "not integration"

Note: These tests require a valid LLM_API_KEY environment variable.
"""

from __future__ import annotations

import asyncio

import pytest
from datetime import datetime, timezone

from src.analysis import LLMAnalyzer
from src.analysis.llm_analyzer import AnalysisError
from src.config import settings
from src.models.market import Market, MarketCategory
from src.models.prediction import PredictionResult, Recommendation

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Skip all tests if no API key is configured
requires_llm_api_key = pytest.mark.skipif(
    not settings.llm.api_key,
    reason="LLM_API_KEY not configured",
)


@pytest.fixture
def sample_market() -> Market:
    """Create a sample market for testing."""
    return Market(
        id="test-market-integration-001",
        title="Will Bitcoin reach $100,000 by end of 2026?",
        description="This market resolves to YES if Bitcoin (BTC) reaches or exceeds $100,000 USD on any major exchange before December 31, 2026.",
        category=MarketCategory.CRYPTO,
        yes_price=0.45,
        no_price=0.55,
        liquidity=100000.0,
        deadline=datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc),
    )


@pytest.fixture
def low_liquidity_market() -> Market:
    """Create a low liquidity market for testing."""
    return Market(
        id="test-market-low-liquidity",
        title="Will it rain in London on January 1, 2027?",
        description="Weather prediction market.",
        category=MarketCategory.ECONOMICS,  # Use a valid category
        yes_price=0.30,
        no_price=0.70,
        liquidity=500.0,
        deadline=datetime(2027, 1, 1, 23, 59, tzinfo=timezone.utc),
    )


class TestLLMAnalyzerIntegration:
    """Integration tests for LLMAnalyzer with real LLM API."""

    @requires_llm_api_key
    @pytest.mark.asyncio
    async def test_analyze_market_returns_prediction_result(
        self, sample_market: Market
    ) -> None:
        """Test that analyze_market returns a valid PredictionResult."""
        analyzer = LLMAnalyzer()
        result = await analyzer.analyze_market(sample_market)

        assert isinstance(result, PredictionResult)
        assert 0.0 <= result.predicted_probability <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.reasoning, str)
        assert len(result.reasoning) > 0
        assert isinstance(result.recommendation, Recommendation)
        assert isinstance(result.key_assumptions, list)

    @requires_llm_api_key
    @pytest.mark.asyncio
    async def test_analyze_market_probability_range(
        self, sample_market: Market
    ) -> None:
        """Test that predicted probability is within valid range."""
        analyzer = LLMAnalyzer()
        result = await analyzer.analyze_market(sample_market)

        assert result.predicted_probability >= 0.0
        assert result.predicted_probability <= 1.0

    @requires_llm_api_key
    @pytest.mark.asyncio
    async def test_analyze_market_confidence_range(self, sample_market: Market) -> None:
        """Test that confidence is within valid range."""
        analyzer = LLMAnalyzer()
        result = await analyzer.analyze_market(sample_market)

        assert result.confidence >= 0.0
        assert result.confidence <= 1.0

    @requires_llm_api_key
    @pytest.mark.asyncio
    async def test_analyze_market_valid_recommendation(
        self, sample_market: Market
    ) -> None:
        """Test that recommendation is a valid enum value."""
        analyzer = LLMAnalyzer()
        result = await analyzer.analyze_market(sample_market)

        assert result.recommendation in [
            Recommendation.BUY_YES,
            Recommendation.BUY_NO,
            Recommendation.NO_TRADE,
        ]

    @requires_llm_api_key
    @pytest.mark.asyncio
    async def test_analyze_market_has_reasoning(self, sample_market: Market) -> None:
        """Test that analysis includes reasoning."""
        analyzer = LLMAnalyzer()
        result = await analyzer.analyze_market(sample_market)

        assert result.reasoning is not None
        assert len(result.reasoning) > 50  # Should have substantial reasoning

    @requires_llm_api_key
    @pytest.mark.asyncio
    async def test_analyze_market_edge_calculation(self, sample_market: Market) -> None:
        """Test that edge is calculated when market has yes_price."""
        analyzer = LLMAnalyzer()
        result = await analyzer.analyze_market(sample_market)

        # Edge should be calculated since sample_market has yes_price
        assert result.edge is not None
        assert 0.0 <= result.edge <= 1.0

    @requires_llm_api_key
    @pytest.mark.asyncio
    async def test_analyze_market_without_price(self) -> None:
        """Test analysis when market has no price."""
        analyzer = LLMAnalyzer()
        market = Market(
            id="test-no-price",
            title="Test market without price",
            description="A test market",
            category=MarketCategory.ECONOMICS,
            yes_price=None,
            no_price=None,
            liquidity=None,
            deadline=datetime(2026, 12, 31, tzinfo=timezone.utc),
        )

        result = await analyzer.analyze_market(market)

        assert isinstance(result, PredictionResult)
        # Edge should not be calculated without market price
        assert result.edge is None


class TestLLMAnalyzerBatchIntegration:
    """Integration tests for LLMAnalyzer batch analysis."""

    @requires_llm_api_key
    @pytest.mark.asyncio
    async def test_analyze_markets_batch(
        self, sample_market: Market, low_liquidity_market: Market
    ) -> None:
        """Test batch analysis of multiple markets."""
        analyzer = LLMAnalyzer()
        markets = [sample_market, low_liquidity_market]

        results = await analyzer.analyze_markets(markets, max_concurrent=2)

        assert len(results) == 2
        for market, result in results:
            assert market in markets
            # Each result should be either PredictionResult or AnalysisError
            assert isinstance(result, (PredictionResult, AnalysisError))

    @requires_llm_api_key
    @pytest.mark.asyncio
    async def test_analyze_markets_concurrency_control(
        self, sample_market: Market
    ) -> None:
        """Test that concurrency control works."""
        analyzer = LLMAnalyzer()
        # Create 3 copies of the same market
        markets = [
            Market(
                id=f"test-market-concurrent-{i}",
                title=f"Test market {i}",
                description="Test",
                category=MarketCategory.ECONOMICS,
                yes_price=0.5,
                deadline=datetime(2026, 12, 31, tzinfo=timezone.utc),
            )
            for i in range(3)
        ]

        # Run with max_concurrent=1 to test serialization
        results = await analyzer.analyze_markets(markets, max_concurrent=1)

        assert len(results) == 3

    @requires_llm_api_key
    @pytest.mark.asyncio
    async def test_analyze_markets_mixed_results(self, sample_market: Market) -> None:
        """Test batch analysis with mixed results."""
        analyzer = LLMAnalyzer()

        # Create a market that might produce different results
        markets = [
            sample_market,
            Market(
                id="test-market-different",
                title="Will the sun rise tomorrow?",
                description="A very predictable event",
                category=MarketCategory.ECONOMICS,
                yes_price=0.99,
                deadline=datetime(2026, 12, 31, tzinfo=timezone.utc),
            ),
        ]

        results = await analyzer.analyze_markets(markets)

        assert len(results) == 2
        success_count = sum(1 for _, r in results if isinstance(r, PredictionResult))
        assert success_count >= 1  # At least one should succeed


class TestLLMAnalyzerEdgeCalculation:
    """Integration tests for Edge calculation."""

    def test_calculate_edge_buy_yes(self) -> None:
        """Test Edge calculation for BUY_YES recommendation."""
        analyzer = LLMAnalyzer()

        result = PredictionResult(
            predicted_probability=0.80,
            confidence=0.85,
            reasoning="Test",
            key_assumptions=[],
            recommendation=Recommendation.BUY_YES,
        )

        edge = analyzer.calculate_edge(result, 0.65)
        assert (
            abs(edge - 0.15) < 0.001
        )  # 0.80 - 0.65 (use approximate comparison for float)

    def test_calculate_edge_buy_no(self) -> None:
        """Test Edge calculation for BUY_NO recommendation."""
        analyzer = LLMAnalyzer()

        result = PredictionResult(
            predicted_probability=0.30,
            confidence=0.85,
            reasoning="Test",
            key_assumptions=[],
            recommendation=Recommendation.BUY_NO,
        )

        # BUY_NO: (1 - predicted) - (1 - market) = market - predicted
        edge = analyzer.calculate_edge(result, 0.65)
        assert edge == 0.35  # (1 - 0.30) - (1 - 0.65) = 0.70 - 0.35

    def test_calculate_edge_no_trade(self) -> None:
        """Test Edge calculation for NO_TRADE recommendation."""
        analyzer = LLMAnalyzer()

        result = PredictionResult(
            predicted_probability=0.50,
            confidence=0.60,
            reasoning="Test",
            key_assumptions=[],
            recommendation=Recommendation.NO_TRADE,
        )

        edge = analyzer.calculate_edge(result, 0.50)
        assert edge == 0.0


class TestLLMAnalyzerTradeableCheck:
    """Integration tests for tradeable check."""

    def test_is_tradeable_high_confidence_buy_yes(self) -> None:
        """Test tradeable check with high confidence BUY_YES."""
        analyzer = LLMAnalyzer()

        result = PredictionResult(
            predicted_probability=0.80,
            confidence=0.85,
            reasoning="Test",
            key_assumptions=[],
            recommendation=Recommendation.BUY_YES,
            edge=0.15,
        )

        assert analyzer._is_tradeable(result, 0.65) is True

    def test_is_tradeable_low_confidence(self) -> None:
        """Test tradeable check with low confidence."""
        analyzer = LLMAnalyzer()

        result = PredictionResult(
            predicted_probability=0.80,
            confidence=0.50,  # Below min_confidence (0.75)
            reasoning="Test",
            key_assumptions=[],
            recommendation=Recommendation.BUY_YES,
            edge=0.15,
        )

        assert analyzer._is_tradeable(result, 0.65) is False

    def test_is_tradeable_no_trade_recommendation(self) -> None:
        """Test tradeable check with NO_TRADE recommendation."""
        analyzer = LLMAnalyzer()

        result = PredictionResult(
            predicted_probability=0.55,
            confidence=0.85,
            reasoning="Test",
            key_assumptions=[],
            recommendation=Recommendation.NO_TRADE,
            edge=0.0,
        )

        assert analyzer._is_tradeable(result, 0.50) is False

    def test_is_tradeable_low_edge(self) -> None:
        """Test tradeable check with edge below minimum."""
        analyzer = LLMAnalyzer()

        result = PredictionResult(
            predicted_probability=0.52,
            confidence=0.85,
            reasoning="Test",
            key_assumptions=[],
            recommendation=Recommendation.BUY_YES,
            edge=0.02,  # Below min_edge (0.10)
        )

        assert analyzer._is_tradeable(result, 0.50) is False


class TestLLMAnalyzerConfiguration:
    """Integration tests for LLMAnalyzer configuration."""

    def test_analyzer_loads_risk_settings(self) -> None:
        """Test that analyzer loads risk settings from config."""
        analyzer = LLMAnalyzer()

        # These should be loaded from settings.risk
        assert analyzer._min_confidence >= 0.0
        assert analyzer._min_confidence <= 1.0
        assert analyzer._min_edge >= 0.0
        assert analyzer._min_edge <= 1.0

    def test_analyzer_default_min_confidence(self) -> None:
        """Test default minimum confidence is reasonable."""
        analyzer = LLMAnalyzer()

        # Default should be 0.75 as per Story 3.3
        assert analyzer._min_confidence == 0.75

    def test_analyzer_default_min_edge(self) -> None:
        """Test default minimum edge is reasonable."""
        analyzer = LLMAnalyzer()

        # Default should be 0.10 as per Story 3.5
        assert analyzer._min_edge == 0.10
