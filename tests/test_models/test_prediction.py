"""Tests for Prediction model.

This module tests the Prediction, PredictionResult models and Recommendation
enum including:
- Recommendation enum values
- PredictionResult model (LLM raw output)
- Prediction model (stored prediction)
- Field validation (probability, confidence range)
- DateTime serialization
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.models import Prediction, PredictionResult, Recommendation


class TestRecommendation:
    """Tests for Recommendation enum."""

    def test_all_recommendations_exist(self) -> None:
        """Test all recommendation values exist."""
        assert Recommendation.BUY_YES.value == "BUY_YES"
        assert Recommendation.BUY_NO.value == "BUY_NO"
        assert Recommendation.NO_TRADE.value == "NO_TRADE"

    def test_recommendation_count(self) -> None:
        """Test total number of recommendations."""
        assert len(Recommendation) == 3

    def test_recommendation_is_str_enum(self) -> None:
        """Test Recommendation is string enum."""
        assert isinstance(Recommendation.BUY_YES, str)


class TestPredictionResult:
    """Tests for PredictionResult model (LLM raw output)."""

    def test_create_result_minimal(self) -> None:
        """Test creating result with required fields only."""
        result = PredictionResult(
            predicted_probability=0.72,
            confidence=0.85,
            reasoning="Strong technical indicators",
            recommendation=Recommendation.BUY_YES,
        )

        assert result.predicted_probability == 0.72
        assert result.confidence == 0.85
        assert result.reasoning == "Strong technical indicators"
        assert result.recommendation == Recommendation.BUY_YES
        assert result.key_assumptions == []

    def test_create_result_full(self) -> None:
        """Test creating result with all fields."""
        result = PredictionResult(
            predicted_probability=0.72,
            confidence=0.85,
            reasoning="Strong technical indicators suggest upward momentum",
            key_assumptions=["Market sentiment positive", "No major news expected"],
            recommendation=Recommendation.BUY_YES,
        )

        assert result.predicted_probability == 0.72
        assert result.confidence == 0.85
        assert result.reasoning == "Strong technical indicators suggest upward momentum"
        assert len(result.key_assumptions) == 2
        assert "Market sentiment positive" in result.key_assumptions
        assert result.recommendation == Recommendation.BUY_YES

    def test_probability_validation_valid(self) -> None:
        """Test valid probability range (0-1)."""
        result = PredictionResult(
            predicted_probability=0.0,
            confidence=0.5,
            reasoning="Test",
            recommendation=Recommendation.NO_TRADE,
        )
        assert result.predicted_probability == 0.0

        result = PredictionResult(
            predicted_probability=1.0,
            confidence=0.5,
            reasoning="Test",
            recommendation=Recommendation.NO_TRADE,
        )
        assert result.predicted_probability == 1.0

    def test_probability_validation_invalid_high(self) -> None:
        """Test probability validation rejects values > 1."""
        with pytest.raises(ValueError):
            PredictionResult(
                predicted_probability=1.5,
                confidence=0.5,
                reasoning="Test",
                recommendation=Recommendation.NO_TRADE,
            )

    def test_probability_validation_invalid_negative(self) -> None:
        """Test probability validation rejects negative values."""
        with pytest.raises(ValueError):
            PredictionResult(
                predicted_probability=-0.1,
                confidence=0.5,
                reasoning="Test",
                recommendation=Recommendation.NO_TRADE,
            )

    def test_confidence_validation_invalid_high(self) -> None:
        """Test confidence validation rejects values > 1."""
        with pytest.raises(ValueError):
            PredictionResult(
                predicted_probability=0.5,
                confidence=1.5,
                reasoning="Test",
                recommendation=Recommendation.NO_TRADE,
            )

    def test_confidence_validation_invalid_negative(self) -> None:
        """Test confidence validation rejects negative values."""
        with pytest.raises(ValueError):
            PredictionResult(
                predicted_probability=0.5,
                confidence=-0.1,
                reasoning="Test",
                recommendation=Recommendation.NO_TRADE,
            )

    def test_reasoning_validation_empty(self) -> None:
        """Test reasoning validation rejects empty strings."""
        with pytest.raises(ValueError):
            PredictionResult(
                predicted_probability=0.5,
                confidence=0.5,
                reasoning="",
                recommendation=Recommendation.NO_TRADE,
            )

    def test_key_assumptions_default_empty_list(self) -> None:
        """Test key_assumptions defaults to empty list."""
        result = PredictionResult(
            predicted_probability=0.5,
            confidence=0.5,
            reasoning="Test",
            recommendation=Recommendation.NO_TRADE,
        )
        assert result.key_assumptions == []
        assert isinstance(result.key_assumptions, list)

    def test_recommendation_from_string(self) -> None:
        """Test recommendation creation from string."""
        result = PredictionResult(
            predicted_probability=0.5,
            confidence=0.5,
            reasoning="Test",
            recommendation="BUY_NO",
        )
        assert result.recommendation == Recommendation.BUY_NO


class TestPrediction:
    """Tests for Prediction model (stored prediction)."""

    def test_create_prediction_minimal(self) -> None:
        """Test creating prediction with required fields only."""
        prediction = Prediction(
            id=1,
            market_id="market-123",
            predicted_probability=0.72,
            confidence=0.85,
        )

        assert prediction.id == 1
        assert prediction.market_id == "market-123"
        assert prediction.predicted_probability == 0.72
        assert prediction.confidence == 0.85
        assert prediction.reasoning is None
        assert prediction.key_assumptions is None
        assert prediction.model_used is None
        assert prediction.recommendation is None
        assert prediction.actual_outcome is None
        assert prediction.is_correct is None
        assert prediction.validated_at is None
        assert prediction.created_at is None

    def test_create_prediction_full(self) -> None:
        """Test creating prediction with all fields."""
        prediction = Prediction(
            id=1,
            market_id="btc-100k-2026",
            predicted_probability=0.72,
            confidence=0.85,
            reasoning="Strong technical indicators",
            key_assumptions=["Trend continuation", "No regulatory changes"],
            model_used="glm-4",
            recommendation=Recommendation.BUY_YES,
            actual_outcome="YES",
            is_correct=True,
            validated_at=datetime(2027, 1, 1, 12, 0, 0),
            created_at=datetime(2026, 2, 15, 10, 30, 0),
        )

        assert prediction.id == 1
        assert prediction.market_id == "btc-100k-2026"
        assert prediction.predicted_probability == 0.72
        assert prediction.confidence == 0.85
        assert prediction.reasoning == "Strong technical indicators"
        assert prediction.key_assumptions == ["Trend continuation", "No regulatory changes"]
        assert prediction.model_used == "glm-4"
        assert prediction.recommendation == Recommendation.BUY_YES
        assert prediction.actual_outcome == "YES"
        assert prediction.is_correct is True
        assert prediction.validated_at == datetime(2027, 1, 1, 12, 0, 0)
        assert prediction.created_at == datetime(2026, 2, 15, 10, 30, 0)

    def test_probability_validation_valid(self) -> None:
        """Test valid probability range (0-1)."""
        prediction = Prediction(
            id=1,
            market_id="test",
            predicted_probability=0.0,
            confidence=0.0,
        )
        assert prediction.predicted_probability == 0.0

        prediction = Prediction(
            id=1,
            market_id="test",
            predicted_probability=1.0,
            confidence=1.0,
        )
        assert prediction.predicted_probability == 1.0

    def test_probability_validation_invalid(self) -> None:
        """Test probability validation rejects invalid values."""
        with pytest.raises(ValueError):
            Prediction(
                id=1,
                market_id="test",
                predicted_probability=1.5,
                confidence=0.5,
            )

    def test_confidence_validation_invalid(self) -> None:
        """Test confidence validation rejects invalid values."""
        with pytest.raises(ValueError):
            Prediction(
                id=1,
                market_id="test",
                predicted_probability=0.5,
                confidence=1.5,
            )

    def test_datetime_serialization(self) -> None:
        """Test datetime serialization to ISO 8601."""
        prediction = Prediction(
            id=1,
            market_id="test",
            predicted_probability=0.5,
            confidence=0.5,
            created_at=datetime(2026, 2, 15, 10, 30, 0),
            validated_at=datetime(2027, 1, 1, 12, 0, 0),
        )

        # model_dump with mode='json' returns ISO strings
        data = prediction.model_dump(mode="json")
        assert data["created_at"] == "2026-02-15T10:30:00"
        assert data["validated_at"] == "2027-01-01T12:00:00"

    def test_is_correct_can_be_false(self) -> None:
        """Test is_correct can be False."""
        prediction = Prediction(
            id=1,
            market_id="test",
            predicted_probability=0.8,
            confidence=0.9,
            is_correct=False,
        )
        assert prediction.is_correct is False

    def test_model_json_export(self) -> None:
        """Test JSON export."""
        prediction = Prediction(
            id=1,
            market_id="test-123",
            predicted_probability=0.72,
            confidence=0.85,
        )
        json_str = prediction.model_dump_json()

        assert '"id":1' in json_str
        assert '"market_id":"test-123"' in json_str
        assert '"predicted_probability":0.72' in json_str

    def test_model_config_validate_assignment(self) -> None:
        """Test that validate_assignment is enabled."""
        prediction = Prediction(
            id=1,
            market_id="test",
            predicted_probability=0.5,
            confidence=0.5,
        )

        # Should validate on assignment
        with pytest.raises(ValueError):
            prediction.predicted_probability = 1.5

        # Valid assignment should work
        prediction.predicted_probability = 0.8
        assert prediction.predicted_probability == 0.8
