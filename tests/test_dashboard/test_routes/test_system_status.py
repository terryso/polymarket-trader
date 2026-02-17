"""Tests for system status API routes.

This module contains tests for the system status API endpoints,
including /status and /settings endpoints.

Story 7.5: 系统状态 API
"""

import os
from datetime import datetime
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.state import StateSnapshot


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings with default test values."""
    settings = MagicMock()
    settings.trading_mode = "paper"
    settings.log_level = "INFO"
    settings.initial_capital = 200.0
    settings.trading = MagicMock()
    settings.trading.initial_capital = 200.0
    settings.trading.trade_unit = 10.0
    settings.risk = MagicMock()
    settings.risk.max_single_ratio = 0.2
    settings.risk.min_confidence = 0.75
    settings.risk.min_edge = 0.1
    settings.risk.daily_loss_limit = 0.3
    settings.risk.max_open_markets = 3
    settings.llm = MagicMock()
    settings.llm.model = "glm-4"
    settings.llm.api_base = "https://open.bigmodel.cn/api/paas/v4"
    settings.llm.api_key = "test-api-key-12345"
    settings.polymarket = MagicMock()
    settings.polymarket.proxy_wallet = "0x1234567890abcdef1234567890abcdef12345678"
    return settings


@pytest.fixture(autouse=True)
def reset_settings_env() -> Generator[None, None, None]:
    """Reset settings environment variables and cache for each test."""
    # Clear settings cache
    from src.config import get_settings

    get_settings.cache_clear()

    # Save and clear relevant env vars
    saved_env = {}
    env_keys = ["TRADING_MODE", "LLM_API_BASE", "LLM_MODEL", "LLM_API_KEY"]
    for key in env_keys:
        if key in os.environ:
            saved_env[key] = os.environ[key]

    yield

    # Restore env vars
    for key in env_keys:
        if key in os.environ:
            del os.environ[key]
    for key, val in saved_env.items():
        os.environ[key] = val

    # Clear cache again
    get_settings.cache_clear()


@pytest.fixture
def sample_state_snapshot() -> StateSnapshot:
    """Create sample state snapshot for testing."""
    return StateSnapshot(
        current_capital=180.50,
        daily_pnl=-5.50,
        consecutive_losses=1,
        open_positions_count=2,
        trading_enabled=True,
        reduced_mode=False,
        updated_at=datetime(2026, 2, 15, 10, 30, 0),
    )


@pytest.fixture
def mock_state() -> MagicMock:
    """Create a mock ThreadSafeState for testing."""
    state = MagicMock()
    state.get_state = AsyncMock()
    return state


@pytest.fixture
def client(mock_state: MagicMock, mock_settings: MagicMock) -> Generator[TestClient, None, None]:
    """Create test client with mocked dependencies."""
    with patch("src.dashboard.app.init_db", new_callable=AsyncMock):
        with patch("src.dashboard.app.close_db", new_callable=AsyncMock):
            with patch(
                "src.dashboard.routes.statistics.get_last_market_fetch",
                new_callable=AsyncMock,
            ) as mock_fetch:
                mock_fetch.return_value = datetime(2026, 2, 15, 10, 30, 0)

                def mock_get_state() -> MagicMock:
                    return mock_state

                from src.dashboard.app import app
                from src.dashboard.routes.statistics import get_state

                app.dependency_overrides[get_state] = mock_get_state

                # Mock settings in the statistics module
                with patch("src.dashboard.routes.statistics.settings", mock_settings):
                    with TestClient(app, raise_server_exceptions=False) as c:
                        yield c

                app.dependency_overrides.clear()


class TestGetSystemStatus:
    """Tests for GET /api/statistics/status endpoint."""

    def test_get_status_returns_200(
        self,
        client: TestClient,
        mock_state: MagicMock,
        sample_state_snapshot: StateSnapshot,
    ) -> None:
        """Test status endpoint returns 200."""
        mock_state.get_state.return_value = sample_state_snapshot
        response = client.get("/api/statistics/status")
        assert response.status_code == 200

    def test_get_status_format(
        self,
        client: TestClient,
        mock_state: MagicMock,
        sample_state_snapshot: StateSnapshot,
    ) -> None:
        """Test response format."""
        mock_state.get_state.return_value = sample_state_snapshot
        response = client.get("/api/statistics/status")
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert data["success"] is True

    def test_get_status_required_fields(
        self,
        client: TestClient,
        mock_state: MagicMock,
        sample_state_snapshot: StateSnapshot,
    ) -> None:
        """Test required fields exist in response."""
        mock_state.get_state.return_value = sample_state_snapshot
        response = client.get("/api/statistics/status")
        data = response.json()
        assert "trading_enabled" in data["data"]
        assert "mode" in data["data"]
        assert "current_capital" in data["data"]
        assert "daily_pnl" in data["data"]
        assert "open_positions" in data["data"]
        assert "consecutive_losses" in data["data"]
        assert "reduced_mode" in data["data"]

    def test_get_status_values(
        self,
        client: TestClient,
        mock_state: MagicMock,
        sample_state_snapshot: StateSnapshot,
    ) -> None:
        """Test status values are correct."""
        mock_state.get_state.return_value = sample_state_snapshot
        response = client.get("/api/statistics/status")
        data = response.json()
        assert data["data"]["trading_enabled"] is True
        assert data["data"]["mode"] == "PAPER"
        assert data["data"]["current_capital"] == 180.50
        assert data["data"]["daily_pnl"] == -5.50
        assert data["data"]["open_positions"] == 2
        assert data["data"]["consecutive_losses"] == 1
        assert data["data"]["reduced_mode"] is False

    def test_get_status_uptime_hours(
        self,
        client: TestClient,
        mock_state: MagicMock,
        sample_state_snapshot: StateSnapshot,
    ) -> None:
        """Test uptime_hours field exists and is numeric."""
        mock_state.get_state.return_value = sample_state_snapshot
        response = client.get("/api/statistics/status")
        data = response.json()
        assert "uptime_hours" in data["data"]
        assert isinstance(data["data"]["uptime_hours"], (int, float))
        assert data["data"]["uptime_hours"] >= 0

    def test_get_status_last_market_fetch(
        self,
        client: TestClient,
        mock_state: MagicMock,
        sample_state_snapshot: StateSnapshot,
    ) -> None:
        """Test last_market_fetch field exists."""
        mock_state.get_state.return_value = sample_state_snapshot
        response = client.get("/api/statistics/status")
        data = response.json()
        assert "last_market_fetch" in data["data"]

    def test_get_status_trading_disabled(
        self,
        client: TestClient,
        mock_state: MagicMock,
    ) -> None:
        """Test status when trading is disabled."""
        disabled_snapshot = StateSnapshot(
            current_capital=100.0,
            daily_pnl=-20.0,
            consecutive_losses=3,
            open_positions_count=0,
            trading_enabled=False,
            reduced_mode=True,
            updated_at=datetime(2026, 2, 15, 10, 30, 0),
        )
        mock_state.get_state.return_value = disabled_snapshot
        response = client.get("/api/statistics/status")
        data = response.json()
        assert data["data"]["trading_enabled"] is False
        assert data["data"]["reduced_mode"] is True


class TestGetSettings:
    """Tests for GET /api/statistics/settings endpoint."""

    def test_get_settings_returns_200(self, client: TestClient) -> None:
        """Test settings endpoint returns 200."""
        response = client.get("/api/statistics/settings")
        assert response.status_code == 200

    def test_get_settings_format(self, client: TestClient) -> None:
        """Test response format."""
        response = client.get("/api/statistics/settings")
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert data["success"] is True

    def test_get_settings_required_fields(self, client: TestClient) -> None:
        """Test required fields exist in response."""
        response = client.get("/api/statistics/settings")
        data = response.json()
        assert "trading_mode" in data["data"]
        assert "initial_capital" in data["data"]
        assert "trade_unit" in data["data"]
        assert "max_single_ratio" in data["data"]
        assert "min_confidence" in data["data"]
        assert "min_edge" in data["data"]
        assert "daily_loss_limit" in data["data"]
        assert "max_open_markets" in data["data"]
        assert "llm_model" in data["data"]
        assert "llm_api_base" in data["data"]
        assert "llm_api_key" in data["data"]
        assert "polymarket_pk" in data["data"]
        assert "proxy_wallet" in data["data"]

    def test_get_settings_api_key_masked(self, client: TestClient) -> None:
        """Test API Key is masked properly."""
        response = client.get("/api/statistics/settings")
        data = response.json()
        api_key = data["data"]["llm_api_key"]
        # Should show first 4 chars + **** or [NOT_SET]
        assert "****" in api_key or api_key == "[NOT_SET]"

    def test_get_settings_private_key_fully_hidden(self, client: TestClient) -> None:
        """Test private key is fully hidden."""
        response = client.get("/api/statistics/settings")
        data = response.json()
        pk = data["data"]["polymarket_pk"]
        assert pk == "[REDACTED]"

    def test_get_settings_wallet_masked(self, client: TestClient) -> None:
        """Test wallet address is masked properly."""
        response = client.get("/api/statistics/settings")
        data = response.json()
        wallet = data["data"]["proxy_wallet"]
        # Should be masked or [NOT_SET]
        assert "..." in wallet or wallet == "[NOT_SET]"

    def test_get_settings_values(self, client: TestClient) -> None:
        """Test settings values match expected defaults."""
        response = client.get("/api/statistics/settings")
        data = response.json()
        # Check default values from config
        assert data["data"]["trading_mode"] == "PAPER"
        assert data["data"]["initial_capital"] == 200.0
        assert data["data"]["trade_unit"] == 10.0
        assert data["data"]["max_single_ratio"] == 0.20
        assert data["data"]["min_confidence"] == 0.75
        assert data["data"]["min_edge"] == 0.10
        assert data["data"]["daily_loss_limit"] == 0.30
        assert data["data"]["max_open_markets"] == 3


class TestMaskingFunctions:
    """Tests for the masking utility functions."""

    def test_mask_api_key_full_key(self) -> None:
        """Test masking a full API key."""
        from src.dashboard.routes.statistics import mask_api_key

        result = mask_api_key("sk-1234567890abcdef")
        assert result == "sk-1****"

    def test_mask_api_key_short_key(self) -> None:
        """Test masking a short API key."""
        from src.dashboard.routes.statistics import mask_api_key

        result = mask_api_key("abc")
        assert result == "abc****"

    def test_mask_api_key_empty(self) -> None:
        """Test masking an empty API key."""
        from src.dashboard.routes.statistics import mask_api_key

        result = mask_api_key("")
        assert result == "[NOT_SET]"

    def test_mask_private_key(self) -> None:
        """Test private key is always fully masked."""
        from src.dashboard.routes.statistics import mask_private_key

        result = mask_private_key()
        assert result == "[REDACTED]"

    def test_mask_wallet_address_full(self) -> None:
        """Test masking a full wallet address."""
        from src.dashboard.routes.statistics import mask_wallet_address

        result = mask_wallet_address("0x1234567890abcdef1234")
        assert result == "0x1234...1234"

    def test_mask_wallet_address_short(self) -> None:
        """Test masking a short wallet address."""
        from src.dashboard.routes.statistics import mask_wallet_address

        result = mask_wallet_address("0x12345")
        assert result == "0x1234..."

    def test_mask_wallet_address_very_short(self) -> None:
        """Test masking a very short wallet address."""
        from src.dashboard.routes.statistics import mask_wallet_address

        result = mask_wallet_address("0x1")
        assert result == "0x1..."

    def test_mask_wallet_address_empty(self) -> None:
        """Test masking an empty wallet address."""
        from src.dashboard.routes.statistics import mask_wallet_address

        result = mask_wallet_address("")
        assert result == "[NOT_SET]"
