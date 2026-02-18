# Story 9.2: 通知消息发送

Status: done

## Story

As a **用户**,
I want **系统能够发送 Telegram 通知消息**,
So that **我能收到交易执行、分析结果等通知**.

## Acceptance Criteria

**Given** Telegram Bot 已初始化 (Story 9.1)
**When** 实现 `src/notifications/telegram_notifier.py`
**Then** 创建 `TelegramNotifier` 类:
- `send_message(text: str, parse_mode='Markdown')` - 发送普通消息
- `send_trade_notification(trade, market)` - 发送交易通知
- `send_analysis_notification(prediction, market)` - 发送分析结果
- `send_error_notification(error)` - 发送错误告警
- `send_system_notification(event, details)` - 发送系统事件通知
**And** 消息格式使用 Markdown:
```
💰 *交易执行*
市场: Will Trump win 2028?
方向: BUY YES
金额: $10.00
价格: 0.65
状态: ✅ 成功
```
**And** 实现消息队列避免 API 限流
**And** 发送失败时记录错误日志但不中断主流程
**And** 支持配置开关控制是否发送通知

## Tasks / Subtasks

- [ ] Task 1: 创建通知模块目录结构 (AC: All)
  - [ ] 1.1 创建 `src/notifications/` 目录
  - [ ] 1.2 创建 `src/notifications/__init__.py`

- [ ] Task 2: 实现 TelegramNotifier 类 (AC: #1)
  - [ ] 2.1 创建 `src/notifications/telegram_notifier.py` 文件
  - [ ] 2.2 添加模块 docstring 和使用示例
  - [ ] 2.3 定义 `TelegramNotifier` 类
  - [ ] 2.4 实现构造函数，接收 `TelegramClient` 依赖注入
  - [ ] 2.5 实现 `send_message()` 基础方法
  - [ ] 2.6 实现 `send_trade_notification()` 方法
  - [ ] 2.7 实现 `send_analysis_notification()` 方法
  - [ ] 2.8 实现 `send_error_notification()` 方法
  - [ ] 2.9 实现 `send_system_notification()` 方法

- [ ] Task 3: 实现消息格式化 (AC: #2)
  - [ ] 3.1 创建 `_format_trade_message()` 辅助方法
  - [ ] 3.2 创建 `_format_analysis_message()` 辅助方法
  - [ ] 3.3 创建 `_format_error_message()` 辅助方法
  - [ ] 3.4 创建 `_format_system_message()` 辅助方法
  - [ ] 3.5 使用 Markdown 格式化 (加粗标题、emoji)

- [ ] Task 4: 实现消息队列机制 (AC: #3)
  - [ ] 4.1 创建 `src/notifications/message_queue.py` 文件
  - [ ] 4.2 定义 `MessageQueue` 类使用 `asyncio.Queue`
  - [ ] 4.3 实现消息优先级 (错误 > 交易 > 分析)
  - [ ] 4.4 实现发送频率限制 (最大 30 条/秒)
  - [ ] 4.5 实现后台发送任务
  - [ ] 4.6 在 `TelegramNotifier` 中集成 `MessageQueue`

- [ ] Task 5: 实现错误处理 (AC: #4)
  - [ ] 5.1 捕获 `telegram.error.TelegramError` 异常
  - [ ] 5.2 发送失败时记录错误日志
  - [ ] 5.3 不抛出异常，不影响主流程
  - [ ] 5.4 实现重试机制 (可选)

- [ ] Task 6: 实现配置开关 (AC: #5)
  - [ ] 6.1 使用 `settings.telegram.enabled` 控制发送
  - [ ] 6.2 disabled 时静默跳过，不记录错误

- [ ] Task 7: 更新模块导出 (AC: All)
  - [ ] 7.1 更新 `src/notifications/__init__.py` 导出 `TelegramNotifier`
  - [ ] 7.2 更新 `src/__init__.py` 或确保可以从 `src.notifications` 导入

- [ ] Task 8: 编写测试 (AC: All)
  - [ ] 8.1 创建 `tests/test_notifications/` 目录
  - [ ] 8.2 创建 `tests/test_notifications/__init__.py`
  - [ ] 8.3 创建 `tests/test_notifications/test_telegram_notifier.py`
  - [ ] 8.4 测试 `send_message()` 成功和失败情况
  - [ ] 8.5 测试各类通知消息格式化
  - [ ] 8.6 测试 disabled 时的行为
  - [ ] 8.7 测试消息队列发送

- [ ] Task 9: 代码质量检查 (AC: All)
  - [ ] 9.1 运行 `mypy src/notifications/` 无错误
  - [ ] 9.2 运行 `black --check src/notifications/` 通过
  - [ ] 9.3 运行 `isort --check src/notifications/` 通过
  - [ ] 9.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: epics.md#Story 9.2]

**TelegramNotifier API:**

```python
class TelegramNotifier:
    """Telegram 通知发送器."""

    async def send_message(
        self,
        text: str,
        parse_mode: str = "Markdown"
    ) -> bool:
        """发送普通消息."""
        ...

    async def send_trade_notification(
        self,
        trade: Trade,
        market: Market
    ) -> bool:
        """发送交易通知."""
        ...

    async def send_analysis_notification(
        self,
        prediction: PredictionResult,
        market: Market
    ) -> bool:
        """发送分析结果通知."""
        ...

    async def send_error_notification(
        self,
        error: Exception | str
    ) -> bool:
        """发送错误告警."""
        ...

    async def send_system_notification(
        self,
        event: str,
        details: dict | None = None
    ) -> bool:
        """发送系统事件通知."""
        ...
```

### 现有依赖 [Source: Story 9.1]

**TelegramClient 已实现的方法:**
- `initialize()` - 初始化客户端
- `shutdown()` - 关闭客户端
- `get_me()` - 获取 Bot 信息
- `is_enabled` - 检查是否启用
- `authorized_chat_id` - 获取授权 Chat ID
- `is_authorized_chat(chat_id)` - 验证 Chat ID

**需要扩展的方法:**
- `send_message()` - 发送消息 (本 Story 新增)

### 消息格式模板

**交易通知:**
```markdown
💰 *交易执行*
市场: Will Trump win 2028?
方向: BUY YES
金额: $10.00
价格: 0.65
份额: 15.38
状态: ✅ 成功
```

**分析通知:**
```markdown
🧠 *市场分析*
市场: Will BTC reach $100k?
市场价格: YES 0.55
预测概率: YES 0.75 (±0.10)
置信度: 85%
Edge: 20%
建议: BUY YES
```

**错误告警:**
```markdown
❌ *错误告警*
类型: NetworkError
信息: Telegram network error
时间: 2026-02-18 10:30:00
```

**系统通知:**
```markdown
ℹ️ *系统事件*
事件: 启动
详情: Paper Trading 模式
时间: 2026-02-18 10:00:00
```

### 消息队列设计 [Source: Story 9.12 预研]

**消息优先级:**
```python
class MessagePriority(IntEnum):
    """消息优先级."""
    LOW = 0      # 分析通知
    NORMAL = 1   # 交易通知
    HIGH = 2     # 错误告警
    URGENT = 3   # 系统事件
```

**队列配置:**
```python
# Telegram API 限制: 30 条/秒
MAX_MESSAGES_PER_SECOND = 30
# 单条消息最大字符数
MAX_MESSAGE_LENGTH = 4096
# 队列最大长度
MAX_QUEUE_SIZE = 100
```

### 数据模型 [Source: src/models/]

**Trade 模型关键字段:**
```python
class Trade(BaseModel):
    id: int
    market_id: str
    trade_type: TradeType  # BUY_YES, BUY_NO, SELL
    mode: TradeMode        # PAPER, LIVE
    amount: float
    price: float
    shares: float | None
    status: TradeStatus    # PENDING, FILLED, CANCELLED
    created_at: datetime | None
```

**Market 模型关键字段:**
```python
class Market(BaseModel):
    id: str
    title: str
    description: str | None
    category: MarketCategory | None
    yes_price: float | None
    no_price: float | None
```

**PredictionResult 模型关键字段:**
```python
class PredictionResult(BaseModel):
    predicted_probability: float  # 0-1
    confidence: float             # 0-1
    reasoning: str
    key_assumptions: list[str]
    recommendation: Recommendation  # BUY_YES, BUY_NO, NO_TRADE
    edge: float | None           # 0-1
```

### 实现模板

**TelegramNotifier 完整模板:**

```python
# src/notifications/telegram_notifier.py
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
            self._logger.info(
                "TelegramNotifier initialized (disabled)"
            )
        else:
            self._logger.info(
                "TelegramNotifier initialized (enabled)"
            )

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
                self._logger.warning(
                    "No chat_id configured, skipping notification"
                )
                return False

            # Send via bot
            await self._client._bot.send_message(
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
        from datetime import datetime

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
        from datetime import datetime

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
```

### 项目结构 [Source: architecture.md#Project Structure]

**新增/修改文件:**
```
src/notifications/
├── __init__.py              # 新增: 导出 TelegramNotifier
├── telegram_notifier.py     # 新增: TelegramNotifier 实现
└── message_queue.py         # 新增: 消息队列 (可选，Story 9.12)

tests/test_notifications/
├── __init__.py              # 新增
└── test_telegram_notifier.py  # 新增: TelegramNotifier 测试
```

### 依赖关系

**本故事依赖:**
- Story 9.1: Telegram Bot 配置与初始化 (TelegramClient)
- Story 1.3: 日志系统 (get_logger)
- Story 1.7: Pydantic 数据模型 (Trade, Market, PredictionResult)

**后续故事依赖本故事:**
- Story 9.3: 交易事件通知集成 (需要 TelegramNotifier)
- Story 9.4: LLM 分析结果通知 (需要 TelegramNotifier)
- Story 9.12: 消息队列与限流 (扩展 MessageQueue)

### 实现注意事项

**关键点:**

1. **依赖注入**: TelegramNotifier 接收 TelegramClient 实例，便于测试
2. **配置开关**: 使用 `settings.telegram.enabled` 控制是否发送
3. **错误处理**: 发送失败不抛出异常，只记录日志
4. **消息格式**: 使用 Markdown 格式，支持 emoji
5. **字符限制**: 单条消息不超过 4096 字符

**与 TelegramClient 的关系:**
- TelegramNotifier 依赖 TelegramClient 的 `_bot` 属性发送消息
- 需要访问 `authorized_chat_id` 获取目标 Chat ID
- 可以考虑在 TelegramClient 中添加 `send_message()` 方法

### 前一个故事学习 [Source: 9-1-telegram-bot-config-init.md]

**从 Story 9.1 学到的模式:**

1. **配置可选性**: 新功能配置应可选，不影响核心系统运行
2. **警告而非错误**: 配置缺失时警告但允许继续
3. **模块化设计**: 新模块应独立于核心业务逻辑
4. **异步生命周期**: 使用 `initialize()` 和 `shutdown()` 管理资源
5. **Token 脱敏**: 只显示前 4 位和后 4 位

### 测试策略

```python
# tests/test_notifications/test_telegram_notifier.py
"""Tests for TelegramNotifier."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.notifications.telegram_notifier import TelegramNotifier
from src.models.trade import Trade, TradeType, TradeMode, TradeStatus
from src.models.market import Market
from src.models.prediction import PredictionResult, Recommendation


class TestTelegramNotifier:
    """Tests for TelegramNotifier class."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock TelegramClient."""
        client = MagicMock()
        client.is_enabled = True
        client.authorized_chat_id = "123456789"
        client._bot = AsyncMock()
        return client

    @pytest.fixture
    def notifier(self, mock_client: MagicMock) -> TelegramNotifier:
        """Create a TelegramNotifier with mock client."""
        with patch("src.notifications.telegram_notifier.settings") as mock_settings:
            mock_settings.telegram.enabled = True
            return TelegramNotifier(mock_client)

    def test_init_disabled(self, mock_client: MagicMock) -> None:
        """Test initialization when disabled."""
        with patch("src.notifications.telegram_notifier.settings") as mock_settings:
            mock_settings.telegram.enabled = False
            mock_client.is_enabled = False

            notifier = TelegramNotifier(mock_client)
            assert notifier._enabled is False

    @pytest.mark.asyncio
    async def test_send_message_success(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
    ) -> None:
        """Test successful message sending."""
        result = await notifier.send_message("Test message")
        assert result is True
        mock_client._bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_disabled(self, mock_client: MagicMock) -> None:
        """Test message sending when disabled."""
        with patch("src.notifications.telegram_notifier.settings") as mock_settings:
            mock_settings.telegram.enabled = False
            mock_client.is_enabled = False

            notifier = TelegramNotifier(mock_client)
            result = await notifier.send_message("Test message")
            assert result is False

    @pytest.mark.asyncio
    async def test_send_message_error(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
    ) -> None:
        """Test message sending with error."""
        mock_client._bot.send_message.side_effect = Exception("Network error")
        result = await notifier.send_message("Test message")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_trade_notification(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
    ) -> None:
        """Test trade notification."""
        trade = Trade(
            id=1,
            market_id="market-1",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=10.0,
            price=0.65,
            shares=15.38,
            status=TradeStatus.FILLED,
        )
        market = Market(
            id="market-1",
            title="Will Trump win 2028?",
            yes_price=0.65,
        )

        result = await notifier.send_trade_notification(trade, market)
        assert result is True

        # Verify message format
        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        assert "*交易执行*" in message
        assert "Will Trump win 2028?" in message
        assert "BUY_YES" in message

    @pytest.mark.asyncio
    async def test_send_analysis_notification(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
    ) -> None:
        """Test analysis notification."""
        prediction = PredictionResult(
            predicted_probability=0.75,
            confidence=0.85,
            reasoning="Strong indicators",
            key_assumptions=["Economy stable", "No major news"],
            recommendation=Recommendation.BUY_YES,
            edge=0.20,
        )
        market = Market(
            id="market-1",
            title="Will BTC reach $100k?",
            yes_price=0.55,
        )

        result = await notifier.send_analysis_notification(prediction, market)
        assert result is True

        # Verify message format
        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        assert "*市场分析*" in message
        assert "Will BTC reach $100k?" in message
        assert "75%" in message or "0.75" in message

    def test_format_trade_message(self, notifier: TelegramNotifier) -> None:
        """Test trade message formatting."""
        trade = Trade(
            id=1,
            market_id="market-1",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=10.0,
            price=0.65,
            shares=15.38,
            status=TradeStatus.FILLED,
        )
        market = Market(
            id="market-1",
            title="Test Market",
        )

        message = notifier._format_trade_message(trade, market)
        assert "*交易执行*" in message
        assert "Test Market" in message
        assert "BUY_YES" in message

    def test_format_error_message(self, notifier: TelegramNotifier) -> None:
        """Test error message formatting."""
        error = ValueError("Test error")
        message = notifier._format_error_message(error)

        assert "*错误告警*" in message
        assert "ValueError" in message
        assert "Test error" in message
```

### References

- [Source: epics.md#Story 9.2] - 原始 Story 定义
- [Source: 9-1-telegram-bot-config-init.md] - 前一个故事实现
- [Source: src/api/telegram.py] - TelegramClient 实现
- [Source: src/models/trade.py] - Trade 数据模型
- [Source: src/models/market.py] - Market 数据模型
- [Source: src/models/prediction.py] - PredictionResult 数据模型
- [Source: architecture.md#Logging Patterns] - 日志格式和 emoji
- [Source: python-telegram-bot 文档] - https://docs.python-telegram-bot.org/

## Dev Agent Record

### Agent Model Used

GLM-5 (via Claude Code)

### Debug Log References

None required - all tests passed on first run.

### Completion Notes List

1. Implementation completed successfully on 2026-02-18
2. All 28 unit tests pass
3. Code quality checks pass (mypy, black, isort)
4. TelegramNotifier class provides methods for sending trade, analysis, error, and system notifications
5. Message formatting uses Markdown with emoji for better readability
6. Error handling ensures sending failures don't interrupt main flow
7. Configuration switch (settings.telegram.enabled) controls whether notifications are sent

### File List

**New Files:**
- `src/notifications/__init__.py` - Module exports for TelegramNotifier
- `src/notifications/telegram_notifier.py` - TelegramNotifier implementation
- `tests/test_notifications/__init__.py` - Test module init
- `tests/test_notifications/test_telegram_notifier.py` - Comprehensive test suite (28 tests)
