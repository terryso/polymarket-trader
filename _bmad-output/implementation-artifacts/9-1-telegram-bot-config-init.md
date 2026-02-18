# Story 9.1: Telegram Bot 配置与初始化

Status: ready-for-dev

## Story

As a **开发者**,
I want **创建 Telegram Bot 配置和客户端初始化**,
So that **系统能够与 Telegram API 安全通信**.

## Acceptance Criteria

**Given** Epic 1 配置系统已完成
**When** 扩展配置和创建 Telegram 客户端
**Then** 在 `src/config.py` 添加:
```python
# Telegram 配置
TELEGRAM_BOT_TOKEN: str | None = None
TELEGRAM_CHAT_ID: str | None = None  # 授权的用户 Chat ID
TELEGRAM_ENABLED: bool = False
```
**And** 添加到 `requirements.txt`:
```
python-telegram-bot>=20.0
```
**And** 创建 `src/api/telegram.py`:
- 使用 `python-telegram-bot` 库 (异步)
- 初始化 Bot 实例和 Application
- 实现 `get_me()` 验证 Bot 连接
**And** 更新 `.env.example` 添加 Telegram 配置项
**And** 配置项缺失时记录警告但不阻止系统启动

## Tasks / Subtasks

- [ ] Task 1: 扩展配置系统 (AC: #1)
  - [ ] 1.1 在 `src/config.py` 添加 `TelegramSettings` 类
  - [ ] 1.2 添加配置项: `bot_token`, `chat_id`, `enabled`
  - [ ] 1.3 添加环境变量前缀 `TELEGRAM_`
  - [ ] 1.4 在主 `Settings` 类中添加 `telegram` 字段
  - [ ] 1.5 添加配置验证 (enabled=True 时检查 token 存在)

- [ ] Task 2: 更新依赖 (AC: #2)
  - [ ] 2.1 在 `requirements.txt` 添加 `python-telegram-bot>=20.0`
  - [ ] 2.2 运行 `pip install -r requirements.txt` 安装依赖
  - [ ] 2.3 验证库版本兼容性

- [ ] Task 3: 创建 Telegram 客户端 (AC: #3)
  - [ ] 3.1 创建 `src/api/telegram.py` 文件
  - [ ] 3.2 添加模块 docstring 和使用示例
  - [ ] 3.3 定义 `TelegramClient` 类
  - [ ] 3.4 实现构造函数，从 settings 加载配置
  - [ ] 3.5 初始化 `Application.builder()` 创建 Application
  - [ ] 3.6 实现 `get_me()` 方法验证 Bot 连接
  - [ ] 3.7 实现 `initialize()` 和 `shutdown()` 生命周期方法
  - [ ] 3.8 添加上下文管理器支持 (`__aenter__`, `__aexit__`)

- [ ] Task 4: 实现错误处理 (AC: #3)
  - [ ] 4.1 捕获 `telegram.error.InvalidToken` -> `ConfigurationError`
  - [ ] 4.2 捕获 `telegram.error.NetworkError` -> `NetworkError`
  - [ ] 4.3 捕获 `telegram.error.TelegramError` -> 通用错误处理
  - [ ] 4.4 记录错误日志 (带 emoji)

- [ ] Task 5: 实现日志脱敏 (AC: #3)
  - [ ] 5.1 创建 `_mask_token(token: str)` 辅助方法
  - [ ] 5.2 Bot Token 只显示前 4 位和后 4 位
  - [ ] 5.3 在初始化和错误日志中使用脱敏

- [ ] Task 6: 更新配置模板 (AC: #4)
  - [ ] 6.1 在 `.env.example` 添加 Telegram 配置部分
  - [ ] 6.2 添加配置说明注释
  - [ ] 6.3 使用占位符而非真实值

- [ ] Task 7: 更新模块导出 (AC: All)
  - [ ] 7.1 更新 `src/api/__init__.py` 导出 TelegramClient
  - [ ] 7.2 确保从 src.api 可以导入 TelegramClient

- [ ] Task 8: 编写测试 (AC: All)
  - [ ] 8.1 创建 `tests/test_api/test_telegram.py`
  - [ ] 8.2 测试配置加载
  - [ ] 8.3 测试 `get_me()` 成功情况 (mock Telegram API)
  - [ ] 8.4 测试错误处理 (无效 token、网络错误)
  - [ ] 8.5 测试 Token 脱敏
  - [ ] 8.6 测试配置缺失时的警告日志

- [ ] Task 9: 代码质量检查 (AC: All)
  - [ ] 9.1 运行 `mypy src/api/telegram.py` 无错误
  - [ ] 9.2 运行 `black --check src/api/telegram.py` 通过
  - [ ] 9.3 运行 `isort --check src/api/telegram.py` 通过
  - [ ] 9.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: epics.md#Story 9.1]

**Telegram Bot API:**
- 使用 `python-telegram-bot` 库 v20+ (异步版本)
- 支持 Bot Token 认证
- 支持授权用户 Chat ID 验证

**配置项:**
```python
TELEGRAM_BOT_TOKEN: str | None = None  # Bot Token (从 @BotFather 获取)
TELEGRAM_CHAT_ID: str | None = None     # 授权用户的 Chat ID
TELEGRAM_ENABLED: bool = False          # 是否启用 Telegram 功能
```

### 配置实现模板 [Source: src/config.py]

**TelegramSettings 模板:**

```python
class TelegramSettings(BaseSettings):
    """Telegram Bot configuration settings."""

    model_config = SettingsConfigDict(env_prefix="TELEGRAM_")

    bot_token: str | None = Field(
        default=None,
        description="Telegram Bot Token (from @BotFather)"
    )
    chat_id: str | None = Field(
        default=None,
        description="Authorized user Chat ID for commands"
    )
    enabled: bool = Field(
        default=False,
        description="Enable Telegram notifications and commands"
    )

    @field_validator("enabled")
    @classmethod
    def validate_enabled(cls, v: bool, info: ValidationInfo) -> bool:
        """If enabled, bot_token must be set."""
        if v:
            token = info.data.get("bot_token")
            if not token:
                import warnings
                warnings.warn(
                    "Telegram is enabled but TELEGRAM_BOT_TOKEN is not set. "
                    "Telegram features will be disabled.",
                    UserWarning
                )
                return False
        return v
```

### python-telegram-bot v20+ 使用 [Source: python-telegram-bot 文档]

**v20+ 版本变化:**
- 全面异步化 (`async`/`await`)
- 使用 `Application` 类替代 `Updater`
- 需要显式调用 `initialize()` 和 `shutdown()`

**客户端初始化:**

```python
from telegram import Bot
from telegram.ext import Application

# 方式 1: 简单 Bot 实例 (仅发送消息)
bot = Bot(token="YOUR_BOT_TOKEN")
me = await bot.get_me()

# 方式 2: Application 实例 (支持命令处理)
application = Application.builder().token("YOUR_BOT_TOKEN").build()
await application.initialize()
await application.bot.get_me()
await application.shutdown()
```

### 实现模板

**TelegramClient 完整模板:**

```python
# src/api/telegram.py
"""Telegram Bot API client for notifications and remote control.

This module provides a typed interface to the Telegram Bot API,
using python-telegram-bot library (v20+).

Usage:
    from src.api import TelegramClient

    # Async context manager
    async with TelegramClient() as client:
        # Verify connection
        me = await client.get_me()
        print(f"Connected as: {me.username}")

    # Or manually manage lifecycle
    client = TelegramClient()
    await client.initialize()
    try:
        me = await client.get_me()
    finally:
        await client.shutdown()
"""

from __future__ import annotations

__all__ = ["TelegramClient"]

from typing import Any

from telegram import Bot, User
from telegram.error import InvalidToken, NetworkError as TelegramNetworkError, TelegramError
from telegram.ext import Application

from src.config import settings
from src.exceptions import ConfigurationError, NetworkError
from src.utils.logger import OPERATION_EMOJIS, get_logger


class TelegramClient:
    """Telegram Bot client with async support.

    Provides methods to interact with Telegram Bot API for
    notifications and remote commands.

    Attributes:
        _application: The underlying Application instance
        _bot: The Bot instance for direct API calls
        _token: The bot token (masked in logs)
        _chat_id: Authorized user Chat ID
        _enabled: Whether Telegram features are enabled

    Example:
        >>> async with TelegramClient() as client:
        ...     me = await client.get_me()
        ...     print(f"Bot: @{me.username}")
    """

    def __init__(self) -> None:
        """Initialize the Telegram client with settings from config."""
        self._logger = get_logger(__name__)

        # Load configuration
        self._token = settings.telegram.bot_token
        self._chat_id = settings.telegram.chat_id
        self._enabled = settings.telegram.enabled

        # Log initialization (with masked token)
        self._logger.info(
            f"{OPERATION_EMOJIS['network']} Initializing Telegram client "
            f"(enabled={self._enabled}, token={self._mask_token(self._token or '')})"
        )

        # Initialize application (deferred until initialize())
        self._application: Application | None = None
        self._bot: Bot | None = None

    def _mask_token(self, token: str) -> str:
        """Mask bot token for logging (show only first/last 4 chars).

        Args:
            token: The bot token to mask

        Returns:
            Masked token (e.g., "1234****5678")
        """
        if not token:
            return "[NOT_SET]"
        if len(token) <= 8:
            return "****"
        return f"{token[:4]}****{token[-4:]}"

    async def initialize(self) -> None:
        """Initialize the Telegram application.

        Raises:
            ConfigurationError: If token is invalid
            NetworkError: If connection fails
        """
        if not self._enabled or not self._token:
            self._logger.warning(
                f"{OPERATION_EMOJIS['warning']} Telegram client not enabled or token not set"
            )
            return

        try:
            self._application = (
                Application.builder()
                .token(self._token)
                .build()
            )
            await self._application.initialize()
            self._bot = self._application.bot

            self._logger.info(
                f"{OPERATION_EMOJIS['success']} Telegram client initialized"
            )

        except InvalidToken as e:
            raise ConfigurationError(
                message=f"Invalid Telegram bot token: {self._mask_token(self._token)}",
                config_key="TELEGRAM_BOT_TOKEN",
                original_exception=e,
            )
        except TelegramNetworkError as e:
            raise NetworkError(
                message=f"Telegram network error: {e}",
                endpoint="initialize",
                original_exception=e,
            )
        except TelegramError as e:
            raise NetworkError(
                message=f"Telegram API error: {e}",
                endpoint="initialize",
                original_exception=e,
            )

    async def shutdown(self) -> None:
        """Shutdown the Telegram application."""
        if self._application:
            try:
                await self._application.shutdown()
                self._logger.info(
                    f"{OPERATION_EMOJIS['success']} Telegram client shutdown"
                )
            except Exception as e:
                self._logger.error(
                    f"{OPERATION_EMOJIS['error']} Error during Telegram shutdown: {e}"
                )
            finally:
                self._application = None
                self._bot = None

    async def __aenter__(self) -> "TelegramClient":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any
    ) -> None:
        """Async context manager exit."""
        await self.shutdown()

    @property
    def is_enabled(self) -> bool:
        """Check if Telegram client is enabled and initialized."""
        return self._enabled and self._bot is not None

    @property
    def authorized_chat_id(self) -> str | None:
        """Get the authorized Chat ID for commands."""
        return self._chat_id

    async def get_me(self) -> User | None:
        """Get bot information to verify connection.

        Returns:
            Bot User object if successful, None if not enabled

        Raises:
            NetworkError: If API call fails
            ConfigurationError: If client not initialized
        """
        if not self.is_enabled or not self._bot:
            self._logger.warning(
                f"{OPERATION_EMOJIS['warning']} Telegram client not enabled or not initialized"
            )
            return None

        try:
            me = await self._bot.get_me()
            self._logger.info(
                f"{OPERATION_EMOJIS['success']} Telegram bot verified: "
                f"@{me.username} ({me.first_name})"
            )
            return me

        except TelegramNetworkError as e:
            raise NetworkError(
                message=f"Telegram network error: {e}",
                endpoint="get_me",
                original_exception=e,
            )
        except TelegramError as e:
            raise NetworkError(
                message=f"Telegram API error: {e}",
                endpoint="get_me",
                original_exception=e,
            )

    def is_authorized_chat(self, chat_id: int | str) -> bool:
        """Check if a chat ID is authorized.

        Args:
            chat_id: The chat ID to check

        Returns:
            True if authorized (or if no chat_id restriction), False otherwise
        """
        if not self._chat_id:
            # No restriction configured
            return True
        return str(chat_id) == str(self._chat_id)
```

### 异常处理 [Source: src/exceptions.py]

**现有异常类型:**

```python
class ConfigurationError(BotError):
    """Configuration error."""
    def __init__(
        self,
        message: str,
        config_key: str = "",
        original_exception: Exception | None = None,
    ): ...

class NetworkError(BotError):
    """Network/API error."""
    def __init__(
        self,
        message: str,
        endpoint: str = "",
        status_code: int | None = None,
        original_exception: Exception | None = None,
    ): ...
```

### 日志系统 [Source: src/utils/logger.py]

**OPERATION_EMOJIS 映射:**
```python
OPERATION_EMOJIS = {
    "success": "✅",
    "warning": "⚠️",
    "error": "❌",
    "network": "🌐",
    "trade": "💰",
    "analysis": "🧠",
    "data": "📊",
}
```

### .env.example 更新 [Source: .env.example]

**添加以下内容:**

```env
# ========== Telegram Configuration ==========
# Telegram Bot Token (from @BotFather)
TELEGRAM_BOT_TOKEN=

# Authorized user Chat ID (optional, restricts commands to this user)
# Get your Chat ID by messaging @userinfobot on Telegram
TELEGRAM_CHAT_ID=

# Enable Telegram notifications and commands
TELEGRAM_ENABLED=false
```

### 项目结构 [Source: architecture.md#Project Structure]

**新增/修改文件:**
```
src/api/
├── __init__.py          # 更新: 导出 TelegramClient
├── polymarket.py        # 已存在
├── llm.py               # 已存在
└── telegram.py          # 新增: Telegram API 客户端

tests/test_api/
├── __init__.py          # 已存在
├── test_polymarket.py   # 已存在
├── test_llm.py          # 已存在
└── test_telegram.py     # 新增: Telegram 客户端测试
```

### 测试策略

```python
# tests/test_api/test_telegram.py
"""Tests for TelegramClient."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import User
from telegram.error import InvalidToken, NetworkError as TelegramNetworkError

from src.api.telegram import TelegramClient
from src.exceptions import ConfigurationError, NetworkError


class TestTelegramClient:
    """Tests for TelegramClient class."""

    def test_init_disabled(self) -> None:
        """Test initialization when Telegram is disabled."""
        with patch("src.api.telegram.settings") as mock_settings:
            mock_settings.telegram.bot_token = None
            mock_settings.telegram.chat_id = None
            mock_settings.telegram.enabled = False

            client = TelegramClient()
            assert client._enabled is False
            assert client._token is None

    def test_mask_token(self) -> None:
        """Test token masking."""
        with patch("src.api.telegram.settings") as mock_settings:
            mock_settings.telegram.bot_token = "test-token"
            mock_settings.telegram.chat_id = None
            mock_settings.telegram.enabled = False

            client = TelegramClient()
            assert client._mask_token("1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11") == "1234****w11"
            assert client._mask_token("short") == "****"
            assert client._mask_token("") == "[NOT_SET]"

    @pytest.mark.asyncio
    async def test_initialize_success(self) -> None:
        """Test successful initialization."""
        with patch("src.api.telegram.settings") as mock_settings:
            mock_settings.telegram.bot_token = "test-token-1234"
            mock_settings.telegram.chat_id = "123456789"
            mock_settings.telegram.enabled = True

            with patch("src.api.telegram.Application") as mock_app:
                mock_instance = AsyncMock()
                mock_app.builder.return_value.token.return_value.build.return_value = mock_instance

                client = TelegramClient()
                await client.initialize()

                mock_instance.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_invalid_token(self) -> None:
        """Test initialization with invalid token."""
        with patch("src.api.telegram.settings") as mock_settings:
            mock_settings.telegram.bot_token = "invalid-token"
            mock_settings.telegram.chat_id = None
            mock_settings.telegram.enabled = True

            with patch("src.api.telegram.Application") as mock_app:
                mock_instance = AsyncMock()
                mock_instance.initialize.side_effect = InvalidToken()
                mock_app.builder.return_value.token.return_value.build.return_value = mock_instance

                client = TelegramClient()
                with pytest.raises(ConfigurationError):
                    await client.initialize()

    @pytest.mark.asyncio
    async def test_get_me_success(self) -> None:
        """Test get_me success."""
        with patch("src.api.telegram.settings") as mock_settings:
            mock_settings.telegram.bot_token = "test-token"
            mock_settings.telegram.chat_id = None
            mock_settings.telegram.enabled = True

            client = TelegramClient()
            client._bot = AsyncMock()

            mock_user = MagicMock(spec=User)
            mock_user.username = "test_bot"
            mock_user.first_name = "Test Bot"
            client._bot.get_me.return_value = mock_user

            result = await client.get_me()
            assert result == mock_user

    def test_is_authorized_chat(self) -> None:
        """Test chat ID authorization check."""
        with patch("src.api.telegram.settings") as mock_settings:
            mock_settings.telegram.bot_token = "test-token"
            mock_settings.telegram.chat_id = "123456789"
            mock_settings.telegram.enabled = True

            client = TelegramClient()

            assert client.is_authorized_chat("123456789") is True
            assert client.is_authorized_chat(123456789) is True
            assert client.is_authorized_chat("987654321") is False

    def test_is_authorized_chat_no_restriction(self) -> None:
        """Test chat ID authorization when no restriction."""
        with patch("src.api.telegram.settings") as mock_settings:
            mock_settings.telegram.bot_token = "test-token"
            mock_settings.telegram.chat_id = None
            mock_settings.telegram.enabled = True

            client = TelegramClient()

            # No restriction means all chats are authorized
            assert client.is_authorized_chat("123456789") is True
            assert client.is_authorized_chat("any_chat_id") is True
```

### 依赖关系

**本故事依赖:**
- Story 1.2: 配置管理系统 (Settings 基类)
- Story 1.3: 日志系统 (get_logger, OPERATION_EMOJIS)
- Story 1.4: 自定义异常体系 (ConfigurationError, NetworkError)

**后续故事依赖本故事:**
- Story 9.2: 通知消息发送 (需要 TelegramClient)
- Story 9.3: 交易事件通知集成 (需要 TelegramClient)
- Story 9.5-9.11: 命令处理 (需要 TelegramClient)

### 实现注意事项

**关键点:**

1. **异步支持**: python-telegram-bot v20+ 是完全异步的，使用 `async`/`await`
2. **生命周期管理**: 需要显式调用 `initialize()` 和 `shutdown()`
3. **配置缺失处理**: 配置缺失时记录警告但不阻止系统启动
4. **Token 脱敏**: 只显示前 4 位和后 4 位
5. **Chat ID 验证**: 用于限制谁可以发送命令给 Bot

**与 LLMClient 的相似模式:**
- 使用 `@dataclass` 或类属性存储配置
- 上下文管理器支持 (`__aenter__`/`__aexit__`)
- 错误映射到项目自定义异常
- 日志脱敏

**获取 Telegram Bot Token:**
1. 在 Telegram 中搜索 @BotFather
2. 发送 `/newbot` 命令
3. 按提示设置 Bot 名称
4. 获取 Bot Token (格式: `1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

**获取 Chat ID:**
1. 在 Telegram 中搜索 @userinfobot
2. 发送任意消息
3. 获取你的 Chat ID (数字)

### 前一个故事学习 [Source: 8-6-run-scripts-and-process-management.md]

**从 Epic 8 学到的模式:**

1. **配置可选性**: 新功能配置应可选，不影响核心系统运行
2. **警告而非错误**: 配置缺失时警告但允许继续
3. **模块化设计**: 新模块应独立于核心业务逻辑
4. **异步生命周期**: 使用 `initialize()` 和 `shutdown()` 管理资源

### References

- [Source: epics.md#Story 9.1] - 原始 Story 定义
- [Source: architecture.md#Core Dependencies] - 依赖管理
- [Source: architecture.md#Security] - API Token 保护
- [Source: src/config.py] - Settings 配置模式
- [Source: src/api/llm.py] - API 客户端实现模式
- [Source: src/exceptions.py] - 自定义异常
- [Source: src/utils/logger.py] - 日志系统
- [Source: python-telegram-bot 文档] - https://docs.python-telegram-bot.org/

## Dev Agent Record

### Agent Model Used

GLM-5 (via Claude Code)

### Debug Log References

None required - all tests passed on first run after fixing test expectations.

### Completion Notes List

1. Implementation completed successfully on 2026-02-18
2. All 32 unit tests pass
3. Code quality checks pass (mypy, black, isort)
4. Pre-existing test failures in other modules (Python 3.14 event loop changes, integration tests) are unrelated to this story
5. Token masking follows security best practices (showing only first 4 and last 4 characters)
6. Configuration missing warning implemented but does not block system startup

### File List

**Modified Files:**
- `src/config.py` - Added TelegramSettings class and telegram field to Settings
- `requirements.txt` - Added python-telegram-bot>=20.0 dependency
- `.env.example` - Added Telegram configuration section
- `src/api/__init__.py` - Added TelegramClient export

**New Files:**
- `src/api/telegram.py` - TelegramClient implementation with async support
- `tests/test_api/test_telegram.py` - Comprehensive test suite (32 tests)
