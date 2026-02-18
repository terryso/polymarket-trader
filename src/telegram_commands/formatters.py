"""Message formatters for Telegram commands.

This module provides formatting functions for Telegram command responses.

Story 9.5: Telegram 命令处理 - 状态查询
Story 9.6: Telegram 命令处理 - 持仓查询
Story 9.7: Telegram 命令处理 - 统计查询
Story 9.8: Telegram 命令处理 - 市场查询
Story 9.9: Telegram 命令处理 - 交易历史
Story 9.10: Telegram 命令处理 - 手动触发分析
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import Market, MarketCategory, Trade, TradeMode
    from src.models.prediction import PredictionResult

__all__ = [
    "format_status_message",
    "format_help_message",
    "format_unauthorized_message",
    "format_positions_message",
    "format_stats_message",
    "format_markets_message",
    "format_history_message",
    "_format_relative_time",
    # Story 9.10: 手动触发分析
    "format_predict_market_list",
    "format_analyzing_message",
    "format_predict_result_with_confirm",
    "format_predict_result_no_trade",
    "format_trade_suggestion",
    "format_trade_cancelled",
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
        "/stats [days] - 查看交易统计",
        "/markets [n] [category] - 查看活跃市场",
        "/history [n] [paper|live] - 查看交易历史",
        "/predict [序号|市场ID] - 手动触发市场分析",
        "/confirm - 确认交易建议",
        "/cancel - 取消交易建议",
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


def _format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time string.

    Story 9.9: Telegram 命令处理 - 交易历史

    Args:
        dt: Datetime to format

    Returns:
        Human-readable relative time string (e.g., "2小时前", "1天前")

    Example:
        >>> from datetime import datetime, timedelta
        >>> _format_relative_time(datetime.now())
        '刚刚'
        >>> "小时前" in _format_relative_time(datetime.now() - timedelta(hours=5))
        True
    """
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    diff = now - dt

    if diff < timedelta(minutes=1):
        return "刚刚"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes}分钟前"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours}小时前"
    elif diff < timedelta(days=30):
        days = diff.days
        return f"{days}天前"
    else:
        return dt.strftime("%Y-%m-%d")


def format_history_message(
    trades: list["Trade"],
    trade_data: list[dict] | None = None,
    mode: "TradeMode | None" = None,
) -> str:
    """Format a trade history message.

    Story 9.9: Telegram 命令处理 - 交易历史

    Args:
        trades: List of Trade models to display (optional if trade_data provided)
        trade_data: List of dicts with enriched trade data (market_title, etc.)
        mode: Optional mode filter that was applied

    Returns:
        Formatted Markdown message

    Example:
        >>> from src.models import Trade, TradeType, TradeMode, TradeStatus
        >>> from datetime import datetime
        >>> trades = [Trade(
        ...     id=1,
        ...     market_id="m1",
        ...     trade_type=TradeType.BUY_YES,
        ...     mode=TradeMode.PAPER,
        ...     amount=10.0,
        ...     price=0.65,
        ...     status=TradeStatus.FILLED,
        ...     created_at=datetime.now()
        ... )]
        >>> msg = format_history_message(trades)
        >>> "*最近交易*" in msg
        True
    """
    # If trade_data is provided, use it; otherwise convert trades
    if trade_data is None:
        trade_data = []
        for trade in trades:
            trade_data.append(
                {
                    "id": trade.id,
                    "market_id": trade.market_id,
                    "market_title": f"Market {trade.market_id[:20]}...",
                    "trade_type": trade.trade_type,
                    "mode": trade.mode,
                    "amount": trade.amount,
                    "price": trade.price,
                    "status": trade.status,
                    "created_at": trade.created_at,
                }
            )

    if not trade_data:
        mode_text = f" ({mode.value})" if mode else ""
        return f"\U0001f4dc *最近交易*{mode_text}\n\n暂无交易记录"

    # Header
    mode_text = f" ({mode.value})" if mode else ""
    lines = [
        f"\U0001f4dc *最近交易*{mode_text} ({len(trade_data)} 笔)",
        "",
    ]

    # Format each trade
    for i, t in enumerate(trade_data, 1):
        # Trade type emoji and text
        trade_type = t.get("trade_type")
        if trade_type is None:
            type_emoji = "\U0001f4b0"  # Money bag
            type_text = "TRADE"
        elif hasattr(trade_type, "value"):
            type_val = trade_type.value
            if type_val == "BUY_YES":
                type_emoji = "\U0001f7e2"  # Green circle for YES
                type_text = "BUY YES"
            elif type_val == "BUY_NO":
                type_emoji = "\U0001f534"  # Red circle for NO
                type_text = "BUY NO"
            else:  # SELL
                type_emoji = "\U0001f4b8"  # Money with wings
                type_text = "SELL"
        else:
            type_emoji = "\U0001f4b0"
            type_text = str(trade_type)

        # Format status
        status = t.get("status")
        if status is None:
            status_text = "\U00002753 处理中"  # Question mark
        elif hasattr(status, "value"):
            status_val = status.value
            if status_val == "FILLED":
                status_text = "\U00002705 持仓中"  # Check mark - in position
            elif status_val == "CANCELLED":
                status_text = "\U0000274c 已取消"  # X mark
            else:
                status_text = "\U000023f3 处理中"  # Hourglass
        else:
            status_text = str(status)

        # Format amount and price
        amount_str = f"${t['amount']:.2f}"
        price_str = f"{t['price']:.2f}"

        # Format time
        time_str = ""
        created_at = t.get("created_at")
        if created_at:
            time_str = _format_relative_time(created_at)

        # Market title
        market_title = t.get("market_title", f"Market {t.get('market_id', 'unknown')}")

        lines.extend(
            [
                f"{i}. {type_emoji} *{type_text}* {market_title}",
                f"   {amount_str} @ {price_str} | {time_str}",
                f"   状态: {status_text}",
                "",
            ]
        )

    return "\n".join(lines)


# =============================================================================
# Story 9.10: Telegram 命令处理 - 手动触发分析
# =============================================================================


def format_predict_market_list(markets: list["Market"]) -> str:
    """Format a market list for predict command.

    Args:
        markets: List of Market models to display

    Returns:
        Formatted Markdown message

    Example:
        >>> from src.models import Market
        >>> markets = [Market(id="1", title="Test", yes_price=0.5, liquidity=1000)]
        >>> msg = format_predict_market_list(markets)
        >>> "*选择市场分析*" in msg
        True
    """
    if not markets:
        return "\U0001f9e0 *选择市场分析*\n\n暂无活跃市场"

    lines = [
        "\U0001f9e0 *选择市场分析*",
        "",
    ]

    for i, market in enumerate(markets, 1):
        # Format price
        price_str = ""
        if market.yes_price is not None:
            price_str = f"YES: {market.yes_price:.2f}"
        elif market.no_price is not None:
            price_str = f"NO: {market.no_price:.2f}"

        # Format liquidity
        liquidity_str = ""
        if market.liquidity is not None:
            if market.liquidity >= 1000:
                liquidity_str = f"${market.liquidity / 1000:.0f}k"
            else:
                liquidity_str = f"${market.liquidity:.0f}"

        # Truncate long titles
        title = market.title[:50] + "..." if len(market.title) > 50 else market.title

        lines.extend(
            [
                f"{i}. *{title}*",
                f"   {price_str} | 流动性: {liquidity_str}",
                "",
            ]
        )

    lines.append("回复 `/predict <序号>` 或 `/predict <市场ID>` 开始分析")

    return "\n".join(lines)


def format_analyzing_message(market: "Market") -> str:
    """Format analyzing in progress message.

    Args:
        market: Market being analyzed

    Returns:
        Formatted Markdown message

    Example:
        >>> from src.models import Market
        >>> market = Market(id="1", title="Test", yes_price=0.5)
        >>> msg = format_analyzing_message(market)
        >>> "*分析中...*" in msg
        True
    """
    return "\n".join(
        [
            "\U0001f9e0 *分析中...*",
            f"市场: {market.title}",
            "请稍候，LLM 正在分析...",
        ]
    )


def format_predict_result_with_confirm(
    market: "Market",
    prediction: "PredictionResult",
) -> str:
    """Format prediction result with trade confirmation.

    Args:
        market: Analyzed market
        prediction: LLM prediction result

    Returns:
        Formatted Markdown message

    Example:
        >>> from src.models import Market
        >>> from src.models.prediction import PredictionResult, Recommendation
        >>> market = Market(id="1", title="Test", yes_price=0.5)
        >>> pred = PredictionResult(
        ...     predicted_probability=0.8,
        ...     confidence=0.85,
        ...     reasoning="Test",
        ...     key_assumptions=[],
        ...     recommendation=Recommendation.BUY_YES,
        ...     edge=0.15
        ... )
        >>> msg = format_predict_result_with_confirm(market, pred)
        >>> "*市场分析完成*" in msg
        True
    """
    # Format recommendation
    from src.models.prediction import Recommendation

    if prediction.recommendation == Recommendation.BUY_YES:
        rec_emoji = "\U0001f7e2"  # Green circle
        rec_text = "BUY YES"
    elif prediction.recommendation == Recommendation.BUY_NO:
        rec_emoji = "\U0001f534"  # Red circle
        rec_text = "BUY NO"
    else:
        rec_emoji = "\U000023f9"  # Stop button
        rec_text = "NO_TRADE"

    # Format price
    price_str = f"YES {market.yes_price:.2f}" if market.yes_price else "N/A"

    lines = [
        "\U0001f9e0 *市场分析完成*",
        "",
        f"市场: {market.title}",
        f"市场价格: {price_str}",
        f"预测概率: {prediction.predicted_probability:.0%}",
        f"置信度: {prediction.confidence:.0%}",
    ]

    if prediction.edge is not None:
        lines.append(f"Edge: {prediction.edge:.0%}")

    lines.extend(
        [
            "",
            f"建议: {rec_emoji} *{rec_text}*",
            "",
            "是否执行交易？",
            "回复 /confirm 确认 或 /cancel 取消",
        ]
    )

    return "\n".join(lines)


def format_predict_result_no_trade(
    market: "Market",
    prediction: "PredictionResult",
) -> str:
    """Format prediction result when not tradeable.

    Args:
        market: Analyzed market
        prediction: LLM prediction result

    Returns:
        Formatted Markdown message

    Example:
        >>> from src.models import Market
        >>> from src.models.prediction import PredictionResult, Recommendation
        >>> market = Market(id="1", title="Test", yes_price=0.5)
        >>> pred = PredictionResult(
        ...     predicted_probability=0.5,
        ...     confidence=0.6,
        ...     reasoning="Test",
        ...     key_assumptions=[],
        ...     recommendation=Recommendation.NO_TRADE,
        ...     edge=0.05
        ... )
        >>> msg = format_predict_result_no_trade(market, pred)
        >>> "NO_TRADE" in msg
        True
    """
    lines = [
        "\U0001f9e0 *市场分析完成*",
        "",
        f"市场: {market.title}",
        f"预测概率: {prediction.predicted_probability:.0%}",
        f"置信度: {prediction.confidence:.0%}",
    ]

    if prediction.edge is not None:
        lines.append(f"Edge: {prediction.edge:.0%}")

    lines.extend(
        [
            "",
            "建议: NO_TRADE",
            "",
            "_(置信度或 Edge 未达到交易门槛)_",
        ]
    )

    return "\n".join(lines)


def format_trade_suggestion(
    market: "Market",
    prediction: "PredictionResult",
    amount: float,
) -> str:
    """Format trade suggestion after confirmation.

    Note: This only shows the suggestion, does NOT execute actual trade.

    Args:
        market: Market to trade
        prediction: LLM prediction result
        amount: Suggested trade amount in USD

    Returns:
        Formatted Markdown message

    Example:
        >>> from src.models import Market
        >>> from src.models.prediction import PredictionResult, Recommendation
        >>> market = Market(id="1", title="Test", yes_price=0.65)
        >>> pred = PredictionResult(
        ...     predicted_probability=0.8,
        ...     confidence=0.85,
        ...     reasoning="Test",
        ...     key_assumptions=[],
        ...     recommendation=Recommendation.BUY_YES,
        ...     edge=0.15
        ... )
        >>> msg = format_trade_suggestion(market, pred, 40.0)
        >>> "*交易建议*" in msg
        True
    """
    from src.models.prediction import Recommendation

    if prediction.recommendation == Recommendation.BUY_YES:
        direction = "BUY YES"
        price = market.yes_price or 0.5
    else:
        direction = "BUY NO"
        price = market.no_price or (1 - (market.yes_price or 0.5))

    shares = amount / price if price > 0 else 0

    lines = [
        "\U0001f4b0 *交易建议*",
        "",
        f"市场: {market.title}",
        f"方向: {direction}",
        f"建议金额: ${amount:.2f}",
        f"价格: {price:.2f}",
        f"份额: {shares:.2f}",
        "",
        "_注意: 这是手动触发的分析建议。_",
        "_实际交易需要 Paper Trading 或 Live 模式启用。_",
    ]

    return "\n".join(lines)


def format_trade_cancelled() -> str:
    """Format trade cancelled message.

    Returns:
        Formatted Markdown message

    Example:
        >>> msg = format_trade_cancelled()
        >>> "*交易已取消*" in msg
        True
    """
    return "\U0000274c *交易已取消*"
