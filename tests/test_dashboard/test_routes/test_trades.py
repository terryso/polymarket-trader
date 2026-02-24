"""Tests for trade API routes.

This module contains tests for the trade data API endpoints,
including list and detail endpoints with pagination and mode filtering.

Story 7.3: 持仓与交易 API
"""

from datetime import datetime
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

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
            llm_prediction_id=10,
            position_id=1,
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
            llm_prediction_id=11,
            position_id=2,
            created_at=datetime(2026, 2, 14, 9, 0, 0),
        ),
        Trade(
            id=3,
            market_id="market-003",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.LIVE,
            amount=25.0,
            price=0.60,
            shares=41.67,
            status=TradeStatus.FILLED,
            llm_prediction_id=12,
            position_id=3,
            created_at=datetime(2026, 2, 13, 8, 0, 0),
        ),
    ]


@pytest.fixture
def sample_trade() -> Trade:
    """Create a single sample trade for testing."""
    return Trade(
        id=1,
        market_id="market-001",
        trade_type=TradeType.BUY_YES,
        mode=TradeMode.PAPER,
        amount=100.0,
        price=0.45,
        shares=222.22,
        status=TradeStatus.FILLED,
        llm_prediction_id=10,
        position_id=1,
        created_at=datetime(2026, 2, 15, 10, 30, 0),
    )


@pytest.fixture
def mock_trade_repo() -> MagicMock:
    """Create a mock TradeRepository for testing."""
    repo = MagicMock()
    repo.get_recent = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_market = AsyncMock(return_value=[])
    repo.get_by_mode = AsyncMock(return_value=[])
    repo.get_by_date_range = AsyncMock(return_value=[])
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def client(mock_trade_repo: MagicMock) -> Generator[TestClient, None, None]:
    """Create test client with mocked dependencies."""
    # Patch init_db and close_db to avoid database operations
    with patch("src.dashboard.app.init_db", new_callable=AsyncMock):
        with patch("src.dashboard.app.close_db", new_callable=AsyncMock):
            # Create a mock repository factory function
            def mock_get_trade_repository() -> MagicMock:
                return mock_trade_repo

            # Import app after patches
            from src.dashboard.app import app
            from src.dashboard.routes.trades import get_trade_repository

            # Override the dependency
            app.dependency_overrides[get_trade_repository] = mock_get_trade_repository

            with TestClient(app, raise_server_exceptions=False) as c:
                yield c

            # Clean up
            app.dependency_overrides.clear()


class TestListTrades:
    """Tests for the trade list endpoint."""

    def test_list_trades_returns_200(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
    ) -> None:
        """Test list trades returns 200."""
        mock_trade_repo.get_recent.return_value = []

        response = client.get("/api/trades")

        assert response.status_code == 200

    def test_list_trades_returns_success(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
    ) -> None:
        """Test list trades returns success status."""
        mock_trade_repo.get_recent.return_value = []

        response = client.get("/api/trades")
        data = response.json()

        assert data["success"] is True

    def test_list_trades_returns_data_list(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
    ) -> None:
        """Test list trades returns data as list."""
        mock_trade_repo.get_recent.return_value = []

        response = client.get("/api/trades")
        data = response.json()

        assert "data" in data
        assert isinstance(data["data"], list)

    def test_list_trades_returns_meta(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
    ) -> None:
        """Test list trades returns pagination metadata."""
        mock_trade_repo.get_recent.return_value = []

        response = client.get("/api/trades")
        data = response.json()

        assert "meta" in data
        assert "total" in data["meta"]
        assert "page" in data["meta"]
        assert "per_page" in data["meta"]

    def test_list_trades_with_data(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
        sample_trades: list[Trade],
    ) -> None:
        """Test list trades returns trades correctly."""
        mock_trade_repo.get_recent.return_value = sample_trades

        response = client.get("/api/trades")
        data = response.json()

        assert response.status_code == 200
        assert data["success"] is True
        assert len(data["data"]) == 3

        # Check first trade
        first_trade = data["data"][0]
        assert first_trade["id"] == 1
        assert first_trade["market_id"] == "market-001"
        assert first_trade["trade_type"] == "BUY_YES"
        assert first_trade["mode"] == "PAPER"
        assert first_trade["amount"] == 100.0
        assert first_trade["price"] == 0.45
        assert first_trade["status"] == "FILLED"

    def test_list_trades_pagination(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
        sample_trades: list[Trade],
    ) -> None:
        """Test list trades pagination."""
        mock_trade_repo.get_recent.return_value = sample_trades

        response = client.get("/api/trades?page=1&per_page=2")
        data = response.json()

        assert response.status_code == 200
        assert data["meta"]["page"] == 1
        assert data["meta"]["per_page"] == 2
        assert data["meta"]["total"] == 3
        assert len(data["data"]) == 2

    def test_list_trades_page_2(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
        sample_trades: list[Trade],
    ) -> None:
        """Test list trades second page."""
        mock_trade_repo.get_recent.return_value = sample_trades

        response = client.get("/api/trades?page=2&per_page=2")
        data = response.json()

        assert response.status_code == 200
        assert data["meta"]["page"] == 2
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == 3

    def test_list_trades_mode_filter_paper(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
        sample_trades: list[Trade],
    ) -> None:
        """Test list trades with mode filter for paper trades."""
        paper_trades = [t for t in sample_trades if t.mode == TradeMode.PAPER]
        mock_trade_repo.get_by_mode.return_value = paper_trades

        response = client.get("/api/trades?mode=paper")
        data = response.json()

        assert response.status_code == 200
        # All returned trades should be PAPER mode
        for trade in data["data"]:
            assert trade["mode"] == "PAPER"

    def test_list_trades_mode_filter_live(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
        sample_trades: list[Trade],
    ) -> None:
        """Test list trades with mode filter for live trades."""
        live_trades = [t for t in sample_trades if t.mode == TradeMode.LIVE]
        mock_trade_repo.get_by_mode.return_value = live_trades

        response = client.get("/api/trades?mode=live")
        data = response.json()

        assert response.status_code == 200
        # All returned trades should be LIVE mode
        for trade in data["data"]:
            assert trade["mode"] == "LIVE"

    def test_list_trades_invalid_mode(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
    ) -> None:
        """Test list trades with invalid mode filter."""
        response = client.get("/api/trades?mode=invalid")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 0

    def test_list_trades_empty(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
    ) -> None:
        """Test list trades returns empty list when no trades."""
        mock_trade_repo.get_recent.return_value = []

        response = client.get("/api/trades")
        data = response.json()

        assert response.status_code == 200
        assert data["success"] is True
        assert len(data["data"]) == 0
        assert data["meta"]["total"] == 0


class TestGetTrade:
    """Tests for the trade detail endpoint."""

    def test_get_trade_returns_200(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
        sample_trade: Trade,
    ) -> None:
        """Test get trade returns 200 when found."""
        mock_trade_repo.get_by_id.return_value = sample_trade

        response = client.get("/api/trades/1")

        assert response.status_code == 200

    def test_get_trade_returns_success(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
        sample_trade: Trade,
    ) -> None:
        """Test get trade returns success status when found."""
        mock_trade_repo.get_by_id.return_value = sample_trade

        response = client.get("/api/trades/1")
        data = response.json()

        assert data["success"] is True

    def test_get_trade_returns_correct_data(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
        sample_trade: Trade,
    ) -> None:
        """Test get trade returns correct trade data."""
        mock_trade_repo.get_by_id.return_value = sample_trade

        response = client.get("/api/trades/1")
        data = response.json()

        assert data["success"] is True
        assert data["data"]["id"] == 1
        assert data["data"]["market_id"] == "market-001"
        assert data["data"]["trade_type"] == "BUY_YES"
        assert data["data"]["mode"] == "PAPER"
        assert data["data"]["amount"] == 100.0
        assert data["data"]["price"] == 0.45
        assert data["data"]["shares"] == 222.22
        assert data["data"]["status"] == "FILLED"
        assert data["data"]["llm_prediction_id"] == 10
        assert data["data"]["position_id"] == 1

    def test_get_trade_404(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
    ) -> None:
        """Test get trade returns 404 when not found."""
        mock_trade_repo.get_by_id.return_value = None

        response = client.get("/api/trades/99999")

        assert response.status_code == 404

    def test_get_trade_404_error_format(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
    ) -> None:
        """Test get trade 404 returns correct error format."""
        mock_trade_repo.get_by_id.return_value = None

        response = client.get("/api/trades/99999")
        data = response.json()

        assert "detail" in data
        assert data["detail"]["success"] is False
        assert data["detail"]["error"]["code"] == "NOT_FOUND"
        assert "99999" in data["detail"]["error"]["message"]

    def test_get_trade_includes_references(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
    ) -> None:
        """Test get trade includes llm_prediction_id and position_id."""
        trade_with_refs = Trade(
            id=5,
            market_id="market-005",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.LIVE,
            amount=200.0,
            price=0.50,
            shares=400.0,
            status=TradeStatus.FILLED,
            llm_prediction_id=20,
            position_id=10,
            created_at=datetime(2026, 2, 16, 10, 0, 0),
        )
        mock_trade_repo.get_by_id.return_value = trade_with_refs

        response = client.get("/api/trades/5")
        data = response.json()

        assert response.status_code == 200
        assert data["data"]["llm_prediction_id"] == 20
        assert data["data"]["position_id"] == 10

    def test_get_trade_null_references(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
    ) -> None:
        """Test get trade handles null references."""
        trade_no_refs = Trade(
            id=6,
            market_id="market-006",
            trade_type=TradeType.SELL_YES,
            mode=TradeMode.PAPER,
            amount=50.0,
            price=0.80,
            shares=62.5,
            status=TradeStatus.FILLED,
            llm_prediction_id=None,
            position_id=None,
            created_at=datetime(2026, 2, 16, 11, 0, 0),
        )
        mock_trade_repo.get_by_id.return_value = trade_no_refs

        response = client.get("/api/trades/6")
        data = response.json()

        assert response.status_code == 200
        assert data["data"]["llm_prediction_id"] is None
        assert data["data"]["position_id"] is None
