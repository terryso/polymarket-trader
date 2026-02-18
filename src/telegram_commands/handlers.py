"""Telegram command handlers for bot interactions.

This module provides command handler functions for the Telegram bot,
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
]

from collections.abc import Awaitable
from typing import TYPE_CHECKING, Callable

from telegram import Update
from telegram.ext import Application, CommandHandler

from src.config import settings
from src.storage.repositories import MarketRepository, PositionRepository
from src.telegram_commands.formatters import (
    format_help_message,
    format_positions_message,
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

    # Register handlers
    application.add_handler(CommandHandler("status", status_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("help", help_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("positions", positions_handler))  # type: ignore[arg-type]

    logger.info("Command handlers registered: /status, /help, /positions")
