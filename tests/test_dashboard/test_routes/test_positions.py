"""Tests for position API routes.

This module contains tests for the position data API endpoints,
including list, detail, and manual exit endpoints.

Story 7.3: 持仓与交易 API
Story 10.6: Dashboard 退出策略管理 - 手动退出持仓
"""

from datetime import datetime
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.models.position import CacheFreshness, Position, PositionOutcome, PositionStatus
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType


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
    # Reset PositionCacheService singleton to ensure clean state
    from src.trading.position_sync import PositionCacheService
    PositionCacheService._reset_instance()

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

            # Reset singleton after test
            PositionCacheService._reset_instance()


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

    def test_list_positions_returns_data_with_cache_info(
        self,
        client: TestClient,
        mock_position_repo: MagicMock,
    ) -> None:
        """Test list positions returns data with cache information."""
        mock_position_repo.get_open_positions.return_value = []

        response = client.get("/api/positions")
        data = response.json()

        assert "data" in data
        assert "positions" in data["data"]
        assert "cache_freshness" in data["data"]
        assert "cache_age_seconds" in data["data"]
        assert "total_count" in data["data"]
        assert isinstance(data["data"]["positions"], list)

    def test_list_positions_with_data(
        self,
        client: TestClient,
        mock_position_repo: MagicMock,
        sample_positions: list[Position],
    ) -> None:
        """Test list positions returns positions correctly."""
        from src.models.position import CacheFreshness

        # Mock the PositionCacheService - patch at module level where it's imported
        with patch("src.trading.position_sync.PositionCacheService") as mock_cache_service:
            mock_instance = MagicMock()
            mock_instance.get_positions = AsyncMock(
                return_value=(sample_positions, CacheFreshness.FRESH)
            )
            mock_instance.get_cache_status = AsyncMock(
                return_value=MagicMock(
                    cache_updated_at=datetime(2026, 2, 15, 10, 30, 0),
                    cache_age_seconds=30,
                    cache_freshness=CacheFreshness.FRESH,
                    is_refreshing=False,
                    can_refresh=True,
                    last_error=None,
                    total_positions=2,
                )
            )
            mock_cache_service.return_value = mock_instance

            response = client.get("/api/positions")
            data = response.json()

            assert response.status_code == 200
            assert data["success"] is True
            assert len(data["data"]["positions"]) == 2

            # Check first position
            first_position = data["data"]["positions"][0]
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
        assert len(data["data"]["positions"]) == 0
        assert data["data"]["total_count"] == 0


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


# ==================== Story 10.6: 手动退出持仓 ====================


@pytest.fixture
def mock_trade_repo() -> MagicMock:
    """Create a mock TradeRepository for testing."""
    repo = MagicMock()
    repo.get_recent = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=None)
    repo.save = AsyncMock(
        return_value=Trade(
            id=1,
            market_id="market-001",
            trade_type=TradeType.SELL_YES,
            mode=TradeMode.PAPER,
            amount=100.0,
            price=0.70,
            shares=142.86,
            status=TradeStatus.FILLED,
            exit_type="manual",
        )
    )
    return repo


@pytest.fixture
def client_with_both_repos(
    mock_position_repo: MagicMock,
    mock_trade_repo: MagicMock,
) -> Generator[TestClient, None, None]:
    """Create test client with mocked position and trade repositories."""
    with patch("src.dashboard.app.init_db", new_callable=AsyncMock):
        with patch("src.dashboard.app.close_db", new_callable=AsyncMock):
            def mock_get_position_repository() -> MagicMock:
                return mock_position_repo

            def mock_get_trade_repository() -> MagicMock:
                return mock_trade_repo

            from src.dashboard.app import app
            from src.dashboard.routes.positions import (
                get_position_repository,
                get_trade_repository,
            )

            app.dependency_overrides[get_position_repository] = mock_get_position_repository
            app.dependency_overrides[get_trade_repository] = mock_get_trade_repository

            with TestClient(app, raise_server_exceptions=False) as c:
                yield c

            app.dependency_overrides.clear()


class TestManualExitPosition:
    """Tests for the POST /api/positions/{position_id}/exit endpoint."""

    def test_manual_exit_returns_200(
        self,
        client_with_both_repos: TestClient,
        mock_position_repo: MagicMock,
        sample_position: Position,
    ) -> None:
        """Test manual exit returns 200 for open position."""
        mock_position_repo.get_by_id.return_value = sample_position
        mock_position_repo.update.return_value = sample_position

        response = client_with_both_repos.post("/api/positions/1/exit")

        assert response.status_code == 200

    def test_manual_exit_returns_success(
        self,
        client_with_both_repos: TestClient,
        mock_position_repo: MagicMock,
        sample_position: Position,
    ) -> None:
        """Test manual exit returns success status."""
        mock_position_repo.get_by_id.return_value = sample_position
        mock_position_repo.update.return_value = sample_position

        response = client_with_both_repos.post("/api/positions/1/exit")
        data = response.json()

        assert data["success"] is True

    def test_manual_exit_returns_correct_data(
        self,
        client_with_both_repos: TestClient,
        mock_position_repo: MagicMock,
        sample_position: Position,
    ) -> None:
        """Test manual exit returns correct exit data."""
        mock_position_repo.get_by_id.return_value = sample_position
        mock_position_repo.update.return_value = sample_position

        response = client_with_both_repos.post("/api/positions/1/exit")
        data = response.json()

        assert data["success"] is True
        assert data["data"]["success"] is True
        assert data["data"]["position_id"] == 1
        assert data["data"]["market_id"] == "market-001"
        assert data["data"]["exit_type"] == "manual"
        assert "shares_sold" in data["data"]
        assert "avg_price" in data["data"]
        assert "total_value" in data["data"]

    def test_manual_exit_shares_sold(
        self,
        client_with_both_repos: TestClient,
        mock_position_repo: MagicMock,
        sample_position: Position,
    ) -> None:
        """Test manual exit returns correct shares sold."""
        mock_position_repo.get_by_id.return_value = sample_position
        mock_position_repo.update.return_value = sample_position

        response = client_with_both_repos.post("/api/positions/1/exit")
        data = response.json()

        assert data["data"]["shares_sold"] == 222.22

    def test_manual_exit_calculates_pnl(
        self,
        client_with_both_repos: TestClient,
        mock_position_repo: MagicMock,
        sample_position: Position,
    ) -> None:
        """Test manual exit calculates realized PnL."""
        mock_position_repo.get_by_id.return_value = sample_position
        mock_position_repo.update.return_value = sample_position

        response = client_with_both_repos.post("/api/positions/1/exit")
        data = response.json()

        # With initial_value=100 and current_value=155.55
        # exit_price = current_value / shares = 155.55 / 222.22 = 0.70
        # total_value = shares * exit_price = 222.22 * 0.70 = 155.55
        # realized_pnl = total_value - initial_value = 155.55 - 100 = 55.55
        assert "realized_pnl" in data["data"]
        assert data["data"]["realized_pnl"] is not None

    def test_manual_exit_404_not_found(
        self,
        client_with_both_repos: TestClient,
        mock_position_repo: MagicMock,
    ) -> None:
        """Test manual exit returns 404 for non-existent position."""
        mock_position_repo.get_by_id.return_value = None

        response = client_with_both_repos.post("/api/positions/99999/exit")

        assert response.status_code == 404

    def test_manual_exit_404_error_format(
        self,
        client_with_both_repos: TestClient,
        mock_position_repo: MagicMock,
    ) -> None:
        """Test manual exit 404 returns correct error format."""
        mock_position_repo.get_by_id.return_value = None

        response = client_with_both_repos.post("/api/positions/99999/exit")
        data = response.json()

        assert "detail" in data
        assert data["detail"]["success"] is False
        assert data["detail"]["error"]["code"] == "NOT_FOUND"
        assert "99999" in data["detail"]["error"]["message"]

    def test_manual_exit_400_closed_position(
        self,
        client_with_both_repos: TestClient,
        mock_position_repo: MagicMock,
    ) -> None:
        """Test manual exit returns 400 for closed position."""
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

        response = client_with_both_repos.post("/api/positions/3/exit")

        assert response.status_code == 400

    def test_manual_exit_400_error_format(
        self,
        client_with_both_repos: TestClient,
        mock_position_repo: MagicMock,
    ) -> None:
        """Test manual exit 400 returns correct error format."""
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

        response = client_with_both_repos.post("/api/positions/3/exit")
        data = response.json()

        assert "detail" in data
        assert data["detail"]["success"] is False
        assert data["detail"]["error"]["code"] == "VALIDATION_ERROR"
        assert "not open" in data["detail"]["error"]["message"].lower()

    def test_manual_exit_updates_position_status(
        self,
        client_with_both_repos: TestClient,
        mock_position_repo: MagicMock,
        sample_position: Position,
    ) -> None:
        """Test manual exit updates position status to CLOSED."""
        mock_position_repo.get_by_id.return_value = sample_position
        mock_position_repo.update.return_value = sample_position

        client_with_both_repos.post("/api/positions/1/exit")

        # Verify update was called
        mock_position_repo.update.assert_called_once()
        # Check that status was set to CLOSED
        updated_position = mock_position_repo.update.call_args[0][0]
        assert updated_position.status == PositionStatus.CLOSED
        assert updated_position.closed_at is not None

    def test_manual_exit_creates_trade_record(
        self,
        client_with_both_repos: TestClient,
        mock_position_repo: MagicMock,
        mock_trade_repo: MagicMock,
        sample_position: Position,
    ) -> None:
        """Test manual exit creates a sell trade record."""
        mock_position_repo.get_by_id.return_value = sample_position
        mock_position_repo.update.return_value = sample_position

        client_with_both_repos.post("/api/positions/1/exit")

        # Verify trade was saved
        mock_trade_repo.save.assert_called_once()
        saved_trade = mock_trade_repo.save.call_args[0][0]
        assert saved_trade.exit_type == "manual"
        assert saved_trade.status == TradeStatus.FILLED
        assert saved_trade.mode == TradeMode.PAPER

    def test_manual_exit_no_outcome_position(
        self,
        client_with_both_repos: TestClient,
        mock_position_repo: MagicMock,
        mock_trade_repo: MagicMock,
    ) -> None:
        """Test manual exit handles position with NO outcome."""
        no_position = Position(
            id=4,
            market_id="market-004",
            outcome=PositionOutcome.NO,
            shares=200.0,
            avg_price=0.30,
            initial_value=60.0,
            current_value=80.0,
            pnl=20.0,
            status=PositionStatus.OPEN,
            opened_at=datetime(2026, 2, 12, 10, 0, 0),
            closed_at=None,
        )
        mock_position_repo.get_by_id.return_value = no_position
        mock_position_repo.update.return_value = no_position

        response = client_with_both_repos.post("/api/positions/4/exit")
        data = response.json()

        assert response.status_code == 200
        assert data["success"] is True

        # Verify trade type was SELL_NO for NO outcome positions
        saved_trade = mock_trade_repo.save.call_args[0][0]
        assert saved_trade.trade_type == TradeType.SELL_NO

    def test_manual_exit_zero_initial_value(
        self,
        client_with_both_repos: TestClient,
        mock_position_repo: MagicMock,
    ) -> None:
        """Test manual exit handles position with no initial value."""
        position_no_initial = Position(
            id=5,
            market_id="market-005",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.50,
            initial_value=None,  # No initial value
            current_value=50.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime(2026, 2, 13, 10, 0, 0),
            closed_at=None,
        )
        mock_position_repo.get_by_id.return_value = position_no_initial
        mock_position_repo.update.return_value = position_no_initial

        response = client_with_both_repos.post("/api/positions/5/exit")
        data = response.json()

        assert response.status_code == 200
        assert data["success"] is True
        # realized_pnl should be None when initial_value is None
        assert data["data"]["realized_pnl"] is None
