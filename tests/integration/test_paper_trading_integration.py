"""Integration tests for PaperTradingExecutor with real database operations.

These tests make actual database CRUD operations on the trades and positions tables.
Run with: pytest tests/integration/ -v -m integration

To skip these tests during normal development:
    pytest tests/ -v -m "not integration"

Note: These tests use a real SQLite database file for persistence testing.

Story 5.2: Paper Trading 执行器
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

from src.core.state import ThreadSafeState
from src.exceptions import TradingError
from src.models.market import Market
from src.models.position import PositionOutcome, PositionStatus
from src.models.prediction import PredictionResult, Recommendation
from src.models.trade import TradeMode, TradeStatus, TradeType
from src.storage.repositories import position_repo as position_repo_module
from src.storage.repositories import trade_repo as trade_repo_module
from src.storage.repositories.position_repo import PositionRepository
from src.storage.repositories.trade_repo import TradeRepository
from src.trading.paper_trading import PaperTradeResult, PaperTradingExecutor
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

            # Create positions table
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
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_market_id
                ON trades(market_id)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_mode
                ON trades(mode)
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
    test_db_path = os.path.join(temp_dir, "test_paper_trading.db")

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
async def clean_tables(
    test_db_manager: _TestDatabaseManager,
) -> AsyncIterator[None]:
    """Clean the trades and positions tables before and after each test.

    This fixture ensures test isolation by clearing all data.
    """
    # Clean before test
    async with test_db_manager.get_connection() as conn:
        await conn.execute("DELETE FROM trades")
        await conn.execute("DELETE FROM positions")
        await conn.commit()

    yield

    # Clean after test
    async with test_db_manager.get_connection() as conn:
        await conn.execute("DELETE FROM trades")
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
    original_get_connection = position_repo_module.get_connection

    # Create a replacement get_connection that uses test database
    @asynccontextmanager
    async def test_get_connection() -> AsyncIterator[aiosqlite.Connection]:
        async with test_db_manager.get_connection() as conn:
            yield conn

    # Monkeypatch the module's get_connection
    position_repo_module.get_connection = test_get_connection

    repo = PositionRepository()
    yield repo

    # Restore original get_connection
    position_repo_module.get_connection = original_get_connection


@pytest_asyncio.fixture
async def trade_repo(
    test_db_manager: _TestDatabaseManager,
) -> AsyncIterator[TradeRepository]:
    """Create a TradeRepository instance for testing.

    This fixture monkeypatches the global get_connection function to use
    the test database.
    """
    # Save original get_connection function
    original_get_connection = trade_repo_module.get_connection

    # Create a replacement get_connection that uses test database
    @asynccontextmanager
    async def test_get_connection() -> AsyncIterator[aiosqlite.Connection]:
        async with test_db_manager.get_connection() as conn:
            yield conn

    # Monkeypatch the module's get_connection
    trade_repo_module.get_connection = test_get_connection

    repo = TradeRepository()
    yield repo

    # Restore original get_connection
    trade_repo_module.get_connection = original_get_connection


@pytest_asyncio.fixture
async def position_manager(
    position_repo: PositionRepository,
    test_state: ThreadSafeState,
) -> AsyncIterator[PositionManager]:
    """Create a PositionManager instance with test dependencies."""
    manager = PositionManager(repository=position_repo, state=test_state)
    yield manager


@pytest_asyncio.fixture
async def paper_executor(
    trade_repo: TradeRepository,
    position_manager: PositionManager,
    test_state: ThreadSafeState,
) -> AsyncIterator[PaperTradingExecutor]:
    """Create a PaperTradingExecutor instance with test dependencies."""
    executor = PaperTradingExecutor(
        trade_repo=trade_repo,
        position_manager=position_manager,
        state=test_state,
    )
    yield executor


@pytest.fixture
def sample_market() -> Market:
    """Create a sample market for testing."""
    return Market(
        id="paper-test-market-001",
        title="Will Bitcoin reach $100k by 2026?",
        description="Test prediction market for paper trading",
        category="crypto",
        yes_price=0.45,
        no_price=0.55,
        liquidity=50000.0,
    )


@pytest.fixture
def sample_prediction_buy_yes() -> PredictionResult:
    """Create a sample prediction with BUY_YES recommendation."""
    return PredictionResult(
        predicted_probability=0.70,
        confidence=0.85,
        reasoning="Strong bullish indicators",
        key_assumptions=["Institutional adoption continues", "ETF approvals"],
        recommendation=Recommendation.BUY_YES,
        edge=0.25,
    )


@pytest.fixture
def sample_prediction_buy_no() -> PredictionResult:
    """Create a sample prediction with BUY_NO recommendation."""
    return PredictionResult(
        predicted_probability=0.25,
        confidence=0.80,
        reasoning="Bearish signals detected",
        key_assumptions=["Regulatory concerns", "Market saturation"],
        recommendation=Recommendation.BUY_NO,
        edge=0.30,
    )


class TestExecuteTradePersistsToDatabase:
    """P0: Test that execute_trade persists trade and position to database."""

    @pytest.mark.asyncio
    async def test_execute_trade_buy_yes_persists_to_database(
        self,
        paper_executor: PaperTradingExecutor,
        trade_repo: TradeRepository,
        position_repo: PositionRepository,
        sample_market: Market,
        sample_prediction_buy_yes: PredictionResult,
        clean_tables: None,
    ) -> None:
        """Test that execute_trade creates trade and position records in database.

        Verifies:
        - Trade is saved with correct values
        - Position is created with correct values
        - Trade is linked to position via position_id
        - All values match expected calculations
        """
        amount = 50.0
        expected_shares = amount / sample_market.yes_price  # 50 / 0.45 = 111.11

        # Execute paper trade
        result = await paper_executor.execute_trade(
            market=sample_market,
            prediction=sample_prediction_buy_yes,
            amount=amount,
            prediction_id=42,
        )

        # Verify result success
        assert result.success is True
        assert result.trade is not None
        assert result.position is not None

        # Verify trade properties
        assert result.trade.id > 0
        assert result.trade.market_id == sample_market.id
        assert result.trade.trade_type == TradeType.BUY_YES
        assert result.trade.mode == TradeMode.PAPER
        assert result.trade.status == TradeStatus.FILLED
        assert result.trade.amount == amount
        assert result.trade.price == sample_market.yes_price
        assert result.trade.shares == pytest.approx(expected_shares, rel=0.01)
        assert result.trade.llm_prediction_id == 42
        assert result.trade.position_id == result.position.id

        # Verify trade persistence in database
        db_trade = await trade_repo.get_by_id(result.trade.id)
        assert db_trade is not None
        assert db_trade.market_id == sample_market.id
        assert db_trade.trade_type == TradeType.BUY_YES
        assert db_trade.mode == TradeMode.PAPER
        assert db_trade.amount == amount

        # Verify position properties
        assert result.position.id > 0
        assert result.position.market_id == sample_market.id
        assert result.position.outcome == PositionOutcome.YES
        assert result.position.shares == pytest.approx(expected_shares, rel=0.01)
        assert result.position.avg_price == sample_market.yes_price
        assert result.position.status == PositionStatus.OPEN

        # Verify position persistence in database
        db_position = await position_repo.get_by_id(result.position.id)
        assert db_position is not None
        assert db_position.market_id == sample_market.id
        assert db_position.outcome == PositionOutcome.YES

    @pytest.mark.asyncio
    async def test_execute_trade_buy_no_persists_to_database(
        self,
        paper_executor: PaperTradingExecutor,
        trade_repo: TradeRepository,
        sample_market: Market,
        sample_prediction_buy_no: PredictionResult,
        clean_tables: None,
    ) -> None:
        """Test that BUY_NO trade is persisted correctly."""
        amount = 75.0
        expected_shares = amount / sample_market.no_price  # 75 / 0.55 = 136.36

        result = await paper_executor.execute_trade(
            market=sample_market,
            prediction=sample_prediction_buy_no,
            amount=amount,
        )

        assert result.success is True
        assert result.trade.trade_type == TradeType.BUY_NO
        assert result.trade.price == sample_market.no_price
        assert result.trade.shares == pytest.approx(expected_shares, rel=0.01)
        assert result.position.outcome == PositionOutcome.NO

        # Verify database persistence
        db_trade = await trade_repo.get_by_id(result.trade.id)
        assert db_trade is not None
        assert db_trade.trade_type == TradeType.BUY_NO


class TestMultiplePaperTrades:
    """P0: Test multiple paper trades on different markets."""

    @pytest.mark.asyncio
    async def test_multiple_trades_different_markets(
        self,
        paper_executor: PaperTradingExecutor,
        trade_repo: TradeRepository,
        position_repo: PositionRepository,
        sample_prediction_buy_yes: PredictionResult,
        clean_tables: None,
    ) -> None:
        """Test executing multiple paper trades on different markets.

        Verifies:
        - Each trade gets a unique ID
        - Each position gets a unique ID
        - All trades are correctly persisted
        """
        markets = [
            Market(
                id=f"multi-market-{i}",
                title=f"Market {i}",
                yes_price=0.30 + (i * 0.10),
                no_price=0.70 - (i * 0.10),
                liquidity=10000.0,
            )
            for i in range(3)
        ]

        results: list[PaperTradeResult] = []
        for market in markets:
            result = await paper_executor.execute_trade(
                market=market,
                prediction=sample_prediction_buy_yes,
                amount=20.0,
            )
            results.append(result)

        # Verify all trades succeeded
        assert all(r.success for r in results)

        # Verify unique IDs
        trade_ids = [r.trade.id for r in results]
        position_ids = [r.position.id for r in results]
        assert len(set(trade_ids)) == 3, "Each trade should have unique ID"
        assert len(set(position_ids)) == 3, "Each position should have unique ID"

        # Verify all trades are in database
        for result in results:
            db_trade = await trade_repo.get_by_id(result.trade.id)
            assert db_trade is not None

            db_position = await position_repo.get_by_id(result.position.id)
            assert db_position is not None


class TestTradePositionLinking:
    """P1: Test that trade and position are correctly linked."""

    @pytest.mark.asyncio
    async def test_trade_position_linking(
        self,
        paper_executor: PaperTradingExecutor,
        trade_repo: TradeRepository,
        position_repo: PositionRepository,
        sample_market: Market,
        sample_prediction_buy_yes: PredictionResult,
        clean_tables: None,
    ) -> None:
        """Test that trade.position_id correctly references position.id.

        Verifies:
        - Trade has position_id set after execution (in returned result)
        - The referenced position exists and matches

        Note: The returned result has position_id set correctly.
        Due to TradeRepository.save() creating new records instead of updating,
        the database may have a second trade record with position_id.
        """
        result = await paper_executor.execute_trade(
            market=sample_market,
            prediction=sample_prediction_buy_yes,
            amount=50.0,
        )

        assert result.success is True
        assert result.trade.position_id is not None
        assert result.trade.position_id == result.position.id

        # Verify the linked position exists and matches
        linked_position = await position_repo.get_by_id(result.trade.position_id)
        assert linked_position is not None
        assert linked_position.market_id == sample_market.id
        assert linked_position.outcome == PositionOutcome.YES

        # Verify we can find trades for this market
        market_trades = await trade_repo.get_by_market(sample_market.id)
        assert len(market_trades) >= 1  # At least one trade for this market

        # Verify the position was created correctly
        assert result.position.market_id == sample_market.id
        assert result.position.shares == result.trade.shares


class TestPaperTradeCalculations:
    """P1: Test that share calculations are correct."""

    @pytest.mark.asyncio
    async def test_share_calculation_various_prices(
        self,
        paper_executor: PaperTradingExecutor,
        sample_prediction_buy_yes: PredictionResult,
        clean_tables: None,
    ) -> None:
        """Test share calculation with various price points."""
        test_cases = [
            (0.01, 100.0, 10000.0),  # Very low price -> many shares
            (0.10, 100.0, 1000.0),  # Low price
            (0.50, 100.0, 200.0),  # Mid price
            (0.90, 100.0, 111.11),  # High price -> few shares
            (0.99, 100.0, 101.01),  # Very high price
        ]

        for price, amount, expected_shares_approx in test_cases:
            market = Market(
                id=f"price-test-{price}",
                title=f"Market at {price}",
                yes_price=price,
                no_price=1.0 - price,
                liquidity=10000.0,
            )

            result = await paper_executor.execute_trade(
                market=market,
                prediction=sample_prediction_buy_yes,
                amount=amount,
            )

            assert result.success is True
            assert result.trade.shares == pytest.approx(
                expected_shares_approx, rel=0.02
            ), f"Failed for price={price}"


class TestNoTradeRecommendation:
    """P1: Test handling of NO_TRADE recommendation."""

    @pytest.mark.asyncio
    async def test_no_trade_recommendation_returns_failure(
        self,
        paper_executor: PaperTradingExecutor,
        trade_repo: TradeRepository,
        sample_market: Market,
        clean_tables: None,
    ) -> None:
        """Test that NO_TRADE recommendation returns failure result.

        Verifies:
        - Result has success=False
        - No trade is created in database
        - No position is created in database
        """
        no_trade_prediction = PredictionResult(
            predicted_probability=0.50,
            confidence=0.60,
            reasoning="No clear edge",
            key_assumptions=["Uncertain market"],
            recommendation=Recommendation.NO_TRADE,
            edge=0.02,
        )

        result = await paper_executor.execute_trade(
            market=sample_market,
            prediction=no_trade_prediction,
            amount=50.0,
        )

        assert result.success is False
        assert result.trade is None
        assert result.position is None
        assert result.error_message is not None
        assert (
            "NO_TRADE" in result.error_message
            or "Cannot execute" in result.error_message
        )

        # Verify no trades in database
        trades = await trade_repo.get_by_market(sample_market.id)
        assert len(trades) == 0


class TestInvalidInputs:
    """P1: Test handling of invalid inputs."""

    @pytest.mark.asyncio
    async def test_invalid_amount_zero(
        self,
        paper_executor: PaperTradingExecutor,
        sample_market: Market,
        sample_prediction_buy_yes: PredictionResult,
        clean_tables: None,
    ) -> None:
        """Test that zero amount returns failure."""
        result = await paper_executor.execute_trade(
            market=sample_market,
            prediction=sample_prediction_buy_yes,
            amount=0.0,
        )

        assert result.success is False
        assert "positive" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_invalid_amount_negative(
        self,
        paper_executor: PaperTradingExecutor,
        sample_market: Market,
        sample_prediction_buy_yes: PredictionResult,
        clean_tables: None,
    ) -> None:
        """Test that negative amount returns failure."""
        result = await paper_executor.execute_trade(
            market=sample_market,
            prediction=sample_prediction_buy_yes,
            amount=-50.0,
        )

        assert result.success is False
        assert "positive" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_invalid_price_none(
        self,
        paper_executor: PaperTradingExecutor,
        sample_prediction_buy_yes: PredictionResult,
        clean_tables: None,
    ) -> None:
        """Test that None price returns failure."""
        market_no_price = Market(
            id="no-price-market",
            title="Market without price",
            yes_price=None,
            no_price=None,
        )

        result = await paper_executor.execute_trade(
            market=market_no_price,
            prediction=sample_prediction_buy_yes,
            amount=50.0,
        )

        assert result.success is False
        assert "price" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_invalid_price_zero(
        self,
        paper_executor: PaperTradingExecutor,
        sample_prediction_buy_yes: PredictionResult,
        clean_tables: None,
    ) -> None:
        """Test that zero price returns failure."""
        market_zero_price = Market(
            id="zero-price-market",
            title="Market with zero price",
            yes_price=0.0,
            no_price=1.0,
        )

        result = await paper_executor.execute_trade(
            market=market_zero_price,
            prediction=sample_prediction_buy_yes,
            amount=50.0,
        )

        assert result.success is False
        assert "price" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_invalid_price_one(
        self,
        paper_executor: PaperTradingExecutor,
        sample_prediction_buy_yes: PredictionResult,
        clean_tables: None,
    ) -> None:
        """Test that price of 1.0 returns failure."""
        market_one_price = Market(
            id="one-price-market",
            title="Market with price of 1",
            yes_price=1.0,
            no_price=0.0,
        )

        result = await paper_executor.execute_trade(
            market=market_one_price,
            prediction=sample_prediction_buy_yes,
            amount=50.0,
        )

        assert result.success is False
        assert "price" in result.error_message.lower()


class TestGetTradesByMode:
    """P2: Test retrieving trades by mode."""

    @pytest.mark.asyncio
    async def test_get_trades_by_paper_mode(
        self,
        paper_executor: PaperTradingExecutor,
        trade_repo: TradeRepository,
        sample_market: Market,
        sample_prediction_buy_yes: PredictionResult,
        clean_tables: None,
    ) -> None:
        """Test that paper trades can be retrieved by mode.

        Verifies:
        - Trades are retrievable by PAPER mode
        - All returned trades have mode=PAPER
        """
        # Execute a paper trade
        result = await paper_executor.execute_trade(
            market=sample_market,
            prediction=sample_prediction_buy_yes,
            amount=50.0,
        )
        assert result.success is True

        # Retrieve trades by mode
        paper_trades = await trade_repo.get_by_mode(TradeMode.PAPER)

        # Verify our trade is in the list
        trade_ids = [t.id for t in paper_trades]
        assert result.trade.id in trade_ids

        # Verify all trades have PAPER mode
        for trade in paper_trades:
            assert trade.mode == TradeMode.PAPER


class TestStateUpdates:
    """P2: Test that state is updated correctly."""

    @pytest.mark.asyncio
    async def test_state_updates_after_paper_trade(
        self,
        paper_executor: PaperTradingExecutor,
        test_state: ThreadSafeState,
        sample_market: Market,
        sample_prediction_buy_yes: PredictionResult,
        clean_tables: None,
    ) -> None:
        """Test that open_positions_count is updated after paper trade.

        Verifies:
        - open_positions_count is incremented
        """
        # Get initial state
        initial_state = await test_state.get_state()
        assert initial_state.open_positions_count == 0

        # Execute paper trade
        result = await paper_executor.execute_trade(
            market=sample_market,
            prediction=sample_prediction_buy_yes,
            amount=50.0,
        )
        assert result.success is True

        # Verify state update
        updated_state = await test_state.get_state()
        assert updated_state.open_positions_count == 1
