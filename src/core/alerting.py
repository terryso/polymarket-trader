"""Alerting system for the Polymarket Trader application.

This module provides alerting capabilities including multiple channels
(log file, webhook) and alert throttling to prevent alert storms.

Example:
    >>> from src.core.alerting import AlertManager, LogAlertChannel, AlertLevel
    >>>
    >>> # Create alert manager with default log channel
    >>> manager = AlertManager(min_level=AlertLevel.WARNING)
    >>>
    >>> # Check and send alert
    >>> manager.check_and_alert(NetworkError("API failed"), {"source": "api"})
"""

from __future__ import annotations

__all__ = [
    "Alert",
    "AlertChannel",
    "AlertLevel",
    "AlertManager",
    "LogAlertChannel",
    "WebhookAlertChannel",
]

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from src.exceptions import BotError, NetworkError
from src.utils.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class Alert:
    """Alert data container.

    Attributes:
        level: Alert severity level
        message: Alert message
        source: Source component that triggered the alert
        timestamp: When the alert was created
        context: Additional context data
        count: Number of times this alert has occurred
    """

    level: str
    message: str
    source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: dict[str, Any] = field(default_factory=dict)
    count: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize alert to dictionary.

        Returns:
            Dictionary representation of the alert
        """
        return {
            "level": self.level,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "count": self.count,
        }


class AlertChannel(ABC):
    """Abstract base class for alert channels."""

    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """Send an alert through this channel.

        Args:
            alert: The alert to send

        Returns:
            True if the alert was sent successfully, False otherwise
        """
        pass


class LogAlertChannel(AlertChannel):
    """Alert channel that writes to a log file.

    This channel writes alerts to a dedicated error log file in JSON format,
    one alert per line for easy parsing and analysis.
    """

    def __init__(self, log_file: str = "logs/errors.log") -> None:
        """Initialize the log alert channel.

        Args:
            log_file: Path to the error log file
        """
        self.log_file = log_file
        # Ensure directory exists
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    async def send(self, alert: Alert) -> bool:
        """Write alert to the log file.

        Args:
            alert: The alert to send

        Returns:
            True if the alert was written successfully, False otherwise
        """
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert.to_dict()) + "\n")
            logger.debug(f"Alert written to {self.log_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to write alert to log: {e}")
            return False


class WebhookAlertChannel(AlertChannel):
    """Alert channel that sends to a webhook URL.

    This channel sends alerts as JSON payloads to a configured webhook URL,
    useful for integration with external alerting systems.
    """

    def __init__(self, webhook_url: str, timeout: float = 10.0) -> None:
        """Initialize the webhook alert channel.

        Args:
            webhook_url: The URL to send alerts to
            timeout: Request timeout in seconds
        """
        self.webhook_url = webhook_url
        self.timeout = timeout

    async def send(self, alert: Alert) -> bool:
        """Send alert to the webhook URL.

        Args:
            alert: The alert to send

        Returns:
            True if the alert was sent successfully, False otherwise
        """
        try:
            import aiohttp

            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.webhook_url,
                    json=alert.to_dict(),
                ) as response:
                    if response.status == 200:
                        logger.debug(f"Alert sent to webhook: {self.webhook_url}")
                        return True
                    else:
                        logger.warning(
                            f"Webhook returned status {response.status}: {self.webhook_url}"
                        )
                        return False
        except ImportError:
            logger.error("aiohttp not installed, cannot send webhook alert")
            return False
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False


class AlertManager:
    """Central alert management system.

    The AlertManager coordinates alert creation, throttling, and delivery
    across multiple channels. It prevents alert storms through configurable
    throttling and tracks consecutive failures for automatic escalation.

    Attributes:
        channels: List of alert channels to send alerts through
        min_level: Minimum alert level to trigger notifications
        throttle_seconds: Minimum time between duplicate alerts
        consecutive_failure_threshold: Number of failures before escalation

    Example:
        >>> manager = AlertManager(
        ...     channels=[LogAlertChannel()],
        ...     min_level=AlertLevel.WARNING,
        ...     consecutive_failure_threshold=3
        ... )
        >>> manager.check_and_alert(exception, {"source": "api"})
    """

    # Alert level numeric thresholds
    LEVEL_THRESHOLD: dict[str, int] = {
        AlertLevel.INFO.value: 0,
        AlertLevel.WARNING.value: 1,
        AlertLevel.ERROR.value: 2,
        AlertLevel.CRITICAL.value: 3,
    }

    def __init__(
        self,
        channels: list[AlertChannel] | None = None,
        min_level: str | AlertLevel = AlertLevel.WARNING,
        throttle_seconds: int = 300,
        consecutive_failure_threshold: int = 3,
    ) -> None:
        """Initialize the alert manager.

        Args:
            channels: List of alert channels (defaults to LogAlertChannel)
            min_level: Minimum alert level to trigger notifications
            throttle_seconds: Minimum seconds between duplicate alerts
            consecutive_failure_threshold: Failures before escalation
        """
        self.channels = channels or [LogAlertChannel()]
        self.min_level = min_level.value if isinstance(min_level, AlertLevel) else min_level
        self.throttle_seconds = throttle_seconds
        self.consecutive_failure_threshold = consecutive_failure_threshold

        # Alert history for throttling (key -> last alert time)
        self._alert_history: dict[str, datetime] = {}

        # Consecutive failure tracking (source -> count)
        self._consecutive_failures: dict[str, int] = {}

    def check_and_alert(
        self,
        exception: Exception,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Check if an alert should be sent and send it.

        This method determines the appropriate alert level, checks throttling
        rules, and sends the alert through all configured channels if appropriate.

        Args:
            exception: The exception that triggered the alert check
            context: Additional context about the error
        """
        context = context or {}

        # Determine alert level
        level = self._determine_level(exception, context)

        # Check if level meets minimum threshold
        if self.LEVEL_THRESHOLD.get(level, 0) < self.LEVEL_THRESHOLD.get(
            self.min_level, 1
        ):
            logger.debug(f"Alert level {level} below minimum {self.min_level}, skipping")
            return

        # Generate alert key for throttling
        alert_key = self._generate_alert_key(exception, context)

        # Check throttling
        if alert_key in self._alert_history:
            elapsed = datetime.utcnow() - self._alert_history[alert_key]
            if elapsed.total_seconds() < self.throttle_seconds:
                logger.debug(f"Alert throttled: {alert_key}")
                return

        # Create and send alert
        alert = Alert(
            level=level,
            message=str(exception),
            source=context.get("source", "system"),
            context=context,
        )

        self._send_alert(alert)
        self._alert_history[alert_key] = datetime.utcnow()

    def record_failure(self, source: str) -> int:
        """Record a failure for a source.

        Tracks consecutive failures and triggers an alert if the threshold
        is reached.

        Args:
            source: Identifier for the failing component

        Returns:
            Current consecutive failure count
        """
        self._consecutive_failures[source] = self._consecutive_failures.get(source, 0) + 1
        count = self._consecutive_failures[source]

        logger.warning(
            f"Failure recorded for {source}: {count} consecutive "
            f"(threshold: {self.consecutive_failure_threshold})"
        )

        if count >= self.consecutive_failure_threshold:
            self.check_and_alert(
                Exception(f"Consecutive failures exceeded: {count}"),
                {"source": source, "failures": count, "threshold_exceeded": True},
            )

        return count

    def reset_failures(self, source: str) -> None:
        """Reset consecutive failure count for a source.

        Called when a previously failing component succeeds.

        Args:
            source: Identifier for the component
        """
        if source in self._consecutive_failures:
            logger.info(f"Failure count reset for {source}")
            del self._consecutive_failures[source]

    def get_failure_count(self, source: str) -> int:
        """Get current consecutive failure count for a source.

        Args:
            source: Identifier for the component

        Returns:
            Current consecutive failure count
        """
        return self._consecutive_failures.get(source, 0)

    def _determine_level(self, exception: Exception, context: dict[str, Any]) -> str:
        """Determine the appropriate alert level for an exception.

        Args:
            exception: The exception to evaluate
            context: Additional context

        Returns:
            The determined alert level string
        """
        source = context.get("source", "")

        # Escalate if consecutive failures exceed threshold
        if self._consecutive_failures.get(source, 0) >= self.consecutive_failure_threshold:
            return AlertLevel.ERROR.value

        # Network/connection errors are errors (check before BotError since NetworkError inherits from it)
        if isinstance(exception, (NetworkError, ConnectionError, TimeoutError)):
            return AlertLevel.ERROR.value

        # Business exceptions are warnings
        if isinstance(exception, BotError):
            return AlertLevel.WARNING.value

        # Everything else is critical (unexpected)
        return AlertLevel.CRITICAL.value

    def _generate_alert_key(self, exception: Exception, context: dict[str, Any]) -> str:
        """Generate a unique key for alert throttling.

        Args:
            exception: The exception
            context: Additional context

        Returns:
            A unique key for this type of alert
        """
        exception_type = type(exception).__name__
        source = context.get("source", "unknown")
        return f"{exception_type}:{source}"

    def _send_alert(self, alert: Alert) -> None:
        """Send alert to all configured channels.

        Creates async tasks for each channel to avoid blocking.
        If no event loop is running, logs a warning instead of failing.

        Args:
            alert: The alert to send
        """
        logger.info(f"Sending alert: [{alert.level}] {alert.message}")

        for channel in self.channels:
            try:
                # Check if there's a running event loop
                loop = asyncio.get_running_loop()
                # Create task with exception handling callback
                task = loop.create_task(self._send_to_channel(channel, alert))
                task.add_done_callback(self._create_task_error_handler(channel))
            except RuntimeError:
                # No running event loop - alert will be logged but not sent async
                logger.warning(
                    f"No event loop running, cannot send alert async to {type(channel).__name__}. "
                    f"Alert: [{alert.level}] {alert.message}"
                )
            except Exception as e:
                logger.error(f"Failed to create alert task: {e}")

    def _create_task_error_handler(
        self, channel: AlertChannel
    ) -> Callable[[asyncio.Task[None]], None]:
        """Create an error handler callback for async tasks.

        Args:
            channel: The channel the task is sending to

        Returns:
            A callback function that logs any exceptions from the task
        """

        def handler(task: asyncio.Task[None]) -> None:
            """Handle task completion and log any exceptions."""
            try:
                task.result()
            except asyncio.CancelledError:
                logger.debug(f"Alert task to {type(channel).__name__} was cancelled")
            except Exception as e:
                logger.error(f"Alert task to {type(channel).__name__} failed: {e}")

        return handler

    async def _send_to_channel(self, channel: AlertChannel, alert: Alert) -> None:
        """Send alert to a single channel.

        Args:
            channel: The channel to send to
            alert: The alert to send
        """
        try:
            success = await channel.send(alert)
            channel_name = type(channel).__name__
            if success:
                logger.debug(f"Alert sent to {channel_name}")
            else:
                logger.warning(f"Alert failed to send to {channel_name}")
        except Exception as e:
            logger.error(f"Error sending alert to {type(channel).__name__}: {e}")

    def clear_history(self) -> None:
        """Clear alert history (for testing)."""
        self._alert_history.clear()

    def clear_failures(self) -> None:
        """Clear all failure counts (for testing)."""
        self._consecutive_failures.clear()
