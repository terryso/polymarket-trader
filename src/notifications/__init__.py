"""Telegram notification module.

This module provides notification functionality for trade events,
analysis results, and system alerts via Telegram.

Story 9.2: 通知消息发送
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

from src.notifications.message_queue import (
    CRITICAL_CATEGORIES,
    MAX_MESSAGE_LENGTH,
    MAX_MESSAGES_PER_SECOND,
    MAX_QUEUE_SIZE,
    MERGEABLE_CATEGORIES,
    MessageCategory,
    MessagePriority,
    MessageQueue,
    QueuedMessage,
    RateLimiter,
)
from src.notifications.telegram_notifier import TelegramNotifier

__all__ = [
    "TelegramNotifier",
    "MessageQueue",
    "MessagePriority",
    "MessageCategory",
    "QueuedMessage",
    "RateLimiter",
    "MAX_MESSAGES_PER_SECOND",
    "MAX_MESSAGE_LENGTH",
    "MAX_QUEUE_SIZE",
    "MERGEABLE_CATEGORIES",
    "CRITICAL_CATEGORIES",
]
