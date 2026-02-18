# Story 9.5: Telegram 命令处理 - 状态查询

Status: ready-for-dev

## Story

As a **用户**,
I want **通过 Telegram 命令查询系统状态**,
So that **我能随时随地了解系统运行情况**.

## Acceptance Criteria

**Given** Telegram Bot 已初始化 (Story 9.1)
**When** 在 `src/api/telegram.py` 添加命令处理器
**Then** 实现 `/status` 命令:
- 返回: 交易模式、当前资金、日盈亏、持仓数、连续亏损
- 显示交易是否启用
```
📊 *系统状态*
模式: PAPER
资金: $180.50
日盈亏: -$5.50 (-2.9%)
持仓: 2 个
连续亏损: 1
交易: ✅ 启用
```
**And** 实现 `/help` 命令显示所有可用命令
**And** 验证发送者 Chat ID 是否匹配授权用户
**And** 未授权用户发送命令时忽略或返回错误

## Tasks / Subtasks

- [ ] Task 1: 扩展 TelegramClient 支持命令处理 (AC: #1)
  - [ ] 1.1 在 `TelegramClient` 中添加 `setup_command_handlers()` 方法
  - [ ] 1.2 创建 `/status` 命令处理函数
  - [ ] 1.3 创建 `/help` 命令处理函数
  - [ ] 1.4 注册命令处理器到 Application

- [ ] Task 2: 实现状态格式化 (AC: #1)
  - [ ] 2.1 创建 `_format_status_message()` 方法
  - [ ] 2.2 格式化资金、日盈亏、持仓数等信息
  - [ ] 2.3 添加 emoji 增强可读性
  - [ ] 2.4 计算日盈亏百分比

- [ ] Task 3: 实现帮助命令格式化 (AC: #2)
  - [ ] 3.1 创建 `_format_help_message()` 方法
  - [ ] 3.2 列出所有可用命令及说明
  - [ ] 3.3 使用 Markdown 格式化

- [ ] Task 4: 实现授权验证 (AC: #3, #4)
  - [ ] 4.1 在命令处理函数中验证 Chat ID
  - [ ] 4.2 未授权用户返回错误消息或忽略
  - [ ] 4.3 记录未授权访问日志

- [ ] Task 5: 集成状态管理器 (AC: #1)
  - [ ] 5.1 在命令处理中注入 `ThreadSafeState` 依赖
  - [ ] 5.2 从状态管理器获取实时状态
  - [ ] 5.3 获取交易模式配置

- [ ] Task 6: 实现 Bot 启动轮询 (AC: All)
  - [ ] 6.1 添加 `start_polling()` 方法启动命令监听
  - [ ] 6.2 添加 `stop_polling()` 方法停止命令监听
  - [ ] 6.3 在 `initialize()` 中自动注册命令处理器

- [ ] Task 7: 创建命令处理模块 (AC: All)
  - [ ] 7.1 创建 `src/telegram_commands/` 目录
  - [ ] 7.2 创建 `src/telegram_commands/__init__.py`
  - [ ] 7.3 创建 `src/telegram_commands/handlers.py` - 命令处理函数
  - [ ] 7.4 创建 `src/telegram_commands/formatters.py` - 消息格式化

- [ ] Task 8: 编写测试 (AC: All)
  - [ ] 8.1 创建 `tests/test_telegram_commands/` 目录
  - [ ] 8.2 创建 `tests/test_telegram_commands/__init__.py`
  - [ ] 8.3 创建 `tests/test_telegram_commands/test_handlers.py`
  - [ ] 8.4 测试 `/status` 命令成功情况
  - [ ] 8.5 测试 `/help` 命令
  - [ ] 8.6 测试未授权用户访问
  - [ ] 8.7 测试消息格式化

- [ ] Task 9: 代码质量检查 (AC: All)
  - [ ] 9.1 运行 `mypy src/telegram_commands/` 无错误
  - [ ] 9.2 运行 `black --check src/telegram_commands/` 通过
  - [ ] 9.3 运行 `isort --check src/telegram_commands/` 通过
  - [ ] 9.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: epics.md#Story 9.5]

**Telegram 命令处理:**

- 使用 `python-telegram-bot` 库的 `CommandHandler`
- 支持 `/status` 和 `/help` 命令
- 验证发送者 Chat ID 是否授权

**命令响应格式:**

```markdown
📊 *系统状态*
模式: PAPER
资金: $180.50
日盈亏: -$5.50 (-2.9%)
持仓: 2 个
连续亏损: 1
交易: ✅ 启用
```

### 现有依赖 [Source: Story 9.1, 9.2]

**TelegramClient 已实现的方法:**
- `initialize()` - 初始化客户端
- `shutdown()` - 关闭客户端
- `get_me()` - 获取 Bot 信息
- `is_enabled` - 检查是否启用
- `authorized_chat_id` - 获取授权 Chat ID
- `is_authorized_chat(chat_id)` - 验证 Chat ID

**ThreadSafeState 已实现的属性 [Source: src/core/state.py]:**
- `current_capital` - 当前资金
- `daily_pnl` - 日盈亏
- `consecutive_losses` - 连续亏损次数
- `open_positions_count` - 持仓数量
- `trading_enabled` - 交易是否启用
- `reduced_mode` - 是否处于降级模式

### python-telegram-bot 命令处理 [Source: python-telegram-bot 文档]

**CommandHandler 使用:**

```python
from telegram.ext import CommandHandler, ContextTypes
from telegram import Update

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    chat_id = update.effective_chat.id

    # Verify authorization
    if not is_authorized(chat_id):
        await update.message.reply_text("未授权访问")
        return

    # Get status and format message
    status_message = format_status()
    await update.message.reply_text(status_message, parse_mode="Markdown")

# Register handler
application.add_handler(CommandHandler("status", status_command))
```

**启动轮询:**

```python
# Start polling for updates
await application.start_polling()

# Stop polling
await application.stop_polling()
```

### 项目结构 [Source: architecture.md#Project Structure]

**新增文件:**
```
src/telegram_commands/
├── __init__.py              # 模块导出
├── handlers.py              # 命令处理函数
└── formatters.py            # 消息格式化

tests/test_telegram_commands/
├── __init__.py
└── test_handlers.py         # 命令处理测试
```

### 实现模板

**handlers.py 完整模板:**

```python
# src/telegram_commands/handlers.py
"""Telegram command handlers for bot interactions.

This module provides command handler functions for the Telegram bot,
implementing /status and /help commands.

Story 9.5: Telegram 命令处理 - 状态查询

Usage:
    from src.telegram_commands import setup_command_handlers

    # In TelegramClient
    setup_command_handlers(application, state_manager)
"""

from __future__ import annotations

__all__ = ["setup_command_handlers"]

from typing import TYPE_CHECKING, Callable

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.config import settings
from src.telegram_commands.formatters import (
    format_help_message,
    format_status_message,
    format_unauthorized_message,
)
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.core.state import ThreadSafeState

logger = get_logger(__name__)


def create_status_handler(
    state_manager: "ThreadSafeState",
    authorized_chat_id: str | None,
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], None]:
    """Create a status command handler with injected dependencies.

    Args:
        state_manager: ThreadSafeState instance for getting system state
        authorized_chat_id: Authorized chat ID for access control

    Returns:
        Async function that handles /status command
    """

    async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = update.effective_chat.id

        # Verify authorization
        if authorized_chat_id and str(chat_id) != str(authorized_chat_id):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Get current state
        snapshot = await state_manager.get_state()

        # Determine trading mode
        mode = "PAPER" if settings.paper_trading else "LIVE"

        # Format and send status message
        message = format_status_message(
            mode=mode,
            current_capital=snapshot.current_capital,
            daily_pnl=snapshot.daily_pnl,
            open_positions=snapshot.open_positions_count,
            consecutive_losses=snapshot.consecutive_losses,
            trading_enabled=snapshot.trading_enabled,
        )

        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Status command processed for chat_id: {chat_id}")

    return status_handler


def create_help_handler(
    authorized_chat_id: str | None,
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], None]:
    """Create a help command handler.

    Args:
        authorized_chat_id: Authorized chat ID for access control

    Returns:
        Async function that handles /help command
    """

    async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = update.effective_chat.id

        # Verify authorization
        if authorized_chat_id and str(chat_id) != str(authorized_chat_id):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Send help message
        message = format_help_message()
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Help command processed for chat_id: {chat_id}")

    return help_handler


def setup_command_handlers(
    application: Application,
    state_manager: "ThreadSafeState",
    authorized_chat_id: str | None = None,
) -> None:
    """Setup all command handlers for the Telegram bot.

    Args:
        application: Telegram Application instance
        state_manager: ThreadSafeState instance for system state
        authorized_chat_id: Optional chat ID for access control
    """
    # Create handlers with injected dependencies
    status_handler = create_status_handler(state_manager, authorized_chat_id)
    help_handler = create_help_handler(authorized_chat_id)

    # Register handlers
    application.add_handler(CommandHandler("status", status_handler))
    application.add_handler(CommandHandler("help", help_handler))

    logger.info("Command handlers registered: /status, /help")
```

**formatters.py 完整模板:**

```python
# src/telegram_commands/formatters.py
"""Message formatters for Telegram commands.

This module provides formatting functions for Telegram command responses.

Story 9.5: Telegram 命令处理 - 状态查询
"""

from __future__ import annotations

__all__ = [
    "format_status_message",
    "format_help_message",
    "format_unauthorized_message",
]


def format_status_message(
    mode: str,
    current_capital: float,
    daily_pnl: float,
    open_positions: int,
    consecutive_losses: int,
    trading_enabled: bool,
) -> str:
    """Format a system status message.

    Args:
        mode: Trading mode (PAPER/LIVE)
        current_capital: Current capital in USD
        daily_pnl: Daily profit/loss in USD
        open_positions: Number of open positions
        consecutive_losses: Number of consecutive losses
        trading_enabled: Whether trading is enabled

    Returns:
        Formatted Markdown message
    """
    # Calculate daily PnL percentage
    daily_pnl_pct = (daily_pnl / current_capital * 100) if current_capital > 0 else 0.0

    # Format PnL with sign
    pnl_sign = "+" if daily_pnl >= 0 else ""
    pnl_emoji = "\U0001f4c8" if daily_pnl >= 0 else "\U0001f4c9"  # chart_up / chart_down

    # Trading status emoji
    trading_emoji = "\u2705" if trading_enabled else "\u274c"  # check / x
    trading_status = "启用" if trading_enabled else "禁用"

    lines = [
        "\U0001f4ca *系统状态*",  # chart emoji
        f"模式: {mode}",
        f"资金: ${current_capital:.2f}",
        f"日盈亏: {pnl_emoji} {pnl_sign}${daily_pnl:.2f} ({pnl_sign}{daily_pnl_pct:.1f}%)",
        f"持仓: {open_positions} 个",
        f"连续亏损: {consecutive_losses}",
        f"交易: {trading_emoji} {trading_status}",
    ]

    return "\n".join(lines)


def format_help_message() -> str:
    """Format a help message with available commands.

    Returns:
        Formatted Markdown message with command list
    """
    lines = [
        "\U0001f4cb *可用命令*",
        "",
        "/status - 查看系统状态",
        "/positions - 查看当前持仓 (Story 9.6)",
        "/stats - 查看交易统计 (Story 9.7)",
        "/markets - 查看活跃市场 (Story 9.8)",
        "/history - 查看交易历史 (Story 9.9)",
        "/predict - 手动触发分析 (Story 9.10)",
        "/enable - 启用交易 (Story 9.11)",
        "/disable - 禁用交易 (Story 9.11)",
        "/mode - 查看/切换模式 (Story 9.11)",
        "/help - 显示帮助信息",
    ]

    return "\n".join(lines)


def format_unauthorized_message() -> str:
    """Format an unauthorized access message.

    Returns:
        Formatted Markdown message for unauthorized users
    """
    return "\u26a0\ufe0f *未授权访问*\n\n您没有权限使用此机器人。"
```

### 修改 TelegramClient [Source: src/api/telegram.py]

**需要添加的方法:**

```python
# 在 TelegramClient 类中添加

async def setup_commands(
    self,
    state_manager: "ThreadSafeState",
) -> None:
    """Setup command handlers for the bot.

    Args:
        state_manager: ThreadSafeState instance for system state
    """
    if not self.is_enabled or not self._application:
        self._logger.warning("Cannot setup commands: client not enabled")
        return

    from src.telegram_commands import setup_command_handlers

    setup_command_handlers(
        self._application,
        state_manager,
        self._chat_id,
    )

    self._logger.info("Command handlers setup complete")

async def start_polling(self) -> None:
    """Start polling for Telegram updates."""
    if not self.is_enabled or not self._application:
        self._logger.warning("Cannot start polling: client not enabled")
        return

    await self._application.start_polling()
    self._logger.info("Started polling for Telegram updates")

async def stop_polling(self) -> None:
    """Stop polling for Telegram updates."""
    if not self._application:
        return

    await self._application.stop_polling()
    self._logger.info("Stopped polling for Telegram updates")
```

### 依赖关系

**本故事依赖:**
- Story 9.1: Telegram Bot 配置与初始化 (TelegramClient)
- Story 1.3: 日志系统 (get_logger)
- Story 4.2: 线程安全状态管理 (ThreadSafeState)

**后续故事依赖本故事:**
- Story 9.6: 持仓查询命令 (需要命令处理框架)
- Story 9.7: 统计查询命令 (需要命令处理框架)
- Story 9.8-9.11: 其他命令 (需要命令处理框架)

### 配置项 [Source: src/config.py]

**需要的状态配置:**
```python
# 交易模式 (已存在于 Settings)
paper_trading: bool = Field(
    default=True,
    description="Use paper trading mode (simulated trades)"
)
```

### 测试策略

```python
# tests/test_telegram_commands/test_handlers.py
"""Tests for Telegram command handlers."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.telegram_commands.handlers import (
    create_help_handler,
    create_status_handler,
    setup_command_handlers,
)
from src.telegram_commands.formatters import (
    format_help_message,
    format_status_message,
    format_unauthorized_message,
)


class TestFormatters:
    """Tests for message formatters."""

    def test_format_status_message_profit(self) -> None:
        """Test status message formatting with profit."""
        message = format_status_message(
            mode="PAPER",
            current_capital=200.0,
            daily_pnl=10.0,
            open_positions=2,
            consecutive_losses=0,
            trading_enabled=True,
        )

        assert "*系统状态*" in message
        assert "PAPER" in message
        assert "$200.00" in message
        assert "+$10.00" in message
        assert "+5.0%" in message
        assert "2 个" in message
        assert "启用" in message

    def test_format_status_message_loss(self) -> None:
        """Test status message formatting with loss."""
        message = format_status_message(
            mode="LIVE",
            current_capital=100.0,
            daily_pnl=-5.0,
            open_positions=1,
            consecutive_losses=3,
            trading_enabled=False,
        )

        assert "*系统状态*" in message
        assert "LIVE" in message
        assert "-$5.00" in message
        assert "-5.0%" in message
        assert "禁用" in message

    def test_format_help_message(self) -> None:
        """Test help message formatting."""
        message = format_help_message()

        assert "*可用命令*" in message
        assert "/status" in message
        assert "/help" in message

    def test_format_unauthorized_message(self) -> None:
        """Test unauthorized message formatting."""
        message = format_unauthorized_message()

        assert "*未授权访问*" in message


class TestStatusHandler:
    """Tests for status command handler."""

    @pytest.fixture
    def mock_state_manager(self) -> MagicMock:
        """Create a mock state manager."""
        manager = MagicMock()
        snapshot = MagicMock()
        snapshot.current_capital = 200.0
        snapshot.daily_pnl = 10.0
        snapshot.open_positions_count = 2
        snapshot.consecutive_losses = 0
        snapshot.trading_enabled = True
        manager.get_state = AsyncMock(return_value=snapshot)
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
    async def test_status_handler_authorized(
        self,
        mock_state_manager: MagicMock,
        mock_update: MagicMock,
    ) -> None:
        """Test status handler with authorized user."""
        with patch("src.telegram_commands.handlers.settings") as mock_settings:
            mock_settings.paper_trading = True

            handler = create_status_handler(mock_state_manager, "123456789")
            await handler(mock_update, MagicMock())

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "*系统状态*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_status_handler_unauthorized(
        self,
        mock_state_manager: MagicMock,
        mock_update: MagicMock,
    ) -> None:
        """Test status handler with unauthorized user."""
        handler = create_status_handler(mock_state_manager, "999888777")
        await handler(mock_update, MagicMock())

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "*未授权访问*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_status_handler_no_restriction(
        self,
        mock_state_manager: MagicMock,
        mock_update: MagicMock,
    ) -> None:
        """Test status handler with no chat ID restriction."""
        with patch("src.telegram_commands.handlers.settings") as mock_settings:
            mock_settings.paper_trading = True

            # None means no restriction
            handler = create_status_handler(mock_state_manager, None)
            await handler(mock_update, MagicMock())

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "*系统状态*" in call_args.args[0]


class TestHelpHandler:
    """Tests for help command handler."""

    @pytest.fixture
    def mock_update(self) -> MagicMock:
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456789
        update.message = AsyncMock()
        return update

    @pytest.mark.asyncio
    async def test_help_handler_authorized(self, mock_update: MagicMock) -> None:
        """Test help handler with authorized user."""
        handler = create_help_handler("123456789")
        await handler(mock_update, MagicMock())

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "*可用命令*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_help_handler_unauthorized(self, mock_update: MagicMock) -> None:
        """Test help handler with unauthorized user."""
        handler = create_help_handler("999888777")
        await handler(mock_update, MagicMock())

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "*未授权访问*" in call_args.args[0]


class TestSetupCommandHandlers:
    """Tests for setup_command_handlers function."""

    def test_setup_registers_handlers(self) -> None:
        """Test that handlers are registered."""
        mock_app = MagicMock()
        mock_state = MagicMock()

        setup_command_handlers(mock_app, mock_state, "123456789")

        # Should add two handlers: status and help
        assert mock_app.add_handler.call_count == 2
```

### 实现注意事项

**关键点:**

1. **依赖注入**: 命令处理函数通过工厂函数创建，注入状态管理器和授权 Chat ID
2. **授权验证**: 每个命令处理函数都验证发送者的 Chat ID
3. **模块化**: 命令处理和消息格式化分离，便于测试和维护
4. **Markdown 格式**: 使用 Markdown 格式化消息，支持加粗和 emoji
5. **日志记录**: 记录命令处理和未授权访问尝试

**与 TelegramClient 的集成:**
- 在 `initialize()` 后调用 `setup_commands(state_manager)`
- 启动时调用 `start_polling()` 开始监听命令
- 关闭时调用 `stop_polling()` 停止监听

### 前一个故事学习 [Source: 9-2-notification-message-sending.md]

**从 Story 9.2 学到的模式:**

1. **消息格式化分离**: 格式化函数独立于发送逻辑
2. **Markdown 格式**: 使用 emoji 和加粗增强可读性
3. **错误处理**: 发送失败不抛出异常，只记录日志
4. **配置开关**: 使用 `settings.telegram.enabled` 控制功能

### References

- [Source: epics.md#Story 9.5] - 原始 Story 定义
- [Source: src/api/telegram.py] - TelegramClient 实现
- [Source: src/core/state.py] - ThreadSafeState 状态管理
- [Source: src/notifications/telegram_notifier.py] - 消息格式化模式
- [Source: architecture.md#Logging Patterns] - 日志格式和 emoji
- [Source: python-telegram-bot 文档] - https://docs.python-telegram-bot.org/

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
