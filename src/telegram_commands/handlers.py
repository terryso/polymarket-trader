"""Telegram command handlers for bot interactions.

This module provides command handler functions for the Telegram bot,
implementing /status, /help, /positions, /stats, and /markets commands.

Story 9.5: Telegram 命令处理 - 状态查询
Story 9.6: Telegram 命令处理 - 持仓查询
Story 9.7: Telegram 命令处理 - 统计查询
Story 9.8: Telegram 命令处理 - 市场查询

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
]

from collections.abc import Awaitable
from datetime import date, timedelta
from typing import TYPE_CHECKING, Callable

from telegram import Update
from telegram.ext import Application, CommandHandler

from src.config import settings
from src.models.market import MarketCategory
from src.models.trade import TradeMode
from src.storage.repositories import (
    MarketRepository,
    PositionRepository,
    PredictionRepository,
    StatisticsRepository,
)
from src.telegram_commands.formatters import (
    format_help_message,
    format_markets_message,
    format_positions_message,
    format_stats_message,
    format_status_message,
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

    # Register handlers
    application.add_handler(CommandHandler("status", status_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("help", help_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("positions", positions_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("stats", stats_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("markets", markets_handler))  # type: ignore[arg-type]

    logger.info(
        "Command handlers registered: /status, /help, /positions, /stats, /markets"
    )
