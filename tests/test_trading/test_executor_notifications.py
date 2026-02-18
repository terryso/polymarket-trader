"""Tests for TradingExecutor notification integration.

Story 9.3: 交易事件通知集成
"""

from __future__ import annotations

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


class TestTradingExecutorNotifications:
    """Tests for TradingExecutor notification integration."""

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
    def mock_notifier(self) -> AsyncMock:
        """Create a mock TelegramNotifier."""
        notifier = AsyncMock()
        notifier.send_trade_notification = AsyncMock(return_value=True)
        notifier.send_error_notification = AsyncMock(return_value=True)
        return notifier

    @pytest.fixture
    def sample_market(self) -> Market:
        """Create a sample market."""
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
    def sample_trade(self) -> Trade:
        """Create a sample trade for testing."""
        return Trade(
            id=1,
            market_id="test-market",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=40.0,
            price=0.45,
            shares=88.89,
            status=TradeStatus.FILLED,
        )

    # ========== Initialization Tests ==========

    def test_init_with_notifier(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        mock_notifier: AsyncMock,
    ) -> None:
        """Test initialization with notifier."""
        with patch("src.trading.executor.settings") as mock_settings:
            mock_settings.trading_mode = "PAPER"

            executor = TradingExecutor(
                llm_analyzer=mock_llm_analyzer,
                risk_controller=mock_risk_controller,
                paper_executor=mock_paper_executor,
                state=mock_state,
                notifier=mock_notifier,
            )

            assert executor._notifier is mock_notifier

    def test_init_without_notifier(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
    ) -> None:
        """Test initialization without notifier."""
        with patch("src.trading.executor.settings") as mock_settings:
            mock_settings.trading_mode = "PAPER"

            executor = TradingExecutor(
                llm_analyzer=mock_llm_analyzer,
                risk_controller=mock_risk_controller,
                paper_executor=mock_paper_executor,
                state=mock_state,
            )

            assert executor._notifier is None

    # ========== Trade Success Notification Tests ==========

    @pytest.mark.asyncio
    async def test_notify_on_trade_success(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        mock_notifier: AsyncMock,
        sample_market: Market,
        sample_trade: Trade,
    ) -> None:
        """Test notification sent on trade success."""
        with patch("src.trading.executor.settings") as mock_settings:
            mock_settings.trading_mode = "PAPER"
            mock_settings.risk.min_bet = 5.0
            mock_settings.risk.max_single_ratio = 0.2

            executor = TradingExecutor(
                llm_analyzer=mock_llm_analyzer,
                risk_controller=mock_risk_controller,
                paper_executor=mock_paper_executor,
                state=mock_state,
                notifier=mock_notifier,
            )

            await executor.process_market(sample_market)

            # Verify notification was sent
            mock_notifier.send_trade_notification.assert_called_once()
            call_args = mock_notifier.send_trade_notification.call_args
            assert call_args[0][0] == sample_trade
            assert call_args[0][1] == sample_market

    # ========== Trade Failure Notification Tests ==========

    @pytest.mark.asyncio
    async def test_notify_on_trade_failure(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        mock_notifier: AsyncMock,
        sample_market: Market,
    ) -> None:
        """Test notification sent on trade failure."""
        with patch("src.trading.executor.settings") as mock_settings:
            mock_settings.trading_mode = "PAPER"
            mock_settings.risk.min_bet = 5.0
            mock_settings.risk.max_single_ratio = 0.2

            # Setup paper executor to return failure
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
                notifier=mock_notifier,
            )

            await executor.process_market(sample_market)

            # Verify error notification was sent
            mock_notifier.send_error_notification.assert_called_once()
            call_args = mock_notifier.send_error_notification.call_args
            error_msg = call_args[0][0]
            assert "Trade failed" in error_msg
            assert "Database error" in error_msg

    @pytest.mark.asyncio
    async def test_notify_on_unexpected_exception(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        mock_notifier: AsyncMock,
        sample_market: Market,
    ) -> None:
        """Test notification sent on unexpected exception."""
        with patch("src.trading.executor.settings") as mock_settings:
            mock_settings.trading_mode = "PAPER"
            mock_settings.risk.min_bet = 5.0
            mock_settings.risk.max_single_ratio = 0.2

            # Setup LLM analyzer to raise exception
            mock_llm_analyzer.analyze_market.side_effect = RuntimeError(
                "Network error"
            )

            executor = TradingExecutor(
                llm_analyzer=mock_llm_analyzer,
                risk_controller=mock_risk_controller,
                paper_executor=mock_paper_executor,
                state=mock_state,
                notifier=mock_notifier,
            )

            await executor.process_market(sample_market)

            # Verify error notification was sent
            mock_notifier.send_error_notification.assert_called_once()
            call_args = mock_notifier.send_error_notification.call_args
            error_msg = call_args[0][0]
            assert "Unexpected error" in error_msg

    # ========== No Notification Tests ==========

    @pytest.mark.asyncio
    async def test_no_notification_when_notifier_is_none(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        sample_market: Market,
    ) -> None:
        """Test no notification when notifier is None."""
        with patch("src.trading.executor.settings") as mock_settings:
            mock_settings.trading_mode = "PAPER"
            mock_settings.risk.min_bet = 5.0
            mock_settings.risk.max_single_ratio = 0.2

            executor = TradingExecutor(
                llm_analyzer=mock_llm_analyzer,
                risk_controller=mock_risk_controller,
                paper_executor=mock_paper_executor,
                state=mock_state,
                notifier=None,
            )

            # Should not raise exception
            decision = await executor.process_market(sample_market)

            assert decision.success is True
            assert decision.trade is not None

    @pytest.mark.asyncio
    async def test_no_notification_on_risk_rejection(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        mock_notifier: AsyncMock,
        sample_market: Market,
    ) -> None:
        """Test no notification when trade is rejected by risk check."""
        with patch("src.trading.executor.settings") as mock_settings:
            mock_settings.trading_mode = "PAPER"

            # Setup risk controller to reject
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
                notifier=mock_notifier,
            )

            decision = await executor.process_market(sample_market)

            assert decision.skipped is True
            # No notification should be sent for risk rejection
            mock_notifier.send_trade_notification.assert_not_called()
            mock_notifier.send_error_notification.assert_not_called()

    # ========== Notification Failure Does Not Affect Main Flow Tests ==========

    @pytest.mark.asyncio
    async def test_notification_failure_does_not_affect_trade(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        mock_notifier: AsyncMock,
        sample_market: Market,
        sample_trade: Trade,
    ) -> None:
        """Test that notification failure doesn't affect trade result."""
        with patch("src.trading.executor.settings") as mock_settings:
            mock_settings.trading_mode = "PAPER"
            mock_settings.risk.min_bet = 5.0
            mock_settings.risk.max_single_ratio = 0.2

            # Make notification fail
            mock_notifier.send_trade_notification = AsyncMock(
                side_effect=Exception("Network error")
            )

            executor = TradingExecutor(
                llm_analyzer=mock_llm_analyzer,
                risk_controller=mock_risk_controller,
                paper_executor=mock_paper_executor,
                state=mock_state,
                notifier=mock_notifier,
            )

            # Should not raise exception
            result = await executor.process_market(sample_market)

            # Trade should still be successful
            assert result.success is True
            assert result.trade == sample_trade

    @pytest.mark.asyncio
    async def test_error_notification_failure_does_not_affect_trade(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        mock_notifier: AsyncMock,
        sample_market: Market,
    ) -> None:
        """Test that error notification failure doesn't affect trade result."""
        with patch("src.trading.executor.settings") as mock_settings:
            mock_settings.trading_mode = "PAPER"
            mock_settings.risk.min_bet = 5.0
            mock_settings.risk.max_single_ratio = 0.2

            # Setup paper executor to return failure
            mock_paper_executor.execute_trade.return_value = PaperTradeResult(
                trade=None,
                position=None,
                success=False,
                error_message="Database error",
            )

            # Make notification fail
            mock_notifier.send_error_notification = AsyncMock(
                side_effect=Exception("Network error")
            )

            executor = TradingExecutor(
                llm_analyzer=mock_llm_analyzer,
                risk_controller=mock_risk_controller,
                paper_executor=mock_paper_executor,
                state=mock_state,
                notifier=mock_notifier,
            )

            # Should not raise exception
            result = await executor.process_market(sample_market)

            # Trade should still be marked as failed
            assert result.success is False
            assert "Database error" in result.error_message

    # ========== Helper Method Tests ==========

    @pytest.mark.asyncio
    async def test_notify_trade_success_returns_early_when_notifier_is_none(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        sample_trade: Trade,
        sample_market: Market,
    ) -> None:
        """Test _notify_trade_success returns early when notifier is None."""
        with patch("src.trading.executor.settings") as mock_settings:
            mock_settings.trading_mode = "PAPER"

            executor = TradingExecutor(
                llm_analyzer=mock_llm_analyzer,
                risk_controller=mock_risk_controller,
                paper_executor=mock_paper_executor,
                state=mock_state,
                notifier=None,
            )

            # Should not raise exception
            await executor._notify_trade_success(sample_trade, sample_market)

    @pytest.mark.asyncio
    async def test_notify_trade_failed_returns_early_when_notifier_is_none(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        sample_market: Market,
    ) -> None:
        """Test _notify_trade_failed returns early when notifier is None."""
        with patch("src.trading.executor.settings") as mock_settings:
            mock_settings.trading_mode = "PAPER"

            executor = TradingExecutor(
                llm_analyzer=mock_llm_analyzer,
                risk_controller=mock_risk_controller,
                paper_executor=mock_paper_executor,
                state=mock_state,
                notifier=None,
            )

            # Should not raise exception
            await executor._notify_trade_failed(sample_market, "Test error")
