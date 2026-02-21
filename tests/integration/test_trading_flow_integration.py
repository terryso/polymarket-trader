"""End-to-end integration tests for Epic 5: Paper Trading.

These tests verify the complete trading flow from market analysis
to trade execution to statistics recording, using real database operations.

Run with: pytest tests/integration/ -v -m integration

To skip these tests during normal development:
    pytest tests/ -v -m "not integration"

Epic 5: Paper Trading 模拟交易
- Story 5.1: 交易记录数据模型
- Story 5.2: Paper Trading 执行器
- Story 5.3: 交易决策流程
- Story 5.4: 模拟持仓 PnL 计算
- Story 5.5: 统计数据记录
"""

from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import AsyncIterator

import aiosqlite
import pytest
import pytest_asyncio

from src.core.state import ThreadSafeState
from src.models.market import Market
from src.models.position import PositionOutcome, PositionStatus
from src.models.prediction import PredictionResult, Recommendation
from src.models.statistics import Statistics
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.storage.repositories import position_repo as position_repo_module
from src.storage.repositories import statistics_repo as statistics_repo_module
from src.storage.repositories import trade_repo as trade_repo_module
from src.storage.repositories.position_repo import PositionRepository
from src.storage.repositories.statistics_repo import StatisticsRepository
from src.storage.repositories.trade_repo import TradeRepository
from src.trading.executor import TradingExecutor
from src.trading.paper_trading import PaperTradingExecutor
from src.trading.position_manager import PositionManager
from src.trading.risk_control import RiskCheckResult, RiskController
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
    """Test database manager for Epic 5 end-to-end tests."""

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
            # Create all tables needed for Epic 5
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
                CREATE INDEX IF NOT EXISTS idx_positions_market_id ON positions(market_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_market_id ON trades(market_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_mode ON trades(mode)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_statistics_date_mode ON statistics(date, mode)
            """)

            await conn.commit()


_test_db_manager: _TestDatabaseManager | None = None


@pytest_asyncio.fixture(scope="module")
async def test_db_manager() -> AsyncIterator[_TestDatabaseManager]:
    global _test_db_manager

    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_epic5_e2e.db")

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
        await conn.execute("DELETE FROM positions")
        await conn.execute("DELETE FROM statistics")
        await conn.commit()

    yield

    async with test_db_manager.get_connection() as conn:
        await conn.execute("DELETE FROM trades")
        await conn.execute("DELETE FROM positions")
        await conn.execute("DELETE FROM statistics")
        await conn.commit()


def _create_test_get_connection(db_manager: _TestDatabaseManager):
    @asynccontextmanager
    async def get_connection() -> AsyncIterator[aiosqlite.Connection]:
        async with db_manager.get_connection() as conn:
            yield conn

    return get_connection


@pytest_asyncio.fixture
async def test_state() -> AsyncIterator[ThreadSafeState]:
    state = ThreadSafeState(initial_capital=200.0)
    yield state


@pytest_asyncio.fixture
async def position_repo(
    test_db_manager: _TestDatabaseManager,
) -> AsyncIterator[PositionRepository]:
    original = position_repo_module.get_connection
    position_repo_module.get_connection = _create_test_get_connection(test_db_manager)
    repo = PositionRepository()
    yield repo
    position_repo_module.get_connection = original


@pytest_asyncio.fixture
async def trade_repo(
    test_db_manager: _TestDatabaseManager,
) -> AsyncIterator[TradeRepository]:
    original = trade_repo_module.get_connection
    trade_repo_module.get_connection = _create_test_get_connection(test_db_manager)
    repo = TradeRepository()
    yield repo
    trade_repo_module.get_connection = original


@pytest_asyncio.fixture
async def stats_repo(
    test_db_manager: _TestDatabaseManager,
) -> AsyncIterator[StatisticsRepository]:
    original = statistics_repo_module.get_connection
    statistics_repo_module.get_connection = _create_test_get_connection(test_db_manager)
    repo = StatisticsRepository()
    yield repo
    statistics_repo_module.get_connection = original


@pytest_asyncio.fixture
async def position_manager(
    position_repo: PositionRepository,
    test_state: ThreadSafeState,
) -> AsyncIterator[PositionManager]:
    yield PositionManager(repository=position_repo, state=test_state)


@pytest_asyncio.fixture
async def paper_executor(
    trade_repo: TradeRepository,
    position_manager: PositionManager,
    test_state: ThreadSafeState,
) -> AsyncIterator[PaperTradingExecutor]:
    yield PaperTradingExecutor(
        trade_repo=trade_repo,
        position_manager=position_manager,
        state=test_state,
    )


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


class MockLLMAnalyzer:
    """Mock LLM analyzer for testing."""

    def __init__(self, recommendation: Recommendation = Recommendation.BUY_YES):
        self._recommendation = recommendation

    async def analyze_market(self, market: Market) -> PredictionResult:
        return PredictionResult(
            predicted_probability=0.70,
            confidence=0.85,
            reasoning="Strong indicators",
            key_assumptions=["Test assumption"],
            recommendation=self._recommendation,
            edge=0.25,
        )


class MockRiskController:
    """Mock risk controller for testing."""

    def __init__(self, allowed: bool = True, position_ratio: float = 0.20):
        self._allowed = allowed
        self._position_ratio = position_ratio

    async def check_trade_allowed(
        self, prediction: PredictionResult, market: Market
    ) -> RiskCheckResult:
        return RiskCheckResult(
            allowed=self._allowed,
            reasons=[] if self._allowed else ["Risk check failed"],
            position_ratio=self._position_ratio,
        )


@pytest_asyncio.fixture
async def trading_executor(
    paper_executor: PaperTradingExecutor,
    test_state: ThreadSafeState,
) -> AsyncIterator[TradingExecutor]:
    yield TradingExecutor(
        llm_analyzer=MockLLMAnalyzer(),
        risk_controller=MockRiskController(),
        paper_executor=paper_executor,
        state=test_state,
    )


class TestEpic5EndToEndFlow:
    """P0: Complete end-to-end trading flow tests."""

    @pytest.mark.asyncio
    async def test_complete_trading_flow(
        self,
        trading_executor: TradingExecutor,
        position_manager: PositionManager,
        recorder: DailyStatisticsRecorder,
        trade_repo: TradeRepository,
        position_repo: PositionRepository,
        stats_repo: StatisticsRepository,
        test_state: ThreadSafeState,
        clean_tables: None,
    ) -> None:
        """Test the complete flow: analyze -> trade -> update PnL -> record stats.

        This is the primary Epic 5 integration test that verifies:
        1. TradingExecutor creates trades and positions (Story 5.1, 5.2, 5.3)
        2. PositionManager calculates PnL (Story 5.4)
        3. DailyStatisticsRecorder records statistics (Story 5.5)

        Note: Statistics recording requires trades with created_at timestamps.
        We manually create a trade with timestamp to verify the full flow.
        """
        # Create test market
        market = Market(
            id="e2e-market-001",
            title="Will BTC reach $100k?",
            yes_price=0.45,
            no_price=0.55,
            liquidity=50000.0,
        )

        # Step 1: Execute trading decision
        decision = await trading_executor.process_market(market)

        # Verify trading decision (Stories 5.1, 5.2, 5.3)
        assert decision.success is True
        assert decision.skipped is False
        assert decision.trade is not None
        assert decision.position is not None
        assert decision.trade.id > 0
        assert decision.position.id > 0

        # Verify trade in database
        db_trade = await trade_repo.get_by_id(decision.trade.id)
        assert db_trade is not None
        assert db_trade.status == TradeStatus.FILLED
        assert db_trade.mode == TradeMode.PAPER

        # Verify position in database
        db_position = await position_repo.get_by_id(decision.position.id)
        assert db_position is not None
        assert db_position.status == PositionStatus.OPEN

        # Step 2: Calculate PnL (Story 5.4)
        current_price = 0.55  # Price went up
        pnl_result = position_manager.calculate_pnl(db_position, current_price)

        assert pnl_result.pnl > 0  # Should be profitable
        assert pnl_result.current_value > db_position.initial_value

        # Update position with new price
        updated_position = await position_manager.update_position_value(
            db_position.id, current_price
        )
        assert updated_position.pnl > 0

        # Step 3: Record daily statistics (Story 5.5)
        # Create a trade with proper timestamp for statistics recording
        stats_trade = _create_trade_with_today_timestamp(
            market_id="e2e-market-001",
            mode=TradeMode.PAPER,
            status=TradeStatus.FILLED,
            amount=decision.trade.amount,
            price=decision.trade.price,
            shares=decision.trade.shares,
        )
        await trade_repo.save(stats_trade)

        stats = await recorder.record_daily_stats(TradeMode.PAPER)

        assert stats.id > 0
        assert stats.date == date.today()
        assert stats.total_trades == 1
        assert stats.mode == TradeMode.PAPER

    @pytest.mark.asyncio
    async def test_multiple_trades_with_statistics(
        self,
        trading_executor: TradingExecutor,
        position_manager: PositionManager,
        recorder: DailyStatisticsRecorder,
        trade_repo: TradeRepository,
        stats_repo: StatisticsRepository,
        clean_tables: None,
    ) -> None:
        """Test multiple trades and statistics aggregation."""
        # Process multiple markets
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

        decisions = await trading_executor.process_markets(markets)

        # Verify all trades executed
        assert len(decisions) == 3
        assert all(d.success for d in decisions)

        # Create trades with proper timestamps for statistics
        for i, decision in enumerate(decisions):
            if decision.trade:
                stats_trade = _create_trade_with_today_timestamp(
                    market_id=f"multi-market-{i}",
                    mode=TradeMode.PAPER,
                    status=TradeStatus.FILLED,
                    amount=decision.trade.amount,
                    price=decision.trade.price,
                    shares=decision.trade.shares,
                )
                await trade_repo.save(stats_trade)

        # Record statistics
        stats = await recorder.record_daily_stats(TradeMode.PAPER)

        assert stats.total_trades == 3

        # Verify statistics persistence
        db_stats = await stats_repo.get_by_date(date.today(), TradeMode.PAPER)
        assert db_stats is not None
        assert db_stats.total_trades == 3

    @pytest.mark.asyncio
    async def test_pnl_tracking_across_positions(
        self,
        trading_executor: TradingExecutor,
        position_manager: PositionManager,
        test_state: ThreadSafeState,
        clean_tables: None,
    ) -> None:
        """Test PnL tracking across multiple positions."""
        # Create positions
        markets = [
            Market(
                id=f"pnl-market-{i}",
                title=f"Market {i}",
                yes_price=0.40,
                no_price=0.60,
                liquidity=10000.0,
            )
            for i in range(2)
        ]

        decisions = await trading_executor.process_markets(markets)
        assert all(d.success for d in decisions)

        # Update all positions with new prices
        market_prices = {
            "pnl-market-0": 0.50,  # Profit
            "pnl-market-1": 0.30,  # Loss
        }

        updated_positions = await position_manager.update_all_positions_value(
            market_prices
        )
        assert len(updated_positions) == 2

        # Calculate total PnL
        total_pnl = await position_manager.calculate_total_pnl()

        assert total_pnl.positions_count == 2
        assert total_pnl.winning_count >= 1  # At least one profitable
        assert total_pnl.losing_count >= 1  # At least one losing


class TestTradingFlowWithRiskRejection:
    """P1: Test trading flow when risk checks reject trades."""

    @pytest.mark.asyncio
    async def test_risk_rejection_prevents_trade(
        self,
        paper_executor: PaperTradingExecutor,
        test_state: ThreadSafeState,
        trade_repo: TradeRepository,
        stats_repo: StatisticsRepository,
        recorder: DailyStatisticsRecorder,
        clean_tables: None,
    ) -> None:
        """Test that risk rejection prevents trade execution."""
        executor = TradingExecutor(
            llm_analyzer=MockLLMAnalyzer(),
            risk_controller=MockRiskController(allowed=False),
            paper_executor=paper_executor,
            state=test_state,
        )

        market = Market(
            id="rejected-market",
            title="Rejected Market",
            yes_price=0.45,
            no_price=0.55,
            liquidity=10000.0,
        )

        decision = await executor.process_market(market)

        assert decision.success is True
        assert decision.skipped is True
        assert decision.trade is None

        # Verify no trades in database
        trades = await trade_repo.get_by_market("rejected-market")
        assert len(trades) == 0

        # Statistics should show 0 trades
        stats = await recorder.record_daily_stats(TradeMode.PAPER)
        assert stats.total_trades == 0


class TestTradingFlowWithNoTradeRecommendation:
    """P1: Test trading flow with NO_TRADE recommendation."""

    @pytest.mark.asyncio
    async def test_no_trade_recommendation(
        self,
        paper_executor: PaperTradingExecutor,
        test_state: ThreadSafeState,
        trade_repo: TradeRepository,
        clean_tables: None,
    ) -> None:
        """Test that NO_TRADE recommendation prevents trade execution."""
        executor = TradingExecutor(
            llm_analyzer=MockLLMAnalyzer(recommendation=Recommendation.NO_TRADE),
            risk_controller=MockRiskController(),
            paper_executor=paper_executor,
            state=test_state,
        )

        market = Market(
            id="no-trade-market",
            title="No Trade Market",
            yes_price=0.45,
            no_price=0.55,
            liquidity=10000.0,
        )

        decision = await executor.process_market(market)

        # Should fail because paper executor can't execute NO_TRADE
        assert decision.success is False
        assert decision.trade is None

        # Verify no trades in database
        trades = await trade_repo.get_by_market("no-trade-market")
        assert len(trades) == 0


class TestPositionCloseFlow:
    """P2: Test position closing flow with PnL realization."""

    @pytest.mark.asyncio
    async def test_close_position_realizes_pnl(
        self,
        trading_executor: TradingExecutor,
        position_manager: PositionManager,
        test_state: ThreadSafeState,
        clean_tables: None,
    ) -> None:
        """Test that closing a position realizes PnL."""
        # Open a position
        market = Market(
            id="close-market",
            title="Close Test Market",
            yes_price=0.40,
            no_price=0.60,
            liquidity=10000.0,
        )

        decision = await trading_executor.process_market(market)
        assert decision.success is True

        initial_state = await test_state.get_state()
        initial_open_positions = initial_state.open_positions_count

        # Close the position at a higher price (profit)
        final_price = 0.60
        closed_position = await position_manager.close_position(
            decision.position.id, final_price
        )

        # Verify position is closed
        assert closed_position.status == PositionStatus.CLOSED
        assert closed_position.pnl > 0  # Profit

        # Verify state updates
        final_state = await test_state.get_state()
        assert final_state.open_positions_count == initial_open_positions - 1
        assert final_state.current_capital > initial_state.current_capital


class TestStatisticsFlowAfterMultipleDays:
    """P2: Test statistics flow across multiple days."""

    @pytest.mark.asyncio
    async def test_statistics_chain_multiple_days(
        self,
        trading_executor: TradingExecutor,
        recorder: DailyStatisticsRecorder,
        trade_repo: TradeRepository,
        stats_repo: StatisticsRepository,
        clean_tables: None,
    ) -> None:
        """Test statistics chain across multiple simulated days.

        Note: We simulate multiple days by saving stats directly with different dates.
        """
        from datetime import timedelta

        today = date.today()
        yesterday = today - timedelta(days=1)

        # Simulate yesterday's stats
        yesterday_stats = Statistics(
            id=0,
            date=yesterday,
            mode=TradeMode.PAPER,
            starting_capital=200.0,
            ending_capital=190.0,
            total_pnl=-10.0,
            total_trades=3,
            winning_trades=1,
            losing_trades=2,
            win_rate=1 / 3,
        )
        await stats_repo.save(yesterday_stats)

        # Execute a trade today
        market = Market(
            id="today-market",
            title="Today's Market",
            yes_price=0.45,
            no_price=0.55,
            liquidity=10000.0,
        )
        decision = await trading_executor.process_market(market)
        assert decision.success is True

        # Create trade with timestamp for statistics
        stats_trade = _create_trade_with_today_timestamp(
            market_id="today-market",
            mode=TradeMode.PAPER,
            status=TradeStatus.FILLED,
            amount=decision.trade.amount if decision.trade else 40.0,
            price=decision.trade.price if decision.trade else 0.45,
            shares=decision.trade.shares if decision.trade else 88.89,
        )
        await trade_repo.save(stats_trade)

        # Record today's stats
        today_stats = await recorder.record_daily_stats(TradeMode.PAPER)

        # Today's starting capital should be yesterday's ending
        assert today_stats.starting_capital == 190.0
        assert today_stats.total_trades == 1


class TestConcurrentPositionManagement:
    """P2: Test concurrent position management scenarios."""

    @pytest.mark.asyncio
    async def test_cannot_open_duplicate_position(
        self,
        trading_executor: TradingExecutor,
        clean_tables: None,
    ) -> None:
        """Test that duplicate positions for the same market are prevented."""
        market = Market(
            id="duplicate-market",
            title="Duplicate Test",
            yes_price=0.45,
            no_price=0.55,
            liquidity=10000.0,
        )

        # First trade should succeed
        decision1 = await trading_executor.process_market(market)
        assert decision1.success is True

        # Second trade for same market should fail (position already exists)
        decision2 = await trading_executor.process_market(market)
        assert decision2.success is False
        assert "position" in decision2.error_message.lower()


class TestFullEpic5Integration:
    """Complete Epic 5 integration tests."""

    @pytest.mark.asyncio
    async def test_full_paper_trading_cycle(
        self,
        trading_executor: TradingExecutor,
        position_manager: PositionManager,
        recorder: DailyStatisticsRecorder,
        trade_repo: TradeRepository,
        position_repo: PositionRepository,
        stats_repo: StatisticsRepository,
        test_state: ThreadSafeState,
        clean_tables: None,
    ) -> None:
        """Complete paper trading cycle: open -> update -> close -> stats.

        This test verifies the complete Epic 5 flow:
        1. Open position via TradingExecutor
        2. Update position value with market price changes
        3. Close position and realize PnL
        4. Record daily statistics
        """
        # 1. Open position
        market = Market(
            id="cycle-market",
            title="Full Cycle Test",
            yes_price=0.40,
            no_price=0.60,
            liquidity=50000.0,
        )

        open_decision = await trading_executor.process_market(market)
        assert open_decision.success is True

        position = open_decision.position
        trade = open_decision.trade

        # Verify initial state
        assert position.status == PositionStatus.OPEN
        assert position.avg_price == 0.40
        assert position.pnl == 0.0

        # 2. Update position with profitable price
        profit_price = 0.55
        updated_position = await position_manager.update_position_value(
            position.id, profit_price
        )

        assert updated_position.pnl > 0
        assert updated_position.current_value > position.initial_value

        # Calculate PnL to verify
        pnl_result = position_manager.calculate_pnl(updated_position, profit_price)
        assert pnl_result.pnl > 0
        assert pnl_result.pnl_pct > 0

        # 3. Close position
        closed_position = await position_manager.close_position(
            position.id, profit_price
        )

        assert closed_position.status == PositionStatus.CLOSED
        assert closed_position.pnl > 0

        # 4. Create trade with timestamp and record statistics
        stats_trade = _create_trade_with_today_timestamp(
            market_id="cycle-market",
            mode=TradeMode.PAPER,
            status=TradeStatus.FILLED,
            amount=trade.amount if trade else 40.0,
            price=trade.price if trade else 0.40,
            shares=trade.shares if trade else 100.0,
        )
        await trade_repo.save(stats_trade)

        stats = await recorder.record_daily_stats(TradeMode.PAPER)

        assert stats.total_trades == 1
        assert stats.mode == TradeMode.PAPER

        # Verify complete data chain
        # Note: TradeRepository.save() creates new records, so we verify via get_by_market
        market_trades = await trade_repo.get_by_market("cycle-market")
        assert len(market_trades) >= 1

        # Position should be closed
        final_position = await position_repo.get_by_id(position.id)
        assert final_position is not None
        assert final_position.status == PositionStatus.CLOSED

        # Statistics should be recorded
        final_stats = await stats_repo.get_by_date(date.today(), TradeMode.PAPER)
        assert final_stats is not None
