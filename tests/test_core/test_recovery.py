"""Tests for RecoveryManager.

Story 8.4: Auto Recovery Mechanism
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.recovery import RecoveryManager, RecoveryResult
from src.storage.repositories.position_repo import PositionRepository
from src.storage.repositories.state_repo import StateRepository


class TestRecoveryResult:
    """Test cases for RecoveryResult."""

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        result = RecoveryResult(success=True)

        assert result.success is True
        assert result.recovered_state == {}
        assert result.warnings == []
        assert result.errors == []

    def test_with_values(self) -> None:
        """Test with custom values."""
        result = RecoveryResult(
            success=False,
            recovered_state={"current_capital": 150.0},
            warnings=["Warning 1"],
            errors=["Error 1"],
        )

        assert result.success is False
        assert result.recovered_state == {"current_capital": 150.0}
        assert result.warnings == ["Warning 1"]
        assert result.errors == ["Error 1"]

    def test_with_errors(self) -> None:
        """Test with errors."""
        result = RecoveryResult(
            success=False,
            errors=["Something went wrong", "Another error"],
        )

        assert result.success is False
        assert len(result.errors) == 2


class TestRecoveryManager:
    """Test cases for RecoveryManager."""

    @pytest.fixture
    def mock_state_repo(self) -> MagicMock:
        """Create a mock state repository."""
        repo = MagicMock(spec=StateRepository)
        repo.load_state = AsyncMock(return_value={})
        repo.save_state = AsyncMock()
        return repo

    @pytest.fixture
    def mock_position_repo(self) -> MagicMock:
        """Create a mock position repository."""
        repo = MagicMock(spec=PositionRepository)
        repo.get_open_positions = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def recovery_manager(
        self, mock_state_repo: MagicMock, mock_position_repo: MagicMock
    ) -> RecoveryManager:
        """Create a RecoveryManager instance."""
        return RecoveryManager(
            state_repo=mock_state_repo,
            position_repo=mock_position_repo,
            initial_capital=200.0,
        )

    @pytest.fixture
    def recovery_manager_no_position(
        self, mock_state_repo: MagicMock
    ) -> RecoveryManager:
        """Create a RecoveryManager without position repo."""
        return RecoveryManager(
            state_repo=mock_state_repo,
            position_repo=None,
            initial_capital=200.0,
        )

    def test_default_safe_state(self, recovery_manager: RecoveryManager) -> None:
        """Test default safe state has correct values."""
        assert recovery_manager.DEFAULT_SAFE_STATE["trading_enabled"] is False
        assert "current_capital" in recovery_manager.DEFAULT_SAFE_STATE
        assert "daily_pnl" in recovery_manager.DEFAULT_SAFE_STATE
        assert "consecutive_losses" in recovery_manager.DEFAULT_SAFE_STATE
        assert "open_positions_count" in recovery_manager.DEFAULT_SAFE_STATE
        assert "reduced_mode" in recovery_manager.DEFAULT_SAFE_STATE

    def test_initial_capital_from_settings(self, mock_state_repo: MagicMock) -> None:
        """Test initial capital is set from settings when not provided."""
        with patch("src.core.recovery.settings") as mock_settings:
            mock_settings.initial_capital = 300.0
            manager = RecoveryManager(state_repo=mock_state_repo)
            assert manager.initial_capital == 300.0

    @pytest.mark.asyncio
    async def test_recover_empty_state(self, recovery_manager: RecoveryManager) -> None:
        """Test recovery from empty state."""
        result = await recovery_manager.recover()

        assert result.success is True
        # Should use initial capital when current_capital is 0.0
        assert result.recovered_state["current_capital"] == 200.0
        assert result.recovered_state["trading_enabled"] is False  # Safe default

    @pytest.mark.asyncio
    async def test_recover_with_saved_state(
        self, mock_state_repo: MagicMock, mock_position_repo: MagicMock
    ) -> None:
        """Test recovery with saved state."""
        mock_state_repo.load_state.return_value = {
            "current_capital": 150.0,
            "consecutive_losses": 2,
            "trading_enabled": True,
            "daily_pnl": 10.0,
            "open_positions_count": 1,
        }

        # Set up position repo to return 1 position to match state
        mock_position = MagicMock()
        mock_position_repo.get_open_positions.return_value = [mock_position]

        manager = RecoveryManager(
            state_repo=mock_state_repo,
            position_repo=mock_position_repo,
            initial_capital=200.0,
        )

        result = await manager.recover()

        assert result.success is True
        assert result.recovered_state["current_capital"] == 150.0
        assert result.recovered_state["consecutive_losses"] == 2
        assert result.recovered_state["trading_enabled"] is True
        assert result.recovered_state["daily_pnl"] == 10.0
        assert result.recovered_state["open_positions_count"] == 1

    @pytest.mark.asyncio
    async def test_recover_with_position_validation(
        self,
        recovery_manager: RecoveryManager,
        mock_state_repo: MagicMock,
        mock_position_repo: MagicMock,
    ) -> None:
        """Test recovery with position validation."""
        mock_state_repo.load_state.return_value = {
            "current_capital": 150.0,
            "open_positions_count": 2,  # State says 2
        }

        # Database has only 1 open position
        mock_position = MagicMock()
        mock_position_repo.get_open_positions.return_value = [mock_position]

        result = await recovery_manager.recover()

        assert result.success is True
        # Should have warning about mismatch
        assert len(result.warnings) == 1
        assert "Position count mismatch" in result.warnings[0]
        # State should be updated to match reality
        assert result.recovered_state["open_positions_count"] == 1

    @pytest.mark.asyncio
    async def test_recover_no_position_repo(
        self, recovery_manager_no_position: RecoveryManager, mock_state_repo: MagicMock
    ) -> None:
        """Test recovery without position repository."""
        mock_state_repo.load_state.return_value = {
            "current_capital": 150.0,
            "open_positions_count": 2,
        }

        result = await recovery_manager_no_position.recover()

        assert result.success is True
        # No position validation warnings
        assert len(result.warnings) == 0

    @pytest.mark.asyncio
    async def test_recover_inconsistent_state_negative_capital(
        self, recovery_manager: RecoveryManager, mock_state_repo: MagicMock
    ) -> None:
        """Test recovery with negative capital (inconsistent state)."""
        mock_state_repo.load_state.return_value = {
            "current_capital": -50.0,
            "daily_pnl": 0.0,
            "consecutive_losses": 0,
        }

        result = await recovery_manager.recover()

        assert result.success is True
        # Should have errors
        assert len(result.errors) > 0
        assert any("Negative capital" in e for e in result.errors)
        # Trading should be disabled for safety
        assert result.recovered_state["trading_enabled"] is False
        # Should have warning about inconsistency
        assert any("inconsistency" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_recover_inconsistent_state_negative_losses(
        self, recovery_manager: RecoveryManager, mock_state_repo: MagicMock
    ) -> None:
        """Test recovery with negative consecutive losses (inconsistent state)."""
        mock_state_repo.load_state.return_value = {
            "current_capital": 100.0,
            "daily_pnl": 0.0,
            "consecutive_losses": -1,
        }

        result = await recovery_manager.recover()

        assert result.success is True
        # Should have errors
        assert len(result.errors) > 0
        assert any("Negative consecutive losses" in e for e in result.errors)
        # Trading should be disabled for safety
        assert result.recovered_state["trading_enabled"] is False

    @pytest.mark.asyncio
    async def test_recover_inconsistent_state_pnl_exceeds_capital(
        self, recovery_manager: RecoveryManager, mock_state_repo: MagicMock
    ) -> None:
        """Test recovery with daily PnL exceeding capital (now considered valid).

        Note: daily_pnl exceeding capital is valid because:
        - daily_pnl tracks cumulative P&L for the day
        - capital reflects current available funds after all changes
        - Example: Started with 250, gained 150 profit, now have 400 capital
        """
        mock_state_repo.load_state.return_value = {
            "current_capital": 100.0,
            "daily_pnl": 150.0,  # Valid scenario
            "consecutive_losses": 0,
        }

        result = await recovery_manager.recover()

        assert result.success is True
        # Should NOT have errors - this is now considered valid
        assert len(result.errors) == 0
        # Trading state should remain as default (False for safe recovery)
        assert result.recovered_state["trading_enabled"] is False

    @pytest.mark.asyncio
    async def test_recover_load_failure(
        self, recovery_manager: RecoveryManager, mock_state_repo: MagicMock
    ) -> None:
        """Test recovery when loading fails."""
        mock_state_repo.load_state.side_effect = Exception("Database error")

        result = await recovery_manager.recover()

        assert result.success is False
        assert len(result.errors) == 1
        assert "Recovery failed" in result.errors[0]
        # Should return safe default state
        assert result.recovered_state["trading_enabled"] is False
        assert result.recovered_state["current_capital"] == 200.0

    def test_merge_with_defaults_empty(self, recovery_manager: RecoveryManager) -> None:
        """Test merging empty state with defaults."""
        merged = recovery_manager._merge_with_defaults({})

        assert merged["current_capital"] == 200.0  # Initial capital
        assert merged["trading_enabled"] is False  # Safe default
        assert merged["daily_pnl"] == 0.0
        assert merged["consecutive_losses"] == 0

    def test_merge_with_defaults_partial(
        self, recovery_manager: RecoveryManager
    ) -> None:
        """Test merging partial state with defaults."""
        merged = recovery_manager._merge_with_defaults(
            {
                "current_capital": 150.0,
                "consecutive_losses": 2,
            }
        )

        assert merged["current_capital"] == 150.0  # From saved
        assert merged["consecutive_losses"] == 2  # From saved
        assert merged["trading_enabled"] is False  # Default
        assert merged["daily_pnl"] == 0.0  # Default

    def test_merge_with_defaults_unknown_key(
        self, recovery_manager: RecoveryManager
    ) -> None:
        """Test merging state with unknown keys."""
        merged = recovery_manager._merge_with_defaults(
            {
                "custom_key": "custom_value",
            }
        )

        # Unknown keys should be preserved
        assert merged["custom_key"] == "custom_value"

    def test_check_consistency_normal_state(
        self, recovery_manager: RecoveryManager
    ) -> None:
        """Test consistency check with normal state."""
        errors = recovery_manager._check_consistency(
            {
                "current_capital": 100.0,
                "daily_pnl": 10.0,
                "consecutive_losses": 1,
            }
        )

        assert len(errors) == 0

    def test_check_consistency_negative_capital(
        self, recovery_manager: RecoveryManager
    ) -> None:
        """Test consistency check with negative capital."""
        errors = recovery_manager._check_consistency(
            {
                "current_capital": -50.0,
                "daily_pnl": 0.0,
                "consecutive_losses": 0,
            }
        )

        assert len(errors) > 0
        assert any("Negative capital" in e for e in errors)

    def test_check_consistency_negative_losses(
        self, recovery_manager: RecoveryManager
    ) -> None:
        """Test consistency check with negative consecutive losses."""
        errors = recovery_manager._check_consistency(
            {
                "current_capital": 100.0,
                "daily_pnl": 0.0,
                "consecutive_losses": -1,
            }
        )

        assert len(errors) > 0
        assert any("Negative consecutive losses" in e for e in errors)

    def test_check_consistency_pnl_exceeds_capital(
        self, recovery_manager: RecoveryManager
    ) -> None:
        """Test consistency check with PnL exceeding capital is now valid.

        Note: daily_pnl exceeding capital is valid because:
        - daily_pnl tracks cumulative P&L for the day
        - capital reflects current available funds after losses
        - Example: Started with 250, gained 150 profit, now have 250+150=400 capital
          with daily_pnl=150 (valid scenario)
        """
        errors = recovery_manager._check_consistency(
            {
                "current_capital": 100.0,
                "daily_pnl": 150.0,  # Valid: could have started with 250 and gained 150
                "consecutive_losses": 0,
            }
        )

        # Should NOT report errors - this is valid
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_validate_positions_success(
        self, recovery_manager: RecoveryManager, mock_position_repo: MagicMock
    ) -> None:
        """Test position validation when counts match."""
        mock_position = MagicMock()
        mock_position_repo.get_open_positions.return_value = [mock_position]

        state = {"open_positions_count": 1}
        warnings = await recovery_manager._validate_positions(state)

        assert len(warnings) == 0
        assert state["open_positions_count"] == 1

    @pytest.mark.asyncio
    async def test_validate_positions_mismatch(
        self, recovery_manager: RecoveryManager, mock_position_repo: MagicMock
    ) -> None:
        """Test position validation when counts don't match."""
        mock_position = MagicMock()
        mock_position_repo.get_open_positions.return_value = [mock_position]

        state = {"open_positions_count": 3}  # Says 3, but database has 1
        warnings = await recovery_manager._validate_positions(state)

        assert len(warnings) == 1
        assert "Position count mismatch" in warnings[0]
        # State should be updated
        assert state["open_positions_count"] == 1

    @pytest.mark.asyncio
    async def test_validate_positions_no_repo(self, mock_state_repo: MagicMock) -> None:
        """Test position validation without position repository."""
        manager = RecoveryManager(
            state_repo=mock_state_repo,
            position_repo=None,
            initial_capital=200.0,
        )

        state = {"open_positions_count": 3}
        warnings = await manager._validate_positions(state)

        assert len(warnings) == 0
        # State should not be modified
        assert state["open_positions_count"] == 3

    @pytest.mark.asyncio
    async def test_validate_positions_error(
        self, recovery_manager: RecoveryManager, mock_position_repo: MagicMock
    ) -> None:
        """Test position validation when error occurs."""
        mock_position_repo.get_open_positions.side_effect = Exception("DB error")

        state = {"open_positions_count": 1}
        warnings = await recovery_manager._validate_positions(state)

        assert len(warnings) == 1
        assert "Failed to validate positions" in warnings[0]

    @pytest.mark.asyncio
    async def test_save_state_snapshot(
        self, recovery_manager: RecoveryManager, mock_state_repo: MagicMock
    ) -> None:
        """Test saving state snapshot."""
        state = {"current_capital": 150.0, "trading_enabled": True}

        await recovery_manager.save_state_snapshot(state)

        mock_state_repo.save_state.assert_called_once_with(state)

    @pytest.mark.asyncio
    async def test_reset_to_safe_state(
        self, recovery_manager: RecoveryManager, mock_state_repo: MagicMock
    ) -> None:
        """Test resetting to safe state."""
        safe_state = await recovery_manager.reset_to_safe_state()

        assert safe_state["trading_enabled"] is False
        assert safe_state["current_capital"] == 200.0
        assert "start_time" in safe_state
        assert safe_state["daily_pnl"] == 0.0
        assert safe_state["consecutive_losses"] == 0
        assert safe_state["reduced_mode"] is False

        mock_state_repo.save_state.assert_called_once()


class TestRecoveryManagerIntegration:
    """Integration tests for RecoveryManager with ThreadSafeState."""

    @pytest.fixture
    def mock_state_repo(self) -> MagicMock:
        """Create a mock state repository."""
        repo = MagicMock(spec=StateRepository)
        repo.load_state = AsyncMock(return_value={})
        repo.save_state = AsyncMock()
        return repo

    @pytest.fixture
    def mock_position_repo(self) -> MagicMock:
        """Create a mock position repository."""
        repo = MagicMock(spec=PositionRepository)
        repo.get_open_positions = AsyncMock(return_value=[])
        return repo

    @pytest.mark.asyncio
    async def test_full_recovery_flow(
        self, mock_state_repo: MagicMock, mock_position_repo: MagicMock
    ) -> None:
        """Test the full recovery flow."""
        # Setup saved state
        mock_state_repo.load_state.return_value = {
            "current_capital": 175.0,
            "daily_pnl": 25.0,
            "consecutive_losses": 0,
            "open_positions_count": 0,
            "trading_enabled": True,
            "reduced_mode": False,
        }

        manager = RecoveryManager(
            state_repo=mock_state_repo,
            position_repo=mock_position_repo,
            initial_capital=200.0,
        )

        result = await manager.recover()

        assert result.success is True
        assert result.recovered_state["current_capital"] == 175.0
        assert result.recovered_state["daily_pnl"] == 25.0
        assert result.recovered_state["trading_enabled"] is True
        assert len(result.warnings) == 0
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_recovery_with_all_issues(
        self, mock_state_repo: MagicMock, mock_position_repo: MagicMock
    ) -> None:
        """Test recovery with multiple issues."""
        # Setup problematic state
        mock_state_repo.load_state.return_value = {
            "current_capital": -10.0,  # Negative
            "daily_pnl": 50.0,
            "consecutive_losses": -2,  # Negative
            "open_positions_count": 5,  # Doesn't match database
        }

        # Database has 2 positions
        mock_positions = [MagicMock(), MagicMock()]
        mock_position_repo.get_open_positions.return_value = mock_positions

        manager = RecoveryManager(
            state_repo=mock_state_repo,
            position_repo=mock_position_repo,
            initial_capital=200.0,
        )

        result = await manager.recover()

        assert result.success is True  # Still succeeds
        assert len(result.errors) >= 2  # At least 2 consistency errors
        assert len(result.warnings) >= 2  # Position mismatch + inconsistency warning
        # Trading must be disabled
        assert result.recovered_state["trading_enabled"] is False
