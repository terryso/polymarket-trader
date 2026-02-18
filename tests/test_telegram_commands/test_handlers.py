"""Tests for Telegram command handlers.

Story 9.5: Telegram 命令处理 - 状态查询
Story 9.6: Telegram 命令处理 - 持仓查询
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.market import Market
from src.models.position import Position, PositionOutcome, PositionStatus
from src.telegram_commands.formatters import (
    format_help_message,
    format_positions_message,
    format_status_message,
    format_unauthorized_message,
)
from src.telegram_commands.handlers import (
    create_help_handler,
    create_positions_handler,
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


class TestSetupCommandHandlers:
    """Tests for setup_command_handlers function."""

    def test_setup_registers_handlers(self) -> None:
        """Test that handlers are registered."""
        mock_app = MagicMock()
        mock_state = MagicMock()

        setup_command_handlers(mock_app, mock_state, "123456789")

        # Should add three handlers: status, help, and positions
        assert mock_app.add_handler.call_count == 3

    def test_setup_registers_handlers_no_auth(self) -> None:
        """Test that handlers are registered without auth."""
        mock_app = MagicMock()
        mock_state = MagicMock()

        setup_command_handlers(mock_app, mock_state, None)

        # Should add three handlers: status, help, and positions
        assert mock_app.add_handler.call_count == 3


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
