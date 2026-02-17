# Story 8.5: 错误处理与告警

**Story ID:** 8-5-error-handling-and-alerting
**Epic:** Epic 8 - 系统调度与自动化运行
**Status:** ready-for-dev
**Created:** 2026-02-17

---

## User Story

As a **用户**,
I want **系统在遇到错误时能够正确处理并记录**,
So that **问题可追踪且不影响整体运行**.

---

## Context

这是 Epic 8 的第五个故事，在自动恢复机制 (Story 8.4) 完成后，需要实现全局错误处理和告警机制，确保系统在遇到各种错误时能够正确处理、记录并告警，而不影响整体运行。

### Prerequisites
- Epic 1-7 已完成
- Story 8.1: APScheduler 调度器配置 (已完成)
- Story 8.2: 定时任务配置 (已完成)
- Story 8.3: 主入口与启动流程 (已完成)
- Story 8.4: 自动恢复机制 (已完成)
- 现有异常体系 (src/exceptions.py)
- 现有日志系统 (src/utils/logger.py)
- 现有状态管理 (src/core/state.py)
- 现有数据库系统 (src/storage/database.py)

---

## Acceptance Criteria

### AC1: 全局异常处理器

**Given** 自动恢复机制已实现
**When** 实现全局错误处理
**Then** 配置全局异常处理器:
- 捕获未处理异常
- 记录详细错误日志 (使用 CRITICAL 级别)
- 不中断主循环运行
- 记录到 `logs/errors.log`
- 设置系统状态 `last_error` 字段

### AC2: 任务级错误处理

**Given** 调度任务正在运行
**When** 单个任务执行失败
**Then** 执行任务级错误处理:
- 单个任务失败不影响其他任务
- 失败任务自动重试 (最多 3 次)
- 连续失败触发告警
- 记录任务错误日志

### AC3: 错误告警机制

**Given** 错误被捕获
**When** 满足告警条件
**Then** 实现错误告警机制:
- 记录到 `logs/errors.log` 专用错误日志文件
- 设置系统状态 `last_error` 字段
- 支持配置告警阈值 (连续失败次数等)
- 可选: 集成外部告警 (邮件、Webhook 等)

### AC4: API 错误处理

**Given** FastAPI 应用正在运行
**When** API 请求发生错误
**Then** 实现 API 错误处理:
- 返回统一错误格式
- 记录 API 错误日志
- 不暴露敏感信息
- 区分客户端错误 (4xx) 和服务端错误 (5xx)

### AC5: 单元测试

**Given** 错误处理机制实现完成
**When** 编写单元测试
**Then** 创建/更新测试文件包含:
- 测试全局异常处理器
- 测试任务级错误处理
- 测试错误告警机制
- 测试 API 错误处理

---

## Technical Design

### File Structure

```
src/
├── core/
│   ├── __init__.py
│   ├── error_handler.py        # 新增: 全局错误处理器
│   ├── alerting.py             # 新增: 告警机制
│   ├── scheduler.py            # 已有: 调度器 (需要扩展)
│   └── state.py                # 已有: 状态管理
├── dashboard/
│   ├── app.py                  # 已有: FastAPI 应用 (需要扩展)
│   └── middleware/
│       └── error_middleware.py # 新增: API 错误中间件
├── utils/
│   └── logger.py               # 已有: 日志系统 (需要扩展)
├── exceptions.py               # 已有: 异常体系
└── main.py                     # 已有: 主入口 (需要扩展)
tests/
├── test_core/
│   ├── test_error_handler.py   # 新增: 错误处理器测试
│   └── test_alerting.py        # 新增: 告警机制测试
└── test_api/
    └── test_error_middleware.py # 新增: API 错误中间件测试
```

### Error Handler Design

```python
# src/core/error_handler.py

from typing import Callable, Any, Optional, Dict, List
from functools import wraps
from datetime import datetime
import traceback
import asyncio

from src.utils.logger import get_logger
from src.exceptions import BotError, NetworkError, TradingError, ValidationError
from src.core.alerting import AlertManager

logger = get_logger(__name__)


class ErrorHandler:
    """全局错误处理器"""

    def __init__(
        self,
        alert_manager: Optional[AlertManager] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.alert_manager = alert_manager
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._error_counts: Dict[str, int] = {}
        self._last_errors: Dict[str, datetime] = {}

    def handle_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """处理异常"""
        context = context or {}
        error_type = type(exception).__name__
        error_message = str(exception)

        # 记录错误计数
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
        self._last_errors[error_type] = datetime.utcnow()

        # 根据异常类型记录不同级别日志
        if isinstance(exception, BotError):
            # 业务异常 - ERROR 级别
            logger.error(
                f"Business error: {error_type} - {error_message}",
                extra={"context": context}
            )
        else:
            # 未预期异常 - CRITICAL 级别
            logger.critical(
                f"Unhandled exception: {error_type} - {error_message}",
                extra={
                    "context": context,
                    "traceback": traceback.format_exc()
                }
            )

        # 触发告警
        if self.alert_manager:
            self.alert_manager.check_and_alert(exception, context)

    def task_wrapper(
        self,
        task_name: str,
        retry_exceptions: tuple = (NetworkError,)
    ) -> Callable:
        """任务装饰器 - 包装异步任务以处理错误"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                last_exception = None

                for attempt in range(self.max_retries):
                    try:
                        return await func(*args, **kwargs)
                    except retry_exceptions as e:
                        last_exception = e
                        logger.warning(
                            f"Task {task_name} failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                        )
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                    except Exception as e:
                        # 非重试异常，直接处理
                        self.handle_exception(e, {"task": task_name})
                        raise

                # 所有重试都失败
                self.handle_exception(
                    last_exception,
                    {"task": task_name, "attempts": self.max_retries}
                )
                raise last_exception

            return wrapper
        return decorator

    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        return {
            "error_counts": self._error_counts.copy(),
            "last_errors": {
                k: v.isoformat() for k, v in self._last_errors.items()
            }
        }

    def reset_counts(self) -> None:
        """重置错误计数"""
        self._error_counts.clear()
        self._last_errors.clear()


# 全局错误处理器实例
_global_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器"""
    global _global_handler
    if _global_handler is None:
        _global_handler = ErrorHandler()
    return _global_handler


def setup_error_handler(alert_manager: Optional[AlertManager] = None) -> ErrorHandler:
    """设置全局错误处理器"""
    global _global_handler
    _global_handler = ErrorHandler(alert_manager=alert_manager)
    return _global_handler
```

### Alert Manager Design

```python
# src/core/alerting.py

from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json

from src.utils.logger import get_logger
from src.exceptions import BotError

logger = get_logger(__name__)


@dataclass
class Alert:
    """告警数据"""
    level: str  # INFO, WARNING, ERROR, CRITICAL
    message: str
    source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)
    count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "count": self.count
        }


class AlertChannel(ABC):
    """告警渠道抽象基类"""

    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """发送告警"""
        pass


class LogAlertChannel(AlertChannel):
    """日志告警渠道 - 写入专用错误日志文件"""

    def __init__(self, log_file: str = "logs/errors.log"):
        self.log_file = log_file

    async def send(self, alert: Alert) -> bool:
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(alert.to_dict()) + "\n")
            return True
        except Exception as e:
            logger.error(f"Failed to write alert to log: {e}")
            return False


class WebhookAlertChannel(AlertChannel):
    """Webhook 告警渠道"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send(self, alert: Alert) -> bool:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=alert.to_dict()
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False


class AlertManager:
    """告警管理器"""

    # 告警级别阈值
    LEVEL_THRESHOLD = {
        "INFO": 0,
        "WARNING": 1,
        "ERROR": 2,
        "CRITICAL": 3
    }

    def __init__(
        self,
        channels: Optional[List[AlertChannel]] = None,
        min_level: str = "WARNING",
        throttle_seconds: int = 300,  # 5 分钟内相同告警只发送一次
        consecutive_failure_threshold: int = 3
    ):
        self.channels = channels or [LogAlertChannel()]
        self.min_level = min_level
        self.throttle_seconds = throttle_seconds
        self.consecutive_failure_threshold = consecutive_failure_threshold

        # 告警历史 (用于去重)
        self._alert_history: Dict[str, datetime] = {}

        # 连续失败计数
        self._consecutive_failures: Dict[str, int] = {}

    def check_and_alert(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """检查是否需要告警"""
        context = context or {}

        # 确定告警级别
        level = self._determine_level(exception, context)

        # 检查是否满足最小级别
        if self.LEVEL_THRESHOLD.get(level, 0) < self.LEVEL_THRESHOLD.get(self.min_level, 0):
            return

        # 生成告警键 (用于去重)
        alert_key = self._generate_alert_key(exception, context)

        # 检查是否在节流时间内
        if alert_key in self._alert_history:
            elapsed = datetime.utcnow() - self._alert_history[alert_key]
            if elapsed.total_seconds() < self.throttle_seconds:
                logger.debug(f"Alert throttled: {alert_key}")
                return

        # 创建并发送告警
        alert = Alert(
            level=level,
            message=str(exception),
            source=context.get("source", "system"),
            context=context
        )

        self._send_alert(alert)
        self._alert_history[alert_key] = datetime.utcnow()

    def record_failure(self, source: str) -> None:
        """记录失败"""
        self._consecutive_failures[source] = self._consecutive_failures.get(source, 0) + 1

        if self._consecutive_failures[source] >= self.consecutive_failure_threshold:
            self.check_and_alert(
                Exception(f"Consecutive failures: {self._consecutive_failures[source]}"),
                {"source": source, "failures": self._consecutive_failures[source]}
            )

    def reset_failures(self, source: str) -> None:
        """重置失败计数"""
        self._consecutive_failures.pop(source, None)

    def _determine_level(self, exception: Exception, context: Dict[str, Any]) -> str:
        """确定告警级别"""
        # 连续失败触发 ERROR
        source = context.get("source", "")
        if self._consecutive_failures.get(source, 0) >= self.consecutive_failure_threshold:
            return "ERROR"

        # 根据异常类型确定级别
        if isinstance(exception, BotError):
            return "WARNING"
        elif isinstance(exception, (ConnectionError, TimeoutError)):
            return "ERROR"
        else:
            return "CRITICAL"

    def _generate_alert_key(self, exception: Exception, context: Dict[str, Any]) -> str:
        """生成告警键"""
        return f"{type(exception).__name__}:{context.get('source', 'unknown')}"

    def _send_alert(self, alert: Alert) -> None:
        """发送告警到所有渠道"""
        logger.info(f"Sending alert: [{alert.level}] {alert.message}")

        for channel in self.channels:
            try:
                import asyncio
                asyncio.create_task(self._send_to_channel(channel, alert))
            except Exception as e:
                logger.error(f"Failed to send alert to channel: {e}")

    async def _send_to_channel(self, channel: AlertChannel, alert: Alert) -> None:
        """发送告警到单个渠道"""
        try:
            success = await channel.send(alert)
            if success:
                logger.debug(f"Alert sent successfully to {type(channel).__name__}")
            else:
                logger.warning(f"Alert failed to send to {type(channel).__name__}")
        except Exception as e:
            logger.error(f"Error sending alert to {type(channel).__name__}: {e}")
```

### API Error Middleware Design

```python
# src/dashboard/middleware/error_middleware.py

from typing import Callable, Dict, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import traceback

from src.utils.logger import get_logger
from src.exceptions import BotError, ConfigurationError, NetworkError, TradingError, ValidationError

logger = get_logger(__name__)


class ErrorMiddleware(BaseHTTPMiddleware):
    """API 错误处理中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            return self._handle_error(request, e)

    def _handle_error(self, request: Request, error: Exception) -> JSONResponse:
        """处理错误并返回统一格式响应"""
        # 获取请��信息
        request_info = {
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else None
        }

        # 根据异常类型确定响应
        if isinstance(error, ValidationError):
            status_code = 400
            error_code = "VALIDATION_ERROR"
            message = str(error)
            log_level = "warning"
        elif isinstance(error, ConfigurationError):
            status_code = 500
            error_code = "CONFIGURATION_ERROR"
            message = "Configuration error"
            log_level = "error"
        elif isinstance(error, NetworkError):
            status_code = 503
            error_code = "NETWORK_ERROR"
            message = "Network error, please retry"
            log_level = "error"
        elif isinstance(error, TradingError):
            status_code = 400
            error_code = "TRADING_ERROR"
            message = str(error)
            log_level = "warning"
        elif isinstance(error, BotError):
            status_code = 500
            error_code = "BUSINESS_ERROR"
            message = "Business error occurred"
            log_level = "error"
        else:
            status_code = 500
            error_code = "INTERNAL_ERROR"
            message = "Internal server error"
            log_level = "critical"

        # 记录日志
        log_data = {
            "request": request_info,
            "error": str(error),
            "traceback": traceback.format_exc()
        }

        if log_level == "warning":
            logger.warning(f"API error: {error_code} - {error}", extra=log_data)
        elif log_level == "error":
            logger.error(f"API error: {error_code} - {error}", extra=log_data)
        else:
            logger.critical(f"API error: {error_code} - {error}", extra=log_data)

        # 返回统一格式响应
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": {
                    "code": error_code,
                    "message": message
                }
            }
        )


def setup_exception_handlers(app) -> None:
    """设置 FastAPI 异常处理器"""

    @app.exception_handler(BotError)
    async def bot_error_handler(request: Request, exc: BotError):
        logger.error(f"BotError: {exc}")
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "code": type(exc).__name__.upper(),
                    "message": str(exc)
                }
            }
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.critical(f"Unhandled exception: {exc}", extra={
            "traceback": traceback.format_exc()
        })
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error"
                }
            }
        )
```

### Logger Extensions for Error Log File

```python
# 在 src/utils/logger.py 中添加的配置

# 创建专用错误日志 handler
def setup_error_log_handler(log_dir: str = "logs") -> logging.Handler:
    """设置专用错误日志文件"""
    from logging.handlers import RotatingFileHandler

    error_handler = RotatingFileHandler(
        f"{log_dir}/errors.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)8s | %(message)s | %(extra)s'
    ))
    return error_handler
```

### Scheduler Extensions for Task Error Handling

```python
# 在 src/core/scheduler.py 中添加的错误处理逻辑

class Scheduler:
    """调度器 - 扩展版本"""

    # ... 现有代码 ...

    def _wrap_job_with_error_handling(self, job_func: Callable, job_id: str) -> Callable:
        """包装任务函数以添加错误处理"""
        from src.core.error_handler import get_error_handler

        error_handler = get_error_handler()

        @wraps(job_func)
        async def wrapped_job(*args, **kwargs):
            try:
                result = await job_func(*args, **kwargs)
                # 任务成功，重置失败计数
                error_handler.alert_manager.reset_failures(job_id)
                return result
            except Exception as e:
                # 记录失败
                error_handler.record_failure(job_id)
                error_handler.handle_exception(e, {
                    "source": job_id,
                    "job_id": job_id
                })
                raise

        return wrapped_job

    def add_job(
        self,
        func: Callable,
        trigger: str,
        id: str,
        **kwargs
    ) -> None:
        """添加任务 (带错误处理)"""
        wrapped_func = self._wrap_job_with_error_handling(func, id)
        self._scheduler.add_job(wrapped_func, trigger, id=id, **kwargs)
        logger.info(f"Scheduled job added: {id}")
```

### Main Entry Updates

```python
# 在 src/main.py 中添加的全局错误处理设置

import signal
import sys

from src.core.error_handler import setup_error_handler
from src.core.alerting import AlertManager, LogAlertChannel


def setup_global_exception_handler() -> None:
    """设置全局异常处理器"""
    from src.core.error_handler import get_error_handler

    def handle_exception(exc_type, exc_value, exc_traceback):
        """处理未捕获异常"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        error_handler = get_error_handler()
        error_handler.handle_exception(
            exc_value,
            {"source": "global", "traceback": "".join(traceback.format_tb(exc_traceback))}
        )

    sys.excepthook = handle_exception


def setup_async_exception_handler() -> None:
    """设置异步异常处理器"""
    import asyncio
    from src.core.error_handler import get_error_handler

    def handle_loop_exception(loop, context):
        """处理事件循环异常"""
        error_handler = get_error_handler()
        exception = context.get("exception")
        if exception:
            error_handler.handle_exception(exception, {
                "source": "async_loop",
                "message": context.get("message")
            })
        else:
            logger.error(f"Async loop error: {context}")

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_loop_exception)


class Application:
    """主应用程序类 - 扩展版本"""

    async def initialize(self) -> None:
        """初始化所有组件 (包含错误处理)"""
        logger.info("Initializing application...")

        # 0. 设置错误处理
        alert_manager = AlertManager(
            channels=[LogAlertChannel()],
            min_level="WARNING"
        )
        setup_error_handler(alert_manager)
        setup_global_exception_handler()
        setup_async_exception_handler()
        logger.info("Error handling initialized")

        # ... 其他初始化代码 ...
```

---

## Dependencies

### Python Packages
- 已有: `asyncio`, `logging`, `json`, `traceback`
- 已有: `typing`, `dataclasses`, `datetime`
- 已有: `functools`, `abc`

### Internal Dependencies
- `src/config.py` - 配置管理
- `src/exceptions.py` - 异常体系
- `src/utils/logger.py` - 日志系统 (需要扩展)
- `src/core/state.py` - 状态管理
- `src/core/scheduler.py` - 调度器 (需要扩展)
- `src/dashboard/app.py` - FastAPI 应用 (需要扩展)
- `src/main.py` - 主入口 (需要扩展)

---

## Test Cases

### Test File: `tests/test_core/test_error_handler.py`

```python
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime

from src.core.error_handler import ErrorHandler, setup_error_handler
from src.core.alerting import AlertManager
from src.exceptions import NetworkError, TradingError, ValidationError


class TestErrorHandler:
    """测试错误处理器"""

    @pytest.fixture
    def error_handler(self):
        """创建错误处理器实例"""
        mock_alert_manager = MagicMock(spec=AlertManager)
        return ErrorHandler(
            alert_manager=mock_alert_manager,
            max_retries=3,
            retry_delay=0.1
        )

    def test_handle_exception_business_error(self, error_handler):
        """测试处理业务异常"""
        exception = TradingError("Test trading error")
        error_handler.handle_exception(exception, {"task": "test"})

        assert error_handler._error_counts.get("TradingError") == 1

    def test_handle_exception_unexpected_error(self, error_handler):
        """测试处理未预期异常"""
        exception = RuntimeError("Unexpected error")
        error_handler.handle_exception(exception, {"task": "test"})

        assert error_handler._error_counts.get("RuntimeError") == 1

    def test_handle_exception_triggers_alert(self, error_handler):
        """测试异常触发告警"""
        exception = TradingError("Test error")
        error_handler.handle_exception(exception, {"task": "test"})

        error_handler.alert_manager.check_and_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_wrapper_success(self, error_handler):
        """测试任务包装器成功执行"""
        @error_handler.task_wrapper("test_task")
        async def successful_task():
            return "success"

        result = await successful_task()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_task_wrapper_retry_on_network_error(self, error_handler):
        """测试网络错误时重试"""
        call_count = 0

        @error_handler.task_wrapper("test_task", retry_exceptions=(NetworkError,))
        async def failing_task():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Network failed")
            return "success"

        result = await failing_task()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_task_wrapper_max_retries_exceeded(self, error_handler):
        """测试超过最大重试次数"""
        @error_handler.task_wrapper("test_task", retry_exceptions=(NetworkError,))
        async def always_failing_task():
            raise NetworkError("Always fails")

        with pytest.raises(NetworkError):
            await always_failing_task()

    def test_get_error_stats(self, error_handler):
        """测试获取错误统计"""
        error_handler.handle_exception(RuntimeError("Error 1"), {})
        error_handler.handle_exception(RuntimeError("Error 2"), {})

        stats = error_handler.get_error_stats()
        assert stats["error_counts"]["RuntimeError"] == 2
        assert "RuntimeError" in stats["last_errors"]

    def test_reset_counts(self, error_handler):
        """测试重置错误计数"""
        error_handler.handle_exception(RuntimeError("Error"), {})
        error_handler.reset_counts()

        assert len(error_handler._error_counts) == 0
        assert len(error_handler._last_errors) == 0


class TestSetupErrorHandler:
    """测试错误处理器设置"""

    def test_setup_creates_global_handler(self):
        """测试设置创建全局处理器"""
        handler = setup_error_handler()

        assert handler is not None
        assert isinstance(handler, ErrorHandler)
```

### Test File: `tests/test_core/test_alerting.py`

```python
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import json

from src.core.alerting import (
    Alert, AlertManager, AlertChannel,
    LogAlertChannel, WebhookAlertChannel
)
from src.exceptions import TradingError, NetworkError


class TestAlert:
    """测试告警数据"""

    def test_to_dict(self):
        """测试转换为字典"""
        alert = Alert(
            level="ERROR",
            message="Test alert",
            source="test",
            context={"key": "value"}
        )

        data = alert.to_dict()
        assert data["level"] == "ERROR"
        assert data["message"] == "Test alert"
        assert data["source"] == "test"
        assert data["context"]["key"] == "value"

    def test_default_values(self):
        """测试默认值"""
        alert = Alert(level="INFO", message="Test", source="test")

        assert alert.count == 1
        assert isinstance(alert.timestamp, datetime)
        assert alert.context == {}


class TestLogAlertChannel:
    """测试日志告警渠道"""

    @pytest.fixture
    def channel(self, tmp_path):
        """创建日志告警渠道实例"""
        log_file = str(tmp_path / "errors.log")
        return LogAlertChannel(log_file)

    @pytest.mark.asyncio
    async def test_send_alert(self, channel, tmp_path):
        """测试发送告警"""
        alert = Alert(
            level="ERROR",
            message="Test error",
            source="test"
        )

        success = await channel.send(alert)
        assert success is True

        # 验证文件内容
        with open(str(tmp_path / "errors.log")) as f:
            content = f.read()
            assert "Test error" in content


class TestWebhookAlertChannel:
    """测试 Webhook 告警渠道"""

    @pytest.fixture
    def channel(self):
        """创建 Webhook 告警渠道实例"""
        return WebhookAlertChannel("https://example.com/webhook")

    @pytest.mark.asyncio
    async def test_send_alert_success(self, channel):
        """测试发送告警成功"""
        alert = Alert(level="ERROR", message="Test", source="test")

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response

            success = await channel.send(alert)
            assert success is True


class TestAlertManager:
    """测试告警管理器"""

    @pytest.fixture
    def alert_manager(self):
        """创建告警管理器实例"""
        mock_channel = MagicMock(spec=AlertChannel)
        mock_channel.send = AsyncMock(return_value=True)

        return AlertManager(
            channels=[mock_channel],
            min_level="WARNING",
            throttle_seconds=60,
            consecutive_failure_threshold=3
        )

    def test_determine_level_business_error(self, alert_manager):
        """测试业务异常级别"""
        level = alert_manager._determine_level(TradingError("Test"), {})
        assert level == "WARNING"

    def test_determine_level_network_error(self, alert_manager):
        """测试网络异常级别"""
        level = alert_manager._determine_level(NetworkError("Test"), {})
        assert level == "ERROR"

    def test_determine_level_unexpected_error(self, alert_manager):
        """测试未预期异常级别"""
        level = alert_manager._determine_level(RuntimeError("Test"), {})
        assert level == "CRITICAL"

    def test_check_and_alert_below_threshold(self, alert_manager):
        """测试低于阈值的告警"""
        exception = TradingError("Test")  # WARNING 级别
        alert_manager.min_level = "ERROR"  # 设置更高阈值

        alert_manager.check_and_alert(exception, {"source": "test"})

        # 不应该发送告警
        assert len(alert_manager._alert_history) == 0

    def test_check_and_alert_throttle(self, alert_manager):
        """测试告警节流"""
        exception = TradingError("Test")

        # 第一次告警
        alert_manager.check_and_alert(exception, {"source": "test"})
        assert len(alert_manager._alert_history) == 1

        # 立即第二次告警 - 应该被节流
        alert_manager.check_and_alert(exception, {"source": "test"})
        assert len(alert_manager._alert_history) == 1

    def test_record_failure(self, alert_manager):
        """测试记录失败"""
        alert_manager.record_failure("test_source")
        assert alert_manager._consecutive_failures["test_source"] == 1

    def test_consecutive_failures_trigger_alert(self, alert_manager):
        """测试连续失败触发告警"""
        for _ in range(3):
            alert_manager.record_failure("test_source")

        assert alert_manager._consecutive_failures["test_source"] >= 3

    def test_reset_failures(self, alert_manager):
        """测试重置失败计数"""
        alert_manager.record_failure("test_source")
        alert_manager.reset_failures("test_source")

        assert "test_source" not in alert_manager._consecutive_failures
```

### Test File: `tests/test_api/test_error_middleware.py`

```python
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.dashboard.middleware.error_middleware import ErrorMiddleware, setup_exception_handlers
from src.exceptions import ValidationError, TradingError, NetworkError


class TestErrorMiddleware:
    """测试 API 错误中间件"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = FastAPI()
        app.add_middleware(ErrorMiddleware)
        setup_exception_handlers(app)

        @app.get("/test-validation")
        async def test_validation():
            raise ValidationError("Invalid input")

        @app.get("/test-network")
        async def test_network():
            raise NetworkError("Network failed")

        @app.get("/test-unexpected")
        async def test_unexpected():
            raise RuntimeError("Unexpected error")

        @app.get("/test-success")
        async def test_success():
            return {"success": True}

        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)

    def test_success_response(self, client):
        """测试成功响应"""
        response = client.get("/test-success")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_validation_error(self, client):
        """测试验证错误"""
        response = client.get("/test-validation")
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_network_error(self, client):
        """测试网络错误"""
        response = client.get("/test-network")
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "NETWORK_ERROR"

    def test_unexpected_error(self, client):
        """测试未预期错误"""
        response = client.get("/test-unexpected")
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "INTERNAL_ERROR"
        # 不应该暴露内部错误详情
        assert "Unexpected error" not in data["error"]["message"]

    def test_error_response_format(self, client):
        """测试错误响应格式"""
        response = client.get("/test-validation")
        data = response.json()

        assert "success" in data
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
```

---

## Implementation Notes

1. **全局异常处理**: 使用 `sys.excepthook` 捕获未处理异常，使用 `asyncio` 事件循环的 `set_exception_handler` 捕获异步异常
2. **任务错误隔离**: 每个调度任务独立包装，单个任务失败不影响其他任务
3. **错误重试**: 对网络类错误自动重试，使用指数退避策略
4. **告警节流**: 相同告警在节流时间内只发送一次，避免告警风暴
5. **统一 API 响应**: 所有 API 错误返回统一格式 `{success: false, error: {code, message}}`
6. **专用错误日志**: 错误写入专用 `logs/errors.log` 文件，便于追踪和分析
7. **日志标记**: 使用特定 emoji (如 CRITICAL 级别) 标记错误日志，便于识别

---

## Definition of Done

- [ ] `src/core/error_handler.py` 实现完成
- [ ] `src/core/alerting.py` 实现完成
- [ ] `src/dashboard/middleware/error_middleware.py` 实现完成
- [ ] `src/core/scheduler.py` 错误处理扩展完成
- [ ] `src/utils/logger.py` 错误日志 handler 添加完成
- [ ] `src/main.py` 全局错误处理集成完成
- [ ] `tests/test_core/test_error_handler.py` 测试通过
- [ ] `tests/test_core/test_alerting.py` 测试通过
- [ ] `tests/test_api/test_error_middleware.py` 测试通过
- [ ] 全局异常处理正常
- [ ] 任务级错误隔离正常
- [ ] 告警机制正常
- [ ] API 错误响应格式统一
- [ ] 代码通过 `pytest`、`mypy src/` 和 `ruff check .`
- [ ] 代码覆盖率 >= 90%

---

## Next Story

完成后继续: **Story 8.6: 运行脚本与进程管理** - 创建便捷的运行脚本和进程管理工具
