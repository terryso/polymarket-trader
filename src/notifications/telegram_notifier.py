"""Telegram notification sender for trade and system events.

This module provides the TelegramNotifier class for sending
formatted notifications to Telegram.

Story 9.2: 通知消息发送

Usage:
    from src.notifications import TelegramNotifier
    from src.api import TelegramClient

    # With dependency injection
    async with TelegramClient() as client:
        notifier = TelegramNotifier(client)

        # Send trade notification
        await notifier.send_trade_notification(trade, market)

        # Send analysis notification
        await notifier.send_analysis_notification(prediction, market)
"""

from __future__ import annotations

__all__ = ["TelegramNotifier"]

from datetime import datetime
from typing import TYPE_CHECKING

from src.config import settings
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.api.telegram import TelegramClient
    from src.models.market import Market
    from src.models.prediction import PredictionResult
    from src.models.trade import Trade


class TelegramNotifier:
    """Telegram notification sender.

    Provides methods to send formatted notifications for
    trades, analysis results, errors, and system events.

    Attributes:
        _client: TelegramClient instance for sending messages
        _logger: Logger instance
        _enabled: Whether notifications are enabled

    Example:
        >>> async with TelegramClient() as client:
        ...     notifier = TelegramNotifier(client)
        ...     await notifier.send_trade_notification(trade, market)
    """

    def __init__(self, client: "TelegramClient") -> None:
        """Initialize the notifier with a Telegram client.

        Args:
            client: Initialized TelegramClient instance
        """
        self._client = client
        self._logger = get_logger(__name__)
        self._enabled = client.is_enabled and settings.telegram.enabled

        if not self._enabled:
            self._logger.info("TelegramNotifier initialized (disabled)")
        else:
            self._logger.info("TelegramNotifier initialized (enabled)")

    async def send_message(
        self,
        text: str,
        parse_mode: str = "Markdown",
    ) -> bool:
        """Send a message to the configured chat.

        Args:
            text: Message text (Markdown formatted)
            parse_mode: Parse mode (default: Markdown)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self._enabled:
            return False

        try:
            # Get chat_id from client
            chat_id = self._client.authorized_chat_id
            if not chat_id:
                self._logger.warning("No chat_id configured, skipping notification")
                return False

            # Get bot instance
            bot = self._client._bot
            if not bot:
                self._logger.warning("Bot not initialized, skipping notification")
                return False

            # Send via bot
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
            )
            self._logger.debug(f"Message sent: {text[:50]}...")
            return True

        except Exception as e:
            self._logger.error(f"Failed to send message: {e}")
            return False

    async def send_trade_notification(
        self,
        trade: "Trade",
        market: "Market",
    ) -> bool:
        """Send a trade execution notification.

        Args:
            trade: The executed trade
            market: The market for the trade

        Returns:
            True if sent successfully, False otherwise
        """
        message = self._format_trade_message(trade, market)
        return await self.send_message(message)

    async def send_analysis_notification(
        self,
        prediction: "PredictionResult",
        market: "Market",
    ) -> bool:
        """Send an LLM analysis result notification.

        Args:
            prediction: The LLM prediction result
            market: The analyzed market

        Returns:
            True if sent successfully, False otherwise
        """
        message = self._format_analysis_message(prediction, market)
        return await self.send_message(message)

    async def send_error_notification(
        self,
        error: Exception | str,
    ) -> bool:
        """Send an error alert notification.

        Args:
            error: The error exception or message

        Returns:
            True if sent successfully, False otherwise
        """
        message = self._format_error_message(error)
        return await self.send_message(message)

    async def send_system_notification(
        self,
        event: str,
        details: dict | None = None,
    ) -> bool:
        """Send a system event notification.

        Args:
            event: Event name (e.g., "startup", "shutdown")
            details: Optional event details

        Returns:
            True if sent successfully, False otherwise
        """
        message = self._format_system_message(event, details)
        return await self.send_message(message)

    def _format_trade_message(
        self,
        trade: "Trade",
        market: "Market",
    ) -> str:
        """Format a trade notification message.

        Args:
            trade: The trade to format
            market: The market for the trade

        Returns:
            Formatted Markdown message
        """
        status_emoji = "\u2705" if trade.status.value == "FILLED" else "\u274c"

        lines = [
            "\U0001f4b0 *交易执行*",
            f"市场: {market.title}",
            f"方向: {trade.trade_type.value}",
            f"金额: ${trade.amount:.2f}",
            f"价格: {trade.price:.4f}",
        ]

        if trade.shares:
            lines.append(f"份额: {trade.shares:.2f}")

        lines.append(f"状态: {status_emoji} {trade.status.value}")

        return "\n".join(lines)

    def _format_analysis_message(
        self,
        prediction: "PredictionResult",
        market: "Market",
    ) -> str:
        """Format an analysis notification message.

        Args:
            prediction: The prediction to format
            market: The analyzed market

        Returns:
            Formatted Markdown message
        """
        yes_price = market.yes_price or 0.5
        direction = "YES" if prediction.recommendation.value == "BUY_YES" else "NO"

        lines = [
            "\U0001f9e0 *市场分析*",
            f"市场: {market.title}",
            f"市场价格: YES {yes_price:.2f}",
            f"预测概率: {direction} {prediction.predicted_probability:.2f}",
            f"置信度: {prediction.confidence:.0%}",
        ]

        if prediction.edge is not None:
            lines.append(f"Edge: {prediction.edge:.0%}")

        lines.append(f"建议: {prediction.recommendation.value}")

        # Add key assumptions (max 3)
        if prediction.key_assumptions:
            lines.append("")
            lines.append("*关键假设:*")
            for assumption in prediction.key_assumptions[:3]:
                lines.append(f"- {assumption}")

        return "\n".join(lines)

    def _format_error_message(
        self,
        error: Exception | str,
    ) -> str:
        """Format an error notification message.

        Args:
            error: The error to format

        Returns:
            Formatted Markdown message
        """
        error_type = type(error).__name__ if isinstance(error, Exception) else "Error"
        error_msg = str(error)

        lines = [
            "\u274c *错误告警*",
            f"类型: {error_type}",
            f"信息: {error_msg[:200]}",  # Truncate long messages
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        return "\n".join(lines)

    def _format_system_message(
        self,
        event: str,
        details: dict | None = None,
    ) -> str:
        """Format a system event notification message.

        Args:
            event: Event name
            details: Optional event details

        Returns:
            Formatted Markdown message
        """
        lines = [
            "\u2139\ufe0f *系统事件*",
            f"事件: {event}",
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        if details:
            lines.append("")
            lines.append("*详情:*")
            for key, value in details.items():
                lines.append(f"- {key}: {value}")

        return "\n".join(lines)
