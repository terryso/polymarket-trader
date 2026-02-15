# Story 1.5: 重试机制

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **开发者**,
I want **实现指数退避重试装饰器**,
So that **API 调用更加健壮**.

## Acceptance Criteria

**Given** 异常体系已实现
**When** 实现 `src/utils/retry.py`
**Then** 创建 `@retry` 装饰器支持:
- 最大重试次数: 3
- 基础延迟: 1s
- 最大延迟: 30s
- 指数退避
- 可配置重试异常类型
**And** 支持异步函数
**And** 记录重试日志

## Tasks / Subtasks

- [x] Task 1: 实现 retry 装饰器 (AC: All)
  - [x] 1.1 创建 `src/utils/retry.py` 文件
  - [x] 1.2 实现 `RetryConfig` 配置类
  - [x] 1.3 实现同步函数的 `@retry` 装饰器
  - [x] 1.4 实现异步函数的 `@retry` 装饰器
  - [x] 1.5 实现指数退避延迟计算逻辑
  - [x] 1.6 集成日志记录 (使用 project emoji 🔄)

- [x] Task 2: 编写测试 (AC: All)
  - [x] 2.1 创建 `tests/test_retry.py` 测试文件
  - [x] 2.2 测试同步函数重试
  - [x] 2.3 测试异步函数重试
  - [x] 2.4 测试指数退避延迟计算
  - [x] 2.5 测试最大重试次数限制
  - [x] 2.6 测试可配置异常类型
  - [x] 2.7 测试成功后不重试
  - [x] 2.8 测试重试日志输出

- [x] Task 3: 代码质量检查 (AC: All)
  - [x] 3.1 运行 `mypy src/utils/retry.py` 无错误
  - [x] 3.2 运行 `black --check src/utils/retry.py` 通过
  - [x] 3.3 运行 `isort --check src/utils/retry.py` 通过
  - [x] 3.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md#API & Communication Patterns]

**重试策略配置:**

| 参数 | 值 | 说明 |
|------|-----|------|
| max_attempts | 3 | 最大重试次数 |
| base_delay | 1s | 初始延迟 |
| max_delay | 30s | 最大延迟 |
| exponential_backoff | True | 指数退避 |
| 适用异常 | NetworkError, RateLimitError, RequestTimeoutError | - |

**重试装饰器使用示例:**

```python
@retry(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_backoff=True,
    exceptions=(NetworkError, RateLimitError, RequestTimeoutError)
)
async def call_api(...):
    ...
```

### 指数退避算法

**延迟计算公式:**
```
delay = min(base_delay * (2 ** attempt), max_delay)
```

| 重试次数 | 计算公式 | 延迟 |
|----------|----------|------|
| 1 | 1 * 2^0 = 1 | 1s |
| 2 | 1 * 2^1 = 2 | 2s |
| 3 | 1 * 2^2 = 4 | 4s |

### 异常类型 [Source: src/exceptions.py]

重试装饰器应捕获以下异常类型 (来自 Story 1-4):

```python
from src.exceptions import (
    NetworkError,
    RateLimitError,
    RequestTimeoutError,  # 注意: 实际类名是 RequestTimeoutError
)
```

**异常层次:**
```
BotError (基类)
├── NetworkError        # 网络错误 - 可重试
│   ├── RateLimitError  # API 限流 - 可重试
│   └── RequestTimeoutError  # 请求超时 - 可重试
```

### 代码规范 [Source: project-context.md]

**类型注解 (mypy strict mode):**
- ALL 函数必须有完整类型注解
- 使用 `from __future__ import annotations` (Python 3.9+ 兼容)
- 使用 `str | None` 语法 (Python 3.10+)，不是 `Optional[str]`
- 使用 `list[Type]` 语法，不是 `List[Type]`
- 使用 `Callable[..., T]` 类型

**命名规范:**
- 文件: `snake_case.py` → `retry.py`
- 类: PascalCase → `RetryConfig`
- 函数: snake_case → `calculate_delay()`
- 装饰器: snake_case → `@retry`
- 常量: UPPER_SNAKE_CASE → `DEFAULT_MAX_ATTEMPTS`

### 日志格式 [Source: architecture.md#Logging Patterns]

```
{timestamp} | {level:8} | {thread:12} | {module} | {emoji} {message}
```

**重试相关 Emoji:**
- 重试开始: 🔄
- 重试成功: ✅
- 重试失败: ❌

**日志示例:**
```
2026-02-15 10:30:00 | WARNING  | MainThread  | src.utils.retry | 🔄 Retrying call_api (attempt 1/3) after 1.0s: NetworkError
2026-02-15 10:30:02 | WARNING  | MainThread  | src.utils.retry | 🔄 Retrying call_api (attempt 2/3) after 2.0s: NetworkError
2026-02-15 10:30:05 | INFO     | MainThread  | src.utils.retry | ✅ call_api succeeded after 2 retries
```

### 实现参考

**RetryConfig 配置类:**

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar, cast

T = TypeVar("T")

@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_backoff: bool = True
    exceptions: tuple[type[Exception], ...] = (Exception,)

    def calculate_delay(self, attempt: int) -> float:
        """计算第 N 次重试的延迟时间"""
        if not self.exponential_backoff:
            return self.base_delay
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)
```

**同步装饰器签名:**

```python
def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_backoff: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    ...
```

**异步装饰器签名:**

```python
def retry_async(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_backoff: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    ...
```

**或者使用统一的 `@retry` 装饰器自动检测同步/异步:**

```python
import asyncio
import functools
from typing import ParamSpec

P = ParamSpec("P")
R = TypeVar("R")

def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_backoff: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """统一的重试装饰器，自动检测同步/异步函数"""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                ...
            return cast(Callable[P, R], async_wrapper)
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                ...
            return cast(Callable[P, R], sync_wrapper)

    return decorator
```

### 测试策略

**测试文件结构:**

```python
# tests/test_retry.py

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.utils.retry import retry, RetryConfig
from src.exceptions import NetworkError, RateLimitError, RequestTimeoutError

class TestRetryConfig:
    """测试 RetryConfig 配置类"""

    def test_default_values(self) -> None: ...
    def test_calculate_delay_linear(self) -> None: ...
    def test_calculate_delay_exponential(self) -> None: ...
    def test_calculate_delay_respects_max(self) -> None: ...

class TestRetrySync:
    """测试同步函数重试"""

    def test_no_retry_on_success(self) -> None: ...
    def test_retry_on_exception(self) -> None: ...
    def test_max_attempts_reached(self) -> None: ...
    def test_only_configured_exceptions_trigger_retry(self) -> None: ...
    def test_success_after_retry(self) -> None: ...

class TestRetryAsync:
    """测试异步函数重试"""

    @pytest.mark.asyncio
    async def test_no_retry_on_success(self) -> None: ...
    @pytest.mark.asyncio
    async def test_retry_on_exception(self) -> None: ...
    @pytest.mark.asyncio
    async def test_max_attempts_reached(self) -> None: ...
    @pytest.mark.asyncio
    async def test_success_after_retry(self) -> None: ...

class TestRetryLogging:
    """测试重试日志"""

    def test_logs_retry_attempt(self, caplog: pytest.LogCaptureFixture) -> None: ...
    def test_logs_success_after_retry(self, caplog: pytest.LogCaptureFixture) -> None: ...
    def test_logs_final_failure(self, caplog: pytest.LogCaptureFixture) -> None: ...
```

### Project Structure Notes

- 文件位置: `src/utils/retry.py` (需创建)
- 测试位置: `tests/test_retry.py` (需创建)
- 依赖: `src/exceptions.py` (已完成)
- 依赖: `src/utils/logger.py` (已完成)

**目录结构确认:**
```
src/
└── utils/
    ├── __init__.py  (已存在)
    ├── logger.py    (已完成 - Story 1.3)
    └── retry.py     (待创建 - 本 Story)
```

### References

- [Source: architecture.md#API & Communication Patterns] - 重试策略配置
- [Source: architecture.md#Logging Patterns] - 日志格式和 Emoji
- [Source: project-context.md#Code Quality] - 代码规范和类型注解
- [Source: project-context.md#Performance] - 不要在循环中查询
- [Source: epics.md#Story 1.5] - 原始 Story 定义
- [Source: src/exceptions.py] - 可重试异常类型定义
- [Source: tests/test_exceptions.py] - 测试模式参考

### 与后续 Story 的关系

**Story 1.5 完成后，重试装饰器将被以下模块使用:**

| 模块 | 文件 | 用途 |
|------|------|------|
| Polymarket API | `src/api/polymarket.py` | API 调用重试 |
| LLM API | `src/api/llm.py` | LLM 调用重试 |
| 市场数据获取 | `src/storage/database.py` | 数据库操作重试 |

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6-20250528)

### Debug Log References

无

### Completion Notes List

- 2026-02-15: 实现了完整的重试装饰器，支持同步和异步函数
- 使用 `@dataclass` 实现 `RetryConfig` 配置类
- 使用 `asyncio.iscoroutinefunction()` 自动检测函数类型
- 实现指数退避算法: `delay = min(base_delay * (2 ** attempt), max_delay)`
- 集成项目日志系统，使用 emoji (🔄 ✅ 💥) 标识重试状态
- 编写 32 个测试用例，覆盖同步/异步重试、指数退避、日志输出、参数验证等场景
- 通过 mypy strict mode 类型检查
- 通过 black 和 isort 代码格式检查
- 完整测试套件 177 个测试全部通过

### Senior Developer Review (AI)

**审查日期:** 2026-02-15
**审查者:** Claude Opus 4.6 (BMAD Code Review Workflow)

**发现的问题 (已修复):**

| 严重性 | 问题 | 修复内容 |
|--------|------|----------|
| HIGH | `max_attempts=0` 导致 RuntimeError | 添加 `__post_init__` 验证，抛出 ValueError |
| HIGH | 负数 `base_delay` 导致 ValueError | 添加参数验证，确保非负 |
| HIGH | ERROR 日志双 Emoji (❌ ❌) | 改用 💥 作为失败 emoji，避免与 logger 的 ❌ 冲突 |
| MEDIUM | 缺少输入参数验证 | 添加完整的 `__post_init__` 验证逻辑 |
| MEDIUM | 缺少 jitter 支持 | 添加 `jitter` 参数支持随机延迟抖动 |
| MEDIUM | 测试覆盖不足 | 新增 9 个边界情况测试用例 |
| MEDIUM | 日志测试断言太弱 | 增强断言验证无双 emoji |

**修复后测试结果:** 32 个测试全部通过，完整套件 177 个测试通过

### File List

**新增文件:**
- `src/utils/retry.py` - 重试装饰器模块
- `tests/test_retry.py` - 重试模块测试文件

## Change Log

- 2026-02-15: Story 实现完成，所有 AC 满足，23 个测试通过，状态更新为 review
- 2026-02-15: 代码审查修复 - 添加参数验证、修复双 emoji bug、增加 jitter 支持、新增 9 个边界测试用例，状态更新为 done
