"""Message formatters for Telegram commands.

This module provides formatting functions for Telegram command responses.

Story 9.5: Telegram 命令处理 - 状态查询
Story 9.6: Telegram 命令处理 - 持仓查询
Story 9.7: Telegram 命令处理 - 统计查询
Story 9.8: Telegram 命令处理 - 市场查询
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import Market, MarketCategory

__all__ = [
    "format_status_message",
    "format_help_message",
    "format_unauthorized_message",
    "format_positions_message",
    "format_stats_message",
    "format_markets_message",
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
        "/positions - 查看当前持仓",
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


def format_positions_message(
    position_data: list[dict],
    total_exposure: float,
    total_pnl: float,
) -> str:
    """Format a positions message.

    Args:
        position_data: List of dicts with market_title, outcome, shares,
                       cost, current_value, pnl
        total_exposure: Total initial value of all positions
        total_pnl: Total PnL of all positions

    Returns:
        Formatted Markdown message

    Example:
        >>> msg = format_positions_message(
        ...     [{"market_title": "Test", "outcome": "YES", "shares": 100.0,
        ...       "cost": 50.0, "current_value": 60.0, "pnl": 10.0}],
        ...     50.0,
        ...     10.0
        ... )
        >>> "*当前持仓*" in msg
        True
    """
    if not position_data:
        return "\U0001f4cd *当前持仓*\n\n暂无持仓"

    lines = ["\U0001f4cd *当前持仓*"]

    for i, pos in enumerate(position_data, 1):
        # Format PnL with sign
        pnl = pos["pnl"]
        pnl_sign = "+" if pnl >= 0 else ""
        pnl_pct = (pnl / pos["cost"] * 100) if pos["cost"] > 0 else 0.0

        lines.extend(
            [
                "",
                f"{i}. *{pos['market_title']}*",
                f"   方向: {pos['outcome']} | 份额: {pos['shares']:.2f}",
                f"   成本: ${pos['cost']:.2f} | 现值: ${pos['current_value']:.2f}",
                f"   盈亏: {pnl_sign}${pnl:.2f} ({pnl_sign}{pnl_pct:.0f}%)",
            ]
        )

    # Format totals
    total_pnl_sign = "+" if total_pnl >= 0 else ""
    lines.extend(
        [
            "",
            f"*总风险敞口: ${total_exposure:.2f}*",
            f"*总盈亏: {total_pnl_sign}${total_pnl:.2f}*",
        ]
    )

    return "\n".join(lines)


def format_stats_message(
    total_trades: int,
    total_winning: int,
    total_losing: int,
    win_rate: float,
    total_pnl: float,
    recent_trades: int,
    recent_win_rate: float,
    recent_pnl: float,
    days: int,
    total_predictions: int,
    validated_count: int,
    accuracy: float,
) -> str:
    """Format a trading statistics message.

    Story 9.7: Telegram 命令处理 - 统计查询

    Args:
        total_trades: Total number of trades
        total_winning: Number of winning trades
        total_losing: Number of losing trades
        win_rate: Win rate percentage
        total_pnl: Total profit/loss
        recent_trades: Number of recent trades
        recent_win_rate: Recent win rate percentage
        recent_pnl: Recent profit/loss
        days: Number of days for recent period
        total_predictions: Total predictions count
        validated_count: Validated predictions count
        accuracy: Prediction accuracy percentage

    Returns:
        Formatted Markdown message

    Example:
        >>> msg = format_stats_message(
        ...     total_trades=25, total_winning=15, total_losing=10,
        ...     win_rate=60.0, total_pnl=45.20,
        ...     recent_trades=8, recent_win_rate=75.0, recent_pnl=18.50,
        ...     days=7, total_predictions=30, validated_count=20, accuracy=70.0
        ... )
        >>> "*交易统计*" in msg
        True
    """
    # Format PnL with sign
    pnl_sign = "+" if total_pnl >= 0 else ""
    recent_pnl_sign = "+" if recent_pnl >= 0 else ""

    lines = [
        "\U0001f4c8 *交易统计*",  # chart_increasing emoji
        "",
        "*总体表现*",
        f"总交易: {total_trades}",
        f"胜: {total_winning} | 负: {total_losing}",
        f"胜率: {win_rate:.0f}%",
        f"总盈亏: {pnl_sign}${total_pnl:.2f}",
        "",
        f"*近期表现 ({days}天)*",
        f"交易: {recent_trades}",
        f"胜率: {recent_win_rate:.0f}%",
        f"盈亏: {recent_pnl_sign}${recent_pnl:.2f}",
        "",
        "*LLM 预测*",
        f"总预测: {total_predictions}",
        f"已验证: {validated_count}",
        f"准确率: {accuracy:.0f}%",
    ]

    return "\n".join(lines)


def format_markets_message(
    markets: list["Market"],
    category: "MarketCategory | None" = None,
) -> str:
    """Format an active markets message.

    Story 9.8: Telegram 命令处理 - 市场查询

    Args:
        markets: List of Market models to display
        category: Optional category filter that was applied

    Returns:
        Formatted Markdown message

    Example:
        >>> from src.models import Market, MarketCategory
        >>> markets = [Market(id="1", title="Test", yes_price=0.5, liquidity=1000)]
        >>> msg = format_markets_message(markets)
        >>> "*活跃市场*" in msg
        True
    """
    if not markets:
        category_text = f" ({category.value})" if category else ""
        return f"\U0001f3af *活跃市场*{category_text}\n\n暂无活跃市场"

    # Header
    category_text = f" ({category.value})" if category else ""
    lines = [
        f"\U0001f3af *活跃市场*{category_text} ({len(markets)} 个)",
        "",
    ]

    # Format each market
    for i, market in enumerate(markets, 1):
        # Truncate long titles (max 50 chars)
        title = market.title[:50] + "..." if len(market.title) > 50 else market.title

        # Format price
        price_str = (
            f"YES {market.yes_price:.2f}" if market.yes_price is not None else "N/A"
        )

        # Format liquidity (convert to K format for readability)
        if market.liquidity is not None:
            if market.liquidity >= 1000:
                liquidity_str = f"${market.liquidity / 1000:.0f}k"
            else:
                liquidity_str = f"${market.liquidity:.0f}"
        else:
            liquidity_str = "N/A"

        # Format deadline
        if market.deadline:
            deadline_str = market.deadline.strftime("%Y-%m-%d")
        else:
            deadline_str = "N/A"

        lines.extend(
            [
                f"{i}. *{title}*",
                f"   价格: {price_str} | 流动性: {liquidity_str}",
                f"   截止: {deadline_str}",
                "",
            ]
        )

    return "\n".join(lines)
