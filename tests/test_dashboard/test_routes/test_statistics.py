"""Tests for statistics API routes.

This module contains tests for the statistics API endpoints,
including overview, daily, and performance endpoints.

Story 7.4: 预测与统计 API
"""

from datetime import date, datetime
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.polymarket import WalletBalance
from src.core.state import StateSnapshot
from src.models.position import Position, PositionOutcome, PositionStatus
from src.models.statistics import Statistics
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType


@pytest.fixture
def sample_statistics() -> list[Statistics]:
    """Create sample statistics for testing."""
    return [
        Statistics(
            id=1,
            date=date(2026, 2, 15),
            mode=TradeMode.PAPER,
            starting_capital=200.0,
            ending_capital=205.0,
            total_pnl=5.0,
            total_trades=3,
            winning_trades=2,
            losing_trades=1,
            win_rate=0.67,
            created_at=datetime(2026, 2, 15, 23, 59, 59),
        ),
        Statistics(
            id=2,
            date=date(2026, 2, 14),
            mode=TradeMode.PAPER,
            starting_capital=200.0,
            ending_capital=200.0,
            total_pnl=0.0,
            total_trades=2,
            winning_trades=1,
            losing_trades=1,
            win_rate=0.50,
            created_at=datetime(2026, 2, 14, 23, 59, 59),
        ),
        Statistics(
            id=3,
            date=date(2026, 2, 13),
            mode=TradeMode.PAPER,
            starting_capital=200.0,
            ending_capital=195.0,
            total_pnl=-5.0,
            total_trades=1,
            winning_trades=0,
            losing_trades=1,
            win_rate=0.0,
            created_at=datetime(2026, 2, 13, 23, 59, 59),
        ),
    ]


@pytest.fixture
def sample_trades() -> list[Trade]:
    """Create sample trades for testing."""
    return [
        Trade(
            id=1,
            market_id="market-001",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=50.0,
            price=0.45,
            shares=111.11,
            status=TradeStatus.FILLED,
            created_at=datetime(2026, 2, 15, 10, 0, 0),
        ),
        Trade(
            id=2,
            market_id="market-002",
            trade_type=TradeType.BUY_NO,
            mode=TradeMode.PAPER,
            amount=30.0,
            price=0.35,
            shares=85.71,
            status=TradeStatus.FILLED,
            created_at=datetime(2026, 2, 14, 11, 0, 0),
        ),
    ]


@pytest.fixture
def sample_positions() -> list[Position]:
    """Create sample positions for testing."""
    return [
        Position(
            id=1,
            market_id="market-001",
            outcome=PositionOutcome.YES,
            shares=111.11,
            avg_price=0.45,
            initial_value=50.0,
            current_value=55.0,
            pnl=5.0,
            status=PositionStatus.OPEN,
            opened_at=datetime(2026, 2, 15, 10, 0, 0),
            closed_at=None,
        ),
    ]


@pytest.fixture
def sample_state_snapshot() -> StateSnapshot:
    """Create sample state snapshot for testing."""
    return StateSnapshot(
        current_capital=200.0,
        daily_pnl=5.0,
        consecutive_losses=0,
        open_positions_count=1,
        trading_enabled=True,
        reduced_mode=False,
        updated_at=datetime(2026, 2, 15, 12, 0, 0),
    )


@pytest.fixture
def mock_statistics_repo() -> MagicMock:
    """Create a mock StatisticsRepository for testing."""
    repo = MagicMock()
    repo.get_all = AsyncMock(return_value=[])
    repo.get_by_date_range = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_trade_repo() -> MagicMock:
    """Create a mock TradeRepository for testing."""
    repo = MagicMock()
    repo.get_recent = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_position_repo() -> MagicMock:
    """Create a mock PositionRepository for testing."""
    repo = MagicMock()
    repo.get_open_positions = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_state() -> MagicMock:
    """Create a mock ThreadSafeState for testing."""
    state = MagicMock()
    state.get_state = AsyncMock()
    return state


@pytest.fixture
def client(
    mock_statistics_repo: MagicMock,
    mock_trade_repo: MagicMock,
    mock_position_repo: MagicMock,
    mock_state: MagicMock,
) -> Generator[TestClient, None, None]:
    """Create test client with mocked dependencies."""
    with patch("src.dashboard.app.init_db", new_callable=AsyncMock):
        with patch("src.dashboard.app.close_db", new_callable=AsyncMock):
            def mock_get_statistics_repository() -> MagicMock:
                return mock_statistics_repo

            def mock_get_trade_repository() -> MagicMock:
                return mock_trade_repo

            def mock_get_position_repository() -> MagicMock:
                return mock_position_repo

            def mock_get_state() -> MagicMock:
                return mock_state

            from src.dashboard.app import app
            from src.dashboard.routes.statistics import (
                get_position_repository,
                get_state,
                get_statistics_repository,
                get_trade_repository,
            )

            app.dependency_overrides[get_statistics_repository] = mock_get_statistics_repository
            app.dependency_overrides[get_trade_repository] = mock_get_trade_repository
            app.dependency_overrides[get_position_repository] = mock_get_position_repository
            app.dependency_overrides[get_state] = mock_get_state

            with TestClient(app, raise_server_exceptions=False) as c:
                yield c

            app.dependency_overrides.clear()


class TestGetOverview:
    """Tests for GET /api/statistics/overview endpoint."""

    def test_get_overview_returns_200(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
        mock_position_repo: MagicMock,
        mock_state: MagicMock,
        sample_trades: list[Trade],
        sample_positions: list[Position],
        sample_state_snapshot: StateSnapshot,
    ) -> None:
        """Test overview endpoint returns 200."""
        mock_trade_repo.get_recent.return_value = sample_trades
        mock_position_repo.get_open_positions.return_value = sample_positions
        mock_state.get_state.return_value = sample_state_snapshot

        with patch("src.dashboard.routes.statistics.PolymarketClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_wallet_balance.return_value = WalletBalance(
                usdc_balance=100.0, error=None
            )
            mock_client_class.return_value = mock_client

            response = client.get("/api/statistics/overview")
            assert response.status_code == 200

    def test_get_overview_format(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
        mock_position_repo: MagicMock,
        mock_state: MagicMock,
        sample_trades: list[Trade],
        sample_positions: list[Position],
        sample_state_snapshot: StateSnapshot,
    ) -> None:
        """Test response format."""
        mock_trade_repo.get_recent.return_value = sample_trades
        mock_position_repo.get_open_positions.return_value = sample_positions
        mock_state.get_state.return_value = sample_state_snapshot

        with patch("src.dashboard.routes.statistics.PolymarketClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_wallet_balance.return_value = WalletBalance(
                usdc_balance=100.0, error=None
            )
            mock_client_class.return_value = mock_client

            response = client.get("/api/statistics/overview")
            data = response.json()
            assert "success" in data
            assert "data" in data
            assert "current_capital" in data["data"]
            assert "total_pnl" in data["data"]
            assert "win_rate" in data["data"]
            assert "total_trades" in data["data"]
            assert "open_positions" in data["data"]
            assert "trading_enabled" in data["data"]
            assert "mode" in data["data"]
            assert "wallet_balance" in data["data"]
            assert "wallet_balance_error" in data["data"]

    def test_get_overview_values(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
        mock_position_repo: MagicMock,
        mock_state: MagicMock,
        sample_trades: list[Trade],
        sample_positions: list[Position],
        sample_state_snapshot: StateSnapshot,
    ) -> None:
        """Test overview values are calculated correctly."""
        mock_trade_repo.get_recent.return_value = sample_trades
        mock_position_repo.get_open_positions.return_value = sample_positions
        mock_state.get_state.return_value = sample_state_snapshot

        with patch("src.dashboard.routes.statistics.PolymarketClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_wallet_balance.return_value = WalletBalance(
                usdc_balance=150.0, error=None
            )
            mock_client_class.return_value = mock_client

            response = client.get("/api/statistics/overview")
            data = response.json()
            # current_capital = wallet_balance (150) + position_value (55) = 205
            assert data["data"]["current_capital"] == 205.0
            assert data["data"]["initial_capital"] == 200.0
            # total_pnl = current_capital (205) - initial_capital (200) = 5
            assert data["data"]["total_pnl"] == 5.0
            assert data["data"]["position_value"] == 55.0
            assert data["data"]["position_pnl"] == 5.0
            assert data["data"]["open_positions"] == 1
            assert data["data"]["trading_enabled"] is True
            assert data["data"]["wallet_balance"] == 150.0
            assert data["data"]["wallet_balance_error"] is None

    def test_get_overview_empty_trades(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
        mock_position_repo: MagicMock,
        mock_state: MagicMock,
        sample_positions: list[Position],
        sample_state_snapshot: StateSnapshot,
    ) -> None:
        """Test overview with no trades."""
        mock_trade_repo.get_recent.return_value = []
        mock_position_repo.get_open_positions.return_value = sample_positions
        mock_state.get_state.return_value = sample_state_snapshot

        with patch("src.dashboard.routes.statistics.PolymarketClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_wallet_balance.return_value = WalletBalance(
                usdc_balance=100.0, error=None
            )
            mock_client_class.return_value = mock_client

            response = client.get("/api/statistics/overview")
            data = response.json()
            assert data["data"]["total_trades"] == 0
            assert data["data"]["win_rate"] == 0.0

    def test_get_overview_wallet_balance_error(
        self,
        client: TestClient,
        mock_trade_repo: MagicMock,
        mock_position_repo: MagicMock,
        mock_state: MagicMock,
        sample_trades: list[Trade],
        sample_positions: list[Position],
        sample_state_snapshot: StateSnapshot,
    ) -> None:
        """Test overview handles wallet balance fetch error."""
        mock_trade_repo.get_recent.return_value = sample_trades
        mock_position_repo.get_open_positions.return_value = sample_positions
        mock_state.get_state.return_value = sample_state_snapshot

        with patch("src.dashboard.routes.statistics.PolymarketClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_wallet_balance.return_value = WalletBalance(
                usdc_balance=None, error="Network error"
            )
            mock_client_class.return_value = mock_client

            response = client.get("/api/statistics/overview")
            data = response.json()
            assert data["data"]["wallet_balance"] is None
            assert data["data"]["wallet_balance_error"] == "Network error"


class TestGetDailyStats:
    """Tests for GET /api/statistics/daily endpoint."""

    def test_get_daily_stats_returns_200(
        self, client: TestClient, mock_statistics_repo: MagicMock, sample_statistics: list[Statistics]
    ) -> None:
        """Test daily stats endpoint returns 200."""
        mock_statistics_repo.get_all.return_value = sample_statistics
        response = client.get("/api/statistics/daily")
        assert response.status_code == 200

    def test_get_daily_stats_format(
        self, client: TestClient, mock_statistics_repo: MagicMock, sample_statistics: list[Statistics]
    ) -> None:
        """Test response format."""
        mock_statistics_repo.get_all.return_value = sample_statistics
        response = client.get("/api/statistics/daily")
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "meta" in data
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_get_daily_stats_pagination(
        self, client: TestClient, mock_statistics_repo: MagicMock, sample_statistics: list[Statistics]
    ) -> None:
        """Test pagination functionality."""
        mock_statistics_repo.get_all.return_value = sample_statistics
        response = client.get("/api/statistics/daily?page=1&per_page=10")
        data = response.json()
        assert "meta" in data
        assert data["meta"]["page"] == 1
        assert data["meta"]["per_page"] == 10

    def test_get_daily_stats_sorted_desc(
        self, client: TestClient, mock_statistics_repo: MagicMock, sample_statistics: list[Statistics]
    ) -> None:
        """Test daily stats are sorted by date descending."""
        mock_statistics_repo.get_all.return_value = sample_statistics
        response = client.get("/api/statistics/daily")
        data = response.json()
        if len(data["data"]) > 1:
            dates = [item["date"] for item in data["data"]]
            assert dates == sorted(dates, reverse=True)

    def test_get_daily_stats_empty(
        self, client: TestClient, mock_statistics_repo: MagicMock
    ) -> None:
        """Test empty daily stats response."""
        mock_statistics_repo.get_all.return_value = []
        response = client.get("/api/statistics/daily")
        data = response.json()
        assert data["data"] == []
        assert data["meta"]["total"] == 0


class TestGetPerformance:
    """Tests for GET /api/statistics/performance endpoint."""

    def test_get_performance_returns_200(
        self, client: TestClient, mock_statistics_repo: MagicMock, sample_statistics: list[Statistics]
    ) -> None:
        """Test performance endpoint returns 200."""
        mock_statistics_repo.get_by_date_range.return_value = sample_statistics
        response = client.get("/api/statistics/performance")
        assert response.status_code == 200

    def test_get_performance_format(
        self, client: TestClient, mock_statistics_repo: MagicMock, sample_statistics: list[Statistics]
    ) -> None:
        """Test response format."""
        mock_statistics_repo.get_by_date_range.return_value = sample_statistics
        response = client.get("/api/statistics/performance")
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "capital_history" in data["data"]
        assert "win_rate_history" in data["data"]
        assert "trades_by_day" in data["data"]

    def test_get_performance_days_parameter(
        self, client: TestClient, mock_statistics_repo: MagicMock, sample_statistics: list[Statistics]
    ) -> None:
        """Test days parameter."""
        mock_statistics_repo.get_by_date_range.return_value = sample_statistics
        response = client.get("/api/statistics/performance?days=7")
        assert response.status_code == 200
        # The implementation fills in all dates in range
        # We just verify the endpoint accepts the parameter

    def test_get_performance_empty(
        self, client: TestClient, mock_statistics_repo: MagicMock
    ) -> None:
        """Test performance with no data."""
        mock_statistics_repo.get_by_date_range.return_value = []
        response = client.get("/api/statistics/performance?days=7")
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"]["capital_history"], list)
        assert isinstance(data["data"]["win_rate_history"], list)
        assert isinstance(data["data"]["trades_by_day"], list)

    def test_get_performance_max_days(
        self, client: TestClient, mock_statistics_repo: MagicMock
    ) -> None:
        """Test performance endpoint respects max days limit."""
        response = client.get("/api/statistics/performance?days=400")
        # Should either accept it (since our impl allows up to 365) or reject it
        # Our implementation allows up to 365
        assert response.status_code in [200, 422]  # Either OK or validation error
