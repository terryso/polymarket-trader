"""Telegram commands module for bot interactions.

This module provides command handlers for the Telegram bot,
implementing /status, /help, and /positions commands.

Story 9.5: Telegram 命令处理 - 状态查询
Story 9.6: Telegram 命令处理 - 持仓查询

Usage:
    from src.telegram_commands import setup_command_handlers

    # In TelegramClient
    setup_command_handlers(application, state_manager, authorized_chat_id)
"""

from __future__ import annotations

__all__ = [
    "setup_command_handlers",
    "create_status_handler",
    "create_help_handler",
    "create_positions_handler",
    "format_status_message",
    "format_help_message",
    "format_unauthorized_message",
    "format_positions_message",
]

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
