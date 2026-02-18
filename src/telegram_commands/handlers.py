"""Telegram command handlers for bot interactions.

This module provides command handler functions for the Telegram bot,
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
    # Story 9.11: 远程控制
    "create_enable_handler",
    "create_disable_handler",
    "create_mode_handler",
    "create_confirm_mode_handler",
    "create_cancel_mode_handler",
    "PendingModeChange",
]

from collections.abc import Awaitable
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Callable

from telegram import Update
from telegram.ext import Application, CommandHandler

from src.analysis import AnalysisError, LLMAnalyzer
from src.config import settings
from src.models.market import Market, MarketCategory
from src.models.prediction import PredictionResult, Recommendation
from src.models.trade import TradeMode
from src.storage.repositories import (
    MarketRepository,
    PositionRepository,
    PredictionRepository,
    StatisticsRepository,
    TradeRepository,
)
from src.telegram_commands.audit import AuditEventType, log_audit_event
from src.telegram_commands.formatters import (
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
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from telegram.ext import CallbackContext

    from src.core.state import ThreadSafeState

logger = get_logger(__name__)


def create_status_handler(
    state_manager: "ThreadSafeState",
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a status command handler with injected dependencies.

    Args:
        state_manager: ThreadSafeState instance for getting system state
        authorized_chat_id: Authorized chat ID for access control

    Returns:
        Async function that handles /status command

    Example:
        >>> handler = create_status_handler(state_manager, "123456789")
        >>> # Register with: application.add_handler(CommandHandler("status", handler))
    """

    async def status_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /status command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = update.effective_chat.id

        # Verify authorization
        if authorized_chat_id and str(chat_id) != str(authorized_chat_id):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Get current state
        snapshot = await state_manager.get_state()

        # Determine trading mode
        mode = "PAPER" if settings.trading_mode == "paper" else "LIVE"

        # Format and send status message
        message = format_status_message(
            mode=mode,
            current_capital=snapshot.current_capital,
            daily_pnl=snapshot.daily_pnl,
            open_positions=snapshot.open_positions_count,
            consecutive_losses=snapshot.consecutive_losses,
            trading_enabled=snapshot.trading_enabled,
        )

        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Status command processed for chat_id: {chat_id}")

    return status_handler


def create_help_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a help command handler.

    Args:
        authorized_chat_id: Authorized chat ID for access control

    Returns:
        Async function that handles /help command

    Example:
        >>> handler = create_help_handler("123456789")
        >>> # Register with: application.add_handler(CommandHandler("help", handler))
    """

    async def help_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /help command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = update.effective_chat.id

        # Verify authorization
        if authorized_chat_id and str(chat_id) != str(authorized_chat_id):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Send help message
        message = format_help_message()
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Help command processed for chat_id: {chat_id}")

    return help_handler


def create_positions_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a positions command handler.

    Args:
        authorized_chat_id: Authorized chat ID for access control

    Returns:
        Async function that handles /positions command

    Example:
        >>> handler = create_positions_handler("123456789")
        >>> # Register with: application.add_handler(CommandHandler("positions", handler))
    """

    async def positions_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /positions command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = update.effective_chat.id

        # Verify authorization
        if authorized_chat_id and str(chat_id) != str(authorized_chat_id):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Get open positions
        position_repo = PositionRepository()
        market_repo = MarketRepository()

        positions = await position_repo.get_open_positions()

        if not positions:
            await update.message.reply_text(
                format_positions_message([], 0.0, 0.0),
                parse_mode="Markdown",
            )
            return

        # Enrich positions with market data
        position_data: list[dict] = []
        total_exposure = 0.0
        total_pnl = 0.0

        for position in positions:
            market = await market_repo.get_market(position.market_id)
            market_title = market.title if market else position.market_id

            initial_value = position.initial_value or 0.0
            current_value = position.current_value or 0.0
            pnl = position.pnl or 0.0

            total_exposure += initial_value
            total_pnl += pnl

            position_data.append(
                {
                    "market_title": market_title,
                    "outcome": position.outcome.value,
                    "shares": position.shares,
                    "cost": initial_value,
                    "current_value": current_value,
                    "pnl": pnl,
                }
            )

        # Format and send message
        message = format_positions_message(position_data, total_exposure, total_pnl)
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Positions command processed for chat_id: {chat_id}")

    return positions_handler


def create_stats_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a stats command handler.

    Story 9.7: Telegram 命令处理 - 统计查询

    Args:
        authorized_chat_id: Authorized chat ID for access control

    Returns:
        Async function that handles /stats command

    Example:
        >>> handler = create_stats_handler("123456789")
        >>> # Register with: application.add_handler(CommandHandler("stats", handler))
    """

    async def stats_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /stats command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = update.effective_chat.id

        # Verify authorization
        if authorized_chat_id and str(chat_id) != str(authorized_chat_id):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Parse days parameter (default 7)
        days = 7
        if context.args and len(context.args) > 0:
            try:
                days = int(context.args[0])
                # Limit to 1-365 days
                days = max(1, min(365, days))
            except ValueError:
                pass  # Keep default

        # Get repositories
        stats_repo = StatisticsRepository()
        prediction_repo = PredictionRepository()

        # Determine trading mode
        mode = TradeMode.PAPER if settings.trading_mode == "paper" else TradeMode.LIVE

        # Calculate date ranges
        today = date.today()
        recent_start = today - timedelta(days=days)

        # Get overall statistics (all time)
        all_stats = await stats_repo.get_latest(mode, limit=365)

        # Calculate overall totals
        total_trades = sum(s.total_trades for s in all_stats)
        total_winning = sum(s.winning_trades for s in all_stats)
        total_losing = sum(s.losing_trades for s in all_stats)
        total_pnl = sum(s.total_pnl or 0 for s in all_stats)
        overall_win_rate = (
            total_winning / total_trades * 100 if total_trades > 0 else 0.0
        )

        # Get recent statistics
        recent_stats = await stats_repo.get_by_date_range(recent_start, today, mode)

        # Calculate recent totals
        recent_trades = sum(s.total_trades for s in recent_stats)
        recent_winning = sum(s.winning_trades for s in recent_stats)
        recent_win_rate = (
            recent_winning / recent_trades * 100 if recent_trades > 0 else 0.0
        )
        recent_pnl = sum(s.total_pnl or 0 for s in recent_stats)

        # Get prediction statistics
        total_predictions = await prediction_repo.count()
        validated_predictions = await prediction_repo.get_all_validated()

        validated_count = len(validated_predictions)
        correct_count = sum(1 for p in validated_predictions if p.is_correct)
        accuracy = correct_count / validated_count * 100 if validated_count > 0 else 0.0

        # Format and send message
        message = format_stats_message(
            total_trades=total_trades,
            total_winning=total_winning,
            total_losing=total_losing,
            win_rate=overall_win_rate,
            total_pnl=total_pnl,
            recent_trades=recent_trades,
            recent_win_rate=recent_win_rate,
            recent_pnl=recent_pnl,
            days=days,
            total_predictions=total_predictions,
            validated_count=validated_count,
            accuracy=accuracy,
        )
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Stats command processed for chat_id: {chat_id}")

    return stats_handler


def create_markets_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a markets command handler.

    Story 9.8: Telegram 命令处理 - 市场查询

    Args:
        authorized_chat_id: Authorized chat ID for access control

    Returns:
        Async function that handles /markets command

    Example:
        >>> handler = create_markets_handler("123456789")
        >>> # Register with: application.add_handler(CommandHandler("markets", handler))
    """

    async def markets_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /markets command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = update.effective_chat.id

        # Verify authorization
        if authorized_chat_id and str(chat_id) != str(authorized_chat_id):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Parse parameters
        limit = 5  # Default limit
        category: MarketCategory | None = None

        if context.args:
            for arg in context.args:
                # Try to parse as number (limit)
                try:
                    limit = int(arg)
                    # Limit range: 1-20
                    limit = max(1, min(20, limit))
                    continue
                except ValueError:
                    pass

                # Try to parse as category
                try:
                    category = MarketCategory(arg.lower())
                    continue
                except ValueError:
                    pass

        # Get repositories
        market_repo = MarketRepository()

        # Get active markets
        if category:
            markets = await market_repo.get_markets_by_category(category)
            # Filter to active only
            markets = [m for m in markets if m.resolution_status is None]
        else:
            markets = await market_repo.get_active_markets()

        # Sort by liquidity (highest first) and limit
        markets = sorted(
            markets,
            key=lambda m: m.liquidity or 0,
            reverse=True,
        )[:limit]

        # Format and send message
        message = format_markets_message(markets, category)
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Markets command processed for chat_id: {chat_id}")

    return markets_handler


def create_history_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a history command handler.

    Story 9.9: Telegram 命令处理 - 交易历史

    Args:
        authorized_chat_id: Authorized chat ID for access control

    Returns:
        Async function that handles /history command

    Example:
        >>> handler = create_history_handler("123456789")
        >>> # Register with: application.add_handler(CommandHandler("history", handler))
    """

    async def history_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /history command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = update.effective_chat.id

        # Verify authorization
        if authorized_chat_id and str(chat_id) != str(authorized_chat_id):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Parse parameters
        limit = 10  # Default limit
        mode: TradeMode | None = None

        if context.args:
            for arg in context.args:
                # Try to parse as number (limit)
                try:
                    limit = int(arg)
                    # Limit range: 1-50
                    limit = max(1, min(50, limit))
                    continue
                except ValueError:
                    pass

                # Try to parse as mode
                if arg.lower() == "paper":
                    mode = TradeMode.PAPER
                elif arg.lower() == "live":
                    mode = TradeMode.LIVE

        # Get repositories
        trade_repo = TradeRepository()
        market_repo = MarketRepository()

        # Get recent trades
        if mode:
            # Get trades filtered by mode and limit
            all_trades = await trade_repo.get_by_mode(mode)
            trades = all_trades[:limit]
        else:
            trades = await trade_repo.get_recent(limit)

        # Enrich trades with market data
        trade_data: list[dict] = []
        for trade in trades:
            market = await market_repo.get_market(trade.market_id)
            market_title = (
                market.title if market else f"Market {trade.market_id[:20]}..."
            )

            trade_data.append(
                {
                    "id": trade.id,
                    "market_id": trade.market_id,
                    "market_title": market_title,
                    "trade_type": trade.trade_type,
                    "mode": trade.mode,
                    "amount": trade.amount,
                    "price": trade.price,
                    "status": trade.status,
                    "created_at": trade.created_at,
                }
            )

        # Format and send message
        message = format_history_message([], trade_data, mode)
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"History command processed for chat_id: {chat_id}")

    return history_handler


# =============================================================================
# Story 9.10: Telegram 命令处理 - 手动触发分析
# =============================================================================

# Module-level storage for pending confirmations
# In production, consider using Redis or database for persistence
_pending_confirmations: dict[str, "PendingConfirmation"] = {}


class PendingConfirmation:
    """Pending trade confirmation data.

    Stores the state for a trade confirmation request that is awaiting
    user response via /confirm or /cancel commands.

    Attributes:
        chat_id: Chat ID where the confirmation was requested
        market: The market to be traded
        prediction: The LLM prediction result
        created_at: When the confirmation was created
        expires_at: When the confirmation expires (30 seconds)

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
        ... )
        >>> pending = PendingConfirmation("123456", market, pred)
        >>> pending.is_expired()
        False
    """

    def __init__(
        self,
        chat_id: str,
        market: Market,
        prediction: PredictionResult,
    ) -> None:
        """Initialize pending confirmation.

        Args:
            chat_id: Chat ID where the confirmation was requested
            market: The market to be traded
            prediction: The LLM prediction result
        """
        self.chat_id = chat_id
        self.market = market
        self.prediction = prediction
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=30)

    def is_expired(self) -> bool:
        """Check if the confirmation has expired.

        Returns:
            True if expired (30 seconds have passed), False otherwise
        """
        return datetime.now() > self.expires_at


def create_predict_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a predict command handler.

    Story 9.10: Telegram 命令处理 - 手动触发分析

    Args:
        authorized_chat_id: Authorized chat ID for access control

    Returns:
        Async function that handles /predict command

    Example:
        >>> handler = create_predict_handler("123456789")
        >>> # Register with: application.add_handler(CommandHandler("predict", handler))
    """

    async def predict_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /predict command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = update.effective_chat.id
        chat_id_str = str(chat_id)

        # Verify authorization
        if authorized_chat_id and chat_id_str != str(authorized_chat_id):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        market_repo = MarketRepository()

        # Parse parameters - no args shows market list
        if not context.args or len(context.args) == 0:
            markets = await market_repo.get_active_markets()
            # Limit to first 10 markets
            markets = markets[:10]
            message = format_predict_market_list(markets)
            await update.message.reply_text(message, parse_mode="Markdown")
            return

        # Get market by index or ID
        market: Market | None = None
        arg = context.args[0]

        # Try to parse as index (number)
        try:
            index = int(arg) - 1  # Convert to 0-based index
            if index < 0:
                await update.message.reply_text(
                    "❌ 无效的市场序号，请使用正整数",
                    parse_mode="Markdown",
                )
                return
            markets = await market_repo.get_active_markets()
            if index >= len(markets):
                await update.message.reply_text(
                    f"❌ 市场序号 {index + 1} 不存在",
                    parse_mode="Markdown",
                )
                return
            market = markets[index]
        except ValueError:
            # Not a number, try as market ID
            market = await market_repo.get_market(arg)
            if not market:
                await update.message.reply_text(
                    f"❌ 市场不存在: {arg}",
                    parse_mode="Markdown",
                )
                return

        # Send analyzing message
        analyzing_msg = format_analyzing_message(market)
        await update.message.reply_text(analyzing_msg, parse_mode="Markdown")

        # Execute analysis
        analyzer = LLMAnalyzer()
        try:
            result = await analyzer.analyze_market(market)

            # Check if tradeable
            is_tradeable = result.confidence >= settings.risk.min_confidence
            if result.edge is not None:
                is_tradeable = is_tradeable and result.edge >= settings.risk.min_edge
            is_tradeable = (
                is_tradeable and result.recommendation != Recommendation.NO_TRADE
            )

            if is_tradeable:
                # Store pending confirmation
                _pending_confirmations[chat_id_str] = PendingConfirmation(
                    chat_id=chat_id_str,
                    market=market,
                    prediction=result,
                )
                message = format_predict_result_with_confirm(market, result)
            else:
                message = format_predict_result_no_trade(market, result)

            await update.message.reply_text(message, parse_mode="Markdown")
            logger.info(
                f"Predict command completed for chat_id: {chat_id}, market: {market.id}"
            )

        except AnalysisError as e:
            logger.error(f"Analysis error for market {market.id}: {e}")
            await update.message.reply_text(
                f"❌ 分析失败: {e.message}",
                parse_mode="Markdown",
            )

    return predict_handler


def create_confirm_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a confirm command handler for trade confirmation.

    Story 9.10: Telegram 命令处理 - 手动触发分析

    Args:
        authorized_chat_id: Authorized chat ID for access control

    Returns:
        Async function that handles /confirm command
    """

    async def confirm_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /confirm command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = str(update.effective_chat.id)

        # Verify authorization
        if authorized_chat_id and chat_id != str(authorized_chat_id):
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Check for pending confirmation
        pending = _pending_confirmations.get(chat_id)
        if not pending:
            await update.message.reply_text(
                "❌ 没有待确认的交易。请先使用 /predict 分析市场。",
                parse_mode="Markdown",
            )
            return

        if pending.is_expired():
            del _pending_confirmations[chat_id]
            await update.message.reply_text(
                "❌ 确认已超时 (30秒)。请重新执行 /predict 分析。",
                parse_mode="Markdown",
            )
            return

        # Calculate suggested amount
        amount = settings.trading.initial_capital * settings.risk.max_single_ratio

        # Generate trade suggestion (NOT executing actual trade)
        message = format_trade_suggestion(pending.market, pending.prediction, amount)
        del _pending_confirmations[chat_id]

        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Trade confirmed for chat_id: {chat_id}")

    return confirm_handler


def create_cancel_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a cancel command handler.

    Story 9.10: Telegram 命令处理 - 手动触发分析

    Args:
        authorized_chat_id: Authorized chat ID for access control

    Returns:
        Async function that handles /cancel command
    """

    async def cancel_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /cancel command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = str(update.effective_chat.id)

        # Verify authorization
        if authorized_chat_id and chat_id != str(authorized_chat_id):
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Check for pending confirmation
        if chat_id in _pending_confirmations:
            del _pending_confirmations[chat_id]
            message = format_trade_cancelled()
        else:
            message = "没有待取消的交易。"

        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Trade cancelled for chat_id: {chat_id}")

    return cancel_handler


# =============================================================================
# Story 9.11: Telegram 命令处理 - 远程控制
# =============================================================================

# Module-level storage for pending mode changes
# In production, consider using Redis or database for persistence
_pending_mode_changes: dict[str, "PendingModeChange"] = {}


class PendingModeChange:
    """待确认的模式切换请求.

    Story 9.11: Telegram 命令处理 - 远程控制

    Stores the state for a mode change request that is awaiting
    user confirmation via /confirm live command.

    Attributes:
        chat_id: Chat ID where the confirmation was requested
        target_mode: The target mode to switch to (live or paper)
        created_at: When the confirmation was created
        expires_at: When the confirmation expires (30 seconds)

    Example:
        >>> pending = PendingModeChange("123456", "live")
        >>> pending.is_expired()
        False
    """

    def __init__(self, chat_id: str, target_mode: str) -> None:
        """Initialize pending mode change.

        Args:
            chat_id: Chat ID where the confirmation was requested
            target_mode: The target mode to switch to (live or paper)
        """
        self.chat_id = chat_id
        self.target_mode = target_mode  # "live" or "paper"
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=30)

    def is_expired(self) -> bool:
        """Check if the confirmation has expired.

        Returns:
            True if expired (30 seconds have passed), False otherwise
        """
        return datetime.now() > self.expires_at


def create_enable_handler(
    authorized_chat_id: str | None,
    state_manager: "ThreadSafeState",
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create an enable trading command handler.

    Story 9.11: Telegram 命令处理 - 远程控制

    Args:
        authorized_chat_id: Authorized chat ID for access control
        state_manager: ThreadSafeState instance for system state

    Returns:
        Async function that handles /enable command

    Example:
        >>> handler = create_enable_handler("123456789", state_manager)
        >>> # Register with: application.add_handler(CommandHandler("enable", handler))
    """

    async def enable_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /enable command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = str(update.effective_chat.id)

        # Verify authorization
        if authorized_chat_id and chat_id != str(authorized_chat_id):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Enable trading
        await state_manager.set_trading_enabled(True)

        # Log audit event
        log_audit_event(
            AuditEventType.ENABLE_TRADING,
            chat_id,
        )

        # Send confirmation
        message = format_enable_message()
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Trading enabled by chat_id: {chat_id}")

    return enable_handler


def create_disable_handler(
    authorized_chat_id: str | None,
    state_manager: "ThreadSafeState",
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a disable trading command handler.

    Story 9.11: Telegram 命令处理 - 远程控制

    Args:
        authorized_chat_id: Authorized chat ID for access control
        state_manager: ThreadSafeState instance for system state

    Returns:
        Async function that handles /disable command

    Example:
        >>> handler = create_disable_handler("123456789", state_manager)
        >>> # Register with: application.add_handler(CommandHandler("disable", handler))
    """

    async def disable_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /disable command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = str(update.effective_chat.id)

        # Verify authorization
        if authorized_chat_id and chat_id != str(authorized_chat_id):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Disable trading
        await state_manager.set_trading_enabled(False)

        # Log audit event
        log_audit_event(
            AuditEventType.DISABLE_TRADING,
            chat_id,
        )

        # Send confirmation
        message = format_disable_message()
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Trading disabled by chat_id: {chat_id}")

    return disable_handler


def create_mode_handler(
    authorized_chat_id: str | None,
    state_manager: "ThreadSafeState",
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a mode command handler.

    Story 9.11: Telegram 命令处理 - 远程控制

    Args:
        authorized_chat_id: Authorized chat ID for access control
        state_manager: ThreadSafeState instance for system state

    Returns:
        Async function that handles /mode command

    Example:
        >>> handler = create_mode_handler("123456789", state_manager)
        >>> # Register with: application.add_handler(CommandHandler("mode", handler))
    """

    async def mode_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /mode command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = str(update.effective_chat.id)

        # Verify authorization
        if authorized_chat_id and chat_id != str(authorized_chat_id):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Get current mode
        current_mode = "PAPER" if settings.trading_mode == "paper" else "LIVE"

        # No args - show current mode
        if not context.args or len(context.args) == 0:
            snapshot = await state_manager.get_state()
            message = format_mode_status_message(
                current_mode=current_mode,
                trading_enabled=snapshot.trading_enabled,
            )
            await update.message.reply_text(message, parse_mode="Markdown")
            return

        # Parse target mode
        target_mode = context.args[0].lower()

        if target_mode not in ("paper", "live"):
            await update.message.reply_text(
                "❌ 无效的模式。请使用 `paper` 或 `live`。",
                parse_mode="Markdown",
            )
            return

        # Switch to Paper mode - direct
        if target_mode == "paper":
            if current_mode == "PAPER":
                await update.message.reply_text(
                    "当前已经是 PAPER 模式。",
                    parse_mode="Markdown",
                )
                return

            await state_manager.set_mode(paper_trading=True)
            log_audit_event(
                AuditEventType.MODE_CHANGE,
                chat_id,
                {"from": current_mode, "to": "PAPER"},
            )
            message = format_mode_changed_message("LIVE", "PAPER")
            await update.message.reply_text(message, parse_mode="Markdown")
            logger.info(f"Mode changed: LIVE -> PAPER by chat_id: {chat_id}")
            return

        # Switch to Live mode - requires confirmation
        if current_mode == "LIVE":
            await update.message.reply_text(
                "当前已经是 LIVE 模式。",
                parse_mode="Markdown",
            )
            return

        # Store pending mode change
        _pending_mode_changes[chat_id] = PendingModeChange(
            chat_id=chat_id,
            target_mode="live",
        )

        message = format_mode_change_confirmation()
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Mode change to LIVE requested by chat_id: {chat_id}")

    return mode_handler


def create_confirm_mode_handler(
    authorized_chat_id: str | None,
    state_manager: "ThreadSafeState",
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a confirm mode change command handler.

    Story 9.11: Telegram 命令处理 - 远程控制

    Args:
        authorized_chat_id: Authorized chat ID for access control
        state_manager: ThreadSafeState instance for system state

    Returns:
        Async function that handles /confirm command for mode change

    Example:
        >>> handler = create_confirm_mode_handler("123456789", state_manager)
        >>> # Register with: application.add_handler(CommandHandler("confirm", handler))
    """

    async def confirm_mode_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /confirm command for mode change."""
        if not update.effective_chat or not update.message:
            return

        chat_id = str(update.effective_chat.id)

        # Verify authorization
        if authorized_chat_id and chat_id != str(authorized_chat_id):
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Check for pending mode change
        pending = _pending_mode_changes.get(chat_id)
        if not pending:
            # Not for mode change - let trade confirmation handler deal with it
            return

        if pending.is_expired():
            del _pending_mode_changes[chat_id]
            await update.message.reply_text(
                "❌ 确认已超时 (30秒)。请重新执行 /mode live。",
                parse_mode="Markdown",
            )
            return

        # Verify confirmation phrase
        if (
            not context.args
            or len(context.args) == 0
            or context.args[0].lower() != "live"
        ):
            await update.message.reply_text(
                "❌ 请输入 /confirm live 确认切换到 LIVE 模式。",
                parse_mode="Markdown",
            )
            return

        # Execute mode change
        await state_manager.set_mode(paper_trading=False)
        del _pending_mode_changes[chat_id]

        log_audit_event(
            AuditEventType.CONFIRM_MODE_CHANGE,
            chat_id,
            {"from": "PAPER", "to": "LIVE"},
        )

        message = format_mode_changed_message("PAPER", "LIVE")
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Mode change confirmed: PAPER -> LIVE by chat_id: {chat_id}")

    return confirm_mode_handler


def create_cancel_mode_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a cancel mode change command handler.

    Story 9.11: Telegram 命令处理 - 远程控制

    Args:
        authorized_chat_id: Authorized chat ID for access control

    Returns:
        Async function that handles /cancel command for mode change
    """

    async def cancel_mode_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /cancel command for mode change."""
        if not update.effective_chat or not update.message:
            return

        chat_id = str(update.effective_chat.id)

        # Verify authorization
        if authorized_chat_id and chat_id != str(authorized_chat_id):
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Check for pending mode change
        if chat_id in _pending_mode_changes:
            del _pending_mode_changes[chat_id]
            log_audit_event(
                AuditEventType.CANCEL_MODE_CHANGE,
                chat_id,
            )
            message = format_mode_change_cancelled()
            await update.message.reply_text(message, parse_mode="Markdown")
            logger.info(f"Mode change cancelled by chat_id: {chat_id}")
        # If no pending mode change, let trade cancel handler deal with it

    return cancel_mode_handler


def setup_command_handlers(
    application: Application,
    state_manager: "ThreadSafeState",
    authorized_chat_id: str | None = None,
) -> None:
    """Setup all command handlers for the Telegram bot.

    This function creates and registers all command handlers with the
    Telegram Application instance.

    Args:
        application: Telegram Application instance
        state_manager: ThreadSafeState instance for system state
        authorized_chat_id: Optional chat ID for access control

    Example:
        >>> from telegram.ext import Application
        >>> app = Application.builder().token("TOKEN").build()
        >>> setup_command_handlers(app, state_manager, "123456789")
    """
    # Create handlers with injected dependencies
    status_handler = create_status_handler(state_manager, authorized_chat_id)
    help_handler = create_help_handler(authorized_chat_id)
    positions_handler = create_positions_handler(authorized_chat_id)
    stats_handler = create_stats_handler(authorized_chat_id)
    markets_handler = create_markets_handler(authorized_chat_id)
    history_handler = create_history_handler(authorized_chat_id)
    predict_handler = create_predict_handler(authorized_chat_id)
    confirm_handler = create_confirm_handler(authorized_chat_id)
    cancel_handler = create_cancel_handler(authorized_chat_id)

    # Story 9.11: Remote control handlers
    enable_handler = create_enable_handler(authorized_chat_id, state_manager)
    disable_handler = create_disable_handler(authorized_chat_id, state_manager)
    mode_handler = create_mode_handler(authorized_chat_id, state_manager)
    confirm_mode_handler = create_confirm_mode_handler(
        authorized_chat_id, state_manager
    )
    cancel_mode_handler = create_cancel_mode_handler(authorized_chat_id)

    # Register handlers
    application.add_handler(CommandHandler("status", status_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("help", help_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("positions", positions_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("stats", stats_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("markets", markets_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("history", history_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("predict", predict_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("confirm", confirm_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("cancel", cancel_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("confirm", confirm_mode_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("cancel", cancel_mode_handler))  # type: ignore[arg-type]

    # Story 9.11: Control handlers
    application.add_handler(CommandHandler("enable", enable_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("disable", disable_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("mode", mode_handler))  # type: ignore[arg-type]

    logger.info(
        "Command handlers registered: /status, /help, /positions, /stats, "
        "/markets, /history, /predict, /confirm, /cancel, "
        "/enable, /disable, /mode"
    )
