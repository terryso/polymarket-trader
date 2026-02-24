# Story 10.5: 退出通知集成

Status: done

## Story

As a **用户**,
I want **在持仓自动退出时收到 Telegram 通知**,
So that **我能实时了解系统的退出操作和盈亏结果**.

## Acceptance Criteria

**Given** Epic 9 Telegram 通知已实现
**When** 在 `src/notifications/telegram_notifier.py` 添加退出通知
**Then** 创建 `send_exit_notification` 方法:

1. **在 `src/notifications/telegram_notifier.py` 添加退出通知方法:**
   - `send_exit_notification(position, market, pnl, pnl_pct, exit_reason)` - 发送退出通知
   - `_format_exit_message(position, market, pnl, pnl_pct, exit_reason)` - 格式化消息

2. **退出通知消息格式:**
   ```
   🚪 *持仓退出*
   市场: Will Trump win 2028?
   方向: YES
   退出原因: 止盈
   份额: 15.38
   成本: $10.00
   收益: $12.50
   盈亏: 📈 +$2.50 (+25%)
   时间: 2026-02-25 10:30:00
   ```

3. **在 `src/trading/exit_scheduler.py` 集成通知:**
   - 添加 `notifier: TelegramNotifier | None` 参数到 `ExitScheduler` 构造函数
   - 在成功退出后发送 `send_exit_notification`
   - 在退出失败时发送 `send_error_notification`
   - 通知发送失败不影响主流程

4. **使用消息队列优先级:**
   - 退出通知使用 `MessagePriority.NORMAL` (与交易通知同级)
   - 分类使用 `MessageCategory.TRADE`

5. **支持不同退出原因的显示:**
   - `take_profit` -> "止盈"
   - `stop_loss` -> "止损"
   - `time_exit` -> "时间退出"
   - `signal_exit` -> "信号反转"
   - `manual` -> "手动退出"

6. **盈亏显示格式:**
   - 盈利: 📈 绿色上涨图表
   - 亏损: 📉 红色下跌图表
   - 正数显示 `+` 前缀
   - 百分比保留1位小数

## Tasks / Subtasks

- [ ] Task 1: 扩展 TelegramNotifier (AC: #1, #2, #4, #5, #6)
  - [ ] 1.1 添加 `send_exit_notification` 方法签名
  - [ ] 1.2 添加 `_format_exit_message` 格式化方法
  - [ ] 1.3 实现退出原因中文映射 (take_profit -> 止盈 等)
  - [ ] 1.4 实现盈亏 emoji 和格式化 (盈利📈/亏损📉, +前缀)
  - [ ] 1.5 使用 MessagePriority.NORMAL 和 MessageCategory.TRADE
  - [ ] 1.6 更新 `src/notifications/__init__.py` (如需要)

- [ ] Task 2: 修改 ExitScheduler 构造函数 (AC: #3)
  - [ ] 2.1 添加 `notifier: TelegramNotifier | None` 参数
  - [ ] 2.2 存储 notifier 到实例变量
  - [ ] 2.3 记录日志说明通知是否启用
  - [ ] 2.4 保持向后兼容 (notifier 可选)

- [ ] Task 3: 实现退出成功通知 (AC: #3)
  - [ ] 3.1 在退出成功后调用 `notifier.send_exit_notification()`
  - [ ] 3.2 传递 position, market, pnl, pnl_pct, exit_reason 参数
  - [ ] 3.3 处理通知发送失败 (不影响主流程)
  - [ ] 3.4 记录通知发送状态日志

- [ ] Task 4: 实现退出失败通知 (AC: #3)
  - [ ] 4.1 在退出失败后调用 `notifier.send_error_notification()`
  - [ ] 4.2 构造有意义的错误消息
  - [ ] 4.3 处理通知发送失败 (不影响主流程)

- [ ] Task 5: 编写测试 (AC: All)
  - [ ] 5.1 创建 `tests/test_notifications/test_exit_notification.py`
  - [ ] 5.2 测试退出通知消息格式
  - [ ] 5.3 测试不同退出原因的显示
  - [ ] 5.4 测试盈亏格式化 (正数/负数)
  - [ ] 5.5 测试 notifier 为 None 时行为
  - [ ] 5.6 测试通知发送失败不影响主流程
  - [ ] 5.7 扩展 `tests/test_trading/test_exit_scheduler.py` 添加通知集成测试

- [ ] Task 6: 代码质量检查 (AC: All)
  - [ ] 6.1 运行 `mypy src/notifications/telegram_notifier.py` 无错误
  - [ ] 6.2 运行 `mypy src/trading/exit_scheduler.py` 无错误
  - [ ] 6.3 运行 `black --check src/` 通过
  - [ ] 6.4 运行 `isort --check src/` 通过
  - [ ] 6.5 运行完整测试套件确保通过

## Dev Notes

### 现有代码分析

**TelegramNotifier (`src/notifications/telegram_notifier.py`):**
- 已有 `send_position_closed_notification` 方法 (Story 9.3)
- 使用消息队列进行限流 (Story 9.12)
- 支持多种消息类型: 交易、分析、错误、系统事件

**ExitScheduler (`src/trading/exit_scheduler.py`):**
- 定期检查持仓退出条件
- 调用 `ExitChecker` 检查退出条件
- 调用 `LiveTradingExecutor.sell_position` 执行卖出
- 当前没有通知集成

**ExitReason 枚举 (`src/trading/exit_checker.py`):**
```python
class ExitReason(str, Enum):
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TIME_EXIT = "time_exit"
    SIGNAL_EXIT = "signal_exit"
```

### 实现模板

**TelegramNotifier 扩展:**

```python
# src/notifications/telegram_notifier.py (添加新方法)

# 退出原因中文映射
EXIT_REASON_MAP = {
    "take_profit": "止盈",
    "stop_loss": "止损",
    "time_exit": "时间退出",
    "signal_exit": "信号反转",
    "manual": "手动退出",
}

async def send_exit_notification(
    self,
    position: "Position",
    market: "Market",
    pnl: float,
    pnl_pct: float,
    exit_reason: str,
) -> bool:
    """Send an exit notification.

    Story 10.5: 退出通知集成

    Args:
        position: The exited position
        market: The market for the position
        pnl: Realized profit/loss in USD
        pnl_pct: Profit/loss percentage
        exit_reason: Reason for exit (take_profit, stop_loss, etc.)

    Returns:
        True if sent successfully, False otherwise
    """
    message = self._format_exit_message(
        position, market, pnl, pnl_pct, exit_reason
    )

    if self._queue:
        return await self._queue.enqueue(
            text=message,
            priority=MessagePriority.NORMAL,
            category=MessageCategory.TRADE,
        )

    return await self.send_message(message)

def _format_exit_message(
    self,
    position: "Position",
    market: "Market",
    pnl: float,
    pnl_pct: float,
    exit_reason: str,
) -> str:
    """Format an exit notification message.

    Args:
        position: The exited position
        market: The market for the position
        pnl: Realized profit/loss in USD
        pnl_pct: Profit/loss percentage
        exit_reason: Reason for exit

    Returns:
        Formatted Markdown message
    """
    # Get localized exit reason
    reason_display = EXIT_REASON_MAP.get(exit_reason, exit_reason)

    # Choose emoji based on profit/loss
    pnl_emoji = "\U0001f4c8" if pnl >= 0 else "\U0001f4c9"  # chart_up / chart_down
    pnl_sign = "+" if pnl >= 0 else ""

    lines = [
        "\U0001f6aa *持仓退出*",  # door emoji
        f"市场: {market.title}",
        f"方向: {position.outcome.value}",
        f"退出原因: {reason_display}",
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
```

**ExitScheduler 修改:**

```python
# src/trading/exit_scheduler.py (修改)

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.notifications.telegram_notifier import TelegramNotifier

class ExitScheduler:
    """Scheduler for automated exit strategy execution.

    Story 10.5: Added Telegram notification support for exit events.
    """

    def __init__(
        self,
        # ... existing parameters ...
        notifier: "TelegramNotifier | None" = None,
    ) -> None:
        """Initialize ExitScheduler.

        Args:
            # ... existing args ...
            notifier: Optional Telegram notifier for exit notifications
        """
        # ... existing initialization ...
        self._notifier = notifier

        # Log notification status
        if self._notifier:
            self._logger.info("ExitScheduler initialized (notifications=enabled)")
        else:
            self._logger.info("ExitScheduler initialized (notifications=disabled)")

    async def _execute_exit(
        self,
        position: Position,
        market: Market,
        exit_reason: str,
    ) -> bool:
        """Execute exit for a position.

        Story 10.5: Added notification support.
        """
        try:
            # Execute sell
            result = await self._executor.sell_position(
                position=position,
                reason=exit_reason,
            )

            if result.success:
                # Send success notification
                await self._notify_exit_success(
                    position=position,
                    market=market,
                    pnl=result.realized_pnl,
                    pnl_pct=result.realized_pnl / position.initial_value if position.initial_value else 0,
                    exit_reason=exit_reason,
                )
                return True
            else:
                # Send failure notification
                await self._notify_exit_failed(
                    position=position,
                    market=market,
                    error_message=result.error_message or "Unknown error",
                )
                return False

        except Exception as e:
            self._logger.error(f"Exit execution failed: {e}")
            await self._notify_exit_failed(
                position=position,
                market=market,
                error_message=str(e),
            )
            return False

    async def _notify_exit_success(
        self,
        position: Position,
        market: Market,
        pnl: float,
        pnl_pct: float,
        exit_reason: str,
    ) -> None:
        """Send exit success notification."""
        if not self._notifier:
            return

        try:
            success = await self._notifier.send_exit_notification(
                position=position,
                market=market,
                pnl=pnl,
                pnl_pct=pnl_pct,
                exit_reason=exit_reason,
            )
            if success:
                self._logger.debug(f"Exit notification sent for position {position.id}")
            else:
                self._logger.warning(f"Failed to send exit notification for position {position.id}")
        except Exception as e:
            self._logger.error(f"Error sending exit notification: {e}")

    async def _notify_exit_failed(
        self,
        position: Position,
        market: Market,
        error_message: str,
    ) -> None:
        """Send exit failure notification."""
        if not self._notifier:
            return

        try:
            error_msg = f"Exit failed for {market.title} (position {position.id}): {error_message}"
            await self._notifier.send_error_notification(error_msg)
        except Exception as e:
            self._logger.error(f"Error sending exit failure notification: {e}")
```

### 项目结构 [Source: architecture.md#Project Structure]

**修改文件:**
```
src/notifications/
└── telegram_notifier.py     # 修改: 添加退出通知方法

src/trading/
└── exit_scheduler.py        # 修改: 添加通知集成

tests/test_notifications/
└── test_exit_notification.py  # 新增: 退出通知测试

tests/test_trading/
└── test_exit_scheduler.py   # 修改: 添加通知集成测试
```

### 依赖关系

**本故事依赖:**
- Story 9.1: Telegram Bot 配置与初始化 (TelegramClient)
- Story 9.2: 通知消息发送 (TelegramNotifier)
- Story 9.3: 交易事件通知集成 (通知模式)
- Story 9.12: 消息队列与限流 (MessageQueue, MessagePriority)
- Story 10.1: 卖出执行器 (LiveTradingExecutor.sell_position)
- Story 10.3: 退出条件检查器 (ExitReason 枚举)
- Story 10.4: 退出策略调度 (ExitScheduler)

### 实现注意事项

**关键点:**

1. **可选依赖注入**: TelegramNotifier 是可选的，不影响核心退出功能
2. **错误隔离**: 通知发送失败不影响退出执行
3. **向后兼容**: 现有代码无需修改即可继续工作
4. **日志记录**: 记录通知发送状态，便于调试
5. **消息优先级**: 退出通知使用 NORMAL 优先级，与交易通知同级

**与现有代码的集成:**
- ExitScheduler 通过构造函数接收 notifier
- 主入口 (main.py) 负责创建和注入 notifier
- 通知发送使用 try/except 包装，确保异常不传播

### 前一个故事学习 [Source: 9-3-trade-event-notification.md]

**从 Story 9.3 学到的模式:**

1. **依赖注入**: TelegramNotifier 通过构造函数注入
2. **错误处理**: 发送失败不抛出异常，只记录日志
3. **消息格式**: 使用 Markdown 格式，支持 emoji
4. **返回值**: 发送方法返回 bool 表示成功/失败
5. **通知隔离**: 通知逻辑在独立方法中，不污染主流程

### 测试策略

```python
# tests/test_notifications/test_exit_notification.py
"""Tests for exit notification.

Story 10.5: 退出通知集成
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.notifications.telegram_notifier import TelegramNotifier, EXIT_REASON_MAP


class TestExitNotification:
    """Tests for exit notification functionality."""

    @pytest.fixture
    def mock_client(self) -> AsyncMock:
        """Create a mock TelegramClient."""
        client = AsyncMock()
        client.is_enabled = True
        client.authorized_chat_id = 123456
        client._bot = AsyncMock()
        return client

    @pytest.fixture
    def sample_position(self) -> MagicMock:
        """Create a sample position."""
        position = MagicMock()
        position.id = 1
        position.market_id = "market-1"
        position.outcome = MagicMock(value="YES")
        position.shares = 15.38
        position.initial_value = 10.0
        position.current_value = 12.5
        return position

    @pytest.fixture
    def sample_market(self) -> MagicMock:
        """Create a sample market."""
        market = MagicMock()
        market.id = "market-1"
        market.title = "Will Trump win 2028?"
        return market

    def test_exit_reason_mapping(self) -> None:
        """Test exit reason Chinese mapping."""
        assert EXIT_REASON_MAP["take_profit"] == "止盈"
        assert EXIT_REASON_MAP["stop_loss"] == "止损"
        assert EXIT_REASON_MAP["time_exit"] == "时间退出"
        assert EXIT_REASON_MAP["signal_exit"] == "信号反转"
        assert EXIT_REASON_MAP["manual"] == "手动退出"

    def test_format_exit_message_profit(
        self,
        mock_client: AsyncMock,
        sample_position: MagicMock,
        sample_market: MagicMock,
    ) -> None:
        """Test exit message formatting with profit."""
        notifier = TelegramNotifier(mock_client, use_queue=False)

        message = notifier._format_exit_message(
            position=sample_position,
            market=sample_market,
            pnl=2.5,
            pnl_pct=0.25,
            exit_reason="take_profit",
        )

        assert "持仓退出" in message
        assert "止盈" in message
        assert "+$2.50" in message
        assert "+25.0%" in message

    def test_format_exit_message_loss(
        self,
        mock_client: AsyncMock,
        sample_position: MagicMock,
        sample_market: MagicMock,
    ) -> None:
        """Test exit message formatting with loss."""
        notifier = TelegramNotifier(mock_client, use_queue=False)

        message = notifier._format_exit_message(
            position=sample_position,
            market=sample_market,
            pnl=-1.5,
            pnl_pct=-0.15,
            exit_reason="stop_loss",
        )

        assert "止损" in message
        assert "-$1.50" in message
        assert "-15.0%" in message

    @pytest.mark.asyncio
    async def test_send_exit_notification_success(
        self,
        mock_client: AsyncMock,
        sample_position: MagicMock,
        sample_market: MagicMock,
    ) -> None:
        """Test successful exit notification."""
        notifier = TelegramNotifier(mock_client, use_queue=False)

        result = await notifier.send_exit_notification(
            position=sample_position,
            market=sample_market,
            pnl=2.5,
            pnl_pct=0.25,
            exit_reason="take_profit",
        )

        assert result is True
        mock_client._bot.send_message.assert_called_once()
```

### References

- [Source: epics.md#Story 10.5] - 原始 Story 定义
- [Source: 9-3-trade-event-notification.md] - 交易通知模式参考
- [Source: src/notifications/telegram_notifier.py] - TelegramNotifier 现有实现
- [Source: src/trading/exit_checker.py] - ExitReason 枚举定义
- [Source: src/trading/exit_scheduler.py] - ExitScheduler 实现
- [Source: architecture.md#Logging Patterns] - 日志格式和 emoji
- [Source: architecture.md#API & Communication Patterns] - 错误处理模式

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

- `src/notifications/telegram_notifier.py` (modified) - 添加 send_exit_notification 方法
- `src/trading/exit_scheduler.py` (modified) - 添加 notifier 参数和通知集成
- `tests/test_notifications/test_exit_notification.py` (new) - 退出通知测试
- `tests/test_trading/test_exit_scheduler.py` (modified) - 通知集成测试
