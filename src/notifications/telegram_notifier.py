"""Telegram notification sender for trade and system events.

This module provides the TelegramNotifier class for sending
formatted notifications to Telegram.

Story 9.2: 通知消息发送
Story 9.3: 交易事件通知集成
Story 9.12: 消息队列与限流

Usage:
    from src.notifications import TelegramNotifier
    from src.api import TelegramClient

    # With dependency injection
    async with TelegramClient() as client:
        notifier = TelegramNotifier(client)

        # Start the message queue (optional, enables rate limiting)
        await notifier.start()

        # Send trade notification
        await notifier.send_trade_notification(trade, market)

        # Send analysis notification
        await notifier.send_analysis_notification(prediction, market)

        # Stop when done
        await notifier.stop()
"""

from __future__ import annotations

__all__ = ["TelegramNotifier"]

from datetime import datetime
from typing import TYPE_CHECKING

from src.config import settings
from src.notifications.message_queue import (
    MAX_QUEUE_SIZE,
    MessageCategory,
    MessagePriority,
    MessageQueue,
)
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.api.telegram import TelegramClient
    from src.models.market import Market
    from src.models.position import Position
    from src.models.prediction import PredictionResult
    from src.models.trade import Trade


class TelegramNotifier:
    """Telegram notification sender.

    Provides methods to send formatted notifications for
    trades, analysis results, errors, and system events.

    Story 9.12: Integrates MessageQueue for rate-limited sending.

    Attributes:
        _client: TelegramClient instance for sending messages
        _logger: Logger instance
        _enabled: Whether notifications are enabled
        _queue: MessageQueue instance for rate-limited sending
        _use_queue: Whether to use the message queue

    Example:
        >>> async with TelegramClient() as client:
        ...     notifier = TelegramNotifier(client)
        ...     await notifier.start()  # Start queue for rate limiting
        ...     await notifier.send_trade_notification(trade, market)
        ...     await notifier.stop()  # Stop queue when done
    """

    def __init__(
        self,
        client: "TelegramClient",
        use_queue: bool = True,
        max_queue_size: int = MAX_QUEUE_SIZE,
    ) -> None:
        """Initialize the notifier with a Telegram client.

        Args:
            client: Initialized TelegramClient instance
            use_queue: Whether to use the message queue (default: True)
            max_queue_size: Maximum queue size (default: 100)
        """
        self._client = client
        self._logger = get_logger(__name__)
        self._enabled = client.is_enabled and settings.telegram.enabled
        self._use_queue = use_queue
        self._queue: MessageQueue | None = None

        # Create the message queue if enabled
        if self._enabled and self._use_queue:
            self._queue = MessageQueue(
                sender=self._direct_send,
                max_size=max_queue_size,
            )

        if not self._enabled:
            self._logger.info("TelegramNotifier initialized (disabled)")
        elif self._use_queue:
            self._logger.info("TelegramNotifier initialized (enabled, with queue)")
        else:
            self._logger.info("TelegramNotifier initialized (enabled, direct send)")

    async def start(self) -> None:
        """Start the message queue for rate-limited sending.

        If the queue is not enabled, this is a no-op.
        """
        if self._queue:
            await self._queue.start()
            self._logger.debug("Message queue started")

    async def stop(self) -> None:
        """Stop the message queue gracefully.

        If the queue is not enabled, this is a no-op.
        """
        if self._queue:
            await self._queue.stop()
            self._logger.debug("Message queue stopped")

    def get_queue_stats(self) -> dict | None:
        """Get queue statistics.

        Returns:
            Queue statistics dict or None if queue is not enabled
        """
        if self._queue:
            return self._queue.get_stats()
        return None

    async def send_message(
        self,
        text: str,
        parse_mode: str = "Markdown",
        immediate: bool = False,
    ) -> bool:
        """Send a message to the configured chat.

        Story 9.12: Supports immediate mode for high-priority messages.

        Args:
            text: Message text (Markdown formatted)
            parse_mode: Parse mode (default: Markdown)
            immediate: Send immediately, bypassing the queue (default: False)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self._enabled:
            return False

        # Use queue if available and not immediate
        if self._queue and not immediate:
            return await self._queue.enqueue(
                text=text,
                priority=MessagePriority.NORMAL,
                category=MessageCategory.SYSTEM,
                parse_mode=parse_mode,
            )

        # Direct send
        return await self._direct_send(text, parse_mode)

    async def _direct_send(
        self,
        text: str,
        parse_mode: str = "Markdown",
    ) -> bool:
        """Directly send a message without queueing.

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

        Story 9.12: Uses NORMAL priority via queue.

        Args:
            trade: The executed trade
            market: The market for the trade

        Returns:
            True if sent successfully, False otherwise
        """
        message = self._format_trade_message(trade, market)

        if self._queue:
            return await self._queue.enqueue(
                text=message,
                priority=MessagePriority.NORMAL,
                category=MessageCategory.TRADE,
            )

        return await self.send_message(message)

    async def send_analysis_notification(
        self,
        prediction: "PredictionResult",
        market: "Market",
    ) -> bool:
        """Send an LLM analysis result notification.

        Story 9.12: Uses LOW priority via queue (mergeable).

        Args:
            prediction: The LLM prediction result
            market: The analyzed market

        Returns:
            True if sent successfully, False otherwise
        """
        message = self._format_analysis_message(prediction, market)

        if self._queue:
            return await self._queue.enqueue(
                text=message,
                priority=MessagePriority.LOW,
                category=MessageCategory.ANALYSIS,
            )

        return await self.send_message(message)

    async def send_error_notification(
        self,
        error: Exception | str,
    ) -> bool:
        """Send an error alert notification.

        Story 9.12: Uses HIGH priority via queue.

        Args:
            error: The error exception or message

        Returns:
            True if sent successfully, False otherwise
        """
        message = self._format_error_message(error)

        if self._queue:
            return await self._queue.enqueue(
                text=message,
                priority=MessagePriority.HIGH,
                category=MessageCategory.ERROR,
            )

        return await self.send_message(message)

    async def send_system_notification(
        self,
        event: str,
        details: dict | None = None,
    ) -> bool:
        """Send a system event notification.

        Story 9.12: Uses NORMAL priority via queue (mergeable).

        Args:
            event: Event name (e.g., "startup", "shutdown")
            details: Optional event details

        Returns:
            True if sent successfully, False otherwise
        """
        message = self._format_system_message(event, details)

        if self._queue:
            return await self._queue.enqueue(
                text=message,
                priority=MessagePriority.NORMAL,
                category=MessageCategory.SYSTEM,
            )

        return await self.send_message(message)

    async def send_position_closed_notification(
        self,
        position: "Position",
        market: "Market",
        pnl: float,
        pnl_pct: float,
    ) -> bool:
        """Send a position closed notification.

        Story 9.3: 交易事件通知集成
        Story 9.12: Uses NORMAL priority via queue.

        Args:
            position: The closed position
            market: The market for the position
            pnl: Profit/loss amount in USD
            pnl_pct: Profit/loss percentage

        Returns:
            True if sent successfully, False otherwise
        """
        message = self._format_position_closed_message(position, market, pnl, pnl_pct)

        if self._queue:
            return await self._queue.enqueue(
                text=message,
                priority=MessagePriority.NORMAL,
                category=MessageCategory.TRADE,
            )

        return await self.send_message(message)

    async def send_command_response(
        self,
        text: str,
        parse_mode: str = "Markdown",
    ) -> bool:
        """Send a command response with highest priority.

        Story 9.12: Uses URGENT priority (immediate send, bypasses queue).

        Args:
            text: Response text (Markdown formatted)
            parse_mode: Parse mode (default: Markdown)

        Returns:
            True if sent successfully, False otherwise
        """
        if self._queue:
            return await self._queue.enqueue(
                text=text,
                priority=MessagePriority.URGENT,
                category=MessageCategory.COMMAND,
                parse_mode=parse_mode,
            )

        return await self.send_message(text, parse_mode, immediate=True)

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

        # Escape special Markdown characters in title
        title = market.title or ""
        title = title.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")

        lines = [
            "\U0001f9e0 *市场分析*",
            f"市场: {title}",
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
                # Escape special characters in assumptions
                safe_assumption = assumption.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
                lines.append(f"- {safe_assumption}")

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

    def _format_position_closed_message(
        self,
        position: "Position",
        market: "Market",
        pnl: float,
        pnl_pct: float,
    ) -> str:
        """Format a position closed notification message.

        Story 9.3: 交易事件通知集成

        Args:
            position: The closed position
            market: The market for the position
            pnl: Profit/loss amount in USD
            pnl_pct: Profit/loss percentage

        Returns:
            Formatted Markdown message
        """
        pnl_emoji = "\U0001f4c8" if pnl >= 0 else "\U0001f4c9"  # chart_up / chart_down
        pnl_sign = "+" if pnl >= 0 else ""

        lines = [
            "\U0001f4ca *持仓平仓*",
            f"市场: {market.title}",
            f"方向: {position.outcome.value}",
            f"份额: {position.shares:.2f}",
            (
                f"成本: ${position.initial_value:.2f}"
                if position.initial_value
                else "成本: N/A"
            ),
            (
                f"收益: ${position.current_value:.2f}"
                if position.current_value
                else "收益: N/A"
            ),
            f"盈亏: {pnl_emoji} {pnl_sign}${pnl:.2f} ({pnl_sign}{pnl_pct:.1%})",
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        return "\n".join(lines)
