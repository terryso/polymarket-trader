"""Tests for activity API routes.

This module contains tests for the activity data API endpoints,
including the list endpoint with limit parameter.

Story 7.7: 最近活动 API 与前端集成
"""

from datetime import datetime
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.models.prediction import Prediction, Recommendation
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType


@pytest.fixture
def sample_trades() -> list[Trade]:
    """Create sample trades for testing."""
    return [
        Trade(
            id=1,
            market_id="market-001",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=100.0,
            price=0.45,
            shares=222.22,
            status=TradeStatus.FILLED,
            created_at=datetime(2026, 2, 15, 10, 30, 0),
        ),
        Trade(
            id=2,
            market_id="market-002",
            trade_type=TradeType.BUY_NO,
            mode=TradeMode.PAPER,
            amount=50.0,
            price=0.35,
            shares=142.86,
            status=TradeStatus.FILLED,
            created_at=datetime(2026, 2, 15, 9, 0, 0),
        ),
    ]


@pytest.fixture
def sample_predictions() -> list[Prediction]:
    """Create sample predictions for testing."""
    return [
        Prediction(
            id=1,
            market_id="market-001",
            predicted_probability=0.75,
            confidence=0.85,
            recommendation=Recommendation.BUY_YES,
            created_at=datetime(2026, 2, 15, 8, 0, 0),
        ),
        Prediction(
            id=2,
            market_id="market-002",
            predicted_probability=0.35,
            confidence=0.70,
            recommendation=Recommendation.BUY_NO,
            created_at=datetime(2026, 2, 15, 7, 0, 0),
        ),
    ]


@pytest.fixture
def mock_trade_repo(sample_trades: list[Trade]) -> MagicMock:
    """Create a mock TradeRepository for testing."""
    repo = MagicMock()
    repo.get_recent = AsyncMock(return_value=sample_trades)
    return repo


@pytest.fixture
def mock_prediction_repo(sample_predictions: list[Prediction]) -> MagicMock:
    """Create a mock PredictionRepository for testing."""
    repo = MagicMock()
    repo.get_all = AsyncMock(return_value=sample_predictions)
    return repo


@pytest.fixture
def client(
    mock_trade_repo: MagicMock,
    mock_prediction_repo: MagicMock,
) -> Generator[TestClient, None, None]:
    """Create test client with mocked dependencies."""
    # Patch init_db and close_db to avoid database operations
    with patch("src.dashboard.app.init_db", new_callable=AsyncMock):
        with patch("src.dashboard.app.close_db", new_callable=AsyncMock):
            # Import app after patches
            from src.dashboard.app import app
            from src.dashboard.routes.activities import (
                trade_repo_dependency,
                prediction_repo_dependency,
            )

            # Create mock factory functions
            def mock_get_trade_repo() -> MagicMock:
                return mock_trade_repo

            def mock_get_prediction_repo() -> MagicMock:
                return mock_prediction_repo

            # Override the dependencies
            app.dependency_overrides[trade_repo_dependency] = mock_get_trade_repo
            app.dependency_overrides[prediction_repo_dependency] = mock_get_prediction_repo

            with TestClient(app, raise_server_exceptions=False) as c:
                yield c

            # Clean up
            app.dependency_overrides.clear()


class TestGetActivities:
    """Tests for GET /api/activities endpoint."""

    def test_get_activities_returns_200(self, client: TestClient) -> None:
        """Test that the endpoint returns 200 status."""
        response = client.get("/api/activities")
        assert response.status_code == 200

    def test_get_activities_response_format(
        self, client: TestClient
    ) -> None:
        """Test that the response has correct format."""
        response = client.get("/api/activities")
        data = response.json()

        assert "success" in data
        assert "data" in data
        assert data["success"] is True
        assert "items" in data["data"]
        assert "total" in data["data"]

    def test_get_activities_includes_trades(
        self, client: TestClient
    ) -> None:
        """Test that activities include trade records."""
        response = client.get("/api/activities")
        data = response.json()

        items = data["data"]["items"]
        trade_items = [item for item in items if item["type"] == "trade"]

        assert len(trade_items) > 0
        # Check trade item structure
        trade_item = trade_items[0]
        assert "id" in trade_item
        assert "type" in trade_item
        assert "description" in trade_item
        assert "time" in trade_item
        assert "amount" in trade_item
        assert trade_item["amount"] is not None

    def test_get_activities_includes_predictions(
        self, client: TestClient
    ) -> None:
        """Test that activities include prediction records."""
        response = client.get("/api/activities")
        data = response.json()

        items = data["data"]["items"]
        prediction_items = [item for item in items if item["type"] == "prediction"]

        assert len(prediction_items) > 0
        # Check prediction item structure
        pred_item = prediction_items[0]
        assert "id" in pred_item
        assert "type" in pred_item
        assert "description" in pred_item
        assert "time" in pred_item
        assert "amount" in pred_item
        # Predictions don't have amount
        assert pred_item["amount"] is None

    def test_get_activities_includes_system_events(
        self, client: TestClient
    ) -> None:
        """Test that activities include system events."""
        response = client.get("/api/activities")
        data = response.json()

        items = data["data"]["items"]
        system_items = [item for item in items if item["type"] == "system"]

        # System events may or may not be present depending on state
        # Just check structure if present
        if len(system_items) > 0:
            sys_item = system_items[0]
            assert "id" in sys_item
            assert "type" in sys_item
            assert "description" in sys_item

    def test_get_activities_sorted_by_time(
        self, client: TestClient
    ) -> None:
        """Test that activities are sorted by time (most recent first)."""
        response = client.get("/api/activities")
        data = response.json()

        items = data["data"]["items"]

        # Get timestamps for items that have them
        timestamps = [
            item.get("timestamp") for item in items if item.get("timestamp")
        ]

        # Verify timestamps are in descending order (most recent first)
        if len(timestamps) > 1:
            for i in range(len(timestamps) - 1):
                assert timestamps[i] >= timestamps[i + 1]

    def test_get_activities_limit_parameter(
        self, client: TestClient
    ) -> None:
        """Test that limit parameter works correctly."""
        # Test with limit=2
        response = client.get("/api/activities?limit=2")
        data = response.json()

        items = data["data"]["items"]
        assert len(items) <= 2

    def test_get_activities_default_limit(
        self, client: TestClient
    ) -> None:
        """Test that default limit is 10."""
        response = client.get("/api/activities")
        data = response.json()

        items = data["data"]["items"]
        # Items should be at most 10 (default)
        assert len(items) <= 10

    def test_get_activities_empty_repos(self, client: TestClient) -> None:
        """Test behavior when repositories return empty lists."""
        # Create new mocks that return empty lists
        empty_trade_repo = MagicMock()
        empty_trade_repo.get_recent = AsyncMock(return_value=[])

        empty_prediction_repo = MagicMock()
        empty_prediction_repo.get_all = AsyncMock(return_value=[])

        with patch("src.dashboard.app.init_db", new_callable=AsyncMock):
            with patch("src.dashboard.app.close_db", new_callable=AsyncMock):
                from src.dashboard.app import app
                from src.dashboard.routes.activities import (
                    trade_repo_dependency,
                    prediction_repo_dependency,
                )

                def mock_empty_trade_repo() -> MagicMock:
                    return empty_trade_repo

                def mock_empty_prediction_repo() -> MagicMock:
                    return empty_prediction_repo

                app.dependency_overrides[trade_repo_dependency] = mock_empty_trade_repo
                app.dependency_overrides[prediction_repo_dependency] = mock_empty_prediction_repo

                with TestClient(app, raise_server_exceptions=False) as test_client:
                    response = test_client.get("/api/activities")
                    data = response.json()

                    assert response.status_code == 200
                    assert data["success"] is True
                    # With no trades/predictions, items list should be empty or contain only system events
                    items = data["data"]["items"]
                    assert isinstance(items, list)

                app.dependency_overrides.clear()


class TestActivityTypes:
    """Tests for activity type validation."""

    def test_trade_activity_has_correct_type(
        self, client: TestClient
    ) -> None:
        """Test that trade activities have type='trade'."""
        response = client.get("/api/activities")
        data = response.json()

        trade_items = [item for item in data["data"]["items"] if "trade" in item["id"]]
        for item in trade_items:
            assert item["type"] == "trade"

    def test_prediction_activity_has_correct_type(
        self, client: TestClient
    ) -> None:
        """Test that prediction activities have type='prediction'."""
        response = client.get("/api/activities")
        data = response.json()

        pred_items = [
            item for item in data["data"]["items"] if "prediction" in item["id"]
        ]
        for item in pred_items:
            assert item["type"] == "prediction"
