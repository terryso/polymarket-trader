"""Message queue with rate limiting for Telegram notifications.

This module provides a priority-based message queue with rate limiting
to prevent Telegram API throttling.

Story 9.12: 消息队列与限流

Usage:
    from src.notifications.message_queue import (
        MessageQueue,
        MessagePriority,
        MessageCategory,
    )

    async def sender(text: str, parse_mode: str) -> bool:
        # Actual send logic
        return True

    queue = MessageQueue(sender=sender)

    # Enqueue messages with priority
    await queue.enqueue(
        "Urgent message",
        priority=MessagePriority.URGENT,
        category=MessageCategory.COMMAND,
    )

    # Start background sender task
    await queue.start()

    # Stop when done
    await queue.stop()
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import TYPE_CHECKING, Awaitable, Callable

from src.utils.logger import get_logger

if TYPE_CHECKING:
    pass


# Telegram API limits
MAX_MESSAGES_PER_SECOND = 30
MAX_MESSAGES_PER_MINUTE = 1800

# Message limits
MAX_MESSAGE_LENGTH = 4096  # Single message max characters
MAX_QUEUE_SIZE = 100  # Queue max length

# Batch sending
BATCH_WINDOW_MS = 100  # Batch window time (milliseconds)
MAX_BATCH_SIZE = 5  # Max messages per batch


class MessagePriority(IntEnum):
    """Message priority (higher value = higher priority)."""

    LOW = 0  # Analysis notifications
    NORMAL = 1  # Trade notifications, system notifications
    HIGH = 2  # Error alerts
    URGENT = 3  # Command responses


class MessageCategory(str, Enum):
    """Message category for grouping and merging."""

    COMMAND = "command"  # Command responses (/status, /positions, etc.)
    ERROR = "error"  # Error alerts
    TRADE = "trade"  # Trade notifications
    ANALYSIS = "analysis"  # Analysis results
    SYSTEM = "system"  # System events


# Categories that can be merged together
MERGEABLE_CATEGORIES: set[MessageCategory] = {
    MessageCategory.ANALYSIS,
    MessageCategory.SYSTEM,
}

# Categories that are critical and should not be dropped
CRITICAL_CATEGORIES: set[MessageCategory] = {
    MessageCategory.COMMAND,
    MessageCategory.ERROR,
}


@dataclass(order=True)
class QueuedMessage:
    """Message in the queue.

    The sort_index uses negative priority so that higher priority messages
    come first in the priority queue (lower values = higher priority in
    asyncio.PriorityQueue).
    """

    sort_index: int  # Negative priority for correct ordering
    text: str = field(compare=False)
    category: MessageCategory = field(compare=False)
    priority: MessagePriority = field(compare=False)
    timestamp: datetime = field(default_factory=datetime.now, compare=False)
    parse_mode: str = field(default="Markdown", compare=False)

    @classmethod
    def create(
        cls,
        text: str,
        priority: MessagePriority,
        category: MessageCategory,
        parse_mode: str = "Markdown",
    ) -> "QueuedMessage":
        """Create a queued message with proper sort index.

        Args:
            text: Message text
            priority: Message priority
            category: Message category
            parse_mode: Parse mode (Markdown, HTML, etc.)

        Returns:
            QueuedMessage instance
        """
        # Use negative priority so higher priority comes first
        sort_index = -priority.value
        return cls(
            sort_index=sort_index,
            text=text,
            category=category,
            priority=priority,
            parse_mode=parse_mode,
        )


class RateLimiter:
    """Token bucket rate limiter.

    Implements the token bucket algorithm for smooth rate limiting.
    """

    def __init__(
        self,
        rate: float = MAX_MESSAGES_PER_SECOND,
        burst: int = MAX_MESSAGES_PER_SECOND,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            rate: Tokens added per second (messages per second)
            burst: Maximum tokens in bucket (burst capacity)
        """
        self._rate = rate
        self._burst = burst
        self._tokens = float(burst)
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()
        self._logger = get_logger(__name__)

    async def acquire(self) -> None:
        """Wait until a token is available and consume it.

        This method will block if no tokens are available until
        enough time has passed for a new token to be generated.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_update

            # Add tokens based on elapsed time
            self._tokens = min(
                self._burst,
                self._tokens + elapsed * self._rate,
            )
            self._last_update = now

            if self._tokens < 1.0:
                # Need to wait for token
                wait_time = (1.0 - self._tokens) / self._rate
                self._logger.debug(f"Rate limiter waiting {wait_time:.3f}s")
                await asyncio.sleep(wait_time)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0


class MessageQueue:
    """Async message queue with priority and rate limiting.

    This class provides a thread-safe message queue that:
    - Orders messages by priority
    - Rate-limits message sending
    - Supports message merging and splitting
    - Handles queue overflow by dropping non-critical messages

    Attributes:
        _sender: Async function to send messages
        _max_size: Maximum queue size
        _rate_limit: Messages per second limit
        _queue: Priority queue for messages
        _rate_limiter: Token bucket rate limiter
        _running: Whether the background task is running
        _task: Background sender task
        _stats: Queue statistics
    """

    def __init__(
        self,
        sender: Callable[[str, str], Awaitable[bool]],
        max_size: int = MAX_QUEUE_SIZE,
        rate_limit: float = MAX_MESSAGES_PER_SECOND,
    ) -> None:
        """Initialize the message queue.

        Args:
            sender: Async function to send messages (text, parse_mode) -> success
            max_size: Maximum queue size
            rate_limit: Maximum messages per second
        """
        self._sender = sender
        self._max_size = max_size
        self._rate_limit = rate_limit
        self._queue: asyncio.PriorityQueue[QueuedMessage] = asyncio.PriorityQueue()
        self._rate_limiter = RateLimiter(rate=rate_limit, burst=int(rate_limit))
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._logger = get_logger(__name__)

        # Statistics
        self._stats = {
            "enqueued_count": 0,
            "sent_count": 0,
            "dropped_count": 0,
            "merged_count": 0,
            "split_count": 0,
        }
        self._stats_lock = asyncio.Lock()

    async def enqueue(
        self,
        text: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        category: MessageCategory = MessageCategory.SYSTEM,
        parse_mode: str = "Markdown",
    ) -> bool:
        """Add a message to the queue.

        If the queue is full, non-critical messages will be dropped
        to make room for higher priority messages.

        Args:
            text: Message text
            priority: Message priority
            category: Message category
            parse_mode: Parse mode (Markdown, HTML, etc.)

        Returns:
            True if message was enqueued successfully, False if dropped
        """
        # Handle immediate sending for urgent messages
        if priority == MessagePriority.URGENT:
            return await self._send_immediate(text, parse_mode)

        # Check if queue is full
        if self._queue.qsize() >= self._max_size:
            # Try to make room by dropping non-critical messages
            if not await self._make_room(category):
                self._logger.warning("Queue full, dropping message")
                async with self._stats_lock:
                    self._stats["dropped_count"] += 1
                return False

        # Split long messages
        messages = self._split_long_message(text)
        if len(messages) > 1:
            async with self._stats_lock:
                self._stats["split_count"] += len(messages) - 1

        # Enqueue each part
        for msg_text in messages:
            message = QueuedMessage.create(
                text=msg_text,
                priority=priority,
                category=category,
                parse_mode=parse_mode,
            )
            await self._queue.put(message)

        async with self._stats_lock:
            self._stats["enqueued_count"] += len(messages)

        return True

    async def start(self) -> None:
        """Start the background sender task."""
        if self._running:
            self._logger.warning("MessageQueue already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._sender_loop())
        self._logger.info(
            f"MessageQueue started (rate_limit={self._rate_limit}/s, "
            f"max_size={self._max_size})"
        )

    async def stop(self) -> None:
        """Stop the background sender task gracefully."""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        self._logger.info(
            f"MessageQueue stopped (sent={self._stats['sent_count']}, "
            f"dropped={self._stats['dropped_count']})"
        )

    def get_stats(self) -> dict:
        """Get queue statistics.

        Returns:
            Dictionary with queue statistics
        """
        return {
            "queue_size": self._queue.qsize(),
            "max_size": self._max_size,
            "running": self._running,
            **self._stats,
        }

    async def _send_immediate(self, text: str, parse_mode: str) -> bool:
        """Send a message immediately, bypassing the queue.

        Used for URGENT priority messages.

        Args:
            text: Message text
            parse_mode: Parse mode

        Returns:
            True if sent successfully
        """
        try:
            await self._rate_limiter.acquire()
            result = await self._sender(text, parse_mode)
            if result:
                async with self._stats_lock:
                    self._stats["sent_count"] += 1
            return result
        except Exception as e:
            self._logger.error(f"Failed to send immediate message: {e}")
            return False

    async def _make_room(self, new_category: MessageCategory) -> bool:
        """Try to make room in the queue by dropping non-critical messages.

        Args:
            new_category: Category of the new message

        Returns:
            True if room was made, False if queue is still full
        """
        # Find and remove oldest non-critical message
        temp_messages: list[QueuedMessage] = []
        dropped = False

        # Drain queue to find droppable message
        while not self._queue.empty():
            try:
                msg = self._queue.get_nowait()
                if not dropped and msg.category not in CRITICAL_CATEGORIES:
                    # Drop this message
                    dropped = True
                    self._logger.debug(
                        f"Dropped message: category={msg.category.value}"
                    )
                    async with self._stats_lock:
                        self._stats["dropped_count"] += 1
                else:
                    temp_messages.append(msg)
            except asyncio.QueueEmpty:
                break

        # Put remaining messages back
        for msg in temp_messages:
            await self._queue.put(msg)

        return dropped

    async def _sender_loop(self) -> None:
        """Background task that sends messages from the queue."""
        self._logger.debug("Sender loop started")

        while self._running:
            try:
                # Wait for a message with timeout to allow checking _running
                try:
                    message = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue

                # Try to batch similar messages
                batch = await self._collect_batch(message)

                # Send the batch
                for msg in batch:
                    await self._rate_limiter.acquire()
                    try:
                        success = await self._sender(msg.text, msg.parse_mode)
                        if success:
                            async with self._stats_lock:
                                self._stats["sent_count"] += 1
                        else:
                            self._logger.warning("Failed to send message")
                    except Exception as e:
                        self._logger.error(f"Error sending message: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in sender loop: {e}")
                await asyncio.sleep(0.1)  # Prevent tight error loop

        self._logger.debug("Sender loop stopped")

    async def _collect_batch(
        self,
        first_message: QueuedMessage,
    ) -> list[QueuedMessage]:
        """Collect a batch of mergeable messages.

        Args:
            first_message: The first message to include in the batch

        Returns:
            List of messages to send (may be merged)
        """
        batch: list[QueuedMessage] = [first_message]

        # Only try to batch if the first message is mergeable
        if first_message.category not in MERGEABLE_CATEGORIES:
            return batch

        # Try to collect more messages of the same category
        deadline = time.monotonic() + (BATCH_WINDOW_MS / 1000.0)

        while len(batch) < MAX_BATCH_SIZE and time.monotonic() < deadline:
            try:
                msg = self._queue.get_nowait()

                # Only batch same category and non-critical messages
                if (
                    msg.category == first_message.category
                    and msg.category in MERGEABLE_CATEGORIES
                ):
                    batch.append(msg)
                else:
                    # Put non-matching message back
                    await self._queue.put(msg)
                    break
            except asyncio.QueueEmpty:
                break

        # Try to merge batch if multiple messages
        if len(batch) > 1:
            merged = self._merge_messages(batch)
            if merged:
                async with self._stats_lock:
                    self._stats["merged_count"] += len(batch) - 1
                return [merged]

        return batch

    def _can_merge_messages(
        self,
        msg1: QueuedMessage,
        msg2: QueuedMessage,
    ) -> bool:
        """Check if two messages can be merged.

        Args:
            msg1: First message
            msg2: Second message

        Returns:
            True if messages can be merged
        """
        # Only merge messages of the same mergeable category
        if msg1.category != msg2.category:
            return False

        if msg1.category not in MERGEABLE_CATEGORIES:
            return False

        # Check combined length
        combined_length = len(msg1.text) + len(msg2.text) + 10  # +10 for separator
        return combined_length <= MAX_MESSAGE_LENGTH

    def _merge_messages(self, messages: list[QueuedMessage]) -> QueuedMessage | None:
        """Merge multiple messages into one.

        Args:
            messages: List of messages to merge

        Returns:
            Merged message or None if cannot merge
        """
        if len(messages) < 2:
            return messages[0] if messages else None

        category = messages[0].category

        if category == MessageCategory.ANALYSIS:
            return self._merge_analysis_messages(messages)
        elif category == MessageCategory.SYSTEM:
            return self._merge_system_messages(messages)

        return None

    def _merge_analysis_messages(
        self,
        messages: list[QueuedMessage],
    ) -> QueuedMessage | None:
        """Merge analysis messages into a summary.

        Args:
            messages: List of analysis messages

        Returns:
            Merged summary message
        """
        if len(messages) < 2:
            return None

        lines = [
            f"\U0001f9e0 *市场分析汇总* ({len(messages)} 个市场)",
            "",
        ]

        for i, msg in enumerate(messages, 1):
            # Extract first line (title) from each message
            first_line = msg.text.split("\n")[0] if "\n" in msg.text else msg.text[:50]
            lines.append(f"{i}. {first_line}")

        merged_text = "\n".join(lines)

        # Check if merged message is too long
        if len(merged_text) > MAX_MESSAGE_LENGTH:
            return None

        return QueuedMessage.create(
            text=merged_text,
            priority=MessagePriority.LOW,
            category=MessageCategory.ANALYSIS,
        )

    def _merge_system_messages(
        self,
        messages: list[QueuedMessage],
    ) -> QueuedMessage | None:
        """Merge system messages into a summary.

        Args:
            messages: List of system messages

        Returns:
            Merged summary message
        """
        if len(messages) < 2:
            return None

        lines = [
            f"\u2139\ufe0f *系统事件汇总* ({len(messages)} 个事件)",
            "",
        ]

        for msg in messages:
            # Extract first line from each message
            first_line = msg.text.split("\n")[0] if "\n" in msg.text else msg.text[:50]
            lines.append(f"- {first_line}")

        merged_text = "\n".join(lines)

        # Check if merged message is too long
        if len(merged_text) > MAX_MESSAGE_LENGTH:
            return None

        return QueuedMessage.create(
            text=merged_text,
            priority=MessagePriority.LOW,
            category=MessageCategory.SYSTEM,
        )

    def _split_long_message(self, text: str) -> list[str]:
        """Split a long message into multiple parts.

        Args:
            text: Message text to split

        Returns:
            List of message parts (each <= MAX_MESSAGE_LENGTH)
        """
        if len(text) <= MAX_MESSAGE_LENGTH:
            return [text]

        parts: list[str] = []
        remaining = text
        total_parts = -1  # Will be calculated after splitting

        # First pass: split into chunks
        raw_parts: list[str] = []
        while remaining:
            if len(remaining) <= MAX_MESSAGE_LENGTH - 20:  # Leave room for part marker
                raw_parts.append(remaining)
                break

            # Find a good split point (newline or space)
            split_point = MAX_MESSAGE_LENGTH - 20

            # Try to find a newline
            newline_pos = remaining.rfind("\n", 0, split_point)
            if newline_pos > MAX_MESSAGE_LENGTH // 2:
                split_point = newline_pos + 1
            else:
                # Try to find a space
                space_pos = remaining.rfind(" ", 0, split_point)
                if space_pos > MAX_MESSAGE_LENGTH // 2:
                    split_point = space_pos + 1

            raw_parts.append(remaining[:split_point])
            remaining = remaining[split_point:]

        total_parts = len(raw_parts)

        # Second pass: add part markers
        for i, part in enumerate(raw_parts, 1):
            # Add part marker
            marker = f" ({i}/{total_parts})"
            part_with_marker = part + marker
            parts.append(part_with_marker)

        self._logger.debug(f"Split message into {len(parts)} parts")
        return parts

    async def _dequeue(self) -> QueuedMessage | None:
        """Dequeue the highest priority message.

        This is primarily used for testing.

        Returns:
            The highest priority message or None if queue is empty
        """
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None
