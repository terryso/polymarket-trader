"""Audit logging for Telegram control commands.

Story 9.11: Telegram 命令处理 - 远程控制

This module provides audit logging functionality for tracking
control commands such as enable/disable trading and mode changes.
"""

from __future__ import annotations

__all__ = ["log_audit_event", "AuditEventType"]

from datetime import datetime
from enum import Enum
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)


class AuditEventType(str, Enum):
    """审计事件类型."""

    ENABLE_TRADING = "enable_trading"
    DISABLE_TRADING = "disable_trading"
    MODE_CHANGE = "mode_change"
    CONFIRM_MODE_CHANGE = "confirm_mode_change"
    CANCEL_MODE_CHANGE = "cancel_mode_change"


def log_audit_event(
    event_type: AuditEventType,
    chat_id: str,
    details: dict[str, Any] | None = None,
) -> None:
    """记录审计事件.

    Args:
        event_type: 事件类型
        chat_id: 执行操作的 Chat ID
        details: 事件详情

    Example:
        >>> log_audit_event(
        ...     AuditEventType.ENABLE_TRADING,
        ...     "123456789",
        ... )
        >>> log_audit_event(
        ...     AuditEventType.MODE_CHANGE,
        ...     "123456789",
        ...     {"from": "LIVE", "to": "PAPER"},
        ... )
    """
    timestamp = datetime.now().isoformat()
    details_str = f" | details: {details}" if details else ""

    logger.info(
        f"📋 AUDIT | {event_type.value} | "
        f"chat_id: {chat_id} | "
        f"timestamp: {timestamp}{details_str}"
    )
