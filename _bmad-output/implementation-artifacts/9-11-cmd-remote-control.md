# Story 9.11: Telegram 命令处理 - 远程控制

Status: ready-for-dev

## Story

As a **用户**,
I want **通过 Telegram 命令远程控制系统**,
So that **我能远程开启/关闭交易、切换模式**.

## Acceptance Criteria

**Given** 所有查询命令已实现 (Story 9.5-9.10)
**When** 添加控制命令
**Then** 实现以下控制命令:

**交易开关:**
- `/enable` - 启用交易
- `/disable` - 禁用交易
- 返回确认消息并记录审计日志

**模式切换:**
- `/mode` - 显示当前模式
- `/mode paper` - 切换到 Paper Trading
- `/mode live` - 切换到 Live Trading (需二次确认)

**安全机制:**
- 切换到 Live 模式需要二次确认
- 所有控制命令记录审计日志
- 发送安全短语确认身份 (可选配置)
```
⚠️ *安全确认*
即将切换到 LIVE 模式
回复 /confirm live 在 30 秒内确认
```
**And** 控制成功后发送通知确认
**And** 更新 ThreadSafeState 状态

## Tasks / Subtasks

- [ ] Task 1: 扩展命令处理模块 (AC: #1)
  - [ ] 1.1 在 `src/telegram_commands/handlers.py` 添加 `create_enable_handler()`
  - [ ] 1.2 添加 `create_disable_handler()`
  - [ ] 1.3 添加 `create_mode_handler()`
  - [ ] 1.4 添加 `create_confirm_mode_handler()` 用于模式切换确认
  - [ ] 1.5 在 `setup_command_handlers()` 中注册 `/enable`, `/disable`, `/mode` 命令

- [ ] Task 2: 实现交易启用/禁用 (AC: #1)
  - [ ] 2.1 `/enable` 调用 `ThreadSafeState.set_trading_enabled(True)`
  - [ ] 2.2 `/disable` 调用 `ThreadSafeState.set_trading_enabled(False)`
  - [ ] 2.3 格式化确认消息
  - [ ] 2.4 记录审计日志 (谁在何时执行了什么操作)

- [ ] Task 3: 实现模式查询 (AC: #1)
  - [ ] 3.1 `/mode` 无参数时显示当前模式
  - [ ] 3.2 从 `settings.paper_trading` 获取当前模式
  - [ ] 3.3 格式化模式显示消息

- [ ] Task 4: 实现模式切换 (AC: #1, #2)
  - [ ] 4.1 `/mode paper` 直接切换到 Paper Trading
  - [ ] 4.2 `/mode live` 触发安全确认流程
  - [ ] 4.3 存储待确认的模式切换请求
  - [ ] 4.4 `/confirm live` 完成切换
  - [ ] 4.5 设置确认超时 (30 秒)

- [ ] Task 5: 实现安全确认机制 (AC: #2)
  - [ ] 5.1 创建 `PendingModeChange` 类存储待确认状态
  - [ ] 5.2 使用模块级字典存储待确认请求
  - [ ] 5.3 验证确认短语 `/confirm live`
  - [ ] 5.4 超时自动取消待确认状态

- [ ] Task 6: 实现审计日志 (AC: #1, #2)
  - [ ] 6.1 创建 `src/telegram_commands/audit.py` 模块
  - [ ] 6.2 实现 `log_audit_event()` 函数
  - [ ] 6.3 记录事件类型: ENABLE_TRADING, DISABLE_TRADING, MODE_CHANGE
  - [ ] 6.4 记录 chat_id, 时间戳, 操作详情

- [ ] Task 7: 实现消息格式化 (AC: #1, #2)
  - [ ] 7.1 在 `src/telegram_commands/formatters.py` 添加 `format_enable_message()`
  - [ ] 7.2 添加 `format_disable_message()`
  - [ ] 7.3 添加 `format_mode_status_message()`
  - [ ] 7.4 添加 `format_mode_change_confirmation()`
  - [ ] 7.5 添加 `format_mode_changed_message()`
  - [ ] 7.6 添加 `format_mode_change_cancelled()`

- [ ] Task 8: 更新帮助信息 (AC: #1)
  - [ ] 8.1 在 `format_help_message()` 中添加 `/enable` 命令描述
  - [ ] 8.2 添加 `/disable` 命令描述
  - [ ] 8.3 添加 `/mode` 命令描述

- [ ] Task 9: 扩展 ThreadSafeState (AC: #1)
  - [ ] 9.1 添加 `set_trading_enabled(enabled: bool)` 方法
  - [ ] 9.2 添加 `set_mode(paper_trading: bool)` 方法
  - [ ] 9.3 持久化状态到 `system_state` 表

- [ ] Task 10: 编写测试 (AC: All)
  - [ ] 10.1 在 `tests/test_telegram_commands/test_handlers.py` 添加 enable/disable handler 测试
  - [ ] 10.2 测试 `/enable` 命令成功场景
  - [ ] 10.3 测试 `/disable` 命令成功场景
  - [ ] 10.4 测试 `/mode` 无参数场景
  - [ ] 10.5 测试 `/mode paper` 场景
  - [ ] 10.6 测试 `/mode live` 确认流程
  - [ ] 10.7 测试确认超时场景
  - [ ] 10.8 测试未授权用户访问
  - [ ] 10.9 测试 formatter 函数
  - [ ] 10.10 测试审计日志记录

- [ ] Task 11: 代码质量检查 (AC: All)
  - [ ] 11.1 运行 `mypy src/telegram_commands/` 无错误
  - [ ] 11.2 运行 `black --check src/telegram_commands/` 通过
  - [ ] 11.3 运行 `isort --check src/telegram_commands/` 通过
  - [ ] 11.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: epics.md#Story 9.11]

**控制命令流程:**

1. **启用交易 - `/enable`:**
```markdown
✅ *交易已启用*

系统现在可以执行交易操作。

操作时间: 2026-02-18 10:30:00
操作者: Chat ID 123456789
```

2. **禁用交易 - `/disable`:**
```markdown
❌ *交易已禁用*

系统现在不会执行任何交易操作。

操作时间: 2026-02-18 10:30:00
操作者: Chat ID 123456789
```

3. **查看模式 - `/mode`:**
```markdown
📊 *当前模式*

模式: PAPER
交易: ✅ 启用

使用 `/mode paper` 切换到 Paper Trading
使用 `/mode live` 切换到 Live Trading
```

4. **切换到 Paper 模式 - `/mode paper`:**
```markdown
📝 *模式已切换*

从 LIVE → PAPER

所有交易将使用模拟资金执行。

操作时间: 2026-02-18 10:30:00
操作者: Chat ID 123456789
```

5. **切换到 Live 模式 - `/mode live` (需要确认):**
```markdown
⚠️ *安全确认*

即将切换到 LIVE 模式

这意味着系统将使用真实资金执行交易！

请在 30 秒内回复:
/confirm live

或回复 /cancel 取消
```

6. **确认切换 - `/confirm live`:**
```markdown
🔴 *模式已切换*

从 PAPER → LIVE

⚠️ 系统现在将使用真实资金执行交易！

操作时间: 2026-02-18 10:30:00
操作者: Chat ID 123456789
```

### 现有依赖 [Source: Story 9.5-9.10]

**命令处理框架已实现:**
- `src/telegram_commands/__init__.py` - 模块导出
- `src/telegram_commands/handlers.py` - 命令处理函数
- `src/telegram_commands/formatters.py` - 消息格式化

**已有的处理模式:**
```python
def create_xxx_handler(
    authorized_chat_id: str | None,
    state_manager: "ThreadSafeState",
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    # 1. 验证授权
    # 2. 执行操作
    # 3. 记录审计日志
    # 4. 格式化消息
    # 5. 发送响应
```

### ThreadSafeState 扩展 [Source: src/core/state.py]

**需要添加的方法:**

```python
class ThreadSafeState:
    # 现有属性...
    trading_enabled: bool
    # ...

    async def set_trading_enabled(self, enabled: bool) -> None:
        """设置交易启用状态.

        Args:
            enabled: 是否启用交易
        """
        async with self._lock:
            self.trading_enabled = enabled
            await self._persist_state()

    async def set_mode(self, paper_trading: bool) -> None:
        """设置交易模式.

        Args:
            paper_trading: True for Paper Trading, False for Live Trading
        """
        async with self._lock:
            # Update settings (runtime)
            settings.paper_trading = paper_trading
            await self._persist_state()

    async def _persist_state(self) -> None:
        """持久化状态到数据库."""
        # Save to system_state table
        pass
```

### 审计日志模块

**src/telegram_commands/audit.py:**

```python
"""Audit logging for Telegram control commands.

Story 9.11: Telegram 命令处理 - 远程控制
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
    """
    timestamp = datetime.now().isoformat()
    details_str = f" | details: {details}" if details else ""

    logger.info(
        f"📋 AUDIT | {event_type.value} | "
        f"chat_id: {chat_id} | "
        f"timestamp: {timestamp}{details_str}"
    )
```

### 实现模板

**handlers.py 扩展:**

```python
# 在 src/telegram_commands/handlers.py 中添加

from datetime import datetime, timedelta
from enum import Enum

from src.telegram_commands.audit import AuditEventType, log_audit_event


# 会话状态 - 存储待确认的模式切换
_pending_mode_changes: dict[str, "PendingModeChange"] = {}


class PendingModeChange:
    """待确认的模式切换请求."""

    def __init__(self, chat_id: str, target_mode: str):
        self.chat_id = chat_id
        self.target_mode = target_mode  # "live" or "paper"
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=30)

    def is_expired(self) -> bool:
        """检查是否已过期."""
        return datetime.now() > self.expires_at


def create_enable_handler(
    authorized_chat_id: str | None,
    state_manager: "ThreadSafeState",
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create an enable trading command handler."""

    async def enable_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /enable command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = str(update.effective_chat.id)

        # Verify authorization
        if authorized_chat_id and chat_id != str(authorized_chat_id):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Enable trading
        await state_manager.set_trading_enabled(True)

        # Log audit event
        log_audit_event(
            AuditEventType.ENABLE_TRADING,
            chat_id,
        )

        # Send confirmation
        message = format_enable_message()
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Trading enabled by chat_id: {chat_id}")

    return enable_handler


def create_disable_handler(
    authorized_chat_id: str | None,
    state_manager: "ThreadSafeState",
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a disable trading command handler."""

    async def disable_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /disable command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = str(update.effective_chat.id)

        # Verify authorization
        if authorized_chat_id and chat_id != str(authorized_chat_id):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Disable trading
        await state_manager.set_trading_enabled(False)

        # Log audit event
        log_audit_event(
            AuditEventType.DISABLE_TRADING,
            chat_id,
        )

        # Send confirmation
        message = format_disable_message()
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Trading disabled by chat_id: {chat_id}")

    return disable_handler


def create_mode_handler(
    authorized_chat_id: str | None,
    state_manager: "ThreadSafeState",
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a mode command handler."""

    async def mode_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /mode command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = str(update.effective_chat.id)

        # Verify authorization
        if authorized_chat_id and chat_id != str(authorized_chat_id):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Get current mode
        current_mode = "PAPER" if settings.paper_trading else "LIVE"

        # No args - show current mode
        if not context.args or len(context.args) == 0:
            snapshot = await state_manager.get_state()
            message = format_mode_status_message(
                current_mode=current_mode,
                trading_enabled=snapshot.trading_enabled,
            )
            await update.message.reply_text(message, parse_mode="Markdown")
            return

        # Parse target mode
        target_mode = context.args[0].lower()

        if target_mode not in ("paper", "live"):
            await update.message.reply_text(
                "❌ 无效的模式。请使用 `paper` 或 `live`。",
                parse_mode="Markdown",
            )
            return

        # Switch to Paper mode - direct
        if target_mode == "paper":
            if current_mode == "PAPER":
                await update.message.reply_text(
                    "当前已经是 PAPER 模式。",
                    parse_mode="Markdown",
                )
                return

            await state_manager.set_mode(paper_trading=True)
            log_audit_event(
                AuditEventType.MODE_CHANGE,
                chat_id,
                {"from": current_mode, "to": "PAPER"},
            )
            message = format_mode_changed_message("LIVE", "PAPER")
            await update.message.reply_text(message, parse_mode="Markdown")
            logger.info(f"Mode changed: LIVE -> PAPER by chat_id: {chat_id}")
            return

        # Switch to Live mode - requires confirmation
        if current_mode == "LIVE":
            await update.message.reply_text(
                "当前已经是 LIVE 模式。",
                parse_mode="Markdown",
            )
            return

        # Store pending mode change
        _pending_mode_changes[chat_id] = PendingModeChange(
            chat_id=chat_id,
            target_mode="live",
        )

        message = format_mode_change_confirmation()
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Mode change to LIVE requested by chat_id: {chat_id}")

    return mode_handler


def create_confirm_mode_handler(
    authorized_chat_id: str | None,
    state_manager: "ThreadSafeState",
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a confirm mode change command handler."""

    async def confirm_mode_handler(
        update: Update, context: "CallbackContext"
    ) -> None:
        """Handle /confirm command for mode change."""
        if not update.effective_chat or not update.message:
            return

        chat_id = str(update.effective_chat.id)

        # Verify authorization
        if authorized_chat_id and chat_id != str(authorized_chat_id):
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Check for pending mode change
        pending = _pending_mode_changes.get(chat_id)
        if not pending:
            await update.message.reply_text(
                "❌ 没有待确认的模式切换。请先使用 /mode live 发起请求。",
                parse_mode="Markdown",
            )
            return

        if pending.is_expired():
            del _pending_mode_changes[chat_id]
            await update.message.reply_text(
                "❌ 确认已超时 (30秒)。请重新执行 /mode live。",
                parse_mode="Markdown",
            )
            return

        # Verify confirmation phrase
        if not context.args or len(context.args) == 0 or context.args[0].lower() != "live":
            await update.message.reply_text(
                "❌ 请输入 /confirm live 确认切换到 LIVE 模式。",
                parse_mode="Markdown",
            )
            return

        # Execute mode change
        await state_manager.set_mode(paper_trading=False)
        del _pending_mode_changes[chat_id]

        log_audit_event(
            AuditEventType.CONFIRM_MODE_CHANGE,
            chat_id,
            {"from": "PAPER", "to": "LIVE"},
        )

        message = format_mode_changed_message("PAPER", "LIVE")
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Mode change confirmed: PAPER -> LIVE by chat_id: {chat_id}")

    return confirm_mode_handler


def setup_command_handlers(
    application: Application,
    state_manager: "ThreadSafeState",
    authorized_chat_id: str | None = None,
) -> None:
    """Setup all command handlers for the Telegram bot."""
    # ... existing handlers ...

    # Add control handlers
    enable_handler = create_enable_handler(authorized_chat_id, state_manager)
    disable_handler = create_disable_handler(authorized_chat_id, state_manager)
    mode_handler = create_mode_handler(authorized_chat_id, state_manager)
    confirm_mode_handler = create_confirm_mode_handler(authorized_chat_id, state_manager)

    # Register handlers
    application.add_handler(CommandHandler("enable", enable_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("disable", disable_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("mode", mode_handler))  # type: ignore[arg-type]
    # Note: /confirm is already registered by Story 9.10, we extend it here
    # If /confirm was not registered before, register it now
    if not any(h.command == "confirm" for h in application.handlers.get(0, [])):  # type: ignore[attr-defined]
        application.add_handler(CommandHandler("confirm", confirm_mode_handler))  # type: ignore[arg-type]

    logger.info(
        "Command handlers registered: /enable, /disable, /mode"
    )
```

**formatters.py 扩展:**

```python
# 在 src/telegram_commands/formatters.py 中添加

from datetime import datetime


def format_enable_message() -> str:
    """Format enable trading message.

    Returns:
        Formatted Markdown message
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return "\n".join([
        "\u2705 *交易已启用*",
        "",
        "系统现在可以执行交易操作。",
        "",
        f"操作时间: {timestamp}",
    ])


def format_disable_message() -> str:
    """Format disable trading message.

    Returns:
        Formatted Markdown message
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return "\n".join([
        "\u274c *交易已禁用*",
        "",
        "系统现在不会执行任何交易操作。",
        "",
        f"操作时间: {timestamp}",
    ])


def format_mode_status_message(
    current_mode: str,
    trading_enabled: bool,
) -> str:
    """Format mode status message.

    Args:
        current_mode: Current trading mode (PAPER/LIVE)
        trading_enabled: Whether trading is enabled

    Returns:
        Formatted Markdown message
    """
    trading_emoji = "\u2705" if trading_enabled else "\u274c"
    trading_status = "启用" if trading_enabled else "禁用"

    mode_emoji = "\U0001f4d3" if current_mode == "PAPER" else "\U0001f534"  # notebook / red circle

    return "\n".join([
        "\U0001f4ca *当前模式*",
        "",
        f"模式: {mode_emoji} {current_mode}",
        f"交易: {trading_emoji} {trading_status}",
        "",
        "使用 `/mode paper` 切换到 Paper Trading",
        "使用 `/mode live` 切换到 Live Trading",
    ])


def format_mode_change_confirmation() -> str:
    """Format mode change confirmation request.

    Returns:
        Formatted Markdown message
    """
    return "\n".join([
        "\u26a0\ufe0f *安全确认*",
        "",
        "即将切换到 LIVE 模式",
        "",
        "_这意味着系统将使用真实资金执行交易！_",
        "",
        "请在 30 秒内回复:",
        "/confirm live",
        "",
        "或回复 /cancel 取消",
    ])


def format_mode_changed_message(from_mode: str, to_mode: str) -> str:
    """Format mode changed message.

    Args:
        from_mode: Previous mode
        to_mode: New mode

    Returns:
        Formatted Markdown message
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if to_mode == "LIVE":
        warning = "\n\n\u26a0\ufe0f *系统现在将使用真实资金执行交易！*"
        emoji = "\U0001f534"  # Red circle
    else:
        warning = "\n\n所有交易将使用模拟资金执行。"
        emoji = "\U0001f4d3"  # Notebook

    return "\n".join([
        f"{emoji} *模式已切换*",
        "",
        f"从 {from_mode} \u2192 {to_mode}",
        warning,
        "",
        f"操作时间: {timestamp}",
    ])


def format_mode_change_cancelled() -> str:
    """Format mode change cancelled message.

    Returns:
        Formatted Markdown message
    """
    return "\n".join([
        "\u274c *模式切换已取消*",
        "",
        "当前模式未改变。",
    ])
```

### 更新 __init__.py

```python
# src/telegram_commands/__init__.py
__all__ = [
    "setup_command_handlers",
    # ... existing exports ...
    "create_enable_handler",   # NEW
    "create_disable_handler",  # NEW
    "create_mode_handler",     # NEW
    "create_confirm_mode_handler",  # NEW
    # ... formatter exports ...
    "format_enable_message",           # NEW
    "format_disable_message",          # NEW
    "format_mode_status_message",      # NEW
    "format_mode_change_confirmation", # NEW
    "format_mode_changed_message",     # NEW
    "format_mode_change_cancelled",    # NEW
    # ... audit exports ...
    "log_audit_event",
    "AuditEventType",
]
```

### 更新帮助信息

```python
# 在 format_help_message() 中更新
help_text = """
*可用命令:*

/status - 查看系统状态
/positions - 查看当前持仓
/stats [days] - 查看交易统计
/markets [n] [category] - 查看活跃市场
/history [n] [paper|live] - 查看交易历史
/predict [序号|市场ID] - 手动触发市场分析
/enable - 启用交易
/disable - 禁用交易
/mode [paper|live] - 查看/切换交易模式
/help - 显示帮助信息
"""
```

### 项目结构

**新增/修改的文件:**
```
src/telegram_commands/
├── __init__.py              # 添加新导出
├── handlers.py              # 添加 enable, disable, mode handlers
├── formatters.py            # 添加 format_*_message 函数
└── audit.py                 # NEW: 审计日志模块

src/core/
└── state.py                 # 扩展 set_trading_enabled, set_mode 方法

tests/test_telegram_commands/
└── test_handlers.py         # 添加 enable/disable/mode handler 测试
```

### 依赖关系

**本故事依赖:**
- Story 9.5: Telegram 命令处理 - 状态查询 (命令处理框架)
- Story 9.10: Telegram 命令处理 - 手动触发分析 (/confirm 命令模式)
- Story 4.2: 线程安全状态管理 (ThreadSafeState)

**后续故事依赖本故事:**
- Story 9.12: 消息队列与限流 (可能需要通知控制状态变化)

### 测试策略

```python
# tests/test_telegram_commands/test_handlers.py 添加

class TestEnableDisableHandlers:
    """Tests for enable/disable command handlers."""

    @pytest.fixture
    def mock_state_manager(self) -> MagicMock:
        """Create a mock state manager."""
        manager = MagicMock()
        manager.set_trading_enabled = AsyncMock()
        manager.get_state = AsyncMock(return_value=MagicMock(
            trading_enabled=True,
        ))
        return manager

    @pytest.fixture
    def mock_update(self) -> MagicMock:
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456789
        update.message = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock callback context."""
        return MagicMock(args=[])

    @pytest.mark.asyncio
    async def test_enable_handler_success(
        self,
        mock_state_manager: MagicMock,
        mock_update: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test enable handler success."""
        handler = create_enable_handler("123456789", mock_state_manager)
        await handler(mock_update, mock_context)

        mock_state_manager.set_trading_enabled.assert_called_once_with(True)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args.args[0]
        assert "*交易已启用*" in call_args

    @pytest.mark.asyncio
    async def test_disable_handler_success(
        self,
        mock_state_manager: MagicMock,
        mock_update: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test disable handler success."""
        handler = create_disable_handler("123456789", mock_state_manager)
        await handler(mock_update, mock_context)

        mock_state_manager.set_trading_enabled.assert_called_once_with(False)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args.args[0]
        assert "*交易已禁用*" in call_args

    @pytest.mark.asyncio
    async def test_enable_handler_unauthorized(
        self,
        mock_state_manager: MagicMock,
        mock_update: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test enable handler with unauthorized user."""
        handler = create_enable_handler("999888777", mock_state_manager)
        await handler(mock_update, mock_context)

        mock_state_manager.set_trading_enabled.assert_not_called()
        call_args = mock_update.message.reply_text.call_args.args[0]
        assert "*未授权访问*" in call_args


class TestModeHandler:
    """Tests for mode command handler."""

    @pytest.fixture
    def mock_state_manager(self) -> MagicMock:
        """Create a mock state manager."""
        manager = MagicMock()
        manager.set_mode = AsyncMock()
        manager.get_state = AsyncMock(return_value=MagicMock(
            trading_enabled=True,
        ))
        return manager

    @pytest.fixture
    def mock_update(self) -> MagicMock:
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456789
        update.message = AsyncMock()
        return update

    @pytest.mark.asyncio
    async def test_mode_handler_no_args(
        self,
        mock_state_manager: MagicMock,
        mock_update: MagicMock,
    ) -> None:
        """Test mode handler without args shows current mode."""
        mock_context = MagicMock(args=[])
        with patch("src.telegram_commands.handlers.settings") as mock_settings:
            mock_settings.paper_trading = True

            handler = create_mode_handler("123456789", mock_state_manager)
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args.args[0]
            assert "*当前模式*" in call_args
            assert "PAPER" in call_args

    @pytest.mark.asyncio
    async def test_mode_handler_switch_to_paper(
        self,
        mock_state_manager: MagicMock,
        mock_update: MagicMock,
    ) -> None:
        """Test mode handler switch to paper."""
        mock_context = MagicMock(args=["paper"])
        with patch("src.telegram_commands.handlers.settings") as mock_settings:
            mock_settings.paper_trading = False  # Currently LIVE

            handler = create_mode_handler("123456789", mock_state_manager)
            await handler(mock_update, mock_context)

            mock_state_manager.set_mode.assert_called_once_with(paper_trading=True)
            call_args = mock_update.message.reply_text.call_args.args[0]
            assert "*模式已切换*" in call_args

    @pytest.mark.asyncio
    async def test_mode_handler_switch_to_live_requires_confirm(
        self,
        mock_state_manager: MagicMock,
        mock_update: MagicMock,
    ) -> None:
        """Test mode handler switch to live requires confirmation."""
        mock_context = MagicMock(args=["live"])
        with patch("src.telegram_commands.handlers.settings") as mock_settings:
            mock_settings.paper_trading = True  # Currently PAPER

            handler = create_mode_handler("123456789", mock_state_manager)
            await handler(mock_update, mock_context)

            # Should NOT switch immediately
            mock_state_manager.set_mode.assert_not_called()
            call_args = mock_update.message.reply_text.call_args.args[0]
            assert "*安全确认*" in call_args


class TestConfirmModeHandler:
    """Tests for confirm mode change handler."""

    @pytest.fixture
    def mock_state_manager(self) -> MagicMock:
        """Create a mock state manager."""
        manager = MagicMock()
        manager.set_mode = AsyncMock()
        return manager

    @pytest.fixture
    def mock_update(self) -> MagicMock:
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456789
        update.message = AsyncMock()
        return update

    @pytest.mark.asyncio
    async def test_confirm_mode_no_pending(
        self,
        mock_state_manager: MagicMock,
        mock_update: MagicMock,
    ) -> None:
        """Test confirm mode without pending request."""
        mock_context = MagicMock(args=["live"])

        # Clear any pending requests
        _pending_mode_changes.clear()

        handler = create_confirm_mode_handler("123456789", mock_state_manager)
        await handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args.args[0]
        assert "没有待确认的模式切换" in call_args

    @pytest.mark.asyncio
    async def test_confirm_mode_success(
        self,
        mock_state_manager: MagicMock,
        mock_update: MagicMock,
    ) -> None:
        """Test confirm mode success."""
        mock_context = MagicMock(args=["live"])

        # Setup pending request
        from src.telegram_commands.handlers import PendingModeChange
        _pending_mode_changes["123456789"] = PendingModeChange(
            chat_id="123456789",
            target_mode="live",
        )

        handler = create_confirm_mode_handler("123456789", mock_state_manager)
        await handler(mock_update, mock_context)

        mock_state_manager.set_mode.assert_called_once_with(paper_trading=False)
        call_args = mock_update.message.reply_text.call_args.args[0]
        assert "*模式已切换*" in call_args


class TestControlFormatters:
    """Tests for control message formatters."""

    def test_format_enable_message(self) -> None:
        """Test enable message formatting."""
        message = format_enable_message()
        assert "*交易已启用*" in message
        assert "操作时间:" in message

    def test_format_disable_message(self) -> None:
        """Test disable message formatting."""
        message = format_disable_message()
        assert "*交易已禁用*" in message
        assert "操作时间:" in message

    def test_format_mode_status_message_paper(self) -> None:
        """Test mode status message for paper mode."""
        message = format_mode_status_message("PAPER", True)
        assert "*当前模式*" in message
        assert "PAPER" in message
        assert "启用" in message

    def test_format_mode_status_message_live(self) -> None:
        """Test mode status message for live mode."""
        message = format_mode_status_message("LIVE", False)
        assert "*当前模式*" in message
        assert "LIVE" in message
        assert "禁用" in message

    def test_format_mode_change_confirmation(self) -> None:
        """Test mode change confirmation message."""
        message = format_mode_change_confirmation()
        assert "*安全确认*" in message
        assert "LIVE 模式" in message
        assert "/confirm live" in message

    def test_format_mode_changed_message_to_live(self) -> None:
        """Test mode changed message to live."""
        message = format_mode_changed_message("PAPER", "LIVE")
        assert "*模式已切换*" in message
        assert "PAPER" in message
        assert "LIVE" in message
        assert "真实资金" in message

    def test_format_mode_changed_message_to_paper(self) -> None:
        """Test mode changed message to paper."""
        message = format_mode_changed_message("LIVE", "PAPER")
        assert "*模式已切换*" in message
        assert "LIVE" in message
        assert "PAPER" in message
        assert "模拟资金" in message
```

### 实现注意事项

**关键点:**

1. **安全第一**: 切换到 Live 模式需要二次确认，防止误操作
2. **审计日志**: 所有控制操作都记录审计日志，便于追溯
3. **状态持久化**: 状态变更需要持久化到数据库，确保重启后恢复
4. **授权验证**: 每个命令都验证发送者的 Chat ID
5. **与 /confirm 命令的关系**: 扩展现有的 /confirm 命令，支持模式切换确认

**与 Story 9.10 的 /confirm 命令:**
- Story 9.10 的 /confirm 用于确认交易
- Story 9.11 的 /confirm live 用于确认模式切换
- 两者共享相同的命令名称，但参数不同
- 需要检查是否有待确认的请求来区分

**ThreadSafeState 扩展:**
- 添加 `set_trading_enabled()` 和 `set_mode()` 方法
- 确保异步安全
- 持久化到 system_state 表

### 前一个故事学习 [Source: 9-10-cmd-predict-trigger.md]

**从 Story 9.10 学到的模式:**

1. **会话状态管理**: 使用模块级字典存储待确认状态
2. **超时机制**: 设置 30 秒超时自动取消
3. **确认流程**: 两阶段确认模式
4. **错误处理**: 处理无参数、无效参数、超时等边界情况

### References

- [Source: epics.md#Story 9.11] - 原始 Story 定义
- [Source: src/telegram_commands/handlers.py] - 命令处理框架
- [Source: src/telegram_commands/formatters.py] - 消息格式化模式
- [Source: src/core/state.py] - ThreadSafeState 状态管理
- [Source: architecture.md#Logging Patterns] - 日志格式和 emoji
- [Source: project-context.md] - 项目实现规范

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
