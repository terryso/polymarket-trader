"""Tests for position API routes.

This module contains tests for the position data API endpoints,
including list and detail endpoints.

Story 7.3: 持仓与交易 API
"""

from datetime import datetime
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.models.position import Position, PositionOutcome, PositionStatus


@pytest.fixture
def sample_positions() -> list[Position]:
    """Create sample positions for testing."""
    return [
        Position(
            id=1,
            market_id="market-001",
            outcome=PositionOutcome.YES,
            shares=222.22,
            avg_price=0.45,
            initial_value=100.0,
            current_value=155.55,
            pnl=55.55,
            status=PositionStatus.OPEN,
            opened_at=datetime(2026, 2, 15, 10, 30, 0),
            closed_at=None,
        ),
        Position(
            id=2,
            market_id="market-002",
            outcome=PositionOutcome.NO,
            shares=100.0,
            avg_price=0.35,
            initial_value=50.0,
            current_value=45.0,
            pnl=-5.0,
            status=PositionStatus.OPEN,
            opened_at=datetime(2026, 2, 14, 9, 0, 0),
            closed_at=None,
        ),
    ]


@pytest.fixture
def sample_position() -> Position:
    """Create a single sample position for testing."""
    return Position(
        id=1,
        market_id="market-001",
        outcome=PositionOutcome.YES,
        shares=222.22,
        avg_price=0.45,
        initial_value=100.0,
        current_value=155.55,
        pnl=55.55,
        status=PositionStatus.OPEN,
        opened_at=datetime(2026, 2, 15, 10, 30, 0),
        closed_at=None,
    )


@pytest.fixture
def mock_position_repo() -> MagicMock:
    """Create a mock PositionRepository for testing."""
    repo = MagicMock()
    repo.get_open_positions = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_market = AsyncMock(return_value=None)
    repo.save = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def client(mock_position_repo: MagicMock) -> Generator[TestClient, None, None]:
    """Create test client with mocked dependencies."""
    # Patch init_db and close_db to avoid database operations
    with patch("src.dashboard.app.init_db", new_callable=AsyncMock):
        with patch("src.dashboard.app.close_db", new_callable=AsyncMock):
            # Create a mock repository factory function
            def mock_get_position_repository() -> MagicMock:
                return mock_position_repo

            # Import app after patches
            from src.dashboard.app import app
            from src.dashboard.routes.positions import get_position_repository

            # Override the dependency
            app.dependency_overrides[get_position_repository] = mock_get_position_repository

            with TestClient(app, raise_server_exceptions=False) as c:
                yield c

            # Clean up
            app.dependency_overrides.clear()


class TestListPositions:
    """Tests for the position list endpoint."""

    def test_list_positions_returns_200(
        self,
        client: TestClient,
        mock_position_repo: MagicMock,
    ) -> None:
        """Test list positions returns 200."""
        mock_position_repo.get_open_positions.return_value = []

        response = client.get("/api/positions")

        assert response.status_code == 200

    def test_list_positions_returns_success(
        self,
        client: TestClient,
        mock_position_repo: MagicMock,
    ) -> None:
        """Test list positions returns success status."""
        mock_position_repo.get_open_positions.return_value = []

        response = client.get("/api/positions")
        data = response.json()

        assert data["success"] is True

    def test_list_positions_returns_data_list(
        self,
        client: TestClient,
        mock_position_repo: MagicMock,
    ) -> None:
        """Test list positions returns data as list."""
        mock_position_repo.get_open_positions.return_value = []

        response = client.get("/api/positions")
        data = response.json()

        assert "data" in data
        assert isinstance(data["data"], list)

    def test_list_positions_with_data(
        self,
        client: TestClient,
        mock_position_repo: MagicMock,
        sample_positions: list[Position],
    ) -> None:
        """Test list positions returns positions correctly."""
        mock_position_repo.get_open_positions.return_value = sample_positions

        response = client.get("/api/positions")
        data = response.json()

        assert response.status_code == 200
        assert data["success"] is True
        assert len(data["data"]) == 2

        # Check first position
        first_position = data["data"][0]
        assert first_position["id"] == 1
        assert first_position["market_id"] == "market-001"
        assert first_position["outcome"] == "YES"
        assert first_position["shares"] == 222.22
        assert first_position["avg_price"] == 0.45
        assert first_position["status"] == "OPEN"

    def test_list_positions_empty(
        self,
        client: TestClient,
        mock_position_repo: MagicMock,
    ) -> None:
        """Test list positions returns empty list when no positions."""
        mock_position_repo.get_open_positions.return_value = []

        response = client.get("/api/positions")
        data = response.json()

        assert response.status_code == 200
        assert data["success"] is True
        assert len(data["data"]) == 0


class TestGetPosition:
    """Tests for the position detail endpoint."""

    def test_get_position_returns_200(
        self,
        client: TestClient,
        mock_position_repo: MagicMock,
        sample_position: Position,
    ) -> None:
        """Test get position returns 200 when found."""
        mock_position_repo.get_by_id.return_value = sample_position

        response = client.get("/api/positions/1")

        assert response.status_code == 200

    def test_get_position_returns_success(
        self,
        client: TestClient,
        mock_position_repo: MagicMock,
        sample_position: Position,
    ) -> None:
        """Test get position returns success status when found."""
        mock_position_repo.get_by_id.return_value = sample_position

        response = client.get("/api/positions/1")
        data = response.json()

        assert data["success"] is True

    def test_get_position_returns_correct_data(
        self,
        client: TestClient,
        mock_position_repo: MagicMock,
        sample_position: Position,
    ) -> None:
        """Test get position returns correct position data."""
        mock_position_repo.get_by_id.return_value = sample_position

        response = client.get("/api/positions/1")
        data = response.json()

        assert data["success"] is True
        assert data["data"]["id"] == 1
        assert data["data"]["market_id"] == "market-001"
        assert data["data"]["outcome"] == "YES"
        assert data["data"]["shares"] == 222.22
        assert data["data"]["avg_price"] == 0.45
        assert data["data"]["initial_value"] == 100.0
        assert data["data"]["current_value"] == 155.55
        assert data["data"]["pnl"] == 55.55
        assert data["data"]["status"] == "OPEN"

    def test_get_position_404(
        self,
        client: TestClient,
        mock_position_repo: MagicMock,
    ) -> None:
        """Test get position returns 404 when not found."""
        mock_position_repo.get_by_id.return_value = None

        response = client.get("/api/positions/99999")

        assert response.status_code == 404

    def test_get_position_404_error_format(
        self,
        client: TestClient,
        mock_position_repo: MagicMock,
    ) -> None:
        """Test get position 404 returns correct error format."""
        mock_position_repo.get_by_id.return_value = None

        response = client.get("/api/positions/99999")
        data = response.json()

        assert "detail" in data
        assert data["detail"]["success"] is False
        assert data["detail"]["error"]["code"] == "NOT_FOUND"
        assert "99999" in data["detail"]["error"]["message"]

    def test_get_position_includes_closed_at(
        self,
        client: TestClient,
        mock_position_repo: MagicMock,
    ) -> None:
        """Test get position includes closed_at for closed positions."""
        closed_position = Position(
            id=3,
            market_id="market-003",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.50,
            initial_value=50.0,
            current_value=100.0,
            pnl=50.0,
            status=PositionStatus.CLOSED,
            opened_at=datetime(2026, 2, 10, 10, 0, 0),
            closed_at=datetime(2026, 2, 15, 15, 0, 0),
        )
        mock_position_repo.get_by_id.return_value = closed_position

        response = client.get("/api/positions/3")
        data = response.json()

        assert response.status_code == 200
        assert data["data"]["status"] == "CLOSED"
        assert data["data"]["closed_at"] is not None
