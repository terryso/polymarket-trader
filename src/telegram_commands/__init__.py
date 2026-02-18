"""Telegram commands module for bot interactions.

This module provides command handlers for the Telegram bot,
implementing /status, /help, /positions, /stats, /markets, /history, /predict, /confirm, and /cancel commands.

Story 9.5: Telegram 命令处理 - 状态查询
Story 9.6: Telegram 命令处理 - 持仓查询
Story 9.7: Telegram 命令处理 - 统计查询
Story 9.8: Telegram 命令处理 - 市场查询
Story 9.9: Telegram 命令处理 - 交易历史
Story 9.10: Telegram 命令处理 - 手动触发分析

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
    "create_stats_handler",
    "create_markets_handler",
    "create_history_handler",
    "create_predict_handler",
    "create_confirm_handler",
    "create_cancel_handler",
    "PendingConfirmation",
    "format_status_message",
    "format_help_message",
    "format_unauthorized_message",
    "format_positions_message",
    "format_stats_message",
    "format_markets_message",
    "format_history_message",
    "format_predict_market_list",
    "format_analyzing_message",
    "format_predict_result_with_confirm",
    "format_predict_result_no_trade",
    "format_trade_suggestion",
    "format_trade_cancelled",
]

from src.telegram_commands.formatters import (
    format_analyzing_message,
    format_help_message,
    format_history_message,
    format_markets_message,
    format_positions_message,
    format_predict_market_list,
    format_predict_result_no_trade,
    format_predict_result_with_confirm,
    format_stats_message,
    format_status_message,
    format_trade_cancelled,
    format_trade_suggestion,
    format_unauthorized_message,
)
from src.telegram_commands.handlers import (
    PendingConfirmation,
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
