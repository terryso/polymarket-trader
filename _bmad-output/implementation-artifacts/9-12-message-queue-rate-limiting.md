# Story 9.12: 消息队列与限流

Status: ready-for-dev

## Story

As a **开发者**,
I want **实现 Telegram 消息队列和限流**,
So that **系统不会因消息过多而被 Telegram API 限流**.

## Acceptance Criteria

**Given** 通知发送已实现 (Story 9.2)
**When** 实现消息队列机制
**Then** 创建 `src/notifications/message_queue.py`:
- 使用 `asyncio.Queue` 实现消息队列
- 限制发送频率: 最大 30 条/秒 (Telegram API 限制)
- 消息优先级: 控制命令响应 > 错误告警 > 交易通知 > 分析通知
**And** 实现消息批量发送:
- 相同类型的短消息合并发送
- 单条消息字符限制: 4096 字符
- 超长消息自动分割
**And** 队列满时丢弃最旧的非关键消息
**And** 记录队列状态日志

## Tasks / Subtasks

- [ ] Task 1: 创建消息优先级和数据类 (AC: #1)
  - [ ] 1.1 定义 `MessagePriority` 枚举 (URGENT, HIGH, NORMAL, LOW)
  - [ ] 1.2 定义 `QueuedMessage` 数据类 (text, priority, timestamp, category)
  - [ ] 1.3 定义 `MessageCategory` 枚举 (COMMAND, ERROR, TRADE, ANALYSIS, SYSTEM)

- [ ] Task 2: 实现 MessageQueue 类 (AC: #1)
  - [ ] 2.1 创建 `src/notifications/message_queue.py` 文件
  - [ ] 2.2 添加模块 docstring 和使用示例
  - [ ] 2.3 定义 `MessageQueue` 类
  - [ ] 2.4 实现构造函数 (max_size, rate_limit)
  - [ ] 2.5 实现优先级队列 (使用 asyncio.PriorityQueue)
  - [ ] 2.6 实现 `enqueue()` 方法支持优先级
  - [ ] 2.7 实现 `dequeue()` 方法返回最高优先级消息
  - [ ] 2.8 实现 `start()` 和 `stop()` 后台发送任务

- [ ] Task 3: 实现限流机制 (AC: #1)
  - [ ] 3.1 定义 Telegram API 限制常量 (30 条/秒)
  - [ ] 3.2 实现 `RateLimiter` 类 (令牌桶算法)
  - [ ] 3.3 实现 `acquire()` 方法等待可用令牌
  - [ ] 3.4 集成到 MessageQueue 发送循环

- [ ] Task 4: 实现消息批量发送 (AC: #2)
  - [ ] 4.1 实现 `_can_merge_messages()` 判断是否可合并
  - [ ] 4.2 实现 `_merge_messages()` 合并同类消息
  - [ ] 4.3 实现 `_split_long_message()` 分割超长消息 (4096 字符)
  - [ ] 4.4 在发送循环中应用批量发送逻辑

- [ ] Task 5: 实现队列满处理 (AC: #3)
  - [ ] 5.1 定义 `is_critical()` 判断消息是否关键
  - [ ] 5.2 队列满时丢弃最旧的非关键消息
  - [ ] 5.3 记录丢弃日志

- [ ] Task 6: 集成到 TelegramNotifier (AC: All)
  - [ ] 6.1 在 `TelegramNotifier` 中添加 `MessageQueue` 依赖
  - [ ] 6.2 修改 `send_message()` 使用队列发送
  - [ ] 6.3 添加 `start()` 和 `stop()` 方法管理队列
  - [ ] 6.4 支持立即发送模式 (用于高优先级消息)

- [ ] Task 7: 实现队列状态监控 (AC: #4)
  - [ ] 7.1 实现 `get_queue_stats()` 返回队列统计
  - [ ] 7.2 记录队列状态日志 (队列大小、发送速率)
  - [ ] 7.3 添加队列健康检查

- [ ] Task 8: 更新模块导出 (AC: All)
  - [ ] 8.1 更新 `src/notifications/__init__.py` 导出 `MessageQueue`, `MessagePriority`
  - [ ] 8.2 更新 `TelegramNotifier` 初始化逻辑

- [ ] Task 9: 编写测试 (AC: All)
  - [ ] 9.1 创建 `tests/test_notifications/test_message_queue.py`
  - [ ] 9.2 测试优先级队列行为
  - [ ] 9.3 测试限流机制
  - [ ] 9.4 测试消息合并
  - [ ] 9.5 测试消息分割
  - [ ] 9.6 测试队列满丢弃逻辑
  - [ ] 9.7 测试与 TelegramNotifier 集成

- [ ] Task 10: 代码质量检查 (AC: All)
  - [ ] 10.1 运行 `mypy src/notifications/` 无错误
  - [ ] 10.2 运行 `black --check src/notifications/` 通过
  - [ ] 10.3 运行 `isort --check src/notifications/` 通过
  - [ ] 10.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: epics.md#Story 9.12]

**消息优先级设计:**

```python
from enum import IntEnum

class MessagePriority(IntEnum):
    """消息优先级 (数值越大优先级越高)."""
    LOW = 0       # 分析通知
    NORMAL = 1    # 交易通知、系统通知
    HIGH = 2      # 错误告警
    URGENT = 3    # 控制命令响应
```

**消息类别:**

```python
class MessageCategory(str, Enum):
    """消息类别."""
    COMMAND = "command"    # 命令响应 (/status, /positions 等)
    ERROR = "error"        # 错误告警
    TRADE = "trade"        # 交易通知
    ANALYSIS = "analysis"  # 分析结果
    SYSTEM = "system"      # 系统事件
```

**队列配置常量:**

```python
# Telegram API 限制
MAX_MESSAGES_PER_SECOND = 30
MAX_MESSAGES_PER_MINUTE = 1800

# 消息限制
MAX_MESSAGE_LENGTH = 4096  # 单条消息最大字符数
MAX_QUEUE_SIZE = 100       # 队列最大长度

# 批量发送
BATCH_WINDOW_MS = 100      # 批量窗口时间 (毫秒)
MAX_BATCH_SIZE = 5         # 单次批量发送最大消息数
```

### 现有依赖 [Source: Story 9.2]

**TelegramNotifier 已实现的方法:**
- `send_message(text, parse_mode)` - 发送普通消息
- `send_trade_notification(trade, market)` - 发送交易通知
- `send_analysis_notification(prediction, market)` - 发送分析结果
- `send_error_notification(error)` - 发送错误告警
- `send_system_notification(event, details)` - 发送系统事件通知

**需要扩展的方法:**
- `start()` - 启动消息队列
- `stop()` - 停止消息队列
- `send_message(immediate=True)` - 支持立即发送模式

### 限流算法: 令牌桶

```python
import asyncio
import time

class RateLimiter:
    """令牌桶限流器."""

    def __init__(
        self,
        rate: float = 30.0,  # 每秒令牌数
        burst: int = 30,     # 桶容量
    ) -> None:
        self._rate = rate
        self._burst = burst
        self._tokens = float(burst)
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """等待获取一个令牌."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_update
            self._tokens = min(
                self._burst,
                self._tokens + elapsed * self._rate
            )
            self._last_update = now

            if self._tokens < 1.0:
                # 需要等待
                wait_time = (1.0 - self._tokens) / self._rate
                await asyncio.sleep(wait_time)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0
```

### 消息队列设计

**QueuedMessage 数据类:**

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass(order=True)
class QueuedMessage:
    """队列中的消息."""
    priority: int  # 用于优先级排序 (负数，数值越大优先级越高)
    text: str = field(compare=False)
    category: MessageCategory = field(compare=False)
    timestamp: datetime = field(default_factory=datetime.now, compare=False)
    parse_mode: str = field(default="Markdown", compare=False)
```

**MessageQueue API:**

```python
class MessageQueue:
    """异步消息队列，支持优先级和限流."""

    def __init__(
        self,
        sender: Callable[[str, str], Awaitable[bool]],
        max_size: int = 100,
        rate_limit: float = 30.0,
    ) -> None:
        """初始化消息队列.

        Args:
            sender: 发送消息的异步函数
            max_size: 队列最大长度
            rate_limit: 每秒最大发送数
        """
        ...

    async def enqueue(
        self,
        text: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        category: MessageCategory = MessageCategory.SYSTEM,
        parse_mode: str = "Markdown",
    ) -> bool:
        """将消息加入队列.

        Args:
            text: 消息文本
            priority: 消息优先级
            category: 消息类别
            parse_mode: 解析模式

        Returns:
            True 如果成功加入队列，False 如果队列满且消息被丢弃
        """
        ...

    async def start(self) -> None:
        """启动后台发送任务."""
        ...

    async def stop(self) -> None:
        """停止后台发送任务."""
        ...

    def get_stats(self) -> dict:
        """获取队列统计信息."""
        ...
```

### 消息合并策略

**可合并的消息类别:**
- ANALYSIS: 多个分析结果可合并为一个汇总消息
- SYSTEM: 多个系统事件可合并

**不可合并的消息类别:**
- COMMAND: 命令响应必须独立发送
- ERROR: 错误告警必须独立发送
- TRADE: 交易通知必须独立发送

**合并示例:**

```markdown
# 合并前 (3 条分析消息)
🧠 *市场分析* BTC...
🧠 *市场分析* ETH...
🧠 *市场分析* SOL...

# 合并后 (1 条汇总消息)
🧠 *市场分析汇总* (3 个市场)
1. BTC: BUY YES (置信度 85%)
2. ETH: NO_TRADE (置信度 60%)
3. SOL: BUY NO (置信度 78%)
```

### 消息分割策略

**超长消息分割:**
- 单条消息超过 4096 字符时自动分割
- 分割时保持 Markdown 格式完整性
- 添加 "(1/N)" 标记分割序号

**分割示例:**

```markdown
# 原始消息 (5000 字符)
📜 *交易历史* (20 笔)
... (超过 4096 字符)

# 分割后
# 消息 1
📜 *交易历史* (1/2) (20 笔)
... (前 4000 字符)

# 消息 2
📜 *交易历史* (2/2)
... (剩余字符)
```

### 数据模型 [Source: src/models/]

本 Story 不需要新的数据模型，使用现有的 Trade, Market, PredictionResult 模型。

### 项目结构 [Source: architecture.md#Project Structure]

**新增/修改文件:**
```
src/notifications/
├── __init__.py              # 修改: 导出 MessageQueue, MessagePriority
├── telegram_notifier.py     # 修改: 集成 MessageQueue
└── message_queue.py         # 新增: MessageQueue 实现

tests/test_notifications/
├── __init__.py              # 已存在
├── test_telegram_notifier.py  # 修改: 更新集成测试
└── test_message_queue.py    # 新增: MessageQueue 测试
```

### 依赖关系

**本故事依赖:**
- Story 9.1: Telegram Bot 配置与初始化 (TelegramClient)
- Story 9.2: 通知消息发送 (TelegramNotifier)
- Story 1.3: 日志系统 (get_logger)

**后续故事依赖本故事:**
- 无 (Epic 9 最后一个故事)

### 前一个故事学习 [Source: 9-11-cmd-remote-control.md]

**从 Story 9.11 学到的模式:**

1. **命令响应优先级**: 命令响应应立即发送，不应延迟
2. **安全确认**: 重要操作需要二次确认
3. **审计日志**: 控制命令应记录审计日志
4. **状态同步**: 状态更新应立即生效

**应用于本故事:**
- URGENT 优先级用于命令响应，应绕过队列或立即发送
- 控制命令响应不应被丢弃或延迟

### 实现注意事项

**关键点:**

1. **优先级队列**: 使用 `asyncio.PriorityQueue` 实现优先级排序
2. **令牌桶限流**: 使用令牌桶算法实现平滑限流
3. **消息合并**: 只合并可合并类别的消息
4. **消息分割**: 保持 Markdown 格式完整性
5. **队列满处理**: 丢弃最旧的非关键消息
6. **立即发送**: URGENT 优先级支持绕过队列

**与 TelegramNotifier 的集成:**
- TelegramNotifier 内部创建 MessageQueue 实例
- `start()` 方法启动队列后台任务
- `stop()` 方法停止队列后台任务
- `send_message(immediate=True)` 支持立即发送

### 测试策略

```python
# tests/test_notifications/test_message_queue.py
"""Tests for MessageQueue."""

from __future__ import annotations

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.notifications.message_queue import (
    MessageQueue,
    MessagePriority,
    MessageCategory,
    QueuedMessage,
    RateLimiter,
)


class TestRateLimiter:
    """Tests for RateLimiter class."""

    @pytest.fixture
    def limiter(self) -> RateLimiter:
        """Create a rate limiter."""
        return RateLimiter(rate=30.0, burst=30)

    @pytest.mark.asyncio
    async def test_acquire_within_burst(self, limiter: RateLimiter) -> None:
        """Test acquiring within burst capacity."""
        # Should not wait for first 30 requests
        start = asyncio.get_event_loop().time()
        for _ in range(30):
            await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start
        assert elapsed < 0.1  # Should be nearly instant

    @pytest.mark.asyncio
    async def test_acquire_rate_limited(self, limiter: RateLimiter) -> None:
        """Test rate limiting kicks in after burst."""
        # Exhaust burst
        for _ in range(30):
            await limiter.acquire()

        # Next request should wait ~33ms
        start = asyncio.get_event_loop().time()
        await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start
        assert elapsed >= 0.03  # At least 33ms


class TestMessageQueue:
    """Tests for MessageQueue class."""

    @pytest.fixture
    def mock_sender(self) -> AsyncMock:
        """Create a mock sender function."""
        return AsyncMock(return_value=True)

    @pytest.fixture
    def queue(self, mock_sender: AsyncMock) -> MessageQueue:
        """Create a message queue."""
        return MessageQueue(
            sender=mock_sender,
            max_size=10,
            rate_limit=100.0,  # High rate for testing
        )

    @pytest.mark.asyncio
    async def test_enqueue_success(
        self,
        queue: MessageQueue,
    ) -> None:
        """Test successful enqueue."""
        result = await queue.enqueue(
            "Test message",
            priority=MessagePriority.NORMAL,
        )
        assert result is True
        assert queue.get_stats()["queue_size"] == 1

    @pytest.mark.asyncio
    async def test_priority_order(
        self,
        queue: MessageQueue,
    ) -> None:
        """Test messages are processed in priority order."""
        await queue.enqueue("Low", priority=MessagePriority.LOW)
        await queue.enqueue("Urgent", priority=MessagePriority.URGENT)
        await queue.enqueue("High", priority=MessagePriority.HIGH)

        # Dequeue should return in priority order
        msg1 = await queue._dequeue()
        assert msg1.text == "Urgent"

        msg2 = await queue._dequeue()
        assert msg2.text == "High"

        msg3 = await queue._dequeue()
        assert msg3.text == "Low"

    @pytest.mark.asyncio
    async def test_queue_full_drops_non_critical(
        self,
        mock_sender: AsyncMock,
    ) -> None:
        """Test queue full drops oldest non-critical message."""
        queue = MessageQueue(
            sender=mock_sender,
            max_size=2,
            rate_limit=100.0,
        )

        # Fill queue
        await queue.enqueue("Old low", priority=MessagePriority.LOW)
        await queue.enqueue("High", priority=MessagePriority.HIGH)

        # Add one more - should drop oldest non-critical
        result = await queue.enqueue("Urgent", priority=MessagePriority.URGENT)
        assert result is True

        stats = queue.get_stats()
        assert stats["queue_size"] == 2
        assert stats["dropped_count"] == 1

    @pytest.mark.asyncio
    async def test_message_split(
        self,
        queue: MessageQueue,
    ) -> None:
        """Test long message is split."""
        long_text = "x" * 5000  # 5000 characters
        parts = queue._split_long_message(long_text)
        assert len(parts) == 2
        assert len(parts[0]) <= 4096
        assert len(parts[1]) <= 4096

    @pytest.mark.asyncio
    async def test_start_stop(
        self,
        queue: MessageQueue,
        mock_sender: AsyncMock,
    ) -> None:
        """Test starting and stopping the queue."""
        await queue.start()
        assert queue._running is True

        await queue.enqueue("Test")
        await asyncio.sleep(0.1)  # Allow processing
        assert mock_sender.called

        await queue.stop()
        assert queue._running is False
```

### References

- [Source: epics.md#Story 9.12] - 原始 Story 定义
- [Source: 9-2-notification-message-sending.md] - TelegramNotifier 实现
- [Source: 9-11-cmd-remote-control.md] - 前一个故事学习
- [Source: architecture.md#Logging Patterns] - 日志格式和 emoji
- [Source: Telegram Bot API 文档] - https://core.telegram.org/bots/api
- [Source: python-telegram-bot 文档] - https://docs.python-telegram-bot.org/
- [Source: 令牌桶算法] - https://en.wikipedia.org/wiki/Token_bucket

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
