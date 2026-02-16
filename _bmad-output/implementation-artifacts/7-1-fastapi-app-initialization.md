# Story 7.1: FastAPI 应用初始化

Status: review

## Story

As a **开发者**,
I want **创建 FastAPI 应用基础结构**,
So that **Dashboard 有可用的后端 API 服务**.

## Acceptance Criteria

**Given** Epic 1-6 已完成
**When** 实现 `src/dashboard/app.py`
**Then** 创建 FastAPI 应用实例:
- 配置 CORS 允许前端访问
- 配置响应格式统一 (AR10)
- 添加健康检查端点 `GET /health`

**And** 创建路由目录结构:
```
src/dashboard/
├── __init__.py
├── app.py
├── dependencies.py
└── routes/
    ├── __init__.py
    ├── markets.py
    ├── trades.py
    ├── positions.py
    ├── predictions.py
    └── statistics.py
```

**And** 实现依赖注入 `dependencies.py`:
- `get_db()` - 数据库连接
- `get_state()` - 系统状态

**And** 统一响应格式:
```json
// 成功
{"success": true, "data": {...}}
// 错误
{"success": false, "error": {"code": "XXX", "message": "..."}}
// 列表
{"success": true, "data": [...], "meta": {"total": 100, "page": 1, "per_page": 20}}
```

## Tasks / Subtasks

- [x] Task 1: 创建目录结构 (AC: All)
  - [x] 1.1 创建 `src/dashboard/routes/` 目录
  - [x] 1.2 创建 `src/dashboard/routes/__init__.py`
  - [x] 1.3 创建 `src/dashboard/__init__.py` (如不存在)
  - [x] 1.4 创建空路由文件占位符

- [x] Task 2: 定义响应模型 (AC: 4)
  - [x] 2.1 在 `src/models/` 创建 `api_response.py`
  - [x] 2.2 定义 `ApiResponse[T]` 泛型模型
  - [x] 2.3 定义 `ErrorResponse` 模型
  - [x] 2.4 定义 `PaginatedResponse[T]` 泛型模型
  - [x] 2.5 定义 `ErrorDetail` 模型 (code, message)
  - [x] 2.6 更新 `__all__` 导出

- [x] Task 3: 实现依赖注入 (AC: 3)
  - [x] 3.1 创建 `src/dashboard/dependencies.py`
  - [x] 3.2 实现 `get_db()` 依赖 (返回数据库连接)
  - [x] 3.3 实现 `get_state()` 依赖 (返回 ThreadSafeState 实例)
  - [x] 3.4 添加类型注解和文档

- [x] Task 4: 创建 FastAPI 应用 (AC: 1)
  - [x] 4.1 创建 `src/dashboard/app.py`
  - [x] 4.2 配置 CORS 中间件 (允许 localhost:5173, localhost:3000)
  - [x] 4.3 配置应用元数据 (title, description, version)
  - [x] 4.4 添加 `/health` 健康检查端点
  - [x] 4.5 添加根路由 `/` 返回 API 信息
  - [x] 4.6 添加响应模型自动包装

- [x] Task 5: 创建路由占位符 (AC: 2)
  - [x] 5.1 创建 `routes/markets.py` 带空路由器
  - [x] 5.2 创建 `routes/trades.py` 带空路由器
  - [x] 5.3 创建 `routes/positions.py` 带空路由器
  - [x] 5.4 创建 `routes/predictions.py` 带空路由器
  - [x] 5.5 创建 `routes/statistics.py` 带空路由器
  - [x] 5.6 在 app.py 注册所有路由器

- [x] Task 6: 添加异常处理器 (AC: 1, 4)
  - [x] 6.1 实现 `validation_exception_handler` 处理 RequestValidationError
  - [x] 6.2 实现 `bot_error_handler` 处理自定义异常 (BotError)
  - [x] 6.3 实现 `generic_exception_handler` 处理未预期异常
  - [x] 6.4 确保所有异常返回统一错误格式

- [x] Task 7: 编写单元测试 (AC: All)
  - [x] 7.1 创建 `tests/test_dashboard/__init__.py`
  - [x] 7.2 创建 `tests/test_dashboard/test_app.py`
  - [x] 7.3 测试 `/health` 端点返回正确响应
  - [x] 7.4 测试 CORS 配置正确
  - [x] 7.5 测试错误响应格式符合规范
  - [x] 7.6 测试依赖注入正常工作
  - [x] 7.7 使用 TestClient 进行集成测试

- [x] Task 8: 代码质量检查 (AC: All)
  - [x] 8.1 运行 `mypy src/dashboard/` 无错误
  - [x] 8.2 运行 `black --check` 通过
  - [x] 8.3 运行 `isort --check` 通过
  - [x] 8.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md, epics.md]

**FastAPI 配置:**

```python
# CORS 配置
ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Alternative dev port
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

# 应用元数据
APP_TITLE = "Polymarket Trader API"
APP_DESCRIPTION = "LLM 驱动的 Polymarket 自动交易系统 Dashboard API"
APP_VERSION = "1.0.0"
```

**响应格式规范 [Source: architecture.md#API Response Format]:**

```json
// 成功响应
{
  "success": true,
  "data": { ... }
}

// 错误响应
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid market ID"
  }
}

// 分页列表响应
{
  "success": true,
  "data": [...],
  "meta": {
    "total": 100,
    "page": 1,
    "per_page": 20
  }
}
```

### 已有组件 (必须复用)

**ThreadSafeState** [Source: src/core/state.py]
```python
class ThreadSafeState:
    """线程安全状态管理器."""
    def get_state(self) -> StateSnapshot: ...
    def update_capital(self, amount: float) -> None: ...
```

**Database** [Source: src/storage/database.py]
```python
async def get_connection() -> aiosqlite.Connection:
    """获取数据库连接."""
    ...

async def init_db() -> None:
    """初始化数据库表."""
    ...

async def close_db() -> None:
    """关闭数据库连接池."""
    ...
```

**异常体系** [Source: src/exceptions.py]
```python
class BotError(Exception):
    """基础异常."""

class ConfigurationError(BotError):
    """配置错误."""

class NetworkError(BotError):
    """网络错误."""

class TradingError(BotError):
    """交易错误."""

class ValidationError(BotError):
    """验证错误."""
```

### 新增数据模型

**src/models/api_response.py:**

```python
"""API 响应模型定义."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """错误详情.

    Attributes:
        code: 错误代码
        message: 错误消息
    """

    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应格式.

    Attributes:
        success: 是否成功
        data: 响应数据 (成功时)
        error: 错误详情 (失败时)
    """

    success: bool = Field(..., description="是否成功")
    data: T | None = Field(None, description="响应数据")
    error: ErrorDetail | None = Field(None, description="错误详情")


class PaginationMeta(BaseModel):
    """分页元数据.

    Attributes:
        total: 总记录数
        page: 当前页码
        per_page: 每页记录数
    """

    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    per_page: int = Field(..., description="每页记录数")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页列表响应.

    Attributes:
        success: 是否成功
        data: 数据列表
        meta: 分页元数据
    """

    success: bool = Field(default=True, description="是否成功")
    data: list[T] = Field(default_factory=list, description="数据列表")
    meta: PaginationMeta = Field(..., description="分页元数据")


# 错误代码常量
class ErrorCode:
    """错误代码常量."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    TRADING_ERROR = "TRADING_ERROR"


__all__ = [
    "ErrorDetail",
    "ApiResponse",
    "PaginationMeta",
    "PaginatedResponse",
    "ErrorCode",
]
```

### 实现模板

**src/dashboard/app.py:**

```python
"""FastAPI Dashboard Application.

This module provides the main FastAPI application for the Dashboard API.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.config import settings
from src.exceptions import BotError, ValidationError as BotValidationError
from src.models.api_response import ApiResponse, ErrorDetail, ErrorCode
from src.storage.database import init_db, close_db

logger = logging.getLogger(__name__)

# CORS 配置
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理.

    Args:
        app: FastAPI 应用实例
    """
    # 启动时初始化
    logger.info("🚀 Starting Dashboard API...")
    await init_db()
    logger.info("✅ Database initialized")

    yield

    # 关闭时清理
    logger.info("🛑 Shutting down Dashboard API...")
    await close_db()
    logger.info("✅ Cleanup complete")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例.

    Returns:
        配置好的 FastAPI 应用实例
    """
    app = FastAPI(
        title="Polymarket Trader API",
        description="LLM 驱动的 Polymarket 自动交易系统 Dashboard API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册异常处理器
    _register_exception_handlers(app)

    # 注册路由
    _register_routers(app)

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """注册异常处理器.

    Args:
        app: FastAPI 应用实例
    """

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """处理请求验证错误."""
        errors = exc.errors()
        messages = [e.get("msg", str(e)) for e in errors]
        return JSONResponse(
            status_code=422,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="; ".join(messages),
                ),
            ).model_dump(),
        )

    @app.exception_handler(BotError)
    async def bot_error_handler(request: Request, exc: BotError) -> JSONResponse:
        """处理自定义业务异常."""
        # 根据异常类型确定错误代码
        if isinstance(exc, BotValidationError):
            code = ErrorCode.VALIDATION_ERROR
        elif isinstance(exc, type(exc).__name__.startswith("Configuration")):
            code = ErrorCode.CONFIGURATION_ERROR
        elif isinstance(exc, type(exc).__name__.startswith("Network")):
            code = ErrorCode.NETWORK_ERROR
        else:
            code = ErrorCode.INTERNAL_ERROR

        return JSONResponse(
            status_code=400,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(code=code, message=str(exc)),
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """处理未预期的异常."""
        logger.exception(f"❌ Unexpected error: {exc}")
        return JSONResponse(
            status_code=500,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="An unexpected error occurred",
                ),
            ).model_dump(),
        )


def _register_routers(app: FastAPI) -> None:
    """注册路由器.

    Args:
        app: FastAPI 应用实例
    """
    from src.dashboard.routes import (
        markets,
        trades,
        positions,
        predictions,
        statistics,
    )

    app.include_router(markets.router, prefix="/api/markets", tags=["markets"])
    app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
    app.include_router(
        positions.router, prefix="/api/positions", tags=["positions"]
    )
    app.include_router(
        predictions.router, prefix="/api/predictions", tags=["predictions"]
    )
    app.include_router(
        statistics.router, prefix="/api/statistics", tags=["statistics"]
    )


# 创建应用实例
app = create_app()


@app.get("/", response_model=ApiResponse[dict])
async def root() -> ApiResponse[dict]:
    """API 根路由.

    Returns:
        API 信息
    """
    return ApiResponse(
        success=True,
        data={
            "name": "Polymarket Trader API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
        },
    )


@app.get("/health", response_model=ApiResponse[dict])
async def health_check() -> ApiResponse[dict]:
    """健康检查端点.

    Returns:
        健康状态
    """
    return ApiResponse(
        success=True,
        data={
            "status": "healthy",
            "service": "dashboard-api",
        },
    )
```

**src/dashboard/dependencies.py:**

```python
"""FastAPI 依赖注入.

This module provides dependency injection functions for FastAPI routes.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

import aiosqlite
from fastapi import Depends

from src.core.state import ThreadSafeState
from src.storage.database import get_connection

logger = logging.getLogger(__name__)

# 全局状态实例 (延迟初始化)
_state: ThreadSafeState | None = None


def get_state() -> ThreadSafeState:
    """获取系统状态管理器.

    Returns:
        ThreadSafeState 实例
    """
    global _state
    if _state is None:
        _state = ThreadSafeState()
    return _state


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """获取数据库连接.

    Yields:
        数据库连接

    Example:
        @router.get("/markets")
        async def list_markets(db: aiosqlite.Connection = Depends(get_db)):
            ...
    """
    async with get_connection() as conn:
        yield conn


__all__ = ["get_state", "get_db"]
```

**src/dashboard/routes/__init__.py:**

```python
"""Dashboard API 路由模块."""

from src.dashboard.routes import markets, trades, positions, predictions, statistics

__all__ = ["markets", "trades", "positions", "predictions", "statistics"]
```

**src/dashboard/routes/markets.py (占位符):**

```python
"""市场数据 API 路由."""

from fastapi import APIRouter

router = APIRouter()


# 后续 Story 7.2 实现具体端点

__all__ = ["router"]
```

### 项目结构 [Source: architecture.md#Project Structure]

**新增/修改文件:**
```
src/
├── models/
│   └── api_response.py           # 新增: API 响应模型
└── dashboard/
    ├── __init__.py               # 新增/更新
    ├── app.py                    # 新增: FastAPI 应用
    ├── dependencies.py           # 新增: 依赖注入
    └── routes/
        ├── __init__.py           # 新增
        ├── markets.py            # 新增: 市场路由 (占位符)
        ├── trades.py             # 新增: 交易路由 (占位符)
        ├── positions.py          # 新增: 持仓路由 (占位符)
        ├── predictions.py        # 新增: 预测路由 (占位符)
        └── statistics.py         # 新增: 统计路由 (占位符)

tests/
└── test_dashboard/
    ├── __init__.py               # 新增
    └── test_app.py               # 新增: 应用测试
```

### 依赖关系

**本故事依赖:**
- Epic 1: 项目基础设施 (已完成 - config.py, exceptions.py, database.py)
- Epic 4: 风险控制 (已完成 - ThreadSafeState)
- Epic 6: 预测追踪 (已完成 - 数据模型)

**后续故事依赖本故事:**
- Story 7.2: 市场数据 API (需要 app.py 和路由结构)
- Story 7.3: 持仓与交易 API
- Story 7.4: 预测与统计 API
- Story 7.5: 系统状态 API
- Story 7.6: 前端 API 集成

### 前一个故事学习 [Source: 6-5-performance-analysis-and-insights.md]

**从 Story 6.5 学到的模式:**

1. **数据类返回结果** - 使用 `@dataclass` 定义结构化返回类型
2. **依赖注入** - 所有 Repository 通过构造函数注入
3. **日志标准化** - 使用 emoji 标记日志 (🚀 启动, ✅ 成功, ❌ 错误)
4. **类型注解** - 使用 `TYPE_CHECKING` 避免循环导入
5. **`__all__` 导出** - 明确模块公共 API
6. **异步方法** - 所有数据库操作使用 async/await

### 实现注意事项

**关键点:**

1. **CORS 配置** - 必须允许前端开发服务器地址
2. **异常处理** - 所有异常必须返回统一格式
3. **生命周期管理** - 使用 lifespan 管理数据库连接
4. **路由占位符** - 先创建空路由器，后续 Story 实现具体端点

**错误代码映射:**

| 异常类型 | 错误代码 | HTTP 状态码 |
|----------|----------|-------------|
| RequestValidationError | VALIDATION_ERROR | 422 |
| BotValidationError | VALIDATION_ERROR | 400 |
| ConfigurationError | CONFIGURATION_ERROR | 500 |
| NetworkError | NETWORK_ERROR | 503 |
| TradingError | TRADING_ERROR | 400 |
| 其他 Exception | INTERNAL_ERROR | 500 |

**日志级别:**

| 级别 | 场景 | Emoji |
|------|------|-------|
| INFO | 启动、关闭 | 🚀 🛑 |
| INFO | 操作成功 | ✅ |
| WARNING | 警告 | ⚠️ |
| ERROR | 操作失败 | ❌ |

### 测试策略

```python
# tests/test_dashboard/test_app.py
"""Tests for FastAPI Dashboard Application."""

import pytest
from fastapi.testclient import TestClient

from src.dashboard.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """测试健康检查端点."""

    def test_health_check_returns_200(self, client: TestClient) -> None:
        """测试健康检查返回 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_returns_success(self, client: TestClient) -> None:
        """测试健康检查返回成功状态."""
        response = client.get("/health")
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"


class TestCORS:
    """测试 CORS 配置."""

    def test_cors_allows_localhost(self, client: TestClient) -> None:
        """测试 CORS 允许 localhost."""
        response = client.options(
            "/health",
            headers={"Origin": "http://localhost:5173"},
        )
        assert "access-control-allow-origin" in response.headers


class TestErrorResponse:
    """测试错误响应格式."""

    def test_validation_error_format(self, client: TestClient) -> None:
        """测试验证错误返回统一格式."""
        response = client.get("/api/markets/invalid")
        # 根据 Story 7.2 实现后调整
        assert "success" in response.json()
        assert "error" in response.json()
```

### 运行命令

```bash
# 启动开发服务器
uvicorn src.dashboard.app:app --reload --host 0.0.0.0 --port 8000

# 查看 API 文档
open http://localhost:8000/docs

# 运行测试
pytest tests/test_dashboard/ -v
```

### References

- [Source: architecture.md#API Response Format] - 统一响应格式规范
- [Source: architecture.md#Frontend Architecture] - 前端技术栈和 CORS 需求
- [Source: architecture.md#Error Handling Patterns] - 异常处理模式
- [Source: epics.md#Story 7.1] - 原始 Story 定义
- [Source: src/config.py] - 配置管理
- [Source: src/exceptions.py] - 异常定义
- [Source: src/storage/database.py] - 数据库操作
- [Source: src/core/state.py] - ThreadSafeState 实现
- [Source: 6-5-performance-analysis-and-insights.md] - 前一个故事实现参考

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (via GLM-5)

### Debug Log References

N/A

### Completion Notes List

1. 创建了 `src/models/api_response.py` 定义统一的 API 响应模型，包括 `ApiResponse[T]`, `PaginatedResponse[T]`, `ErrorDetail`, `PaginationMeta`, 和 `ErrorCode` 常量类。

2. 实现了 `src/dashboard/dependencies.py` 提供依赖注入函数 `get_db()` 和 `get_state()`。

3. 创建了 `src/dashboard/app.py` 作为主 FastAPI 应用，包含：
   - CORS 中间件配置（允许 localhost:5173, localhost:3000, 127.0.0.1:5173, 127.0.0.1:3000）
   - 应用元数据（title, description, version）
   - 生命周期管理（lifespan context manager）
   - 完整的异常处理器（处理 RequestValidationError, ValidationError, ConfigurationError, NetworkError, RateLimitError, TradingError, InsufficientFundsError, RiskLimitExceededError, DatabaseError, BotError, Exception）
   - 根路由 `/` 和健康检查端点 `/health`

4. 创建了路由占位符文件：
   - `src/dashboard/routes/markets.py`
   - `src/dashboard/routes/trades.py`
   - `src/dashboard/routes/positions.py`
   - `src/dashboard/routes/predictions.py`
   - `src/dashboard/routes/statistics.py`

5. 编写了完整的单元测试 `tests/test_dashboard/test_app.py`，包含 33 个测试用例覆盖：
   - 根端点测试
   - 健康检查端点测试
   - CORS 配置测试
   - 错误响应格式测试
   - 依赖注入测试
   - API 响应模型测试
   - 异常处理器测试
   - 路由注册测试
   - OpenAPI 文档测试

6. 所有代码质量检查通过：
   - mypy 类型检查通过
   - black 格式化通过
   - isort 导入排序通过
   - 完整测试套件通过（1124 个测试）

### File List

**新增文件:**
- `src/models/api_response.py`
- `src/dashboard/app.py`
- `src/dashboard/dependencies.py`
- `src/dashboard/routes/__init__.py`
- `src/dashboard/routes/markets.py`
- `src/dashboard/routes/trades.py`
- `src/dashboard/routes/positions.py`
- `src/dashboard/routes/predictions.py`
- `src/dashboard/routes/statistics.py`
- `tests/test_dashboard/__init__.py`
- `tests/test_dashboard/test_app.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

**修改文件:**
- `src/models/__init__.py` - 添加 api_response 模块导出
- `src/dashboard/__init__.py` - 添加 app, create_app, get_db, get_state 导出
