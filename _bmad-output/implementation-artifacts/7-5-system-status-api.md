# Story 7.5: 系统状态 API

Status: review

## Story

As a **用户**,
I want **通过 API 获取系统运行状态**,
So that **Dashboard 能够监控系统能否正常工作**.

## Acceptance Criteria

**Given** 统计 API 已实现 (Story 7.4)
**When** 扩展 `src/dashboard/routes/statistics.py`
**Then** 实现状态端点:

- `GET /api/statistics/status` - 获取系统状态
- 返回内容:
  ```json
  {
    "success": true,
    "data": {
      "trading_enabled": true,
      "mode": "PAPER",
      "current_capital": 180.50,
      "daily_pnl": -5.50,
      "open_positions": 2,
      "consecutive_losses": 1,
      "reduced_mode": false,
      "last_market_fetch": "2026-02-15T10:30:00Z",
      "uptime_hours": 72.5
    }
  }
  ```

**And** 添加配置查看端点:

- `GET /api/statistics/settings` - 获取当前配置 (脱敏)
- 返回配置但隐藏敏感信息 (API Key, 私钥)

**And** 使用统一响应格式

## Tasks / Subtasks

- [x] Task 1: 定义系统状态响应模型 (AC: 1)
  - [x] 1.1 在 `src/models/` 创建 `system_status.py`
  - [x] 1.2 定义 `SystemStatus` 模型 (系统运行状态)
  - [x] 1.3 定义 `SanitizedSettings` 模型 (脱敏配置)
  - [x] 1.4 更新 `src/models/__init__.py` 导出新模型

- [x] Task 2: 实现系统状态 API 端点 (AC: 1)
  - [x] 2.1 在 `src/dashboard/routes/statistics.py` 添加 `GET /api/statistics/status` 路由
  - [x] 2.2 从 ThreadSafeState 获取运行状态 (trading_enabled, reduced_mode, etc.)
  - [x] 2.3 从 system_state 表获取 last_market_fetch 时间
  - [x] 2.4 计算系统运行时间 (uptime_hours)
  - [x] 2.5 组合数据返回 SystemStatus 响应

- [x] Task 3: 实现配置查看 API 端点 (AC: 2)
  - [x] 3.1 添加 `GET /api/statistics/settings` 路由
  - [x] 3.2 从 settings 读取当前配置
  - [x] 3.3 实现敏感信息脱敏 (API Key, 私钥, 钱包地址)
  - [x] 3.4 返回 SanitizedSettings 响应

- [x] Task 4: 编写单元测试 (AC: All)
  - [x] 4.1 创建 `tests/test_dashboard/test_routes/test_system_status.py`
  - [x] 4.2 测试 `GET /api/statistics/status` 返回 200
  - [x] 4.3 测试 `GET /api/statistics/status` 响应格式正确
  - [x] 4.4 测试 `GET /api/statistics/status` 包含所有必需字段
  - [x] 4.5 测试 `GET /api/statistics/settings` 返回 200
  - [x] 4.6 测试 `GET /api/statistics/settings` 敏感信息已脱敏
  - [x] 4.7 测试 API Key 只显示前4位
  - [x] 4.8 测试私钥完全隐藏

- [x] Task 5: 代码质量检查 (AC: All)
  - [x] 5.1 运行 `mypy src/dashboard/routes/statistics.py` 无错误
  - [x] 5.2 运行 `mypy src/models/system_status.py` 无错误
  - [x] 5.3 运行 `black --check` 通过
  - [x] 5.4 运行 `isort --check` 通过
  - [x] 5.5 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md, epics.md]

**API 端点规范:**

| 端点 | 方法 | 描述 | 响应类型 |
|------|------|------|----------|
| `/api/statistics/status` | GET | 获取系统状态 | `ApiResponse[SystemStatus]` |
| `/api/statistics/settings` | GET | 获取脱敏配置 | `ApiResponse[SanitizedSettings]` |

**响应格式规范 [Source: architecture.md#API Response Format]:**

```json
// 系统状态响应
{
  "success": true,
  "data": {
    "trading_enabled": true,
    "mode": "PAPER",
    "current_capital": 180.50,
    "daily_pnl": -5.50,
    "open_positions": 2,
    "consecutive_losses": 1,
    "reduced_mode": false,
    "last_market_fetch": "2026-02-15T10:30:00Z",
    "uptime_hours": 72.5
  }
}

// 脱敏配置响应
{
  "success": true,
  "data": {
    "trading_mode": "PAPER",
    "initial_capital": 200.00,
    "trade_unit": 10.0,
    "max_single_ratio": 0.20,
    "min_confidence": 0.75,
    "min_edge": 0.10,
    "daily_loss_limit": 0.30,
    "max_open_markets": 3,
    "llm_model": "glm-4",
    "llm_api_base": "https://open.bigmodel.cn/api/paas/v4",
    "llm_api_key": "sk-x****xxxx",  // 只显示前4位
    "polymarket_pk": "[REDACTED]",   // 完全隐藏
    "proxy_wallet": "0x1234...5678"  // 前6后4位
  }
}
```

### 已有组件 (必须复用)

**ThreadSafeState** [Source: src/core/state.py]
```python
class StateSnapshot(BaseModel):
    current_capital: float
    daily_pnl: float = 0.0
    consecutive_losses: int = 0
    open_positions_count: int = 0
    trading_enabled: bool = True
    reduced_mode: bool = False
    updated_at: datetime | None = None

class ThreadSafeState:
    async def get_state(self) -> StateSnapshot: ...
    # 返回: current_capital, daily_pnl, consecutive_losses, open_positions_count, trading_enabled, reduced_mode
```

**Settings** [Source: src/config.py]
```python
class Settings(BaseSettings):
    # LLM Configuration
    llm_api_base: str = "https://open.bigmodel.cn/api/paas/v4"
    llm_api_key: str = ""
    llm_model: str = "glm-4"

    # Polymarket Configuration
    polymarket_pk: str = ""
    proxy_wallet: str = ""
    trader_address: str = ""

    # Trading Parameters
    initial_capital: float = 200.0
    trade_unit: float = 10.0
    trading_mode: str = "PAPER"

    # Risk Control
    max_single_ratio: float = 0.20
    min_confidence: float = 0.75
    min_edge: float = 0.10
    daily_loss_limit: float = 0.30
    max_open_markets: int = 3
```

**API 响应模型** [Source: src/models/api_response.py]
```python
class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None
    error: ErrorDetail | None
```

**system_state 表** [Source: src/storage/database.py]
```sql
CREATE TABLE system_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 新增数据模型

**src/models/system_status.py:**

```python
"""System status API response models.

This module defines Pydantic models for system status API responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer


class SystemStatus(BaseModel):
    """System running status for monitoring.

    Contains real-time system status for dashboard monitoring.

    Attributes:
        trading_enabled: Whether trading is currently enabled
        mode: Current trading mode (PAPER/LIVE)
        current_capital: Current capital in USD
        daily_pnl: Daily profit/loss
        open_positions: Number of open positions
        consecutive_losses: Consecutive losing trades count
        reduced_mode: Whether system is in reduced position mode
        last_market_fetch: Timestamp of last market data fetch
        uptime_hours: System uptime in hours
    """

    trading_enabled: bool = Field(..., description="Trading enabled status")
    mode: str = Field(..., description="Trading mode (PAPER/LIVE)")
    current_capital: float = Field(..., description="Current capital (USD)")
    daily_pnl: float = Field(..., description="Daily P&L (USD)")
    open_positions: int = Field(..., description="Open positions count")
    consecutive_losses: int = Field(..., description="Consecutive losses")
    reduced_mode: bool = Field(..., description="Reduced mode active")
    last_market_fetch: datetime | None = Field(
        None, description="Last market fetch timestamp"
    )
    uptime_hours: float | None = Field(None, description="System uptime (hours)")

    @field_serializer("last_market_fetch")
    def serialize_datetime(self, dt: datetime | None, _info: Any) -> str | None:
        """Serialize datetime to ISO 8601 format."""
        if dt is None:
            return None
        return dt.isoformat()


class SanitizedSettings(BaseModel):
    """Sanitized settings for API response.

    Contains configuration values with sensitive data masked.

    Attributes:
        trading_mode: Current trading mode
        initial_capital: Initial capital amount
        trade_unit: Base trade unit amount
        max_single_ratio: Maximum single position ratio
        min_confidence: Minimum LLM confidence threshold
        min_edge: Minimum edge requirement
        daily_loss_limit: Daily loss limit percentage
        max_open_markets: Maximum concurrent markets
        llm_model: LLM model name
        llm_api_base: LLM API base URL
        llm_api_key: Masked API key (first 4 chars only)
        polymarket_pk: Masked private key (fully hidden)
        proxy_wallet: Masked wallet address (first 6 + last 4)
    """

    trading_mode: str = Field(..., description="Trading mode (PAPER/LIVE)")
    initial_capital: float = Field(..., description="Initial capital (USD)")
    trade_unit: float = Field(..., description="Trade unit amount")
    max_single_ratio: float = Field(..., description="Max single position ratio")
    min_confidence: float = Field(..., description="Min confidence threshold")
    min_edge: float = Field(..., description="Min edge requirement")
    daily_loss_limit: float = Field(..., description="Daily loss limit")
    max_open_markets: int = Field(..., description="Max open markets")
    llm_model: str = Field(..., description="LLM model name")
    llm_api_base: str = Field(..., description="LLM API base URL")
    llm_api_key: str = Field(..., description="Masked LLM API key")
    polymarket_pk: str = Field(..., description="Masked private key")
    proxy_wallet: str = Field(..., description="Masked wallet address")


__all__ = ["SystemStatus", "SanitizedSettings"]
```

### 实现模板

**更新 src/dashboard/routes/statistics.py:**

```python
# 在文件末尾添加以下内容

import time
from src.models.system_status import SystemStatus, SanitizedSettings
from src.storage.database import get_connection

# 记录应用启动时间
_app_start_time: float = time.time()


async def get_last_market_fetch() -> datetime | None:
    """Get last market fetch timestamp from database.

    Returns:
        datetime | None: Last market fetch timestamp or None
    """
    try:
        async with get_connection() as conn:
            cursor = await conn.execute(
                "SELECT value, updated_at FROM system_state WHERE key = ?",
                ("last_market_fetch",),
            )
            row = await cursor.fetchone()
            if row and row[1]:
                return datetime.fromisoformat(row[1])
    except Exception as e:
        logger.warning(f"Failed to get last market fetch: {e}")
    return None


@router.get("/status", response_model=ApiResponse[SystemStatus])
async def get_system_status(
    state: ThreadSafeState = Depends(get_state),
) -> ApiResponse[SystemStatus]:
    """Get system running status.

    Returns real-time system status for monitoring including
    trading state, capital, and performance metrics.

    Args:
        state: ThreadSafeState dependency

    Returns:
        System status data
    """
    logger.info("📊 Getting system status")

    # Get current state
    state_snapshot = await state.get_state()

    # Get last market fetch time
    last_market_fetch = await get_last_market_fetch()

    # Calculate uptime
    uptime_hours = (time.time() - _app_start_time) / 3600

    status = SystemStatus(
        trading_enabled=state_snapshot.trading_enabled,
        mode=settings.trading_mode.upper(),
        current_capital=state_snapshot.current_capital,
        daily_pnl=state_snapshot.daily_pnl,
        open_positions=state_snapshot.open_positions_count,
        consecutive_losses=state_snapshot.consecutive_losses,
        reduced_mode=state_snapshot.reduced_mode,
        last_market_fetch=last_market_fetch,
        uptime_hours=round(uptime_hours, 2),
    )

    return ApiResponse(success=True, data=status, error=None)


def mask_api_key(key: str) -> str:
    """Mask API key, showing only first 4 characters.

    Args:
        key: API key to mask

    Returns:
        Masked API key (e.g., "sk-x****xxxx")

    Example:
        >>> mask_api_key("sk-1234567890abcdef")
        'sk-1****'
    """
    if not key:
        return "[NOT_SET]"
    if len(key) <= 4:
        return key[:4] + "****"
    return key[:4] + "****"


def mask_private_key() -> str:
    """Return fully masked private key indicator.

    Returns:
        Always returns "[REDACTED]"
    """
    return "[REDACTED]"


def mask_wallet_address(address: str) -> str:
    """Mask wallet address, showing first 6 and last 4 characters.

    Args:
        address: Wallet address to mask

    Returns:
        Masked address (e.g., "0x1234...5678")

    Example:
        >>> mask_wallet_address("0x1234567890abcdef1234")
        '0x1234...1234'
    """
    if not address:
        return "[NOT_SET]"
    if len(address) <= 10:
        return address[:6] + "..." if len(address) >= 6 else address + "..."
    return f"{address[:6]}...{address[-4:]}"


@router.get("/settings", response_model=ApiResponse[SanitizedSettings])
async def get_settings_sanitized() -> ApiResponse[SanitizedSettings]:
    """Get sanitized system settings.

    Returns configuration values with sensitive data masked
    for secure display in the dashboard.

    Returns:
        Sanitized settings data
    """
    logger.info("📊 Getting sanitized settings")

    sanitized = SanitizedSettings(
        trading_mode=settings.trading_mode.upper(),
        initial_capital=settings.initial_capital,
        trade_unit=settings.trade_unit,
        max_single_ratio=settings.max_single_ratio,
        min_confidence=settings.min_confidence,
        min_edge=settings.min_edge,
        daily_loss_limit=settings.daily_loss_limit,
        max_open_markets=settings.max_open_markets,
        llm_model=settings.llm_model,
        llm_api_base=settings.llm_api_base,
        llm_api_key=mask_api_key(settings.llm_api_key),
        polymarket_pk=mask_private_key(),
        proxy_wallet=mask_wallet_address(settings.proxy_wallet),
    )

    return ApiResponse(success=True, data=sanitized, error=None)
```

### 项目结构 [Source: architecture.md#Project Structure]

**新增/修改文件:**
```
src/
├── models/
│   ├── system_status.py        # 新增: 系统状态响应模型
│   └── __init__.py             # 更新: 导出新模型
└── dashboard/
    └── routes/
        └── statistics.py       # 更新: 添加 /status 和 /settings 端点

tests/
└── test_dashboard/
    └── test_routes/
        └── test_system_status.py  # 新增: 系统状态路由测试
```

### 依赖关系

**本故事依赖:**
- Story 7.1: FastAPI 应用初始化 (已完成 - app.py, dependencies.py, api_response.py)
- Story 7.2: 市场数据 API (已完成 - 参考 markets.py 实现模式)
- Story 7.3: 持仓与交易 API (已完成 - 参考实现模式)
- Story 7.4: 预测与统计 API (已完成 - 在 statistics.py 基础上扩展)
- Epic 4: 风险控制与熔断系统 (已完成 - ThreadSafeState)

**后续故事依赖本故事:**
- Story 7.6: 前端 API 集成 (使用本故事的端点)

### 前一个故事学习 [Source: 7-4-prediction-and-statistics-api.md]

**从 Story 7.4 学到的模式:**

1. **响应模型分离** - API 响应模型与数据库模型分离
2. **依赖注入** - 使用 FastAPI Depends 注入 Repository 和 State
3. **统一错误处理** - 使用 HTTPException 返回统一错误格式
4. **日志标准化** - 使用 emoji 标记日志 (📊 统计/状态)
5. **类型注解** - 使用 Annotated 类型提供 OpenAPI 文档
6. **单例获取** - 使用 `get_state_manager()` 获取 ThreadSafeState 单例

### 日志脱敏规则 [Source: architecture.md#Authentication & Security]

| 信息类型 | 脱敏规则 | 示例 |
|----------|----------|------|
| API Key | 只显示前4位 | `sk-xxxx****xxxx` |
| 私钥 | 完全隐藏 | `[REDACTED]` |
| 钱包地址 | 前6后4位 | `0x1234...5678` |

### 实现注意事项

**关键点:**

1. **状态数据来源** - trading_enabled, reduced_mode 等来自 ThreadSafeState
2. **最后市场获取时间** - 从 system_state 表读取 last_market_fetch
3. **系统运行时间** - 使用模块级变量 `_app_start_time` 计算运行时长
4. **配置脱敏** - 敏感信息必须按要求规则脱敏
5. **路由顺序** - `/status` 和 `/settings` 添加在 statistics.py 末尾

**性能考虑:**

- NFR4 要求响应时间 < 2 秒
- 状态端点需要快速响应，避免复杂查询
- 配置端点直接从 settings 读取，无需数据库查询

**日志级别:**

| 级别 | 场景 | Emoji |
|------|------|-------|
| INFO | 状态查询 | 📊 |
| INFO | 配置查询 | 📊 |
| WARNING | 读取 last_market_fetch 失败 | 📊 |

### 测试策略

```python
# tests/test_dashboard/test_routes/test_system_status.py
"""Tests for system status API routes."""

import pytest
from fastapi.testclient import TestClient

from src.dashboard.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestGetSystemStatus:
    """测试系统状态端点."""

    def test_get_status_returns_200(self, client: TestClient) -> None:
        """测试状态返回 200."""
        response = client.get("/api/status")
        assert response.status_code == 200

    def test_get_status_format(self, client: TestClient) -> None:
        """测试响应格式."""
        response = client.get("/api/status")
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert data["success"] is True

    def test_get_status_required_fields(self, client: TestClient) -> None:
        """测试必需字段存在."""
        response = client.get("/api/status")
        data = response.json()
        assert "trading_enabled" in data["data"]
        assert "mode" in data["data"]
        assert "current_capital" in data["data"]
        assert "daily_pnl" in data["data"]
        assert "open_positions" in data["data"]
        assert "consecutive_losses" in data["data"]
        assert "reduced_mode" in data["data"]


class TestGetSettings:
    """测试配置端点."""

    def test_get_settings_returns_200(self, client: TestClient) -> None:
        """测试配置返回 200."""
        response = client.get("/api/settings")
        assert response.status_code == 200

    def test_get_settings_format(self, client: TestClient) -> None:
        """测试响应格式."""
        response = client.get("/api/settings")
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert data["success"] is True

    def test_get_settings_api_key_masked(self, client: TestClient) -> None:
        """测试 API Key 已脱敏."""
        response = client.get("/api/settings")
        data = response.json()
        api_key = data["data"]["llm_api_key"]
        # Should show first 4 chars + ****
        assert "****" in api_key or api_key == "[NOT_SET]"

    def test_get_settings_private_key_fully_hidden(self, client: TestClient) -> None:
        """测试私钥完全隐藏."""
        response = client.get("/api/settings")
        data = response.json()
        pk = data["data"]["polymarket_pk"]
        assert pk == "[REDACTED]"

    def test_get_settings_wallet_masked(self, client: TestClient) -> None:
        """测试钱包地址已脱敏."""
        response = client.get("/api/settings")
        data = response.json()
        wallet = data["data"]["proxy_wallet"]
        # Should be masked or [NOT_SET]
        assert "..." in wallet or wallet == "[NOT_SET]"
```

### 运行命令

```bash
# 启动开发服务器
uvicorn src.dashboard.app:app --reload --host 0.0.0.0 --port 8000

# 测试系统状态
curl http://localhost:8000/api/statistics/status

# 测试配置查看
curl http://localhost:8000/api/statistics/settings

# 查看 API 文档
open http://localhost:8000/docs

# 运行测试
pytest tests/test_dashboard/test_routes/test_system_status.py -v
```

### References

- [Source: architecture.md#API Response Format] - 统一响应格式规范
- [Source: architecture.md#Authentication & Security] - 日志脱敏规则
- [Source: epics.md#Story 7.5] - 原始 Story 定义
- [Source: src/core/state.py] - ThreadSafeState 实现
- [Source: src/config.py] - Settings 配置
- [Source: src/models/api_response.py] - API 响应模型
- [Source: src/storage/database.py] - system_state 表结构
- [Source: 7-4-prediction-and-statistics-api.md] - 前一个故事实现参考

## Dev Agent Record

### Agent Model Used

GLM-5 (Claude Opus 4.6 via Claude Code)

### Debug Log References

无

### Completion Notes List

1. **Task 1 完成**: 创建了 `src/models/system_status.py`，定义了 `SystemStatus` 和 `SanitizedSettings` 两个 Pydantic 模型，并更新了 `src/models/__init__.py` 导出新模型。

2. **Task 2 完成**: 在 `src/dashboard/routes/statistics.py` 中添加了 `GET /api/statistics/status` 端点:
   - 从 ThreadSafeState 获取运行状态 (trading_enabled, reduced_mode, capital 等)
   - 实现了 `get_last_market_fetch()` 从 system_state 表读取最后市场获取时间
   - 使用模块级变量 `_app_start_time` 计算系统运行时间

3. **Task 3 完成**: 添加了 `GET /api/statistics/settings` 端点:
   - 实现了 `mask_api_key()` - 只显示前4位
   - 实现了 `mask_private_key()` - 完全隐藏为 [REDACTED]
   - 实现了 `mask_wallet_address()` - 前6后4位格式

4. **Task 4 完成**: 创建了 `tests/test_dashboard/test_routes/test_system_status.py`，包含 22 个测试用例:
   - TestGetSystemStatus (7 个测试)
   - TestGetSettings (7 个测试)
   - TestMaskingFunctions (8 个测试)

5. **Task 5 完成**: 所有代码质量检查通过:
   - mypy 类型检查通过
   - black 格式检查通过
   - isort 导入检查通过
   - 完整测试套件 1263 个测试全部通过

### File List

**新增文件:**
- src/models/system_status.py
- tests/test_dashboard/test_routes/test_system_status.py

**修改文件:**
- src/models/__init__.py (添加导出)
- src/dashboard/routes/statistics.py (添加 /status 和 /settings 端点)

### Change Log

- 2026-02-17: Story 7.5 实现完成，所有 AC 满足，22 个新测试通过，完整测试套件 1263 测试通过
