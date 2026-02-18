"""Telegram notification module.

This module provides notification functionality for trade events,
analysis results, and system alerts via Telegram.

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

from src.notifications.telegram_notifier import TelegramNotifier

__all__ = ["TelegramNotifier"]
