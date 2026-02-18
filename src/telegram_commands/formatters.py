"""Message formatters for Telegram commands.

This module provides formatting functions for Telegram command responses.

Story 9.5: Telegram 命令处理 - 状态查询
"""

from __future__ import annotations

__all__ = [
    "format_status_message",
    "format_help_message",
    "format_unauthorized_message",
]


def format_status_message(
    mode: str,
    current_capital: float,
    daily_pnl: float,
    open_positions: int,
    consecutive_losses: int,
    trading_enabled: bool,
) -> str:
    """Format a system status message.

    Args:
        mode: Trading mode (PAPER/LIVE)
        current_capital: Current capital in USD
        daily_pnl: Daily profit/loss in USD
        open_positions: Number of open positions
        consecutive_losses: Number of consecutive losses
        trading_enabled: Whether trading is enabled

    Returns:
        Formatted Markdown message

    Example:
        >>> msg = format_status_message("PAPER", 200.0, 10.0, 2, 0, True)
        >>> "*系统状态*" in msg
        True
    """
    # Calculate daily PnL percentage
    daily_pnl_pct = (daily_pnl / current_capital * 100) if current_capital > 0 else 0.0

    # Format PnL with sign
    pnl_sign = "+" if daily_pnl >= 0 else ""
    pnl_emoji = (
        "\U0001f4c8" if daily_pnl >= 0 else "\U0001f4c9"
    )  # chart_up / chart_down

    # Trading status emoji
    trading_emoji = "\u2705" if trading_enabled else "\u274c"  # check / x
    trading_status = "启用" if trading_enabled else "禁用"

    lines = [
        "\U0001f4ca *系统状态*",  # chart emoji
        f"模式: {mode}",
        f"资金: ${current_capital:.2f}",
        f"日盈亏: {pnl_emoji} {pnl_sign}${daily_pnl:.2f} ({pnl_sign}{daily_pnl_pct:.1f}%)",
        f"持仓: {open_positions} 个",
        f"连续亏损: {consecutive_losses}",
        f"交易: {trading_emoji} {trading_status}",
    ]

    return "\n".join(lines)


def format_help_message() -> str:
    """Format a help message with available commands.

    Returns:
        Formatted Markdown message with command list

    Example:
        >>> msg = format_help_message()
        >>> "/status" in msg
        True
    """
    lines = [
        "\U0001f4cb *可用命令*",
        "",
        "/status - 查看系统状态",
        "/positions - 查看当前持仓 (Story 9.6)",
        "/stats - 查看交易统计 (Story 9.7)",
        "/markets - 查看活跃市场 (Story 9.8)",
        "/history - 查看交易历史 (Story 9.9)",
        "/predict - 手动触发分析 (Story 9.10)",
        "/enable - 启用交易 (Story 9.11)",
        "/disable - 禁用交易 (Story 9.11)",
        "/mode - 查看/切换模式 (Story 9.11)",
        "/help - 显示帮助信息",
    ]

    return "\n".join(lines)


def format_unauthorized_message() -> str:
    """Format an unauthorized access message.

    Returns:
        Formatted Markdown message for unauthorized users

    Example:
        >>> msg = format_unauthorized_message()
        >>> "*未授权访问*" in msg
        True
    """
    return "\u26a0\ufe0f *未授权访问*\n\n您没有权限使用此机器人。"
