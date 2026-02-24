"""Tests for settings API routes.

This module contains tests for the settings API endpoints,
including exit strategy configuration.

Story 10.6: Dashboard 退出策略管理
"""

from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_exit_strategy_settings() -> MagicMock:
    """Create mock exit strategy settings for testing."""
    settings = MagicMock()
    settings.take_profit_enabled = True
    settings.take_profit_pct = 0.50
    settings.stop_loss_enabled = True
    settings.stop_loss_pct = -0.30
    settings.time_exit_enabled = True
    settings.time_exit_hours = 72
    settings.signal_exit_enabled = True
    settings.exit_check_interval_minutes = 1
    return settings


@pytest.fixture
def mock_settings(mock_exit_strategy_settings: MagicMock) -> MagicMock:
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.exit_strategy = mock_exit_strategy_settings
    return settings


@pytest.fixture
def client(mock_settings: MagicMock) -> Generator[TestClient, None, None]:
    """Create test client with mocked dependencies."""
    with patch("src.dashboard.app.init_db", new_callable=AsyncMock):
        with patch("src.dashboard.app.close_db", new_callable=AsyncMock):
            with patch(
                "src.dashboard.routes.settings.settings", mock_settings
            ):
                from src.dashboard.app import app

                with TestClient(app, raise_server_exceptions=False) as c:
                    yield c


class TestGetExitStrategyConfig:
    """Tests for the GET /api/settings/exit-strategy endpoint."""

    def test_get_exit_strategy_config_returns_200(
        self,
        client: TestClient,
    ) -> None:
        """Test get exit strategy config returns 200."""
        response = client.get("/api/settings/exit-strategy")

        assert response.status_code == 200

    def test_get_exit_strategy_config_returns_success(
        self,
        client: TestClient,
    ) -> None:
        """Test get exit strategy config returns success status."""
        response = client.get("/api/settings/exit-strategy")
        data = response.json()

        assert data["success"] is True

    def test_get_exit_strategy_config_returns_data(
        self,
        client: TestClient,
        mock_exit_strategy_settings: MagicMock,
    ) -> None:
        """Test get exit strategy config returns correct data."""
        response = client.get("/api/settings/exit-strategy")
        data = response.json()

        assert "data" in data
        config = data["data"]

        # Verify all expected fields are present
        assert "take_profit_enabled" in config
        assert "take_profit_pct" in config
        assert "stop_loss_enabled" in config
        assert "stop_loss_pct" in config
        assert "time_exit_enabled" in config
        assert "time_exit_hours" in config
        assert "signal_exit_enabled" in config
        assert "exit_check_interval_minutes" in config

        # Verify values match mock
        assert config["take_profit_enabled"] == mock_exit_strategy_settings.take_profit_enabled
        assert config["take_profit_pct"] == mock_exit_strategy_settings.take_profit_pct
        assert config["stop_loss_enabled"] == mock_exit_strategy_settings.stop_loss_enabled
        assert config["stop_loss_pct"] == mock_exit_strategy_settings.stop_loss_pct
        assert config["time_exit_enabled"] == mock_exit_strategy_settings.time_exit_enabled
        assert config["time_exit_hours"] == mock_exit_strategy_settings.time_exit_hours
        assert config["signal_exit_enabled"] == mock_exit_strategy_settings.signal_exit_enabled
        assert config["exit_check_interval_minutes"] == mock_exit_strategy_settings.exit_check_interval_minutes

    def test_get_exit_strategy_config_no_error(
        self,
        client: TestClient,
    ) -> None:
        """Test get exit strategy config has no error."""
        response = client.get("/api/settings/exit-strategy")
        data = response.json()

        assert data["error"] is None


class TestUpdateExitStrategyConfig:
    """Tests for the PUT /api/settings/exit-strategy endpoint."""

    def test_update_exit_strategy_config_returns_200(
        self,
        client: TestClient,
        mock_exit_strategy_settings: MagicMock,
    ) -> None:
        """Test update exit strategy config returns 200."""
        response = client.put(
            "/api/settings/exit-strategy",
            json={"take_profit_pct": 0.60},
        )

        assert response.status_code == 200

    def test_update_exit_strategy_config_returns_success(
        self,
        client: TestClient,
        mock_exit_strategy_settings: MagicMock,
    ) -> None:
        """Test update exit strategy config returns success status."""
        response = client.put(
            "/api/settings/exit-strategy",
            json={"take_profit_pct": 0.60},
        )
        data = response.json()

        assert data["success"] is True

    def test_update_take_profit_pct(
        self,
        client: TestClient,
        mock_exit_strategy_settings: MagicMock,
    ) -> None:
        """Test updating take profit percentage."""
        response = client.put(
            "/api/settings/exit-strategy",
            json={"take_profit_pct": 0.60},
        )
        data = response.json()

        assert response.status_code == 200
        assert data["data"]["take_profit_pct"] == 0.60

    def test_update_stop_loss_pct(
        self,
        client: TestClient,
        mock_exit_strategy_settings: MagicMock,
    ) -> None:
        """Test updating stop loss percentage."""
        response = client.put(
            "/api/settings/exit-strategy",
            json={"stop_loss_pct": -0.25},
        )
        data = response.json()

        assert response.status_code == 200
        assert data["data"]["stop_loss_pct"] == -0.25

    def test_update_time_exit_hours(
        self,
        client: TestClient,
        mock_exit_strategy_settings: MagicMock,
    ) -> None:
        """Test updating time exit hours."""
        response = client.put(
            "/api/settings/exit-strategy",
            json={"time_exit_hours": 48},
        )
        data = response.json()

        assert response.status_code == 200
        assert data["data"]["time_exit_hours"] == 48

    def test_update_multiple_fields(
        self,
        client: TestClient,
        mock_exit_strategy_settings: MagicMock,
    ) -> None:
        """Test updating multiple fields at once."""
        response = client.put(
            "/api/settings/exit-strategy",
            json={
                "take_profit_enabled": False,
                "take_profit_pct": 0.75,
                "stop_loss_enabled": False,
            },
        )
        data = response.json()

        assert response.status_code == 200
        assert data["data"]["take_profit_enabled"] is False
        assert data["data"]["take_profit_pct"] == 0.75
        assert data["data"]["stop_loss_enabled"] is False

    def test_update_toggles(
        self,
        client: TestClient,
        mock_exit_strategy_settings: MagicMock,
    ) -> None:
        """Test updating toggle settings."""
        response = client.put(
            "/api/settings/exit-strategy",
            json={
                "take_profit_enabled": False,
                "stop_loss_enabled": False,
                "time_exit_enabled": False,
                "signal_exit_enabled": False,
            },
        )
        data = response.json()

        assert response.status_code == 200
        assert data["data"]["take_profit_enabled"] is False
        assert data["data"]["stop_loss_enabled"] is False
        assert data["data"]["time_exit_enabled"] is False
        assert data["data"]["signal_exit_enabled"] is False

    def test_update_empty_body(
        self,
        client: TestClient,
        mock_exit_strategy_settings: MagicMock,
    ) -> None:
        """Test update with empty body returns current config."""
        response = client.put(
            "/api/settings/exit-strategy",
            json={},
        )
        data = response.json()

        assert response.status_code == 200
        assert data["success"] is True

    def test_update_invalid_take_profit_pct_too_high(
        self,
        client: TestClient,
    ) -> None:
        """Test update with invalid take profit percentage (too high)."""
        response = client.put(
            "/api/settings/exit-strategy",
            json={"take_profit_pct": 1.5},  # > 1
        )

        assert response.status_code == 422

    def test_update_invalid_take_profit_pct_negative(
        self,
        client: TestClient,
    ) -> None:
        """Test update with invalid take profit percentage (negative)."""
        response = client.put(
            "/api/settings/exit-strategy",
            json={"take_profit_pct": -0.1},  # < 0
        )

        assert response.status_code == 422

    def test_update_invalid_stop_loss_pct_too_low(
        self,
        client: TestClient,
    ) -> None:
        """Test update with invalid stop loss percentage (too low)."""
        response = client.put(
            "/api/settings/exit-strategy",
            json={"stop_loss_pct": -1.5},  # < -1
        )

        assert response.status_code == 422

    def test_update_invalid_stop_loss_pct_positive(
        self,
        client: TestClient,
    ) -> None:
        """Test update with invalid stop loss percentage (positive)."""
        response = client.put(
            "/api/settings/exit-strategy",
            json={"stop_loss_pct": 0.1},  # > 0
        )

        assert response.status_code == 422

    def test_update_invalid_time_exit_hours_zero(
        self,
        client: TestClient,
    ) -> None:
        """Test update with invalid time exit hours (zero)."""
        response = client.put(
            "/api/settings/exit-strategy",
            json={"time_exit_hours": 0},  # < 1
        )

        assert response.status_code == 422

    def test_update_invalid_time_exit_hours_negative(
        self,
        client: TestClient,
    ) -> None:
        """Test update with invalid time exit hours (negative)."""
        response = client.put(
            "/api/settings/exit-strategy",
            json={"time_exit_hours": -1},  # < 1
        )

        assert response.status_code == 422

    def test_update_invalid_exit_check_interval_zero(
        self,
        client: TestClient,
    ) -> None:
        """Test update with invalid exit check interval (zero)."""
        response = client.put(
            "/api/settings/exit-strategy",
            json={"exit_check_interval_minutes": 0},  # < 1
        )

        assert response.status_code == 422
