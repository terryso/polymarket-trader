"""Integration tests for TradingExecutor with real database operations.

These tests verify the complete trading decision flow from LLM analysis
to trade execution using actual database operations.

Run with: pytest tests/integration/ -v -m integration

To skip these tests during normal development:
    pytest tests/ -v -m "not integration"

Story 5.3: 交易决策流程
"""

from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import pytest
import pytest_asyncio

from src.core.state import ThreadSafeState
from src.models.market import Market
from src.models.position import PositionOutcome, PositionStatus
from src.models.prediction import PredictionResult, Recommendation
from src.models.trade import TradeMode, TradeStatus, TradeType
from src.storage.repositories import position_repo as position_repo_module
from src.storage.repositories import statistics_repo as statistics_repo_module
from src.storage.repositories import trade_repo as trade_repo_module
from src.storage.repositories.position_repo import PositionRepository
from src.storage.repositories.statistics_repo import StatisticsRepository
from src.storage.repositories.trade_repo import TradeRepository
from src.trading.executor import TradingDecision, TradingExecutor
from src.trading.paper_trading import PaperTradingExecutor
from src.trading.position_manager import PositionManager
from src.trading.risk_control import RiskCheckResult, RiskController

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

        Creates all tables required for trading executor tests.
        """
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        async with self.get_connection() as conn:
            # Create markets table
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

            # Create predictions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL,
                    predicted_probability REAL,
                    confidence REAL,
                    reasoning TEXT,
                    key_assumptions TEXT,
                    model_used TEXT,
                    recommendation TEXT,
                    edge REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
                    cur_price REAL,
                    initial_value REAL,
                    current_value REAL,
                    pnl REAL,
                    status TEXT,
                    opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    closed_at DATETIME,
                    take_profit_order_id TEXT
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
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    polymarket_order_id TEXT,
                    exit_type TEXT
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
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_statistics_date_mode
                ON statistics(date, mode)
            """)

            await conn.commit()


# Module-level test database manager
_test_db_manager: _TestDatabaseManager | None = None


@pytest_asyncio.fixture(scope="module")
async def test_db_manager() -> AsyncIterator[_TestDatabaseManager]:
    """Create a test database manager with a temporary database file."""
    global _test_db_manager

    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_executor.db")

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
    """Clean all tables before and after each test."""
    async with test_db_manager.get_connection() as conn:
        await conn.execute("DELETE FROM trades")
        await conn.execute("DELETE FROM positions")
        await conn.execute("DELETE FROM statistics")
        await conn.commit()

    yield

    async with test_db_manager.get_connection() as conn:
        await conn.execute("DELETE FROM trades")
        await conn.execute("DELETE FROM positions")
        await conn.execute("DELETE FROM statistics")
        await conn.commit()


@pytest_asyncio.fixture
async def test_state() -> AsyncIterator[ThreadSafeState]:
    """Create a fresh ThreadSafeState instance for testing."""
    state = ThreadSafeState(initial_capital=200.0)
    yield state


def _create_test_get_connection(db_manager: _TestDatabaseManager):
    """Create a get_connection function for test database."""

    @asynccontextmanager
    async def get_connection() -> AsyncIterator[aiosqlite.Connection]:
        async with db_manager.get_connection() as conn:
            yield conn

    return get_connection


@pytest_asyncio.fixture
async def position_repo(
    test_db_manager: _TestDatabaseManager,
) -> AsyncIterator[PositionRepository]:
    """Create a PositionRepository instance for testing."""
    original_get_connection = position_repo_module.get_connection
    position_repo_module.get_connection = _create_test_get_connection(test_db_manager)

    repo = PositionRepository()
    yield repo

    position_repo_module.get_connection = original_get_connection


@pytest_asyncio.fixture
async def trade_repo(
    test_db_manager: _TestDatabaseManager,
) -> AsyncIterator[TradeRepository]:
    """Create a TradeRepository instance for testing."""
    original_get_connection = trade_repo_module.get_connection
    trade_repo_module.get_connection = _create_test_get_connection(test_db_manager)

    repo = TradeRepository()
    yield repo

    trade_repo_module.get_connection = original_get_connection


@pytest_asyncio.fixture
async def stats_repo(
    test_db_manager: _TestDatabaseManager,
) -> AsyncIterator[StatisticsRepository]:
    """Create a StatisticsRepository instance for testing."""
    original_get_connection = statistics_repo_module.get_connection
    statistics_repo_module.get_connection = _create_test_get_connection(test_db_manager)

    repo = StatisticsRepository()
    yield repo

    statistics_repo_module.get_connection = original_get_connection


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


@pytest_asyncio.fixture
async def risk_controller(test_state: ThreadSafeState) -> AsyncIterator[RiskController]:
    """Create a mock RiskController that allows all trades."""

    class MockRiskController:
        async def check_trade_allowed(
            self, prediction: PredictionResult, market: Market
        ) -> RiskCheckResult:
            return RiskCheckResult(
                allowed=True,
                reasons=[],
                position_ratio=0.20,
            )

    yield MockRiskController()


@pytest_asyncio.fixture
async def llm_analyzer() -> AsyncIterator[AsyncMock]:
    """Create a mock LLMAnalyzer that returns successful predictions."""

    class MockLLMAnalyzer:
        async def analyze_market(self, market: Market) -> PredictionResult:
            return PredictionResult(
                predicted_probability=0.70,
                confidence=0.85,
                reasoning="Strong bullish indicators",
                key_assumptions=["Institutional adoption continues"],
                recommendation=Recommendation.BUY_YES,
                edge=0.25,
            )

    yield MockLLMAnalyzer()


@pytest_asyncio.fixture
async def trading_executor(
    llm_analyzer: AsyncMock,
    risk_controller: RiskController,
    paper_executor: PaperTradingExecutor,
    test_state: ThreadSafeState,
) -> AsyncIterator[TradingExecutor]:
    """Create a TradingExecutor instance with test dependencies."""
    executor = TradingExecutor(
        llm_analyzer=llm_analyzer,
        risk_controller=risk_controller,
        paper_executor=paper_executor,
        state=test_state,
    )
    yield executor


@pytest.fixture
def sample_market() -> Market:
    """Create a sample market for testing."""
    return Market(
        id="executor-test-market-001",
        title="Will Bitcoin reach $100k by 2026?",
        description="Test prediction market for executor integration",
        category="crypto",
        yes_price=0.45,
        no_price=0.55,
        liquidity=50000.0,
    )


class TestProcessMarketPersistsToDatabase:
    """P0: Test that process_market persists trade and position to database."""

    @pytest.mark.asyncio
    async def test_process_market_success_persists_to_database(
        self,
        trading_executor: TradingExecutor,
        trade_repo: TradeRepository,
        position_repo: PositionRepository,
        sample_market: Market,
        clean_tables: None,
    ) -> None:
        """Test that process_market creates trade and position records in database.

        Verifies:
        - TradingDecision is successful
        - Trade is saved with correct values
        - Position is created with correct values
        """
        decision = await trading_executor.process_market(sample_market)

        # Verify decision success
        assert decision.success is True
        assert decision.skipped is False
        assert decision.trade is not None
        assert decision.position is not None
        assert decision.prediction is not None

        # Verify trade properties
        assert decision.trade.id > 0
        assert decision.trade.market_id == sample_market.id
        assert decision.trade.trade_type == TradeType.BUY_YES
        assert decision.trade.mode == TradeMode.PAPER
        assert decision.trade.status == TradeStatus.FILLED

        # Verify trade persistence in database
        db_trade = await trade_repo.get_by_id(decision.trade.id)
        assert db_trade is not None
        assert db_trade.market_id == sample_market.id
        assert db_trade.trade_type == TradeType.BUY_YES

        # Verify position persistence in database
        db_position = await position_repo.get_by_id(decision.position.id)
        assert db_position is not None
        assert db_position.market_id == sample_market.id
        assert db_position.outcome == PositionOutcome.YES

    @pytest.mark.asyncio
    async def test_process_market_risk_check_rejected(
        self,
        llm_analyzer: AsyncMock,
        paper_executor: PaperTradingExecutor,
        test_state: ThreadSafeState,
        trade_repo: TradeRepository,
        sample_market: Market,
        clean_tables: None,
    ) -> None:
        """Test that rejected risk check skips trade without database changes."""

        class RejectingRiskController:
            async def check_trade_allowed(
                self, prediction: PredictionResult, market: Market
            ) -> RiskCheckResult:
                return RiskCheckResult(
                    allowed=False,
                    reasons=["Confidence too low"],
                    position_ratio=0.0,
                )

        executor = TradingExecutor(
            llm_analyzer=llm_analyzer,
            risk_controller=RejectingRiskController(),
            paper_executor=paper_executor,
            state=test_state,
        )

        decision = await executor.process_market(sample_market)

        # Verify decision was skipped
        assert decision.success is True
        assert decision.skipped is True
        assert decision.trade is None
        assert decision.position is None
        assert "Confidence too low" in decision.reason

        # Verify no trades in database
        trades = await trade_repo.get_by_market(sample_market.id)
        assert len(trades) == 0


class TestProcessMarketsBatch:
    """P0: Test batch processing of multiple markets."""

    @pytest.mark.asyncio
    async def test_process_markets_multiple_markets(
        self,
        trading_executor: TradingExecutor,
        trade_repo: TradeRepository,
        position_repo: PositionRepository,
        clean_tables: None,
    ) -> None:
        """Test processing multiple markets in batch.

        Verifies:
        - All markets are processed
        - Each trade gets unique ID
        - All trades are persisted correctly
        """
        markets = [
            Market(
                id=f"batch-market-{i}",
                title=f"Market {i}",
                yes_price=0.30 + (i * 0.10),
                no_price=0.70 - (i * 0.10),
                liquidity=10000.0,
            )
            for i in range(3)
        ]

        decisions = await trading_executor.process_markets(markets)

        # Verify all decisions
        assert len(decisions) == 3
        assert all(d.success for d in decisions)
        assert all(not d.skipped for d in decisions)

        # Verify unique trade IDs
        trade_ids = [d.trade.id for d in decisions if d.trade]
        assert len(set(trade_ids)) == 3

        # Verify all trades in database
        for decision in decisions:
            if decision.trade:
                db_trade = await trade_repo.get_by_id(decision.trade.id)
                assert db_trade is not None


class TestPositionSizeCalculation:
    """P1: Test position size calculation with real state."""

    @pytest.mark.asyncio
    async def test_position_size_with_real_capital(
        self,
        trading_executor: TradingExecutor,
        sample_market: Market,
        clean_tables: None,
    ) -> None:
        """Test that position size is calculated based on current capital.

        With 20% position ratio and $200 capital, trade amount should be $40.
        """
        decision = await trading_executor.process_market(sample_market)

        assert decision.success is True
        assert decision.trade is not None
        # 20% of $200 = $40
        assert decision.trade.amount == 40.0


class TestLLMAnalysisFailure:
    """P1: Test handling of LLM analysis failure."""

    @pytest.mark.asyncio
    async def test_llm_analysis_failure(
        self,
        paper_executor: PaperTradingExecutor,
        test_state: ThreadSafeState,
        risk_controller: RiskController,
        trade_repo: TradeRepository,
        sample_market: Market,
        clean_tables: None,
    ) -> None:
        """Test that LLM analysis failure is handled gracefully."""

        class FailingLLMAnalyzer:
            async def analyze_market(self, market: Market) -> PredictionResult:
                raise Exception("API error")

        executor = TradingExecutor(
            llm_analyzer=FailingLLMAnalyzer(),
            risk_controller=risk_controller,
            paper_executor=paper_executor,
            state=test_state,
        )

        decision = await executor.process_market(sample_market)

        assert decision.success is False
        assert decision.error_message is not None
        assert "API error" in decision.error_message

        # Verify no trades in database
        trades = await trade_repo.get_by_market(sample_market.id)
        assert len(trades) == 0


class TestTradeExecutionFailure:
    """P1: Test handling of trade execution failure."""

    @pytest.mark.asyncio
    async def test_trade_execution_failure(
        self,
        llm_analyzer: AsyncMock,
        test_state: ThreadSafeState,
        risk_controller: RiskController,
        sample_market: Market,
        clean_tables: None,
    ) -> None:
        """Test that trade execution failure is handled gracefully."""

        class FailingPaperExecutor:
            async def execute_trade(
                self,
                market: Market,
                prediction: PredictionResult,
                amount: float,
                prediction_id: int | None = None,
            ):
                from src.trading.paper_trading import PaperTradeResult

                return PaperTradeResult(
                    trade=None,
                    position=None,
                    success=False,
                    error_message="Database error",
                )

        executor = TradingExecutor(
            llm_analyzer=llm_analyzer,
            risk_controller=risk_controller,
            paper_executor=FailingPaperExecutor(),
            state=test_state,
        )

        decision = await executor.process_market(sample_market)

        assert decision.success is False
        assert "Database error" in decision.error_message


class TestStateUpdatesAfterTrade:
    """P2: Test that system state is updated correctly after trade."""

    @pytest.mark.asyncio
    async def test_state_open_positions_count(
        self,
        trading_executor: TradingExecutor,
        test_state: ThreadSafeState,
        sample_market: Market,
        clean_tables: None,
    ) -> None:
        """Test that open_positions_count is incremented after successful trade."""
        initial_state = await test_state.get_state()
        assert initial_state.open_positions_count == 0

        decision = await trading_executor.process_market(sample_market)
        assert decision.success is True

        updated_state = await test_state.get_state()
        assert updated_state.open_positions_count == 1

    @pytest.mark.asyncio
    async def test_state_multiple_trades(
        self,
        trading_executor: TradingExecutor,
        test_state: ThreadSafeState,
        clean_tables: None,
    ) -> None:
        """Test state tracking with multiple trades."""
        markets = [
            Market(
                id=f"state-market-{i}",
                title=f"Market {i}",
                yes_price=0.40 + (i * 0.05),
                no_price=0.60 - (i * 0.05),
                liquidity=10000.0,
            )
            for i in range(3)
        ]

        for market in markets:
            decision = await trading_executor.process_market(market)
            assert decision.success is True

        final_state = await test_state.get_state()
        assert final_state.open_positions_count == 3


class TestTradingDecisionResult:
    """P2: Test TradingDecision result structure."""

    @pytest.mark.asyncio
    async def test_trading_decision_structure(
        self,
        trading_executor: TradingExecutor,
        sample_market: Market,
        clean_tables: None,
    ) -> None:
        """Test that TradingDecision contains all expected fields."""
        decision = await trading_executor.process_market(sample_market)

        assert decision.market_id == sample_market.id
        assert decision.success is True
        assert decision.skipped is False
        assert decision.trade is not None
        assert decision.position is not None
        assert decision.prediction is not None
        assert decision.reason is None
        assert decision.error_message is None

        # Verify prediction structure
        assert decision.prediction.recommendation == Recommendation.BUY_YES
        assert decision.prediction.confidence == 0.85

        # Verify trade structure
        assert decision.trade.trade_type == TradeType.BUY_YES
        assert decision.trade.mode == TradeMode.PAPER
        assert decision.trade.status == TradeStatus.FILLED

        # Verify position structure
        assert decision.position.outcome == PositionOutcome.YES
        assert decision.position.status == PositionStatus.OPEN
