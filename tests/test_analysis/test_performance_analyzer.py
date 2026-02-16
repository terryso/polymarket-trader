"""Tests for PerformanceAnalyzer.

Story 6.5: 表现分析与洞察
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.analysis.performance_analyzer import (
    CategoryPerformance,
    ConfidenceAnalysis,
    EdgeAnalysis,
    ImprovementSuggestion,
    PatternInsight,
    PatternType,
    PerformanceAnalyzer,
    PerformanceInsightReport,
    PerformanceLevel,
    PerformanceMetrics,
    SuggestionPriority,
)
from src.models.market import Market, MarketCategory
from src.models.prediction import Prediction, Recommendation


class TestDataModels:
    """Tests for data model classes."""

    def test_performance_metrics_creation(self) -> None:
        """Test PerformanceMetrics creation with all fields."""
        metrics = PerformanceMetrics(
            total_trades=100,
            winning_trades=65,
            losing_trades=35,
            win_rate=0.65,
            total_pnl=150.0,
            avg_pnl=1.5,
            max_profit=50.0,
            max_loss=-20.0,
            avg_confidence=0.78,
            avg_edge=0.12,
            performance_level=PerformanceLevel.GOOD,
            analysis_period=(datetime(2024, 1, 1), datetime(2024, 1, 31)),
        )

        assert metrics.total_trades == 100
        assert metrics.win_rate == 0.65
        assert metrics.performance_level == PerformanceLevel.GOOD

    def test_category_performance_creation(self) -> None:
        """Test CategoryPerformance creation."""
        cp = CategoryPerformance(
            category="politics",
            total_trades=20,
            winning_trades=15,
            win_rate=0.75,
            total_pnl=100.0,
            avg_pnl=5.0,
            avg_confidence=0.82,
        )

        assert cp.category == "politics"
        assert cp.win_rate == 0.75

    def test_confidence_analysis_creation(self) -> None:
        """Test ConfidenceAnalysis creation."""
        ca = ConfidenceAnalysis(
            confidence_range="0.8-1.0",
            min_confidence=0.8,
            max_confidence=1.0,
            sample_size=30,
            accuracy=0.80,
            avg_pnl=3.5,
        )

        assert ca.confidence_range == "0.8-1.0"
        assert ca.accuracy == 0.80

    def test_edge_analysis_creation(self) -> None:
        """Test EdgeAnalysis creation."""
        ea = EdgeAnalysis(
            edge_range=">= 0.2",
            min_edge=0.2,
            max_edge=1.0,
            sample_size=15,
            success_rate=0.73,
            avg_return=5.0,
        )

        assert ea.edge_range == ">= 0.2"
        assert ea.success_rate == 0.73

    def test_pattern_insight_creation(self) -> None:
        """Test PatternInsight creation."""
        pi = PatternInsight(
            pattern_type=PatternType.SUCCESS,
            title="Strong politics performance",
            description="75% accuracy in politics markets",
            examples=["Market A", "Market B"],
            recommendation="Focus more on politics",
        )

        assert pi.pattern_type == PatternType.SUCCESS
        assert pi.recommendation == "Focus more on politics"

    def test_improvement_suggestion_creation(self) -> None:
        """Test ImprovementSuggestion creation."""
        isg = ImprovementSuggestion(
            category="risk",
            priority=SuggestionPriority.HIGH,
            title="Review risk management",
            description="Max loss exceeds max profit",
            action="Implement stop-loss rules",
        )

        assert isg.priority == SuggestionPriority.HIGH
        assert isg.action == "Implement stop-loss rules"


class TestPerformanceLevel:
    """Tests for PerformanceLevel enum."""

    def test_performance_levels(self) -> None:
        """Test all performance levels exist."""
        assert PerformanceLevel.EXCELLENT.value == "excellent"
        assert PerformanceLevel.GOOD.value == "good"
        assert PerformanceLevel.AVERAGE.value == "average"
        assert PerformanceLevel.POOR.value == "poor"


class TestPatternType:
    """Tests for PatternType enum."""

    def test_pattern_types(self) -> None:
        """Test all pattern types exist."""
        assert PatternType.SUCCESS.value == "success"
        assert PatternType.FAILURE.value == "failure"
        assert PatternType.NEUTRAL.value == "neutral"


class TestPerformanceAnalyzer:
    """Tests for PerformanceAnalyzer class."""

    @pytest.fixture
    def mock_prediction_repo(self) -> AsyncMock:
        """Create a mock PredictionRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_trade_repo(self) -> AsyncMock:
        """Create a mock TradeRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_position_repo(self) -> AsyncMock:
        """Create a mock PositionRepository."""
        return AsyncMock()

    @pytest.fixture
    def analyzer(
        self,
        mock_prediction_repo: AsyncMock,
        mock_trade_repo: AsyncMock,
        mock_position_repo: AsyncMock,
    ) -> PerformanceAnalyzer:
        """Create a PerformanceAnalyzer instance for testing."""
        return PerformanceAnalyzer(
            prediction_repo=mock_prediction_repo,
            trade_repo=mock_trade_repo,
            position_repo=mock_position_repo,
            reports_dir="/tmp/test_reports",
        )

    @pytest.fixture
    def sample_prediction_correct(self) -> Prediction:
        """Create a sample correct prediction."""
        return Prediction(
            id=1,
            market_id="test-market-1",
            predicted_probability=0.75,
            confidence=0.85,
            reasoning="Strong indicators",
            recommendation=Recommendation.BUY_YES,
            edge=0.15,
            is_correct=True,
            validated_at=datetime(2024, 1, 15),
        )

    @pytest.fixture
    def sample_prediction_incorrect(self) -> Prediction:
        """Create a sample incorrect prediction."""
        return Prediction(
            id=2,
            market_id="test-market-2",
            predicted_probability=0.70,
            confidence=0.80,
            reasoning="Expected YES outcome",
            recommendation=Recommendation.BUY_YES,
            edge=0.10,
            is_correct=False,
            validated_at=datetime(2024, 1, 15),
        )

    @pytest.fixture
    def sample_market_politics(self) -> Market:
        """Create a sample politics market."""
        return Market(
            id="test-market-1",
            title="Will X win election?",
            category=MarketCategory.POLITICS,
            yes_price=0.60,
            no_price=0.40,
        )

    @pytest.fixture
    def sample_market_crypto(self) -> Market:
        """Create a sample crypto market."""
        return Market(
            id="test-market-2",
            title="Will BTC reach 100k?",
            category=MarketCategory.CRYPTO,
            yes_price=0.45,
            no_price=0.55,
        )

    @pytest.mark.asyncio
    async def test_analyze_performance_no_data(
        self,
        analyzer: PerformanceAnalyzer,
        mock_prediction_repo: AsyncMock,
        mock_trade_repo: AsyncMock,
        mock_position_repo: AsyncMock,
    ) -> None:
        """Test analyze_performance with no data."""
        mock_prediction_repo.get_validated_with_market = AsyncMock(return_value=[])
        mock_trade_repo.get_by_mode = AsyncMock(return_value=[])
        mock_position_repo.get_open_positions = AsyncMock(return_value=[])

        metrics = await analyzer.analyze_performance()

        assert metrics.total_trades == 0
        assert metrics.win_rate == 0.0
        assert metrics.performance_level == PerformanceLevel.POOR

    @pytest.mark.asyncio
    async def test_analyze_performance_with_data(
        self,
        analyzer: PerformanceAnalyzer,
        mock_prediction_repo: AsyncMock,
        mock_trade_repo: AsyncMock,
        mock_position_repo: AsyncMock,
        sample_prediction_correct: Prediction,
        sample_prediction_incorrect: Prediction,
        sample_market_politics: Market,
        sample_market_crypto: Market,
    ) -> None:
        """Test analyze_performance with data."""
        mock_prediction_repo.get_validated_with_market = AsyncMock(
            return_value=[
                (sample_prediction_correct, sample_market_politics),
                (sample_prediction_incorrect, sample_market_crypto),
            ]
        )
        mock_trade_repo.get_by_mode = AsyncMock(return_value=[])
        mock_position_repo.get_open_positions = AsyncMock(return_value=[])

        metrics = await analyzer.analyze_performance()

        assert metrics.total_trades == 2
        assert metrics.winning_trades == 1
        assert metrics.losing_trades == 1
        assert metrics.win_rate == 0.5

    @pytest.mark.asyncio
    async def test_get_best_performing_categories(
        self,
        analyzer: PerformanceAnalyzer,
        mock_prediction_repo: AsyncMock,
    ) -> None:
        """Test get_best_performing_categories."""
        # Create predictions with different categories
        politics_pred = Prediction(
            id=1,
            market_id="m1",
            predicted_probability=0.8,
            confidence=0.85,
            is_correct=True,
            validated_at=datetime.now(),
        )
        crypto_pred = Prediction(
            id=2,
            market_id="m2",
            predicted_probability=0.7,
            confidence=0.75,
            is_correct=False,
            validated_at=datetime.now(),
        )

        politics_market = Market(
            id="m1",
            title="Politics Market",
            category=MarketCategory.POLITICS,
        )
        crypto_market = Market(
            id="m2",
            title="Crypto Market",
            category=MarketCategory.CRYPTO,
        )

        mock_prediction_repo.get_validated_with_market = AsyncMock(
            return_value=[
                (politics_pred, politics_market),
                (politics_pred, politics_market),
                (crypto_pred, crypto_market),
            ]
        )

        best = await analyzer.get_best_performing_categories()

        assert len(best) >= 1
        assert best[0].category == "politics"
        assert best[0].win_rate == 1.0

    @pytest.mark.asyncio
    async def test_get_worst_performing_categories(
        self,
        analyzer: PerformanceAnalyzer,
        mock_prediction_repo: AsyncMock,
    ) -> None:
        """Test get_worst_performing_categories."""
        politics_pred = Prediction(
            id=1,
            market_id="m1",
            predicted_probability=0.8,
            confidence=0.85,
            is_correct=True,
            validated_at=datetime.now(),
        )
        crypto_pred = Prediction(
            id=2,
            market_id="m2",
            predicted_probability=0.7,
            confidence=0.75,
            is_correct=False,
            validated_at=datetime.now(),
        )

        politics_market = Market(
            id="m1",
            title="Politics Market",
            category=MarketCategory.POLITICS,
        )
        crypto_market = Market(
            id="m2",
            title="Crypto Market",
            category=MarketCategory.CRYPTO,
        )

        mock_prediction_repo.get_validated_with_market = AsyncMock(
            return_value=[
                (politics_pred, politics_market),
                (crypto_pred, crypto_market),
                (crypto_pred, crypto_market),
            ]
        )

        worst = await analyzer.get_worst_performing_categories()

        assert len(worst) >= 1
        assert worst[0].category == "crypto"
        assert worst[0].win_rate == 0.0

    @pytest.mark.asyncio
    async def test_get_confidence_accuracy_correlation(
        self,
        analyzer: PerformanceAnalyzer,
        mock_prediction_repo: AsyncMock,
    ) -> None:
        """Test get_confidence_accuracy_correlation."""
        high_conf_pred = Prediction(
            id=1,
            market_id="m1",
            predicted_probability=0.8,
            confidence=0.85,
            is_correct=True,
            validated_at=datetime.now(),
        )
        low_conf_pred = Prediction(
            id=2,
            market_id="m2",
            predicted_probability=0.6,
            confidence=0.70,
            is_correct=False,
            validated_at=datetime.now(),
        )

        market = Market(
            id="m1",
            title="Test Market",
            category=MarketCategory.POLITICS,
        )

        mock_prediction_repo.get_validated_with_market = AsyncMock(
            return_value=[
                (high_conf_pred, market),
                (low_conf_pred, market),
            ]
        )

        correlation = await analyzer.get_confidence_accuracy_correlation()

        assert len(correlation) >= 1
        # Check that we have proper analysis objects
        for c in correlation:
            assert isinstance(c, ConfidenceAnalysis)
            assert 0 <= c.accuracy <= 1

    @pytest.mark.asyncio
    async def test_get_edge_success_correlation(
        self,
        analyzer: PerformanceAnalyzer,
        mock_prediction_repo: AsyncMock,
    ) -> None:
        """Test get_edge_success_correlation."""
        high_edge_pred = Prediction(
            id=1,
            market_id="m1",
            predicted_probability=0.8,
            confidence=0.85,
            edge=0.25,
            is_correct=True,
            validated_at=datetime.now(),
        )
        low_edge_pred = Prediction(
            id=2,
            market_id="m2",
            predicted_probability=0.6,
            confidence=0.75,
            edge=0.05,
            is_correct=False,
            validated_at=datetime.now(),
        )

        market = Market(
            id="m1",
            title="Test Market",
            category=MarketCategory.POLITICS,
        )

        mock_prediction_repo.get_validated_with_market = AsyncMock(
            return_value=[
                (high_edge_pred, market),
                (low_edge_pred, market),
            ]
        )

        correlation = await analyzer.get_edge_success_correlation()

        assert len(correlation) >= 1
        for e in correlation:
            assert isinstance(e, EdgeAnalysis)
            assert 0 <= e.success_rate <= 1

    @pytest.mark.asyncio
    async def test_identify_patterns(
        self,
        analyzer: PerformanceAnalyzer,
        mock_prediction_repo: AsyncMock,
    ) -> None:
        """Test identify_patterns."""
        pred = Prediction(
            id=1,
            market_id="m1",
            predicted_probability=0.8,
            confidence=0.85,
            edge=0.15,
            is_correct=True,
            validated_at=datetime.now(),
        )

        market = Market(
            id="m1",
            title="Test Market",
            category=MarketCategory.POLITICS,
        )

        mock_prediction_repo.get_validated_with_market = AsyncMock(
            return_value=[(pred, market)] * 5  # 5 correct predictions
        )

        patterns = await analyzer.identify_patterns()

        assert isinstance(patterns, list)
        for p in patterns:
            assert isinstance(p, PatternInsight)
            assert isinstance(p.pattern_type, PatternType)

    @pytest.mark.asyncio
    async def test_identify_patterns_no_data(
        self,
        analyzer: PerformanceAnalyzer,
        mock_prediction_repo: AsyncMock,
    ) -> None:
        """Test identify_patterns with no data."""
        mock_prediction_repo.get_validated_with_market = AsyncMock(return_value=[])

        patterns = await analyzer.identify_patterns()

        assert patterns == []

    def test_generate_insights(
        self,
        analyzer: PerformanceAnalyzer,
    ) -> None:
        """Test generate_insights method."""
        metrics = PerformanceMetrics(
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=0.6,
            total_pnl=50.0,
            avg_pnl=5.0,
            max_profit=20.0,
            max_loss=-10.0,
            avg_confidence=0.75,
            avg_edge=0.12,
            performance_level=PerformanceLevel.GOOD,
        )

        patterns = [
            PatternInsight(
                pattern_type=PatternType.SUCCESS,
                title="Test pattern",
                description="Test description",
            )
        ]

        insights = analyzer.generate_insights(metrics, patterns, [], [], [])

        assert isinstance(insights, list)
        assert len(insights) > 0

    def test_generate_insights_no_trades(
        self,
        analyzer: PerformanceAnalyzer,
    ) -> None:
        """Test generate_insights with no trades."""
        metrics = PerformanceMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            avg_pnl=0.0,
            max_profit=0.0,
            max_loss=0.0,
            avg_confidence=0.0,
            avg_edge=0.0,
            performance_level=PerformanceLevel.POOR,
        )

        insights = analyzer.generate_insights(metrics, [], [], [], [])

        assert len(insights) > 0
        assert any("No validated trades" in i for i in insights)

    def test_get_improvement_suggestions(
        self,
        analyzer: PerformanceAnalyzer,
    ) -> None:
        """Test get_improvement_suggestions method."""
        metrics = PerformanceMetrics(
            total_trades=10,
            winning_trades=3,  # 30% win rate
            losing_trades=7,
            win_rate=0.3,
            total_pnl=-50.0,
            avg_pnl=-5.0,
            max_profit=10.0,
            max_loss=-30.0,  # Max loss > 2x max profit
            avg_confidence=0.65,  # Low confidence
            avg_edge=0.08,  # Low edge
            performance_level=PerformanceLevel.POOR,
        )

        suggestions = analyzer.get_improvement_suggestions(metrics, [], [], [], [])

        assert isinstance(suggestions, list)
        # Should have suggestions for risk management, win rate, confidence, edge
        assert len(suggestions) >= 3

        # Check priority distribution
        priorities = [s.priority for s in suggestions]
        assert SuggestionPriority.HIGH in priorities

    def test_get_improvement_suggestions_good_performance(
        self,
        analyzer: PerformanceAnalyzer,
    ) -> None:
        """Test get_improvement_suggestions with good performance."""
        metrics = PerformanceMetrics(
            total_trades=10,
            winning_trades=8,
            losing_trades=2,
            win_rate=0.8,
            total_pnl=100.0,
            avg_pnl=10.0,
            max_profit=30.0,
            max_loss=-5.0,
            avg_confidence=0.85,
            avg_edge=0.15,
            performance_level=PerformanceLevel.EXCELLENT,
        )

        suggestions = analyzer.get_improvement_suggestions(metrics, [], [], [], [])

        # Should have fewer suggestions for good performance
        assert isinstance(suggestions, list)

    def test_generate_recommendations(
        self,
        analyzer: PerformanceAnalyzer,
    ) -> None:
        """Test generate_recommendations method."""
        metrics = PerformanceMetrics(
            total_trades=10,
            winning_trades=4,
            losing_trades=6,
            win_rate=0.4,
            total_pnl=-20.0,
            avg_pnl=-2.0,
            max_profit=10.0,
            max_loss=-25.0,
            avg_confidence=0.65,
            avg_edge=0.08,
            performance_level=PerformanceLevel.POOR,
        )

        patterns = [
            PatternInsight(
                pattern_type=PatternType.FAILURE,
                title="Test pattern",
                description="Test description",
                recommendation="Test recommendation",
            )
        ]

        recommendations = analyzer.generate_recommendations(metrics, patterns)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        # Should include the pattern recommendation
        assert "Test recommendation" in recommendations

    def test_generate_recommendations_removes_duplicates(
        self,
        analyzer: PerformanceAnalyzer,
    ) -> None:
        """Test generate_recommendations removes duplicates."""
        metrics = PerformanceMetrics(
            total_trades=10,
            winning_trades=4,
            losing_trades=6,
            win_rate=0.4,
            total_pnl=-20.0,
            avg_pnl=-2.0,
            max_profit=10.0,
            max_loss=-25.0,
            avg_confidence=0.65,
            avg_edge=0.08,
            performance_level=PerformanceLevel.POOR,
        )

        patterns = [
            PatternInsight(
                pattern_type=PatternType.FAILURE,
                title="Pattern 1",
                description="Description 1",
                recommendation="Same recommendation",
            ),
            PatternInsight(
                pattern_type=PatternType.FAILURE,
                title="Pattern 2",
                description="Description 2",
                recommendation="Same recommendation",
            ),
        ]

        recommendations = analyzer.generate_recommendations(metrics, patterns)

        # Count occurrences of "Same recommendation"
        count = recommendations.count("Same recommendation")
        assert count == 1  # Should only appear once

    @pytest.mark.asyncio
    async def test_generate_insight_report(
        self,
        analyzer: PerformanceAnalyzer,
        mock_prediction_repo: AsyncMock,
        mock_trade_repo: AsyncMock,
        mock_position_repo: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Test generate_insight_report method."""
        # Update analyzer to use tmp_path
        analyzer._reports_dir = tmp_path

        pred = Prediction(
            id=1,
            market_id="m1",
            predicted_probability=0.8,
            confidence=0.85,
            edge=0.15,
            is_correct=True,
            validated_at=datetime.now(),
        )

        market = Market(
            id="m1",
            title="Test Market",
            category=MarketCategory.POLITICS,
        )

        mock_prediction_repo.get_validated_with_market = AsyncMock(
            return_value=[(pred, market)]
        )
        mock_trade_repo.get_by_mode = AsyncMock(return_value=[])
        mock_position_repo.get_open_positions = AsyncMock(return_value=[])

        report = await analyzer.generate_insight_report()

        assert isinstance(report, PerformanceInsightReport)
        assert isinstance(report.metrics, PerformanceMetrics)
        assert isinstance(report.patterns, list)
        assert isinstance(report.recommendations, list)
        assert isinstance(report.suggestions, list)

        # Check report file was created
        report_files = list(tmp_path.glob("insights_*.json"))
        assert len(report_files) == 1

    @pytest.mark.asyncio
    async def test_generate_insight_report_creates_directory(
        self,
        analyzer: PerformanceAnalyzer,
        mock_prediction_repo: AsyncMock,
        mock_trade_repo: AsyncMock,
        mock_position_repo: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Test generate_insight_report creates directory if needed."""
        # Use a non-existent subdirectory
        reports_dir = tmp_path / "new_reports"
        analyzer._reports_dir = reports_dir

        mock_prediction_repo.get_validated_with_market = AsyncMock(return_value=[])
        mock_trade_repo.get_by_mode = AsyncMock(return_value=[])
        mock_position_repo.get_open_positions = AsyncMock(return_value=[])

        report = await analyzer.generate_insight_report()

        assert reports_dir.exists()
        assert isinstance(report, PerformanceInsightReport)


class TestPerformanceAnalyzerIntegration:
    """Integration tests for PerformanceAnalyzer."""

    @pytest.fixture
    def mock_prediction_repo(self) -> AsyncMock:
        """Create a mock PredictionRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_trade_repo(self) -> AsyncMock:
        """Create a mock TradeRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_position_repo(self) -> AsyncMock:
        """Create a mock PositionRepository."""
        return AsyncMock()

    @pytest.fixture
    def analyzer(
        self,
        mock_prediction_repo: AsyncMock,
        mock_trade_repo: AsyncMock,
        mock_position_repo: AsyncMock,
    ) -> PerformanceAnalyzer:
        """Create a PerformanceAnalyzer instance for testing."""
        return PerformanceAnalyzer(
            prediction_repo=mock_prediction_repo,
            trade_repo=mock_trade_repo,
            position_repo=mock_position_repo,
            reports_dir="/tmp/test_reports_integration",
        )

    @pytest.mark.asyncio
    async def test_full_analysis_workflow(
        self,
        analyzer: PerformanceAnalyzer,
        mock_prediction_repo: AsyncMock,
        mock_trade_repo: AsyncMock,
        mock_position_repo: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Test the full analysis workflow."""
        analyzer._reports_dir = tmp_path

        # Create varied test data (ensure confidence stays <= 1)
        predictions_markets = [
            (
                Prediction(
                    id=i,
                    market_id=f"m{i}",
                    predicted_probability=min(0.7 + i * 0.03, 0.95),
                    confidence=min(0.75 + i * 0.025, 0.95),
                    edge=min(0.1 + i * 0.05, 0.5),
                    is_correct=i % 3 != 0,  # 2/3 correct
                    validated_at=datetime.now(),
                ),
                Market(
                    id=f"m{i}",
                    title=f"Market {i}",
                    category=[MarketCategory.POLITICS, MarketCategory.CRYPTO][i % 2],
                ),
            )
            for i in range(10)
        ]

        mock_prediction_repo.get_validated_with_market = AsyncMock(
            return_value=predictions_markets
        )
        mock_trade_repo.get_by_mode = AsyncMock(return_value=[])
        mock_position_repo.get_open_positions = AsyncMock(return_value=[])

        # Run full analysis
        report = await analyzer.generate_insight_report()

        # Verify report completeness
        assert report.metrics.total_trades == 10
        assert 0 <= report.metrics.win_rate <= 1
        assert len(report.category_performance) > 0
        assert len(report.confidence_analysis) > 0
        assert len(report.edge_analysis) > 0
        assert len(report.patterns) > 0
        assert len(report.recommendations) > 0
        assert len(report.suggestions) > 0

    @pytest.mark.asyncio
    async def test_performance_level_classification(
        self,
        analyzer: PerformanceAnalyzer,
        mock_prediction_repo: AsyncMock,
        mock_trade_repo: AsyncMock,
        mock_position_repo: AsyncMock,
    ) -> None:
        """Test performance level classification based on win rate."""
        mock_trade_repo.get_by_mode = AsyncMock(return_value=[])
        mock_position_repo.get_open_positions = AsyncMock(return_value=[])

        # Test EXCELLENT (>= 70%)
        excellent_preds = [
            (
                Prediction(
                    id=i,
                    market_id=f"m{i}",
                    predicted_probability=0.8,
                    confidence=0.85,
                    is_correct=True,
                    validated_at=datetime.now(),
                ),
                Market(
                    id=f"m{i}", title=f"Market {i}", category=MarketCategory.POLITICS
                ),
            )
            for i in range(7)
        ] + [
            (
                Prediction(
                    id=i,
                    market_id=f"m{i}",
                    predicted_probability=0.8,
                    confidence=0.85,
                    is_correct=False,
                    validated_at=datetime.now(),
                ),
                Market(
                    id=f"m{i}", title=f"Market {i}", category=MarketCategory.POLITICS
                ),
            )
            for i in range(7, 10)
        ]

        mock_prediction_repo.get_validated_with_market = AsyncMock(
            return_value=excellent_preds
        )

        metrics = await analyzer.analyze_performance()
        assert metrics.performance_level == PerformanceLevel.EXCELLENT
        assert metrics.win_rate == 0.7
