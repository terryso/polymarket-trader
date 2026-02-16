"""Integration tests for PositionManager with real database operations.

These tests make actual database CRUD operations on the positions table.
Run with: pytest tests/integration/ -v -m integration

To skip these tests during normal development:
    pytest tests/ -v -m "not integration"

Note: These tests use a real SQLite database file for persistence testing.
"""

from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aiosqlite
import pytest
import pytest_asyncio

from src.config import settings
from src.core.state import ThreadSafeState
from src.exceptions import TradingError, ValidationError
from src.models.position import Position, PositionOutcome, PositionStatus
from src.storage.database import DatabaseConfig, DatabaseManager
from src.storage.repositories import position_repo as repo_module
from src.storage.repositories.position_repo import PositionRepository
from src.trading.position_manager import PositionManager

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class _TestDatabaseManager:
    """Test database manager that disables foreign key constraints."""

    def __init__(self, db_path: str) -> None:
        """Initialize test database manager.

        Args:
            db_path: Path to the SQLite database file
        """
        self._db_path = db_path

    @asynccontextmanager
    async def get_connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Get database connection with foreign keys disabled.

        Yields:
            aiosqlite.Connection: Database connection
        """
        conn = await aiosqlite.connect(self._db_path)
        # Disable foreign key constraints for testing
        await conn.execute("PRAGMA foreign_keys = OFF")
        try:
            yield conn
        finally:
            await conn.close()

    async def init_db(self) -> None:
        """Initialize database schema for testing.

        Creates tables without foreign key constraints.
        """
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        async with self.get_connection() as conn:
            # Create markets table (for FK reference compatibility)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS markets (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    yes_price REAL,
                    no_price REAL,
                    liquidity REAL,
                    deadline DATETIME,
                    resolution_status TEXT,
                    resolution_outcome TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create positions table (without FK constraint for testing)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    shares REAL NOT NULL,
                    avg_price REAL NOT NULL,
                    initial_value REAL,
                    current_value REAL,
                    pnl REAL,
                    status TEXT,
                    opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    closed_at DATETIME
                )
            """)

            # Create indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_positions_market_id
                ON positions(market_id)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_positions_status
                ON positions(status)
            """)

            await conn.commit()


# Module-level test database manager
_test_db_manager: _TestDatabaseManager | None = None


@pytest_asyncio.fixture(scope="module")
async def test_db_manager() -> AsyncIterator[_TestDatabaseManager]:
    """Create a test database manager with a temporary database file.

    This fixture creates a temporary SQLite database for testing
    and cleans it up after all tests in the module complete.
    """
    global _test_db_manager

    # Create a temporary database file
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_positions.db")

    db_manager = _TestDatabaseManager(test_db_path)
    _test_db_manager = db_manager

    # Initialize the database schema
    await db_manager.init_db()

    yield db_manager

    # Cleanup temp files
    _test_db_manager = None
    try:
        Path(test_db_path).unlink(missing_ok=True)
        Path(temp_dir).rmdir()
    except OSError:
        pass


@pytest_asyncio.fixture
async def clean_positions_table(
    test_db_manager: _TestDatabaseManager,
) -> AsyncIterator[None]:
    """Clean the positions table before and after each test.

    This fixture ensures test isolation by clearing all positions.
    """
    # Clean before test
    async with test_db_manager.get_connection() as conn:
        await conn.execute("DELETE FROM positions")
        await conn.commit()

    yield

    # Clean after test
    async with test_db_manager.get_connection() as conn:
        await conn.execute("DELETE FROM positions")
        await conn.commit()


@pytest_asyncio.fixture
async def test_state() -> AsyncIterator[ThreadSafeState]:
    """Create a fresh ThreadSafeState instance for testing.

    Each test gets its own state instance to avoid cross-test contamination.
    """
    state = ThreadSafeState(initial_capital=200.0)
    yield state


@pytest_asyncio.fixture
async def position_repo(
    test_db_manager: _TestDatabaseManager,
) -> AsyncIterator[PositionRepository]:
    """Create a PositionRepository instance for testing.

    This fixture monkeypatches the global get_connection function to use
    the test database.
    """
    # Save original get_connection function
    original_get_connection = repo_module.get_connection

    # Create a replacement get_connection that uses test database
    @asynccontextmanager
    async def test_get_connection() -> AsyncIterator[aiosqlite.Connection]:
        async with test_db_manager.get_connection() as conn:
            yield conn

    # Monkeypatch the module's get_connection
    repo_module.get_connection = test_get_connection

    repo = PositionRepository()
    yield repo

    # Restore original get_connection
    repo_module.get_connection = original_get_connection


@pytest_asyncio.fixture
async def position_manager(
    position_repo: PositionRepository,
    test_state: ThreadSafeState,
) -> AsyncIterator[PositionManager]:
    """Create a PositionManager instance with test dependencies."""
    manager = PositionManager(repository=position_repo, state=test_state)
    yield manager


class TestOpenPositionPersistsToDatabase:
    """P0: Test opening a position persists to database."""

    @pytest.mark.asyncio
    async def test_open_position_persists_to_database(
        self,
        position_manager: PositionManager,
        position_repo: PositionRepository,
        test_state: ThreadSafeState,
        clean_positions_table: None,
    ) -> None:
        """Test that open_position creates a database record with correct values.

        Verifies:
        - Position is saved to database with all fields
        - State is updated (open_positions_count incremented)
        - Returned position has valid ID
        """
        # Setup
        market_id = "test-market-001"
        outcome = PositionOutcome.YES
        shares = 100.0
        price = 0.45

        # Get initial state
        initial_state = await test_state.get_state()
        assert initial_state.open_positions_count == 0

        # Execute
        position = await position_manager.open_position(
            market_id=market_id,
            outcome=outcome,
            shares=shares,
            price=price,
        )

        # Verify returned position
        assert position.id > 0, "Position should have a valid ID after save"
        assert position.market_id == market_id
        assert position.outcome == outcome
        assert position.shares == shares
        assert position.avg_price == price
        assert position.initial_value == shares * price
        assert position.current_value == shares * price
        assert position.pnl == 0.0
        assert position.status == PositionStatus.OPEN
        assert position.opened_at is not None
        assert position.closed_at is None

        # Verify database persistence
        saved_position = await position_repo.get_by_id(position.id)
        assert saved_position is not None
        assert saved_position.id == position.id
        assert saved_position.market_id == market_id
        assert saved_position.status == PositionStatus.OPEN

        # Verify state update
        updated_state = await test_state.get_state()
        assert updated_state.open_positions_count == 1


class TestClosePositionUpdatesStateAndDatabase:
    """P0: Test closing a position updates state and database."""

    @pytest.mark.asyncio
    async def test_close_position_updates_state_and_database(
        self,
        position_manager: PositionManager,
        position_repo: PositionRepository,
        test_state: ThreadSafeState,
        clean_positions_table: None,
    ) -> None:
        """Test that close_position updates database and state correctly.

        Verifies:
        - Position status changes to CLOSED
        - PnL is calculated correctly
        - closed_at timestamp is set
        - State is updated (open_positions_count decremented, capital updated)
        """
        # Setup: Open a position first
        open_position = await position_manager.open_position(
            market_id="test-market-002",
            outcome=PositionOutcome.YES,
            shares=100.0,
            price=0.50,
        )

        # Verify initial state
        initial_state = await test_state.get_state()
        assert initial_state.open_positions_count == 1

        # Execute: Close at higher price (profit)
        final_price = 0.70
        closed_position = await position_manager.close_position(
            position_id=open_position.id,
            final_price=final_price,
        )

        # Verify closed position
        assert closed_position.status == PositionStatus.CLOSED
        assert closed_position.closed_at is not None
        expected_final_value = 100.0 * 0.70  # 70.0
        expected_pnl = expected_final_value - (100.0 * 0.50)  # 20.0
        assert closed_position.current_value == expected_final_value
        assert closed_position.pnl == expected_pnl

        # Verify database update
        db_position = await position_repo.get_by_id(open_position.id)
        assert db_position is not None
        assert db_position.status == PositionStatus.CLOSED
        assert db_position.closed_at is not None
        assert db_position.pnl == expected_pnl

        # Verify state updates
        final_state = await test_state.get_state()
        assert final_state.open_positions_count == 0
        # Capital should be updated by PnL amount
        assert final_state.current_capital == 200.0 + expected_pnl

    @pytest.mark.asyncio
    async def test_close_position_with_loss(
        self,
        position_manager: PositionManager,
        test_state: ThreadSafeState,
        clean_positions_table: None,
    ) -> None:
        """Test closing a position with a loss updates state correctly."""
        # Setup: Open a position
        open_position = await position_manager.open_position(
            market_id="test-market-loss",
            outcome=PositionOutcome.YES,
            shares=100.0,
            price=0.60,
        )

        # Execute: Close at lower price (loss)
        closed_position = await position_manager.close_position(
            position_id=open_position.id,
            final_price=0.40,
        )

        # Verify loss
        expected_pnl = (100.0 * 0.40) - (100.0 * 0.60)  # -20.0
        assert closed_position.pnl == expected_pnl

        # Verify state reflects loss
        final_state = await test_state.get_state()
        assert final_state.current_capital == 200.0 + expected_pnl
        assert final_state.consecutive_losses == 1


class TestPositionLifecycleWithRealDatabase:
    """P0: Test complete position lifecycle with real database."""

    @pytest.mark.asyncio
    async def test_position_lifecycle_with_real_database(
        self,
        position_manager: PositionManager,
        position_repo: PositionRepository,
        test_state: ThreadSafeState,
        clean_positions_table: None,
    ) -> None:
        """Test complete lifecycle: open -> update -> close.

        Verifies:
        - Open creates database record
        - Update modifies value in database
        - Close finalizes position
        - State tracking throughout
        """
        # Phase 1: Open position
        position = await position_manager.open_position(
            market_id="lifecycle-market",
            outcome=PositionOutcome.YES,
            shares=200.0,
            price=0.30,
        )

        assert position.id > 0
        assert position.status == PositionStatus.OPEN
        state_after_open = await test_state.get_state()
        assert state_after_open.open_positions_count == 1

        # Phase 2: Update position value (price increases)
        updated_position = await position_manager.update_position_value(
            position_id=position.id,
            current_price=0.45,
        )

        assert updated_position.current_value == 200.0 * 0.45  # 90.0
        assert updated_position.pnl == 90.0 - 60.0  # 30.0

        # Verify database has updated value
        db_after_update = await position_repo.get_by_id(position.id)
        assert db_after_update is not None
        assert db_after_update.current_value == 90.0
        assert db_after_update.pnl == 30.0

        # Phase 3: Close position
        closed_position = await position_manager.close_position(
            position_id=position.id,
            final_price=0.50,
        )

        assert closed_position.status == PositionStatus.CLOSED
        assert closed_position.closed_at is not None
        # Final PnL: 100.0 - 60.0 = 40.0
        assert closed_position.pnl == 40.0

        # Verify final state
        final_state = await test_state.get_state()
        assert final_state.open_positions_count == 0
        assert final_state.current_capital == 200.0 + 40.0


class TestGetTotalExposureCalculation:
    """P1: Test total exposure calculation."""

    @pytest.mark.asyncio
    async def test_get_total_exposure_calculation(
        self,
        position_manager: PositionManager,
        clean_positions_table: None,
    ) -> None:
        """Test that get_total_exposure sums all open position values correctly."""
        # Open multiple positions
        await position_manager.open_position(
            market_id="exposure-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            price=0.40,  # value = 40.0
        )

        await position_manager.open_position(
            market_id="exposure-market-2",
            outcome=PositionOutcome.NO,
            shares=200.0,
            price=0.30,  # value = 60.0
        )

        await position_manager.open_position(
            market_id="exposure-market-3",
            outcome=PositionOutcome.YES,
            shares=50.0,
            price=0.20,  # value = 10.0
        )

        # Calculate total exposure
        total_exposure = await position_manager.get_total_exposure()

        # Expected: 40.0 + 60.0 + 10.0 = 110.0
        assert total_exposure == 110.0

    @pytest.mark.asyncio
    async def test_get_total_exposure_empty(
        self,
        position_manager: PositionManager,
        clean_positions_table: None,
    ) -> None:
        """Test that get_total_exposure returns 0 when no positions."""
        total_exposure = await position_manager.get_total_exposure()
        assert total_exposure == 0.0


class TestCannotOpenDuplicatePosition:
    """P1: Test that duplicate positions are prevented."""

    @pytest.mark.asyncio
    async def test_cannot_open_duplicate_position(
        self,
        position_manager: PositionManager,
        clean_positions_table: None,
    ) -> None:
        """Test that opening a duplicate position for same market raises TradingError."""
        # Open first position
        market_id = "duplicate-test-market"
        await position_manager.open_position(
            market_id=market_id,
            outcome=PositionOutcome.YES,
            shares=100.0,
            price=0.50,
        )

        # Attempt to open duplicate
        with pytest.raises(TradingError) as exc_info:
            await position_manager.open_position(
                market_id=market_id,
                outcome=PositionOutcome.YES,
                shares=50.0,
                price=0.55,
            )

        # Verify error message mentions market ID
        assert market_id in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_can_reopen_market_after_close(
        self,
        position_manager: PositionManager,
        clean_positions_table: None,
    ) -> None:
        """Test that a market can be reopened after previous position is closed."""
        market_id = "reopen-test-market"

        # Open and close first position
        pos1 = await position_manager.open_position(
            market_id=market_id,
            outcome=PositionOutcome.YES,
            shares=100.0,
            price=0.50,
        )
        await position_manager.close_position(pos1.id, final_price=0.60)

        # Should be able to open again
        pos2 = await position_manager.open_position(
            market_id=market_id,
            outcome=PositionOutcome.YES,
            shares=50.0,
            price=0.55,
        )

        assert pos2.id != pos1.id
        assert pos2.status == PositionStatus.OPEN


class TestUpdatePositionValue:
    """P1: Test updating position value."""

    @pytest.mark.asyncio
    async def test_update_position_value(
        self,
        position_manager: PositionManager,
        position_repo: PositionRepository,
        clean_positions_table: None,
    ) -> None:
        """Test that update_position_value updates current_value and pnl correctly."""
        # Open position
        position = await position_manager.open_position(
            market_id="update-value-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            price=0.50,
        )

        # Initial values
        assert position.current_value == 50.0
        assert position.pnl == 0.0

        # Update with new price
        updated = await position_manager.update_position_value(
            position_id=position.id,
            current_price=0.65,
        )

        # Verify calculations
        assert updated.current_value == 65.0  # 100 * 0.65
        assert updated.pnl == 15.0  # 65 - 50

        # Verify database persistence
        db_position = await position_repo.get_by_id(position.id)
        assert db_position is not None
        assert db_position.current_value == 65.0
        assert db_position.pnl == 15.0

    @pytest.mark.asyncio
    async def test_update_position_value_with_loss(
        self,
        position_manager: PositionManager,
        clean_positions_table: None,
    ) -> None:
        """Test that update shows negative PnL when price drops."""
        position = await position_manager.open_position(
            market_id="update-loss-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            price=0.60,
        )

        # Update with lower price
        updated = await position_manager.update_position_value(
            position_id=position.id,
            current_price=0.40,
        )

        assert updated.pnl == -20.0  # 40 - 60

    @pytest.mark.asyncio
    async def test_update_closed_position_raises_error(
        self,
        position_manager: PositionManager,
        clean_positions_table: None,
    ) -> None:
        """Test that updating a closed position raises TradingError."""
        position = await position_manager.open_position(
            market_id="closed-update-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            price=0.50,
        )

        # Close the position
        await position_manager.close_position(position.id, final_price=0.60)

        # Attempt to update closed position
        with pytest.raises(TradingError):
            await position_manager.update_position_value(
                position_id=position.id,
                current_price=0.70,
            )


class TestGetOpenPositions:
    """P1: Test getting all open positions."""

    @pytest.mark.asyncio
    async def test_get_open_positions(
        self,
        position_manager: PositionManager,
        clean_positions_table: None,
    ) -> None:
        """Test that get_open_positions returns all open positions."""
        # Initially empty
        positions = await position_manager.get_open_positions()
        assert len(positions) == 0

        # Open multiple positions
        await position_manager.open_position(
            market_id="open-pos-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            price=0.50,
        )
        await position_manager.open_position(
            market_id="open-pos-2",
            outcome=PositionOutcome.NO,
            shares=200.0,
            price=0.30,
        )
        await position_manager.open_position(
            market_id="open-pos-3",
            outcome=PositionOutcome.YES,
            shares=150.0,
            price=0.40,
        )

        # Get open positions
        positions = await position_manager.get_open_positions()

        assert len(positions) == 3
        market_ids = {p.market_id for p in positions}
        assert market_ids == {"open-pos-1", "open-pos-2", "open-pos-3"}

    @pytest.mark.asyncio
    async def test_get_open_positions_excludes_closed(
        self,
        position_manager: PositionManager,
        clean_positions_table: None,
    ) -> None:
        """Test that get_open_positions excludes closed positions."""
        # Open positions
        pos1 = await position_manager.open_position(
            market_id="will-be-closed",
            outcome=PositionOutcome.YES,
            shares=100.0,
            price=0.50,
        )
        await position_manager.open_position(
            market_id="will-stay-open",
            outcome=PositionOutcome.YES,
            shares=100.0,
            price=0.50,
        )

        # Close one position
        await position_manager.close_position(pos1.id, final_price=0.60)

        # Get open positions
        positions = await position_manager.get_open_positions()

        assert len(positions) == 1
        assert positions[0].market_id == "will-stay-open"
