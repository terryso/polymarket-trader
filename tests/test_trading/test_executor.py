"""Tests for TradingExecutor.

Story 5.3: 交易决策流程
"""

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import settings
from src.models.market import Market
from src.models.position import Position, PositionOutcome, PositionStatus
from src.models.prediction import PredictionResult, Recommendation
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.trading.executor import TradingDecision, TradingExecutor
from src.trading.paper_trading import PaperTradeResult
from src.trading.risk_control import RiskCheckResult


@dataclass
class MockStateSnapshot:
    """Mock state snapshot for testing."""

    current_capital: float = 200.0
    daily_pnl: float = 0.0
    consecutive_losses: int = 0
    open_positions_count: int = 0
    trading_enabled: bool = True
    reduced_mode: bool = False


class TestTradingExecutor:
    """测试 TradingExecutor."""

    @pytest.fixture
    def mock_llm_analyzer(self) -> AsyncMock:
        """Mock LLMAnalyzer."""
        analyzer = AsyncMock()
        analyzer.analyze_market.return_value = PredictionResult(
            predicted_probability=0.70,
            confidence=0.85,
            reasoning="Strong indicators",
            key_assumptions=["Assumption 1"],
            recommendation=Recommendation.BUY_YES,
            edge=0.25,
        )
        return analyzer

    @pytest.fixture
    def mock_risk_controller(self) -> MagicMock:
        """Mock RiskController."""
        controller = MagicMock()
        controller.check_trade_allowed = AsyncMock(
            return_value=RiskCheckResult(
                allowed=True,
                position_ratio=0.20,
                trade_amount=40.0,
                reasons=[],
                failures=[],
            )
        )
        return controller

    @pytest.fixture
    def mock_paper_executor(self) -> AsyncMock:
        """Mock PaperTradingExecutor."""
        executor = AsyncMock()
        executor.execute_trade.return_value = PaperTradeResult(
            trade=Trade(
                id=1,
                market_id="test-market",
                trade_type=TradeType.BUY_YES,
                mode=TradeMode.PAPER,
                amount=40.0,
                price=0.45,
                shares=88.89,
                status=TradeStatus.FILLED,
            ),
            position=Position(
                id=1,
                market_id="test-market",
                outcome=PositionOutcome.YES,
                shares=88.89,
                avg_price=0.45,
                initial_value=40.0,
                current_value=40.0,
                pnl=0.0,
                status=PositionStatus.OPEN,
            ),
            success=True,
        )
        return executor

    @pytest.fixture
    def mock_state(self) -> AsyncMock:
        """Mock ThreadSafeState."""
        state = AsyncMock()
        state.get_state.return_value = MockStateSnapshot(current_capital=200.0)
        return state

    @pytest.fixture
    def executor(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
    ) -> TradingExecutor:
        """创建测试用执行器."""
        return TradingExecutor(
            llm_analyzer=mock_llm_analyzer,
            risk_controller=mock_risk_controller,
            paper_executor=mock_paper_executor,
            state=mock_state,
        )

    @pytest.fixture
    def sample_market(self) -> Market:
        """创建示例市场."""
        return Market(
            id="test-market",
            title="Test Market",
            description="Test Description",
            category="politics",
            yes_price=0.45,
            no_price=0.55,
            liquidity=50000.0,
        )

    # ========== Success Tests ==========

    @pytest.mark.asyncio
    async def test_process_market_success(
        self,
        executor: TradingExecutor,
        sample_market: Market,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
    ) -> None:
        """测试完整流程成功."""
        decision = await executor.process_market(sample_market)

        assert decision.success is True
        assert decision.skipped is False
        assert decision.trade is not None
        assert decision.position is not None
        assert decision.prediction is not None
        assert decision.market_id == sample_market.id

        # Verify all steps were called
        mock_llm_analyzer.analyze_market.assert_called_once_with(sample_market)
        mock_risk_controller.check_trade_allowed.assert_called_once()
        mock_paper_executor.execute_trade.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_market_with_prediction_id(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        sample_market: Market,
    ) -> None:
        """测试预测 ID 传递到交易执行."""
        # Create a prediction-like object with an id attribute
        # (This simulates a stored Prediction from the database)
        from src.models.prediction import Prediction

        prediction_with_id = Prediction(
            id=42,
            market_id=sample_market.id,
            predicted_probability=0.70,
            confidence=0.85,
            reasoning="Strong indicators",
            key_assumptions=["Assumption 1"],
            recommendation=Recommendation.BUY_YES,
            edge=0.25,
        )
        mock_llm_analyzer.analyze_market.return_value = prediction_with_id

        executor = TradingExecutor(
            llm_analyzer=mock_llm_analyzer,
            risk_controller=mock_risk_controller,
            paper_executor=mock_paper_executor,
            state=mock_state,
        )

        # Mock _save_prediction to return the expected ID
        executor._save_prediction = AsyncMock(return_value=42)

        decision = await executor.process_market(sample_market)

        assert decision.success is True
        # Verify prediction_id was passed to execute_trade
        call_kwargs = mock_paper_executor.execute_trade.call_args.kwargs
        assert call_kwargs["prediction_id"] == 42

    # ========== Risk Check Rejection Tests ==========

    @pytest.mark.asyncio
    async def test_process_market_risk_check_rejected(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        sample_market: Market,
    ) -> None:
        """测试风险检查拒绝交易."""
        mock_risk_controller.check_trade_allowed.return_value = RiskCheckResult(
            allowed=False,
            position_ratio=0.0,
            trade_amount=0.0,
            reasons=["Confidence too low"],
            failures=[],
        )

        executor = TradingExecutor(
            llm_analyzer=mock_llm_analyzer,
            risk_controller=mock_risk_controller,
            paper_executor=mock_paper_executor,
            state=mock_state,
        )

        decision = await executor.process_market(sample_market)

        assert decision.success is True  # Process succeeded, but trade was skipped
        assert decision.skipped is True
        assert decision.trade is None
        assert decision.reason == "Confidence too low"

        # Verify trade was not executed
        mock_paper_executor.execute_trade.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_market_risk_check_rejected_multiple_reasons(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        sample_market: Market,
    ) -> None:
        """测试风险检查拒绝交易（多个原因）."""
        mock_risk_controller.check_trade_allowed.return_value = RiskCheckResult(
            allowed=False,
            position_ratio=0.0,
            trade_amount=0.0,
            reasons=["Confidence too low", "Edge too low"],
            failures=[],
        )

        executor = TradingExecutor(
            llm_analyzer=mock_llm_analyzer,
            risk_controller=mock_risk_controller,
            paper_executor=mock_paper_executor,
            state=mock_state,
        )

        decision = await executor.process_market(sample_market)

        assert decision.skipped is True
        # Should use first reason
        assert decision.reason == "Confidence too low"

    # ========== LLM Analysis Failure Tests ==========

    @pytest.mark.asyncio
    async def test_process_market_llm_analysis_fails(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        sample_market: Market,
    ) -> None:
        """测试 LLM 分析失败."""
        from src.analysis.llm_analyzer import AnalysisError

        mock_llm_analyzer.analyze_market.side_effect = AnalysisError(
            message="API error",
            market_id=sample_market.id,
        )

        executor = TradingExecutor(
            llm_analyzer=mock_llm_analyzer,
            risk_controller=mock_risk_controller,
            paper_executor=mock_paper_executor,
            state=mock_state,
        )

        decision = await executor.process_market(sample_market)

        assert decision.success is False
        assert decision.error_message is not None
        assert "API error" in decision.error_message

        # Verify trade was not executed
        mock_paper_executor.execute_trade.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_market_llm_unexpected_exception(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        sample_market: Market,
    ) -> None:
        """测试 LLM 分析意外异常."""
        mock_llm_analyzer.analyze_market.side_effect = RuntimeError("Network error")

        executor = TradingExecutor(
            llm_analyzer=mock_llm_analyzer,
            risk_controller=mock_risk_controller,
            paper_executor=mock_paper_executor,
            state=mock_state,
        )

        decision = await executor.process_market(sample_market)

        assert decision.success is False
        assert "Unexpected error" in decision.error_message
        assert "Network error" in decision.error_message

    # ========== Trade Execution Failure Tests ==========

    @pytest.mark.asyncio
    async def test_process_market_execution_fails(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        sample_market: Market,
    ) -> None:
        """测试交易执行失败."""
        mock_paper_executor.execute_trade.return_value = PaperTradeResult(
            trade=None,
            position=None,
            success=False,
            error_message="Database error",
        )

        executor = TradingExecutor(
            llm_analyzer=mock_llm_analyzer,
            risk_controller=mock_risk_controller,
            paper_executor=mock_paper_executor,
            state=mock_state,
        )

        decision = await executor.process_market(sample_market)

        assert decision.success is False
        assert "Database error" in decision.error_message

    # ========== Batch Processing Tests ==========

    @pytest.mark.asyncio
    async def test_process_markets_batch(
        self,
        executor: TradingExecutor,
    ) -> None:
        """测试批量处理多个市场."""
        markets = [
            Market(
                id=f"market-{i}",
                title=f"Market {i}",
                yes_price=0.45 + i * 0.05,
                no_price=0.55 - i * 0.05,
                liquidity=50000.0,
            )
            for i in range(3)
        ]

        decisions = await executor.process_markets(markets)

        assert len(decisions) == 3
        assert all(d.success for d in decisions)
        assert all(d.trade is not None for d in decisions)

    @pytest.mark.asyncio
    async def test_process_markets_batch_with_failures(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
    ) -> None:
        """测试批量处理包含失败的情况."""
        markets = [
            Market(id="market-1", title="Market 1", yes_price=0.45, no_price=0.55),
            Market(id="market-2", title="Market 2", yes_price=0.50, no_price=0.50),
            Market(id="market-3", title="Market 3", yes_price=0.55, no_price=0.45),
        ]

        # First call succeeds, second fails LLM, third gets rejected by risk
        call_count = 0

        def analyze_side_effect(market):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("LLM error")
            return PredictionResult(
                predicted_probability=0.70,
                confidence=0.85,
                reasoning="Test",
                key_assumptions=[],
                recommendation=Recommendation.BUY_YES,
                edge=0.25,
            )

        mock_llm_analyzer.analyze_market.side_effect = analyze_side_effect

        risk_call_count = 0

        def risk_side_effect(prediction, market):
            nonlocal risk_call_count
            risk_call_count += 1
            if risk_call_count == 2:  # Third market (second successful LLM call)
                return RiskCheckResult(
                    allowed=False,
                    position_ratio=0.0,
                    trade_amount=0.0,
                    reasons=["Edge too low"],
                    failures=[],
                )
            return RiskCheckResult(
                allowed=True,
                position_ratio=0.20,
                trade_amount=40.0,
                reasons=[],
                failures=[],
            )

        mock_risk_controller.check_trade_allowed.side_effect = risk_side_effect

        executor = TradingExecutor(
            llm_analyzer=mock_llm_analyzer,
            risk_controller=mock_risk_controller,
            paper_executor=mock_paper_executor,
            state=mock_state,
        )

        decisions = await executor.process_markets(markets)

        assert len(decisions) == 3
        assert decisions[0].success is True  # First: success
        assert decisions[0].trade is not None
        assert decisions[1].success is False  # Second: LLM error
        assert decisions[2].success is True  # Third: skipped (risk check)
        assert decisions[2].skipped is True

    @pytest.mark.asyncio
    async def test_process_markets_empty_list(
        self,
        executor: TradingExecutor,
    ) -> None:
        """测试空市场列表."""
        decisions = await executor.process_markets([])

        assert decisions == []

    # ========== Position Size Calculation Tests ==========

    @pytest.mark.asyncio
    async def test_calculate_position_size_normal(
        self,
        executor: TradingExecutor,
        mock_state: AsyncMock,
    ) -> None:
        """测试正常仓位计算."""
        mock_state.get_state.return_value = MockStateSnapshot(current_capital=200.0)

        # 20% of $200 = $40
        amount = await executor._calculate_position_size(0.20)
        assert amount == 40.0

    @pytest.mark.asyncio
    async def test_calculate_position_size_below_minimum(
        self,
        executor: TradingExecutor,
        mock_state: AsyncMock,
    ) -> None:
        """测试仓位计算低于最小值时调整到最小值."""
        mock_state.get_state.return_value = MockStateSnapshot(current_capital=200.0)

        # 0.1% of $200 = $0.2, but min is $1
        amount = await executor._calculate_position_size(0.001)
        assert amount == settings.risk.min_bet

    @pytest.mark.asyncio
    async def test_calculate_position_size_above_maximum(
        self,
        executor: TradingExecutor,
        mock_state: AsyncMock,
    ) -> None:
        """测试仓位计算高于最大值时调整到最大值."""
        mock_state.get_state.return_value = MockStateSnapshot(current_capital=200.0)

        # 50% of $200 = $100, but max is 20% = $40
        amount = await executor._calculate_position_size(0.50)
        assert amount == 200.0 * settings.risk.max_single_ratio

    @pytest.mark.asyncio
    async def test_calculate_position_size_very_low_capital(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
    ) -> None:
        """测试资金过低无法满足最小交易."""
        from src.exceptions import TradingError

        mock_state.get_state.return_value = MockStateSnapshot(current_capital=1.0)

        executor = TradingExecutor(
            llm_analyzer=mock_llm_analyzer,
            risk_controller=mock_risk_controller,
            paper_executor=mock_paper_executor,
            state=mock_state,
        )

        # Even with 100% position ratio, can't meet min bet
        with pytest.raises(TradingError) as exc_info:
            await executor._calculate_position_size(1.0)

        assert "minimum bet" in str(exc_info.value).lower()

    # ========== Integration-like Tests ==========

    @pytest.mark.asyncio
    async def test_full_flow_buy_yes(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        sample_market: Market,
    ) -> None:
        """测试完整 BUY_YES 流程."""
        # Configure mocks for BUY_YES scenario
        mock_llm_analyzer.analyze_market.return_value = PredictionResult(
            predicted_probability=0.75,
            confidence=0.85,
            reasoning="Strong YES indicators",
            key_assumptions=["Economic stability"],
            recommendation=Recommendation.BUY_YES,
            edge=0.30,
        )

        mock_paper_executor.execute_trade.return_value = PaperTradeResult(
            trade=Trade(
                id=1,
                market_id=sample_market.id,
                trade_type=TradeType.BUY_YES,
                mode=TradeMode.PAPER,
                amount=40.0,
                price=sample_market.yes_price,
                shares=40.0 / sample_market.yes_price,
                status=TradeStatus.FILLED,
            ),
            position=Position(
                id=1,
                market_id=sample_market.id,
                outcome=PositionOutcome.YES,
                shares=40.0 / sample_market.yes_price,
                avg_price=sample_market.yes_price,
                initial_value=40.0,
                current_value=40.0,
                pnl=0.0,
                status=PositionStatus.OPEN,
            ),
            success=True,
        )

        executor = TradingExecutor(
            llm_analyzer=mock_llm_analyzer,
            risk_controller=mock_risk_controller,
            paper_executor=mock_paper_executor,
            state=mock_state,
        )

        decision = await executor.process_market(sample_market)

        assert decision.success is True
        assert decision.skipped is False
        assert decision.trade.trade_type == TradeType.BUY_YES
        assert decision.position.outcome == PositionOutcome.YES
        assert decision.prediction.recommendation == Recommendation.BUY_YES

    @pytest.mark.asyncio
    async def test_full_flow_buy_no(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        sample_market: Market,
    ) -> None:
        """测试完整 BUY_NO 流程."""
        # Configure mocks for BUY_NO scenario
        mock_llm_analyzer.analyze_market.return_value = PredictionResult(
            predicted_probability=0.25,
            confidence=0.80,
            reasoning="Strong NO indicators",
            key_assumptions=["Political instability"],
            recommendation=Recommendation.BUY_NO,
            edge=0.35,
        )

        mock_paper_executor.execute_trade.return_value = PaperTradeResult(
            trade=Trade(
                id=1,
                market_id=sample_market.id,
                trade_type=TradeType.BUY_NO,
                mode=TradeMode.PAPER,
                amount=40.0,
                price=sample_market.no_price,
                shares=40.0 / sample_market.no_price,
                status=TradeStatus.FILLED,
            ),
            position=Position(
                id=1,
                market_id=sample_market.id,
                outcome=PositionOutcome.NO,
                shares=40.0 / sample_market.no_price,
                avg_price=sample_market.no_price,
                initial_value=40.0,
                current_value=40.0,
                pnl=0.0,
                status=PositionStatus.OPEN,
            ),
            success=True,
        )

        executor = TradingExecutor(
            llm_analyzer=mock_llm_analyzer,
            risk_controller=mock_risk_controller,
            paper_executor=mock_paper_executor,
            state=mock_state,
        )

        decision = await executor.process_market(sample_market)

        assert decision.success is True
        assert decision.skipped is False
        assert decision.trade.trade_type == TradeType.BUY_NO
        assert decision.position.outcome == PositionOutcome.NO
        assert decision.prediction.recommendation == Recommendation.BUY_NO


class TestTradingDecision:
    """测试 TradingDecision 数据类."""

    def test_default_values(self) -> None:
        """测试默认值."""
        decision = TradingDecision(market_id="test-market")

        assert decision.market_id == "test-market"
        assert decision.success is True
        assert decision.skipped is False
        assert decision.trade is None
        assert decision.position is None
        assert decision.prediction is None
        assert decision.reason is None
        assert decision.error_message is None

    def test_success_decision(self) -> None:
        """测试成功决策."""
        trade = Trade(
            id=1,
            market_id="test-market",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=50.0,
            price=0.45,
            shares=111.11,
            status=TradeStatus.FILLED,
        )
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=111.11,
            avg_price=0.45,
            status=PositionStatus.OPEN,
        )

        decision = TradingDecision(
            market_id="test-market",
            success=True,
            skipped=False,
            trade=trade,
            position=position,
        )

        assert decision.success is True
        assert decision.skipped is False
        assert decision.trade == trade
        assert decision.position == position

    def test_skipped_decision(self) -> None:
        """测试跳过决策."""
        decision = TradingDecision(
            market_id="test-market",
            success=True,
            skipped=True,
            reason="Confidence too low",
        )

        assert decision.success is True
        assert decision.skipped is True
        assert decision.reason == "Confidence too low"
        assert decision.trade is None

    def test_failed_decision(self) -> None:
        """测试失败决策."""
        decision = TradingDecision(
            market_id="test-market",
            success=False,
            error_message="LLM API error",
        )

        assert decision.success is False
        assert decision.skipped is False
        assert decision.error_message == "LLM API error"

    def test_decision_with_prediction(self) -> None:
        """测试带预测结果的决策."""
        prediction = PredictionResult(
            predicted_probability=0.70,
            confidence=0.85,
            reasoning="Test reasoning",
            key_assumptions=["Test assumption"],
            recommendation=Recommendation.BUY_YES,
            edge=0.25,
        )

        decision = TradingDecision(
            market_id="test-market",
            success=True,
            skipped=True,
            prediction=prediction,
            reason="Risk check failed",
        )

        assert decision.prediction == prediction
        assert decision.prediction.recommendation == Recommendation.BUY_YES
