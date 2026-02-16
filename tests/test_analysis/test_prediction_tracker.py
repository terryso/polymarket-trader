"""Tests for PredictionTracker.

Story 6.1: 预测结果验证机制
Story 6.2: 准确率统计
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.analysis.prediction_tracker import (
    AccuracyResult,
    AccuracyStatistics,
    CategoryAccuracy,
    ConfidenceAccuracy,
    DateRangeAccuracy,
    PredictionTracker,
    ValidationResult,
)
from src.models.market import Market, MarketCategory
from src.models.prediction import Prediction, Recommendation


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_creation(self) -> None:
        """Test ValidationResult creation with all fields."""
        result = ValidationResult(
            prediction_id=1,
            is_validated=True,
            is_correct=True,
            actual_outcome="YES",
            reason=None,
        )

        assert result.prediction_id == 1
        assert result.is_validated is True
        assert result.is_correct is True
        assert result.actual_outcome == "YES"
        assert result.reason is None

    def test_validation_result_with_reason(self) -> None:
        """Test ValidationResult with reason field."""
        result = ValidationResult(
            prediction_id=1,
            is_validated=False,
            is_correct=None,
            actual_outcome="YES",
            reason="NO_TRADE recommendation not counted",
        )

        assert result.is_validated is False
        assert result.is_correct is None
        assert result.reason == "NO_TRADE recommendation not counted"


class TestAccuracyResult:
    """Tests for AccuracyResult dataclass."""

    def test_accuracy_result_creation(self) -> None:
        """Test AccuracyResult creation."""
        result = AccuracyResult(
            total=10,
            correct=7,
            accuracy=0.7,
        )

        assert result.total == 10
        assert result.correct == 7
        assert result.accuracy == 0.7

    def test_accuracy_result_no_predictions(self) -> None:
        """Test AccuracyResult with no predictions."""
        result = AccuracyResult(
            total=0,
            correct=0,
            accuracy=None,
        )

        assert result.total == 0
        assert result.correct == 0
        assert result.accuracy is None


class TestPredictionTracker:
    """Tests for PredictionTracker class."""

    @pytest.fixture
    def mock_market_repo(self) -> AsyncMock:
        """Create a mock MarketRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_prediction_repo(self) -> AsyncMock:
        """Create a mock PredictionRepository."""
        return AsyncMock()

    @pytest.fixture
    def tracker(
        self, mock_market_repo: AsyncMock, mock_prediction_repo: AsyncMock
    ) -> PredictionTracker:
        """Create a PredictionTracker instance for testing."""
        return PredictionTracker(mock_market_repo, mock_prediction_repo)

    @pytest.fixture
    def sample_prediction_buy_yes(self) -> Prediction:
        """Create a sample Prediction with BUY_YES recommendation."""
        return Prediction(
            id=1,
            market_id="test-market-1",
            predicted_probability=0.75,
            confidence=0.85,
            reasoning="Strong indicators point to YES",
            recommendation=Recommendation.BUY_YES,
        )

    @pytest.fixture
    def sample_prediction_buy_no(self) -> Prediction:
        """Create a sample Prediction with BUY_NO recommendation."""
        return Prediction(
            id=2,
            market_id="test-market-1",
            predicted_probability=0.25,
            confidence=0.80,
            reasoning="Indicators point to NO",
            recommendation=Recommendation.BUY_NO,
        )

    @pytest.fixture
    def sample_prediction_no_trade(self) -> Prediction:
        """Create a sample Prediction with NO_TRADE recommendation."""
        return Prediction(
            id=3,
            market_id="test-market-1",
            predicted_probability=0.50,
            confidence=0.60,
            reasoning="Market is uncertain",
            recommendation=Recommendation.NO_TRADE,
        )

    @pytest.fixture
    def sample_prediction_no_recommendation(self) -> Prediction:
        """Create a sample Prediction without recommendation."""
        return Prediction(
            id=4,
            market_id="test-market-1",
            predicted_probability=0.65,
            confidence=0.70,
            reasoning="Probability based prediction",
            recommendation=None,
        )

    @pytest.fixture
    def sample_resolved_market_yes(self) -> Market:
        """Create a sample resolved Market with YES outcome."""
        return Market(
            id="test-market-1",
            title="Will X happen?",
            resolution_status="RESOLVED",
            resolution_outcome="YES",
        )

    @pytest.fixture
    def sample_resolved_market_no(self) -> Market:
        """Create a sample resolved Market with NO outcome."""
        return Market(
            id="test-market-2",
            title="Will Y happen?",
            resolution_status="RESOLVED",
            resolution_outcome="NO",
        )

    # ==================== validate_prediction tests ====================

    def test_validate_prediction_correct_yes(
        self,
        tracker: PredictionTracker,
        sample_prediction_buy_yes: Prediction,
    ) -> None:
        """Test validating a correct YES prediction."""
        result = tracker.validate_prediction(sample_prediction_buy_yes, "YES")

        assert result.is_validated is True
        assert result.is_correct is True
        assert result.actual_outcome == "YES"
        assert result.reason is None

    def test_validate_prediction_incorrect_yes(
        self,
        tracker: PredictionTracker,
        sample_prediction_buy_yes: Prediction,
    ) -> None:
        """Test validating an incorrect YES prediction (actual was NO)."""
        result = tracker.validate_prediction(sample_prediction_buy_yes, "NO")

        assert result.is_validated is True
        assert result.is_correct is False
        assert result.actual_outcome == "NO"

    def test_validate_prediction_correct_no(
        self,
        tracker: PredictionTracker,
        sample_prediction_buy_no: Prediction,
    ) -> None:
        """Test validating a correct NO prediction."""
        result = tracker.validate_prediction(sample_prediction_buy_no, "NO")

        assert result.is_validated is True
        assert result.is_correct is True
        assert result.actual_outcome == "NO"

    def test_validate_prediction_incorrect_no(
        self,
        tracker: PredictionTracker,
        sample_prediction_buy_no: Prediction,
    ) -> None:
        """Test validating an incorrect NO prediction (actual was YES)."""
        result = tracker.validate_prediction(sample_prediction_buy_no, "YES")

        assert result.is_validated is True
        assert result.is_correct is False
        assert result.actual_outcome == "YES"

    def test_validate_prediction_no_trade(
        self,
        tracker: PredictionTracker,
        sample_prediction_no_trade: Prediction,
    ) -> None:
        """Test that NO_TRADE recommendation is not validated."""
        result = tracker.validate_prediction(sample_prediction_no_trade, "YES")

        assert result.is_validated is False
        assert result.is_correct is None
        assert "NO_TRADE" in result.reason or "neutral" in result.reason

    def test_validate_prediction_uses_probability_when_no_recommendation(
        self,
        tracker: PredictionTracker,
        sample_prediction_no_recommendation: Prediction,
    ) -> None:
        """Test that probability is used when recommendation is None."""
        # Probability 0.65 > 0.5 means YES prediction
        result = tracker.validate_prediction(sample_prediction_no_recommendation, "YES")

        assert result.is_validated is True
        assert result.is_correct is True

    def test_validate_prediction_uses_probability_for_no(
        self, tracker: PredictionTracker
    ) -> None:
        """Test that probability < 0.5 predicts NO."""
        prediction = Prediction(
            id=1,
            market_id="test-market",
            predicted_probability=0.35,  # < 0.5 means NO
            confidence=0.80,
            recommendation=None,
        )

        result = tracker.validate_prediction(prediction, "NO")

        assert result.is_validated is True
        assert result.is_correct is True

    def test_validate_prediction_neutral_probability(
        self, tracker: PredictionTracker
    ) -> None:
        """Test that probability = 0.5 is neutral (not counted)."""
        prediction = Prediction(
            id=1,
            market_id="test-market",
            predicted_probability=0.5,  # Exactly 0.5 = neutral
            confidence=0.80,
            recommendation=None,
        )

        result = tracker.validate_prediction(prediction, "YES")

        assert result.is_validated is False
        assert result.is_correct is None

    def test_validate_prediction_normalizes_outcome(
        self,
        tracker: PredictionTracker,
        sample_prediction_buy_yes: Prediction,
    ) -> None:
        """Test that outcome is normalized to uppercase."""
        result = tracker.validate_prediction(sample_prediction_buy_yes, "yes")

        assert result.actual_outcome == "YES"
        assert result.is_correct is True

    # ==================== calculate_accuracy tests ====================

    def test_calculate_accuracy_all_correct(self, tracker: PredictionTracker) -> None:
        """Test accuracy calculation with all correct predictions."""
        predictions = [
            Prediction(
                id=i,
                market_id=f"market-{i}",
                predicted_probability=0.7,
                confidence=0.8,
                is_correct=True,
            )
            for i in range(5)
        ]

        result = tracker.calculate_accuracy(predictions)

        assert result.total == 5
        assert result.correct == 5
        assert result.accuracy == 1.0

    def test_calculate_accuracy_all_incorrect(self, tracker: PredictionTracker) -> None:
        """Test accuracy calculation with all incorrect predictions."""
        predictions = [
            Prediction(
                id=i,
                market_id=f"market-{i}",
                predicted_probability=0.7,
                confidence=0.8,
                is_correct=False,
            )
            for i in range(5)
        ]

        result = tracker.calculate_accuracy(predictions)

        assert result.total == 5
        assert result.correct == 0
        assert result.accuracy == 0.0

    def test_calculate_accuracy_mixed(self, tracker: PredictionTracker) -> None:
        """Test accuracy calculation with mixed predictions."""
        predictions = [
            Prediction(
                id=1,
                market_id="m1",
                predicted_probability=0.7,
                confidence=0.8,
                is_correct=True,
            ),
            Prediction(
                id=2,
                market_id="m2",
                predicted_probability=0.6,
                confidence=0.7,
                is_correct=False,
            ),
            Prediction(
                id=3,
                market_id="m3",
                predicted_probability=0.8,
                confidence=0.9,
                is_correct=True,
            ),
        ]

        result = tracker.calculate_accuracy(predictions)

        assert result.total == 3
        assert result.correct == 2
        assert result.accuracy == 2 / 3

    def test_calculate_accuracy_empty(self, tracker: PredictionTracker) -> None:
        """Test accuracy calculation with empty list."""
        result = tracker.calculate_accuracy([])

        assert result.total == 0
        assert result.correct == 0
        assert result.accuracy is None

    def test_calculate_accuracy_filters_unvalidated(
        self, tracker: PredictionTracker
    ) -> None:
        """Test that predictions with is_correct=None are excluded."""
        predictions = [
            Prediction(
                id=1,
                market_id="m1",
                predicted_probability=0.7,
                confidence=0.8,
                is_correct=True,
            ),
            Prediction(
                id=2,
                market_id="m2",
                predicted_probability=0.6,
                confidence=0.7,
                is_correct=None,  # Unvalidated
            ),
            Prediction(
                id=3,
                market_id="m3",
                predicted_probability=0.8,
                confidence=0.9,
                is_correct=False,
            ),
        ]

        result = tracker.calculate_accuracy(predictions)

        assert result.total == 2  # Only validated predictions
        assert result.correct == 1
        assert result.accuracy == 0.5

    def test_calculate_accuracy_all_unvalidated(
        self, tracker: PredictionTracker
    ) -> None:
        """Test accuracy when all predictions are unvalidated."""
        predictions = [
            Prediction(
                id=i,
                market_id=f"market-{i}",
                predicted_probability=0.7,
                confidence=0.8,
                is_correct=None,
            )
            for i in range(5)
        ]

        result = tracker.calculate_accuracy(predictions)

        assert result.total == 0
        assert result.accuracy is None

    # ==================== check_resolved_markets tests ====================

    @pytest.mark.asyncio
    async def test_check_resolved_markets_no_markets(
        self,
        tracker: PredictionTracker,
        mock_market_repo: AsyncMock,
    ) -> None:
        """Test check_resolved_markets when no resolved markets exist."""
        mock_market_repo.get_resolved_markets = AsyncMock(return_value=[])

        results = await tracker.check_resolved_markets()

        assert results == []

    @pytest.mark.asyncio
    async def test_check_resolved_markets_validates_predictions(
        self,
        tracker: PredictionTracker,
        mock_market_repo: AsyncMock,
        mock_prediction_repo: AsyncMock,
        sample_resolved_market_yes: Market,
        sample_prediction_buy_yes: Prediction,
    ) -> None:
        """Test check_resolved_markets validates predictions correctly."""
        mock_market_repo.get_resolved_markets = AsyncMock(
            return_value=[sample_resolved_market_yes]
        )
        mock_prediction_repo.get_predictions_by_market = AsyncMock(
            return_value=[sample_prediction_buy_yes]
        )
        mock_prediction_repo.update_prediction_result = AsyncMock(return_value=True)

        results = await tracker.check_resolved_markets()

        assert len(results) == 1
        assert results[0].is_correct is True
        mock_prediction_repo.update_prediction_result.assert_called_once_with(
            prediction_id=1,
            actual_outcome="YES",
            is_correct=True,
        )

    @pytest.mark.asyncio
    async def test_check_resolved_markets_skips_already_validated(
        self,
        tracker: PredictionTracker,
        mock_market_repo: AsyncMock,
        mock_prediction_repo: AsyncMock,
        sample_resolved_market_yes: Market,
    ) -> None:
        """Test that already validated predictions are skipped."""
        validated_prediction = Prediction(
            id=1,
            market_id="test-market-1",
            predicted_probability=0.75,
            confidence=0.85,
            recommendation=Recommendation.BUY_YES,
            validated_at=datetime.utcnow(),  # Already validated
        )

        mock_market_repo.get_resolved_markets = AsyncMock(
            return_value=[sample_resolved_market_yes]
        )
        mock_prediction_repo.get_predictions_by_market = AsyncMock(
            return_value=[validated_prediction]
        )

        results = await tracker.check_resolved_markets()

        assert len(results) == 0
        mock_prediction_repo.update_prediction_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_resolved_markets_skips_no_trade(
        self,
        tracker: PredictionTracker,
        mock_market_repo: AsyncMock,
        mock_prediction_repo: AsyncMock,
        sample_resolved_market_yes: Market,
        sample_prediction_no_trade: Prediction,
    ) -> None:
        """Test that NO_TRADE predictions are not counted."""
        mock_market_repo.get_resolved_markets = AsyncMock(
            return_value=[sample_resolved_market_yes]
        )
        mock_prediction_repo.get_predictions_by_market = AsyncMock(
            return_value=[sample_prediction_no_trade]
        )

        results = await tracker.check_resolved_markets()

        assert len(results) == 0
        mock_prediction_repo.update_prediction_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_resolved_markets_skips_market_without_outcome(
        self,
        tracker: PredictionTracker,
        mock_market_repo: AsyncMock,
        mock_prediction_repo: AsyncMock,
    ) -> None:
        """Test that markets without resolution_outcome are skipped."""
        market_no_outcome = Market(
            id="test-market-1",
            title="Will X happen?",
            resolution_status="RESOLVED",
            resolution_outcome=None,  # No outcome
        )

        mock_market_repo.get_resolved_markets = AsyncMock(
            return_value=[market_no_outcome]
        )

        results = await tracker.check_resolved_markets()

        assert len(results) == 0
        mock_prediction_repo.get_predictions_by_market.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_resolved_markets_handles_update_failure(
        self,
        tracker: PredictionTracker,
        mock_market_repo: AsyncMock,
        mock_prediction_repo: AsyncMock,
        sample_resolved_market_yes: Market,
        sample_prediction_buy_yes: Prediction,
    ) -> None:
        """Test that update failures are handled gracefully."""
        mock_market_repo.get_resolved_markets = AsyncMock(
            return_value=[sample_resolved_market_yes]
        )
        mock_prediction_repo.get_predictions_by_market = AsyncMock(
            return_value=[sample_prediction_buy_yes]
        )
        mock_prediction_repo.update_prediction_result = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Should not raise exception, just log error
        results = await tracker.check_resolved_markets()

        assert len(results) == 0  # Failed update not included in results

    @pytest.mark.asyncio
    async def test_check_resolved_markets_multiple_markets(
        self,
        tracker: PredictionTracker,
        mock_market_repo: AsyncMock,
        mock_prediction_repo: AsyncMock,
        sample_resolved_market_yes: Market,
        sample_resolved_market_no: Market,
        sample_prediction_buy_yes: Prediction,
        sample_prediction_buy_no: Prediction,
    ) -> None:
        """Test processing multiple resolved markets."""
        mock_market_repo.get_resolved_markets = AsyncMock(
            return_value=[sample_resolved_market_yes, sample_resolved_market_no]
        )

        # First market has YES outcome, second has NO
        def get_predictions_by_market(market_id: str) -> list[Prediction]:
            if market_id == "test-market-1":
                return [sample_prediction_buy_yes]
            elif market_id == "test-market-2":
                return [sample_prediction_buy_no]
            return []

        mock_prediction_repo.get_predictions_by_market = AsyncMock(
            side_effect=get_predictions_by_market
        )
        mock_prediction_repo.update_prediction_result = AsyncMock(return_value=True)

        results = await tracker.check_resolved_markets()

        assert len(results) == 2
        # First prediction: BUY_YES, actual YES = correct
        assert results[0].is_correct is True
        # Second prediction: BUY_NO, actual NO = correct
        assert results[1].is_correct is True

    @pytest.mark.asyncio
    async def test_check_resolved_markets_prediction_without_id(
        self,
        tracker: PredictionTracker,
        mock_market_repo: AsyncMock,
        mock_prediction_repo: AsyncMock,
        sample_resolved_market_yes: Market,
    ) -> None:
        """Test that predictions without ID are skipped."""
        prediction_no_id = Prediction(
            id=None,  # No ID
            market_id="test-market-1",
            predicted_probability=0.75,
            confidence=0.85,
            recommendation=Recommendation.BUY_YES,
        )

        mock_market_repo.get_resolved_markets = AsyncMock(
            return_value=[sample_resolved_market_yes]
        )
        mock_prediction_repo.get_predictions_by_market = AsyncMock(
            return_value=[prediction_no_id]
        )

        results = await tracker.check_resolved_markets()

        assert len(results) == 0

    # ==================== _get_prediction_direction tests ====================

    def test_get_prediction_direction_buy_yes(self, tracker: PredictionTracker) -> None:
        """Test direction for BUY_YES recommendation."""
        prediction = Prediction(
            id=1,
            market_id="test",
            predicted_probability=0.5,
            confidence=0.8,
            recommendation=Recommendation.BUY_YES,
        )

        direction = tracker._get_prediction_direction(prediction)

        assert direction == "YES"

    def test_get_prediction_direction_buy_no(self, tracker: PredictionTracker) -> None:
        """Test direction for BUY_NO recommendation."""
        prediction = Prediction(
            id=1,
            market_id="test",
            predicted_probability=0.5,
            confidence=0.8,
            recommendation=Recommendation.BUY_NO,
        )

        direction = tracker._get_prediction_direction(prediction)

        assert direction == "NO"

    def test_get_prediction_direction_no_trade(
        self, tracker: PredictionTracker
    ) -> None:
        """Test direction for NO_TRADE recommendation."""
        prediction = Prediction(
            id=1,
            market_id="test",
            predicted_probability=0.5,
            confidence=0.8,
            recommendation=Recommendation.NO_TRADE,
        )

        direction = tracker._get_prediction_direction(prediction)

        assert direction is None

    def test_get_prediction_direction_probability_yes(
        self, tracker: PredictionTracker
    ) -> None:
        """Test direction using probability > 0.5."""
        prediction = Prediction(
            id=1,
            market_id="test",
            predicted_probability=0.75,
            confidence=0.8,
            recommendation=None,
        )

        direction = tracker._get_prediction_direction(prediction)

        assert direction == "YES"

    def test_get_prediction_direction_probability_no(
        self, tracker: PredictionTracker
    ) -> None:
        """Test direction using probability < 0.5."""
        prediction = Prediction(
            id=1,
            market_id="test",
            predicted_probability=0.25,
            confidence=0.8,
            recommendation=None,
        )

        direction = tracker._get_prediction_direction(prediction)

        assert direction == "NO"

    def test_get_prediction_direction_probability_neutral(
        self, tracker: PredictionTracker
    ) -> None:
        """Test direction using probability = 0.5 (neutral)."""
        prediction = Prediction(
            id=1,
            market_id="test",
            predicted_probability=0.5,
            confidence=0.8,
            recommendation=None,
        )

        direction = tracker._get_prediction_direction(prediction)

        assert direction is None

    def test_get_prediction_direction_recommendation_overrides_probability(
        self, tracker: PredictionTracker
    ) -> None:
        """Test that recommendation takes precedence over probability."""
        # Probability says NO (0.25), but recommendation says YES
        prediction = Prediction(
            id=1,
            market_id="test",
            predicted_probability=0.25,
            confidence=0.8,
            recommendation=Recommendation.BUY_YES,
        )

        direction = tracker._get_prediction_direction(prediction)

        assert direction == "YES"  # Recommendation wins


# ==================== Story 6.2: 准确率统计测试 ====================


class TestAccuracyStatisticsDataclass:
    """Tests for AccuracyStatistics dataclass."""

    def test_accuracy_statistics_creation(self) -> None:
        """Test AccuracyStatistics creation with all fields."""
        stats = AccuracyStatistics(
            total=10,
            correct=7,
            incorrect=3,
            accuracy=0.7,
        )

        assert stats.total == 10
        assert stats.correct == 7
        assert stats.incorrect == 3
        assert stats.accuracy == 0.7

    def test_accuracy_statistics_no_predictions(self) -> None:
        """Test AccuracyStatistics with no predictions."""
        stats = AccuracyStatistics(
            total=0,
            correct=0,
            incorrect=0,
            accuracy=None,
        )

        assert stats.total == 0
        assert stats.accuracy is None


class TestCategoryAccuracyDataclass:
    """Tests for CategoryAccuracy dataclass."""

    def test_category_accuracy_creation(self) -> None:
        """Test CategoryAccuracy creation."""
        cat_accuracy = CategoryAccuracy(
            category="politics",
            total=5,
            correct=3,
            accuracy=0.6,
        )

        assert cat_accuracy.category == "politics"
        assert cat_accuracy.total == 5
        assert cat_accuracy.correct == 3
        assert cat_accuracy.accuracy == 0.6


class TestConfidenceAccuracyDataclass:
    """Tests for ConfidenceAccuracy dataclass."""

    def test_confidence_accuracy_creation(self) -> None:
        """Test ConfidenceAccuracy creation."""
        conf_accuracy = ConfidenceAccuracy(
            confidence_range="0.8-0.9",
            total=10,
            correct=8,
            accuracy=0.8,
        )

        assert conf_accuracy.confidence_range == "0.8-0.9"
        assert conf_accuracy.total == 10
        assert conf_accuracy.correct == 8
        assert conf_accuracy.accuracy == 0.8


class TestDateRangeAccuracyDataclass:
    """Tests for DateRangeAccuracy dataclass."""

    def test_date_range_accuracy_creation(self) -> None:
        """Test DateRangeAccuracy creation."""
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31)

        date_accuracy = DateRangeAccuracy(
            start_date=start,
            end_date=end,
            total=5,
            correct=4,
            accuracy=0.8,
        )

        assert date_accuracy.start_date == start
        assert date_accuracy.end_date == end
        assert date_accuracy.total == 5
        assert date_accuracy.correct == 4
        assert date_accuracy.accuracy == 0.8


class TestPredictionTrackerAccuracy:
    """Tests for PredictionTracker accuracy statistics methods."""

    @pytest.fixture
    def mock_market_repo(self) -> AsyncMock:
        """Create a mock MarketRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_prediction_repo(self) -> AsyncMock:
        """Create a mock PredictionRepository."""
        return AsyncMock()

    @pytest.fixture
    def tracker(
        self, mock_market_repo: AsyncMock, mock_prediction_repo: AsyncMock
    ) -> PredictionTracker:
        """Create a PredictionTracker instance for testing."""
        return PredictionTracker(mock_market_repo, mock_prediction_repo)

    # ==================== get_overall_accuracy tests ====================

    @pytest.mark.asyncio
    async def test_get_overall_accuracy(
        self, tracker: PredictionTracker, mock_prediction_repo: AsyncMock
    ) -> None:
        """Test getting overall accuracy."""
        mock_prediction_repo.get_all_validated = AsyncMock(
            return_value=[
                Prediction(
                    id=1,
                    market_id="m1",
                    predicted_probability=0.7,
                    confidence=0.8,
                    is_correct=True,
                ),
                Prediction(
                    id=2,
                    market_id="m2",
                    predicted_probability=0.6,
                    confidence=0.7,
                    is_correct=False,
                ),
                Prediction(
                    id=3,
                    market_id="m3",
                    predicted_probability=0.8,
                    confidence=0.9,
                    is_correct=True,
                ),
            ]
        )

        result = await tracker.get_overall_accuracy()

        assert result.total == 3
        assert result.correct == 2
        assert result.incorrect == 1
        assert result.accuracy == 2 / 3

    @pytest.mark.asyncio
    async def test_get_overall_accuracy_empty(
        self, tracker: PredictionTracker, mock_prediction_repo: AsyncMock
    ) -> None:
        """Test getting overall accuracy with no validated predictions."""
        mock_prediction_repo.get_all_validated = AsyncMock(return_value=[])

        result = await tracker.get_overall_accuracy()

        assert result.total == 0
        assert result.correct == 0
        assert result.incorrect == 0
        assert result.accuracy is None

    @pytest.mark.asyncio
    async def test_get_overall_accuracy_all_correct(
        self, tracker: PredictionTracker, mock_prediction_repo: AsyncMock
    ) -> None:
        """Test getting overall accuracy when all predictions are correct."""
        mock_prediction_repo.get_all_validated = AsyncMock(
            return_value=[
                Prediction(
                    id=i,
                    market_id=f"m{i}",
                    predicted_probability=0.7,
                    confidence=0.8,
                    is_correct=True,
                )
                for i in range(5)
            ]
        )

        result = await tracker.get_overall_accuracy()

        assert result.total == 5
        assert result.correct == 5
        assert result.incorrect == 0
        assert result.accuracy == 1.0

    # ==================== get_accuracy_by_category tests ====================

    @pytest.mark.asyncio
    async def test_get_accuracy_by_category(
        self, tracker: PredictionTracker, mock_prediction_repo: AsyncMock
    ) -> None:
        """Test getting accuracy by category."""
        mock_prediction_repo.get_validated_with_market = AsyncMock(
            return_value=[
                (
                    Prediction(
                        id=1,
                        market_id="m1",
                        predicted_probability=0.7,
                        confidence=0.8,
                        is_correct=True,
                    ),
                    Market(
                        id="m1",
                        title="Test 1",
                        category=MarketCategory.POLITICS,
                    ),
                ),
                (
                    Prediction(
                        id=2,
                        market_id="m2",
                        predicted_probability=0.6,
                        confidence=0.7,
                        is_correct=False,
                    ),
                    Market(
                        id="m2",
                        title="Test 2",
                        category=MarketCategory.POLITICS,
                    ),
                ),
                (
                    Prediction(
                        id=3,
                        market_id="m3",
                        predicted_probability=0.8,
                        confidence=0.9,
                        is_correct=True,
                    ),
                    Market(
                        id="m3",
                        title="Test 3",
                        category=MarketCategory.CRYPTO,
                    ),
                ),
            ]
        )

        results = await tracker.get_accuracy_by_category()

        assert len(results) == 2
        # Results should be sorted by total (descending)
        politics = next(r for r in results if r.category == "politics")
        assert politics.total == 2
        assert politics.correct == 1
        assert politics.accuracy == 0.5

        crypto = next(r for r in results if r.category == "crypto")
        assert crypto.total == 1
        assert crypto.correct == 1
        assert crypto.accuracy == 1.0

    @pytest.mark.asyncio
    async def test_get_accuracy_by_category_empty(
        self, tracker: PredictionTracker, mock_prediction_repo: AsyncMock
    ) -> None:
        """Test getting accuracy by category with no validated predictions."""
        mock_prediction_repo.get_validated_with_market = AsyncMock(return_value=[])

        results = await tracker.get_accuracy_by_category()

        assert results == []

    @pytest.mark.asyncio
    async def test_get_accuracy_by_category_no_category(
        self, tracker: PredictionTracker, mock_prediction_repo: AsyncMock
    ) -> None:
        """Test getting accuracy by category when market has no category."""
        mock_prediction_repo.get_validated_with_market = AsyncMock(
            return_value=[
                (
                    Prediction(
                        id=1,
                        market_id="m1",
                        predicted_probability=0.7,
                        confidence=0.8,
                        is_correct=True,
                    ),
                    Market(
                        id="m1",
                        title="Test 1",
                        category=None,  # No category
                    ),
                ),
            ]
        )

        results = await tracker.get_accuracy_by_category()

        assert len(results) == 1
        assert results[0].category == "other"
        assert results[0].total == 1

    # ==================== get_accuracy_by_date_range tests ====================

    @pytest.mark.asyncio
    async def test_get_accuracy_by_date_range(
        self, tracker: PredictionTracker, mock_prediction_repo: AsyncMock
    ) -> None:
        """Test getting accuracy by date range."""
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31)

        mock_prediction_repo.get_validated_by_date_range = AsyncMock(
            return_value=[
                Prediction(
                    id=1,
                    market_id="m1",
                    predicted_probability=0.7,
                    confidence=0.8,
                    is_correct=True,
                ),
                Prediction(
                    id=2,
                    market_id="m2",
                    predicted_probability=0.6,
                    confidence=0.7,
                    is_correct=True,
                ),
            ]
        )

        result = await tracker.get_accuracy_by_date_range(start, end)

        assert result.start_date == start
        assert result.end_date == end
        assert result.total == 2
        assert result.correct == 2
        assert result.accuracy == 1.0

    @pytest.mark.asyncio
    async def test_get_accuracy_by_date_range_empty(
        self, tracker: PredictionTracker, mock_prediction_repo: AsyncMock
    ) -> None:
        """Test getting accuracy by date range with no predictions."""
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31)

        mock_prediction_repo.get_validated_by_date_range = AsyncMock(return_value=[])

        result = await tracker.get_accuracy_by_date_range(start, end)

        assert result.total == 0
        assert result.accuracy is None

    # ======== get_confidence_accuracy_correlation tests ========

    @pytest.mark.asyncio
    async def test_get_confidence_accuracy_correlation(
        self, tracker: PredictionTracker, mock_prediction_repo: AsyncMock
    ) -> None:
        """Test getting confidence-accuracy correlation."""
        mock_prediction_repo.get_all_validated = AsyncMock(
            return_value=[
                Prediction(
                    id=1,
                    market_id="m1",
                    predicted_probability=0.7,
                    confidence=0.85,  # 0.8-0.9 range
                    is_correct=True,
                ),
                Prediction(
                    id=2,
                    market_id="m2",
                    predicted_probability=0.6,
                    confidence=0.75,  # 0.7-0.8 range
                    is_correct=False,
                ),
                Prediction(
                    id=3,
                    market_id="m3",
                    predicted_probability=0.8,
                    confidence=0.95,  # 0.9-1.0 range
                    is_correct=True,
                ),
            ]
        )

        results = await tracker.get_confidence_accuracy_correlation()

        assert len(results) == 3

        # Check 0.8-0.9 range
        high_conf = next((r for r in results if r.confidence_range == "0.8-0.9"), None)
        assert high_conf is not None
        assert high_conf.total == 1
        assert high_conf.accuracy == 1.0

        # Check 0.7-0.8 range
        mid_conf = next((r for r in results if r.confidence_range == "0.7-0.8"), None)
        assert mid_conf is not None
        assert mid_conf.total == 1
        assert mid_conf.accuracy == 0.0

    @pytest.mark.asyncio
    async def test_get_confidence_accuracy_correlation_empty(
        self, tracker: PredictionTracker, mock_prediction_repo: AsyncMock
    ) -> None:
        """Test getting confidence-accuracy correlation with no predictions."""
        mock_prediction_repo.get_all_validated = AsyncMock(return_value=[])

        results = await tracker.get_confidence_accuracy_correlation()

        assert results == []

    @pytest.mark.asyncio
    async def test_get_confidence_accuracy_correlation_single_range(
        self, tracker: PredictionTracker, mock_prediction_repo: AsyncMock
    ) -> None:
        """Test correlation when predictions only exist in one range."""
        mock_prediction_repo.get_all_validated = AsyncMock(
            return_value=[
                Prediction(
                    id=i,
                    market_id=f"m{i}",
                    predicted_probability=0.7,
                    confidence=0.92,  # All in 0.9-1.0 range
                    is_correct=True,
                )
                for i in range(3)
            ]
        )

        results = await tracker.get_confidence_accuracy_correlation()

        assert len(results) == 1
        assert results[0].confidence_range == "0.9-1.0"
        assert results[0].total == 3

    @pytest.mark.asyncio
    async def test_get_confidence_accuracy_correlation_boundary(
        self, tracker: PredictionTracker, mock_prediction_repo: AsyncMock
    ) -> None:
        """Test correlation with confidence at range boundaries."""
        mock_prediction_repo.get_all_validated = AsyncMock(
            return_value=[
                Prediction(
                    id=1,
                    market_id="m1",
                    predicted_probability=0.7,
                    confidence=0.8,  # Exactly at 0.8 boundary
                    is_correct=True,
                ),
                Prediction(
                    id=2,
                    market_id="m2",
                    predicted_probability=0.6,
                    confidence=0.9,  # Exactly at 0.9 boundary
                    is_correct=False,
                ),
            ]
        )

        results = await tracker.get_confidence_accuracy_correlation()

        # 0.8 should be in 0.8-0.9 range (half-open interval [0.8, 0.9))
        conf_08 = next((r for r in results if r.confidence_range == "0.8-0.9"), None)
        assert conf_08 is not None
        assert conf_08.total == 1

        # 0.9 should be in 0.9-1.0 range
        conf_09 = next((r for r in results if r.confidence_range == "0.9-1.0"), None)
        assert conf_09 is not None
        assert conf_09.total == 1
