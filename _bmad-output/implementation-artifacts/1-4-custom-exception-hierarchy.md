# Story 1.4: 自定义异常体系

Status: done

<!-- Note: 实现已存在并通过验证 -->

## Story

As a **开发者**,
I want **实现自定义异常层次结构**,
So that **错误处理清晰且可区分**.

## Acceptance Criteria

**Given** 项目结构已创建
**When** 实现 `src/exceptions.py`
**Then** 创建以下异常层次:
- `BotError` (基类)
- `ConfigurationError` (配置错误)
- `NetworkError` (网络错误)
- `TradingError` (交易错误)
- `ValidationError` (验证错误)
**And** 每个异常支持自定义消息和原始异常

## Tasks / Subtasks

- [x] Task 1: 验证现有实现 (AC: All)
  - [x] 1.1 确认 `src/exceptions.py` 异常层次完整 ✅
  - [x] 1.2 验证所有异常类继承关系正确 ✅
  - [x] 1.3 确认类型注解完整 (mypy strict mode) ✅
  - [x] 1.4 验证异常消息格式符合规范 ✅

- [x] Task 2: 验证测试覆盖 (AC: All)
  - [x] 2.1 确认 `tests/test_exceptions.py` 覆盖所有异常类 ✅
  - [x] 2.2 验证测试覆盖原始异常传递 ✅
  - [x] 2.3 验证测试覆盖上下文参数 ✅
  - [x] 2.4 运行完整测试套件确保通过 ✅ (30/30 passed)

- [x] Task 3: 代码质量检查 (AC: All)
  - [x] 3.1 运行 `mypy src/exceptions.py` 无错误 ✅
  - [x] 3.2 运行 `black --check src/exceptions.py` 通过 ✅
  - [x] 3.3 运行 `isort --check src/exceptions.py` 通过 ✅

## Dev Notes

### 现有实现状态

**✅ 已实现 (src/exceptions.py:1-244):**

异常层次结构:

```
BotError (基类)
├── ConfigurationError  # 配置错误
├── NetworkError        # 网络错误
│   ├── RateLimitError  # API 限流
│   └── TimeoutError    # 请求超时
├── TradingError        # 交易错误
│   ├── InsufficientFundsError  # 资金不足
│   └── RiskLimitExceededError  # 风险超限
└── ValidationError     # 验证错误
```

**核心实现:**

```python
class BotError(Exception):
    """Base exception for all Polymarket Trader errors."""

    def __init__(
        self,
        message: str,
        original_exception: Optional[Exception] = None,
        **context: Any
    ) -> None:
        super().__init__(message)
        self.message = message
        self.original_exception = original_exception
        self.context = context

    def __str__(self) -> str:
        if self.original_exception:
            return f"{self.message} (caused by: {self.original_exception})"
        return self.message
```

**各异常类特性:**

| 异常类 | 特定参数 | 用途 |
|--------|----------|------|
| `ConfigurationError` | `config_key` | 配置缺失/无效 |
| `NetworkError` | `endpoint`, `status_code` | API 通信失败 |
| `TradingError` | `market_id`, `trade_type` | 交易执行失败 |
| `ValidationError` | `field`, `value` | 数据验证失败 |
| `RateLimitError` | `retry_after` | API 限流 |
| `TimeoutError` | `timeout_seconds` | 请求超时 |
| `InsufficientFundsError` | `required`, `available` | 资金不足 |
| `RiskLimitExceededError` | `limit_type`, `current`, `limit` | 风险超限 |

### 现有测试状态

**✅ 已实现 (tests/test_exceptions.py:1-253):**

| 测试类 | 测试数 | 覆盖内容 |
|--------|--------|----------|
| `TestBotError` | 4 | 基础错误、原始异常、上下文 |
| `TestConfigurationError` | 3 | 默认消息、config_key |
| `TestNetworkError` | 4 | endpoint、status_code、完整详情 |
| `TestTradingError` | 4 | market_id、trade_type、完整详情 |
| `TestValidationError` | 3 | field、value |
| `TestRateLimitError` | 3 | retry_after、继承验证 |
| `TestTimeoutError` | 3 | timeout_seconds、继承验证 |
| `TestInsufficientFundsError` | 3 | required/available、继承验证 |
| `TestRiskLimitExceededError` | 3 | limit_type、继承验证 |

**总计: 30 个测试用例**

### 架构约束 [Source: architecture.md#Error Handling Patterns]

**异常层次:**
```python
class BotError(Exception):
    """基础异常"""
    pass

class ConfigurationError(BotError):
    """配置错误"""
    pass

class NetworkError(BotError):
    """网络错误"""
    pass

class TradingError(BotError):
    """交易错误"""
    pass

class ValidationError(BotError):
    """验证错误"""
    pass
```

**错误处理模式:**
```python
try:
    result = await api_call()
except NetworkError as e:
    logger.error(f"❌ Network error: {e}")
    # 重试或降级处理
except ValidationError as e:
    logger.warning(f"⚠️ Validation error: {e}")
    # 跳过或修正数据
except Exception as e:
    logger.critical(f"🔥 Unexpected error: {e}")
    raise
```

### 代码规范 [Source: project-context.md]

**类型注解 (mypy strict mode):**
- ALL 函数必须有完整类型注解
- 使用 `str | None` 语法 (Python 3.10+)，不是 `Optional[str]`
- 使用 `list[Model]` 语法，不是 `List[Model]`

**命名规范:**
- 异常类: PascalCase (如 `NetworkError`)
- 参数: snake_case (如 `market_id`, `config_key`)

### 使用示例

```python
from src.exceptions import (
    BotError, ConfigurationError, NetworkError,
    TradingError, ValidationError, RateLimitError,
    TimeoutError, InsufficientFundsError, RiskLimitExceededError
)

# 配置错误
if not config.api_key:
    raise ConfigurationError("Missing API key", config_key="LLM_API_KEY")

# 网络错误 (带重试装饰器)
try:
    response = await api_client.get("/markets")
except aiohttp.ClientError as e:
    raise NetworkError(
        "Failed to fetch markets",
        endpoint="/api/markets",
        status_code=response.status if response else None,
        original_exception=e
    )

# 交易错误
if available_funds < trade_amount:
    raise InsufficientFundsError(
        required=trade_amount,
        available=available_funds,
        market_id=market.id
    )

# 风险控制
if daily_loss_pct > MAX_DAILY_LOSS:
    raise RiskLimitExceededError(
        limit_type="daily_loss",
        current=daily_loss_pct,
        limit=MAX_DAILY_LOSS
    )

# 验证错误
if market.deadline < datetime.now():
    raise ValidationError(
        "Market deadline has passed",
        field="deadline",
        value=market.deadline.isoformat()
    )
```

### 与重试机制的集成 [Source: architecture.md#Retry Strategy]

重试装饰器应捕获以下异常类型:
- `NetworkError`
- `RateLimitError`
- `TimeoutError`

```python
@retry(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_backoff=True,
    exceptions=(NetworkError, RateLimitError, TimeoutError)
)
async def call_api(...):
    ...
```

### Project Structure Notes

- 异常文件位置: `src/exceptions.py` (已存在)
- 测试文件位置: `tests/test_exceptions.py` (已存在)
- 此故事无新文件需要创建

### References

- [Source: architecture.md#Error Handling Patterns] - 异常层次和处理模式
- [Source: architecture.md#API & Communication Patterns] - 重试策略配置
- [Source: project-context.md#Exception Handling] - 使用项目异常层次
- [Source: epics.md#Story 1.4] - 原始 Story 定义
- [Source: src/exceptions.py] - 现有实现代码
- [Source: tests/test_exceptions.py] - 现有测试代码

## Dev Agent Record

### Agent Model Used

GLM-5 (Claude Opus 4.6 compatible)

### Debug Log References

N/A - 实现已存在，仅执行验证

### Completion Notes List

1. **验证结果 - 测试**: 30/30 测试通过 (0.03s)
   - TestBotError: 4 tests ✅
   - TestConfigurationError: 3 tests ✅
   - TestNetworkError: 4 tests ✅
   - TestTradingError: 4 tests ✅
   - TestValidationError: 3 tests ✅
   - TestRateLimitError: 3 tests ✅
   - TestTimeoutError: 3 tests ✅
   - TestInsufficientFundsError: 3 tests ✅
   - TestRiskLimitExceededError: 3 tests ✅

2. **验证结果 - 类型检查**: mypy strict mode 通过，无问题

3. **实现质量评估**: 优秀
   - 超出原始需求: 实现了 4 个额外的异常类
   - 完整的类型注解
   - 清晰的错误消息格式
   - 良好的继承层次设计

### File List

- `src/exceptions.py` (已验证 - 265 行，9 个异常类 + 向后兼容别名)
- `tests/test_exceptions.py` (已验证 - 354 行，37 个测试)

## Change Log

| Date | Change |
|------|--------|
| 2026-02-15 | 创建故事文件，验证现有实现 |
| 2026-02-15 | 确认 30/30 测试通过 |
| 2026-02-15 | 确认 mypy strict mode 通过 |
| 2026-02-15 | **代码审查修复**: (1) 使用 `X \| None` 语法替代 `Optional[X]` (2) 重命名 TimeoutError → RequestTimeoutError 并添加向后兼容别名 (3) 添加 `__all__` 导出声明 (4) 为 6 个子类异常添加 original_exception 测试 (5) 添加 `from __future__ import annotations` 支持 Python 3.9+ |
| 2026-02-15 | 确认 37/37 测试通过 (新增 7 个测试) |
