"""Telegram Bot API client for notifications and remote control.

This module provides a typed interface to the Telegram Bot API,
using python-telegram-bot library (v20+).

Story 9.1: Telegram Bot 配置与初始化

Usage:
    from src.api import TelegramClient

    # Async context manager
    async with TelegramClient() as client:
        # Verify connection
        me = await client.get_me()
        print(f"Connected as: {me.username}")

    # Or manually manage lifecycle
    client = TelegramClient()
    await client.initialize()
    try:
        me = await client.get_me()
    finally:
        await client.shutdown()
"""

from __future__ import annotations

__all__ = ["TelegramClient"]

from typing import Any

from telegram import Bot, User
from telegram.error import (
    InvalidToken,
)
from telegram.error import NetworkError as TelegramNetworkError
from telegram.error import (
    TelegramError,
)
from telegram.ext import Application

from src.config import settings
from src.exceptions import ConfigurationError, NetworkError
from src.utils.logger import get_logger

# Emoji mappings for Telegram operations
TELEGRAM_EMOJIS = {
    "success": "\u2705",  # Check mark
    "warning": "\u26a0\ufe0f",  # Warning sign
    "error": "\u274c",  # X mark
    "network": "\U0001f310",  # Globe
}


class TelegramClient:
    """Telegram Bot client with async support.

    Provides methods to interact with Telegram Bot API for
    notifications and remote commands.

    Attributes:
        _application: The underlying Application instance
        _bot: The Bot instance for direct API calls
        _token: The bot token (masked in logs)
        _chat_id: Authorized user Chat ID
        _enabled: Whether Telegram features are enabled

    Example:
        >>> async with TelegramClient() as client:
        ...     me = await client.get_me()
        ...     print(f"Bot: @{me.username}")
    """

    def __init__(self) -> None:
        """Initialize the Telegram client with settings from config."""
        self._logger = get_logger(__name__)

        # Load configuration
        self._token = settings.telegram.bot_token
        self._chat_id = settings.telegram.chat_id
        self._enabled = settings.telegram.enabled

        # Log initialization (with masked token)
        self._logger.info(
            f"{TELEGRAM_EMOJIS['network']} Initializing Telegram client "
            f"(enabled={self._enabled}, token={self._mask_token(self._token or '')})"
        )

        # Initialize application (deferred until initialize())
        self._application: Application | None = None
        self._bot: Bot | None = None

    def _mask_token(self, token: str) -> str:
        """Mask bot token for logging (show only first/last 4 chars).

        Args:
            token: The bot token to mask

        Returns:
            Masked token (e.g., "1234****5678")
        """
        if not token:
            return "[NOT_SET]"
        if len(token) <= 8:
            return "****"
        return f"{token[:4]}****{token[-4:]}"

    async def initialize(self) -> None:
        """Initialize the Telegram application.

        Raises:
            ConfigurationError: If token is invalid
            NetworkError: If connection fails
        """
        if not self._enabled or not self._token:
            self._logger.warning(
                f"{TELEGRAM_EMOJIS['warning']} Telegram client not enabled or token not set"
            )
            return

        try:
            self._application = Application.builder().token(self._token).build()
            await self._application.initialize()
            self._bot = self._application.bot

            self._logger.info(
                f"{TELEGRAM_EMOJIS['success']} Telegram client initialized"
            )

        except InvalidToken as e:
            raise ConfigurationError(
                message=f"Invalid Telegram bot token: {self._mask_token(self._token)}",
                config_key="TELEGRAM_BOT_TOKEN",
            ) from e
        except TelegramNetworkError as e:
            raise NetworkError(
                message=f"Telegram network error: {e}",
                endpoint="initialize",
            ) from e
        except TelegramError as e:
            raise NetworkError(
                message=f"Telegram API error: {e}",
                endpoint="initialize",
            ) from e

    async def shutdown(self) -> None:
        """Shutdown the Telegram application."""
        if self._application:
            try:
                await self._application.shutdown()
                self._logger.info(
                    f"{TELEGRAM_EMOJIS['success']} Telegram client shutdown"
                )
            except Exception as e:
                self._logger.error(
                    f"{TELEGRAM_EMOJIS['error']} Error during Telegram shutdown: {e}"
                )
            finally:
                self._application = None
                self._bot = None

    async def __aenter__(self) -> "TelegramClient":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.shutdown()

    @property
    def is_enabled(self) -> bool:
        """Check if Telegram client is enabled and initialized."""
        return self._enabled and self._bot is not None

    @property
    def authorized_chat_id(self) -> str | None:
        """Get the authorized Chat ID for commands."""
        return self._chat_id

    async def get_me(self) -> User | None:
        """Get bot information to verify connection.

        Returns:
            Bot User object if successful, None if not enabled

        Raises:
            NetworkError: If API call fails
            ConfigurationError: If client not initialized
        """
        if not self.is_enabled or not self._bot:
            self._logger.warning(
                f"{TELEGRAM_EMOJIS['warning']} Telegram client not enabled or not initialized"
            )
            return None

        try:
            me = await self._bot.get_me()
            self._logger.info(
                f"{TELEGRAM_EMOJIS['success']} Telegram bot verified: "
                f"@{me.username} ({me.first_name})"
            )
            return me

        except TelegramNetworkError as e:
            raise NetworkError(
                message=f"Telegram network error: {e}",
                endpoint="get_me",
            ) from e
        except TelegramError as e:
            raise NetworkError(
                message=f"Telegram API error: {e}",
                endpoint="get_me",
            ) from e

    def is_authorized_chat(self, chat_id: int | str) -> bool:
        """Check if a chat ID is authorized.

        Args:
            chat_id: The chat ID to check

        Returns:
            True if authorized (or if no chat_id restriction), False otherwise
        """
        if not self._chat_id:
            # No restriction configured
            return True
        return str(chat_id) == str(self._chat_id)
