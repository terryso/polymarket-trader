# Story 7.3: 持仓与交易 API

Status: done

## Story

As a **用户**,
I want **通过 API 获取持仓和交易记录**,
So that **Dashboard 能够展示我的交易活动**.

## Acceptance Criteria

**Given** 市场 API 已实现 (Story 7.2)
**When** 实现 `src/dashboard/routes/positions.py` 和 `trades.py`
**Then** 实现持仓端点:

- `GET /api/positions` - 获取当前持仓列表
- `GET /api/positions/{position_id}` - 获取持仓详情
- 响应包含: market_id, outcome, shares, avg_price, current_value, pnl, status

**And** 实现交易端点:

- `GET /api/trades` - 获取交易历史 (分页)
- `GET /api/trades/{trade_id}` - 获取交易详情
- `GET /api/trades?mode=paper` - 按模式筛选
- 响应包含: market_id, trade_type, mode, amount, price, shares, status, created_at

**And** 支持排序 (按时间倒序)
**And** 使用统一响应格式

## Tasks / Subtasks

- [x] Task 1: 定义持仓响应模型 (AC: 1)
  - [x] 1.1 在 `src/models/` 创建 `position_response.py`
  - [x] 1.2 定义 `PositionResponse` 模型 (完整持仓详情)
  - [x] 1.3 定义 `PositionListItem` 模型 (持仓列表项)
  - [x] 1.4 更新 `src/models/__init__.py` 导出新模型

- [x] Task 2: 定义交易响应模型 (AC: 2)
  - [x] 2.1 在 `src/models/` 创建 `trade_response.py`
  - [x] 2.2 定义 `TradeResponse` 模型 (完整交易详情)
  - [x] 2.3 定义 `TradeListItem` 模型 (交易列表项)
  - [x] 2.4 定义 `TradeListQueryParams` 查询参数模型
  - [x] 2.5 更新 `src/models/__init__.py` 导出新模型

- [x] Task 3: 实现持仓 API 端点 (AC: 1)
  - [x] 3.1 实现 `GET /api/positions` 路由
  - [x] 3.2 实现 `GET /api/positions/{position_id}` 路由
  - [x] 3.3 处理持仓不存在情况 (返回 404)
  - [x] 3.4 注入 PositionRepository 依赖
  - [x] 3.5 转换 Position 到 PositionListItem/PositionResponse

- [x] Task 4: 实现交易 API 端点 (AC: 2, 3, 4)
  - [x] 4.1 实现 `GET /api/trades` 路由
  - [x] 4.2 添加分页参数 (page, per_page)
  - [x] 4.3 添加模式筛选 (mode: paper/live)
  - [x] 4.4 实现 `GET /api/trades/{trade_id}` 路由
  - [x] 4.5 处理交易不存在情况 (返回 404)
  - [x] 4.6 注入 TradeRepository 依赖
  - [x] 4.7 实现分页和排序 (按时间倒序)

- [x] Task 5: 编写单元测试 (AC: All)
  - [x] 5.1 创建 `tests/test_dashboard/test_routes/test_positions.py`
  - [x] 5.2 测试 `GET /api/positions` 返回持仓列表
  - [x] 5.3 测试 `GET /api/positions/{id}` 返回持仓详情
  - [x] 5.4 测试 `GET /api/positions/{id}` 404 处理
  - [x] 5.5 创建 `tests/test_dashboard/test_routes/test_trades.py`
  - [x] 5.6 测试 `GET /api/trades` 返回交易列表
  - [x] 5.7 测试 `GET /api/trades` 分页功能
  - [x] 5.8 测试 `GET /api/trades?mode=paper` 筛选
  - [x] 5.9 测试 `GET /api/trades/{id}` 返回交易详情
  - [x] 5.10 测试 `GET /api/trades/{id}` 404 处理
  - [x] 5.11 测试响应格式符合规范

- [x] Task 6: 代码质量检查 (AC: All)
  - [x] 6.1 运行 `mypy src/dashboard/routes/positions.py` 无错误
  - [x] 6.2 运行 `mypy src/dashboard/routes/trades.py` 无错误
  - [x] 6.3 运行 `black --check` 通过
  - [x] 6.4 运行 `isort --check` 通过
  - [x] 6.5 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md, epics.md]

**API 端点规范:**

| 端点 | 方法 | 描述 | 响应类型 |
|------|------|------|----------|
| `/api/positions` | GET | 获取持仓列表 | `ApiResponse[list[PositionListItem]]` |
| `/api/positions/{position_id}` | GET | 获取持仓详情 | `ApiResponse[PositionResponse]` |
| `/api/trades` | GET | 获取交易历史 | `PaginatedResponse[TradeListItem]` |
| `/api/trades/{trade_id}` | GET | 获取交易详情 | `ApiResponse[TradeResponse]` |

**查询参数 (交易列表):**

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `page` | int | 1 | 页码 (从 1 开始) |
| `per_page` | int | 20 | 每页数量 (最大 100) |
| `mode` | str | None | 模式筛选: paper/live |

**响应格式规范 [Source: architecture.md#API Response Format]:**

```json
// 持仓列表响应
{
  "success": true,
  "data": [
    {
      "id": 1,
      "market_id": "btc-100k-2026",
      "outcome": "YES",
      "shares": 222.22,
      "avg_price": 0.45,
      "current_value": 155.55,
      "pnl": 55.55,
      "status": "OPEN",
      "opened_at": "2026-02-15T10:30:00Z"
    }
  ]
}

// 交易列表响应 (分页)
{
  "success": true,
  "data": [
    {
      "id": 1,
      "market_id": "btc-100k-2026",
      "trade_type": "BUY_YES",
      "mode": "PAPER",
      "amount": 100.0,
      "price": 0.45,
      "shares": 222.22,
      "status": "FILLED",
      "created_at": "2026-02-15T10:30:00Z"
    }
  ],
  "meta": {
    "total": 50,
    "page": 1,
    "per_page": 20
  }
}

// 详情响应
{
  "success": true,
  "data": {
    "id": 1,
    "market_id": "btc-100k-2026",
    "outcome": "YES",
    "shares": 222.22,
    "avg_price": 0.45,
    "initial_value": 100.0,
    "current_value": 155.55,
    "pnl": 55.55,
    "status": "OPEN",
    "opened_at": "2026-02-15T10:30:00Z",
    "closed_at": null
  }
}

// 错误响应 (持仓/交易不存在)
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Position not found: 999"
  }
}
```

### 已有组件 (必须复用)

**Position 模型** [Source: src/models/position.py]
```python
class Position(BaseModel):
    id: int
    market_id: str
    outcome: PositionOutcome  # YES/NO
    shares: float
    avg_price: float  # 0-1
    initial_value: float | None
    current_value: float | None
    pnl: float | None
    status: PositionStatus  # OPEN/CLOSED
    opened_at: datetime | None
    closed_at: datetime | None

class PositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class PositionOutcome(str, Enum):
    YES = "YES"
    NO = "NO"
```

**Trade 模型** [Source: src/models/trade.py]
```python
class Trade(BaseModel):
    id: int
    market_id: str
    trade_type: TradeType  # BUY_YES/BUY_NO/SELL
    mode: TradeMode  # PAPER/LIVE
    amount: float
    price: float  # 0-1
    shares: float | None
    status: TradeStatus  # PENDING/FILLED/CANCELLED
    llm_prediction_id: int | None
    position_id: int | None
    created_at: datetime | None

class TradeType(str, Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    SELL = "SELL"

class TradeMode(str, Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"

class TradeStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
```

**PositionRepository** [Source: src/storage/repositories/position_repo.py]
```python
class PositionRepository:
    async def get_by_id(self, position_id: int) -> Position | None: ...
    async def get_by_market(self, market_id: str, status: PositionStatus | None = None) -> Position | None: ...
    async def get_open_positions(self) -> list[Position]: ...
    async def save(self, position: Position) -> Position: ...
    async def update(self, position: Position) -> Position: ...
    async def delete(self, position_id: int) -> bool: ...
```

**TradeRepository** [Source: src/storage/repositories/trade_repo.py]
```python
class TradeRepository:
    async def get_by_id(self, trade_id: int) -> Trade | None: ...
    async def get_by_market(self, market_id: str) -> list[Trade]: ...
    async def get_by_mode(self, mode: TradeMode) -> list[Trade]: ...
    async def get_recent(self, limit: int = 50) -> list[Trade]: ...
    async def get_by_date_range(self, start_date: date, end_date: date, mode: TradeMode | None = None) -> list[Trade]: ...
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

**src/models/position_response.py:**

```python
"""Position API response models.

This module defines Pydantic models for position API responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer

from src.models.position import PositionOutcome, PositionStatus


class PositionListItem(BaseModel):
    """Position list item for API list responses.

    Contains position fields for list display.

    Attributes:
        id: Position unique identifier
        market_id: Reference to the market
        outcome: Position outcome type (YES/NO)
        shares: Number of shares held
        avg_price: Average purchase price per share
        current_value: Current position value in USD
        pnl: Profit/Loss in USD
        status: Current position status
        opened_at: Position opening timestamp
    """

    id: int = Field(..., description="Position ID")
    market_id: str = Field(..., description="Market reference")
    outcome: PositionOutcome = Field(..., description="Position outcome")
    shares: float = Field(..., description="Number of shares")
    avg_price: float = Field(..., description="Average price (0-1)")
    current_value: float | None = Field(None, description="Current value (USD)")
    pnl: float | None = Field(None, description="Profit/Loss (USD)")
    status: PositionStatus = Field(..., description="Position status")
    opened_at: datetime | None = Field(None, description="Opening timestamp")

    @field_serializer("opened_at")
    def serialize_datetime(self, dt: datetime | None, _info: Any) -> str | None:
        """Serialize datetime to ISO 8601 format."""
        if dt is None:
            return None
        return dt.isoformat()


class PositionResponse(BaseModel):
    """Full position details for API detail responses.

    Contains all position fields for detailed view.

    Attributes:
        id: Position unique identifier
        market_id: Reference to the market
        outcome: Position outcome type (YES/NO)
        shares: Number of shares held
        avg_price: Average purchase price per share
        initial_value: Initial position value in USD
        current_value: Current position value in USD
        pnl: Profit/Loss in USD
        status: Current position status
        opened_at: Position opening timestamp
        closed_at: Position closing timestamp
    """

    id: int = Field(..., description="Position ID")
    market_id: str = Field(..., description="Market reference")
    outcome: PositionOutcome = Field(..., description="Position outcome")
    shares: float = Field(..., description="Number of shares")
    avg_price: float = Field(..., description="Average price (0-1)")
    initial_value: float | None = Field(None, description="Initial value (USD)")
    current_value: float | None = Field(None, description="Current value (USD)")
    pnl: float | None = Field(None, description="Profit/Loss (USD)")
    status: PositionStatus = Field(..., description="Position status")
    opened_at: datetime | None = Field(None, description="Opening timestamp")
    closed_at: datetime | None = Field(None, description="Closing timestamp")

    @field_serializer("opened_at", "closed_at")
    def serialize_datetime(self, dt: datetime | None, _info: Any) -> str | None:
        """Serialize datetime to ISO 8601 format."""
        if dt is None:
            return None
        return dt.isoformat()


__all__ = ["PositionListItem", "PositionResponse"]
```

**src/models/trade_response.py:**

```python
"""Trade API response models.

This module defines Pydantic models for trade API responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer

from src.models.trade import TradeMode, TradeStatus, TradeType


class TradeListItem(BaseModel):
    """Trade list item for API list responses.

    Contains trade fields for list display.

    Attributes:
        id: Trade unique identifier
        market_id: Reference to the market
        trade_type: Type of trade
        mode: Trading mode
        amount: Trade amount in USD
        price: Price per share
        shares: Number of shares traded
        status: Trade status
        created_at: Trade creation timestamp
    """

    id: int = Field(..., description="Trade ID")
    market_id: str = Field(..., description="Market reference")
    trade_type: TradeType = Field(..., description="Trade type")
    mode: TradeMode = Field(..., description="Trading mode")
    amount: float = Field(..., description="Trade amount (USD)")
    price: float = Field(..., description="Price per share (0-1)")
    shares: float | None = Field(None, description="Number of shares")
    status: TradeStatus = Field(..., description="Trade status")
    created_at: datetime | None = Field(None, description="Creation timestamp")

    @field_serializer("created_at")
    def serialize_datetime(self, dt: datetime | None, _info: Any) -> str | None:
        """Serialize datetime to ISO 8601 format."""
        if dt is None:
            return None
        return dt.isoformat()


class TradeResponse(BaseModel):
    """Full trade details for API detail responses.

    Contains all trade fields for detailed view.

    Attributes:
        id: Trade unique identifier
        market_id: Reference to the market
        trade_type: Type of trade
        mode: Trading mode
        amount: Trade amount in USD
        price: Price per share
        shares: Number of shares traded
        status: Trade status
        llm_prediction_id: Reference to LLM prediction
        position_id: Reference to position
        created_at: Trade creation timestamp
    """

    id: int = Field(..., description="Trade ID")
    market_id: str = Field(..., description="Market reference")
    trade_type: TradeType = Field(..., description="Trade type")
    mode: TradeMode = Field(..., description="Trading mode")
    amount: float = Field(..., description="Trade amount (USD)")
    price: float = Field(..., description="Price per share (0-1)")
    shares: float | None = Field(None, description="Number of shares")
    status: TradeStatus = Field(..., description="Trade status")
    llm_prediction_id: int | None = Field(None, description="LLM prediction reference")
    position_id: int | None = Field(None, description="Position reference")
    created_at: datetime | None = Field(None, description="Creation timestamp")

    @field_serializer("created_at")
    def serialize_datetime(self, dt: datetime | None, _info: Any) -> str | None:
        """Serialize datetime to ISO 8601 format."""
        if dt is None:
            return None
        return dt.isoformat()


class TradeListQueryParams(BaseModel):
    """Query parameters for trade list endpoint.

    Attributes:
        page: Page number (1-based)
        per_page: Items per page (max 100)
        mode: Filter by trading mode
    """

    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    mode: TradeMode | None = Field(default=None, description="Mode filter")


__all__ = ["TradeListItem", "TradeResponse", "TradeListQueryParams"]
```

### 实现模板

**src/dashboard/routes/positions.py:**

```python
"""Position data API routes.

This module provides REST API endpoints for position operations.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.models.api_response import ApiResponse, ErrorCode
from src.models.position_response import PositionListItem, PositionResponse
from src.storage.repositories.position_repo import PositionRepository

logger = logging.getLogger(__name__)

router = APIRouter()


def get_position_repository() -> PositionRepository:
    """Get PositionRepository instance.

    Returns:
        PositionRepository instance
    """
    return PositionRepository()


@router.get("", response_model=ApiResponse[list[PositionListItem]])
async def list_positions(
    repo: PositionRepository = Depends(get_position_repository),
) -> ApiResponse[list[PositionListItem]]:
    """Get list of open positions.

    Args:
        repo: PositionRepository dependency

    Returns:
        List of open positions
    """
    logger.info("💰 Listing open positions")

    positions = await repo.get_open_positions()

    items = [
        PositionListItem(
            id=p.id,
            market_id=p.market_id,
            outcome=p.outcome,
            shares=p.shares,
            avg_price=p.avg_price,
            current_value=p.current_value,
            pnl=p.pnl,
            status=p.status,
            opened_at=p.opened_at,
        )
        for p in positions
    ]

    return ApiResponse(success=True, data=items)


@router.get("/{position_id}", response_model=ApiResponse[PositionResponse])
async def get_position(
    position_id: int,
    repo: PositionRepository = Depends(get_position_repository),
) -> ApiResponse[PositionResponse]:
    """Get position details by ID.

    Args:
        position_id: Position ID
        repo: PositionRepository dependency

    Returns:
        Position details

    Raises:
        HTTPException: If position not found
    """
    logger.info(f"💰 Getting position: {position_id}")

    position = await repo.get_by_id(position_id)

    if position is None:
        logger.warning(f"💰 Position not found: {position_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": ErrorCode.NOT_FOUND,
                    "message": f"Position not found: {position_id}",
                },
            },
        )

    response = PositionResponse(
        id=position.id,
        market_id=position.market_id,
        outcome=position.outcome,
        shares=position.shares,
        avg_price=position.avg_price,
        initial_value=position.initial_value,
        current_value=position.current_value,
        pnl=position.pnl,
        status=position.status,
        opened_at=position.opened_at,
        closed_at=position.closed_at,
    )

    return ApiResponse(success=True, data=response)


__all__ = ["router"]
```

**src/dashboard/routes/trades.py:**

```python
"""Trade data API routes.

This module provides REST API endpoints for trade operations.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.models.api_response import ApiResponse, ErrorCode, PaginatedResponse, PaginationMeta
from src.models.trade import TradeMode
from src.models.trade_response import TradeListItem, TradeResponse
from src.storage.repositories.trade_repo import TradeRepository

logger = logging.getLogger(__name__)

router = APIRouter()


def get_trade_repository() -> TradeRepository:
    """Get TradeRepository instance.

    Returns:
        TradeRepository instance
    """
    return TradeRepository()


@router.get("", response_model=PaginatedResponse[TradeListItem])
async def list_trades(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    mode: Annotated[str | None, Query(description="Mode filter (paper/live)")] = None,
    repo: TradeRepository = Depends(get_trade_repository),
) -> PaginatedResponse[TradeListItem]:
    """Get trade history with pagination and filtering.

    Args:
        page: Page number (1-based)
        per_page: Items per page (max 100)
        mode: Mode filter (paper/live)
        repo: TradeRepository dependency

    Returns:
        Paginated list of trades
    """
    logger.info(f"💰 Listing trades: page={page}, per_page={per_page}, mode={mode}")

    # Get trades based on mode filter
    if mode:
        try:
            mode_enum = TradeMode(mode.upper())
            trades = await repo.get_by_mode(mode_enum)
        except ValueError:
            # Invalid mode, return empty list
            trades = []
    else:
        trades = await repo.get_recent(limit=1000)  # Get all for pagination

    # Calculate pagination
    total = len(trades)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_trades = trades[start:end]

    # Convert to response models
    items = [
        TradeListItem(
            id=t.id,
            market_id=t.market_id,
            trade_type=t.trade_type,
            mode=t.mode,
            amount=t.amount,
            price=t.price,
            shares=t.shares,
            status=t.status,
            created_at=t.created_at,
        )
        for t in paginated_trades
    ]

    return PaginatedResponse(
        success=True,
        data=items,
        meta=PaginationMeta(total=total, page=page, per_page=per_page),
    )


@router.get("/{trade_id}", response_model=ApiResponse[TradeResponse])
async def get_trade(
    trade_id: int,
    repo: TradeRepository = Depends(get_trade_repository),
) -> ApiResponse[TradeResponse]:
    """Get trade details by ID.

    Args:
        trade_id: Trade ID
        repo: TradeRepository dependency

    Returns:
        Trade details

    Raises:
        HTTPException: If trade not found
    """
    logger.info(f"💰 Getting trade: {trade_id}")

    trade = await repo.get_by_id(trade_id)

    if trade is None:
        logger.warning(f"💰 Trade not found: {trade_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": ErrorCode.NOT_FOUND,
                    "message": f"Trade not found: {trade_id}",
                },
            },
        )

    response = TradeResponse(
        id=trade.id,
        market_id=trade.market_id,
        trade_type=trade.trade_type,
        mode=trade.mode,
        amount=trade.amount,
        price=trade.price,
        shares=trade.shares,
        status=trade.status,
        llm_prediction_id=trade.llm_prediction_id,
        position_id=trade.position_id,
        created_at=trade.created_at,
    )

    return ApiResponse(success=True, data=response)


__all__ = ["router"]
```

### 项目结构 [Source: architecture.md#Project Structure]

**新增/修改文件:**
```
src/
├── models/
│   ├── position_response.py     # 新增: API 响应模型
│   ├── trade_response.py        # 新增: API 响应模型
│   └── __init__.py              # 更新: 导出新模型
└── dashboard/
    └── routes/
        ├── positions.py         # 更新: 实现端点
        └── trades.py            # 更新: 实现端点

tests/
└── test_dashboard/
    └── test_routes/
        ├── test_positions.py    # 新���: 持仓路由测试
        └── test_trades.py       # 新增: 交易路由测试
```

### 依赖关系

**本故事依赖:**
- Story 7.1: FastAPI 应用初始化 (已完成 - app.py, dependencies.py, api_response.py)
- Story 7.2: 市场数据 API (已完成 - 参考 markets.py 实现模式)
- Epic 4: 风险控制与熔断系统 (已完成 - Position, PositionRepository)
- Epic 5: Paper Trading 模拟交易 (已完成 - Trade, TradeRepository)

**后续故事依赖本故事:**
- Story 7.4: 预测与统计 API (参考本故事实现模式)
- Story 7.6: 前端 API 集成 (使用本故事的端点)

### 前一个故事学习 [Source: 7-2-market-data-api.md]

**从 Story 7.2 学到的模式:**

1. **响应模型分离** - API 响应模型与数据库模型分离 (Trade vs TradeResponse)
2. **依赖注入** - 使用 FastAPI Depends 注入 Repository
3. **统一错误处理** - 使用 HTTPException 返回统一错误格式
4. **日志标准化** - 使用 emoji 标记日志 (💰 交易/持仓)
5. **类型注解** - 使用 Annotated 类型提供 OpenAPI 文档
6. **分页响应** - 使用 PaginatedResponse 包装列表数据

### 实现注意事项

**关键点:**

1. **持仓列表 vs 交易列表** - 持仓列表通常较短，不需要分页；交易历史需要分页
2. **模式筛选** - 交易列表支持 mode 参数筛选 paper/live 模式
3. **404 处理** - 使用 HTTPException 配合 detail 返回统一错误格式
4. **类型转换** - Position/Trade 到响应模型的转换需要显式进行
5. **空列表处理** - 无数据时返回空列表而非 404

**性能考虑:**

- NFR4 要求响应时间 < 2 秒
- 持仓列表通常 < 10 条，不需要分页
- 交易历史可能很长，需要分页支持
- 后续可优化为数据库级别的分页

**日志级别:**

| 级别 | 场景 | Emoji |
|------|------|-------|
| INFO | 列表查询 | 💰 |
| INFO | 详情查询 | 💰 |
| WARNING | 持仓/交易不存在 | 💰 |

### 测试策略

```python
# tests/test_dashboard/test_routes/test_positions.py
"""Tests for position API routes."""

import pytest
from fastapi.testclient import TestClient

from src.dashboard.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestListPositions:
    """测试持仓列表端点."""

    def test_list_positions_returns_200(self, client: TestClient) -> None:
        """测试列表返回 200."""
        response = client.get("/api/positions")
        assert response.status_code == 200

    def test_list_positions_format(self, client: TestClient) -> None:
        """测试响应格式."""
        response = client.get("/api/positions")
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert data["success"] is True
        assert isinstance(data["data"], list)


class TestGetPosition:
    """测试持仓详情端点."""

    def test_get_position_404(self, client: TestClient) -> None:
        """测试持仓不存在返回 404."""
        response = client.get("/api/positions/99999")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "NOT_FOUND"


# tests/test_dashboard/test_routes/test_trades.py
"""Tests for trade API routes."""


class TestListTrades:
    """测试交易列表端点."""

    def test_list_trades_returns_200(self, client: TestClient) -> None:
        """测试列表返回 200."""
        response = client.get("/api/trades")
        assert response.status_code == 200

    def test_list_trades_pagination(self, client: TestClient) -> None:
        """测试分页功能."""
        response = client.get("/api/trades?page=1&per_page=10")
        data = response.json()
        assert "meta" in data
        assert data["meta"]["page"] == 1
        assert data["meta"]["per_page"] == 10

    def test_list_trades_mode_filter(self, client: TestClient) -> None:
        """测试模式筛选."""
        response = client.get("/api/trades?mode=paper")
        assert response.status_code == 200
        data = response.json()
        # 所有返回的交易都应该是 PAPER 模式
        for trade in data["data"]:
            assert trade["mode"] == "PAPER"


class TestGetTrade:
    """测试交易详情端点."""

    def test_get_trade_404(self, client: TestClient) -> None:
        """测试交易不存在返回 404."""
        response = client.get("/api/trades/99999")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "NOT_FOUND"
```

### 运行命令

```bash
# 启动开发服务器
uvicorn src.dashboard.app:app --reload --host 0.0.0.0 --port 8000

# 测试持仓列表
curl http://localhost:8000/api/positions

# 测试持仓详情
curl http://localhost:8000/api/positions/1

# 测试交易列表
curl http://localhost:8000/api/trades

# 测试分页
curl "http://localhost:8000/api/trades?page=1&per_page=10"

# 测试模式筛选
curl "http://localhost:8000/api/trades?mode=paper"

# 测试交易详情
curl http://localhost:8000/api/trades/1

# 查看 API 文档
open http://localhost:8000/docs

# 运行测试
pytest tests/test_dashboard/test_routes/test_positions.py -v
pytest tests/test_dashboard/test_routes/test_trades.py -v
```

### References

- [Source: architecture.md#API Response Format] - 统一响应格式规范
- [Source: architecture.md#Database Schema] - positions 和 trades 表结构
- [Source: epics.md#Story 7.3] - 原始 Story 定义
- [Source: src/models/position.py] - Position 数据模型
- [Source: src/models/trade.py] - Trade 数据模型
- [Source: src/models/api_response.py] - API 响应模型
- [Source: src/storage/repositories/position_repo.py] - PositionRepository 实现
- [Source: src/storage/repositories/trade_repo.py] - TradeRepository 实现
- [Source: 7-2-market-data-api.md] - 前一个故事实现参考

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6-20250528)

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

1. Created API response models for positions and trades:
   - `PositionListItem` - for list endpoint response
   - `PositionResponse` - for detail endpoint response
   - `TradeListItem` - for list endpoint response
   - `TradeResponse` - for detail endpoint response
   - `TradeListQueryParams` - for query parameter validation

2. Implemented API routes:
   - `GET /api/positions` - returns list of open positions
   - `GET /api/positions/{position_id}` - returns position details
   - `GET /api/trades` - returns paginated trade history with mode filter
   - `GET /api/trades/{trade_id}` - returns trade details

3. All tests pass (29 new tests + 1213 total):
   - 11 tests for positions routes
   - 18 tests for trades routes

4. Code quality checks passed:
   - mypy: no type errors
   - black: all files formatted
   - isort: all imports sorted

### File List

**New files:**
- `/Users/nick/CascadeProjects/polymarket-trader-story-7.3/src/models/position_response.py`
- `/Users/nick/CascadeProjects/polymarket-trader-story-7.3/src/models/trade_response.py`
- `/Users/nick/CascadeProjects/polymarket-trader-story-7.3/tests/test_dashboard/test_routes/test_positions.py`
- `/Users/nick/CascadeProjects/polymarket-trader-story-7.3/tests/test_dashboard/test_routes/test_trades.py`

**Modified files:**
- `/Users/nick/CascadeProjects/polymarket-trader-story-7.3/src/models/__init__.py` - added exports
- `/Users/nick/CascadeProjects/polymarket-trader-story-7.3/src/dashboard/routes/positions.py` - implemented routes
- `/Users/nick/CascadeProjects/polymarket-trader-story-7.3/src/dashboard/routes/trades.py` - implemented routes
- `/Users/nick/CascadeProjects/polymarket-trader-story-7.3/tests/test_dashboard/test_app.py` - updated route registration tests
