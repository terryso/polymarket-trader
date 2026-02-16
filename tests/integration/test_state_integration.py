"""Integration tests for ThreadSafeState with real database operations.

These tests make actual database operations using SQLite.
Run with: pytest tests/integration/ -v -m integration

To skip these tests during normal development:
    pytest tests/ -v -m "not integration"

Note: These tests require the database to be initialized.
"""

from __future__ import annotations

import asyncio
import json

import pytest
import pytest_asyncio

from src.core.state import StateSnapshot, ThreadSafeState
from src.storage.database import get_connection, init_db

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest_asyncio.fixture(scope="module")
async def db_setup() -> None:
    """Initialize database for integration tests.

    This fixture ensures the database is initialized before running tests.
    It uses a module scope to only initialize once per test module.
    """
    await init_db()


@pytest_asyncio.fixture
async def clean_state(db_setup: None) -> None:
    """Clean system_state table before and after each test.

    This fixture ensures a clean state for each test by removing
    any existing trading_state from the database.

    Args:
        db_setup: Fixture that ensures database is initialized
    """
    # Clean before test
    async with get_connection() as conn:
        await conn.execute("DELETE FROM system_state WHERE key = ?", ("trading_state",))
        await conn.commit()

    yield

    # Clean after test
    async with get_connection() as conn:
        await conn.execute("DELETE FROM system_state WHERE key = ?", ("trading_state",))
        await conn.commit()


@pytest_asyncio.fixture
async def state_instance(clean_state: None) -> ThreadSafeState:
    """Create a fresh ThreadSafeState instance for testing.

    Args:
        clean_state: Fixture that ensures clean database state

    Returns:
        ThreadSafeState: Fresh state instance with initial capital
    """
    return ThreadSafeState(initial_capital=200.0)


class TestStatePersistAndRestore:
    """Integration tests for state persistence and restoration (P0)."""

    async def test_persist_and_restore_state(
        self, state_instance: ThreadSafeState
    ) -> None:
        """Test state persistence to database and restoration.

        P0: This test verifies that:
        1. State can be persisted to the system_state table
        2. State can be restored from the database
        3. All state values are correctly preserved

        Args:
            state_instance: Fresh ThreadSafeState instance
        """
        # Modify state from initial values
        await state_instance.update_capital(50.0)  # +$50 gain
        await state_instance.record_trade_result(True)  # Win
        await state_instance.increment_open_positions()
        await state_instance.set_reduced_mode(True)

        # Get expected state before persist
        expected_snapshot = await state_instance.get_state()

        # Persist state to database
        await state_instance.persist()

        # Verify state was saved to database
        async with get_connection() as conn:
            cursor = await conn.execute(
                "SELECT value FROM system_state WHERE key = ?", ("trading_state",)
            )
            row = await cursor.fetchone()

            assert row is not None, "State should be persisted to database"

            saved_state = json.loads(row[0])
            assert saved_state["current_capital"] == expected_snapshot.current_capital
            assert saved_state["daily_pnl"] == expected_snapshot.daily_pnl
            assert (
                saved_state["consecutive_losses"]
                == expected_snapshot.consecutive_losses
            )
            assert (
                saved_state["open_positions_count"]
                == expected_snapshot.open_positions_count
            )
            assert saved_state["trading_enabled"] == expected_snapshot.trading_enabled
            assert saved_state["reduced_mode"] == expected_snapshot.reduced_mode

        # Restore state to a new instance
        restored_state = await ThreadSafeState.restore()

        # Verify restored state matches original
        restored_snapshot = await restored_state.get_state()

        assert (
            restored_snapshot.current_capital == expected_snapshot.current_capital
        ), f"Expected capital {expected_snapshot.current_capital}, got {restored_snapshot.current_capital}"
        assert (
            restored_snapshot.daily_pnl == expected_snapshot.daily_pnl
        ), f"Expected daily_pnl {expected_snapshot.daily_pnl}, got {restored_snapshot.daily_pnl}"
        assert (
            restored_snapshot.consecutive_losses == expected_snapshot.consecutive_losses
        )
        assert (
            restored_snapshot.open_positions_count
            == expected_snapshot.open_positions_count
        )
        assert restored_snapshot.trading_enabled == expected_snapshot.trading_enabled
        assert restored_snapshot.reduced_mode == expected_snapshot.reduced_mode

    async def test_restore_creates_default_if_no_saved_state(
        self, clean_state: None
    ) -> None:
        """Test that restore creates default state when no saved state exists.

        P0: This test verifies that:
        1. Restore works when no state exists in database
        2. Default values are correctly applied
        3. Initial capital parameter is respected

        Args:
            clean_state: Fixture ensuring no saved state exists
        """
        # Verify no state exists
        async with get_connection() as conn:
            cursor = await conn.execute(
                "SELECT value FROM system_state WHERE key = ?", ("trading_state",)
            )
            row = await cursor.fetchone()
            assert row is None, "No state should exist before restore"

        # Restore with explicit initial capital
        initial_capital = 500.0
        state = await ThreadSafeState.restore(initial_capital=initial_capital)

        # Verify default values
        snapshot = await state.get_state()

        assert snapshot.current_capital == initial_capital
        assert snapshot.daily_pnl == 0.0
        assert snapshot.consecutive_losses == 0
        assert snapshot.open_positions_count == 0
        assert snapshot.trading_enabled is True
        assert snapshot.reduced_mode is False


class TestStatePersistUpdates:
    """Integration tests for state updates and persistence (P1)."""

    async def test_persist_updates_existing_state(
        self, state_instance: ThreadSafeState
    ) -> None:
        """Test that persist updates existing state in database.

        P1: This test verifies that:
        1. First persist creates state in database
        2. Second persist updates the existing state
        3. Updated values are correctly saved

        Args:
            state_instance: Fresh ThreadSafeState instance
        """
        # First persist - creates state
        await state_instance.update_capital(25.0)
        await state_instance.persist()

        # Verify first state
        async with get_connection() as conn:
            cursor = await conn.execute(
                "SELECT value FROM system_state WHERE key = ?", ("trading_state",)
            )
            row = await cursor.fetchone()
            assert row is not None
            first_state = json.loads(row[0])
            assert first_state["current_capital"] == 225.0  # 200 + 25

        # Modify and persist again - should update
        await state_instance.update_capital(-10.0)  # -$10 loss
        await state_instance.record_trade_result(False)  # Loss
        await state_instance.persist()

        # Verify updated state
        async with get_connection() as conn:
            cursor = await conn.execute(
                "SELECT value FROM system_state WHERE key = ?", ("trading_state",)
            )
            row = await cursor.fetchone()
            assert row is not None
            updated_state = json.loads(row[0])
            assert updated_state["current_capital"] == 215.0  # 225 - 10
            assert updated_state["daily_pnl"] == 15.0  # 25 - 10
            assert updated_state["consecutive_losses"] == 1

        # Restore and verify
        restored = await ThreadSafeState.restore()
        snapshot = await restored.get_state()
        assert snapshot.current_capital == 215.0
        assert snapshot.daily_pnl == 15.0
        assert snapshot.consecutive_losses == 1

    async def test_persist_preserves_all_state_fields(
        self, state_instance: ThreadSafeState
    ) -> None:
        """Test that persist preserves all state fields correctly.

        P1: This test verifies that all state fields are correctly
        persisted and restored, including edge cases.

        Args:
            state_instance: Fresh ThreadSafeState instance
        """
        # Set all fields to specific values
        await state_instance.update_capital(100.0)  # capital=300, pnl=100
        await state_instance.record_trade_result(False)
        await state_instance.record_trade_result(False)
        await state_instance.record_trade_result(False)  # 3 consecutive losses
        await state_instance.increment_open_positions()
        await state_instance.increment_open_positions()
        await state_instance.set_trading_enabled(False)
        await state_instance.set_reduced_mode(True)

        # Persist and restore
        await state_instance.persist()
        restored = await ThreadSafeState.restore()
        snapshot = await restored.get_state()

        # Verify all fields
        assert snapshot.current_capital == 300.0
        assert snapshot.daily_pnl == 100.0
        assert snapshot.consecutive_losses == 3
        assert snapshot.open_positions_count == 2
        assert snapshot.trading_enabled is False
        assert snapshot.reduced_mode is True

    async def test_persist_after_reset_daily(
        self, state_instance: ThreadSafeState
    ) -> None:
        """Test that persist correctly saves state after daily reset.

        P1: This test verifies that daily reset values are persisted.

        Args:
            state_instance: Fresh ThreadSafeState instance
        """
        # Accumulate some daily state
        await state_instance.update_capital(-50.0)
        await state_instance.record_trade_result(False)
        await state_instance.record_trade_result(False)

        # Reset daily
        await state_instance.reset_daily()

        # Persist
        await state_instance.persist()

        # Restore and verify reset values
        restored = await ThreadSafeState.restore()
        snapshot = await restored.get_state()

        assert snapshot.current_capital == 150.0  # 200 - 50 (capital preserved)
        assert snapshot.daily_pnl == 0.0  # Reset
        assert snapshot.consecutive_losses == 0  # Reset


class TestConcurrentStateAccess:
    """Integration tests for concurrent state access (P2)."""

    async def test_concurrent_state_access(
        self, state_instance: ThreadSafeState
    ) -> None:
        """Test concurrent access to state is thread-safe.

        P2: This test verifies that:
        1. Multiple concurrent reads work correctly
        2. Multiple concurrent writes are serialized
        3. Final state is consistent

        Args:
            state_instance: Fresh ThreadSafeState instance
        """
        # Number of concurrent operations
        num_operations = 10

        # Concurrent reads
        async def read_state() -> StateSnapshot:
            return await state_instance.get_state()

        # Execute concurrent reads
        read_tasks = [read_state() for _ in range(num_operations)]
        read_results = await asyncio.gather(*read_tasks)

        # All reads should succeed
        assert len(read_results) == num_operations
        for snapshot in read_results:
            assert snapshot.current_capital == 200.0

        # Concurrent writes
        async def write_capital(amount: float) -> None:
            await state_instance.update_capital(amount)

        # Execute concurrent writes with small amounts
        write_tasks = [write_capital(1.0) for _ in range(num_operations)]
        await asyncio.gather(*write_tasks)

        # Final state should reflect all writes
        final_snapshot = await state_instance.get_state()
        expected_capital = 200.0 + (1.0 * num_operations)
        assert (
            final_snapshot.current_capital == expected_capital
        ), f"Expected {expected_capital}, got {final_snapshot.current_capital}"

    async def test_concurrent_persist_operations(
        self, state_instance: ThreadSafeState
    ) -> None:
        """Test concurrent persist operations are handled correctly.

        P2: This test verifies that concurrent persist operations
        don't cause data corruption or race conditions.

        Args:
            state_instance: Fresh ThreadSafeState instance
        """
        num_operations = 5

        async def modify_and_persist(amount: float) -> None:
            await state_instance.update_capital(amount)
            await state_instance.persist()

        # Execute concurrent modify+persist operations
        tasks = [modify_and_persist(10.0) for _ in range(num_operations)]
        await asyncio.gather(*tasks)

        # Restore and verify state is valid
        restored = await ThreadSafeState.restore()
        snapshot = await restored.get_state()

        # Capital should be initial + all increments
        expected_capital = 200.0 + (10.0 * num_operations)
        assert snapshot.current_capital == expected_capital

        # Verify state in database is valid JSON
        async with get_connection() as conn:
            cursor = await conn.execute(
                "SELECT value FROM system_state WHERE key = ?", ("trading_state",)
            )
            row = await cursor.fetchone()
            assert row is not None
            # Should be valid JSON
            state_dict = json.loads(row[0])
            assert "current_capital" in state_dict
            assert "daily_pnl" in state_dict

    async def test_concurrent_position_tracking(
        self, state_instance: ThreadSafeState
    ) -> None:
        """Test concurrent position increment/decrement operations.

        P2: This test verifies position count tracking under concurrent access.

        Args:
            state_instance: Fresh ThreadSafeState instance
        """
        # Increment positions concurrently
        increment_tasks = [state_instance.increment_open_positions() for _ in range(5)]
        await asyncio.gather(*increment_tasks)

        snapshot = await state_instance.get_state()
        assert snapshot.open_positions_count == 5

        # Decrement some positions concurrently
        decrement_tasks = [state_instance.decrement_open_positions() for _ in range(3)]
        await asyncio.gather(*decrement_tasks)

        snapshot = await state_instance.get_state()
        assert snapshot.open_positions_count == 2

        # Persist and verify
        await state_instance.persist()
        restored = await ThreadSafeState.restore()
        restored_snapshot = await restored.get_state()
        assert restored_snapshot.open_positions_count == 2


class TestStateEdgeCases:
    """Integration tests for edge cases and error handling."""

    async def test_restore_with_partial_state_data(self, clean_state: None) -> None:
        """Test restore handles partial/corrupt state data gracefully.

        This test verifies that restore works even if some fields
        are missing from the saved state.

        Args:
            clean_state: Fixture ensuring clean database state
        """
        # Insert partial state data
        partial_state = {
            "current_capital": 150.0,
            # Missing other fields
        }
        async with get_connection() as conn:
            await conn.execute(
                "INSERT INTO system_state (key, value) VALUES (?, ?)",
                ("trading_state", json.dumps(partial_state)),
            )
            await conn.commit()

        # Restore should use defaults for missing fields
        state = await ThreadSafeState.restore()
        snapshot = await state.get_state()

        assert snapshot.current_capital == 150.0  # From saved state
        assert snapshot.daily_pnl == 0.0  # Default
        assert snapshot.consecutive_losses == 0  # Default
        assert snapshot.trading_enabled is True  # Default

    async def test_state_snapshot_immutability(
        self, state_instance: ThreadSafeState
    ) -> None:
        """Test that StateSnapshot is immutable.

        This test verifies that returned snapshots cannot be modified,
        preventing accidental state corruption.

        Args:
            state_instance: Fresh ThreadSafeState instance
        """
        snapshot = await state_instance.get_state()

        # Attempting to modify should raise error (frozen model)
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            snapshot.current_capital = 999.0  # type: ignore

    async def test_persist_with_negative_capital(
        self, state_instance: ThreadSafeState
    ) -> None:
        """Test persist handles negative capital correctly.

        This test verifies that negative capital (losses exceeding initial)
        is persisted correctly. Note: daily_pnl tracks the raw amount (-250),
        while current_capital is initial_capital + amount (200 + (-250) = -50).

        Args:
            state_instance: Fresh ThreadSafeState instance
        """
        # Create a large loss
        await state_instance.update_capital(-250.0)  # 200 + (-250) = -50 capital
        await state_instance.persist()

        # Restore and verify
        restored = await ThreadSafeState.restore()
        snapshot = await restored.get_state()

        assert snapshot.current_capital == -50.0  # 200 - 250
        assert snapshot.daily_pnl == -250.0  # Raw PnL amount
