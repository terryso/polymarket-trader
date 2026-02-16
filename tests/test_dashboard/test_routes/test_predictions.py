"""Tests for prediction API routes.

This module contains tests for the prediction data API endpoints,
including list, detail, and accuracy endpoints with pagination and filtering.

Story 7.4: 预测与统计 API
"""

from datetime import datetime
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.models.prediction import Prediction, Recommendation


@pytest.fixture
def sample_predictions() -> list[Prediction]:
    """Create sample predictions for testing."""
    return [
        Prediction(
            id=1,
            market_id="market-001",
            predicted_probability=0.72,
            confidence=0.85,
            reasoning="Strong technical indicators suggest upward momentum",
            key_assumptions=["Market sentiment remains positive", "No major regulatory changes"],
            model_used="glm-4",
            recommendation=Recommendation.BUY_YES,
            actual_outcome=None,
            is_correct=None,
            validated_at=None,
            created_at=datetime(2026, 2, 15, 10, 0, 0),
        ),
        Prediction(
            id=2,
            market_id="market-002",
            predicted_probability=0.35,
            confidence=0.78,
            reasoning="Historical patterns indicate low probability",
            key_assumptions=["Economic conditions remain stable"],
            model_used="glm-4",
            recommendation=Recommendation.BUY_NO,
            actual_outcome="YES",
            is_correct=False,
            validated_at=datetime(2026, 2, 16, 12, 0, 0),
            created_at=datetime(2026, 2, 14, 9, 0, 0),
        ),
        Prediction(
            id=3,
            market_id="market-003",
            predicted_probability=0.90,
            confidence=0.92,
            reasoning="Overwhelming evidence supports this outcome",
            key_assumptions=["Current trends continue"],
            model_used="glm-4",
            recommendation=Recommendation.BUY_YES,
            actual_outcome="YES",
            is_correct=True,
            validated_at=datetime(2026, 2, 17, 14, 0, 0),
            created_at=datetime(2026, 2, 13, 8, 0, 0),
        ),
    ]


@pytest.fixture
def mock_prediction_repo() -> MagicMock:
    """Create a mock PredictionRepository for testing."""
    repo = MagicMock()
    repo.get_all = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_validated_predictions = AsyncMock(return_value=[])
    repo.get_unvalidated_predictions = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def client(mock_prediction_repo: MagicMock) -> Generator[TestClient, None, None]:
    """Create test client with mocked dependencies."""
    with patch("src.dashboard.app.init_db", new_callable=AsyncMock):
        with patch("src.dashboard.app.close_db", new_callable=AsyncMock):
            def mock_get_prediction_repository() -> MagicMock:
                return mock_prediction_repo

            from src.dashboard.app import app
            from src.dashboard.routes.predictions import get_prediction_repository

            app.dependency_overrides[get_prediction_repository] = mock_get_prediction_repository

            with TestClient(app, raise_server_exceptions=False) as c:
                yield c

            app.dependency_overrides.clear()


class TestListPredictions:
    """Tests for GET /api/predictions endpoint."""

    def test_list_predictions_returns_200(
        self, client: TestClient, mock_prediction_repo: MagicMock, sample_predictions: list[Prediction]
    ) -> None:
        """Test list endpoint returns 200."""
        mock_prediction_repo.get_all.return_value = sample_predictions
        response = client.get("/api/predictions")
        assert response.status_code == 200

    def test_list_predictions_format(
        self, client: TestClient, mock_prediction_repo: MagicMock, sample_predictions: list[Prediction]
    ) -> None:
        """Test response format."""
        mock_prediction_repo.get_all.return_value = sample_predictions
        response = client.get("/api/predictions")
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "meta" in data
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_list_predictions_pagination(
        self, client: TestClient, mock_prediction_repo: MagicMock, sample_predictions: list[Prediction]
    ) -> None:
        """Test pagination functionality."""
        mock_prediction_repo.get_all.return_value = sample_predictions
        response = client.get("/api/predictions?page=1&per_page=10")
        data = response.json()
        assert data["meta"]["page"] == 1
        assert data["meta"]["per_page"] == 10

    def test_list_predictions_validated_filter(
        self, client: TestClient, mock_prediction_repo: MagicMock, sample_predictions: list[Prediction]
    ) -> None:
        """Test validated filter."""
        validated_predictions = [p for p in sample_predictions if p.is_correct is not None]
        mock_prediction_repo.get_validated_predictions.return_value = validated_predictions

        response = client.get("/api/predictions?validated=true")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_list_predictions_unvalidated_filter(
        self, client: TestClient, mock_prediction_repo: MagicMock, sample_predictions: list[Prediction]
    ) -> None:
        """Test unvalidated filter."""
        unvalidated_predictions = [p for p in sample_predictions if p.is_correct is None]
        mock_prediction_repo.get_unvalidated_predictions.return_value = unvalidated_predictions

        response = client.get("/api/predictions?validated=false")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_list_predictions_empty(
        self, client: TestClient, mock_prediction_repo: MagicMock
    ) -> None:
        """Test empty list response."""
        mock_prediction_repo.get_all.return_value = []
        response = client.get("/api/predictions")
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["meta"]["total"] == 0


class TestGetPrediction:
    """Tests for GET /api/predictions/{prediction_id} endpoint."""

    def test_get_prediction_404(self, client: TestClient, mock_prediction_repo: MagicMock) -> None:
        """Test prediction not found returns 404."""
        mock_prediction_repo.get_by_id.return_value = None
        response = client.get("/api/predictions/99999")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "NOT_FOUND"

    def test_get_prediction_success(
        self, client: TestClient, mock_prediction_repo: MagicMock, sample_predictions: list[Prediction]
    ) -> None:
        """Test successful prediction retrieval."""
        prediction = sample_predictions[0]
        mock_prediction_repo.get_by_id.return_value = prediction
        response = client.get("/api/predictions/1")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == 1
        assert data["data"]["market_id"] == "market-001"
        assert data["data"]["predicted_probability"] == 0.72
        assert data["data"]["confidence"] == 0.85

    def test_get_prediction_includes_all_fields(
        self, client: TestClient, mock_prediction_repo: MagicMock, sample_predictions: list[Prediction]
    ) -> None:
        """Test that detail endpoint includes all fields."""
        prediction = sample_predictions[0]
        mock_prediction_repo.get_by_id.return_value = prediction
        response = client.get("/api/predictions/1")
        data = response.json()
        assert "reasoning" in data["data"]
        assert "key_assumptions" in data["data"]
        assert "model_used" in data["data"]


class TestGetAccuracy:
    """Tests for GET /api/predictions/accuracy endpoint."""

    def test_get_accuracy_returns_200(
        self, client: TestClient, mock_prediction_repo: MagicMock, sample_predictions: list[Prediction]
    ) -> None:
        """Test accuracy endpoint returns 200."""
        mock_prediction_repo.get_all.return_value = sample_predictions
        response = client.get("/api/predictions/accuracy")
        assert response.status_code == 200

    def test_get_accuracy_format(
        self, client: TestClient, mock_prediction_repo: MagicMock, sample_predictions: list[Prediction]
    ) -> None:
        """Test response format."""
        mock_prediction_repo.get_all.return_value = sample_predictions
        response = client.get("/api/predictions/accuracy")
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "total_predictions" in data["data"]
        assert "accuracy" in data["data"]

    def test_get_accuracy_calculation(
        self, client: TestClient, mock_prediction_repo: MagicMock, sample_predictions: list[Prediction]
    ) -> None:
        """Test accuracy calculation."""
        mock_prediction_repo.get_all.return_value = sample_predictions
        response = client.get("/api/predictions/accuracy")
        data = response.json()
        # 3 total predictions, 2 validated, 1 correct
        assert data["data"]["total_predictions"] == 3
        assert data["data"]["validated_predictions"] == 2
        assert data["data"]["correct_predictions"] == 1
        # accuracy = 1/2 = 0.5
        assert data["data"]["accuracy"] == 0.5

    def test_get_accuracy_empty(
        self, client: TestClient, mock_prediction_repo: MagicMock
    ) -> None:
        """Test accuracy with no predictions."""
        mock_prediction_repo.get_all.return_value = []
        response = client.get("/api/predictions/accuracy")
        data = response.json()
        assert data["data"]["total_predictions"] == 0
        assert data["data"]["accuracy"] == 0.0
        assert data["data"]["avg_confidence"] == 0.0

    def test_get_accuracy_avg_confidence(
        self, client: TestClient, mock_prediction_repo: MagicMock, sample_predictions: list[Prediction]
    ) -> None:
        """Test average confidence calculation."""
        mock_prediction_repo.get_all.return_value = sample_predictions
        response = client.get("/api/predictions/accuracy")
        data = response.json()
        # (0.85 + 0.78 + 0.92) / 3 = 0.85
        expected_avg = (0.85 + 0.78 + 0.92) / 3
        assert abs(data["data"]["avg_confidence"] - expected_avg) < 0.01
