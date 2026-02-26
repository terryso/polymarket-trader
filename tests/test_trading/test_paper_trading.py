"""Tests for PaperTradingExecutor.

Story 5.2: Paper Trading 执行器
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.market import Market
from src.models.position import Position, PositionOutcome, PositionStatus
from src.models.prediction import PredictionResult, Recommendation
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.trading.paper_trading import PaperTradeResult, PaperTradingExecutor


class TestPaperTradingExecutor:
    """测试 PaperTradingExecutor."""

    @pytest.fixture
    def mock_trade_repo(self) -> AsyncMock:
        """Mock TradeRepository."""
        repo = AsyncMock()

        # Set up save to return a trade with an ID
        def make_saved_trade(trade: Trade) -> Trade:
            if trade.id == 0:
                return Trade(
                    id=1,
                    market_id=trade.market_id,
                    trade_type=trade.trade_type,
                    mode=trade.mode,
                    amount=trade.amount,
                    price=trade.price,
                    shares=trade.shares,
                    status=trade.status,
                    llm_prediction_id=trade.llm_prediction_id,
                    position_id=trade.position_id,
                    created_at=trade.created_at,
                )
            return trade

        repo.save.side_effect = make_saved_trade
        return repo

    @pytest.fixture
    def mock_position_manager(self) -> AsyncMock:
        """Mock PositionManager."""
        manager = AsyncMock()

        def make_position(
            market_id: str, outcome: PositionOutcome, shares: float, price: float
        ) -> Position:
            return Position(
                id=1,
                market_id=market_id,
                outcome=outcome,
                shares=shares,
                avg_price=price,
                initial_value=shares * price,
                current_value=shares * price,
                pnl=0.0,
                status=PositionStatus.OPEN,
            )

        manager.open_position.side_effect = make_position
        # Tech-Spec: Single Source of Truth - mock the API fetch method
        manager.get_position_by_market_from_api = AsyncMock(return_value=None)
        return manager

    @pytest.fixture
    def mock_state(self) -> AsyncMock:
        """Mock ThreadSafeState."""
        return AsyncMock()

    @pytest.fixture
    def executor(
        self,
        mock_trade_repo: AsyncMock,
        mock_position_manager: AsyncMock,
        mock_state: AsyncMock,
    ) -> PaperTradingExecutor:
        """创建测试用执行器."""
        return PaperTradingExecutor(mock_trade_repo, mock_position_manager, mock_state)

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

    @pytest.fixture
    def sample_prediction_buy_yes(self) -> PredictionResult:
        """创建示例预测 (BUY_YES)."""
        return PredictionResult(
            predicted_probability=0.70,
            confidence=0.85,
            reasoning="Strong indicators",
            key_assumptions=["Assumption 1"],
            recommendation=Recommendation.BUY_YES,
            edge=0.25,
        )

    @pytest.fixture
    def sample_prediction_buy_no(self) -> PredictionResult:
        """创建示例预测 (BUY_NO)."""
        return PredictionResult(
            predicted_probability=0.30,
            confidence=0.80,
            reasoning="NO is more likely",
            key_assumptions=["Assumption 1"],
            recommendation=Recommendation.BUY_NO,
            edge=0.25,
        )

    @pytest.fixture
    def sample_prediction_no_trade(self) -> PredictionResult:
        """创建示例预测 (NO_TRADE)."""
        return PredictionResult(
            predicted_probability=0.50,
            confidence=0.60,
            reasoning="No clear edge",
            key_assumptions=["Assumption 1"],
            recommendation=Recommendation.NO_TRADE,
            edge=0.02,
        )

    # ========== Success Tests ==========

    @pytest.mark.asyncio
    async def test_execute_trade_buy_yes_success(
        self,
        executor: PaperTradingExecutor,
        sample_market: Market,
        sample_prediction_buy_yes: PredictionResult,
        mock_trade_repo: AsyncMock,
        mock_position_manager: AsyncMock,
    ) -> None:
        """测试 BUY_YES 交易成功."""
        amount = 50.0
        expected_shares = amount / sample_market.yes_price  # 50 / 0.45 = 111.11

        result = await executor.execute_trade(
            sample_market, sample_prediction_buy_yes, amount
        )

        assert result.success is True
        assert result.trade is not None
        assert result.position is not None
        assert result.error_message is None

        # Verify trade properties
        assert result.trade.trade_type == TradeType.BUY_YES
        assert result.trade.mode == TradeMode.PAPER
        assert result.trade.status == TradeStatus.FILLED
        assert result.trade.price == sample_market.yes_price
        assert result.trade.shares == pytest.approx(expected_shares, rel=0.01)
        assert result.trade.amount == amount

        # Verify position creation
        mock_position_manager.open_position.assert_called_once()
        call_kwargs = mock_position_manager.open_position.call_args.kwargs
        assert call_kwargs["market_id"] == sample_market.id
        assert call_kwargs["outcome"] == PositionOutcome.YES
        assert call_kwargs["shares"] == pytest.approx(expected_shares, rel=0.01)
        assert call_kwargs["price"] == sample_market.yes_price

        # Verify trade repo was called twice (save + update with position_id)
        assert mock_trade_repo.save.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_trade_buy_no_success(
        self,
        executor: PaperTradingExecutor,
        sample_market: Market,
        sample_prediction_buy_no: PredictionResult,
        mock_trade_repo: AsyncMock,
        mock_position_manager: AsyncMock,
    ) -> None:
        """测试 BUY_NO 交易成功."""
        amount = 50.0
        expected_shares = amount / sample_market.no_price  # 50 / 0.55 = 90.91

        result = await executor.execute_trade(
            sample_market, sample_prediction_buy_no, amount
        )

        assert result.success is True
        assert result.trade is not None
        assert result.position is not None
        assert result.error_message is None

        # Verify trade properties
        assert result.trade.trade_type == TradeType.BUY_NO
        assert result.trade.mode == TradeMode.PAPER
        assert result.trade.status == TradeStatus.FILLED
        assert result.trade.price == sample_market.no_price
        assert result.trade.shares == pytest.approx(expected_shares, rel=0.01)
        assert result.trade.amount == amount

        # Verify position creation with NO outcome
        mock_position_manager.open_position.assert_called_once()
        call_kwargs = mock_position_manager.open_position.call_args.kwargs
        assert call_kwargs["outcome"] == PositionOutcome.NO

    @pytest.mark.asyncio
    async def test_execute_trade_with_prediction_id(
        self,
        executor: PaperTradingExecutor,
        sample_market: Market,
        sample_prediction_buy_yes: PredictionResult,
        mock_trade_repo: AsyncMock,
    ) -> None:
        """测试带 prediction_id 的交易."""
        prediction_id = 42

        result = await executor.execute_trade(
            sample_market, sample_prediction_buy_yes, 50.0, prediction_id=prediction_id
        )

        assert result.success is True
        assert result.trade.llm_prediction_id == prediction_id

    @pytest.mark.asyncio
    async def test_execute_trade_position_id_linked(
        self,
        executor: PaperTradingExecutor,
        sample_market: Market,
        sample_prediction_buy_yes: PredictionResult,
        mock_trade_repo: AsyncMock,
    ) -> None:
        """测试交易和持仓 ID 关联."""
        result = await executor.execute_trade(
            sample_market, sample_prediction_buy_yes, 50.0
        )

        assert result.success is True
        assert result.trade.position_id == result.position.id

        # Verify that save was called with position_id
        second_save_call = mock_trade_repo.save.call_args_list[1]
        saved_trade = second_save_call.args[0]
        assert saved_trade.position_id == 1

    # ========== Error Tests ==========

    @pytest.mark.asyncio
    async def test_execute_trade_no_trade_recommendation(
        self,
        executor: PaperTradingExecutor,
        sample_market: Market,
        sample_prediction_no_trade: PredictionResult,
    ) -> None:
        """测试 NO_TRADE 推荐应失败."""
        result = await executor.execute_trade(
            sample_market, sample_prediction_no_trade, 50.0
        )

        assert result.success is False
        assert result.trade is None
        assert result.position is None
        assert result.error_message is not None
        assert (
            "NO_TRADE" in result.error_message
            or "Cannot execute" in result.error_message
        )

    @pytest.mark.asyncio
    async def test_execute_trade_invalid_amount_zero(
        self,
        executor: PaperTradingExecutor,
        sample_market: Market,
        sample_prediction_buy_yes: PredictionResult,
    ) -> None:
        """测试金额为 0 应失败."""
        result = await executor.execute_trade(
            sample_market, sample_prediction_buy_yes, 0.0
        )

        assert result.success is False
        assert result.trade is None
        assert result.error_message is not None
        assert "positive" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_trade_invalid_amount_negative(
        self,
        executor: PaperTradingExecutor,
        sample_market: Market,
        sample_prediction_buy_yes: PredictionResult,
    ) -> None:
        """测试负金额应失败."""
        result = await executor.execute_trade(
            sample_market, sample_prediction_buy_yes, -10.0
        )

        assert result.success is False
        assert result.trade is None
        assert result.error_message is not None
        assert "positive" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_trade_none_price(
        self,
        executor: PaperTradingExecutor,
        sample_prediction_buy_yes: PredictionResult,
    ) -> None:
        """测试价格为 None 应失败."""
        market_no_price = Market(
            id="no-price-market",
            title="No Price Market",
            yes_price=None,
            no_price=None,
        )

        result = await executor.execute_trade(
            market_no_price, sample_prediction_buy_yes, 50.0
        )

        assert result.success is False
        assert result.trade is None
        assert result.error_message is not None
        assert "price" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_trade_zero_price(
        self,
        executor: PaperTradingExecutor,
        sample_prediction_buy_yes: PredictionResult,
    ) -> None:
        """测试价格为 0 应失败."""
        market_zero_price = Market(
            id="zero-price-market",
            title="Zero Price Market",
            yes_price=0.0,
            no_price=1.0,
        )

        result = await executor.execute_trade(
            market_zero_price, sample_prediction_buy_yes, 50.0
        )

        assert result.success is False
        assert result.trade is None
        assert result.error_message is not None
        assert "price" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_trade_one_price(
        self,
        executor: PaperTradingExecutor,
        sample_prediction_buy_yes: PredictionResult,
    ) -> None:
        """测试价格为 1 应失败."""
        market_one_price = Market(
            id="one-price-market",
            title="One Price Market",
            yes_price=1.0,
            no_price=0.0,
        )

        result = await executor.execute_trade(
            market_one_price, sample_prediction_buy_yes, 50.0
        )

        assert result.success is False
        assert result.trade is None
        assert result.error_message is not None
        assert "price" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_trade_position_manager_error(
        self,
        mock_trade_repo: AsyncMock,
        mock_state: AsyncMock,
        sample_market: Market,
        sample_prediction_buy_yes: PredictionResult,
    ) -> None:
        """测试 PositionManager 抛出异常时处理."""
        from src.exceptions import TradingError

        mock_position_manager = AsyncMock()
        # Tech-Spec: First check for existing position via API
        mock_position_manager.get_position_by_market_from_api = AsyncMock(return_value=None)
        # Then open_position throws
        mock_position_manager.open_position.side_effect = TradingError(
            "Position already exists"
        )

        executor = PaperTradingExecutor(
            mock_trade_repo, mock_position_manager, mock_state
        )

        result = await executor.execute_trade(
            sample_market, sample_prediction_buy_yes, 50.0
        )

        assert result.success is False
        assert result.trade is None
        assert result.error_message is not None
        assert "Position already exists" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_trade_unexpected_error(
        self,
        mock_trade_repo: AsyncMock,
        mock_position_manager: AsyncMock,
        mock_state: AsyncMock,
        sample_market: Market,
        sample_prediction_buy_yes: PredictionResult,
    ) -> None:
        """测试意外异常时处理."""
        mock_trade_repo.save.side_effect = RuntimeError("Database error")

        executor = PaperTradingExecutor(
            mock_trade_repo, mock_position_manager, mock_state
        )

        result = await executor.execute_trade(
            sample_market, sample_prediction_buy_yes, 50.0
        )

        assert result.success is False
        assert result.trade is None
        assert result.error_message is not None
        assert "Unexpected error" in result.error_message

    # ========== Helper Method Tests ==========

    def test_get_trade_type_buy_yes(self, executor: PaperTradingExecutor) -> None:
        """测试 _get_trade_type 返回 BUY_YES."""
        result = executor._get_trade_type(Recommendation.BUY_YES)
        assert result == TradeType.BUY_YES

    def test_get_trade_type_buy_no(self, executor: PaperTradingExecutor) -> None:
        """测试 _get_trade_type 返回 BUY_NO."""
        result = executor._get_trade_type(Recommendation.BUY_NO)
        assert result == TradeType.BUY_NO

    def test_get_trade_type_no_trade_raises(
        self, executor: PaperTradingExecutor
    ) -> None:
        """测试 _get_trade_type 对 NO_TRADE 抛出异常."""
        from src.exceptions import TradingError

        with pytest.raises(TradingError) as exc_info:
            executor._get_trade_type(Recommendation.NO_TRADE)

        assert "NO_TRADE" in str(exc_info.value)

    def test_get_price_buy_yes(
        self, executor: PaperTradingExecutor, sample_market: Market
    ) -> None:
        """测试 _get_price 返回 yes_price."""
        result = executor._get_price(sample_market, TradeType.BUY_YES)
        assert result == sample_market.yes_price

    def test_get_price_buy_no(
        self, executor: PaperTradingExecutor, sample_market: Market
    ) -> None:
        """测试 _get_price 返回 no_price."""
        result = executor._get_price(sample_market, TradeType.BUY_NO)
        assert result == sample_market.no_price

    def test_calculate_shares(self, executor: PaperTradingExecutor) -> None:
        """测试 _calculate_shares 计算."""
        result = executor._calculate_shares(100.0, 0.5)
        assert result == 200.0

    def test_calculate_shares_zero_price_raises(
        self, executor: PaperTradingExecutor
    ) -> None:
        """测试 _calculate_shares 对 0 价格抛出异常."""
        from src.exceptions import ValidationError

        with pytest.raises(ValidationError):
            executor._calculate_shares(100.0, 0.0)

    def test_calculate_shares_negative_price_raises(
        self, executor: PaperTradingExecutor
    ) -> None:
        """测试 _calculate_shares 对负价格抛出异常."""
        from src.exceptions import ValidationError

        with pytest.raises(ValidationError):
            executor._calculate_shares(100.0, -0.5)

    def test_determine_outcome_buy_yes(self, executor: PaperTradingExecutor) -> None:
        """测试 _determine_outcome 返回 YES."""
        result = executor._determine_outcome(TradeType.BUY_YES)
        assert result == PositionOutcome.YES

    def test_determine_outcome_buy_no(self, executor: PaperTradingExecutor) -> None:
        """测试 _determine_outcome 返回 NO."""
        result = executor._determine_outcome(TradeType.BUY_NO)
        assert result == PositionOutcome.NO

    # ========== Edge Case Tests ==========

    @pytest.mark.asyncio
    async def test_execute_trade_small_amount(
        self,
        executor: PaperTradingExecutor,
        sample_market: Market,
        sample_prediction_buy_yes: PredictionResult,
    ) -> None:
        """测试小金额交易."""
        result = await executor.execute_trade(
            sample_market, sample_prediction_buy_yes, 0.01
        )

        assert result.success is True
        assert result.trade.amount == 0.01
        # Shares should be tiny: 0.01 / 0.45 ≈ 0.022
        assert result.trade.shares == pytest.approx(0.01 / 0.45, rel=0.01)

    @pytest.mark.asyncio
    async def test_execute_trade_large_amount(
        self,
        executor: PaperTradingExecutor,
        sample_market: Market,
        sample_prediction_buy_yes: PredictionResult,
    ) -> None:
        """测试大金额交易."""
        large_amount = 10000.0

        result = await executor.execute_trade(
            sample_market, sample_prediction_buy_yes, large_amount
        )

        assert result.success is True
        assert result.trade.amount == large_amount
        assert result.trade.shares == pytest.approx(large_amount / 0.45, rel=0.01)

    @pytest.mark.asyncio
    async def test_execute_trade_very_low_price(
        self,
        executor: PaperTradingExecutor,
        sample_prediction_buy_yes: PredictionResult,
    ) -> None:
        """测试极低价格交易."""
        market_low_price = Market(
            id="low-price-market",
            title="Low Price Market",
            yes_price=0.01,
            no_price=0.99,
        )

        result = await executor.execute_trade(
            market_low_price, sample_prediction_buy_yes, 10.0
        )

        assert result.success is True
        # Shares should be large: 10 / 0.01 = 1000
        assert result.trade.shares == pytest.approx(1000.0, rel=0.01)


class TestPaperTradeResult:
    """测试 PaperTradeResult 数据类."""

    def test_default_values(self) -> None:
        """测试默认值."""
        result = PaperTradeResult()

        assert result.trade is None
        assert result.position is None
        assert result.success is True
        assert result.error_message is None

    def test_success_result(self) -> None:
        """测试成功结果."""
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

        result = PaperTradeResult(trade=trade, position=position, success=True)

        assert result.trade == trade
        assert result.position == position
        assert result.success is True
        assert result.error_message is None

    def test_failure_result(self) -> None:
        """测试失败结果."""
        result = PaperTradeResult(
            trade=None,
            position=None,
            success=False,
            error_message="Test error",
        )

        assert result.trade is None
        assert result.position is None
        assert result.success is False
        assert result.error_message == "Test error"
