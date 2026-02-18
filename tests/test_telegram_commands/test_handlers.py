"""Tests for Telegram command handlers.

Story 9.5: Telegram 命令处理 - 状态查询
Story 9.6: Telegram 命令处理 - 持仓查询
Story 9.7: Telegram 命令处理 - 统计查询
Story 9.8: Telegram 命令处理 - 市场查询
Story 9.9: Telegram 命令处理 - 交易历史
Story 9.10: Telegram 命令处理 - 手动触发分析
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.market import Market, MarketCategory
from src.models.position import Position, PositionOutcome, PositionStatus
from src.models.statistics import Statistics
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.telegram_commands.formatters import (
    _format_relative_time,
    format_help_message,
    format_history_message,
    format_markets_message,
    format_positions_message,
    format_stats_message,
    format_status_message,
    format_unauthorized_message,
)
from src.telegram_commands.handlers import (
    create_cancel_handler,
    create_confirm_handler,
    create_help_handler,
    create_history_handler,
    create_markets_handler,
    create_positions_handler,
    create_predict_handler,
    create_stats_handler,
    create_status_handler,
    setup_command_handlers,
)


class TestFormatters:
    """Tests for message formatters."""

    def test_format_status_message_profit(self) -> None:
        """Test status message formatting with profit."""
        message = format_status_message(
            mode="PAPER",
            current_capital=200.0,
            daily_pnl=10.0,
            open_positions=2,
            consecutive_losses=0,
            trading_enabled=True,
        )

        assert "*系统状态*" in message
        assert "PAPER" in message
        assert "$200.00" in message
        assert "+$10.00" in message
        assert "+5.0%" in message
        assert "2 个" in message
        assert "启用" in message

    def test_format_status_message_loss(self) -> None:
        """Test status message formatting with loss."""
        message = format_status_message(
            mode="LIVE",
            current_capital=100.0,
            daily_pnl=-5.0,
            open_positions=1,
            consecutive_losses=3,
            trading_enabled=False,
        )

        assert "*系统状态*" in message
        assert "LIVE" in message
        assert "$-5.00" in message  # Note: format is $-X.XX for negative values
        assert "-5.0%" in message
        assert "禁用" in message

    def test_format_status_message_zero_capital(self) -> None:
        """Test status message with zero capital (edge case)."""
        message = format_status_message(
            mode="PAPER",
            current_capital=0.0,
            daily_pnl=0.0,
            open_positions=0,
            consecutive_losses=0,
            trading_enabled=True,
        )

        assert "*系统状态*" in message
        assert "0.0%" in message  # Should not divide by zero

    def test_format_help_message(self) -> None:
        """Test help message formatting."""
        message = format_help_message()

        assert "*可用命令*" in message
        assert "/status" in message
        assert "/help" in message

    def test_format_unauthorized_message(self) -> None:
        """Test unauthorized message formatting."""
        message = format_unauthorized_message()

        assert "*未授权访问*" in message


class TestStatusHandler:
    """Tests for status command handler."""

    @pytest.fixture
    def mock_state_manager(self) -> MagicMock:
        """Create a mock state manager."""
        manager = MagicMock()
        snapshot = MagicMock()
        snapshot.current_capital = 200.0
        snapshot.daily_pnl = 10.0
        snapshot.open_positions_count = 2
        snapshot.consecutive_losses = 0
        snapshot.trading_enabled = True
        manager.get_state = AsyncMock(return_value=snapshot)
        return manager

    @pytest.fixture
    def mock_update(self) -> MagicMock:
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456789
        update.message = AsyncMock()
        return update

    @pytest.mark.asyncio
    async def test_status_handler_authorized(
        self,
        mock_state_manager: MagicMock,
        mock_update: MagicMock,
    ) -> None:
        """Test status handler with authorized user."""
        with patch("src.telegram_commands.handlers.settings") as mock_settings:
            mock_settings.trading_mode = "paper"

            handler = create_status_handler(mock_state_manager, "123456789")
            await handler(mock_update, MagicMock())

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "*系统状态*" in call_args.args[0]
            assert call_args.kwargs.get("parse_mode") == "Markdown"

    @pytest.mark.asyncio
    async def test_status_handler_unauthorized(
        self,
        mock_state_manager: MagicMock,
        mock_update: MagicMock,
    ) -> None:
        """Test status handler with unauthorized user."""
        handler = create_status_handler(mock_state_manager, "999888777")
        await handler(mock_update, MagicMock())

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "*未授权访问*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_status_handler_no_restriction(
        self,
        mock_state_manager: MagicMock,
        mock_update: MagicMock,
    ) -> None:
        """Test status handler with no chat ID restriction."""
        with patch("src.telegram_commands.handlers.settings") as mock_settings:
            mock_settings.trading_mode = "paper"

            # None means no restriction
            handler = create_status_handler(mock_state_manager, None)
            await handler(mock_update, MagicMock())

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "*系统状态*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_status_handler_live_mode(
        self,
        mock_state_manager: MagicMock,
        mock_update: MagicMock,
    ) -> None:
        """Test status handler in LIVE mode."""
        with patch("src.telegram_commands.handlers.settings") as mock_settings:
            mock_settings.trading_mode = "live"

            handler = create_status_handler(mock_state_manager, "123456789")
            await handler(mock_update, MagicMock())

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "LIVE" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_status_handler_no_effective_chat(
        self,
        mock_state_manager: MagicMock,
    ) -> None:
        """Test status handler when update has no effective_chat."""
        mock_update = MagicMock()
        mock_update.effective_chat = None
        mock_update.message = AsyncMock()

        handler = create_status_handler(mock_state_manager, "123456789")
        await handler(mock_update, MagicMock())

        # Should not call reply_text
        mock_update.message.reply_text.assert_not_called()


class TestHelpHandler:
    """Tests for help command handler."""

    @pytest.fixture
    def mock_update(self) -> MagicMock:
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456789
        update.message = AsyncMock()
        return update

    @pytest.mark.asyncio
    async def test_help_handler_authorized(self, mock_update: MagicMock) -> None:
        """Test help handler with authorized user."""
        handler = create_help_handler("123456789")
        await handler(mock_update, MagicMock())

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "*可用命令*" in call_args.args[0]
        assert call_args.kwargs.get("parse_mode") == "Markdown"

    @pytest.mark.asyncio
    async def test_help_handler_unauthorized(self, mock_update: MagicMock) -> None:
        """Test help handler with unauthorized user."""
        handler = create_help_handler("999888777")
        await handler(mock_update, MagicMock())

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "*未授权访问*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_help_handler_no_restriction(self, mock_update: MagicMock) -> None:
        """Test help handler with no chat ID restriction."""
        handler = create_help_handler(None)
        await handler(mock_update, MagicMock())

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "*可用命令*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_help_handler_no_effective_chat(self) -> None:
        """Test help handler when update has no effective_chat."""
        mock_update = MagicMock()
        mock_update.effective_chat = None
        mock_update.message = AsyncMock()

        handler = create_help_handler("123456789")
        await handler(mock_update, MagicMock())

        # Should not call reply_text
        mock_update.message.reply_text.assert_not_called()


class TestSetupCommandHandlers:
    """Tests for setup_command_handlers function."""

    def test_setup_registers_handlers(self) -> None:
        """Test that handlers are registered."""
        mock_app = MagicMock()
        mock_state = MagicMock()

        setup_command_handlers(mock_app, mock_state, "123456789")

        # Should add nine handlers: status, help, positions, stats, markets, history,
        # predict, confirm, cancel
        assert mock_app.add_handler.call_count == 9

    def test_setup_registers_handlers_no_auth(self) -> None:
        """Test that handlers are registered without auth."""
        mock_app = MagicMock()
        mock_state = MagicMock()

        setup_command_handlers(mock_app, mock_state, None)

        # Should add nine handlers: status, help, positions, stats, markets, history,
        # predict, confirm, cancel
        assert mock_app.add_handler.call_count == 9


class TestPositionsFormatter:
    """Tests for positions message formatter."""

    def test_format_positions_message_empty(self) -> None:
        """Test positions message with no positions."""
        message = format_positions_message([], 0.0, 0.0)

        assert "*当前持仓*" in message
        assert "暂无持仓" in message

    def test_format_positions_message_with_data(self) -> None:
        """Test positions message with positions."""
        position_data = [
            {
                "market_title": "Will Trump win 2028?",
                "outcome": "YES",
                "shares": 15.38,
                "cost": 10.0,
                "current_value": 12.5,
                "pnl": 2.5,
            }
        ]
        message = format_positions_message(position_data, 10.0, 2.5)

        assert "*当前持仓*" in message
        assert "Will Trump win 2028?" in message
        assert "YES" in message
        assert "15.38" in message
        assert "$10.00" in message
        assert "$12.50" in message
        assert "+$2.50" in message
        assert "*总风险敞口: $10.00*" in message
        assert "*总盈亏: +$2.50*" in message

    def test_format_positions_message_with_loss(self) -> None:
        """Test positions message with losing position."""
        position_data = [
            {
                "market_title": "BTC > $100k by 2025?",
                "outcome": "NO",
                "shares": 20.0,
                "cost": 8.0,
                "current_value": 7.2,
                "pnl": -0.8,
            }
        ]
        message = format_positions_message(position_data, 8.0, -0.8)

        assert "*当前持仓*" in message
        assert "BTC > $100k by 2025?" in message
        assert "NO" in message
        assert "$-0.80" in message
        assert "*总盈亏: $-0.80*" in message

    def test_format_positions_message_multiple(self) -> None:
        """Test positions message with multiple positions."""
        position_data = [
            {
                "market_title": "Market 1",
                "outcome": "YES",
                "shares": 10.0,
                "cost": 10.0,
                "current_value": 12.0,
                "pnl": 2.0,
            },
            {
                "market_title": "Market 2",
                "outcome": "NO",
                "shares": 20.0,
                "cost": 8.0,
                "current_value": 7.2,
                "pnl": -0.8,
            },
        ]
        message = format_positions_message(position_data, 18.0, 1.2)

        assert "*当前持仓*" in message
        assert "Market 1" in message
        assert "Market 2" in message
        assert "*总风险敞口: $18.00*" in message
        assert "*总盈亏: +$1.20*" in message

    def test_format_positions_message_zero_cost(self) -> None:
        """Test positions message with zero cost (edge case)."""
        position_data = [
            {
                "market_title": "Test Market",
                "outcome": "YES",
                "shares": 100.0,
                "cost": 0.0,
                "current_value": 0.0,
                "pnl": 0.0,
            }
        ]
        message = format_positions_message(position_data, 0.0, 0.0)

        assert "*当前持仓*" in message
        assert "Test Market" in message
        # Should not crash with division by zero
        # pnl_pct is 0.0 when cost is 0, formatted as 0%
        assert "+0%" in message


class TestPositionsHandler:
    """Tests for positions command handler."""

    @pytest.fixture
    def mock_update(self) -> MagicMock:
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456789
        update.message = AsyncMock()
        return update

    @pytest.mark.asyncio
    async def test_positions_handler_with_positions(
        self, mock_update: MagicMock
    ) -> None:
        """Test positions handler with open positions."""
        with (
            patch(
                "src.telegram_commands.handlers.PositionRepository"
            ) as MockPositionRepo,
            patch(
                "src.telegram_commands.handlers.MarketRepository"
            ) as MockMarketRepo,
        ):
            # Setup mocks
            mock_position_repo = MagicMock()
            mock_position_repo.get_open_positions = AsyncMock(
                return_value=[
                    Position(
                        id=1,
                        market_id="market-1",
                        outcome=PositionOutcome.YES,
                        shares=15.38,
                        avg_price=0.65,
                        initial_value=10.0,
                        current_value=12.5,
                        pnl=2.5,
                        status=PositionStatus.OPEN,
                    )
                ]
            )
            MockPositionRepo.return_value = mock_position_repo

            mock_market_repo = MagicMock()
            mock_market_repo.get_market = AsyncMock(
                return_value=Market(
                    id="market-1",
                    title="Will Trump win 2028?",
                )
            )
            MockMarketRepo.return_value = mock_market_repo

            handler = create_positions_handler("123456789")
            await handler(mock_update, MagicMock())

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "*当前持仓*" in call_args.args[0]
            assert "Will Trump win 2028?" in call_args.args[0]
            assert call_args.kwargs.get("parse_mode") == "Markdown"

    @pytest.mark.asyncio
    async def test_positions_handler_empty(self, mock_update: MagicMock) -> None:
        """Test positions handler with no positions."""
        with patch(
            "src.telegram_commands.handlers.PositionRepository"
        ) as MockPositionRepo:
            mock_position_repo = MagicMock()
            mock_position_repo.get_open_positions = AsyncMock(return_value=[])
            MockPositionRepo.return_value = mock_position_repo

            handler = create_positions_handler("123456789")
            await handler(mock_update, MagicMock())

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "暂无持仓" in call_args.args[0]
            assert call_args.kwargs.get("parse_mode") == "Markdown"

    @pytest.mark.asyncio
    async def test_positions_handler_unauthorized(self, mock_update: MagicMock) -> None:
        """Test positions handler with unauthorized user."""
        handler = create_positions_handler("999888777")
        await handler(mock_update, MagicMock())

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "*未授权访问*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_positions_handler_no_restriction(
        self, mock_update: MagicMock
    ) -> None:
        """Test positions handler with no chat ID restriction."""
        with patch(
            "src.telegram_commands.handlers.PositionRepository"
        ) as MockPositionRepo:
            mock_position_repo = MagicMock()
            mock_position_repo.get_open_positions = AsyncMock(return_value=[])
            MockPositionRepo.return_value = mock_position_repo

            # None means no restriction
            handler = create_positions_handler(None)
            await handler(mock_update, MagicMock())

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "*当前持仓*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_positions_handler_no_effective_chat(self) -> None:
        """Test positions handler when update has no effective_chat."""
        mock_update = MagicMock()
        mock_update.effective_chat = None
        mock_update.message = AsyncMock()

        handler = create_positions_handler("123456789")
        await handler(mock_update, MagicMock())

        # Should not call reply_text
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_positions_handler_market_not_found(
        self, mock_update: MagicMock
    ) -> None:
        """Test positions handler when market is not found."""
        with (
            patch(
                "src.telegram_commands.handlers.PositionRepository"
            ) as MockPositionRepo,
            patch(
                "src.telegram_commands.handlers.MarketRepository"
            ) as MockMarketRepo,
        ):
            # Setup mocks
            mock_position_repo = MagicMock()
            mock_position_repo.get_open_positions = AsyncMock(
                return_value=[
                    Position(
                        id=1,
                        market_id="unknown-market",
                        outcome=PositionOutcome.YES,
                        shares=10.0,
                        avg_price=0.5,
                        initial_value=5.0,
                        current_value=6.0,
                        pnl=1.0,
                        status=PositionStatus.OPEN,
                    )
                ]
            )
            MockPositionRepo.return_value = mock_position_repo

            mock_market_repo = MagicMock()
            mock_market_repo.get_market = AsyncMock(return_value=None)
            MockMarketRepo.return_value = mock_market_repo

            handler = create_positions_handler("123456789")
            await handler(mock_update, MagicMock())

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            # Should display market_id as fallback when market not found
            assert "unknown-market" in call_args.args[0]


class TestStatsFormatter:
    """Tests for stats message formatter."""

    def test_format_stats_message_with_data(self) -> None:
        """Test stats message with data."""
        message = format_stats_message(
            total_trades=25,
            total_winning=15,
            total_losing=10,
            win_rate=60.0,
            total_pnl=45.20,
            recent_trades=8,
            recent_win_rate=75.0,
            recent_pnl=18.50,
            days=7,
            total_predictions=30,
            validated_count=20,
            accuracy=70.0,
        )

        assert "*交易统计*" in message
        assert "总交易: 25" in message
        assert "胜: 15 | 负: 10" in message
        assert "胜率: 60%" in message
        assert "+$45.20" in message
        assert "*近期表现 (7天)*" in message
        assert "交易: 8" in message
        assert "胜率: 75%" in message
        assert "+$18.50" in message
        assert "*LLM 预测*" in message
        assert "总预测: 30" in message
        assert "已验证: 20" in message
        assert "准确率: 70%" in message

    def test_format_stats_message_no_data(self) -> None:
        """Test stats message with no data."""
        message = format_stats_message(
            total_trades=0,
            total_winning=0,
            total_losing=0,
            win_rate=0.0,
            total_pnl=0.0,
            recent_trades=0,
            recent_win_rate=0.0,
            recent_pnl=0.0,
            days=7,
            total_predictions=0,
            validated_count=0,
            accuracy=0.0,
        )

        assert "*交易统计*" in message
        assert "总交易: 0" in message
        assert "胜率: 0%" in message

    def test_format_stats_message_negative_pnl(self) -> None:
        """Test stats message with negative PnL."""
        message = format_stats_message(
            total_trades=10,
            total_winning=3,
            total_losing=7,
            win_rate=30.0,
            total_pnl=-25.50,
            recent_trades=5,
            recent_win_rate=20.0,
            recent_pnl=-15.00,
            days=7,
            total_predictions=10,
            validated_count=5,
            accuracy=40.0,
        )

        # Negative values show as $-X.XX (sign is only + for positive)
        assert "$-25.50" in message
        assert "$-15.00" in message

    def test_format_stats_message_custom_days(self) -> None:
        """Test stats message with custom days."""
        message = format_stats_message(
            total_trades=25,
            total_winning=15,
            total_losing=10,
            win_rate=60.0,
            total_pnl=45.20,
            recent_trades=15,
            recent_win_rate=65.0,
            recent_pnl=30.00,
            days=30,
            total_predictions=30,
            validated_count=20,
            accuracy=70.0,
        )

        assert "*近期表现 (30天)*" in message


class TestStatsHandler:
    """Tests for stats command handler."""

    @pytest.fixture
    def mock_update(self) -> MagicMock:
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456789
        update.message = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock callback context."""
        context = MagicMock()
        context.args = []
        return context

    @pytest.mark.asyncio
    async def test_stats_handler_default_days(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test stats handler with default 7 days."""
        with (
            patch(
                "src.telegram_commands.handlers.StatisticsRepository"
            ) as MockStatsRepo,
            patch(
                "src.telegram_commands.handlers.PredictionRepository"
            ) as MockPredictionRepo,
            patch("src.telegram_commands.handlers.settings") as mock_settings,
        ):
            mock_settings.trading_mode = "paper"

            # Setup mock statistics repo
            mock_stats_repo = MagicMock()
            mock_stats_repo.get_latest = AsyncMock(
                return_value=[
                    Statistics(
                        id=1,
                        date=date.today(),
                        mode=TradeMode.PAPER,
                        starting_capital=200.0,
                        ending_capital=210.0,
                        total_pnl=10.0,
                        total_trades=5,
                        winning_trades=3,
                        losing_trades=2,
                        win_rate=0.6,
                    )
                ]
            )
            mock_stats_repo.get_by_date_range = AsyncMock(
                return_value=[
                    Statistics(
                        id=1,
                        date=date.today(),
                        mode=TradeMode.PAPER,
                        starting_capital=200.0,
                        ending_capital=205.0,
                        total_pnl=5.0,
                        total_trades=2,
                        winning_trades=2,
                        losing_trades=0,
                        win_rate=1.0,
                    )
                ]
            )
            MockStatsRepo.return_value = mock_stats_repo

            # Setup mock prediction repo
            mock_pred_repo = MagicMock()
            mock_pred_repo.count = AsyncMock(return_value=10)
            mock_pred_repo.get_all_validated = AsyncMock(return_value=[])
            MockPredictionRepo.return_value = mock_pred_repo

            handler = create_stats_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "*交易统计*" in call_args.args[0]
            assert call_args.kwargs.get("parse_mode") == "Markdown"

    @pytest.mark.asyncio
    async def test_stats_handler_custom_days(self, mock_update: MagicMock) -> None:
        """Test stats handler with custom days parameter."""
        mock_context = MagicMock()
        mock_context.args = ["30"]

        with (
            patch(
                "src.telegram_commands.handlers.StatisticsRepository"
            ) as MockStatsRepo,
            patch(
                "src.telegram_commands.handlers.PredictionRepository"
            ) as MockPredictionRepo,
            patch("src.telegram_commands.handlers.settings") as mock_settings,
        ):
            mock_settings.trading_mode = "paper"

            mock_stats_repo = MagicMock()
            mock_stats_repo.get_latest = AsyncMock(return_value=[])
            mock_stats_repo.get_by_date_range = AsyncMock(return_value=[])
            MockStatsRepo.return_value = mock_stats_repo

            mock_pred_repo = MagicMock()
            mock_pred_repo.count = AsyncMock(return_value=0)
            mock_pred_repo.get_all_validated = AsyncMock(return_value=[])
            MockPredictionRepo.return_value = mock_pred_repo

            handler = create_stats_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            # Verify the message contains 30 days
            call_args = mock_update.message.reply_text.call_args
            assert "(30天)" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_stats_handler_unauthorized(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test stats handler with unauthorized user."""
        handler = create_stats_handler("999888777")
        await handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "*未授权访问*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_stats_handler_no_restriction(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test stats handler with no chat ID restriction."""
        with (
            patch(
                "src.telegram_commands.handlers.StatisticsRepository"
            ) as MockStatsRepo,
            patch(
                "src.telegram_commands.handlers.PredictionRepository"
            ) as MockPredictionRepo,
            patch("src.telegram_commands.handlers.settings") as mock_settings,
        ):
            mock_settings.trading_mode = "paper"

            mock_stats_repo = MagicMock()
            mock_stats_repo.get_latest = AsyncMock(return_value=[])
            mock_stats_repo.get_by_date_range = AsyncMock(return_value=[])
            MockStatsRepo.return_value = mock_stats_repo

            mock_pred_repo = MagicMock()
            mock_pred_repo.count = AsyncMock(return_value=0)
            mock_pred_repo.get_all_validated = AsyncMock(return_value=[])
            MockPredictionRepo.return_value = mock_pred_repo

            # None means no restriction
            handler = create_stats_handler(None)
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "*交易统计*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_stats_handler_no_effective_chat(self) -> None:
        """Test stats handler when update has no effective_chat."""
        mock_update = MagicMock()
        mock_update.effective_chat = None
        mock_update.message = AsyncMock()

        handler = create_stats_handler("123456789")
        await handler(mock_update, MagicMock())

        # Should not call reply_text
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_stats_handler_invalid_days_uses_default(
        self, mock_update: MagicMock
    ) -> None:
        """Test stats handler with invalid days parameter uses default."""
        mock_context = MagicMock()
        mock_context.args = ["invalid"]

        with (
            patch(
                "src.telegram_commands.handlers.StatisticsRepository"
            ) as MockStatsRepo,
            patch(
                "src.telegram_commands.handlers.PredictionRepository"
            ) as MockPredictionRepo,
            patch("src.telegram_commands.handlers.settings") as mock_settings,
        ):
            mock_settings.trading_mode = "paper"

            mock_stats_repo = MagicMock()
            mock_stats_repo.get_latest = AsyncMock(return_value=[])
            mock_stats_repo.get_by_date_range = AsyncMock(return_value=[])
            MockStatsRepo.return_value = mock_stats_repo

            mock_pred_repo = MagicMock()
            mock_pred_repo.count = AsyncMock(return_value=0)
            mock_pred_repo.get_all_validated = AsyncMock(return_value=[])
            MockPredictionRepo.return_value = mock_pred_repo

            handler = create_stats_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            # Should use default 7 days
            call_args = mock_update.message.reply_text.call_args
            assert "(7天)" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_stats_handler_days_out_of_range_clamped(
        self, mock_update: MagicMock
    ) -> None:
        """Test stats handler clamps days to valid range."""
        mock_context = MagicMock()
        mock_context.args = ["500"]  # Over 365

        with (
            patch(
                "src.telegram_commands.handlers.StatisticsRepository"
            ) as MockStatsRepo,
            patch(
                "src.telegram_commands.handlers.PredictionRepository"
            ) as MockPredictionRepo,
            patch("src.telegram_commands.handlers.settings") as mock_settings,
        ):
            mock_settings.trading_mode = "paper"

            mock_stats_repo = MagicMock()
            mock_stats_repo.get_latest = AsyncMock(return_value=[])
            mock_stats_repo.get_by_date_range = AsyncMock(return_value=[])
            MockStatsRepo.return_value = mock_stats_repo

            mock_pred_repo = MagicMock()
            mock_pred_repo.count = AsyncMock(return_value=0)
            mock_pred_repo.get_all_validated = AsyncMock(return_value=[])
            MockPredictionRepo.return_value = mock_pred_repo

            handler = create_stats_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            # Should be clamped to 365 days
            call_args = mock_update.message.reply_text.call_args
            assert "(365天)" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_stats_handler_live_mode(self, mock_update: MagicMock) -> None:
        """Test stats handler in LIVE mode."""
        mock_context = MagicMock()
        mock_context.args = []

        with (
            patch(
                "src.telegram_commands.handlers.StatisticsRepository"
            ) as MockStatsRepo,
            patch(
                "src.telegram_commands.handlers.PredictionRepository"
            ) as MockPredictionRepo,
            patch("src.telegram_commands.handlers.settings") as mock_settings,
        ):
            mock_settings.trading_mode = "live"

            mock_stats_repo = MagicMock()
            mock_stats_repo.get_latest = AsyncMock(
                return_value=[
                    Statistics(
                        id=1,
                        date=date.today(),
                        mode=TradeMode.LIVE,
                        starting_capital=1000.0,
                        ending_capital=1050.0,
                        total_pnl=50.0,
                        total_trades=10,
                        winning_trades=6,
                        losing_trades=4,
                        win_rate=0.6,
                    )
                ]
            )
            mock_stats_repo.get_by_date_range = AsyncMock(return_value=[])
            MockStatsRepo.return_value = mock_stats_repo

            mock_pred_repo = MagicMock()
            mock_pred_repo.count = AsyncMock(return_value=0)
            mock_pred_repo.get_all_validated = AsyncMock(return_value=[])
            MockPredictionRepo.return_value = mock_pred_repo

            handler = create_stats_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            # Verify LIVE mode was used
            mock_stats_repo.get_latest.assert_called_once_with(
                TradeMode.LIVE, limit=365
            )

    @pytest.mark.asyncio
    async def test_stats_handler_with_predictions(
        self, mock_update: MagicMock
    ) -> None:
        """Test stats handler with validated predictions."""
        mock_context = MagicMock()
        mock_context.args = []

        # Create mock predictions
        mock_pred_1 = MagicMock()
        mock_pred_1.is_correct = True
        mock_pred_2 = MagicMock()
        mock_pred_2.is_correct = True
        mock_pred_3 = MagicMock()
        mock_pred_3.is_correct = False

        with (
            patch(
                "src.telegram_commands.handlers.StatisticsRepository"
            ) as MockStatsRepo,
            patch(
                "src.telegram_commands.handlers.PredictionRepository"
            ) as MockPredictionRepo,
            patch("src.telegram_commands.handlers.settings") as mock_settings,
        ):
            mock_settings.trading_mode = "paper"

            mock_stats_repo = MagicMock()
            mock_stats_repo.get_latest = AsyncMock(return_value=[])
            mock_stats_repo.get_by_date_range = AsyncMock(return_value=[])
            MockStatsRepo.return_value = mock_stats_repo

            mock_pred_repo = MagicMock()
            mock_pred_repo.count = AsyncMock(return_value=10)
            mock_pred_repo.get_all_validated = AsyncMock(
                return_value=[mock_pred_1, mock_pred_2, mock_pred_3]
            )
            MockPredictionRepo.return_value = mock_pred_repo

            handler = create_stats_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            # 2 correct out of 3 = 67%
            assert "准确率: 67%" in call_args.args[0]
            assert "已验证: 3" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_stats_handler_days_below_minimum_clamped(
        self, mock_update: MagicMock
    ) -> None:
        """Test stats handler clamps days to minimum of 1."""
        mock_context = MagicMock()
        mock_context.args = ["0"]  # Below 1

        with (
            patch(
                "src.telegram_commands.handlers.StatisticsRepository"
            ) as MockStatsRepo,
            patch(
                "src.telegram_commands.handlers.PredictionRepository"
            ) as MockPredictionRepo,
            patch("src.telegram_commands.handlers.settings") as mock_settings,
        ):
            mock_settings.trading_mode = "paper"

            mock_stats_repo = MagicMock()
            mock_stats_repo.get_latest = AsyncMock(return_value=[])
            mock_stats_repo.get_by_date_range = AsyncMock(return_value=[])
            MockStatsRepo.return_value = mock_stats_repo

            mock_pred_repo = MagicMock()
            mock_pred_repo.count = AsyncMock(return_value=0)
            mock_pred_repo.get_all_validated = AsyncMock(return_value=[])
            MockPredictionRepo.return_value = mock_pred_repo

            handler = create_stats_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            # Should be clamped to 1 day
            call_args = mock_update.message.reply_text.call_args
            assert "(1天)" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_stats_handler_negative_days_clamped(
        self, mock_update: MagicMock
    ) -> None:
        """Test stats handler clamps negative days to minimum of 1."""
        mock_context = MagicMock()
        mock_context.args = ["-5"]

        with (
            patch(
                "src.telegram_commands.handlers.StatisticsRepository"
            ) as MockStatsRepo,
            patch(
                "src.telegram_commands.handlers.PredictionRepository"
            ) as MockPredictionRepo,
            patch("src.telegram_commands.handlers.settings") as mock_settings,
        ):
            mock_settings.trading_mode = "paper"

            mock_stats_repo = MagicMock()
            mock_stats_repo.get_latest = AsyncMock(return_value=[])
            mock_stats_repo.get_by_date_range = AsyncMock(return_value=[])
            MockStatsRepo.return_value = mock_stats_repo

            mock_pred_repo = MagicMock()
            mock_pred_repo.count = AsyncMock(return_value=0)
            mock_pred_repo.get_all_validated = AsyncMock(return_value=[])
            MockPredictionRepo.return_value = mock_pred_repo

            handler = create_stats_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            # Should be clamped to 1 day
            call_args = mock_update.message.reply_text.call_args
            assert "(1天)" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_stats_handler_aggregates_multiple_stats(
        self, mock_update: MagicMock
    ) -> None:
        """Test stats handler correctly aggregates multiple statistics records."""
        mock_context = MagicMock()
        mock_context.args = []

        with (
            patch(
                "src.telegram_commands.handlers.StatisticsRepository"
            ) as MockStatsRepo,
            patch(
                "src.telegram_commands.handlers.PredictionRepository"
            ) as MockPredictionRepo,
            patch("src.telegram_commands.handlers.settings") as mock_settings,
        ):
            mock_settings.trading_mode = "paper"

            mock_stats_repo = MagicMock()
            # Return multiple statistics records
            mock_stats_repo.get_latest = AsyncMock(
                return_value=[
                    Statistics(
                        id=1,
                        date=date.today(),
                        mode=TradeMode.PAPER,
                        starting_capital=200.0,
                        ending_capital=210.0,
                        total_pnl=10.0,
                        total_trades=5,
                        winning_trades=3,
                        losing_trades=2,
                        win_rate=0.6,
                    ),
                    Statistics(
                        id=2,
                        date=date.today(),
                        mode=TradeMode.PAPER,
                        starting_capital=210.0,
                        ending_capital=225.0,
                        total_pnl=15.0,
                        total_trades=3,
                        winning_trades=2,
                        losing_trades=1,
                        win_rate=0.67,
                    ),
                ]
            )
            mock_stats_repo.get_by_date_range = AsyncMock(return_value=[])
            MockStatsRepo.return_value = mock_stats_repo

            mock_pred_repo = MagicMock()
            mock_pred_repo.count = AsyncMock(return_value=0)
            mock_pred_repo.get_all_validated = AsyncMock(return_value=[])
            MockPredictionRepo.return_value = mock_pred_repo

            handler = create_stats_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            # 5+3=8 trades, 3+2=5 winning, 2+1=3 losing
            assert "总交易: 8" in call_args.args[0]
            assert "胜: 5 | 负: 3" in call_args.args[0]
            # 10+15=25 total pnl
            assert "+$25.00" in call_args.args[0]


class TestMarketsFormatter:
    """Tests for markets message formatter.

    Story 9.8: Telegram 命令处理 - 市场查询
    """

    def test_format_markets_message_with_data(self) -> None:
        """Test markets message with data."""
        markets = [
            Market(
                id="market-1",
                title="Will Trump win 2028?",
                category=MarketCategory.POLITICS,
                yes_price=0.65,
                no_price=0.35,
                liquidity=50000.0,
                deadline=datetime(2028, 11, 7),
            ),
            Market(
                id="market-2",
                title="BTC > $100k by 2025?",
                category=MarketCategory.CRYPTO,
                yes_price=0.45,
                no_price=0.55,
                liquidity=120000.0,
                deadline=datetime(2025, 12, 31),
            ),
        ]
        message = format_markets_message(markets)

        assert "*活跃市场*" in message
        assert "(2 个)" in message
        assert "Will Trump win 2028?" in message
        assert "YES 0.65" in message
        assert "$50k" in message
        assert "2028-11-07" in message
        assert "BTC > $100k by 2025?" in message

    def test_format_markets_message_no_markets(self) -> None:
        """Test markets message with no markets."""
        message = format_markets_message([])

        assert "*活跃市场*" in message
        assert "暂无活跃市场" in message

    def test_format_markets_message_with_category(self) -> None:
        """Test markets message with category filter."""
        message = format_markets_message([], category=MarketCategory.CRYPTO)

        assert "*活跃市场* (crypto)" in message

    def test_format_markets_message_truncates_long_title(self) -> None:
        """Test that long titles are truncated."""
        long_title = "A" * 100
        markets = [
            Market(
                id="market-1",
                title=long_title,
                yes_price=0.5,
                liquidity=1000.0,
            )
        ]
        message = format_markets_message(markets)

        # Should truncate to 50 chars + "..."
        assert "..." in message
        assert len([line for line in message.split("\n") if "AAAA" in line][0]) < 60

    def test_format_markets_message_liquidity_formatting(self) -> None:
        """Test liquidity formatting in K format."""
        markets = [
            Market(
                id="market-1",
                title="Test",
                yes_price=0.5,
                liquidity=1500.0,  # Should show as $2k
            ),
            Market(
                id="market-2",
                title="Test 2",
                yes_price=0.5,
                liquidity=500.0,  # Should show as $500
            ),
        ]
        message = format_markets_message(markets)

        assert "$2k" in message
        assert "$500" in message

    def test_format_markets_message_null_values(self) -> None:
        """Test markets message with null values."""
        markets = [
            Market(
                id="market-1",
                title="Test Market",
                yes_price=None,
                liquidity=None,
                deadline=None,
            )
        ]
        message = format_markets_message(markets)

        assert "*活跃市场*" in message
        assert "Test Market" in message
        assert "N/A" in message


class TestMarketsHandler:
    """Tests for markets command handler.

    Story 9.8: Telegram 命令处理 - 市场查询
    """

    @pytest.fixture
    def mock_update(self) -> MagicMock:
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456789
        update.message = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock callback context."""
        context = MagicMock()
        context.args = []
        return context

    @pytest.mark.asyncio
    async def test_markets_handler_default_limit(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test markets handler with default 5 limit."""
        with patch(
            "src.telegram_commands.handlers.MarketRepository"
        ) as MockMarketRepo:
            # Setup mock market repo
            mock_market_repo = MagicMock()
            mock_market_repo.get_active_markets = AsyncMock(
                return_value=[
                    Market(
                        id=f"market-{i}",
                        title=f"Test Market {i}",
                        category=MarketCategory.POLITICS,
                        yes_price=0.5 + i * 0.05,
                        no_price=0.5 - i * 0.05,
                        liquidity=10000.0 + i * 1000,
                        deadline=datetime(2026, 12, 31),
                    )
                    for i in range(10)
                ]
            )
            MockMarketRepo.return_value = mock_market_repo

            handler = create_markets_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "*活跃市场*" in call_args.args[0]
            assert call_args.kwargs.get("parse_mode") == "Markdown"

    @pytest.mark.asyncio
    async def test_markets_handler_custom_limit(
        self, mock_update: MagicMock
    ) -> None:
        """Test markets handler with custom limit parameter."""
        mock_context = MagicMock()
        mock_context.args = ["10"]

        with patch(
            "src.telegram_commands.handlers.MarketRepository"
        ) as MockMarketRepo:
            mock_market_repo = MagicMock()
            mock_market_repo.get_active_markets = AsyncMock(return_value=[])
            MockMarketRepo.return_value = mock_market_repo

            handler = create_markets_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_markets_handler_category_filter(
        self, mock_update: MagicMock
    ) -> None:
        """Test markets handler with category filter."""
        mock_context = MagicMock()
        mock_context.args = ["politics"]

        with patch(
            "src.telegram_commands.handlers.MarketRepository"
        ) as MockMarketRepo:
            mock_market_repo = MagicMock()
            mock_market_repo.get_markets_by_category = AsyncMock(return_value=[])
            MockMarketRepo.return_value = mock_market_repo

            handler = create_markets_handler("123456789")
            await handler(mock_update, mock_context)

            mock_market_repo.get_markets_by_category.assert_called_once_with(
                MarketCategory.POLITICS
            )

    @pytest.mark.asyncio
    async def test_markets_handler_no_markets(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test markets handler with no active markets."""
        with patch(
            "src.telegram_commands.handlers.MarketRepository"
        ) as MockMarketRepo:
            mock_market_repo = MagicMock()
            mock_market_repo.get_active_markets = AsyncMock(return_value=[])
            MockMarketRepo.return_value = mock_market_repo

            handler = create_markets_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "暂无活跃市场" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_markets_handler_unauthorized(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test markets handler with unauthorized user."""
        handler = create_markets_handler("999888777")
        await handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "*未授权访问*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_markets_handler_no_restriction(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test markets handler with no chat ID restriction."""
        with patch(
            "src.telegram_commands.handlers.MarketRepository"
        ) as MockMarketRepo:
            mock_market_repo = MagicMock()
            mock_market_repo.get_active_markets = AsyncMock(return_value=[])
            MockMarketRepo.return_value = mock_market_repo

            # None means no restriction
            handler = create_markets_handler(None)
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "*活跃市场*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_markets_handler_no_effective_chat(self) -> None:
        """Test markets handler when update has no effective_chat."""
        mock_update = MagicMock()
        mock_update.effective_chat = None
        mock_update.message = AsyncMock()

        handler = create_markets_handler("123456789")
        await handler(mock_update, MagicMock())

        # Should not call reply_text
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_markets_handler_limit_out_of_range_clamped(
        self, mock_update: MagicMock
    ) -> None:
        """Test markets handler clamps limit to valid range."""
        mock_context = MagicMock()
        mock_context.args = ["100"]  # Over 20

        with patch(
            "src.telegram_commands.handlers.MarketRepository"
        ) as MockMarketRepo:
            mock_market_repo = MagicMock()
            mock_market_repo.get_active_markets = AsyncMock(return_value=[])
            MockMarketRepo.return_value = mock_market_repo

            handler = create_markets_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_markets_handler_invalid_limit_uses_default(
        self, mock_update: MagicMock
    ) -> None:
        """Test markets handler with invalid limit parameter uses default."""
        mock_context = MagicMock()
        mock_context.args = ["invalid"]

        with patch(
            "src.telegram_commands.handlers.MarketRepository"
        ) as MockMarketRepo:
            mock_market_repo = MagicMock()
            mock_market_repo.get_active_markets = AsyncMock(return_value=[])
            MockMarketRepo.return_value = mock_market_repo

            handler = create_markets_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_markets_handler_filters_resolved_markets(
        self, mock_update: MagicMock
    ) -> None:
        """Test markets handler filters out resolved markets when category is set."""
        mock_context = MagicMock()
        mock_context.args = ["politics"]

        with patch(
            "src.telegram_commands.handlers.MarketRepository"
        ) as MockMarketRepo:
            mock_market_repo = MagicMock()
            # Return mix of active and resolved markets
            mock_market_repo.get_markets_by_category = AsyncMock(
                return_value=[
                    Market(
                        id="market-1",
                        title="Active Market",
                        category=MarketCategory.POLITICS,
                        yes_price=0.5,
                        liquidity=10000.0,
                        resolution_status=None,
                    ),
                    Market(
                        id="market-2",
                        title="Resolved Market",
                        category=MarketCategory.POLITICS,
                        yes_price=0.5,
                        liquidity=10000.0,
                        resolution_status="RESOLVED",
                    ),
                ]
            )
            MockMarketRepo.return_value = mock_market_repo

            handler = create_markets_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            # Should only show 1 active market
            assert "(1 个)" in call_args.args[0]
            assert "Active Market" in call_args.args[0]
            assert "Resolved Market" not in call_args.args[0]

    @pytest.mark.asyncio
    async def test_markets_handler_sorts_by_liquidity(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test markets handler sorts markets by liquidity (highest first)."""
        with patch(
            "src.telegram_commands.handlers.MarketRepository"
        ) as MockMarketRepo:
            mock_market_repo = MagicMock()
            mock_market_repo.get_active_markets = AsyncMock(
                return_value=[
                    Market(
                        id="market-1",
                        title="Low Liquidity",
                        yes_price=0.5,
                        liquidity=1000.0,
                    ),
                    Market(
                        id="market-2",
                        title="High Liquidity",
                        yes_price=0.5,
                        liquidity=100000.0,
                    ),
                    Market(
                        id="market-3",
                        title="Medium Liquidity",
                        yes_price=0.5,
                        liquidity=10000.0,
                    ),
                ]
            )
            MockMarketRepo.return_value = mock_market_repo

            handler = create_markets_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            message = call_args.args[0]
            # High liquidity should be first
            lines = message.split("\n")
            # Find index of each market title
            high_idx = next(i for i, l in enumerate(lines) if "High Liquidity" in l)
            medium_idx = next(i for i, l in enumerate(lines) if "Medium Liquidity" in l)
            low_idx = next(i for i, l in enumerate(lines) if "Low Liquidity" in l)
            # Verify order
            assert high_idx < medium_idx < low_idx


class TestHistoryFormatter:
    """Tests for history message formatter.

    Story 9.9: Telegram 命令处理 - 交易历史
    """

    def test_format_history_message_with_data(self) -> None:
        """Test history message with data."""
        trade_data = [
            {
                "id": 1,
                "market_id": "market-1",
                "market_title": "Will Trump win?",
                "trade_type": TradeType.BUY_YES,
                "mode": TradeMode.PAPER,
                "amount": 10.0,
                "price": 0.65,
                "status": TradeStatus.FILLED,
                "created_at": datetime.now() - timedelta(hours=2),
            },
            {
                "id": 2,
                "market_id": "market-2",
                "market_title": "BTC > $100k?",
                "trade_type": TradeType.SELL,
                "mode": TradeMode.PAPER,
                "amount": 8.0,
                "price": 0.55,
                "status": TradeStatus.FILLED,
                "created_at": datetime.now() - timedelta(hours=5),
            },
        ]
        message = format_history_message([], trade_data=trade_data)

        assert "*最近交易*" in message
        assert "(2 笔)" in message
        assert "BUY YES" in message
        assert "SELL" in message
        assert "$10.00" in message
        assert "0.65" in message
        assert "持仓中" in message

    def test_format_history_message_no_trades(self) -> None:
        """Test history message with no trades."""
        message = format_history_message([])

        assert "*最近交易*" in message
        assert "暂无交易记录" in message

    def test_format_history_message_with_mode(self) -> None:
        """Test history message with mode filter."""
        message = format_history_message([], mode=TradeMode.PAPER)

        assert "*最近交易* (PAPER)" in message

    def test_format_history_message_with_trade_models(self) -> None:
        """Test history message with Trade model objects."""
        trades = [
            Trade(
                id=1,
                market_id="market-1",
                trade_type=TradeType.BUY_YES,
                mode=TradeMode.PAPER,
                amount=10.0,
                price=0.65,
                status=TradeStatus.FILLED,
                created_at=datetime.now() - timedelta(hours=2),
            ),
        ]
        message = format_history_message(trades)

        assert "*最近交易*" in message
        assert "(1 笔)" in message

    def test_format_history_message_cancelled_trade(self) -> None:
        """Test history message with cancelled trade."""
        trade_data = [
            {
                "id": 1,
                "market_id": "market-1",
                "market_title": "Fed rate cut?",
                "trade_type": TradeType.BUY_YES,
                "mode": TradeMode.PAPER,
                "amount": 5.0,
                "price": 0.72,
                "status": TradeStatus.CANCELLED,
                "created_at": datetime.now() - timedelta(days=1),
            },
        ]
        message = format_history_message([], trade_data=trade_data)

        assert "已取消" in message

    def test_format_history_message_pending_trade(self) -> None:
        """Test history message with pending trade."""
        trade_data = [
            {
                "id": 1,
                "market_id": "market-1",
                "market_title": "Test Market",
                "trade_type": TradeType.BUY_NO,
                "mode": TradeMode.PAPER,
                "amount": 10.0,
                "price": 0.45,
                "status": TradeStatus.PENDING,
                "created_at": datetime.now(),
            },
        ]
        message = format_history_message([], trade_data=trade_data)

        assert "处理中" in message

    def test_format_relative_time_just_now(self) -> None:
        """Test relative time formatting for just now."""
        assert _format_relative_time(datetime.now()) == "刚刚"

    def test_format_relative_time_minutes_ago(self) -> None:
        """Test relative time formatting for minutes ago."""
        result = _format_relative_time(datetime.now() - timedelta(minutes=30))
        assert "分钟前" in result

    def test_format_relative_time_hours_ago(self) -> None:
        """Test relative time formatting for hours ago."""
        result = _format_relative_time(datetime.now() - timedelta(hours=5))
        assert "小时前" in result

    def test_format_relative_time_days_ago(self) -> None:
        """Test relative time formatting for days ago."""
        result = _format_relative_time(datetime.now() - timedelta(days=2))
        assert "天前" in result

    def test_format_relative_time_long_ago(self) -> None:
        """Test relative time formatting for dates over 30 days."""
        result = _format_relative_time(datetime.now() - timedelta(days=60))
        # Should return date string in YYYY-MM-DD format
        assert "-" in result

    def test_format_history_message_buy_no(self) -> None:
        """Test history message with BUY NO trade type."""
        trade_data = [
            {
                "id": 1,
                "market_id": "market-1",
                "market_title": "Test Market",
                "trade_type": TradeType.BUY_NO,
                "mode": TradeMode.PAPER,
                "amount": 10.0,
                "price": 0.35,
                "status": TradeStatus.FILLED,
                "created_at": datetime.now(),
            },
        ]
        message = format_history_message([], trade_data=trade_data)

        assert "BUY NO" in message

    def test_format_history_message_with_null_trade_type(self) -> None:
        """Test history message with null trade_type (line 441-442)."""
        trade_data = [
            {
                "id": 1,
                "market_id": "market-1",
                "market_title": "Test Market",
                "trade_type": None,
                "mode": TradeMode.PAPER,
                "amount": 10.0,
                "price": 0.5,
                "status": TradeStatus.FILLED,
                "created_at": datetime.now(),
            },
        ]
        message = format_history_message([], trade_data=trade_data)

        assert "TRADE" in message

    def test_format_history_message_with_dict_trade_type(self) -> None:
        """Test history message with dict trade_type (line 455-456)."""
        trade_data = [
            {
                "id": 1,
                "market_id": "market-1",
                "market_title": "Test Market",
                "trade_type": "CUSTOM_TYPE",  # Not an enum, just a string
                "mode": TradeMode.PAPER,
                "amount": 10.0,
                "price": 0.5,
                "status": TradeStatus.FILLED,
                "created_at": datetime.now(),
            },
        ]
        message = format_history_message([], trade_data=trade_data)

        assert "CUSTOM_TYPE" in message

    def test_format_history_message_with_null_status(self) -> None:
        """Test history message with null status (line 461)."""
        trade_data = [
            {
                "id": 1,
                "market_id": "market-1",
                "market_title": "Test Market",
                "trade_type": TradeType.BUY_YES,
                "mode": TradeMode.PAPER,
                "amount": 10.0,
                "price": 0.5,
                "status": None,
                "created_at": datetime.now(),
            },
        ]
        message = format_history_message([], trade_data=trade_data)

        assert "处理中" in message

    def test_format_history_message_with_dict_status(self) -> None:
        """Test history message with dict status (line 471)."""
        trade_data = [
            {
                "id": 1,
                "market_id": "market-1",
                "market_title": "Test Market",
                "trade_type": TradeType.BUY_YES,
                "mode": TradeMode.PAPER,
                "amount": 10.0,
                "price": 0.5,
                "status": "CUSTOM_STATUS",  # Not an enum, just a string
                "created_at": datetime.now(),
            },
        ]
        message = format_history_message([], trade_data=trade_data)

        assert "CUSTOM_STATUS" in message


class TestHistoryHandler:
    """Tests for history command handler.

    Story 9.9: Telegram 命令处理 - 交易历史
    """

    @pytest.fixture
    def mock_update(self) -> MagicMock:
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456789
        update.message = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock callback context."""
        context = MagicMock()
        context.args = []
        return context

    @pytest.mark.asyncio
    async def test_history_handler_default_limit(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test history handler with default 10 limit."""
        with (
            patch(
                "src.telegram_commands.handlers.TradeRepository"
            ) as MockTradeRepo,
            patch(
                "src.telegram_commands.handlers.MarketRepository"
            ) as MockMarketRepo,
        ):
            # Setup mock trade repo
            mock_trade_repo = MagicMock()
            mock_trade_repo.get_recent = AsyncMock(
                return_value=[
                    Trade(
                        id=i,
                        market_id=f"market-{i}",
                        trade_type=TradeType.BUY_YES,
                        mode=TradeMode.PAPER,
                        amount=10.0 + i,
                        price=0.5 + i * 0.05,
                        shares=10.0,
                        status=TradeStatus.FILLED,
                        created_at=datetime.now() - timedelta(hours=i),
                    )
                    for i in range(10)
                ]
            )
            MockTradeRepo.return_value = mock_trade_repo

            # Setup mock market repo
            mock_market_repo = MagicMock()
            mock_market_repo.get_market = AsyncMock(
                return_value=Market(
                    id="market-1",
                    title="Test Market",
                )
            )
            MockMarketRepo.return_value = mock_market_repo

            handler = create_history_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "*最近交易*" in call_args.args[0]
            assert call_args.kwargs.get("parse_mode") == "Markdown"

    @pytest.mark.asyncio
    async def test_history_handler_custom_limit(
        self, mock_update: MagicMock
    ) -> None:
        """Test history handler with custom limit parameter."""
        mock_context = MagicMock()
        mock_context.args = ["20"]

        with (
            patch(
                "src.telegram_commands.handlers.TradeRepository"
            ) as MockTradeRepo,
            patch(
                "src.telegram_commands.handlers.MarketRepository"
            ) as MockMarketRepo,
        ):
            mock_trade_repo = MagicMock()
            mock_trade_repo.get_recent = AsyncMock(return_value=[])
            MockTradeRepo.return_value = mock_trade_repo

            mock_market_repo = MagicMock()
            MockMarketRepo.return_value = mock_market_repo

            handler = create_history_handler("123456789")
            await handler(mock_update, mock_context)

            # Verify limit parameter was passed
            mock_trade_repo.get_recent.assert_called_once()
            call_args = mock_trade_repo.get_recent.call_args
            assert call_args.args[0] == 20

    @pytest.mark.asyncio
    async def test_history_handler_mode_filter_paper(
        self, mock_update: MagicMock
    ) -> None:
        """Test history handler with paper mode filter."""
        mock_context = MagicMock()
        mock_context.args = ["paper"]

        with (
            patch(
                "src.telegram_commands.handlers.TradeRepository"
            ) as MockTradeRepo,
            patch(
                "src.telegram_commands.handlers.MarketRepository"
            ) as MockMarketRepo,
        ):
            mock_trade_repo = MagicMock()
            mock_trade_repo.get_by_mode = AsyncMock(return_value=[])
            MockTradeRepo.return_value = mock_trade_repo

            mock_market_repo = MagicMock()
            MockMarketRepo.return_value = mock_market_repo

            handler = create_history_handler("123456789")
            await handler(mock_update, mock_context)

            # Verify mode parameter was passed
            mock_trade_repo.get_by_mode.assert_called_once()
            call_args = mock_trade_repo.get_by_mode.call_args
            assert call_args.args[0] == TradeMode.PAPER

    @pytest.mark.asyncio
    async def test_history_handler_mode_filter_live(
        self, mock_update: MagicMock
    ) -> None:
        """Test history handler with live mode filter."""
        mock_context = MagicMock()
        mock_context.args = ["live"]

        with (
            patch(
                "src.telegram_commands.handlers.TradeRepository"
            ) as MockTradeRepo,
            patch(
                "src.telegram_commands.handlers.MarketRepository"
            ) as MockMarketRepo,
        ):
            mock_trade_repo = MagicMock()
            mock_trade_repo.get_by_mode = AsyncMock(return_value=[])
            MockTradeRepo.return_value = mock_trade_repo

            mock_market_repo = MagicMock()
            MockMarketRepo.return_value = mock_market_repo

            handler = create_history_handler("123456789")
            await handler(mock_update, mock_context)

            # Verify mode parameter was passed
            mock_trade_repo.get_by_mode.assert_called_once()
            call_args = mock_trade_repo.get_by_mode.call_args
            assert call_args.args[0] == TradeMode.LIVE

    @pytest.mark.asyncio
    async def test_history_handler_no_trades(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test history handler with no trades."""
        with (
            patch(
                "src.telegram_commands.handlers.TradeRepository"
            ) as MockTradeRepo,
            patch(
                "src.telegram_commands.handlers.MarketRepository"
            ) as MockMarketRepo,
        ):
            mock_trade_repo = MagicMock()
            mock_trade_repo.get_recent = AsyncMock(return_value=[])
            MockTradeRepo.return_value = mock_trade_repo

            mock_market_repo = MagicMock()
            MockMarketRepo.return_value = mock_market_repo

            handler = create_history_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "暂无交易记录" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_history_handler_unauthorized(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test history handler with unauthorized user."""
        handler = create_history_handler("999888777")
        await handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "*未授权访问*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_history_handler_no_restriction(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test history handler with no chat ID restriction."""
        with (
            patch(
                "src.telegram_commands.handlers.TradeRepository"
            ) as MockTradeRepo,
            patch(
                "src.telegram_commands.handlers.MarketRepository"
            ) as MockMarketRepo,
        ):
            mock_trade_repo = MagicMock()
            mock_trade_repo.get_recent = AsyncMock(return_value=[])
            MockTradeRepo.return_value = mock_trade_repo

            mock_market_repo = MagicMock()
            MockMarketRepo.return_value = mock_market_repo

            # None means no restriction
            handler = create_history_handler(None)
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "*最近交易*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_history_handler_no_effective_chat(self) -> None:
        """Test history handler when update has no effective_chat."""
        mock_update = MagicMock()
        mock_update.effective_chat = None
        mock_update.message = AsyncMock()

        handler = create_history_handler("123456789")
        await handler(mock_update, MagicMock())

        # Should not call reply_text
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_history_handler_limit_out_of_range_clamped(
        self, mock_update: MagicMock
    ) -> None:
        """Test history handler clamps limit to valid range."""
        mock_context = MagicMock()
        mock_context.args = ["100"]  # Over 50

        with (
            patch(
                "src.telegram_commands.handlers.TradeRepository"
            ) as MockTradeRepo,
            patch(
                "src.telegram_commands.handlers.MarketRepository"
            ) as MockMarketRepo,
        ):
            mock_trade_repo = MagicMock()
            mock_trade_repo.get_recent = AsyncMock(return_value=[])
            MockTradeRepo.return_value = mock_trade_repo

            mock_market_repo = MagicMock()
            MockMarketRepo.return_value = mock_market_repo

            handler = create_history_handler("123456789")
            await handler(mock_update, mock_context)

            # Verify limit was clamped to 50
            mock_trade_repo.get_recent.assert_called_once()
            call_args = mock_trade_repo.get_recent.call_args
            assert call_args.args[0] == 50

    @pytest.mark.asyncio
    async def test_history_handler_limit_below_minimum_clamped(
        self, mock_update: MagicMock
    ) -> None:
        """Test history handler clamps limit to minimum of 1."""
        mock_context = MagicMock()
        mock_context.args = ["0"]  # Below 1

        with (
            patch(
                "src.telegram_commands.handlers.TradeRepository"
            ) as MockTradeRepo,
            patch(
                "src.telegram_commands.handlers.MarketRepository"
            ) as MockMarketRepo,
        ):
            mock_trade_repo = MagicMock()
            mock_trade_repo.get_recent = AsyncMock(return_value=[])
            MockTradeRepo.return_value = mock_trade_repo

            mock_market_repo = MagicMock()
            MockMarketRepo.return_value = mock_market_repo

            handler = create_history_handler("123456789")
            await handler(mock_update, mock_context)

            # Verify limit was clamped to 1
            mock_trade_repo.get_recent.assert_called_once()
            call_args = mock_trade_repo.get_recent.call_args
            assert call_args.args[0] == 1

    @pytest.mark.asyncio
    async def test_history_handler_invalid_limit_uses_default(
        self, mock_update: MagicMock
    ) -> None:
        """Test history handler with invalid limit parameter uses default."""
        mock_context = MagicMock()
        mock_context.args = ["invalid"]

        with (
            patch(
                "src.telegram_commands.handlers.TradeRepository"
            ) as MockTradeRepo,
            patch(
                "src.telegram_commands.handlers.MarketRepository"
            ) as MockMarketRepo,
        ):
            mock_trade_repo = MagicMock()
            mock_trade_repo.get_recent = AsyncMock(return_value=[])
            MockTradeRepo.return_value = mock_trade_repo

            mock_market_repo = MagicMock()
            MockMarketRepo.return_value = mock_market_repo

            handler = create_history_handler("123456789")
            await handler(mock_update, mock_context)

            # Verify default limit (10) was used
            mock_trade_repo.get_recent.assert_called_once()
            call_args = mock_trade_repo.get_recent.call_args
            assert call_args.args[0] == 10

    @pytest.mark.asyncio
    async def test_history_handler_combined_limit_and_mode(
        self, mock_update: MagicMock
    ) -> None:
        """Test history handler with both limit and mode parameters."""
        mock_context = MagicMock()
        mock_context.args = ["5", "paper"]

        with (
            patch(
                "src.telegram_commands.handlers.TradeRepository"
            ) as MockTradeRepo,
            patch(
                "src.telegram_commands.handlers.MarketRepository"
            ) as MockMarketRepo,
        ):
            mock_trade_repo = MagicMock()
            mock_trade_repo.get_by_mode = AsyncMock(return_value=[])
            MockTradeRepo.return_value = mock_trade_repo

            mock_market_repo = MagicMock()
            MockMarketRepo.return_value = mock_market_repo

            handler = create_history_handler("123456789")
            await handler(mock_update, mock_context)

            # Verify mode was used (with limit applied to results)
            mock_trade_repo.get_by_mode.assert_called_once_with(TradeMode.PAPER)

    @pytest.mark.asyncio
    async def test_history_handler_market_not_found(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test history handler when market is not found."""
        with (
            patch(
                "src.telegram_commands.handlers.TradeRepository"
            ) as MockTradeRepo,
            patch(
                "src.telegram_commands.handlers.MarketRepository"
            ) as MockMarketRepo,
        ):
            mock_trade_repo = MagicMock()
            mock_trade_repo.get_recent = AsyncMock(
                return_value=[
                    Trade(
                        id=1,
                        market_id="unknown-market",
                        trade_type=TradeType.BUY_YES,
                        mode=TradeMode.PAPER,
                        amount=10.0,
                        price=0.5,
                        status=TradeStatus.FILLED,
                        created_at=datetime.now(),
                    )
                ]
            )
            MockTradeRepo.return_value = mock_trade_repo

            mock_market_repo = MagicMock()
            mock_market_repo.get_market = AsyncMock(return_value=None)
            MockMarketRepo.return_value = mock_market_repo

            handler = create_history_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            # Should display market_id as fallback when market not found
            assert "Market unknown-market" in call_args.args[0]


class TestSetupCommandHandlersWithMarkets:
    """Tests for setup_command_handlers with markets handler.

    Story 9.8: Telegram 命令处理 - 市场查询
    """

    def test_setup_registers_nine_handlers_legacy(self) -> None:
        """Test that nine handlers are registered including history."""
        mock_app = MagicMock()
        mock_state = MagicMock()

        setup_command_handlers(mock_app, mock_state, "123456789")

        # Should add nine handlers: status, help, positions, stats, markets, history,
        # predict, confirm, cancel
        assert mock_app.add_handler.call_count == 9


# =============================================================================
# Story 9.10: Telegram 命令处理 - 手动触发分析
# =============================================================================


class TestPredictFormatters:
    """Tests for predict message formatters.

    Story 9.10: Telegram 命令处理 - 手动触发分析
    """

    def test_format_predict_market_list_with_data(self) -> None:
        """Test market list formatting with data."""
        from src.telegram_commands.formatters import format_predict_market_list

        markets = [
            Market(id="m1", title="Test Market 1", yes_price=0.65, liquidity=50000),
            Market(id="m2", title="Test Market 2", yes_price=0.45, liquidity=120000),
        ]
        message = format_predict_market_list(markets)

        assert "*选择市场分析*" in message
        assert "Test Market 1" in message
        assert "YES: 0.65" in message
        assert "$50k" in message

    def test_format_predict_market_list_no_markets(self) -> None:
        """Test market list formatting with no markets."""
        from src.telegram_commands.formatters import format_predict_market_list

        message = format_predict_market_list([])

        assert "*选择市场分析*" in message
        assert "暂无活跃市场" in message

    def test_format_analyzing_message(self) -> None:
        """Test analyzing message formatting."""
        from src.telegram_commands.formatters import format_analyzing_message

        market = Market(id="m1", title="Test Market", yes_price=0.5)
        message = format_analyzing_message(market)

        assert "*分析中...*" in message
        assert "Test Market" in message
        assert "LLM 正在分析" in message

    def test_format_trade_cancelled(self) -> None:
        """Test trade cancelled message."""
        from src.telegram_commands.formatters import format_trade_cancelled

        message = format_trade_cancelled()
        assert "*交易已取消*" in message

    def test_format_predict_result_with_confirm_buy_yes(self) -> None:
        """Test prediction result with confirm for BUY_YES."""
        from src.models.prediction import PredictionResult, Recommendation
        from src.telegram_commands.formatters import format_predict_result_with_confirm

        market = Market(id="m1", title="Test Market", yes_price=0.65)
        prediction = PredictionResult(
            predicted_probability=0.80,
            confidence=0.85,
            reasoning="Strong signal",
            key_assumptions=["Assumption 1"],
            recommendation=Recommendation.BUY_YES,
            edge=0.15,
        )
        message = format_predict_result_with_confirm(market, prediction)

        assert "*市场分析完成*" in message
        assert "Test Market" in message
        assert "BUY YES" in message
        assert "80%" in message
        assert "85%" in message
        assert "15%" in message
        assert "/confirm" in message
        assert "/cancel" in message

    def test_format_predict_result_with_confirm_buy_no(self) -> None:
        """Test prediction result with confirm for BUY_NO."""
        from src.models.prediction import PredictionResult, Recommendation
        from src.telegram_commands.formatters import format_predict_result_with_confirm

        market = Market(id="m1", title="Test Market", yes_price=0.35)
        prediction = PredictionResult(
            predicted_probability=0.30,
            confidence=0.80,
            reasoning="Sell signal",
            key_assumptions=[],
            recommendation=Recommendation.BUY_NO,
            edge=0.20,
        )
        message = format_predict_result_with_confirm(market, prediction)

        assert "BUY NO" in message

    def test_format_predict_result_no_trade(self) -> None:
        """Test prediction result when not tradeable."""
        from src.models.prediction import PredictionResult, Recommendation
        from src.telegram_commands.formatters import format_predict_result_no_trade

        market = Market(id="m1", title="Test Market", yes_price=0.5)
        prediction = PredictionResult(
            predicted_probability=0.55,
            confidence=0.60,
            reasoning="Weak signal",
            key_assumptions=[],
            recommendation=Recommendation.NO_TRADE,
            edge=0.05,
        )
        message = format_predict_result_no_trade(market, prediction)

        assert "*市场分析完成*" in message
        assert "NO_TRADE" in message
        assert "未达到交易门槛" in message

    def test_format_trade_suggestion_buy_yes(self) -> None:
        """Test trade suggestion for BUY_YES."""
        from src.models.prediction import PredictionResult, Recommendation
        from src.telegram_commands.formatters import format_trade_suggestion

        market = Market(id="m1", title="Test Market", yes_price=0.65)
        prediction = PredictionResult(
            predicted_probability=0.80,
            confidence=0.85,
            reasoning="Strong signal",
            key_assumptions=[],
            recommendation=Recommendation.BUY_YES,
            edge=0.15,
        )
        message = format_trade_suggestion(market, prediction, 40.0)

        assert "*交易建议*" in message
        assert "Test Market" in message
        assert "BUY YES" in message
        assert "$40.00" in message
        assert "0.65" in message
        assert "手动触发" in message

    def test_format_trade_suggestion_buy_no(self) -> None:
        """Test trade suggestion for BUY_NO."""
        from src.models.prediction import PredictionResult, Recommendation
        from src.telegram_commands.formatters import format_trade_suggestion

        market = Market(id="m1", title="Test Market", yes_price=0.65)
        prediction = PredictionResult(
            predicted_probability=0.30,
            confidence=0.80,
            reasoning="Sell signal",
            key_assumptions=[],
            recommendation=Recommendation.BUY_NO,
            edge=0.20,
        )
        message = format_trade_suggestion(market, prediction, 40.0)

        assert "BUY NO" in message
        # Price for NO should be 1 - 0.65 = 0.35
        assert "0.35" in message

    def test_format_predict_market_list_with_no_price(self) -> None:
        """Test market list with market that has no yes_price but has no_price."""
        from src.telegram_commands.formatters import format_predict_market_list

        markets = [
            Market(id="m1", title="Test Market", no_price=0.35, liquidity=500),
        ]
        message = format_predict_market_list(markets)

        assert "*选择市场分析*" in message
        assert "NO: 0.35" in message
        assert "$500" in message  # liquidity < 1000

    def test_format_predict_market_list_with_small_liquidity(self) -> None:
        """Test market list with small liquidity (less than 1000)."""
        from src.telegram_commands.formatters import format_predict_market_list

        markets = [
            Market(id="m1", title="Test Market", yes_price=0.5, liquidity=500),
        ]
        message = format_predict_market_list(markets)

        assert "$500" in message  # No 'k' suffix for small liquidity

    def test_format_predict_result_with_confirm_no_trade(self) -> None:
        """Test prediction result with confirm for NO_TRADE recommendation."""
        from src.models.prediction import PredictionResult, Recommendation
        from src.telegram_commands.formatters import format_predict_result_with_confirm

        market = Market(id="m1", title="Test Market", yes_price=0.5)
        prediction = PredictionResult(
            predicted_probability=0.5,
            confidence=0.5,
            reasoning="Uncertain",
            key_assumptions=[],
            recommendation=Recommendation.NO_TRADE,
            edge=0.0,
        )
        message = format_predict_result_with_confirm(market, prediction)

        # Should still format the message even with NO_TRADE
        assert "*市场分析完成*" in message
        assert "NO_TRADE" in message


class TestPredictHandler:
    """Tests for predict command handler.

    Story 9.10: Telegram 命令处理 - 手动触发分析
    """

    @pytest.fixture
    def mock_update(self) -> MagicMock:
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456789
        update.message = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock callback context."""
        context = MagicMock()
        context.args = []
        return context

    @pytest.mark.asyncio
    async def test_predict_handler_no_args_shows_list(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test predict handler without args shows market list."""
        with patch(
            "src.telegram_commands.handlers.MarketRepository"
        ) as MockMarketRepo:
            mock_market_repo = MagicMock()
            mock_market_repo.get_active_markets = AsyncMock(
                return_value=[
                    Market(
                        id=f"market-{i}",
                        title=f"Test Market {i}",
                        yes_price=0.5 + i * 0.1,
                        liquidity=10000.0 + i * 1000,
                    )
                    for i in range(5)
                ]
            )
            MockMarketRepo.return_value = mock_market_repo

            handler = create_predict_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args.args[0]
            assert "*选择市场分析*" in call_args

    @pytest.mark.asyncio
    async def test_predict_handler_with_index(self, mock_update: MagicMock) -> None:
        """Test predict handler with index parameter."""
        from src.models.prediction import PredictionResult, Recommendation

        mock_context = MagicMock()
        mock_context.args = ["2"]

        with (
            patch(
                "src.telegram_commands.handlers.MarketRepository"
            ) as MockMarketRepo,
            patch("src.telegram_commands.handlers.LLMAnalyzer") as MockAnalyzer,
            patch("src.telegram_commands.handlers.settings") as mock_settings,
        ):
            # Setup mock settings
            mock_settings.risk.min_confidence = 0.75
            mock_settings.risk.min_edge = 0.10

            # Setup mock market repo
            mock_market_repo = MagicMock()
            mock_market_repo.get_active_markets = AsyncMock(
                return_value=[
                    Market(id="market-1", title="Test Market 1", yes_price=0.5),
                    Market(id="market-2", title="Test Market 2", yes_price=0.6),
                ]
            )
            MockMarketRepo.return_value = mock_market_repo

            # Setup mock analyzer
            mock_analyzer = MagicMock()
            mock_analyzer.analyze_market = AsyncMock(
                return_value=PredictionResult(
                    predicted_probability=0.8,
                    confidence=0.85,
                    reasoning="Test reasoning",
                    key_assumptions=["Assumption 1"],
                    recommendation=Recommendation.BUY_YES,
                    edge=0.15,
                )
            )
            MockAnalyzer.return_value = mock_analyzer

            handler = create_predict_handler("123456789")
            await handler(mock_update, mock_context)

            # Verify analyze was called with second market (index 1)
            mock_analyzer.analyze_market.assert_called_once()
            called_market = mock_analyzer.analyze_market.call_args.args[0]
            assert called_market.id == "market-2"

    @pytest.mark.asyncio
    async def test_predict_handler_with_market_id(self, mock_update: MagicMock) -> None:
        """Test predict handler with market ID parameter."""
        from src.models.prediction import PredictionResult, Recommendation

        mock_context = MagicMock()
        mock_context.args = ["market-abc123"]

        with (
            patch(
                "src.telegram_commands.handlers.MarketRepository"
            ) as MockMarketRepo,
            patch("src.telegram_commands.handlers.LLMAnalyzer") as MockAnalyzer,
            patch("src.telegram_commands.handlers.settings") as mock_settings,
        ):
            # Setup mock settings
            mock_settings.risk.min_confidence = 0.75
            mock_settings.risk.min_edge = 0.10

            # Setup mock market repo
            mock_market_repo = MagicMock()
            mock_market_repo.get_market = AsyncMock(
                return_value=Market(
                    id="market-abc123",
                    title="Test Market",
                    yes_price=0.6,
                )
            )
            MockMarketRepo.return_value = mock_market_repo

            # Setup mock analyzer
            mock_analyzer = MagicMock()
            mock_analyzer.analyze_market = AsyncMock(
                return_value=PredictionResult(
                    predicted_probability=0.5,
                    confidence=0.6,
                    reasoning="Test",
                    key_assumptions=[],
                    recommendation=Recommendation.NO_TRADE,
                    edge=0.05,
                )
            )
            MockAnalyzer.return_value = mock_analyzer

            handler = create_predict_handler("123456789")
            await handler(mock_update, mock_context)

            # Verify get_market was called with correct ID
            mock_market_repo.get_market.assert_called_once_with("market-abc123")

    @pytest.mark.asyncio
    async def test_predict_handler_market_not_found(
        self, mock_update: MagicMock
    ) -> None:
        """Test predict handler with non-existent market ID."""
        mock_context = MagicMock()
        mock_context.args = ["nonexistent"]

        with patch(
            "src.telegram_commands.handlers.MarketRepository"
        ) as MockMarketRepo:
            mock_market_repo = MagicMock()
            mock_market_repo.get_market = AsyncMock(return_value=None)
            MockMarketRepo.return_value = mock_market_repo

            handler = create_predict_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called()
            call_args = mock_update.message.reply_text.call_args.args[0]
            assert "市场不存在" in call_args

    @pytest.mark.asyncio
    async def test_predict_handler_invalid_index(self, mock_update: MagicMock) -> None:
        """Test predict handler with invalid (negative) index."""
        mock_context = MagicMock()
        mock_context.args = ["0"]  # Will become -1 after conversion

        handler = create_predict_handler("123456789")
        await handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called()
        call_args = mock_update.message.reply_text.call_args.args[0]
        assert "无效的市场序号" in call_args

    @pytest.mark.asyncio
    async def test_predict_handler_index_out_of_range(
        self, mock_update: MagicMock
    ) -> None:
        """Test predict handler with index out of range."""
        mock_context = MagicMock()
        mock_context.args = ["100"]

        with patch(
            "src.telegram_commands.handlers.MarketRepository"
        ) as MockMarketRepo:
            mock_market_repo = MagicMock()
            mock_market_repo.get_active_markets = AsyncMock(
                return_value=[
                    Market(id="market-1", title="Test Market 1", yes_price=0.5),
                ]
            )
            MockMarketRepo.return_value = mock_market_repo

            handler = create_predict_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called()
            call_args = mock_update.message.reply_text.call_args.args[0]
            assert "不存在" in call_args

    @pytest.mark.asyncio
    async def test_predict_handler_unauthorized(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test predict handler with unauthorized user."""
        handler = create_predict_handler("999888777")
        await handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args.args[0]
        assert "*未授权访问*" in call_args

    @pytest.mark.asyncio
    async def test_predict_handler_analysis_error(
        self, mock_update: MagicMock
    ) -> None:
        """Test predict handler when analysis fails."""
        from src.analysis import AnalysisError

        mock_context = MagicMock()
        mock_context.args = ["market-1"]

        with (
            patch(
                "src.telegram_commands.handlers.MarketRepository"
            ) as MockMarketRepo,
            patch("src.telegram_commands.handlers.LLMAnalyzer") as MockAnalyzer,
        ):
            # Setup mock market repo
            mock_market_repo = MagicMock()
            mock_market_repo.get_market = AsyncMock(
                return_value=Market(
                    id="market-1",
                    title="Test Market",
                    yes_price=0.5,
                )
            )
            MockMarketRepo.return_value = mock_market_repo

            # Setup mock analyzer to raise error
            mock_analyzer = MagicMock()
            mock_analyzer.analyze_market = AsyncMock(
                side_effect=AnalysisError("LLM API failed")
            )
            MockAnalyzer.return_value = mock_analyzer

            handler = create_predict_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called()
            # Last call should be error message
            call_args = mock_update.message.reply_text.call_args.args[0]
            assert "分析失败" in call_args

    @pytest.mark.asyncio
    async def test_predict_handler_no_effective_chat(self) -> None:
        """Test predict handler when update has no effective_chat."""
        mock_update = MagicMock()
        mock_update.effective_chat = None
        mock_update.message = AsyncMock()

        handler = create_predict_handler("123456789")
        await handler(mock_update, MagicMock())

        # Should not call reply_text
        mock_update.message.reply_text.assert_not_called()


class TestConfirmCancelHandlers:
    """Tests for confirm and cancel command handlers.

    Story 9.10: Telegram 命令处理 - 手动触发分析
    """

    @pytest.fixture
    def mock_update(self) -> MagicMock:
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456789
        update.message = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock callback context."""
        return MagicMock(args=[])

    @pytest.mark.asyncio
    async def test_confirm_handler_no_effective_chat(self) -> None:
        """Test confirm handler when update has no effective_chat."""
        mock_update = MagicMock()
        mock_update.effective_chat = None
        mock_update.message = AsyncMock()

        handler = create_confirm_handler("123456789")
        await handler(mock_update, MagicMock())

        # Should not call reply_text
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_confirm_handler_expired_confirmation(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test confirm handler with expired pending confirmation."""
        from datetime import datetime, timedelta

        from src.models.prediction import PredictionResult, Recommendation
        from src.telegram_commands import handlers
        from src.telegram_commands.handlers import PendingConfirmation

        # Setup expired pending confirmation
        market = Market(id="m1", title="Test Market", yes_price=0.5)
        prediction = PredictionResult(
            predicted_probability=0.8,
            confidence=0.85,
            reasoning="Test",
            key_assumptions=[],
            recommendation=Recommendation.BUY_YES,
            edge=0.15,
        )
        pending = PendingConfirmation("123456789", market, prediction)
        # Set as expired
        pending.expires_at = datetime.now() - timedelta(seconds=1)
        handlers._pending_confirmations["123456789"] = pending

        handler = create_confirm_handler("123456789")
        await handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args.args[0]
        assert "超时" in call_args

        # Verify expired confirmation was removed
        assert "123456789" not in handlers._pending_confirmations

    @pytest.mark.asyncio
    async def test_cancel_handler_no_effective_chat(self) -> None:
        """Test cancel handler when update has no effective_chat."""
        mock_update = MagicMock()
        mock_update.effective_chat = None
        mock_update.message = AsyncMock()

        handler = create_cancel_handler("123456789")
        await handler(mock_update, MagicMock())

        # Should not call reply_text
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_confirm_handler_no_pending(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test confirm handler with no pending confirmation."""
        # Clear any pending confirmations
        from src.telegram_commands import handlers

        handlers._pending_confirmations.clear()

        handler = create_confirm_handler("123456789")
        await handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args.args[0]
        assert "没有待确认的交易" in call_args

    @pytest.mark.asyncio
    async def test_cancel_handler_no_pending(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test cancel handler with no pending confirmation."""
        # Clear any pending confirmations
        from src.telegram_commands import handlers

        handlers._pending_confirmations.clear()

        handler = create_cancel_handler("123456789")
        await handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args.args[0]
        assert "没有待取消的交易" in call_args

    @pytest.mark.asyncio
    async def test_cancel_handler_with_pending(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test cancel handler with pending confirmation."""
        from src.models.prediction import PredictionResult, Recommendation
        from src.telegram_commands import handlers
        from src.telegram_commands.handlers import PendingConfirmation

        # Setup pending confirmation
        market = Market(id="m1", title="Test Market", yes_price=0.5)
        prediction = PredictionResult(
            predicted_probability=0.8,
            confidence=0.85,
            reasoning="Test",
            key_assumptions=[],
            recommendation=Recommendation.BUY_YES,
            edge=0.15,
        )
        handlers._pending_confirmations["123456789"] = PendingConfirmation(
            chat_id="123456789",
            market=market,
            prediction=prediction,
        )

        handler = create_cancel_handler("123456789")
        await handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args.args[0]
        assert "*交易已取消*" in call_args

        # Verify pending confirmation was removed
        assert "123456789" not in handlers._pending_confirmations

    @pytest.mark.asyncio
    async def test_confirm_handler_unauthorized(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test confirm handler with unauthorized user."""
        handler = create_confirm_handler("999888777")
        await handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args.args[0]
        assert "*未授权访问*" in call_args

    @pytest.mark.asyncio
    async def test_cancel_handler_unauthorized(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test cancel handler with unauthorized user."""
        handler = create_cancel_handler("999888777")
        await handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args.args[0]
        assert "*未授权访问*" in call_args

    @pytest.mark.asyncio
    async def test_confirm_handler_with_pending(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test confirm handler with valid pending confirmation."""
        from src.models.prediction import PredictionResult, Recommendation
        from src.telegram_commands import handlers
        from src.telegram_commands.handlers import PendingConfirmation

        # Setup pending confirmation
        market = Market(id="m1", title="Test Market", yes_price=0.65)
        prediction = PredictionResult(
            predicted_probability=0.8,
            confidence=0.85,
            reasoning="Test",
            key_assumptions=[],
            recommendation=Recommendation.BUY_YES,
            edge=0.15,
        )
        handlers._pending_confirmations["123456789"] = PendingConfirmation(
            chat_id="123456789",
            market=market,
            prediction=prediction,
        )

        with patch("src.telegram_commands.handlers.settings") as mock_settings:
            mock_settings.trading.initial_capital = 200.0
            mock_settings.risk.max_single_ratio = 0.20

            handler = create_confirm_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args.args[0]
            assert "*交易建议*" in call_args

        # Verify pending confirmation was removed
        assert "123456789" not in handlers._pending_confirmations


class TestPendingConfirmation:
    """Tests for PendingConfirmation class.

    Story 9.10: Telegram 命令处理 - 手动触发分析
    """

    def test_pending_confirmation_not_expired_initially(self) -> None:
        """Test that new confirmation is not expired."""
        from src.models.prediction import PredictionResult, Recommendation
        from src.telegram_commands.handlers import PendingConfirmation

        market = Market(id="m1", title="Test", yes_price=0.5)
        prediction = PredictionResult(
            predicted_probability=0.8,
            confidence=0.85,
            reasoning="Test",
            key_assumptions=[],
            recommendation=Recommendation.BUY_YES,
        )
        pending = PendingConfirmation("123456", market, prediction)

        assert not pending.is_expired()

    def test_pending_confirmation_expired_after_30_seconds(self) -> None:
        """Test that confirmation expires after 30 seconds."""
        from datetime import datetime, timedelta

        from src.models.prediction import PredictionResult, Recommendation
        from src.telegram_commands.handlers import PendingConfirmation

        market = Market(id="m1", title="Test", yes_price=0.5)
        prediction = PredictionResult(
            predicted_probability=0.8,
            confidence=0.85,
            reasoning="Test",
            key_assumptions=[],
            recommendation=Recommendation.BUY_YES,
        )
        pending = PendingConfirmation("123456", market, prediction)

        # Simulate time passing
        pending.expires_at = datetime.now() - timedelta(seconds=1)

        assert pending.is_expired()


class TestSetupCommandHandlersWithPredict:
    """Tests for setup_command_handlers with predict handler.

    Story 9.10: Telegram 命令处理 - 手动触发分析
    """

    def test_setup_registers_nine_handlers(self) -> None:
        """Test that nine handlers are registered including predict/confirm/cancel."""
        mock_app = MagicMock()
        mock_state = MagicMock()

        setup_command_handlers(mock_app, mock_state, "123456789")

        # Should add nine handlers: status, help, positions, stats, markets, history,
        # predict, confirm, cancel
        assert mock_app.add_handler.call_count == 9
