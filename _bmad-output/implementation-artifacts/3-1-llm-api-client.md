# Story 3.1: LLM API 客户端

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **开发者**,
I want **实现 LLM API 客户端 (OpenAI 兼容协议)**,
So that **系统能够与 GLM 进行安全可靠的通信**.

## Acceptance Criteria

**Given** Epic 1 基础设施已完成
**When** 实现 `src/api/llm.py`
**Then** 使用 openai 库连接 GLM API (兼容 OpenAI 协议)
**And** 从配置加载: `LLM_API_BASE`, `LLM_API_KEY`, `LLM_MODEL`
**And** 实现基础方法:
- `chat(messages: list)` - 发送对话请求
- `chat_with_system(system_prompt: str, user_prompt: str)` - 带 system prompt 的对话
**And** 设置超时时间 30 秒 (NFR3)
**And** 使用重试装饰器处理网络错误
**And** API Key 日志脱敏 (只显示前4位)

## Tasks / Subtasks

- [ ] Task 1: 创建 LLM 客户端基础结构 (AC: 1)
  - [ ] 1.1 创建 `src/api/llm.py` 文件
  - [ ] 1.2 添加模块 docstring
  - [ ] 1.3 导入必要模块 (openai, 配置, 日志, 重试, 异常)
  - [ ] 1.4 定义 `__all__` 导出列表

- [ ] Task 2: 实现 LLMClient 类 (AC: 1)
  - [ ] 2.1 定义 `LLMClient` 类
  - [ ] 2.2 构造函数从 settings 加载配置
  - [ ] 2.3 初始化 OpenAI 客户端 (使用 api_base)
  - [ ] 2.4 添加类级 docstring 和使用示例
  - [ ] 2.5 实现 `__enter__` 和 `__exit__` 上下文管理

- [ ] Task 3: 实现 chat 方法 (AC: 1)
  - [ ] 3.1 定义 `chat(messages: list[dict])` 方法
  - [ ] 3.2 调用 OpenAI 兼容 API
  - [ ] 3.3 设置超时时间 (30 秒)
  - [ ] 3.4 返回响应内容字符串
  - [ ] 3.5 添加重试装饰器
  - [ ] 3.6 记录请求日志 (API Key 脱敏)
  - [ ] 3.7 处理 API 错误

- [ ] Task 4: 实现 chat_with_system 方法 (AC: 1)
  - [ ] 4.1 定义 `chat_with_system(system_prompt, user_prompt)` 方法
  - [ ] 4.2 构建 messages 列表格式
  - [ ] 4.3 调用 chat 方法
  - [ ] 4.4 返回响应内容
  - [ ] 4.5 记录请求日志

- [ ] Task 5: 实现错误处理 (AC: 1)
  - [ ] 5.1 捕获 openai.APIConnectionError -> NetworkError
  - [ ] 5.2 捕获 openai.RateLimitError -> RateLimitError
  - [ ] 5.3 捕获 openai.APITimeoutError -> RequestTimeoutError
  - [ ] 5.4 捕获 openai.APIStatusError -> NetworkError
  - [ ] 5.5 记录错误日志 (带 emoji)

- [ ] Task 6: 实现日志脱敏 (AC: 1)
  - [ ] 6.1 创建 `_mask_api_key(api_key: str)` 辅助方法
  - [ ] 6.2 只显示 API Key 前 4 位
  - [ ] 6.3 在初始化和请求日志中使用脱敏

- [ ] Task 7: 更新模块导出 (AC: All)
  - [ ] 7.1 更新 `src/api/__init__.py` 导出 LLMClient
  - [ ] 7.2 确保从 src.api 可以导入 LLMClient

- [ ] Task 8: 编写测试 (AC: All)
  - [ ] 8.1 创建 `tests/test_api/test_llm.py`
  - [ ] 8.2 测试 chat 方法 (mock OpenAI 响应)
  - [ ] 8.3 测试 chat_with_system 方法
  - [ ] 8.4 测试错误处理 (网络错误、超时、rate limit)
  - [ ] 8.5 测试 API Key 脱敏
  - [ ] 8.6 测试配置加载
  - [ ] 8.7 测试边界情况 (空消息、超长消息)

- [ ] Task 9: 代码质量检查 (AC: All)
  - [ ] 9.1 运行 `mypy src/api/llm.py` 无错误
  - [ ] 9.2 运行 `black --check src/api/llm.py` 通过
  - [ ] 9.3 运行 `isort --check src/api/llm.py` 通过
  - [ ] 9.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md#Core Dependencies]

**LLM 配置:**
- 使用 OpenAI 兼容协议连接 GLM API
- API Base: `https://open.bigmodel.cn/api/paas/v4`
- 默认模型: `glm-4`
- 超时: 30 秒 (NFR3)

**依赖:**
```txt
openai>=1.0.0
```

### 配置加载 [Source: src/config.py]

**已存在的 LLMSettings:**

```python
class LLMSettings(BaseSettings):
    """LLM API configuration settings."""

    model_config = SettingsConfigDict(env_prefix="LLM_")

    api_base: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4", description="LLM API base URL"
    )
    api_key: str = Field(default="", description="LLM API key")
    model: str = Field(default="glm-4", description="LLM model name")
    timeout: int = Field(default=30, gt=0, description="API timeout in seconds")
```

**使用方式:**
```python
from src.config import settings

# 访问 LLM 配置
api_base = settings.llm.api_base
api_key = settings.llm.api_key
model = settings.llm.model
timeout = settings.llm.timeout
```

### OpenAI 客户端初始化 [Source: OpenAI Python SDK 文档]

```python
from openai import OpenAI

client = OpenAI(
    api_key=api_key,
    base_url=api_base,  # 注意: openai 库使用 base_url 而非 api_base
    timeout=timeout,
)
```

### 实现模板

**LLMClient 完整模板:**

```python
# src/api/llm.py
"""LLM API client for GLM (OpenAI-compatible protocol).

This module provides a typed interface to the GLM API,
which is compatible with OpenAI's chat completion API.

Usage:
    from src.api import LLMClient

    with LLMClient() as client:
        # Simple chat
        response = client.chat([
            {"role": "user", "content": "Hello!"}
        ])

        # Chat with system prompt
        response = client.chat_with_system(
            system_prompt="You are a helpful assistant.",
            user_prompt="What is the capital of France?"
        )
"""

from __future__ import annotations

__all__ = ["LLMClient"]

from typing import Any

from openai import OpenAI
from openai import (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    APIStatusError,
)

from src.config import settings
from src.exceptions import NetworkError, RateLimitError as BotRateLimitError, RequestTimeoutError
from src.utils.logger import OPERATION_EMOJIS, get_logger
from src.utils.retry import retry


class LLMClient:
    """LLM API client with retry and error handling.

    Provides methods to interact with GLM API using OpenAI-compatible protocol.
    All API calls are wrapped with retry logic and proper error handling.

    Attributes:
        _client: The underlying OpenAI client instance
        _model: The model name to use
        _timeout: Request timeout in seconds

    Example:
        >>> with LLMClient() as client:
        ...     response = client.chat([{"role": "user", "content": "Hello!"}])
        ...     print(response)
    """

    def __init__(self) -> None:
        """Initialize the LLM client with settings from config."""
        self._logger = get_logger(__name__)

        # Load configuration
        self._api_base = settings.llm.api_base
        self._api_key = settings.llm.api_key
        self._model = settings.llm.model
        self._timeout = settings.llm.timeout

        # Log initialization (with masked API key)
        self._logger.info(
            f"{OPERATION_EMOJIS['network']} Initializing LLM client "
            f"(model={self._model}, api_base={self._api_base}, "
            f"api_key={self._mask_api_key(self._api_key)})"
        )

        # Initialize OpenAI client
        self._client = OpenAI(
            api_key=self._api_key,
            base_url=self._api_base,
            timeout=self._timeout,
        )

    def _mask_api_key(self, api_key: str) -> str:
        """Mask API key for logging (show only first 4 chars).

        Args:
            api_key: The API key to mask

        Returns:
            Masked API key (e.g., "sk-a****xxxx")
        """
        if not api_key:
            return "[NOT_SET]"
        if len(api_key) <= 4:
            return "****"
        return f"{api_key[:4]}****{api_key[-4:]}"

    def __enter__(self) -> "LLMClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        # OpenAI client doesn't need explicit cleanup
        pass

    @retry(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        exceptions=(NetworkError, BotRateLimitError, RequestTimeoutError),
    )
    def chat(self, messages: list[dict[str, str]]) -> str:
        """Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
                Example: [{"role": "user", "content": "Hello!"}]

        Returns:
            The assistant's response text

        Raises:
            NetworkError: If API request fails
            BotRateLimitError: If rate limit is exceeded
            RequestTimeoutError: If request times out
        """
        self._logger.info(
            f"{OPERATION_EMOJIS['analysis']} Sending LLM request "
            f"(model={self._model}, messages={len(messages)})"
        )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
            )

            content = response.choices[0].message.content or ""
            self._logger.info(
                f"{OPERATION_EMOJIS['analysis']} LLM response received "
                f"(tokens={response.usage.total_tokens if response.usage else 'N/A'})"
            )
            return content

        except APITimeoutError as e:
            raise RequestTimeoutError(
                message="LLM API request timed out",
                endpoint="chat",
                timeout_seconds=self._timeout,
                original_exception=e,
            )
        except RateLimitError as e:
            retry_after = None
            if hasattr(e, "response") and hasattr(e.response, "headers"):
                retry_after_str = e.response.headers.get("Retry-After")
                if retry_after_str:
                    try:
                        retry_after = int(retry_after_str)
                    except ValueError:
                        pass
            raise BotRateLimitError(
                message="LLM API rate limit exceeded",
                endpoint="chat",
                retry_after=retry_after,
                original_exception=e,
            )
        except APIConnectionError as e:
            raise NetworkError(
                message=f"LLM API connection error: {e}",
                endpoint="chat",
                original_exception=e,
            )
        except APIStatusError as e:
            raise NetworkError(
                message=f"LLM API error: {e.status_code}",
                endpoint="chat",
                status_code=e.status_code,
                original_exception=e,
            )

    def chat_with_system(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Send a chat request with system and user prompts.

        Args:
            system_prompt: System prompt to set the assistant's behavior
            user_prompt: User's question or request

        Returns:
            The assistant's response text

        Example:
            >>> with LLMClient() as client:
            ...     response = client.chat_with_system(
            ...         system_prompt="You are a prediction market analyst.",
            ...         user_prompt="Analyze this market: ..."
            ...     )
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.chat(messages)
```

### 异常类型 [Source: src/exceptions.py]

**已存在的异常:**

```python
class NetworkError(BotError):
    """Network/API error."""
    def __init__(
        self,
        message: str,
        endpoint: str = "",
        status_code: int | None = None,
        original_exception: Exception | None = None,
    ): ...

class RateLimitError(BotError):
    """Rate limit exceeded error."""
    def __init__(
        self,
        message: str,
        endpoint: str = "",
        retry_after: int | None = None,
        original_exception: Exception | None = None,
    ): ...

class RequestTimeoutError(BotError):
    """Request timeout error."""
    def __init__(
        self,
        message: str,
        endpoint: str = "",
        timeout_seconds: float | None = None,
        original_exception: Exception | None = None,
    ): ...
```

### 重试装饰器 [Source: src/utils/retry.py]

**已存在的重试装饰器:**

```python
@retry(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    exceptions=(NetworkError, RateLimitError, RequestTimeoutError),
)
def chat(self, messages: list[dict[str, str]]) -> str:
    ...
```

### 日志系统 [Source: src/utils/logger.py]

**使用 OPERATION_EMOJIS:**

```python
from src.utils.logger import OPERATION_EMOJIS, get_logger

logger = get_logger(__name__)

# 使用 Emoji 记录操作
logger.info(f"{OPERATION_EMOJIS['network']} Initializing LLM client")
logger.info(f"{OPERATION_EMOJIS['analysis']} Sending LLM request")
logger.error(f"{OPERATION_EMOJIS['error']} LLM API error: {e}")
```

**Emoji 映射 (来自 logger.py):**
- `network`: 网络操作
- `analysis`: 分析操作 (LLM)
- `error`: 错误
- `success`: 成功

### 项目结构 [Source: architecture.md#Project Structure]

**新增文件:**
```
src/api/
├── __init__.py          # 更新: 导出 LLMClient
├── polymarket.py        # 已存在
└── llm.py               # 新增: LLM API 客户端

tests/test_api/
├── __init__.py          # 已存在
├── test_polymarket.py   # 已存在
└── test_llm.py          # 新增: LLM 客户端测试
```

### 测试策略

```python
# tests/test_api/test_llm.py
"""Tests for LLMClient."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from openai import (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    APIStatusError,
)

from src.api.llm import LLMClient
from src.exceptions import NetworkError, RateLimitError as BotRateLimitError, RequestTimeoutError


class TestLLMClient:
    """Tests for LLMClient class."""

    def test_init(self) -> None:
        """Test LLM client initialization."""
        with patch("src.api.llm.settings") as mock_settings:
            mock_settings.llm.api_base = "https://api.example.com"
            mock_settings.llm.api_key = "test-api-key-1234"
            mock_settings.llm.model = "test-model"
            mock_settings.llm.timeout = 30

            with LLMClient() as client:
                assert client._model == "test-model"
                assert client._timeout == 30

    def test_mask_api_key(self) -> None:
        """Test API key masking."""
        with patch("src.api.llm.settings") as mock_settings:
            mock_settings.llm.api_base = "https://api.example.com"
            mock_settings.llm.api_key = "test-key"
            mock_settings.llm.model = "test-model"
            mock_settings.llm.timeout = 30

            with LLMClient() as client:
                assert client._mask_api_key("abcdefghijklmnop") == "abcd****mnop"
                assert client._mask_api_key("short") == "****"
                assert client._mask_api_key("") == "[NOT_SET]"

    def test_chat_success(self) -> None:
        """Test successful chat request."""
        with patch("src.api.llm.settings") as mock_settings:
            mock_settings.llm.api_base = "https://api.example.com"
            mock_settings.llm.api_key = "test-key"
            mock_settings.llm.model = "test-model"
            mock_settings.llm.timeout = 30

            with patch("src.api.llm.OpenAI") as mock_openai:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Test response"
                mock_response.usage.total_tokens = 10

                mock_openai.return_value.chat.completions.create.return_value = mock_response

                with LLMClient() as client:
                    response = client.chat([{"role": "user", "content": "Hello"}])
                    assert response == "Test response"

    def test_chat_with_system(self) -> None:
        """Test chat with system prompt."""
        with patch("src.api.llm.settings") as mock_settings:
            mock_settings.llm.api_base = "https://api.example.com"
            mock_settings.llm.api_key = "test-key"
            mock_settings.llm.model = "test-model"
            mock_settings.llm.timeout = 30

            with patch("src.api.llm.OpenAI") as mock_openai:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Response"
                mock_response.usage.total_tokens = 10

                mock_openai.return_value.chat.completions.create.return_value = mock_response

                with LLMClient() as client:
                    response = client.chat_with_system(
                        system_prompt="You are helpful.",
                        user_prompt="Hello"
                    )
                    assert response == "Response"

                    # Verify messages format
                    call_args = mock_openai.return_value.chat.completions.create.call_args
                    messages = call_args.kwargs["messages"]
                    assert messages[0]["role"] == "system"
                    assert messages[1]["role"] == "user"

    def test_chat_timeout_error(self) -> None:
        """Test chat timeout error handling."""
        with patch("src.api.llm.settings") as mock_settings:
            mock_settings.llm.api_base = "https://api.example.com"
            mock_settings.llm.api_key = "test-key"
            mock_settings.llm.model = "test-model"
            mock_settings.llm.timeout = 30

            with patch("src.api.llm.OpenAI") as mock_openai:
                mock_openai.return_value.chat.completions.create.side_effect = APITimeoutError(
                    request=MagicMock()
                )

                with LLMClient() as client:
                    with pytest.raises(RequestTimeoutError):
                        client.chat([{"role": "user", "content": "Hello"}])

    def test_chat_rate_limit_error(self) -> None:
        """Test chat rate limit error handling."""
        with patch("src.api.llm.settings") as mock_settings:
            mock_settings.llm.api_base = "https://api.example.com"
            mock_settings.llm.api_key = "test-key"
            mock_settings.llm.model = "test-model"
            mock_settings.llm.timeout = 30

            with patch("src.api.llm.OpenAI") as mock_openai:
                mock_response = MagicMock()
                mock_response.headers = {"Retry-After": "60"}

                mock_openai.return_value.chat.completions.create.side_effect = RateLimitError(
                    message="Rate limit",
                    response=mock_response,
                    body=MagicMock()
                )

                with LLMClient() as client:
                    with pytest.raises(BotRateLimitError) as exc_info:
                        client.chat([{"role": "user", "content": "Hello"}])
                    assert exc_info.value.retry_after == 60
```

### 依赖关系

**本故事依赖:**
- Story 1.2: 配置管理系统 (LLMSettings)
- Story 1.3: 日志系统 (get_logger, OPERATION_EMOJIS)
- Story 1.4: 自定义异常体系 (NetworkError, RateLimitError, RequestTimeoutError)
- Story 1.5: 重试机制 (@retry)

**后续故事依赖本故事:**
- Story 3.2: LLM 提示词模板 (需要 LLMClient)
- Story 3.3: LLM 分析引擎 (需要 LLMClient)

### 实现注意事项

**关键点:**

1. **OpenAI 库配置**: 使用 `base_url` 参数而非 `api_base`
2. **超时设置**: 默认 30 秒，满足 NFR3 要求
3. **日志脱敏**: API Key 只显示前4位和后4位
4. **重试装饰器**: 只对网络相关异常重试
5. **异常映射**: OpenAI 异常映射到项目自定义异常

**与 PolymarketClient 的区别:**
- PolymarketClient 使用同步 `@retry` + py-clob-client
- LLMClient 也使用同步方法（与 openai 库保持一致）
- 两者都使用相同的重试和异常处理模式

**GLM API 特殊说明:**
- GLM 使用 OpenAI 兼容协议
- API Base: `https://open.bigmodel.cn/api/paas/v4`
- 默认模型: `glm-4`
- 需要从智谱 AI 获取 API Key

### 前一个故事学习 [Source: 2-4-market-data-repository.md]

**从 Story 2.4 学到的模式:**

1. **使用 `from __future__ import annotations`** - 支持 Python 3.10+ 类型语法
2. **类型注解使用 `str | None`** - 而非 `Optional[str]`
3. **类型注解使用 `list[dict]`** - 而非 `List[Dict]`
4. **使用 OPERATION_EMOJIS** - 标准化日志 Emoji
5. **返回类型安全结果** - 明确的返回类型注解
6. **使用 pytest + mock** - 单元测试
7. **边界值测试** - 测试 None、空列表等情况
8. **上下文管理器** - `__enter__` 和 `__exit__`

### References

- [Source: architecture.md#Core Dependencies] - LLM 技术栈
- [Source: architecture.md#Security] - API Key 保护
- [Source: architecture.md#Logging Patterns] - 日志格式和 Emoji
- [Source: src/config.py] - LLMSettings 配置
- [Source: src/exceptions.py] - 自定义异常
- [Source: src/utils/retry.py] - 重试装饰器
- [Source: src/utils/logger.py] - 日志系统
- [Source: src/api/polymarket.py] - 参考客户端实现模式
- [Source: epics.md#Story 3.1] - 原始 Story 定义
- [Source: 2-4-market-data-repository.md] - 前一个故事学习

## Dev Agent Record

### Agent Model Used

GLM-5 (via Claude Code / Happy)

### Debug Log References

无

### Completion Notes List

**2026-02-16 - Story 3.1 完成**

1. **实现的功能**:
   - `LLMClient` 类: 使用 OpenAI 兼容协议连接 GLM API
   - `chat(messages)` 方法: 发送对话请求
   - `chat_with_system(system_prompt, user_prompt)` 方法: 带 system prompt 的对话
   - `_mask_api_key(api_key)` 方法: API Key 日志脱敏

2. **错误处理**:
   - `APITimeoutError` -> `RequestTimeoutError`
   - `RateLimitError` -> `BotRateLimitError`
   - `APIConnectionError` -> `NetworkError`
   - `APIStatusError` -> `NetworkError`

3. **重试机制**:
   - 使用 `@retry` 装饰器
   - 最大重试 3 次
   - 指数退避 (1s -> 30s)

4. **类型安全**:
   - 使用 `ChatCompletionMessageParam` 类型
   - mypy 类型检查通过

5. **测试覆盖**:
   - 18 个测试用例全部通过
   - 覆盖初始化、chat、chat_with_system、错误处理、API Key 脱敏、重试机制

6. **代码质量**:
   - mypy 类型检查通过
   - black 格式化通过
   - isort 导入排序通过

### File List

**新增的文件:**
- `src/api/llm.py` - LLM API 客户端实现
- `tests/test_api/test_llm.py` - LLM 客户端测试

**修改的文件:**
- `src/api/__init__.py` - 添加 LLMClient 导出

**已存在的文件 (无需修改):**
- `src/config.py` - LLMSettings 已存在
- `src/exceptions.py` - 异常类型已存在
- `src/utils/retry.py` - 重试装饰器已存在
- `src/utils/logger.py` - 日志系统已存在
