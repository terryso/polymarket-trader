"""Tests for Telegram command handlers.

Story 9.5: Telegram 命令处理 - 状态查询
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.telegram_commands.formatters import (
    format_help_message,
    format_status_message,
    format_unauthorized_message,
)
from src.telegram_commands.handlers import (
    create_help_handler,
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

        # Should add two handlers: status and help
        assert mock_app.add_handler.call_count == 2

    def test_setup_registers_handlers_no_auth(self) -> None:
        """Test that handlers are registered without auth."""
        mock_app = MagicMock()
        mock_state = MagicMock()

        setup_command_handlers(mock_app, mock_state, None)

        # Should add two handlers: status and help
        assert mock_app.add_handler.call_count == 2
