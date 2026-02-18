# tests/test_analysis/test_llm_analyzer_notifications.py
"""Tests for LLMAnalyzer notification integration.

Story 9.4: LLM 分析结果通知
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.analysis.llm_analyzer import LLMAnalyzer
from src.models.market import Market, MarketCategory
from src.models.prediction import PredictionResult, Recommendation


class TestLLMAnalyzerNotifications:
    """Tests for LLMAnalyzer notification integration."""

    @pytest.fixture
    def mock_notifier(self) -> AsyncMock:
        """Create a mock TelegramNotifier."""
        notifier = AsyncMock()
        notifier.send_analysis_notification = AsyncMock(return_value=True)
        return notifier

    @pytest.fixture
    def sample_market(self) -> Market:
        """Create a sample market."""
        return Market(
            id="market-1",
            title="Will BTC reach $100k?",
            yes_price=0.55,
            no_price=0.45,
            category=MarketCategory.CRYPTO,
            deadline=datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc),
        )

    @pytest.fixture
    def tradeable_prediction(self) -> PredictionResult:
        """Create a tradeable prediction."""
        return PredictionResult(
            predicted_probability=0.75,
            confidence=0.85,
            reasoning="Strong indicators",
            key_assumptions=[
                "Economy stable",
                "No major news",
                "Technical indicators bullish",
            ],
            recommendation=Recommendation.BUY_YES,
            edge=0.20,
        )

    @pytest.fixture
    def non_tradeable_prediction_low_confidence(self) -> PredictionResult:
        """Create a non-tradeable prediction (low confidence)."""
        return PredictionResult(
            predicted_probability=0.55,
            confidence=0.60,  # Below 75% threshold
            reasoning="Uncertain",
            key_assumptions=[],
            recommendation=Recommendation.BUY_YES,
            edge=0.05,
        )

    @pytest.fixture
    def non_tradeable_prediction_low_edge(self) -> PredictionResult:
        """Create a non-tradeable prediction (low edge)."""
        return PredictionResult(
            predicted_probability=0.65,
            confidence=0.85,
            reasoning="Edge too low",
            key_assumptions=[],
            recommendation=Recommendation.BUY_YES,
            edge=0.05,  # Below 10% threshold
        )

    @pytest.fixture
    def no_trade_prediction(self) -> PredictionResult:
        """Create a NO_TRADE prediction."""
        return PredictionResult(
            predicted_probability=0.50,
            confidence=0.70,
            reasoning="No clear edge",
            key_assumptions=[],
            recommendation=Recommendation.NO_TRADE,
            edge=0.0,
        )

    def test_init_with_notifier(self, mock_notifier: AsyncMock) -> None:
        """Test initialization with notifier."""
        with patch("src.analysis.llm_analyzer.get_logger"):
            analyzer = LLMAnalyzer(notifier=mock_notifier)
            assert analyzer._notifier is mock_notifier

    def test_init_without_notifier(self) -> None:
        """Test initialization without notifier."""
        with patch("src.analysis.llm_analyzer.get_logger"):
            analyzer = LLMAnalyzer()
            assert analyzer._notifier is None

    def test_should_notify_tradeable_signal(
        self,
        mock_notifier: AsyncMock,
        tradeable_prediction: PredictionResult,
    ) -> None:
        """Test _should_notify_analysis returns True for tradeable signal."""
        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                analyzer = LLMAnalyzer(notifier=mock_notifier)

                should_notify = analyzer._should_notify_analysis(tradeable_prediction)
                assert should_notify is True

    def test_should_not_notify_low_confidence(
        self,
        mock_notifier: AsyncMock,
        non_tradeable_prediction_low_confidence: PredictionResult,
    ) -> None:
        """Test _should_notify_analysis returns False for low confidence."""
        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                analyzer = LLMAnalyzer(notifier=mock_notifier)

                should_notify = analyzer._should_notify_analysis(
                    non_tradeable_prediction_low_confidence
                )
                assert should_notify is False

    def test_should_not_notify_low_edge(
        self,
        mock_notifier: AsyncMock,
        non_tradeable_prediction_low_edge: PredictionResult,
    ) -> None:
        """Test _should_notify_analysis returns False for low edge."""
        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                analyzer = LLMAnalyzer(notifier=mock_notifier)

                should_notify = analyzer._should_notify_analysis(
                    non_tradeable_prediction_low_edge
                )
                assert should_notify is False

    def test_should_not_notify_no_trade(
        self,
        mock_notifier: AsyncMock,
        no_trade_prediction: PredictionResult,
    ) -> None:
        """Test _should_notify_analysis returns False for NO_TRADE."""
        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                analyzer = LLMAnalyzer(notifier=mock_notifier)

                should_notify = analyzer._should_notify_analysis(no_trade_prediction)
                assert should_notify is False

    def test_should_notify_all_when_configured(
        self,
        mock_notifier: AsyncMock,
        non_tradeable_prediction_low_confidence: PredictionResult,
    ) -> None:
        """Test notification sent for all analyses when configured."""
        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = True
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                analyzer = LLMAnalyzer(notifier=mock_notifier)

                should_notify = analyzer._should_notify_analysis(
                    non_tradeable_prediction_low_confidence
                )
                assert should_notify is True

    @pytest.mark.asyncio
    async def test_notify_analysis_result_sends_notification(
        self,
        mock_notifier: AsyncMock,
        sample_market: Market,
        tradeable_prediction: PredictionResult,
    ) -> None:
        """Test _notify_analysis_result sends notification for tradeable signal."""
        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                analyzer = LLMAnalyzer(notifier=mock_notifier)

                await analyzer._notify_analysis_result(
                    tradeable_prediction, sample_market
                )

                mock_notifier.send_analysis_notification.assert_called_once_with(
                    tradeable_prediction, sample_market
                )

    @pytest.mark.asyncio
    async def test_notify_analysis_result_skips_non_tradeable(
        self,
        mock_notifier: AsyncMock,
        sample_market: Market,
        non_tradeable_prediction_low_confidence: PredictionResult,
    ) -> None:
        """Test _notify_analysis_result skips notification for non-tradeable signal."""
        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                analyzer = LLMAnalyzer(notifier=mock_notifier)

                await analyzer._notify_analysis_result(
                    non_tradeable_prediction_low_confidence, sample_market
                )

                mock_notifier.send_analysis_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_analysis_result_without_notifier(
        self,
        sample_market: Market,
        tradeable_prediction: PredictionResult,
    ) -> None:
        """Test _notify_analysis_result does nothing when notifier is None."""
        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                analyzer = LLMAnalyzer()  # No notifier

                # Should not raise exception
                await analyzer._notify_analysis_result(
                    tradeable_prediction, sample_market
                )

    @pytest.mark.asyncio
    async def test_notification_failure_does_not_affect_analysis(
        self,
        mock_notifier: AsyncMock,
        sample_market: Market,
        tradeable_prediction: PredictionResult,
    ) -> None:
        """Test that notification failure doesn't affect analysis result."""
        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                # Make notification fail
                mock_notifier.send_analysis_notification = AsyncMock(
                    side_effect=Exception("Network error")
                )

                analyzer = LLMAnalyzer(notifier=mock_notifier)

                # Should not raise exception
                await analyzer._notify_analysis_result(
                    tradeable_prediction, sample_market
                )

    @pytest.mark.asyncio
    async def test_analyze_market_sends_notification(
        self,
        mock_notifier: AsyncMock,
        sample_market: Market,
    ) -> None:
        """Test analyze_market sends notification after successful analysis."""
        mock_response = """```json
        {
            "predicted_probability": 0.75,
            "confidence": 0.85,
            "reasoning": "Strong indicators",
            "key_assumptions": ["Economy stable"],
            "recommendation": "BUY_YES"
        }
        ```"""

        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.chat_with_system.return_value = mock_response
                    mock_client.__enter__ = MagicMock(return_value=mock_client)
                    mock_client.__exit__ = MagicMock(return_value=None)
                    mock_client_class.return_value = mock_client

                    analyzer = LLMAnalyzer(notifier=mock_notifier)
                    result = await analyzer.analyze_market(sample_market)

                    # Verify result was returned
                    assert isinstance(result, PredictionResult)
                    assert result.recommendation == Recommendation.BUY_YES

                    # Verify notification was sent
                    mock_notifier.send_analysis_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_market_without_notifier(
        self,
        sample_market: Market,
    ) -> None:
        """Test analyze_market works without notifier."""
        mock_response = """```json
        {
            "predicted_probability": 0.75,
            "confidence": 0.85,
            "reasoning": "Strong indicators",
            "key_assumptions": [],
            "recommendation": "BUY_YES"
        }
        ```"""

        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.chat_with_system.return_value = mock_response
                    mock_client.__enter__ = MagicMock(return_value=mock_client)
                    mock_client.__exit__ = MagicMock(return_value=None)
                    mock_client_class.return_value = mock_client

                    analyzer = LLMAnalyzer()  # No notifier
                    result = await analyzer.analyze_market(sample_market)

                    # Verify result was returned
                    assert isinstance(result, PredictionResult)

    @pytest.mark.asyncio
    async def test_analyze_market_notification_failure_does_not_affect_result(
        self,
        mock_notifier: AsyncMock,
        sample_market: Market,
    ) -> None:
        """Test that notification failure doesn't affect analysis result."""
        mock_response = """```json
        {
            "predicted_probability": 0.75,
            "confidence": 0.85,
            "reasoning": "Strong indicators",
            "key_assumptions": [],
            "recommendation": "BUY_YES"
        }
        ```"""

        # Make notification fail
        mock_notifier.send_analysis_notification = AsyncMock(
            side_effect=Exception("Network error")
        )

        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                with patch("src.analysis.llm_analyzer.LLMClient") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.chat_with_system.return_value = mock_response
                    mock_client.__enter__ = MagicMock(return_value=mock_client)
                    mock_client.__exit__ = MagicMock(return_value=None)
                    mock_client_class.return_value = mock_client

                    analyzer = LLMAnalyzer(notifier=mock_notifier)

                    # Should not raise exception
                    result = await analyzer.analyze_market(sample_market)

                    # Verify result was still returned
                    assert isinstance(result, PredictionResult)
                    assert result.recommendation == Recommendation.BUY_YES


class TestShouldNotifyAnalysisEdgeCases:
    """Test edge cases for _should_notify_analysis."""

    @pytest.fixture
    def mock_notifier(self) -> AsyncMock:
        """Create a mock TelegramNotifier."""
        return AsyncMock()

    def test_edge_exactly_at_threshold(
        self,
        mock_notifier: AsyncMock,
    ) -> None:
        """Test edge exactly at threshold is tradeable."""
        prediction = PredictionResult(
            predicted_probability=0.75,
            confidence=0.75,  # Exactly at threshold
            reasoning="Test",
            key_assumptions=[],
            recommendation=Recommendation.BUY_YES,
            edge=0.10,  # Exactly at threshold
        )

        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                analyzer = LLMAnalyzer(notifier=mock_notifier)

                assert analyzer._should_notify_analysis(prediction) is True

    def test_edge_none_value(
        self,
        mock_notifier: AsyncMock,
    ) -> None:
        """Test prediction with None edge passes edge check."""
        prediction = PredictionResult(
            predicted_probability=0.75,
            confidence=0.85,
            reasoning="Test",
            key_assumptions=[],
            recommendation=Recommendation.BUY_YES,
            edge=None,  # No edge calculated
        )

        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                analyzer = LLMAnalyzer(notifier=mock_notifier)

                # Should pass because edge is None (skips edge check)
                assert analyzer._should_notify_analysis(prediction) is True

    def test_confidence_just_below_threshold(
        self,
        mock_notifier: AsyncMock,
    ) -> None:
        """Test confidence just below threshold is not tradeable."""
        prediction = PredictionResult(
            predicted_probability=0.80,
            confidence=0.74,  # Just below 0.75
            reasoning="Test",
            key_assumptions=[],
            recommendation=Recommendation.BUY_YES,
            edge=0.20,
        )

        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                analyzer = LLMAnalyzer(notifier=mock_notifier)

                assert analyzer._should_notify_analysis(prediction) is False

    def test_edge_just_below_threshold(
        self,
        mock_notifier: AsyncMock,
    ) -> None:
        """Test edge just below threshold is not tradeable."""
        prediction = PredictionResult(
            predicted_probability=0.80,
            confidence=0.85,
            reasoning="Test",
            key_assumptions=[],
            recommendation=Recommendation.BUY_YES,
            edge=0.09,  # Just below 0.10
        )

        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                analyzer = LLMAnalyzer(notifier=mock_notifier)

                assert analyzer._should_notify_analysis(prediction) is False
