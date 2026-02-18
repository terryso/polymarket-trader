"""Telegram commands module for bot interactions.

This module provides command handlers for the Telegram bot,
implementing /status, /help, /positions, /stats, /markets, /history, /predict, /confirm, /cancel, /enable, /disable, and /mode commands.

Story 9.5: Telegram 命令处理 - 状态查询
Story 9.6: Telegram 命令处理 - 持仓查询
Story 9.7: Telegram 命令处理 - 统计查询
Story 9.8: Telegram 命令处理 - 市场查询
Story 9.9: Telegram 命令处理 - 交易历史
Story 9.10: Telegram 命令处理 - 手动触发分析
Story 9.11: Telegram 命令处理 - 远程控制

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
    # Story 9.11: 远程控制
    "create_enable_handler",
    "create_disable_handler",
    "create_mode_handler",
    "create_confirm_mode_handler",
    "create_cancel_mode_handler",
    "PendingModeChange",
    # Formatters
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
    # Story 9.11: 远程控制 formatters
    "format_enable_message",
    "format_disable_message",
    "format_mode_status_message",
    "format_mode_change_confirmation",
    "format_mode_changed_message",
    "format_mode_change_cancelled",
    # Audit
    "log_audit_event",
    "AuditEventType",
]

from src.telegram_commands.audit import (
    AuditEventType,
    log_audit_event,
)
from src.telegram_commands.formatters import (  # Story 9.11: 远程控制
    format_analyzing_message,
    format_disable_message,
    format_enable_message,
    format_help_message,
    format_history_message,
    format_markets_message,
    format_mode_change_cancelled,
    format_mode_change_confirmation,
    format_mode_changed_message,
    format_mode_status_message,
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
from src.telegram_commands.handlers import (  # Story 9.11: 远程控制
    PendingConfirmation,
    PendingModeChange,
    create_cancel_handler,
    create_cancel_mode_handler,
    create_confirm_handler,
    create_confirm_mode_handler,
    create_disable_handler,
    create_enable_handler,
    create_help_handler,
    create_history_handler,
    create_markets_handler,
    create_mode_handler,
    create_positions_handler,
    create_predict_handler,
    create_stats_handler,
    create_status_handler,
    setup_command_handlers,
)
