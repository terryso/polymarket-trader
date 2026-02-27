"""Tests for LiveTradingExecutor sell_position method.

Story 10.1: 卖出执行器
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.market import Market
from src.models.position import Position, PositionOutcome, PositionStatus
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.trading.live_trading import LiveTradingExecutor, SellResult


class TestSellResult:
    """测试 SellResult 数据类."""

    def test_default_values(self) -> None:
        """测试默认值."""
        result = SellResult()

        assert result.trade is None
        assert result.position is None
        assert result.realized_pnl == 0.0
        assert result.success is True
        assert result.error_message is None

    def test_success_result(self) -> None:
        """测试成功结果."""
        trade = Trade(
            id=1,
            market_id="test-market",
            trade_type=TradeType.SELL_YES,
            mode=TradeMode.LIVE,
            amount=55.0,
            price=0.55,
            shares=100.0,
            status=TradeStatus.FILLED,
        )
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=0.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=0.0,
            pnl=10.0,
            status=PositionStatus.CLOSED,
        )

        result = SellResult(
            trade=trade,
            position=position,
            realized_pnl=10.0,
            success=True,
        )

        assert result.success is True
        assert result.trade == trade
        assert result.position == position
        assert result.realized_pnl == 10.0
        assert result.error_message is None

    def test_failed_result(self) -> None:
        """测试失败结果."""
        result = SellResult(
            success=False,
            error_message="Position not found",
        )

        assert result.success is False
        assert result.error_message == "Position not found"


class TestTradeTypeSell:
    """测试 SELL_YES 和 SELL_NO 枚举值."""

    def test_sell_yes_exists(self) -> None:
        """测试 SELL_YES 枚举值存在."""
        assert TradeType.SELL_YES == "SELL_YES"

    def test_sell_no_exists(self) -> None:
        """测试 SELL_NO 枚举值存在."""
        assert TradeType.SELL_NO == "SELL_NO"

    def test_sell_types_are_strings(self) -> None:
        """测试卖出类型是字符串枚举."""
        assert isinstance(TradeType.SELL_YES.value, str)
        assert isinstance(TradeType.SELL_NO.value, str)


class TestLiveTradingExecutorSell:
    """测试 LiveTradingExecutor.sell_position 方法."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Mock PolymarketClient."""
        client = MagicMock()
        # Mock the underlying ClobClient
        client._client = MagicMock()
        client._client.create_and_post_order = MagicMock(
            return_value={"orderID": "test-order-123", "success": True}
        )
        return client

    @pytest.fixture
    def mock_trade_repo(self) -> AsyncMock:
        """Mock TradeRepository."""
        repo = AsyncMock()

        async def save_trade(trade: Trade) -> Trade:
            if trade.id == 0:
                trade.id = 1
            return trade

        repo.save = AsyncMock(side_effect=save_trade)
        return repo

    @pytest.fixture
    def mock_position_manager(self) -> AsyncMock:
        """Mock PositionManager."""
        manager = AsyncMock()
        manager._repo = AsyncMock()

        # Mock close_position for full sell
        async def close_position(position_id: int, final_price: float, market=None):
            return Position(
                id=position_id,
                market_id="test-market",
                outcome=PositionOutcome.YES,
                shares=0.0,
                avg_price=0.45,
                initial_value=45.0,
                current_value=0.0,
                pnl=(final_price - 0.45) * 100.0,
                status=PositionStatus.CLOSED,
                closed_at=datetime.now(timezone.utc),
            )

        manager.close_position = AsyncMock(side_effect=close_position)

        # Mock _repo.update for partial sell
        async def update_position(position: Position) -> Position:
            return position

        manager._repo.update = AsyncMock(side_effect=update_position)

        # Tech-Spec: Single Source of Truth - mock the API fetch method
        # Default: return a position with 100 shares (same as sample_position)
        async def get_position_by_market_from_api(market_id: str):
            # Return a default position - tests can override this if needed
            return Position(
                id=1,
                market_id=market_id,
                outcome=PositionOutcome.YES,
                shares=100.0,  # Default shares for sell tests
                avg_price=0.45,
                initial_value=45.0,
                current_value=55.0,
                pnl=10.0,
                status=PositionStatus.OPEN,
            )

        manager.get_position_by_market_from_api = AsyncMock(
            side_effect=get_position_by_market_from_api
        )

        return manager

    @pytest.fixture
    def mock_state(self) -> AsyncMock:
        """Mock ThreadSafeState."""
        state = AsyncMock()
        state.update_capital = AsyncMock()
        return state

    @pytest.fixture
    def executor(
        self,
        mock_client: MagicMock,
        mock_trade_repo: AsyncMock,
        mock_position_manager: AsyncMock,
        mock_state: AsyncMock,
    ) -> LiveTradingExecutor:
        """创建测试用执行器."""
        return LiveTradingExecutor(
            client=mock_client,
            trade_repo=mock_trade_repo,
            position_manager=mock_position_manager,
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
            clob_token_ids=["yes-token-id", "no-token-id"],
            yes_price=0.55,
            no_price=0.45,
            liquidity=50000.0,
        )

    @pytest.fixture
    def sample_position_yes(self) -> Position:
        """创建示例 YES 持仓."""
        return Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=55.0,
            pnl=10.0,
            status=PositionStatus.OPEN,
        )

    @pytest.fixture
    def sample_position_no(self) -> Position:
        """创建示例 NO 持仓."""
        return Position(
            id=2,
            market_id="test-market",
            outcome=PositionOutcome.NO,
            shares=100.0,
            avg_price=0.55,
            initial_value=55.0,
            current_value=45.0,
            pnl=-10.0,
            status=PositionStatus.OPEN,
        )

    # ========== Full Sell Tests ==========

    @pytest.mark.asyncio
    async def test_sell_full_position_yes_success(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
        sample_position_yes: Position,
        mock_client: MagicMock,
        mock_trade_repo: AsyncMock,
        mock_position_manager: AsyncMock,
        mock_state: AsyncMock,
    ) -> None:
        """测试全部卖出 YES 持仓成功."""
        result = await executor.sell_position(
            position=sample_position_yes,
            market=sample_market,
        )

        # Verify result
        assert result.success is True
        assert result.trade is not None
        assert result.trade.trade_type == TradeType.SELL_YES
        assert result.trade.shares == 100.0
        # Sell price is slightly below market price for quick execution
        assert result.trade.price == pytest.approx(
            0.539, rel=1e-2
        )  # 0.55 * 0.98 discount
        # Realized PnL adjusted for discount
        assert result.realized_pnl == pytest.approx(
            8.9, rel=1e-1
        )  # (0.539 - 0.45) * 100

        # Verify order was placed with SELL side
        mock_client._client.create_and_post_order.assert_called_once()
        call_args = mock_client._client.create_and_post_order.call_args[0][0]
        assert call_args.side == "SELL"
        assert call_args.token_id == "yes-token-id"

        # Verify trade was saved
        mock_trade_repo.save.assert_called()

        # Verify position was closed
        mock_position_manager.close_position.assert_called_once()

        # Verify capital was updated
        mock_state.update_capital.assert_called_once()
        call_args = mock_state.update_capital.call_args[0][0]
        assert call_args == pytest.approx(53.9, rel=1e-1)  # 100 * 0.539

    @pytest.mark.asyncio
    async def test_sell_full_position_no_success(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
        sample_position_no: Position,
        mock_client: MagicMock,
    ) -> None:
        """测试全部卖出 NO 持仓成功."""
        result = await executor.sell_position(
            position=sample_position_no,
            market=sample_market,
        )

        assert result.success is True
        assert result.trade is not None
        assert result.trade.trade_type == TradeType.SELL_NO

        # Verify order used NO token
        call_args = mock_client._client.create_and_post_order.call_args[0][0]
        assert call_args.token_id == "no-token-id"

    # ========== Partial Sell Tests ==========

    @pytest.mark.asyncio
    async def test_sell_partial_position_success(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
        sample_position_yes: Position,
        mock_client: MagicMock,
        mock_trade_repo: AsyncMock,
        mock_position_manager: AsyncMock,
        mock_state: AsyncMock,
    ) -> None:
        """测试部分卖出成功."""
        # Sell 50 shares out of 100
        result = await executor.sell_position(
            position=sample_position_yes,
            market=sample_market,
            shares=50.0,
        )

        assert result.success is True
        assert result.trade is not None
        assert result.trade.shares == 50.0
        assert result.realized_pnl == pytest.approx(
            4.45, rel=1e-1
        )  # (0.539 - 0.45) * 50

        # Position should NOT be closed
        mock_position_manager.close_position.assert_not_called()

        # Verify position was updated via repo
        mock_position_manager._repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_sell_partial_position_updates_remaining_shares(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
        sample_position_yes: Position,
    ) -> None:
        """测试部分卖出更新剩余份额."""
        result = await executor.sell_position(
            position=sample_position_yes,
            market=sample_market,
            shares=30.0,
        )

        assert result.success is True
        # The position in the result should have remaining shares
        # Note: In the actual implementation, the position object is modified in place
        assert sample_position_yes.shares == 70.0  # 100 - 30

    # ========== Sell Reason Tests ==========

    @pytest.mark.asyncio
    async def test_sell_with_reason_manual(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
        sample_position_yes: Position,
    ) -> None:
        """测试手动卖出."""
        result = await executor.sell_position(
            position=sample_position_yes,
            market=sample_market,
            reason="manual",
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_sell_with_reason_take_profit(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
        sample_position_yes: Position,
    ) -> None:
        """测试止盈卖出."""
        result = await executor.sell_position(
            position=sample_position_yes,
            market=sample_market,
            reason="take_profit",
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_sell_with_reason_stop_loss(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
        sample_position_no: Position,
    ) -> None:
        """测试止损卖出."""
        result = await executor.sell_position(
            position=sample_position_no,
            market=sample_market,
            reason="stop_loss",
        )

        assert result.success is True

    # ========== Error Handling Tests ==========

    @pytest.mark.asyncio
    async def test_sell_closed_position_fails(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
    ) -> None:
        """测试卖出已关闭持仓失败."""
        closed_position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=0.0,
            pnl=0.0,
            status=PositionStatus.CLOSED,
        )

        result = await executor.sell_position(
            position=closed_position,
            market=sample_market,
        )

        assert result.success is False
        assert "not open" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_sell_shares_exceeds_position_sells_all(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
        sample_position_yes: Position,
    ) -> None:
        """测试卖出份额超过持仓数量时自动卖全部."""
        # New behavior: automatically caps to actual position
        result = await executor.sell_position(
            position=sample_position_yes,
            market=sample_market,
            shares=200.0,  # More than 100 shares held
        )

        # Should succeed and sell all 100 shares
        assert result.success is True
        assert result.trade is not None
        assert result.trade.shares == 100.0  # Capped to actual position

    @pytest.mark.asyncio
    async def test_sell_zero_shares_fails(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
        sample_position_yes: Position,
    ) -> None:
        """测试卖出零份额失败."""
        result = await executor.sell_position(
            position=sample_position_yes,
            market=sample_market,
            shares=0.0,
        )

        assert result.success is False
        assert "invalid" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_sell_negative_shares_fails(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
        sample_position_yes: Position,
    ) -> None:
        """测试卖出负份额失败."""
        result = await executor.sell_position(
            position=sample_position_yes,
            market=sample_market,
            shares=-10.0,
        )

        assert result.success is False
        assert "invalid" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_sell_api_error(
        self,
        mock_client: MagicMock,
        mock_trade_repo: AsyncMock,
        mock_position_manager: AsyncMock,
        mock_state: AsyncMock,
        sample_market: Market,
        sample_position_yes: Position,
    ) -> None:
        """测试 API 调用失败."""
        # Configure mock to return error
        mock_client._client.create_and_post_order = MagicMock(
            return_value={"success": False, "errorMsg": "Insufficient balance"}
        )

        executor = LiveTradingExecutor(
            client=mock_client,
            trade_repo=mock_trade_repo,
            position_manager=mock_position_manager,
            state=mock_state,
        )

        result = await executor.sell_position(
            position=sample_position_yes,
            market=sample_market,
        )

        assert result.success is False
        assert "insufficient balance" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_sell_market_without_token_ids(
        self,
        executor: LiveTradingExecutor,
        sample_position_yes: Position,
    ) -> None:
        """测试市场没有 token IDs."""
        market_no_tokens = Market(
            id="test-market",
            title="Test Market",
            yes_price=0.55,
            no_price=0.45,
            clob_token_ids=None,
        )

        result = await executor.sell_position(
            position=sample_position_yes,
            market=market_no_tokens,
        )

        assert result.success is False
        assert "clob token" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_sell_market_without_price(
        self,
        executor: LiveTradingExecutor,
        sample_position_yes: Position,
    ) -> None:
        """测试市场没有价格."""
        market_no_price = Market(
            id="test-market",
            title="Test Market",
            clob_token_ids=["yes-token", "no-token"],
            yes_price=None,
            no_price=0.45,
        )

        result = await executor.sell_position(
            position=sample_position_yes,
            market=market_no_price,
        )

        assert result.success is False
        assert "does not have" in result.error_message.lower()

    # ========== Helper Method Tests ==========

    def test_get_sell_trade_type_yes(
        self,
        executor: LiveTradingExecutor,
        sample_position_yes: Position,
    ) -> None:
        """测试获取 YES 持仓的卖出类型."""
        trade_type = executor._get_sell_trade_type(sample_position_yes)
        assert trade_type == TradeType.SELL_YES

    def test_get_sell_trade_type_no(
        self,
        executor: LiveTradingExecutor,
        sample_position_no: Position,
    ) -> None:
        """测试获取 NO 持仓的卖出类型."""
        trade_type = executor._get_sell_trade_type(sample_position_no)
        assert trade_type == TradeType.SELL_NO

    def test_get_sell_token_id_yes(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
        sample_position_yes: Position,
    ) -> None:
        """测试获取 YES 持仓的卖出 token ID."""
        token_id = executor._get_sell_token_id(sample_position_yes, sample_market)
        assert token_id == "yes-token-id"

    def test_get_sell_token_id_no(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
        sample_position_no: Position,
    ) -> None:
        """测试获取 NO 持仓的卖出 token ID."""
        token_id = executor._get_sell_token_id(sample_position_no, sample_market)
        assert token_id == "no-token-id"

    def test_get_sell_price_yes(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
        sample_position_yes: Position,
    ) -> None:
        """测试获取 YES 持仓的卖出价格."""
        price = executor._get_sell_price(sample_position_yes, sample_market)
        # Sell price uses 2% discount for quick execution
        assert price == pytest.approx(0.539, rel=1e-2)  # 0.55 * 0.98

    def test_get_sell_price_no(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
        sample_position_no: Position,
    ) -> None:
        """测试获取 NO 持仓的卖出价格."""
        price = executor._get_sell_price(sample_position_no, sample_market)
        # Sell price uses 2% discount for quick execution
        assert price == pytest.approx(0.441, rel=1e-2)  # 0.45 * 0.98

    # ========== PnL Calculation Tests ==========

    @pytest.mark.asyncio
    async def test_realized_pnl_profit(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
        sample_position_yes: Position,
    ) -> None:
        """测试已实现盈利计算."""
        # Position: bought at 0.45, selling at 0.539 (2% discount)
        # PnL = (0.539 - 0.45) * 100 = 8.9
        result = await executor.sell_position(
            position=sample_position_yes,
            market=sample_market,
        )

        assert result.success is True
        assert result.realized_pnl == pytest.approx(8.9, rel=1e-1)

    @pytest.mark.asyncio
    async def test_realized_pnl_loss(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
        sample_position_no: Position,
    ) -> None:
        """测试已实现亏损计算."""
        # Position: bought at 0.55, selling at 0.441 (2% discount)
        # PnL = (0.441 - 0.55) * 100 = -10.9
        result = await executor.sell_position(
            position=sample_position_no,
            market=sample_market,
        )

        assert result.success is True
        assert result.realized_pnl == pytest.approx(-10.9, rel=1e-1)

    @pytest.mark.asyncio
    async def test_realized_pnl_partial_sell(
        self,
        executor: LiveTradingExecutor,
        sample_market: Market,
        sample_position_yes: Position,
    ) -> None:
        """测试部分卖出的已实现盈亏计算."""
        # Sell 30 shares at 0.539 (2% discount), bought at 0.45
        # PnL = (0.539 - 0.45) * 30 = 2.67
        result = await executor.sell_position(
            position=sample_position_yes,
            market=sample_market,
            shares=30.0,
        )

        assert result.success is True
        assert result.realized_pnl == pytest.approx(2.67, rel=1e-1)

    # ========== Market Resolved Tests ==========

    @pytest.mark.asyncio
    async def test_sell_orderbook_not_exist_closes_position(
        self,
        mock_client: MagicMock,
        mock_trade_repo: AsyncMock,
        mock_position_manager: AsyncMock,
        mock_state: AsyncMock,
        sample_market: Market,
        sample_position_yes: Position,
    ) -> None:
        """测试 orderbook 不存在时（市场已结算）自动关闭持仓."""
        # Configure mock to raise exception with orderbook not found
        mock_client._client.create_and_post_order = MagicMock(
            side_effect=Exception(
                "PolyApiException[status_code=400, error_message={'error': 'the orderbook 13815952460361514493880496712561164230868624302562138286445313445449019645304 does not exist'}]"
            )
        )

        # Configure position manager mock
        closed_position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=0.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=0.0,
            pnl=0.0,
            status=PositionStatus.CLOSED,
        )
        mock_position_manager.close_position = AsyncMock(return_value=closed_position)

        executor = LiveTradingExecutor(
            client=mock_client,
            trade_repo=mock_trade_repo,
            position_manager=mock_position_manager,
            state=mock_state,
        )

        result = await executor.sell_position(
            position=sample_position_yes,
            market=sample_market,
        )

        # Position should be closed successfully (market resolved)
        assert result.success is True
        assert result.trade is None  # No trade was executed
        assert result.position is not None
        assert result.position.status == PositionStatus.CLOSED
        assert "market resolved" in result.error_message.lower()
        mock_position_manager.close_position.assert_called_once()

    @pytest.mark.asyncio
    async def test_sell_orderbook_not_exist_close_fails(
        self,
        mock_client: MagicMock,
        mock_trade_repo: AsyncMock,
        mock_position_manager: AsyncMock,
        mock_state: AsyncMock,
        sample_market: Market,
        sample_position_yes: Position,
    ) -> None:
        """测试 orderbook 不存在且关闭持仓失败时返回错误."""
        # Configure mock to raise exception with orderbook not found
        mock_client._client.create_and_post_order = MagicMock(
            side_effect=Exception(
                "PolyApiException[status_code=400, error_message={'error': 'the orderbook 123 does not exist'}]"
            )
        )

        # Configure position manager mock to fail
        mock_position_manager.close_position = AsyncMock(
            side_effect=Exception("Database error")
        )

        executor = LiveTradingExecutor(
            client=mock_client,
            trade_repo=mock_trade_repo,
            position_manager=mock_position_manager,
            state=mock_state,
        )

        result = await executor.sell_position(
            position=sample_position_yes,
            market=sample_market,
        )

        # Should fail since we couldn't close the position
        assert result.success is False
        assert (
            "orderbook" in result.error_message.lower()
            or "does not exist" in result.error_message.lower()
        )

    @pytest.mark.asyncio
    async def test_sell_orderbook_not_exist_zero_current_value(
        self,
        mock_client: MagicMock,
        mock_trade_repo: AsyncMock,
        mock_position_manager: AsyncMock,
        mock_state: AsyncMock,
        sample_market: Market,
    ) -> None:
        """测试 orderbook 不存在且 current_value 为 0 时使用 avg_price 作为 fallback."""
        # Create position with zero current_value but valid avg_price
        position_zero_value = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=0.0,  # Zero current value
            pnl=0.0,
            status=PositionStatus.OPEN,
        )

        # Configure mock to raise exception with orderbook not found
        mock_client._client.create_and_post_order = MagicMock(
            side_effect=Exception(
                "PolyApiException[status_code=400, error_message={'error': 'the orderbook 123 does not exist'}]"
            )
        )
        mock_client._client.get_positions = MagicMock(return_value=[])

        # Configure position manager mock
        closed_position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=0.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=0.0,
            pnl=-45.0,
            status=PositionStatus.CLOSED,
        )
        mock_position_manager.close_position = AsyncMock(return_value=closed_position)
        mock_position_manager.get_position_by_market_from_api = AsyncMock(
            return_value=position_zero_value
        )

        executor = LiveTradingExecutor(
            client=mock_client,
            trade_repo=mock_trade_repo,
            position_manager=mock_position_manager,
            state=mock_state,
        )

        result = await executor.sell_position(
            position=position_zero_value,
            market=sample_market,
        )

        # Position should be closed successfully using avg_price as fallback
        assert result.success is True
        assert result.position is not None
        assert result.position.status == PositionStatus.CLOSED
        # Verify close_position was called with a valid price (between 0 and 1)
        call_args = mock_position_manager.close_position.call_args
        final_price = call_args.kwargs.get("final_price")
        assert final_price is not None
        assert 0 < final_price < 1  # Must be valid price
