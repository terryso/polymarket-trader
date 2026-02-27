"""Integration tests for DailyStatisticsRecorder with real database operations.

These tests verify the daily statistics recording functionality using
actual database operations.

Run with: pytest tests/integration/ -v -m integration

To skip these tests during normal development:
    pytest tests/ -v -m "not integration"

Story 5.5: 统计数据记录
"""

from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import AsyncIterator

import aiosqlite
import pytest
import pytest_asyncio

from src.core.state import ThreadSafeState
from src.models.statistics import Statistics
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.storage.repositories import statistics_repo as statistics_repo_module
from src.storage.repositories import trade_repo as trade_repo_module
from src.storage.repositories.statistics_repo import StatisticsRepository
from src.storage.repositories.trade_repo import TradeRepository
from src.trading.statistics_recorder import DailyStatisticsRecorder


def _create_trade_with_today_timestamp(
    market_id: str,
    mode: TradeMode = TradeMode.PAPER,
    status: TradeStatus = TradeStatus.FILLED,
    amount: float = 20.0,
    price: float = 0.45,
    shares: float = 44.44,
    trade_type: TradeType = TradeType.BUY_YES,
) -> Trade:
    """Helper to create a Trade with today's timestamp for date filtering."""
    return Trade(
        id=0,
        market_id=market_id,
        trade_type=trade_type,
        mode=mode,
        amount=amount,
        price=price,
        shares=shares,
        status=status,
        created_at=datetime.now(timezone.utc),
    )


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class _TestDatabaseManager:
    """Test database manager that disables foreign key constraints."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    @asynccontextmanager
    async def get_connection(self) -> AsyncIterator[aiosqlite.Connection]:
        conn = await aiosqlite.connect(self._db_path)
        await conn.execute("PRAGMA foreign_keys = OFF")
        try:
            yield conn
        finally:
            await conn.close()

    async def init_db(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        async with self.get_connection() as conn:
            # Create trades table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL,
                    trade_type TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    amount REAL NOT NULL,
                    price REAL NOT NULL,
                    shares REAL,
                    status TEXT,
                    llm_prediction_id INTEGER,
                    position_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    polymarket_order_id TEXT
                )
            """)

            # Create statistics table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    mode TEXT NOT NULL,
                    starting_capital REAL,
                    ending_capital REAL,
                    total_pnl REAL,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    win_rate REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_mode
                ON trades(mode)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_statistics_date_mode
                ON statistics(date, mode)
            """)

            await conn.commit()


_test_db_manager: _TestDatabaseManager | None = None


@pytest_asyncio.fixture(scope="module")
async def test_db_manager() -> AsyncIterator[_TestDatabaseManager]:
    global _test_db_manager

    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_statistics_recorder.db")

    db_manager = _TestDatabaseManager(test_db_path)
    _test_db_manager = db_manager

    await db_manager.init_db()

    yield db_manager

    _test_db_manager = None
    try:
        Path(test_db_path).unlink(missing_ok=True)
        Path(temp_dir).rmdir()
    except OSError:
        pass


@pytest_asyncio.fixture
async def clean_tables(
    test_db_manager: _TestDatabaseManager,
) -> AsyncIterator[None]:
    async with test_db_manager.get_connection() as conn:
        await conn.execute("DELETE FROM trades")
        await conn.execute("DELETE FROM statistics")
        await conn.commit()

    yield

    async with test_db_manager.get_connection() as conn:
        await conn.execute("DELETE FROM trades")
        await conn.execute("DELETE FROM statistics")
        await conn.commit()


def _create_test_get_connection(db_manager: _TestDatabaseManager):
    @asynccontextmanager
    async def get_connection() -> AsyncIterator[aiosqlite.Connection]:
        async with db_manager.get_connection() as conn:
            yield conn

    return get_connection


@pytest_asyncio.fixture
async def trade_repo(
    test_db_manager: _TestDatabaseManager,
) -> AsyncIterator[TradeRepository]:
    original_get_connection = trade_repo_module.get_connection
    trade_repo_module.get_connection = _create_test_get_connection(test_db_manager)

    repo = TradeRepository()
    yield repo

    trade_repo_module.get_connection = original_get_connection


@pytest_asyncio.fixture
async def stats_repo(
    test_db_manager: _TestDatabaseManager,
) -> AsyncIterator[StatisticsRepository]:
    original_get_connection = statistics_repo_module.get_connection
    statistics_repo_module.get_connection = _create_test_get_connection(test_db_manager)

    repo = StatisticsRepository()
    yield repo

    statistics_repo_module.get_connection = original_get_connection


@pytest_asyncio.fixture
async def test_state() -> AsyncIterator[ThreadSafeState]:
    state = ThreadSafeState(initial_capital=200.0)
    yield state


@pytest_asyncio.fixture
async def recorder(
    trade_repo: TradeRepository,
    stats_repo: StatisticsRepository,
    test_state: ThreadSafeState,
) -> AsyncIterator[DailyStatisticsRecorder]:
    yield DailyStatisticsRecorder(
        trade_repo=trade_repo,
        stats_repo=stats_repo,
        state_manager=test_state,
    )


class TestRecordDailyStats:
    """P0: Test record_daily_stats with real database operations."""

    @pytest.mark.asyncio
    async def test_record_daily_stats_no_trades(
        self,
        recorder: DailyStatisticsRecorder,
        stats_repo: StatisticsRepository,
        test_state: ThreadSafeState,
        clean_tables: None,
    ) -> None:
        """Test recording daily stats with no trades.

        Verifies:
        - Statistics record is created
        - total_trades is 0
        - win_rate is None
        - starting_capital comes from settings
        """
        stats = await recorder.record_daily_stats(TradeMode.PAPER)

        assert stats.id > 0
        assert stats.date == date.today()
        assert stats.mode == TradeMode.PAPER
        assert stats.total_trades == 0
        assert stats.winning_trades == 0
        assert stats.losing_trades == 0
        assert stats.win_rate is None
        assert stats.starting_capital == 200.0  # From settings

        # Verify persistence
        db_stats = await stats_repo.get_by_date(date.today(), TradeMode.PAPER)
        assert db_stats is not None
        assert db_stats.total_trades == 0

    @pytest.mark.asyncio
    async def test_record_daily_stats_with_trades(
        self,
        recorder: DailyStatisticsRecorder,
        trade_repo: TradeRepository,
        stats_repo: StatisticsRepository,
        test_state: ThreadSafeState,
        clean_tables: None,
    ) -> None:
        """Test recording daily stats with filled trades.

        Verifies:
        - total_trades reflects filled trades count
        - Statistics are persisted correctly
        """
        # Create test trades for today
        today = date.today()
        for i in range(3):
            trade = _create_trade_with_today_timestamp(
                market_id=f"market-{i}",
                mode=TradeMode.PAPER,
                status=TradeStatus.FILLED,
                amount=20.0,
                price=0.45,
                shares=44.44,
            )
            await trade_repo.save(trade)

        # Set positive daily PnL
        await test_state.update_capital(10.0)  # Simulate profit

        stats = await recorder.record_daily_stats(TradeMode.PAPER)

        assert stats.total_trades == 3
        assert (
            stats.winning_trades >= 1
        )  # At least some winning trades with positive PnL
        assert stats.win_rate is not None
        assert stats.win_rate > 0

        # Verify persistence
        db_stats = await stats_repo.get_by_date(today, TradeMode.PAPER)
        assert db_stats is not None
        assert db_stats.total_trades == 3

    @pytest.mark.asyncio
    async def test_record_daily_stats_ignores_non_filled_trades(
        self,
        recorder: DailyStatisticsRecorder,
        trade_repo: TradeRepository,
        stats_repo: StatisticsRepository,
        clean_tables: None,
    ) -> None:
        """Test that only FILLED trades are counted in statistics."""
        # Create a filled trade
        filled_trade = _create_trade_with_today_timestamp(
            market_id="market-1",
            mode=TradeMode.PAPER,
            status=TradeStatus.FILLED,
        )
        await trade_repo.save(filled_trade)

        # Create a pending trade (should be ignored)
        pending_trade = _create_trade_with_today_timestamp(
            market_id="market-2",
            mode=TradeMode.PAPER,
            status=TradeStatus.PENDING,
        )
        await trade_repo.save(pending_trade)

        stats = await recorder.record_daily_stats(TradeMode.PAPER)

        # Only filled trade should be counted
        assert stats.total_trades == 1


class TestStatisticsDateRange:
    """P1: Test statistics date range queries."""

    @pytest.mark.asyncio
    async def test_record_multiple_days(
        self,
        recorder: DailyStatisticsRecorder,
        stats_repo: StatisticsRepository,
        clean_tables: None,
    ) -> None:
        """Test recording statistics for multiple days.

        Note: This test simulates multiple days by saving directly to the repo.
        """
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Record today's stats
        today_stats = await recorder.record_daily_stats(TradeMode.PAPER)
        assert today_stats.date == today

        # Simulate yesterday's stats by saving directly
        yesterday_stats = Statistics(
            id=0,
            date=yesterday,
            mode=TradeMode.PAPER,
            starting_capital=200.0,
            ending_capital=195.0,
            total_pnl=-5.0,
            total_trades=2,
            winning_trades=0,
            losing_trades=2,
            win_rate=0.0,
        )
        await stats_repo.save(yesterday_stats)

        # Query by date range
        stats_range = await stats_repo.get_by_date_range(
            yesterday, today, TradeMode.PAPER
        )

        assert len(stats_range) == 2

    @pytest.mark.asyncio
    async def test_get_latest_statistics(
        self,
        recorder: DailyStatisticsRecorder,
        stats_repo: StatisticsRepository,
        clean_tables: None,
    ) -> None:
        """Test getting latest statistics."""
        # Record today's stats
        await recorder.record_daily_stats(TradeMode.PAPER)

        # Get latest
        latest = await stats_repo.get_latest(TradeMode.PAPER, limit=1)

        assert len(latest) == 1
        assert latest[0].date == date.today()


class TestStartingCapitalSource:
    """P1: Test starting capital source precedence."""

    @pytest.mark.asyncio
    async def test_starting_capital_from_yesterday(
        self,
        recorder: DailyStatisticsRecorder,
        stats_repo: StatisticsRepository,
        clean_tables: None,
    ) -> None:
        """Test that starting capital comes from yesterday's ending capital."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Save yesterday's stats with specific ending capital
        yesterday_stats = Statistics(
            id=0,
            date=yesterday,
            mode=TradeMode.PAPER,
            starting_capital=200.0,
            ending_capital=180.0,  # Ending capital should be today's starting
            total_pnl=-20.0,
            total_trades=5,
            winning_trades=1,
            losing_trades=4,
            win_rate=0.2,
        )
        await stats_repo.save(yesterday_stats)

        # Record today's stats
        today_stats = await recorder.record_daily_stats(TradeMode.PAPER)

        # Starting capital should come from yesterday's ending
        assert today_stats.starting_capital == 180.0

    @pytest.mark.asyncio
    async def test_starting_capital_from_settings_when_no_yesterday(
        self,
        recorder: DailyStatisticsRecorder,
        stats_repo: StatisticsRepository,
        clean_tables: None,
    ) -> None:
        """Test that starting capital comes from settings when no yesterday stats."""
        # Ensure no yesterday stats exist
        yesterday = date.today() - timedelta(days=1)
        yesterday_stats = await stats_repo.get_by_date(yesterday, TradeMode.PAPER)
        assert yesterday_stats is None

        # Record today's stats
        today_stats = await recorder.record_daily_stats(TradeMode.PAPER)

        # Starting capital should come from settings (200.0)
        assert today_stats.starting_capital == 200.0


class TestEndingCapital:
    """P2: Test ending capital from state."""

    @pytest.mark.asyncio
    async def test_ending_capital_from_state(
        self,
        recorder: DailyStatisticsRecorder,
        test_state: ThreadSafeState,
        clean_tables: None,
    ) -> None:
        """Test that ending capital comes from current state."""
        # Modify state capital
        await test_state.update_capital(-15.0)  # Lose $15

        stats = await recorder.record_daily_stats(TradeMode.PAPER)

        # Ending capital should reflect state (200 - 15 = 185)
        assert stats.ending_capital == 185.0


class TestWinRateCalculation:
    """P2: Test win rate calculation logic."""

    @pytest.mark.asyncio
    async def test_win_rate_with_positive_pnl(
        self,
        recorder: DailyStatisticsRecorder,
        trade_repo: TradeRepository,
        test_state: ThreadSafeState,
        clean_tables: None,
    ) -> None:
        """Test win rate calculation with positive daily PnL."""
        # Create trades
        for i in range(4):
            trade = _create_trade_with_today_timestamp(
                market_id=f"market-{i}",
                mode=TradeMode.PAPER,
                status=TradeStatus.FILLED,
            )
            await trade_repo.save(trade)

        # Set positive daily PnL
        await test_state.update_capital(20.0)

        stats = await recorder.record_daily_stats(TradeMode.PAPER)

        assert stats.total_trades == 4
        assert stats.win_rate is not None
        # With positive PnL, win rate should be >= 0.5 (using >= for boundary)
        assert stats.win_rate >= 0.5

    @pytest.mark.asyncio
    async def test_win_rate_with_negative_pnl(
        self,
        recorder: DailyStatisticsRecorder,
        trade_repo: TradeRepository,
        test_state: ThreadSafeState,
        clean_tables: None,
    ) -> None:
        """Test win rate calculation with negative daily PnL."""
        # Create trades
        for i in range(4):
            trade = _create_trade_with_today_timestamp(
                market_id=f"market-{i}",
                mode=TradeMode.PAPER,
                status=TradeStatus.FILLED,
            )
            await trade_repo.save(trade)

        # Set negative daily PnL
        await test_state.update_capital(-20.0)

        stats = await recorder.record_daily_stats(TradeMode.PAPER)

        assert stats.total_trades == 4
        assert stats.win_rate is not None
        # With negative PnL, win rate should be <= 0.5 (using <= for boundary)
        assert stats.win_rate <= 0.5


class TestModeSeparation:
    """P2: Test that PAPER and LIVE modes are tracked separately."""

    @pytest.mark.asyncio
    async def test_paper_and_live_stats_separate(
        self,
        recorder: DailyStatisticsRecorder,
        trade_repo: TradeRepository,
        stats_repo: StatisticsRepository,
        clean_tables: None,
    ) -> None:
        """Test that PAPER and LIVE statistics are tracked separately."""
        # Create trades in both modes
        paper_trade = _create_trade_with_today_timestamp(
            market_id="paper-market",
            mode=TradeMode.PAPER,
            status=TradeStatus.FILLED,
        )
        await trade_repo.save(paper_trade)

        live_trade = _create_trade_with_today_timestamp(
            market_id="live-market",
            mode=TradeMode.LIVE,
            status=TradeStatus.FILLED,
        )
        await trade_repo.save(live_trade)

        # Record stats for both modes
        paper_stats = await recorder.record_daily_stats(TradeMode.PAPER)
        live_stats = await recorder.record_daily_stats(TradeMode.LIVE)

        # Both should have 1 trade but be separate records
        assert paper_stats.mode == TradeMode.PAPER
        assert paper_stats.total_trades == 1

        assert live_stats.mode == TradeMode.LIVE
        assert live_stats.total_trades == 1

        # Verify they're different records
        assert paper_stats.id != live_stats.id

        # Verify separate queries work
        paper_from_db = await stats_repo.get_by_date(date.today(), TradeMode.PAPER)
        live_from_db = await stats_repo.get_by_date(date.today(), TradeMode.LIVE)

        assert paper_from_db is not None
        assert live_from_db is not None
        assert paper_from_db.id != live_from_db.id
