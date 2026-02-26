"""Tests for Story 7.9: Trade history realtime by mode.

This module contains failing tests (TDD RED phase) for the trade history
mode-based data source feature.

Story 7.9: 交易历史按模式实时显示

These tests are designed to FAIL until the feature is implemented.
Run with: pytest tests/test_dashboard/test_routes/test_trades_story79.py -v
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.models.trade import Trade, TradeMode, TradeStatus, TradeType


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def sample_paper_trades() -> list[Trade]:
    """Create sample paper trades for testing."""
    return [
        Trade(
            id=1,
            market_id="market-paper-001",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=100.0,
            price=0.45,
            shares=222.22,
            status=TradeStatus.FILLED,
            created_at=datetime(2026, 2, 27, 10, 0, 0),
        ),
        Trade(
            id=2,
            market_id="market-paper-002",
            trade_type=TradeType.SELL_NO,
            mode=TradeMode.PAPER,
            amount=50.0,
            price=0.35,
            shares=142.86,
            status=TradeStatus.FILLED,
            created_at=datetime(2026, 2, 27, 11, 0, 0),
        ),
    ]


@pytest.fixture
def mock_settings_paper():
    """Mock settings with trading_mode=paper."""
    with patch("src.config._SettingsProxy") as mock_proxy:
        settings = MagicMock()
        settings.trading_mode = "paper"
        mock_proxy.return_value = settings
        yield settings


@pytest.fixture
def mock_settings_live():
    """Mock settings with trading_mode=live."""
    with patch("src.config._SettingsProxy") as mock_proxy:
        settings = MagicMock()
        settings.trading_mode = "live"
        mock_proxy.return_value = settings
        yield settings


@pytest.fixture
def mock_trade_repo() -> MagicMock:
    """Create a mock TradeRepository for testing."""
    repo = MagicMock()
    repo.get_recent = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_mode = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_polymarket_client():
    """Create a mock PolymarketClient for testing."""
    with patch("src.api.polymarket.PolymarketClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def client(mock_trade_repo: MagicMock) -> TestClient:
    """Create test client with mocked dependencies."""
    with patch("src.dashboard.app.init_db", new_callable=AsyncMock):
        with patch("src.dashboard.app.close_db", new_callable=AsyncMock):
            from src.dashboard.app import app
            from src.dashboard.routes.trades import get_trade_repository

            def mock_get_trade_repository() -> MagicMock:
                return mock_trade_repo

            app.dependency_overrides[get_trade_repository] = mock_get_trade_repository

            with TestClient(app, raise_server_exceptions=False) as c:
                yield c

            app.dependency_overrides.clear()


# ==============================================================================
# TEST: Paper Mode Returns Local Data (P0)
# ==============================================================================


class TestPaperModeReturnsLocalData:
    """Tests for paper mode returning local database data.

    RED PHASE: These tests will fail until the feature is implemented.
    """

    @pytest.mark.skip(reason="RED PHASE: Feature not implemented - Story 7.9")
    def test_paper_mode_uses_local_database(
        self,
        client: TestClient,
        mock_settings_paper,
        mock_trade_repo: MagicMock,
        sample_paper_trades: list[Trade],
    ) -> None:
        """Test that paper mode returns data from local database.

        Expected behavior:
        - Read settings.trading_mode
        - When mode='paper', call TradeRepository.get_by_mode(TradeMode.PAPER)
        - Return trades from local database
        """
        mock_trade_repo.get_by_mode.return_value = sample_paper_trades

        response = client.get("/api/trades")

        assert response.status_code == 200
        data = response.json()

        # Should have called get_by_mode with PAPER
        mock_trade_repo.get_by_mode.assert_called_once_with(TradeMode.PAPER)

        # Should return paper trades
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["data"][0]["mode"] == "PAPER"

    @pytest.mark.skip(reason="RED PHASE: Feature not implemented - Story 7.9")
    def test_paper_mode_ignores_mode_query_param(
        self,
        client: TestClient,
        mock_settings_paper,
        mock_trade_repo: MagicMock,
        sample_paper_trades: list[Trade],
    ) -> None:
        """Test that paper mode ignores mode query parameter.

        Expected behavior:
        - Mode is determined by settings.trading_mode, not query param
        - Query param should be ignored or removed
        """
        mock_trade_repo.get_by_mode.return_value = sample_paper_trades

        # Try to request live mode via query param (should be ignored)
        response = client.get("/api/trades?mode=live")

        assert response.status_code == 200
        data = response.json()

        # Should still return PAPER trades (settings override query param)
        mock_trade_repo.get_by_mode.assert_called_once_with(TradeMode.PAPER)
        for trade in data["data"]:
            assert trade["mode"] == "PAPER"


# ==============================================================================
# TEST: Live Mode Calls Polymarket API (P0)
# ==============================================================================


class TestLiveModeCallsPolymarketAPI:
    """Tests for live mode calling Polymarket API.

    RED PHASE: These tests will fail until the feature is implemented.
    """

    @pytest.mark.skip(reason="RED PHASE: Feature not implemented - Story 7.9")
    def test_live_mode_calls_polymarket_api(
        self,
        client: TestClient,
        mock_settings_live,
        mock_polymarket_client,
    ) -> None:
        """Test that live mode calls PolymarketClient.get_order_history().

        Expected behavior:
        - Read settings.trading_mode
        - When mode='live', call PolymarketClient.get_order_history()
        - Convert OrderHistoryResult to TradeListItem format
        """
        # Mock successful API response
        from src.api.polymarket import OrderHistoryItem, OrderHistoryResult

        mock_orders = [
            OrderHistoryItem(
                id="order-001",
                market_id="market-live-001",
                side="BUY",
                size=100.0,
                price=0.55,
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            ),
        ]
        mock_polymarket_client.get_order_history.return_value = OrderHistoryResult(
            is_success=True,
            orders=mock_orders,
            cursor=None,
        )

        response = client.get("/api/trades")

        assert response.status_code == 200
        data = response.json()

        # Should have called Polymarket API
        mock_polymarket_client.get_order_history.assert_called_once()

        # Should return converted trades
        assert data["success"] is True
        assert len(data["data"]) >= 1

    @pytest.mark.skip(reason="RED PHASE: Feature not implemented - Story 7.9")
    def test_live_mode_converts_order_to_trade_format(
        self,
        client: TestClient,
        mock_settings_live,
        mock_polymarket_client,
    ) -> None:
        """Test that Polymarket orders are converted to TradeListItem format.

        Expected behavior:
        - OrderHistoryItem should be converted to TradeListItem
        - All required fields should be populated
        """
        from src.api.polymarket import OrderHistoryItem, OrderHistoryResult

        mock_orders = [
            OrderHistoryItem(
                id="order-001",
                market_id="market-live-001",
                side="BUY",
                size=100.0,
                price=0.55,
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            ),
        ]
        mock_polymarket_client.get_order_history.return_value = OrderHistoryResult(
            is_success=True,
            orders=mock_orders,
            cursor=None,
        )

        response = client.get("/api/trades")
        data = response.json()

        # Check converted trade format
        trade = data["data"][0]
        assert "id" in trade
        assert "market_id" in trade
        assert "trade_type" in trade
        assert "mode" in trade
        assert trade["mode"] == "LIVE"  # Live mode should set LIVE
        assert "amount" in trade
        assert "price" in trade
        assert "shares" in trade


# ==============================================================================
# TEST: Live Mode Handles API Error (P1)
# ==============================================================================


class TestLiveModeHandlesAPIError:
    """Tests for live mode error handling.

    RED PHASE: These tests will fail until the feature is implemented.
    """

    @pytest.mark.skip(reason="RED PHASE: Feature not implemented - Story 7.9")
    def test_live_mode_handles_api_failure(
        self,
        client: TestClient,
        mock_settings_live,
        mock_polymarket_client,
    ) -> None:
        """Test that API failures are handled gracefully.

        Expected behavior:
        - If Polymarket API fails, return error response
        - Include error message in response
        """
        from src.api.polymarket import OrderHistoryResult

        mock_polymarket_client.get_order_history.return_value = OrderHistoryResult(
            is_success=False,
            orders=[],
            error="API connection failed",
        )

        response = client.get("/api/trades")

        # Should return error response (not crash)
        assert response.status_code in [200, 500, 503]
        data = response.json()

        # Should indicate failure
        assert data.get("success") is False or len(data.get("data", [])) == 0

    @pytest.mark.skip(reason="RED PHASE: Feature not implemented - Story 7.9")
    def test_live_mode_handles_missing_credentials(
        self,
        client: TestClient,
        mock_settings_live,
        mock_polymarket_client,
    ) -> None:
        """Test handling when API credentials are not configured.

        Expected behavior:
        - If credentials missing, return helpful error message
        """
        from src.api.polymarket import OrderHistoryResult

        mock_polymarket_client.get_order_history.return_value = OrderHistoryResult(
            is_success=False,
            orders=[],
            error="API credentials not configured",
        )

        response = client.get("/api/trades")

        assert response.status_code in [200, 500, 503]


# ==============================================================================
# TEST: Sync Endpoints Removed or Deprecated (P2)
# ==============================================================================


class TestSyncEndpointsRemoved:
    """Tests for sync endpoint removal.

    RED PHASE: These tests will fail until the feature is implemented.
    """

    @pytest.mark.skip(reason="RED PHASE: Feature not implemented - Story 7.9")
    def test_sync_endpoint_removed_or_deprecated(self, client: TestClient) -> None:
        """Test that sync endpoint is removed or returns deprecated status.

        Expected behavior:
        - Either return 404 (removed) or 410/200 with deprecation notice
        """
        response = client.post("/api/trades/sync")

        # Should either be removed (404) or deprecated (410 or 200 with warning)
        assert response.status_code in [404, 410, 200]

        if response.status_code == 200:
            data = response.json()
            # If still available, should indicate deprecation
            assert data.get("deprecated") is True or "deprecated" in str(data).lower()

    @pytest.mark.skip(reason="RED PHASE: Feature not implemented - Story 7.9")
    def test_sync_status_endpoint_removed_or_deprecated(
        self, client: TestClient
    ) -> None:
        """Test that sync status endpoint is removed or returns deprecated status.

        Expected behavior:
        - Either return 404 (removed) or 410/200 with deprecation notice
        """
        response = client.get("/api/trades/sync/status")

        # Should either be removed (404) or deprecated (410 or 200 with warning)
        assert response.status_code in [404, 410, 200]

        if response.status_code == 200:
            data = response.json()
            # If still available, should indicate deprecation
            assert data.get("deprecated") is True or "deprecated" in str(data).lower()
