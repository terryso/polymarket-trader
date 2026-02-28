"""P0 Tests for Concurrent Batch Processing - Story 5.3.

ATDD Tests for Epic 5, P0 Scenario:
- 5.3-INT-001: 批量市场并发处理

Risk Link: R-002 (并发交易导致持仓状态不一致)

These tests verify thread safety and consistency in concurrent scenarios.
If any test fails, it indicates a potential race condition bug.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.market import Market
from src.models.position import Position, PositionOutcome, PositionStatus
from src.models.prediction import PredictionResult, Recommendation
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.trading.executor import TradingDecision, TradingExecutor
from src.trading.paper_trading import PaperTradeResult


@dataclass
class MockConcurrentState:
    """Mock state for concurrent testing."""

    current_capital: float = 200.0
    daily_pnl: float = 0.0
    consecutive_losses: int = 0
    open_positions_count: int = 0
    trading_enabled: bool = True
    reduced_mode: bool = False
    _lock: asyncio.Lock = None

    def __post_init__(self):
        if self._lock is None:
            self._lock = asyncio.Lock()

    async def get_state(self):
        return self

    async def increment_open_positions(self):
        async with self._lock:
            self.open_positions_count += 1

    async def decrement_open_positions(self):
        async with self._lock:
            self.open_positions_count -= 1


class TestConcurrentBatchProcessingP0:
    """P0 测试: 批量市场并发处理.

    测试场景:
    - 多个市场同时处理
    - 状态一致性验证
    - 竞态条件检测
    """

    @pytest.fixture
    def mock_llm_analyzer(self) -> AsyncMock:
        """Mock LLMAnalyzer with varied responses."""
        call_count = 0

        async def analyze_market(market: Market) -> PredictionResult:
            nonlocal call_count
            call_count += 1

            # Alternate between BUY_YES and BUY_NO
            if call_count % 2 == 0:
                return PredictionResult(
                    predicted_probability=0.25,
                    confidence=0.80,
                    reasoning="Strong NO indicators",
                    key_assumptions=["Test"],
                    recommendation=Recommendation.BUY_NO,
                    edge=0.30,
                )
            return PredictionResult(
                predicted_probability=0.75,
                confidence=0.85,
                reasoning="Strong YES indicators",
                key_assumptions=["Test"],
                recommendation=Recommendation.BUY_YES,
                edge=0.30,
            )

        analyzer = AsyncMock()
        analyzer.analyze_market = analyze_market
        return analyzer

    @pytest.fixture
    def mock_risk_controller(self) -> MagicMock:
        """Mock RiskController."""
        controller = MagicMock()
        controller.check_trade_allowed = AsyncMock(
            return_value=MagicMock(
                allowed=True,
                position_ratio=0.15,
                trade_amount=30.0,
                reasons=[],
                failures=[],
            )
        )
        return controller

    @pytest.fixture
    def concurrent_state(self) -> MockConcurrentState:
        """Create concurrent-safe state."""
        return MockConcurrentState(current_capital=200.0)

    @pytest.fixture
    def mock_paper_executor(self, concurrent_state: MockConcurrentState) -> AsyncMock:
        """Mock PaperTradingExecutor with state tracking."""
        call_count = 0

        async def execute_trade(
            market: Market,
            prediction: PredictionResult,
            amount: float,
            prediction_id: int | None = None,
        ) -> PaperTradeResult:
            nonlocal call_count
            call_count += 1

            # Simulate async operation
            await asyncio.sleep(0.01)

            # Increment position count
            await concurrent_state.increment_open_positions()

            # Create trade
            price = (
                market.yes_price
                if prediction.recommendation == Recommendation.BUY_YES
                else market.no_price
            )
            trade = Trade(
                id=call_count,
                market_id=market.id,
                trade_type=(
                    TradeType.BUY_YES
                    if prediction.recommendation == Recommendation.BUY_YES
                    else TradeType.BUY_NO
                ),
                mode=TradeMode.PAPER,
                amount=amount,
                price=price,
                shares=amount / price,
                status=TradeStatus.FILLED,
            )

            # Create position
            position = Position(
                id=call_count,
                market_id=market.id,
                outcome=(
                    PositionOutcome.YES
                    if prediction.recommendation == Recommendation.BUY_YES
                    else PositionOutcome.NO
                ),
                shares=amount / price,
                avg_price=price,
                initial_value=amount,
                current_value=amount,
                pnl=0.0,
                status=PositionStatus.OPEN,
            )

            return PaperTradeResult(
                trade=trade,
                position=position,
                success=True,
            )

        executor = AsyncMock()
        executor.execute_trade = execute_trade
        return executor

    @pytest.fixture
    def executor(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        concurrent_state: MockConcurrentState,
    ) -> TradingExecutor:
        """Create TradingExecutor for concurrent testing."""
        return TradingExecutor(
            llm_analyzer=mock_llm_analyzer,
            risk_controller=mock_risk_controller,
            paper_executor=mock_paper_executor,
            state=concurrent_state,
        )

    @pytest.fixture
    def multiple_markets(self) -> list[Market]:
        """Create 10 test markets."""
        return [
            Market(
                id=f"market-{i}",
                title=f"Test Market {i}",
                yes_price=0.40 + (i * 0.03),
                no_price=0.60 - (i * 0.03),
                liquidity=50000.0,
            )
            for i in range(10)
        ]

    # ========================================
    # 并发安全测试
    # ========================================

    @pytest.mark.asyncio
    async def test_process_markets_concurrent_safety(
        self,
        executor: TradingExecutor,
        multiple_markets: list[Market],
        concurrent_state: MockConcurrentState,
    ) -> None:
        """测试 10 个市场并发处理的安全性.

        Expected:
        - 所有市场都成功处理
        - 无竞态条件
        - 最终状态一致
        """
        initial_positions = concurrent_state.open_positions_count

        # Process all markets concurrently
        decisions = await executor.process_markets(multiple_markets)

        # Verify all decisions succeeded
        assert len(decisions) == 10, f"Expected 10 decisions, got {len(decisions)}"

        # Count successful trades
        successful_trades = sum(1 for d in decisions if d.success and not d.skipped)
        assert successful_trades == 10, (
            f"Expected all 10 trades to succeed, got {successful_trades}"
        )

        # Verify state consistency
        expected_positions = initial_positions + successful_trades
        assert concurrent_state.open_positions_count == expected_positions, (
            f"Position count mismatch: expected {expected_positions}, "
            f"got {concurrent_state.open_positions_count}"
        )

    @pytest.mark.asyncio
    async def test_process_markets_concurrent_with_rejections(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        concurrent_state: MockConcurrentState,
        multiple_markets: list[Market],
    ) -> None:
        """测试并发处理包含拒绝的情况.

        场景: 部分交易被风控拒绝
        Expected: 状态仍然保持一致
        """
        call_count = 0

        def check_trade_allowed(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Reject every 3rd trade
            if call_count % 3 == 0:
                return MagicMock(
                    allowed=False,
                    position_ratio=0.0,
                    trade_amount=0.0,
                    reasons=["Test rejection"],
                    failures=[],
                )
            return MagicMock(
                allowed=True,
                position_ratio=0.15,
                trade_amount=30.0,
                reasons=[],
                failures=[],
            )

        mock_risk_controller.check_trade_allowed = AsyncMock(
            side_effect=check_trade_allowed
        )

        executor = TradingExecutor(
            llm_analyzer=mock_llm_analyzer,
            risk_controller=mock_risk_controller,
            paper_executor=mock_paper_executor,
            state=concurrent_state,
        )

        decisions = await executor.process_markets(multiple_markets)

        assert len(decisions) == 10

        # Count results
        successful = sum(1 for d in decisions if d.success and not d.skipped)
        skipped = sum(1 for d in decisions if d.skipped)

        # Verify skipped count (should be ~3)
        assert skipped >= 2, f"Expected at least 2 rejections, got {skipped}"

        # Verify state matches actual trades
        assert concurrent_state.open_positions_count == successful, (
            f"Position count should match successful trades: "
            f"{concurrent_state.open_positions_count} != {successful}"
        )

    @pytest.mark.asyncio
    async def test_process_markets_truly_concurrent(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        concurrent_state: MockConcurrentState,
        multiple_markets: list[Market],
    ) -> None:
        """测试真正的并发执行 (asyncio.gather).

        验证 process_markets 内部使用并发处理。
        """
        start_times: list[float] = []
        end_times: list[float] = []

        async def track_execute_trade(
            market: Market,
            prediction: PredictionResult,
            amount: float,
            prediction_id: int | None = None,
        ) -> PaperTradeResult:
            import time

            start_times.append(time.time())
            await asyncio.sleep(0.05)  # Simulate work
            end_times.append(time.time())

            return PaperTradeResult(
                trade=Trade(
                    id=1,
                    market_id=market.id,
                    trade_type=TradeType.BUY_YES,
                    mode=TradeMode.PAPER,
                    amount=amount,
                    price=0.50,
                    shares=amount / 0.50,
                    status=TradeStatus.FILLED,
                ),
                position=Position(
                    id=1,
                    market_id=market.id,
                    outcome=PositionOutcome.YES,
                    shares=amount / 0.50,
                    avg_price=0.50,
                    initial_value=amount,
                    current_value=amount,
                    pnl=0.0,
                    status=PositionStatus.OPEN,
                ),
                success=True,
            )

        mock_paper_executor = AsyncMock()
        mock_paper_executor.execute_trade = track_execute_trade

        executor = TradingExecutor(
            llm_analyzer=mock_llm_analyzer,
            risk_controller=mock_risk_controller,
            paper_executor=mock_paper_executor,
            state=concurrent_state,
        )

        import time

        start_time = time.time()
        await executor.process_markets(multiple_markets)
        total_time = time.time() - start_time

        # If truly concurrent, 10 tasks * 0.05s should take ~0.05-0.1s
        # If sequential, it would take ~0.5s
        assert total_time < 0.5, (
            f"Processing took {total_time:.2f}s, expected < 0.5s for concurrent execution"
        )

    @pytest.mark.asyncio
    async def test_process_markets_state_capital_consistency(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        concurrent_state: MockConcurrentState,
        multiple_markets: list[Market],
    ) -> None:
        """测试并发处理时的资金一致性.

        验证多笔交易同时执行时，资金计算正确。
        """
        trade_amounts: list[float] = []

        async def track_and_execute(
            market: Market,
            prediction: PredictionResult,
            amount: float,
            prediction_id: int | None = None,
        ) -> PaperTradeResult:
            trade_amounts.append(amount)
            await concurrent_state.increment_open_positions()

            return PaperTradeResult(
                trade=Trade(
                    id=1,
                    market_id=market.id,
                    trade_type=TradeType.BUY_YES,
                    mode=TradeMode.PAPER,
                    amount=amount,
                    price=0.50,
                    shares=amount / 0.50,
                    status=TradeStatus.FILLED,
                ),
                position=Position(
                    id=1,
                    market_id=market.id,
                    outcome=PositionOutcome.YES,
                    shares=amount / 0.50,
                    avg_price=0.50,
                    initial_value=amount,
                    current_value=amount,
                    pnl=0.0,
                    status=PositionStatus.OPEN,
                ),
                success=True,
            )

        mock_paper_executor = AsyncMock()
        mock_paper_executor.execute_trade = track_and_execute

        executor = TradingExecutor(
            llm_analyzer=mock_llm_analyzer,
            risk_controller=mock_risk_controller,
            paper_executor=mock_paper_executor,
            state=concurrent_state,
        )

        await executor.process_markets(multiple_markets)

        # Verify all trades were recorded
        assert len(trade_amounts) == 10, (
            f"Expected 10 trade amounts, got {len(trade_amounts)}"
        )

        # Verify total traded amount
        total_traded = sum(trade_amounts)
        expected_total = 10 * 30.0  # 10 trades * $30 each
        assert total_traded == pytest.approx(expected_total, rel=1e-6), (
            f"Total traded amount mismatch: {total_traded} != {expected_total}"
        )


class TestConcurrentStateThreadSafety:
    """ThreadSafeState 并发安全测试."""

    @pytest.mark.asyncio
    async def test_increment_decrement_concurrent(self) -> None:
        """测试并发增减操作的原子性."""
        from src.core.state import ThreadSafeState

        state = ThreadSafeState(initial_capital=200.0)

        async def increment_many():
            for _ in range(100):
                await state.increment_open_positions()

        async def decrement_many():
            for _ in range(50):
                await state.decrement_open_positions()

        # Run concurrently
        await asyncio.gather(increment_many(), decrement_many())

        # Final count should be 100 - 50 = 50
        snapshot = await state.get_state()
        assert snapshot.open_positions_count == 50, (
            f"Expected 50 open positions, got {snapshot.open_positions_count}"
        )

    @pytest.mark.asyncio
    async def test_capital_update_concurrent(self) -> None:
        """测试并发资金更新的原子性."""
        from src.core.state import ThreadSafeState

        state = ThreadSafeState(initial_capital=100.0)

        async def add_capital():
            for _ in range(100):
                await state.update_capital(1.0)

        async def subtract_capital():
            for _ in range(50):
                await state.update_capital(-1.0)

        await asyncio.gather(add_capital(), subtract_capital())

        # Final capital should be 100 + 100 - 50 = 150
        snapshot = await state.get_state()
        assert snapshot.current_capital == pytest.approx(150.0, rel=1e-6), (
            f"Expected capital 150.0, got {snapshot.current_capital}"
        )
