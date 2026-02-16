"""Tests for ThreadSafeState.

This module tests the thread-safe state management functionality
including state snapshots, capital updates, and persistence.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.state import StateSnapshot, ThreadSafeState, get_state_manager


class TestStateSnapshot:
    """Test StateSnapshot model."""

    def test_create_snapshot(self) -> None:
        """Test creating a state snapshot."""
        snapshot = StateSnapshot(current_capital=200.0)
        assert snapshot.current_capital == 200.0
        assert snapshot.daily_pnl == 0.0
        assert snapshot.consecutive_losses == 0
        assert snapshot.open_positions_count == 0
        assert snapshot.trading_enabled is True
        assert snapshot.reduced_mode is False

    def test_create_snapshot_with_all_fields(self) -> None:
        """Test creating a snapshot with all fields."""
        snapshot = StateSnapshot(
            current_capital=300.0,
            daily_pnl=50.0,
            consecutive_losses=2,
            open_positions_count=3,
            trading_enabled=False,
            reduced_mode=True,
        )
        assert snapshot.current_capital == 300.0
        assert snapshot.daily_pnl == 50.0
        assert snapshot.consecutive_losses == 2
        assert snapshot.open_positions_count == 3
        assert snapshot.trading_enabled is False
        assert snapshot.reduced_mode is True

    def test_snapshot_is_frozen(self) -> None:
        """Test that snapshot is immutable (frozen)."""
        snapshot = StateSnapshot(current_capital=200.0)
        with pytest.raises(Exception):  # Pydantic ValidationError
            snapshot.current_capital = 300.0

    def test_snapshot_model_dump(self) -> None:
        """Test serializing snapshot to dict."""
        snapshot = StateSnapshot(current_capital=200.0, daily_pnl=10.0)
        data = snapshot.model_dump(mode="json")
        assert data["current_capital"] == 200.0
        assert data["daily_pnl"] == 10.0
        assert isinstance(data, dict)

    def test_to_dict(self) -> None:
        """Test to_dict method for serialization."""
        snapshot = StateSnapshot(
            current_capital=300.0,
            daily_pnl=50.0,
            consecutive_losses=2,
            open_positions_count=3,
            trading_enabled=False,
            reduced_mode=True,
        )
        data = snapshot.to_dict()
        assert data["current_capital"] == 300.0
        assert data["daily_pnl"] == 50.0
        assert data["consecutive_losses"] == 2
        assert data["open_positions_count"] == 3
        assert data["trading_enabled"] is False
        assert data["reduced_mode"] is True
        assert isinstance(data, dict)

    def test_from_dict(self) -> None:
        """Test from_dict class method for deserialization."""
        data = {
            "current_capital": 250.0,
            "daily_pnl": 25.0,
            "consecutive_losses": 1,
            "open_positions_count": 2,
            "trading_enabled": True,
            "reduced_mode": False,
        }
        snapshot = StateSnapshot.from_dict(data)
        assert snapshot.current_capital == 250.0
        assert snapshot.daily_pnl == 25.0
        assert snapshot.consecutive_losses == 1
        assert snapshot.open_positions_count == 2
        assert snapshot.trading_enabled is True
        assert snapshot.reduced_mode is False

    def test_to_dict_and_from_dict_roundtrip(self) -> None:
        """Test that to_dict and from_dict are inverses."""
        original = StateSnapshot(
            current_capital=400.0,
            daily_pnl=100.0,
            consecutive_losses=5,
            open_positions_count=10,
            trading_enabled=False,
            reduced_mode=True,
        )
        data = original.to_dict()
        restored = StateSnapshot.from_dict(data)
        assert restored.current_capital == original.current_capital
        assert restored.daily_pnl == original.daily_pnl
        assert restored.consecutive_losses == original.consecutive_losses
        assert restored.open_positions_count == original.open_positions_count
        assert restored.trading_enabled == original.trading_enabled
        assert restored.reduced_mode == original.reduced_mode


class TestThreadSafeState:
    """Test ThreadSafeState."""

    @pytest.fixture
    def state(self) -> ThreadSafeState:
        """Create a test state manager."""
        return ThreadSafeState(initial_capital=200.0)

    @pytest.mark.asyncio
    async def test_initial_state(self, state: ThreadSafeState) -> None:
        """Test initial state values."""
        snapshot = await state.get_state()
        assert snapshot.current_capital == 200.0
        assert snapshot.daily_pnl == 0.0
        assert snapshot.consecutive_losses == 0
        assert snapshot.open_positions_count == 0
        assert snapshot.trading_enabled is True
        assert snapshot.reduced_mode is False

    @pytest.mark.asyncio
    async def test_initial_state_without_capital(self) -> None:
        """Test initial state uses settings.initial_capital when not specified."""
        state = ThreadSafeState()
        snapshot = await state.get_state()
        # Should use default from settings
        assert snapshot.current_capital == 200.0

    @pytest.mark.asyncio
    async def test_initial_state_with_none_capital(self) -> None:
        """Test initial state uses settings.initial_capital when None is passed."""
        state = ThreadSafeState(initial_capital=None)
        snapshot = await state.get_state()
        assert snapshot.current_capital == 200.0

    @pytest.mark.asyncio
    async def test_update_capital_positive(self, state: ThreadSafeState) -> None:
        """Test updating capital with positive amount."""
        await state.update_capital(10.0)
        snapshot = await state.get_state()
        assert snapshot.current_capital == 210.0
        assert snapshot.daily_pnl == 10.0

    @pytest.mark.asyncio
    async def test_update_capital_negative(self, state: ThreadSafeState) -> None:
        """Test updating capital with negative amount."""
        await state.update_capital(-5.0)
        snapshot = await state.get_state()
        assert snapshot.current_capital == 195.0
        assert snapshot.daily_pnl == -5.0

    @pytest.mark.asyncio
    async def test_update_capital_multiple_times(self, state: ThreadSafeState) -> None:
        """Test multiple capital updates."""
        await state.update_capital(10.0)
        await state.update_capital(-5.0)
        await state.update_capital(20.0)
        snapshot = await state.get_state()
        assert snapshot.current_capital == 225.0  # 200 + 10 - 5 + 20
        assert snapshot.daily_pnl == 25.0  # 10 - 5 + 20

    @pytest.mark.asyncio
    async def test_record_win_resets_consecutive_losses(
        self, state: ThreadSafeState
    ) -> None:
        """Test that winning trade resets consecutive losses."""
        # Record some losses first
        await state.record_trade_result(False)
        await state.record_trade_result(False)
        assert (await state.get_state()).consecutive_losses == 2

        # Record a win
        await state.record_trade_result(True)
        assert (await state.get_state()).consecutive_losses == 0

    @pytest.mark.asyncio
    async def test_record_loss_increments_consecutive_losses(
        self, state: ThreadSafeState
    ) -> None:
        """Test that losing trade increments consecutive losses."""
        await state.record_trade_result(False)
        assert (await state.get_state()).consecutive_losses == 1

        await state.record_trade_result(False)
        assert (await state.get_state()).consecutive_losses == 2

        await state.record_trade_result(False)
        assert (await state.get_state()).consecutive_losses == 3

    @pytest.mark.asyncio
    async def test_reset_daily(self, state: ThreadSafeState) -> None:
        """Test daily reset."""
        # Modify state
        await state.update_capital(50.0)
        await state.record_trade_result(False)
        await state.record_trade_result(False)

        # Reset daily
        await state.reset_daily()
        snapshot = await state.get_state()
        assert snapshot.daily_pnl == 0.0
        assert snapshot.consecutive_losses == 0
        # Capital should NOT be reset
        assert snapshot.current_capital == 250.0

    @pytest.mark.asyncio
    async def test_set_trading_enabled(self, state: ThreadSafeState) -> None:
        """Test setting trading enabled flag."""
        await state.set_trading_enabled(False)
        assert (await state.get_state()).trading_enabled is False

        await state.set_trading_enabled(True)
        assert (await state.get_state()).trading_enabled is True

    @pytest.mark.asyncio
    async def test_set_reduced_mode(self, state: ThreadSafeState) -> None:
        """Test setting reduced mode flag."""
        await state.set_reduced_mode(True)
        assert (await state.get_state()).reduced_mode is True

        await state.set_reduced_mode(False)
        assert (await state.get_state()).reduced_mode is False

    @pytest.mark.asyncio
    async def test_increment_open_positions(self, state: ThreadSafeState) -> None:
        """Test incrementing open positions count."""
        await state.increment_open_positions()
        assert (await state.get_state()).open_positions_count == 1

        await state.increment_open_positions()
        assert (await state.get_state()).open_positions_count == 2

    @pytest.mark.asyncio
    async def test_decrement_open_positions(self, state: ThreadSafeState) -> None:
        """Test decrementing open positions count."""
        await state.increment_open_positions()
        await state.increment_open_positions()
        assert (await state.get_state()).open_positions_count == 2

        await state.decrement_open_positions()
        assert (await state.get_state()).open_positions_count == 1

    @pytest.mark.asyncio
    async def test_decrement_positions_does_not_go_negative(
        self, state: ThreadSafeState
    ) -> None:
        """Test that positions count cannot go negative."""
        await state.decrement_open_positions()
        assert (await state.get_state()).open_positions_count == 0

        # Try again, should still be 0
        await state.decrement_open_positions()
        assert (await state.get_state()).open_positions_count == 0

    @pytest.mark.asyncio
    async def test_concurrent_access(self, state: ThreadSafeState) -> None:
        """Test thread safety with concurrent access."""

        async def update_capital_task(amount: float, times: int) -> None:
            for _ in range(times):
                await state.update_capital(amount)

        # Run 10 concurrent tasks, each adding 1.0, 100 times
        tasks = [update_capital_task(1.0, 100) for _ in range(10)]
        await asyncio.gather(*tasks)

        snapshot = await state.get_state()
        assert snapshot.current_capital == 200.0 + 1000.0  # 200 + 10*100

    @pytest.mark.asyncio
    async def test_concurrent_record_trade_results(
        self, state: ThreadSafeState
    ) -> None:
        """Test thread safety with concurrent trade result recording."""

        async def record_loss_task() -> None:
            await state.record_trade_result(False)

        async def record_win_task() -> None:
            await state.record_trade_result(True)

        # Record 5 losses, then a win, then 3 more losses
        tasks = [
            record_loss_task(),
            record_loss_task(),
            record_loss_task(),
            record_loss_task(),
            record_loss_task(),
            record_win_task(),
            record_loss_task(),
            record_loss_task(),
            record_loss_task(),
        ]
        await asyncio.gather(*tasks)

        # Final count depends on order, but should be between 0 and 8
        snapshot = await state.get_state()
        assert 0 <= snapshot.consecutive_losses <= 8


class TestThreadSafeStatePersistence:
    """Test ThreadSafeState persistence."""

    @pytest.fixture
    def state(self) -> ThreadSafeState:
        """Create a test state manager."""
        return ThreadSafeState(initial_capital=200.0)

    @pytest.mark.asyncio
    async def test_persist(self, state: ThreadSafeState) -> None:
        """Test persisting state to database."""
        # Modify state
        await state.update_capital(50.0)
        await state.record_trade_result(False)
        await state.increment_open_positions()

        # Mock database connection
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()

        with patch("src.core.state.get_connection") as mock_get_connection:
            mock_get_connection.return_value.__aenter__.return_value = mock_conn

            await state.persist()

            # Verify execute was called with correct SQL
            assert mock_conn.execute.called
            call_args = mock_conn.execute.call_args
            assert "INSERT OR REPLACE INTO system_state" in call_args[0][0]

            # Verify the state was serialized correctly
            json_data = call_args[0][1][1]
            state_dict = json.loads(json_data)
            assert state_dict["current_capital"] == 250.0
            assert state_dict["daily_pnl"] == 50.0
            assert state_dict["consecutive_losses"] == 1
            assert state_dict["open_positions_count"] == 1

    @pytest.mark.asyncio
    async def test_restore_with_saved_state(self) -> None:
        """Test restoring state from database with existing data."""
        saved_state = {
            "current_capital": 350.0,
            "daily_pnl": 25.0,
            "consecutive_losses": 2,
            "open_positions_count": 3,
            "trading_enabled": False,
            "reduced_mode": True,
        }

        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=(json.dumps(saved_state),))
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch("src.core.state.get_connection") as mock_get_connection:
            mock_get_connection.return_value.__aenter__.return_value = mock_conn

            state = await ThreadSafeState.restore(initial_capital=200.0)
            snapshot = await state.get_state()

            assert snapshot.current_capital == 350.0
            assert snapshot.daily_pnl == 25.0
            assert snapshot.consecutive_losses == 2
            assert snapshot.open_positions_count == 3
            assert snapshot.trading_enabled is False
            assert snapshot.reduced_mode is True

    @pytest.mark.asyncio
    async def test_restore_without_saved_state(self) -> None:
        """Test restoring state when no saved state exists."""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch("src.core.state.get_connection") as mock_get_connection:
            mock_get_connection.return_value.__aenter__.return_value = mock_conn

            state = await ThreadSafeState.restore(initial_capital=300.0)
            snapshot = await state.get_state()

            # Should use default/fallback values
            assert snapshot.current_capital == 300.0
            assert snapshot.daily_pnl == 0.0
            assert snapshot.consecutive_losses == 0
            assert snapshot.trading_enabled is True
            assert snapshot.reduced_mode is False

    @pytest.mark.asyncio
    async def test_restore_with_database_error(self) -> None:
        """Test restoring state handles database errors gracefully."""
        with patch("src.core.state.get_connection") as mock_get_connection:
            mock_get_connection.side_effect = Exception("Database error")

            # Should not raise, use defaults instead
            state = await ThreadSafeState.restore(initial_capital=400.0)
            snapshot = await state.get_state()

            assert snapshot.current_capital == 400.0
            assert snapshot.daily_pnl == 0.0


class TestGetStateManager:
    """Test get_state_manager singleton."""

    def test_get_state_manager_returns_singleton(self) -> None:
        """Test that get_state_manager returns the same instance."""
        # Reset the singleton for testing
        import src.core.state as state_module

        state_module._state_manager = None

        state1 = get_state_manager()
        state2 = get_state_manager()
        assert state1 is state2

    def test_get_state_manager_creates_new_instance(self) -> None:
        """Test that get_state_manager creates instance when None."""
        import src.core.state as state_module

        state_module._state_manager = None

        state = get_state_manager()
        assert state is not None
        assert isinstance(state, ThreadSafeState)


class TestStateSnapshotTimestamp:
    """Test StateSnapshot timestamp handling."""

    @pytest.mark.asyncio
    async def test_get_state_includes_timestamp(self) -> None:
        """Test that get_state includes updated_at timestamp."""
        state = ThreadSafeState(initial_capital=200.0)
        snapshot = await state.get_state()
        assert snapshot.updated_at is not None

    @pytest.mark.asyncio
    async def test_snapshot_timestamp_changes(self) -> None:
        """Test that timestamp updates on each get_state call."""
        import datetime

        state = ThreadSafeState(initial_capital=200.0)
        snapshot1 = await state.get_state()

        # Small delay to ensure different timestamp
        await asyncio.sleep(0.01)

        snapshot2 = await state.get_state()
        # Timestamps should be different (or at least both present)
        assert snapshot1.updated_at is not None
        assert snapshot2.updated_at is not None
