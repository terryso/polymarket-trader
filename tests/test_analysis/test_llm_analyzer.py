# tests/test_analysis/test_llm_analyzer.py
"""Tests for LLM market analyzer.

This module tests the LLMAnalyzer class that integrates with the LLM API
to analyze prediction markets and generate probability estimates.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.analysis.llm_analyzer import AnalysisError, LLMAnalyzer
from src.exceptions import NetworkError, RequestTimeoutError
from src.models.market import Market, MarketCategory
from src.models.prediction import PredictionResult, Recommendation


class TestAnalysisError:
    """Test AnalysisError exception class."""

    def test_basic_error(self) -> None:
        """Test basic error creation."""
        error = AnalysisError(message="Test error")
        assert error.message == "Test error"
        assert error.market_id is None
        assert error.original_exception is None
        assert str(error) == "Test error"

    def test_error_with_market_id(self) -> None:
        """Test error with market ID."""
        error = AnalysisError(
            message="Test error",
            market_id="market-123",
        )
        assert error.message == "Test error"
        assert error.market_id == "market-123"
        assert "market_id=market-123" in str(error)

    def test_error_with_original_exception(self) -> None:
        """Test error with original exception."""
        original = ValueError("Original error")
        error = AnalysisError(
            message="Test error",
            original_exception=original,
        )
        assert error.original_exception == original
        assert "caused by: Original error" in str(error)

    def test_error_with_all_fields(self) -> None:
        """Test error with all fields."""
        original = ValueError("Original error")
        error = AnalysisError(
            message="Test error",
            market_id="market-123",
            original_exception=original,
        )
        error_str = str(error)
        assert "Test error" in error_str
        assert "market_id=market-123" in error_str
        assert "caused by: Original error" in error_str


class TestLLMAnalyzer:
    """Test LLMAnalyzer class."""

    @pytest.fixture
    def analyzer(self) -> LLMAnalyzer:
        """Create analyzer instance."""
        return LLMAnalyzer()

    @pytest.fixture
    def sample_market(self) -> Market:
        """Create sample market for testing."""
        return Market(
            id="test-market-123",
            title="Will X happen by 2026?",
            description="A test prediction market",
            category=MarketCategory.POLITICS,
            yes_price=0.65,
            no_price=0.35,
            liquidity=50000.0,
            deadline=datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc),
        )

    def test_init(self, analyzer: LLMAnalyzer) -> None:
        """Test analyzer initialization."""
        assert analyzer._min_confidence == 0.75  # Default from config
        assert analyzer._min_edge == 0.10  # Default from config

    @pytest.mark.asyncio
    async def test_analyze_market_success(
        self, analyzer: LLMAnalyzer, sample_market: Market
    ) -> None:
        """Test successful market analysis."""
        mock_response = """```json
        {
            "predicted_probability": 0.75,
            "confidence": 0.85,
            "reasoning": "Based on current trends...",
            "key_assumptions": ["Economic stability continues"],
            "recommendation": "BUY_YES"
        }
        ```"""

        with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat_with_system.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await analyzer.analyze_market(sample_market)

            assert isinstance(result, PredictionResult)
            assert result.predicted_probability == 0.75
            assert result.confidence == 0.85
            assert result.recommendation == Recommendation.BUY_YES
            assert "Economic stability continues" in result.key_assumptions

    @pytest.mark.asyncio
    async def test_analyze_market_buy_no(
        self, analyzer: LLMAnalyzer, sample_market: Market
    ) -> None:
        """Test analysis returning BUY_NO recommendation."""
        mock_response = """```json
        {
            "predicted_probability": 0.25,
            "confidence": 0.80,
            "reasoning": "Analysis suggests NO outcome is more likely.",
            "key_assumptions": ["Trend reversal expected"],
            "recommendation": "BUY_NO"
        }
        ```"""

        with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat_with_system.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await analyzer.analyze_market(sample_market)

            assert result.recommendation == Recommendation.BUY_NO

    @pytest.mark.asyncio
    async def test_analyze_market_no_trade(
        self, analyzer: LLMAnalyzer, sample_market: Market
    ) -> None:
        """Test analysis returning NO_TRADE recommendation."""
        mock_response = """```json
        {
            "predicted_probability": 0.55,
            "confidence": 0.65,
            "reasoning": "Insufficient edge for trading.",
            "key_assumptions": [],
            "recommendation": "NO_TRADE"
        }
        ```"""

        with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat_with_system.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await analyzer.analyze_market(sample_market)

            assert result.recommendation == Recommendation.NO_TRADE

    @pytest.mark.asyncio
    async def test_analyze_market_json_parse_error(
        self, analyzer: LLMAnalyzer, sample_market: Market
    ) -> None:
        """Test JSON parsing error handling."""
        mock_response = "This is not valid JSON"

        with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat_with_system.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(AnalysisError) as exc_info:
                await analyzer.analyze_market(sample_market)

            assert "Failed to parse LLM response" in str(exc_info.value)
            assert exc_info.value.market_id == sample_market.id

    @pytest.mark.asyncio
    async def test_analyze_market_network_error(
        self, analyzer: LLMAnalyzer, sample_market: Market
    ) -> None:
        """Test network error handling."""
        with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat_with_system.side_effect = NetworkError(
                message="Connection failed",
                endpoint="chat",
            )
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(AnalysisError) as exc_info:
                await analyzer.analyze_market(sample_market)

            assert "LLM API error" in str(exc_info.value)
            assert isinstance(exc_info.value.original_exception, NetworkError)

    @pytest.mark.asyncio
    async def test_analyze_market_timeout_error(
        self, analyzer: LLMAnalyzer, sample_market: Market
    ) -> None:
        """Test timeout error handling."""
        with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat_with_system.side_effect = RequestTimeoutError(
                message="Request timed out",
                endpoint="chat",
                timeout_seconds=30,
            )
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(AnalysisError) as exc_info:
                await analyzer.analyze_market(sample_market)

            assert "LLM API error" in str(exc_info.value)
            assert isinstance(exc_info.value.original_exception, RequestTimeoutError)

    @pytest.mark.asyncio
    async def test_analyze_market_unexpected_error(
        self, analyzer: LLMAnalyzer, sample_market: Market
    ) -> None:
        """Test unexpected error handling."""
        with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat_with_system.side_effect = RuntimeError("Unexpected error")
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(AnalysisError) as exc_info:
                await analyzer.analyze_market(sample_market)

            assert "Unexpected error" in str(exc_info.value)


class TestIsTradeable:
    """Test _is_tradeable validation method."""

    @pytest.fixture
    def analyzer(self) -> LLMAnalyzer:
        """Create analyzer instance."""
        return LLMAnalyzer()

    def test_high_confidence_buy_yes(self, analyzer: LLMAnalyzer) -> None:
        """Test high confidence BUY_YES is tradeable."""
        result = PredictionResult(
            predicted_probability=0.8,
            confidence=0.85,
            reasoning="Strong analysis",
            recommendation=Recommendation.BUY_YES,
        )
        assert analyzer._is_tradeable(result, 0.65) is True

    def test_low_confidence(self, analyzer: LLMAnalyzer) -> None:
        """Test low confidence is not tradeable."""
        result = PredictionResult(
            predicted_probability=0.8,
            confidence=0.5,  # Below 0.75
            reasoning="Analysis",
            recommendation=Recommendation.BUY_YES,
        )
        assert analyzer._is_tradeable(result, 0.65) is False

    def test_no_trade_recommendation(self, analyzer: LLMAnalyzer) -> None:
        """Test NO_TRADE recommendation is not tradeable."""
        result = PredictionResult(
            predicted_probability=0.55,
            confidence=0.85,
            reasoning="Analysis",
            recommendation=Recommendation.NO_TRADE,
        )
        assert analyzer._is_tradeable(result, 0.65) is False

    def test_insufficient_edge_buy_yes(self, analyzer: LLMAnalyzer) -> None:
        """Test BUY_YES with insufficient edge is not tradeable."""
        result = PredictionResult(
            predicted_probability=0.70,  # Only 5% above market
            confidence=0.85,
            reasoning="Analysis",
            recommendation=Recommendation.BUY_YES,
        )
        assert analyzer._is_tradeable(result, 0.65) is False

    def test_insufficient_edge_buy_no(self, analyzer: LLMAnalyzer) -> None:
        """Test BUY_NO with insufficient edge is not tradeable."""
        result = PredictionResult(
            predicted_probability=0.60,  # NO probability = 0.40, market NO = 0.35
            confidence=0.85,
            reasoning="Analysis",
            recommendation=Recommendation.BUY_NO,
        )
        # Edge = 0.40 - 0.35 = 0.05 (below 0.10)
        assert analyzer._is_tradeable(result, 0.65) is False

    def test_sufficient_edge_buy_no(self, analyzer: LLMAnalyzer) -> None:
        """Test BUY_NO with sufficient edge is tradeable."""
        result = PredictionResult(
            predicted_probability=0.20,  # NO probability = 0.80, market NO = 0.35
            confidence=0.85,
            reasoning="Analysis",
            recommendation=Recommendation.BUY_NO,
        )
        # Edge = 0.80 - 0.35 = 0.45 (above 0.10)
        assert analyzer._is_tradeable(result, 0.65) is True

    def test_no_market_price(self, analyzer: LLMAnalyzer) -> None:
        """Test tradeable check without market price (skips edge check)."""
        result = PredictionResult(
            predicted_probability=0.80,
            confidence=0.85,
            reasoning="Analysis",
            recommendation=Recommendation.BUY_YES,
        )
        # Without market price, edge check is skipped
        assert analyzer._is_tradeable(result, None) is True

    def test_at_min_confidence(self, analyzer: LLMAnalyzer) -> None:
        """Test at minimum confidence threshold."""
        result = PredictionResult(
            predicted_probability=0.80,
            confidence=0.75,  # Exactly at threshold
            reasoning="Analysis",
            recommendation=Recommendation.BUY_YES,
        )
        assert analyzer._is_tradeable(result, 0.65) is True


class TestCalculateEdge:
    """Test calculate_edge method."""

    @pytest.fixture
    def analyzer(self) -> LLMAnalyzer:
        """Create analyzer instance."""
        return LLMAnalyzer()

    def test_calculate_edge_buy_yes(self, analyzer: LLMAnalyzer) -> None:
        """Test BUY_YES edge calculation."""
        result = PredictionResult(
            predicted_probability=0.8,
            confidence=0.85,
            reasoning="Detailed analysis",
            recommendation=Recommendation.BUY_YES,
        )
        edge = analyzer.calculate_edge(result, 0.65)
        assert edge == pytest.approx(0.15)  # 0.8 - 0.65

    def test_calculate_edge_buy_no(self, analyzer: LLMAnalyzer) -> None:
        """Test BUY_NO edge calculation."""
        result = PredictionResult(
            predicted_probability=0.3,  # 1 - 0.3 = 0.7 NO probability
            confidence=0.85,
            reasoning="Detailed analysis",
            recommendation=Recommendation.BUY_NO,
        )
        market_yes_price = 0.4  # NO price = 0.6
        edge = analyzer.calculate_edge(result, market_yes_price)
        # (1 - 0.3) - (1 - 0.4) = 0.7 - 0.6 = 0.1
        assert edge == pytest.approx(0.1)

    def test_calculate_edge_no_trade(self, analyzer: LLMAnalyzer) -> None:
        """Test NO_TRADE edge calculation returns 0."""
        result = PredictionResult(
            predicted_probability=0.5,
            confidence=0.85,
            reasoning="Detailed analysis",
            recommendation=Recommendation.NO_TRADE,
        )
        edge = analyzer.calculate_edge(result, 0.5)
        assert edge == pytest.approx(0.0)

    def test_calculate_edge_negative_buy_yes(self, analyzer: LLMAnalyzer) -> None:
        """Test negative edge for BUY_YES (predicted < market)."""
        result = PredictionResult(
            predicted_probability=0.5,
            confidence=0.85,
            reasoning="Detailed analysis",
            recommendation=Recommendation.BUY_YES,
        )
        edge = analyzer.calculate_edge(result, 0.7)
        assert edge == pytest.approx(-0.2)  # 0.5 - 0.7

    def test_calculate_edge_at_boundary(self, analyzer: LLMAnalyzer) -> None:
        """Test edge at exactly 0."""
        result = PredictionResult(
            predicted_probability=0.65,
            confidence=0.85,
            reasoning="Detailed analysis",
            recommendation=Recommendation.BUY_YES,
        )
        edge = analyzer.calculate_edge(result, 0.65)
        assert edge == pytest.approx(0.0)


class TestAnalyzeMarkets:
    """Test analyze_markets batch method."""

    @pytest.fixture
    def analyzer(self) -> LLMAnalyzer:
        """Create analyzer instance."""
        return LLMAnalyzer()

    @pytest.fixture
    def sample_markets(self) -> list[Market]:
        """Create list of sample markets."""
        return [
            Market(
                id=f"market-{i}",
                title=f"Market {i}",
                description=f"Description {i}",
                yes_price=0.5 + i * 0.1,
            )
            for i in range(3)
        ]

    @pytest.mark.asyncio
    async def test_analyze_markets_success(
        self, analyzer: LLMAnalyzer, sample_markets: list[Market]
    ) -> None:
        """Test successful batch analysis."""
        mock_response = """{
            "predicted_probability": 0.75,
            "confidence": 0.85,
            "reasoning": "This is a detailed analysis of the market.",
            "key_assumptions": [],
            "recommendation": "BUY_YES"
        }"""

        with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat_with_system.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)
            mock_client_class.return_value = mock_client

            results = await analyzer.analyze_markets(sample_markets)

            assert len(results) == 3
            for market, result in results:
                assert isinstance(result, PredictionResult)
                assert result.predicted_probability == 0.75

    @pytest.mark.asyncio
    async def test_analyze_markets_mixed_results(
        self, analyzer: LLMAnalyzer, sample_markets: list[Market]
    ) -> None:
        """Test batch analysis with mixed success/failure."""

        def mock_chat_side_effect(*args, **kwargs):
            # First call succeeds, second fails, third succeeds
            call_count = mock_chat_side_effect.call_count
            mock_chat_side_effect.call_count = call_count + 1

            if call_count == 1:
                return """{
                    "predicted_probability": 0.75,
                    "confidence": 0.85,
                    "reasoning": "This is a detailed analysis of the market.",
                    "key_assumptions": [],
                    "recommendation": "BUY_YES"
                }"""
            elif call_count == 2:
                raise NetworkError(message="Connection failed", endpoint="chat")
            else:
                return """{
                    "predicted_probability": 0.65,
                    "confidence": 0.80,
                    "reasoning": "This is a detailed analysis of the market.",
                    "key_assumptions": [],
                    "recommendation": "BUY_NO"
                }"""

        mock_chat_side_effect.call_count = 0

        with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat_with_system.side_effect = mock_chat_side_effect
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)
            mock_client_class.return_value = mock_client

            results = await analyzer.analyze_markets(sample_markets)

            assert len(results) == 3

            # Count successes and errors (order may vary due to concurrency)
            success_count = sum(
                1 for _, result in results if isinstance(result, PredictionResult)
            )
            error_count = sum(
                1 for _, result in results if isinstance(result, AnalysisError)
            )

            assert success_count == 2
            assert error_count == 1

    @pytest.mark.asyncio
    async def test_analyze_markets_all_fail(
        self, analyzer: LLMAnalyzer, sample_markets: list[Market]
    ) -> None:
        """Test batch analysis with all failures."""
        with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat_with_system.side_effect = NetworkError(
                message="Connection failed",
                endpoint="chat",
            )
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)
            mock_client_class.return_value = mock_client

            results = await analyzer.analyze_markets(sample_markets)

            assert len(results) == 3
            for market, result in results:
                assert isinstance(result, AnalysisError)

    @pytest.mark.asyncio
    async def test_analyze_markets_empty_list(self, analyzer: LLMAnalyzer) -> None:
        """Test batch analysis with empty list."""
        results = await analyzer.analyze_markets([])
        assert results == []

    @pytest.mark.asyncio
    async def test_analyze_markets_concurrency_limit(
        self, analyzer: LLMAnalyzer, sample_markets: list[Market]
    ) -> None:
        """Test batch analysis respects concurrency limit."""
        mock_response = """{
            "predicted_probability": 0.75,
            "confidence": 0.85,
            "reasoning": "This is a detailed analysis of the market.",
            "key_assumptions": [],
            "recommendation": "BUY_YES"
        }"""

        concurrent_count = 0
        max_concurrent = 0

        def track_concurrency(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            # Simulate some processing time
            import time

            time.sleep(0.01)
            concurrent_count -= 1
            return mock_response

        with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat_with_system.side_effect = track_concurrency
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Use max_concurrent=1 to ensure sequential execution
            results = await analyzer.analyze_markets(sample_markets, max_concurrent=1)

            assert len(results) == 3
            # With max_concurrent=1, should never exceed 1
            assert max_concurrent <= 1
