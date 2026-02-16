# Story 7.2: 市场数据 API

Status: done

## Story

As a **用户**,
I want **通过 API 获取市场列表和详情**,
So that **Dashboard 能够展示市场信息**.

## Acceptance Criteria

**Given** FastAPI 应用已初始化 (Story 7.1)
**When** 实现 `src/dashboard/routes/markets.py`
**Then** 实现以下端点:

- `GET /api/markets` - 获取市场列表 (分页、筛选)
- `GET /api/markets/{market_id}` - 获取单个市场详情
- `GET /api/markets?status=active` - 筛选活跃市场
- `GET /api/markets?category=politics` - 按类别筛选

**And** 响应包含:
- 市场基本信息 (id, title, description, category)
- 价格信息 (yes_price, no_price)
- 流动性、截止日期
- 结算状态 (如有)

**And** 响应时间 < 2 秒 (NFR4)
**And** 使用统一响应格式

## Tasks / Subtasks

- [ ] Task 1: 定义响应模型 (AC: 2)
  - [ ] 1.1 在 `src/models/` 创建 `market_response.py`
  - [ ] 1.2 定义 `MarketResponse` 模型 (用于单个市场详情)
  - [ ] 1.3 定义 `MarketListItem` 模型 (用于列表项，精简字段)
  - [ ] 1.4 定义 `MarketListQueryParams` 查询参数模型
  - [ ] 1.5 更新 `__all__` 导出

- [ ] Task 2: 实现市场列表端点 (AC: 1, 3, 4)
  - [ ] 2.1 实现 `GET /api/markets` 路由
  - [ ] 2.2 添加分页参数 (page, per_page)
  - [ ] 2.3 添加状态筛选 (status: active/resolved/all)
  - [ ] 2.4 添加类别筛选 (category: politics/business/technology/economics/crypto)
  - [ ] 2.5 返回 `PaginatedResponse[MarketListItem]`

- [ ] Task 3: 实现市场详情端点 (AC: 2)
  - [ ] 3.1 实现 `GET /api/markets/{market_id}` 路由
  - [ ] 3.2 处理市场不存在情况 (返回 404 NOT_FOUND)
  - [ ] 3.3 返回 `ApiResponse[MarketResponse]`

- [ ] Task 4: 集成 MarketRepository (AC: All)
  - [ ] 4.1 在路由中注入 MarketRepository 依赖
  - [ ] 4.2 使用 `get_all_markets()` 获取市场列表
  - [ ] 4.3 使用 `get_market()` 获取单个市场
  - [ ] 4.4 使用 `get_active_markets()` 筛选活跃市场
  - [ ] 4.5 使用 `get_markets_by_category()` 按类别筛选

- [ ] Task 5: 实现分页和筛选逻辑 (AC: 1, 3, 4)
  - [ ] 5.1 实现内存分页 (从 Repository 获取后切片)
  - [ ] 5.2 实现状态筛选逻辑
  - [ ] 5.3 实现类别筛选逻辑
  - [ ] 5.4 计算总数和分页元数据

- [ ] Task 6: 编写单元测试 (AC: All)
  - [ ] 6.1 创建 `tests/test_dashboard/test_routes/__init__.py`
  - [ ] 6.2 创建 `tests/test_dashboard/test_routes/test_markets.py`
  - [ ] 6.3 测试 `GET /api/markets` 返回正确列表
  - [ ] 6.4 测试 `GET /api/markets` 分页功能
  - [ ] 6.5 测试 `GET /api/markets?status=active` 筛选
  - [ ] 6.6 测试 `GET /api/markets?category=politics` 筛选
  - [ ] 6.7 测试 `GET /api/markets/{market_id}` 返回详情
  - [ ] 6.8 测试 `GET /api/markets/{market_id}` 404 处理
  - [ ] 6.9 测试响应格式符合规范

- [ ] Task 7: 代码质量检查 (AC: All)
  - [ ] 7.1 运行 `mypy src/dashboard/routes/markets.py` 无错误
  - [ ] 7.2 运行 `black --check` 通过
  - [ ] 7.3 运行 `isort --check` 通过
  - [ ] 7.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md, epics.md]

**API 端点规范:**

| 端点 | 方法 | 描述 | 响应类型 |
|------|------|------|----------|
| `/api/markets` | GET | 获取市场列表 | `PaginatedResponse[MarketListItem]` |
| `/api/markets/{market_id}` | GET | 获取市场详情 | `ApiResponse[MarketResponse]` |

**查询参数:**

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `page` | int | 1 | 页码 (从 1 开始) |
| `per_page` | int | 20 | 每页数量 (最大 100) |
| `status` | str | "all" | 状态筛选: active/resolved/all |
| `category` | str | None | 类别筛选: politics/business/technology/economics/crypto |

**响应格式规范 [Source: architecture.md#API Response Format]:**

```json
// 列表响应
{
  "success": true,
  "data": [
    {
      "id": "market-123",
      "title": "Will X happen by Y date?",
      "category": "politics",
      "yes_price": 0.65,
      "no_price": 0.35,
      "liquidity": 50000.0,
      "deadline": "2026-03-15T00:00:00Z",
      "resolution_status": null
    }
  ],
  "meta": {
    "total": 100,
    "page": 1,
    "per_page": 20
  }
}

// 详情响应
{
  "success": true,
  "data": {
    "id": "market-123",
    "title": "Will X happen by Y date?",
    "description": "Detailed description...",
    "category": "politics",
    "yes_price": 0.65,
    "no_price": 0.35,
    "liquidity": 50000.0,
    "deadline": "2026-03-15T00:00:00Z",
    "resolution_status": null,
    "resolution_outcome": null,
    "created_at": "2026-02-15T10:30:00Z",
    "updated_at": "2026-02-17T08:00:00Z"
  }
}

// 错误响应 (市场不存在)
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Market not found: invalid-id"
  }
}
```

### 已有组件 (必须复用)

**Market 模型** [Source: src/models/market.py]
```python
class Market(BaseModel):
    id: str
    title: str
    description: str | None
    category: MarketCategory | None
    yes_price: float | None
    no_price: float | None
    liquidity: float | None
    deadline: datetime | None
    resolution_status: str | None
    resolution_outcome: str | None
    created_at: datetime | None
    updated_at: datetime | None

class MarketCategory(str, Enum):
    POLITICS = "politics"
    BUSINESS = "business"
    TECHNOLOGY = "technology"
    ECONOMICS = "economics"
    CRYPTO = "crypto"
```

**MarketRepository** [Source: src/storage/repositories/market_repo.py]
```python
class MarketRepository:
    async def get_market(self, market_id: str) -> Market | None: ...
    async def get_all_markets(self, limit: int | None = None) -> list[Market]: ...
    async def get_active_markets(self) -> list[Market]: ...
    async def get_markets_by_category(self, category: MarketCategory | str) -> list[Market]: ...
    async def get_resolved_markets(self) -> list[Market]: ...
```

**API 响应模型** [Source: src/models/api_response.py]
```python
class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None
    error: ErrorDetail | None

class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T]
    meta: PaginationMeta

class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int

class ErrorCode:
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
```

### 新增数据模型

**src/models/market_response.py:**

```python
"""Market API response models.

This module defines Pydantic models for market API responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer

from src.models.market import MarketCategory


class MarketListItem(BaseModel):
    """Market list item for API list responses.

    Contains a subset of market fields optimized for list display.

    Attributes:
        id: Market unique identifier
        title: Market title
        category: Market category
        yes_price: YES outcome price (0-1)
        no_price: NO outcome price (0-1)
        liquidity: Available liquidity in USD
        deadline: Market deadline
        resolution_status: Resolution status (if resolved)
    """

    id: str = Field(..., description="Market ID")
    title: str = Field(..., description="Market title")
    category: MarketCategory | None = Field(None, description="Market category")
    yes_price: float | None = Field(None, description="YES price")
    no_price: float | None = Field(None, description="NO price")
    liquidity: float | None = Field(None, description="Liquidity (USD)")
    deadline: datetime | None = Field(None, description="Market deadline")
    resolution_status: str | None = Field(None, description="Resolution status")

    @field_serializer("deadline")
    def serialize_datetime(self, dt: datetime | None, _info: Any) -> str | None:
        """Serialize datetime to ISO 8601 format."""
        if dt is None:
            return None
        return dt.isoformat()


class MarketResponse(BaseModel):
    """Full market details for API detail responses.

    Contains all market fields for detailed view.

    Attributes:
        id: Market unique identifier
        title: Market title
        description: Market description
        category: Market category
        yes_price: YES outcome price (0-1)
        no_price: NO outcome price (0-1)
        liquidity: Available liquidity in USD
        deadline: Market deadline
        resolution_status: Resolution status
        resolution_outcome: Resolution outcome (if resolved)
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
    """

    id: str = Field(..., description="Market ID")
    title: str = Field(..., description="Market title")
    description: str | None = Field(None, description="Market description")
    category: MarketCategory | None = Field(None, description="Market category")
    yes_price: float | None = Field(None, description="YES price")
    no_price: float | None = Field(None, description="NO price")
    liquidity: float | None = Field(None, description="Liquidity (USD)")
    deadline: datetime | None = Field(None, description="Market deadline")
    resolution_status: str | None = Field(None, description="Resolution status")
    resolution_outcome: str | None = Field(None, description="Resolution outcome")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Update timestamp")

    @field_serializer("deadline", "created_at", "updated_at")
    def serialize_datetime(self, dt: datetime | None, _info: Any) -> str | None:
        """Serialize datetime to ISO 8601 format."""
        if dt is None:
            return None
        return dt.isoformat()


class MarketListQueryParams(BaseModel):
    """Query parameters for market list endpoint.

    Attributes:
        page: Page number (1-based)
        per_page: Items per page (max 100)
        status: Filter by status (active/resolved/all)
        category: Filter by category
    """

    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    status: str = Field(default="all", description="Status filter")
    category: MarketCategory | None = Field(default=None, description="Category filter")


__all__ = ["MarketListItem", "MarketResponse", "MarketListQueryParams"]
```

### 实现模板

**src/dashboard/routes/markets.py:**

```python
"""Market data API routes.

This module provides REST API endpoints for market data operations.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.models.api_response import ApiResponse, ErrorCode, PaginatedResponse, PaginationMeta
from src.models.market import Market, MarketCategory
from src.models.market_response import MarketListItem, MarketResponse
from src.storage.repositories.market_repo import MarketRepository

logger = logging.getLogger(__name__)

router = APIRouter()


def get_market_repository() -> MarketRepository:
    """Get MarketRepository instance.

    Returns:
        MarketRepository instance
    """
    return MarketRepository()


@router.get("", response_model=PaginatedResponse[MarketListItem])
async def list_markets(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    status: Annotated[str, Query(description="Status filter (active/resolved/all)")] = "all",
    category: Annotated[str | None, Query(description="Category filter")] = None,
    repo: MarketRepository = Depends(get_market_repository),
) -> PaginatedResponse[MarketListItem]:
    """Get market list with pagination and filtering.

    Args:
        page: Page number (1-based)
        per_page: Items per page (max 100)
        status: Status filter (active/resolved/all)
        category: Category filter
        repo: MarketRepository dependency

    Returns:
        Paginated list of markets
    """
    logger.info(f"📊 Listing markets: page={page}, per_page={per_page}, status={status}, category={category}")

    # Get markets based on filters
    if status == "active":
        markets = await repo.get_active_markets()
    elif status == "resolved":
        markets = await repo.get_resolved_markets()
    else:
        markets = await repo.get_all_markets()

    # Apply category filter
    if category:
        try:
            category_enum = MarketCategory(category)
            markets = [m for m in markets if m.category == category_enum]
        except ValueError:
            # Invalid category, return empty list
            markets = []

    # Calculate pagination
    total = len(markets)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_markets = markets[start:end]

    # Convert to response models
    items = [
        MarketListItem(
            id=m.id,
            title=m.title,
            category=m.category,
            yes_price=m.yes_price,
            no_price=m.no_price,
            liquidity=m.liquidity,
            deadline=m.deadline,
            resolution_status=m.resolution_status,
        )
        for m in paginated_markets
    ]

    return PaginatedResponse(
        success=True,
        data=items,
        meta=PaginationMeta(total=total, page=page, per_page=per_page),
    )


@router.get("/{market_id}", response_model=ApiResponse[MarketResponse])
async def get_market(
    market_id: str,
    repo: MarketRepository = Depends(get_market_repository),
) -> ApiResponse[MarketResponse]:
    """Get market details by ID.

    Args:
        market_id: Market ID
        repo: MarketRepository dependency

    Returns:
        Market details

    Raises:
        HTTPException: If market not found
    """
    logger.info(f"📊 Getting market: {market_id}")

    market = await repo.get_market(market_id)

    if market is None:
        logger.warning(f"📊 Market not found: {market_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": ErrorCode.NOT_FOUND,
                    "message": f"Market not found: {market_id}",
                },
            },
        )

    response = MarketResponse(
        id=market.id,
        title=market.title,
        description=market.description,
        category=market.category,
        yes_price=market.yes_price,
        no_price=market.no_price,
        liquidity=market.liquidity,
        deadline=market.deadline,
        resolution_status=market.resolution_status,
        resolution_outcome=market.resolution_outcome,
        created_at=market.created_at,
        updated_at=market.updated_at,
    )

    return ApiResponse(success=True, data=response)


__all__ = ["router"]
```

### 项目结构 [Source: architecture.md#Project Structure]

**新增/修改文件:**
```
src/
├── models/
│   ├── market_response.py        # 新增: API 响应模型
│   └── __init__.py               # 更新: 导出新模型
└── dashboard/
    └── routes/
        └── markets.py            # 更新: 实现端点

tests/
└── test_dashboard/
    └── test_routes/
        ├── __init__.py           # 新增
        └── test_markets.py       # 新增: 市场路由测试
```

### 依赖关系

**本故事依赖:**
- Story 7.1: FastAPI 应用初始化 (已完成 - app.py, dependencies.py, api_response.py)
- Epic 2: 市场数据获取与筛选 (已完成 - Market, MarketRepository)

**后续故事依赖本故事:**
- Story 7.3: 持仓与交易 API (参考 markets.py 实现模式)
- Story 7.6: 前端 API 集成 (使用本故事的端点)

### 前一个故事学习 [Source: 7-1-fastapi-app-initialization.md]

**从 Story 7.1 学到的模式:**

1. **响应模型分离** - API 响应模型与数据库模型分离 (Market vs MarketResponse)
2. **依赖注入** - 使用 FastAPI Depends 注入 Repository
3. **统一错误处理** - 使用 HTTPException 返回统一错误格式
4. **日志标准化** - 使用 emoji 标记日志 (📊 市场数据)
5. **类型注解** - 使用 Annotated 类型提供 OpenAPI 文档
6. **分页响应** - 使用 PaginatedResponse 包装列表数据

### 实现注意事项

**关键点:**

1. **分页实现** - 当前使用内存分页 (从 Repository 获取全部后切片)，后续可优化为数据库分页
2. **筛选逻辑** - status 筛选使用 Repository 方法，category 筛选在内存中进行
3. **404 处理** - 使用 HTTPException 配合 detail 返回统一错误格式
4. **类型转换** - Market 到 MarketListItem/MarketResponse 的转换需要显式进行

**性能考虑:**

- NFR4 要求响应时间 < 2 秒
- 当前实现适合中小型数据集 (1000 条以内)
- 后续可优化为数据库级别的分页和筛选

**日志级别:**

| 级别 | 场景 | Emoji |
|------|------|-------|
| INFO | 列表查询 | 📊 |
| INFO | 详情查询 | 📊 |
| WARNING | 市场不存在 | 📊 |

### 测试策略

```python
# tests/test_dashboard/test_routes/test_markets.py
"""Tests for market API routes."""

import pytest
from fastapi.testclient import TestClient

from src.dashboard.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestListMarkets:
    """测试市场列表端点."""

    def test_list_markets_returns_200(self, client: TestClient) -> None:
        """测试列表返回 200."""
        response = client.get("/api/markets")
        assert response.status_code == 200

    def test_list_markets_pagination(self, client: TestClient) -> None:
        """测试分页功能."""
        response = client.get("/api/markets?page=1&per_page=10")
        data = response.json()
        assert "meta" in data
        assert data["meta"]["page"] == 1
        assert data["meta"]["per_page"] == 10

    def test_list_markets_status_filter(self, client: TestClient) -> None:
        """测试状态筛选."""
        response = client.get("/api/markets?status=active")
        assert response.status_code == 200
        # 所有返回的市场都应该是活跃的
        data = response.json()
        for market in data["data"]:
            assert market["resolution_status"] is None


class TestGetMarket:
    """测试市场详情端点."""

    def test_get_market_404(self, client: TestClient) -> None:
        """测试市场不存在返回 404."""
        response = client.get("/api/markets/nonexistent-id")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "NOT_FOUND"
```

### 运行命令

```bash
# 启动开发服务器
uvicorn src.dashboard.app:app --reload --host 0.0.0.0 --port 8000

# 测试市场列表
curl http://localhost:8000/api/markets

# 测试分页
curl "http://localhost:8000/api/markets?page=1&per_page=10"

# 测试状态筛选
curl "http://localhost:8000/api/markets?status=active"

# 测试类别筛选
curl "http://localhost:8000/api/markets?category=politics"

# 测试市场详情
curl http://localhost:8000/api/markets/{market_id}

# 查看 API 文档
open http://localhost:8000/docs

# 运行测试
pytest tests/test_dashboard/test_routes/test_markets.py -v
```

### References

- [Source: architecture.md#API Response Format] - 统一响应格式规范
- [Source: architecture.md#Frontend Architecture] - 前端技术栈和 API 需求
- [Source: epics.md#Story 7.2] - 原始 Story 定义
- [Source: src/models/market.py] - Market 数据模型
- [Source: src/models/api_response.py] - API 响应模型
- [Source: src/storage/repositories/market_repo.py] - MarketRepository 实现
- [Source: 7-1-fastapi-app-initialization.md] - 前一个故事实现参考

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None

### Completion Notes List

- Successfully implemented all 7 tasks from the story
- Created 3 new files and modified 3 existing files
- All 37 new tests pass
- Full test suite (1184 tests) passes
- Code quality checks (mypy, black, isort) pass

### File List

**New Files:**
- `src/models/market_response.py` - API response models for markets
- `tests/test_dashboard/test_routes/__init__.py` - Test package init
- `tests/test_dashboard/test_routes/test_markets.py` - Market route tests

**Modified Files:**
- `src/models/__init__.py` - Added exports for new models
- `src/dashboard/routes/markets.py` - Implemented market endpoints
- `tests/test_dashboard/test_app.py` - Updated test for route registration
