# Story 7.4: 预测与统计 API

Status: done

## Story

As a **用户**,
I want **通过 API 获取预测记录和统计数据**,
So that **Dashboard 能够展示预测准确率和收益统计**.

## Acceptance Criteria

**Given** 持仓交易 API 已实现 (Story 7.3)
**When** 实现 `src/dashboard/routes/predictions.py` 和 `statistics.py`
**Then** 实现预测端点:

- `GET /api/predictions` - 获取预测列表
- `GET /api/predictions/{prediction_id}` - 获取预测详情
- `GET /api/predictions/accuracy` - 获取准确率统计
- 响应包含: market_id, predicted_probability, confidence, actual_outcome, is_correct

**And** 实现统计端点:

- `GET /api/statistics/overview` - 获取系统概览
  - 返回: current_capital, total_pnl, win_rate, total_trades
- `GET /api/statistics/daily` - 获取每日统计
- `GET /api/statistics/performance` - 获取表现数据 (用于图表)

**And** 使用统一响应格式

## Tasks / Subtasks

- [x] Task 1: 定义预测响应模型 (AC: 1)
  - [x] 1.1 在 `src/models/` 创建 `prediction_response.py`
  - [x] 1.2 定义 `PredictionListItem` 模型 (预测列表项)
  - [x] 1.3 定义 `PredictionResponse` 模型 (完整预测详情)
  - [x] 1.4 定义 `AccuracyStats` 模型 (准确率统计)
  - [x] 1.5 更新 `src/models/__init__.py` 导出新模型

- [x] Task 2: 定义统计响应模型 (AC: 2)
  - [x] 2.1 在 `src/models/` 创建 `statistics_response.py`
  - [x] 2.2 定义 `OverviewStats` 模型 (系统概览)
  - [x] 2.3 定义 `DailyStatsItem` 模型 (每日统计项)
  - [x] 2.4 定义 `PerformanceData` 模型 (图表数据)
  - [x] 2.5 更新 `src/models/__init__.py` 导出新模型

- [x] Task 3: 实现预测 API 端点 (AC: 1)
  - [x] 3.1 实现 `GET /api/predictions` 路由
  - [x] 3.2 实现分页参数 (page, per_page)
  - [x] 3.3 实现 `GET /api/predictions/{prediction_id}` 路由
  - [x] 3.4 实现 `GET /api/predictions/accuracy` 路由
  - [x] 3.5 处理预测不存在情况 (返回 404)
  - [x] 3.6 注入 PredictionRepository 依赖
  - [x] 3.7 转换 Prediction 到响应模型

- [x] Task 4: 实现统计 API 端点 (AC: 2)
  - [x] 4.1 实现 `GET /api/statistics/overview` 路由
  - [x] 4.2 实现 `GET /api/statistics/daily` 路由 (分页)
  - [x] 4.3 实现 `GET /api/statistics/performance` 路由
  - [x] 4.4 注入 StatisticsRepository 和 ThreadSafeState 依赖
  - [x] 4.5 聚合计算概览统计数据

- [x] Task 5: 编写单元测试 (AC: All)
  - [x] 5.1 创建 `tests/test_dashboard/test_routes/test_predictions.py`
  - [x] 5.2 测试 `GET /api/predictions` 返回预测列表
  - [x] 5.3 测试 `GET /api/predictions` 分页功能
  - [x] 5.4 测试 `GET /api/predictions/{id}` 返回预测详情
  - [x] 5.5 测试 `GET /api/predictions/{id}` 404 处理
  - [x] 5.6 测试 `GET /api/predictions/accuracy` 返回准确率统计
  - [x] 5.7 创建 `tests/test_dashboard/test_routes/test_statistics.py`
  - [x] 5.8 测试 `GET /api/statistics/overview` 返回概览
  - [x] 5.9 测试 `GET /api/statistics/daily` 返回每日统计
  - [x] 5.10 测试 `GET /api/statistics/performance` 返回图表数据
  - [x] 5.11 测试响应格式符合规范

- [x] Task 6: 代码质量检查 (AC: All)
  - [x] 6.1 运行 `mypy src/dashboard/routes/predictions.py` 无错误
  - [x] 6.2 运行 `mypy src/dashboard/routes/statistics.py` 无错误
  - [x] 6.3 运行 `black --check` 通过
  - [x] 6.4 运行 `isort --check` 通过
  - [x] 6.5 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md, epics.md]

**API 端点规范:**

| 端点 | 方法 | 描述 | 响应类型 |
|------|------|------|----------|
| `/api/predictions` | GET | 获取预测列表 | `PaginatedResponse[PredictionListItem]` |
| `/api/predictions/{prediction_id}` | GET | 获取预测详情 | `ApiResponse[PredictionResponse]` |
| `/api/predictions/accuracy` | GET | 获取准确率统计 | `ApiResponse[AccuracyStats]` |
| `/api/statistics/overview` | GET | 获取系统概览 | `ApiResponse[OverviewStats]` |
| `/api/statistics/daily` | GET | 获取每日统计 | `PaginatedResponse[DailyStatsItem]` |
| `/api/statistics/performance` | GET | 获取图表数据 | `ApiResponse[PerformanceData]` |

**查询参数 (预测列表):**

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `page` | int | 1 | 页码 (从 1 开始) |
| `per_page` | int | 20 | 每页数量 (最大 100) |
| `validated` | bool | None | 筛选已验证/未验证 |

**响应格式规范 [Source: architecture.md#API Response Format]:**

```json
// 预测列表响应 (分页)
{
  "success": true,
  "data": [
    {
      "id": 1,
      "market_id": "btc-100k-2026",
      "predicted_probability": 0.75,
      "confidence": 0.85,
      "recommendation": "BUY_YES",
      "actual_outcome": null,
      "is_correct": null,
      "created_at": "2026-02-15T10:30:00Z"
    }
  ],
  "meta": {
    "total": 50,
    "page": 1,
    "per_page": 20
  }
}

// 准确率统计响应
{
  "success": true,
  "data": {
    "total_predictions": 100,
    "validated_predictions": 50,
    "correct_predictions": 35,
    "accuracy": 0.70,
    "avg_confidence": 0.82,
    "by_category": {
      "politics": {"total": 20, "correct": 15, "accuracy": 0.75},
      "crypto": {"total": 15, "correct": 10, "accuracy": 0.67}
    }
  }
}

// 系统概览响应
{
  "success": true,
  "data": {
    "current_capital": 180.50,
    "initial_capital": 200.00,
    "total_pnl": -19.50,
    "total_pnl_pct": -0.0975,
    "win_rate": 0.65,
    "total_trades": 20,
    "winning_trades": 13,
    "losing_trades": 7,
    "open_positions": 2,
    "trading_enabled": true,
    "mode": "PAPER"
  }
}

// 每日统计响应 (分页)
{
  "success": true,
  "data": [
    {
      "date": "2026-02-15",
      "starting_capital": 200.00,
      "ending_capital": 195.50,
      "total_pnl": -4.50,
      "total_trades": 3,
      "winning_trades": 1,
      "losing_trades": 2,
      "win_rate": 0.33
    }
  ],
  "meta": {
    "total": 30,
    "page": 1,
    "per_page": 20
  }
}

// 图表数据响应
{
  "success": true,
  "data": {
    "capital_history": [
      {"date": "2026-02-01", "capital": 200.00},
      {"date": "2026-02-02", "capital": 205.50}
    ],
    "win_rate_history": [
      {"date": "2026-02-01", "win_rate": 0.50},
      {"date": "2026-02-02", "win_rate": 0.67}
    ],
    "trades_by_day": [
      {"date": "2026-02-01", "count": 2},
      {"date": "2026-02-02", "count": 3}
    ]
  }
}

// 错误响应 (预测不存在)
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Prediction not found: 999"
  }
}
```

### 已有组件 (必须复用)

**Prediction 模型** [Source: src/models/prediction.py]
```python
class Prediction(BaseModel):
    id: int
    market_id: str
    predicted_probability: float  # 0-1
    confidence: float  # 0-1
    reasoning: str | None
    key_assumptions: list[str] | None
    model_used: str | None
    recommendation: str | None  # BUY_YES/BUY_NO/NO_TRADE
    actual_outcome: str | None  # YES/NO (市场结算后)
    is_correct: bool | None  # 预测是否正确
    validated_at: datetime | None
    created_at: datetime | None
```

**Statistics 模型** [Source: src/models/statistics.py]
```python
class Statistics(BaseModel):
    id: int
    date: date
    mode: TradeMode  # PAPER/LIVE
    starting_capital: float
    ending_capital: float | None
    total_pnl: float | None
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float | None
    created_at: datetime | None
```

**PredictionRepository** [Source: src/storage/repositories/prediction_repo.py]
```python
class PredictionRepository:
    async def get_by_id(self, prediction_id: int) -> Prediction | None: ...
    async def get_by_market(self, market_id: str) -> list[Prediction]: ...
    async def get_predictions_with_outcome(self, status: str | None = None) -> list[Prediction]: ...
    async def get_correct_predictions(self) -> list[Prediction]: ...
    async def get_incorrect_predictions(self) -> list[Prediction]: ...
    async def get_predictions_by_confidence_range(self, min_conf: float, max_conf: float) -> list[Prediction]: ...
    async def get_all(self, limit: int = 100) -> list[Prediction]: ...
    async def count(self) -> int: ...
```

**StatisticsRepository** [Source: src/storage/repositories/statistics_repo.py]
```python
class StatisticsRepository:
    async def get_by_date(self, date: date) -> Statistics | None: ...
    async def get_by_date_range(self, start_date: date, end_date: date) -> list[Statistics]: ...
    async def get_latest(self) -> Statistics | None: ...
    async def get_all(self, limit: int = 100) -> list[Statistics]: ...
    async def save(self, stats: Statistics) -> Statistics: ...
```

**ThreadSafeState** [Source: src/core/state.py]
```python
class ThreadSafeState:
    def get_state(self) -> StateSnapshot: ...
    # 返回: current_capital, daily_pnl, consecutive_losses, open_positions_count, trading_enabled, reduced_mode
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

**src/models/prediction_response.py:**

```python
"""Prediction API response models.

This module defines Pydantic models for prediction API responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer


class PredictionListItem(BaseModel):
    """Prediction list item for API list responses.

    Contains prediction fields for list display.

    Attributes:
        id: Prediction unique identifier
        market_id: Reference to the market
        predicted_probability: Predicted probability (0-1)
        confidence: LLM confidence (0-1)
        recommendation: Trade recommendation
        actual_outcome: Actual market outcome (if resolved)
        is_correct: Whether prediction was correct (if validated)
        created_at: Prediction creation timestamp
    """

    id: int = Field(..., description="Prediction ID")
    market_id: str = Field(..., description="Market reference")
    predicted_probability: float = Field(..., description="Predicted probability (0-1)")
    confidence: float = Field(..., description="LLM confidence (0-1)")
    recommendation: str | None = Field(None, description="Trade recommendation")
    actual_outcome: str | None = Field(None, description="Actual outcome")
    is_correct: bool | None = Field(None, description="Prediction correctness")
    created_at: datetime | None = Field(None, description="Creation timestamp")

    @field_serializer("created_at")
    def serialize_datetime(self, dt: datetime | None, _info: Any) -> str | None:
        """Serialize datetime to ISO 8601 format."""
        if dt is None:
            return None
        return dt.isoformat()


class PredictionResponse(BaseModel):
    """Full prediction details for API detail responses.

    Contains all prediction fields for detailed view.

    Attributes:
        id: Prediction unique identifier
        market_id: Reference to the market
        predicted_probability: Predicted probability (0-1)
        confidence: LLM confidence (0-1)
        reasoning: LLM analysis reasoning
        key_assumptions: Key assumptions made
        model_used: LLM model used
        recommendation: Trade recommendation
        actual_outcome: Actual market outcome (if resolved)
        is_correct: Whether prediction was correct (if validated)
        validated_at: Validation timestamp
        created_at: Prediction creation timestamp
    """

    id: int = Field(..., description="Prediction ID")
    market_id: str = Field(..., description="Market reference")
    predicted_probability: float = Field(..., description="Predicted probability (0-1)")
    confidence: float = Field(..., description="LLM confidence (0-1)")
    reasoning: str | None = Field(None, description="Analysis reasoning")
    key_assumptions: list[str] | None = Field(None, description="Key assumptions")
    model_used: str | None = Field(None, description="LLM model")
    recommendation: str | None = Field(None, description="Trade recommendation")
    actual_outcome: str | None = Field(None, description="Actual outcome")
    is_correct: bool | None = Field(None, description="Prediction correctness")
    validated_at: datetime | None = Field(None, description="Validation timestamp")
    created_at: datetime | None = Field(None, description="Creation timestamp")

    @field_serializer("validated_at", "created_at")
    def serialize_datetime(self, dt: datetime | None, _info: Any) -> str | None:
        """Serialize datetime to ISO 8601 format."""
        if dt is None:
            return None
        return dt.isoformat()


class CategoryAccuracy(BaseModel):
    """Accuracy statistics for a category.

    Attributes:
        total: Total predictions in category
        correct: Correct predictions
        accuracy: Accuracy rate (0-1)
    """

    total: int = Field(..., description="Total predictions")
    correct: int = Field(..., description="Correct predictions")
    accuracy: float = Field(..., description="Accuracy rate (0-1)")


class AccuracyStats(BaseModel):
    """Overall prediction accuracy statistics.

    Attributes:
        total_predictions: Total number of predictions
        validated_predictions: Number of validated predictions
        correct_predictions: Number of correct predictions
        accuracy: Overall accuracy rate (0-1)
        avg_confidence: Average confidence across all predictions
        by_category: Accuracy breakdown by category
    """

    total_predictions: int = Field(..., description="Total predictions")
    validated_predictions: int = Field(..., description="Validated predictions")
    correct_predictions: int = Field(..., description="Correct predictions")
    accuracy: float = Field(..., description="Overall accuracy (0-1)")
    avg_confidence: float = Field(..., description="Average confidence")
    by_category: dict[str, CategoryAccuracy] = Field(
        default_factory=dict, description="Accuracy by category"
    )


__all__ = ["PredictionListItem", "PredictionResponse", "CategoryAccuracy", "AccuracyStats"]
```

**src/models/statistics_response.py:**

```python
"""Statistics API response models.

This module defines Pydantic models for statistics API responses.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_serializer


class OverviewStats(BaseModel):
    """System overview statistics.

    Aggregated view of trading system status and performance.

    Attributes:
        current_capital: Current capital in USD
        initial_capital: Starting capital in USD
        total_pnl: Total profit/loss in USD
        total_pnl_pct: Total profit/loss as percentage
        win_rate: Overall win rate (0-1)
        total_trades: Total number of trades
        winning_trades: Number of winning trades
        losing_trades: Number of losing trades
        open_positions: Number of open positions
        trading_enabled: Whether trading is enabled
        mode: Current trading mode
    """

    current_capital: float = Field(..., description="Current capital (USD)")
    initial_capital: float = Field(..., description="Initial capital (USD)")
    total_pnl: float = Field(..., description="Total P&L (USD)")
    total_pnl_pct: float = Field(..., description="Total P&L percentage")
    win_rate: float = Field(..., description="Win rate (0-1)")
    total_trades: int = Field(..., description="Total trades")
    winning_trades: int = Field(..., description="Winning trades")
    losing_trades: int = Field(..., description="Losing trades")
    open_positions: int = Field(..., description="Open positions count")
    trading_enabled: bool = Field(..., description="Trading enabled")
    mode: str = Field(..., description="Trading mode (PAPER/LIVE)")


class DailyStatsItem(BaseModel):
    """Daily statistics item for API list responses.

    Contains statistics for a single trading day.

    Attributes:
        date: Trading date
        starting_capital: Capital at start of day
        ending_capital: Capital at end of day
        total_pnl: Daily profit/loss
        total_trades: Number of trades
        winning_trades: Number of winning trades
        losing_trades: Number of losing trades
        win_rate: Daily win rate (0-1)
    """

    date: date = Field(..., description="Trading date")
    starting_capital: float = Field(..., description="Starting capital (USD)")
    ending_capital: float | None = Field(None, description="Ending capital (USD)")
    total_pnl: float | None = Field(None, description="Daily P&L (USD)")
    total_trades: int = Field(..., description="Total trades")
    winning_trades: int = Field(..., description="Winning trades")
    losing_trades: int = Field(..., description="Losing trades")
    win_rate: float | None = Field(None, description="Win rate (0-1)")

    @field_serializer("date")
    def serialize_date(self, d: date, _info: Any) -> str:
        """Serialize date to ISO format."""
        return d.isoformat()


class CapitalHistoryPoint(BaseModel):
    """Capital history data point.

    Attributes:
        date: Date of data point
        capital: Capital value
    """

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    capital: float = Field(..., description="Capital (USD)")


class WinRateHistoryPoint(BaseModel):
    """Win rate history data point.

    Attributes:
        date: Date of data point
        win_rate: Cumulative win rate
    """

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    win_rate: float = Field(..., description="Win rate (0-1)")


class TradesByDayPoint(BaseModel):
    """Trades by day data point.

    Attributes:
        date: Date of data point
        count: Number of trades
    """

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    count: int = Field(..., description="Trade count")


class PerformanceData(BaseModel):
    """Performance data for charts.

    Contains time series data for dashboard visualizations.

    Attributes:
        capital_history: Capital over time
        win_rate_history: Win rate over time
        trades_by_day: Trade count by day
    """

    capital_history: list[CapitalHistoryPoint] = Field(
        default_factory=list, description="Capital history"
    )
    win_rate_history: list[WinRateHistoryPoint] = Field(
        default_factory=list, description="Win rate history"
    )
    trades_by_day: list[TradesByDayPoint] = Field(
        default_factory=list, description="Trades by day"
    )


__all__ = [
    "OverviewStats",
    "DailyStatsItem",
    "CapitalHistoryPoint",
    "WinRateHistoryPoint",
    "TradesByDayPoint",
    "PerformanceData",
]
```

### 实现模板

**src/dashboard/routes/predictions.py:**

```python
"""Prediction data API routes.

This module provides REST API endpoints for prediction operations.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.models.api_response import ApiResponse, ErrorCode, PaginatedResponse, PaginationMeta
from src.models.prediction_response import AccuracyStats, CategoryAccuracy, PredictionListItem, PredictionResponse
from src.storage.repositories.prediction_repo import PredictionRepository

logger = logging.getLogger(__name__)

router = APIRouter()


def get_prediction_repository() -> PredictionRepository:
    """Get PredictionRepository instance.

    Returns:
        PredictionRepository instance
    """
    return PredictionRepository()


@router.get("", response_model=PaginatedResponse[PredictionListItem])
async def list_predictions(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    validated: Annotated[bool | None, Query(description="Filter by validation status")] = None,
    repo: PredictionRepository = Depends(get_prediction_repository),
) -> PaginatedResponse[PredictionListItem]:
    """Get prediction history with pagination and filtering.

    Args:
        page: Page number (1-based)
        per_page: Items per page (max 100)
        validated: Filter by validation status
        repo: PredictionRepository dependency

    Returns:
        Paginated list of predictions
    """
    logger.info(f"📊 Listing predictions: page={page}, per_page={per_page}, validated={validated}")

    # Get predictions based on filter
    if validated is True:
        predictions = await repo.get_predictions_with_outcome(status="validated")
    elif validated is False:
        predictions = await repo.get_predictions_with_outcome(status="pending")
    else:
        predictions = await repo.get_all(limit=1000)

    # Calculate pagination
    total = len(predictions)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_predictions = predictions[start:end]

    # Convert to response models
    items = [
        PredictionListItem(
            id=p.id,
            market_id=p.market_id,
            predicted_probability=p.predicted_probability,
            confidence=p.confidence,
            recommendation=p.recommendation,
            actual_outcome=p.actual_outcome,
            is_correct=p.is_correct,
            created_at=p.created_at,
        )
        for p in paginated_predictions
    ]

    return PaginatedResponse(
        success=True,
        data=items,
        meta=PaginationMeta(total=total, page=page, per_page=per_page),
    )


@router.get("/accuracy", response_model=ApiResponse[AccuracyStats])
async def get_accuracy(
    repo: PredictionRepository = Depends(get_prediction_repository),
) -> ApiResponse[AccuracyStats]:
    """Get prediction accuracy statistics.

    Args:
        repo: PredictionRepository dependency

    Returns:
        Accuracy statistics
    """
    logger.info("📊 Getting prediction accuracy statistics")

    # Get all predictions
    all_predictions = await repo.get_all(limit=10000)

    # Calculate statistics
    total = len(all_predictions)
    validated = [p for p in all_predictions if p.is_correct is not None]
    correct = [p for p in validated if p.is_correct is True]

    validated_count = len(validated)
    correct_count = len(correct)
    accuracy = correct_count / validated_count if validated_count > 0 else 0.0
    avg_confidence = sum(p.confidence for p in all_predictions) / total if total > 0 else 0.0

    # TODO: Calculate by_category when market categories are available
    by_category: dict[str, CategoryAccuracy] = {}

    stats = AccuracyStats(
        total_predictions=total,
        validated_predictions=validated_count,
        correct_predictions=correct_count,
        accuracy=accuracy,
        avg_confidence=avg_confidence,
        by_category=by_category,
    )

    return ApiResponse(success=True, data=stats)


@router.get("/{prediction_id}", response_model=ApiResponse[PredictionResponse])
async def get_prediction(
    prediction_id: int,
    repo: PredictionRepository = Depends(get_prediction_repository),
) -> ApiResponse[PredictionResponse]:
    """Get prediction details by ID.

    Args:
        prediction_id: Prediction ID
        repo: PredictionRepository dependency

    Returns:
        Prediction details

    Raises:
        HTTPException: If prediction not found
    """
    logger.info(f"📊 Getting prediction: {prediction_id}")

    prediction = await repo.get_by_id(prediction_id)

    if prediction is None:
        logger.warning(f"📊 Prediction not found: {prediction_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": ErrorCode.NOT_FOUND,
                    "message": f"Prediction not found: {prediction_id}",
                },
            },
        )

    response = PredictionResponse(
        id=prediction.id,
        market_id=prediction.market_id,
        predicted_probability=prediction.predicted_probability,
        confidence=prediction.confidence,
        reasoning=prediction.reasoning,
        key_assumptions=prediction.key_assumptions,
        model_used=prediction.model_used,
        recommendation=prediction.recommendation,
        actual_outcome=prediction.actual_outcome,
        is_correct=prediction.is_correct,
        validated_at=prediction.validated_at,
        created_at=prediction.created_at,
    )

    return ApiResponse(success=True, data=response)


__all__ = ["router"]
```

**src/dashboard/routes/statistics.py:**

```python
"""Statistics API routes.

This module provides REST API endpoints for statistics operations.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.config import settings
from src.core.state import ThreadSafeState
from src.models.api_response import ApiResponse, PaginatedResponse, PaginationMeta
from src.models.statistics_response import (
    CapitalHistoryPoint,
    DailyStatsItem,
    PerformanceData,
    OverviewStats,
    TradesByDayPoint,
    WinRateHistoryPoint,
)
from src.storage.repositories.position_repo import PositionRepository
from src.storage.repositories.statistics_repo import StatisticsRepository
from src.storage.repositories.trade_repo import TradeRepository

logger = logging.getLogger(__name__)

router = APIRouter()


def get_statistics_repository() -> StatisticsRepository:
    """Get StatisticsRepository instance.

    Returns:
        StatisticsRepository instance
    """
    return StatisticsRepository()


def get_trade_repository() -> TradeRepository:
    """Get TradeRepository instance.

    Returns:
        TradeRepository instance
    """
    return TradeRepository()


def get_position_repository() -> PositionRepository:
    """Get PositionRepository instance.

    Returns:
        PositionRepository instance
    """
    return PositionRepository()


def get_state() -> ThreadSafeState:
    """Get ThreadSafeState instance.

    Returns:
        ThreadSafeState instance
    """
    # Note: In production, this should be a singleton or injected
    return ThreadSafeState()


@router.get("/overview", response_model=ApiResponse[OverviewStats])
async def get_overview(
    stats_repo: StatisticsRepository = Depends(get_statistics_repository),
    trade_repo: TradeRepository = Depends(get_trade_repository),
    position_repo: PositionRepository = Depends(get_position_repository),
    state: ThreadSafeState = Depends(get_state),
) -> ApiResponse[OverviewStats]:
    """Get system overview statistics.

    Aggregates data from multiple sources for dashboard overview.

    Args:
        stats_repo: StatisticsRepository dependency
        trade_repo: TradeRepository dependency
        position_repo: PositionRepository dependency
        state: ThreadSafeState dependency

    Returns:
        System overview statistics
    """
    logger.info("📊 Getting system overview statistics")

    # Get current state
    state_snapshot = state.get_state()

    # Get all trades for statistics
    all_trades = await trade_repo.get_recent(limit=10000)
    total_trades = len(all_trades)

    # Calculate win/loss counts
    # Note: This is simplified - in production, you'd calculate from trade results
    winning_trades = sum(1 for t in all_trades if t.status == "FILLED")  # Placeholder
    losing_trades = total_trades - winning_trades
    win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

    # Get open positions count
    open_positions = await position_repo.get_open_positions()
    open_positions_count = len(open_positions)

    # Calculate P&L
    initial_capital = settings.INITIAL_CAPITAL
    current_capital = state_snapshot.current_capital
    total_pnl = current_capital - initial_capital
    total_pnl_pct = total_pnl / initial_capital if initial_capital > 0 else 0.0

    overview = OverviewStats(
        current_capital=current_capital,
        initial_capital=initial_capital,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        win_rate=win_rate,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        open_positions=open_positions_count,
        trading_enabled=state_snapshot.trading_enabled,
        mode="PAPER",  # From config or state
    )

    return ApiResponse(success=True, data=overview)


@router.get("/daily", response_model=PaginatedResponse[DailyStatsItem])
async def get_daily_stats(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    repo: StatisticsRepository = Depends(get_statistics_repository),
) -> PaginatedResponse[DailyStatsItem]:
    """Get daily statistics with pagination.

    Args:
        page: Page number (1-based)
        per_page: Items per page (max 100)
        repo: StatisticsRepository dependency

    Returns:
        Paginated daily statistics
    """
    logger.info(f"📊 Getting daily statistics: page={page}, per_page={per_page}")

    # Get all daily stats
    all_stats = await repo.get_all(limit=1000)

    # Sort by date descending
    all_stats.sort(key=lambda s: s.date, reverse=True)

    # Calculate pagination
    total = len(all_stats)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_stats = all_stats[start:end]

    # Convert to response models
    items = [
        DailyStatsItem(
            date=s.date,
            starting_capital=s.starting_capital,
            ending_capital=s.ending_capital,
            total_pnl=s.total_pnl,
            total_trades=s.total_trades,
            winning_trades=s.winning_trades,
            losing_trades=s.losing_trades,
            win_rate=s.win_rate,
        )
        for s in paginated_stats
    ]

    return PaginatedResponse(
        success=True,
        data=items,
        meta=PaginationMeta(total=total, page=page, per_page=per_page),
    )


@router.get("/performance", response_model=ApiResponse[PerformanceData])
async def get_performance(
    days: Annotated[int, Query(ge=1, le=365, description="Number of days")] = 30,
    repo: StatisticsRepository = Depends(get_statistics_repository),
) -> ApiResponse[PerformanceData]:
    """Get performance data for charts.

    Args:
        days: Number of days to include
        repo: StatisticsRepository dependency

    Returns:
        Performance data for visualizations
    """
    logger.info(f"📊 Getting performance data: days={days}")

    # Get date range
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Get stats for date range
    stats = await repo.get_by_date_range(start_date, end_date)

    # Build time series data
    capital_history: list[CapitalHistoryPoint] = []
    win_rate_history: list[WinRateHistoryPoint] = []
    trades_by_day: list[TradesByDayPoint] = []

    # Create a lookup by date
    stats_by_date = {s.date: s for s in stats}

    # Fill in all dates in range
    current_date = start_date
    cumulative_trades = 0
    cumulative_wins = 0

    while current_date <= end_date:
        date_str = current_date.isoformat()

        if current_date in stats_by_date:
            s = stats_by_date[current_date]
            capital_history.append(
                CapitalHistoryPoint(
                    date=date_str,
                    capital=s.ending_capital or s.starting_capital,
                )
            )
            trades_by_day.append(
                TradesByDayPoint(
                    date=date_str,
                    count=s.total_trades,
                )
            )
            cumulative_trades += s.total_trades
            cumulative_wins += s.winning_trades
            cumulative_win_rate = cumulative_wins / cumulative_trades if cumulative_trades > 0 else 0.0
            win_rate_history.append(
                WinRateHistoryPoint(
                    date=date_str,
                    win_rate=cumulative_win_rate,
                )
            )
        else:
            # No data for this date, use previous day's values
            if capital_history:
                capital_history.append(
                    CapitalHistoryPoint(
                        date=date_str,
                        capital=capital_history[-1].capital,
                    )
                )
            if win_rate_history:
                win_rate_history.append(
                    WinRateHistoryPoint(
                        date=date_str,
                        win_rate=win_rate_history[-1].win_rate,
                    )
                )
            trades_by_day.append(
                TradesByDayPoint(
                    date=date_str,
                    count=0,
                )
            )

        current_date += timedelta(days=1)

    performance = PerformanceData(
        capital_history=capital_history,
        win_rate_history=win_rate_history,
        trades_by_day=trades_by_day,
    )

    return ApiResponse(success=True, data=performance)


__all__ = ["router"]
```

### 项目结构 [Source: architecture.md#Project Structure]

**新增/修改文件:**
```
src/
├── models/
│   ├── prediction_response.py   # 新增: 预测 API 响应模型
│   ├── statistics_response.py   # 新增: 统计 API 响应模型
│   └── __init__.py              # 更新: 导出新模型
└── dashboard/
    └── routes/
        ├── predictions.py       # 更新: 实现端点
        └── statistics.py        # 更新: 实现端点

tests/
└── test_dashboard/
    └── test_routes/
        ├── test_predictions.py  # 新增: 预测路由测试
        └── test_statistics.py   # 新增: 统计路由测试
```

### 依赖关系

**本故事依赖:**
- Story 7.1: FastAPI 应用初始化 (已完成 - app.py, dependencies.py, api_response.py)
- Story 7.2: 市场数据 API (已完成 - 参考 markets.py 实现模式)
- Story 7.3: 持仓与交易 API (已完成 - 参考实现模式)
- Epic 3: LLM 智能分析引擎 (已完成 - Prediction, PredictionRepository)
- Epic 4: 风险控制与熔断系统 (已完成 - ThreadSafeState)
- Epic 5: Paper Trading 模拟交易 (已完成 - Statistics, StatisticsRepository)

**后续故事依赖本故事:**
- Story 7.5: 系统状态 API (参考本故事实现模式)
- Story 7.6: 前端 API 集成 (使用本故事的端点)

### 前一个故事学习 [Source: 7-3-position-and-trade-api.md]

**从 Story 7.3 学到的模式:**

1. **响应模型分离** - API 响应模型与数据库模型分离
2. **依赖注入** - 使用 FastAPI Depends 注入 Repository
3. **统一错误处理** - 使用 HTTPException 返回统一错误格式
4. **日志标准化** - 使用 emoji 标记日志 (📊 预测/统计)
5. **类型注解** - 使用 Annotated 类型提供 OpenAPI 文档
6. **分页响应** - 使用 PaginatedResponse 包装列表数据

### 实现注意事项

**关键点:**

1. **预测准确率计算** - 只计算已验证的预测 (is_correct is not None)
2. **概览统计聚合** - 需要从多个来源聚合数据
3. **图表数据填充** - 日期范围内无数据的日期需要填充
4. **路由顺序** - `/accuracy` 必须在 `/{prediction_id}` 之前定义
5. **ThreadSafeState** - 用于获取当前运行状态 (capital, trading_enabled)

**性能考虑:**

- NFR4 要求响应时间 < 2 秒
- 预测列表可能有大量数据，需要分页
- 统计计算可能涉及聚合，注意优化
- 图表数据限制最大天数 (365天)

**日志级别:**

| 级别 | 场景 | Emoji |
|------|------|-------|
| INFO | 列表查询 | 📊 |
| INFO | 详情查询 | 📊 |
| INFO | 统计计算 | 📊 |
| WARNING | 预测不存在 | 📊 |

### 测试策略

```python
# tests/test_dashboard/test_routes/test_predictions.py
"""Tests for prediction API routes."""

import pytest
from fastapi.testclient import TestClient

from src.dashboard.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestListPredictions:
    """测试预测列表端点."""

    def test_list_predictions_returns_200(self, client: TestClient) -> None:
        """测试列表返回 200."""
        response = client.get("/api/predictions")
        assert response.status_code == 200

    def test_list_predictions_format(self, client: TestClient) -> None:
        """测试响应格式."""
        response = client.get("/api/predictions")
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "meta" in data
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_list_predictions_pagination(self, client: TestClient) -> None:
        """测试分页功能."""
        response = client.get("/api/predictions?page=1&per_page=10")
        data = response.json()
        assert data["meta"]["page"] == 1
        assert data["meta"]["per_page"] == 10


class TestGetPrediction:
    """测试预测详情端点."""

    def test_get_prediction_404(self, client: TestClient) -> None:
        """测试预测不存在返回 404."""
        response = client.get("/api/predictions/99999")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "NOT_FOUND"


class TestGetAccuracy:
    """测试准确率统计端点."""

    def test_get_accuracy_returns_200(self, client: TestClient) -> None:
        """测试准确率返回 200."""
        response = client.get("/api/predictions/accuracy")
        assert response.status_code == 200

    def test_get_accuracy_format(self, client: TestClient) -> None:
        """测试响应格式."""
        response = client.get("/api/predictions/accuracy")
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "total_predictions" in data["data"]
        assert "accuracy" in data["data"]


# tests/test_dashboard/test_routes/test_statistics.py
"""Tests for statistics API routes."""


class TestGetOverview:
    """测试系统概览端点."""

    def test_get_overview_returns_200(self, client: TestClient) -> None:
        """测试概览返回 200."""
        response = client.get("/api/statistics/overview")
        assert response.status_code == 200

    def test_get_overview_format(self, client: TestClient) -> None:
        """测试响应格式."""
        response = client.get("/api/statistics/overview")
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "current_capital" in data["data"]
        assert "total_pnl" in data["data"]
        assert "win_rate" in data["data"]


class TestGetDailyStats:
    """测试每日统计端点."""

    def test_get_daily_stats_returns_200(self, client: TestClient) -> None:
        """测试每日统计返回 200."""
        response = client.get("/api/statistics/daily")
        assert response.status_code == 200

    def test_get_daily_stats_pagination(self, client: TestClient) -> None:
        """测试分页功能."""
        response = client.get("/api/statistics/daily?page=1&per_page=10")
        data = response.json()
        assert "meta" in data


class TestGetPerformance:
    """测试图表数据端点."""

    def test_get_performance_returns_200(self, client: TestClient) -> None:
        """测试图表数据返回 200."""
        response = client.get("/api/statistics/performance")
        assert response.status_code == 200

    def test_get_performance_format(self, client: TestClient) -> None:
        """测试响应格式."""
        response = client.get("/api/statistics/performance")
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "capital_history" in data["data"]
        assert "win_rate_history" in data["data"]
        assert "trades_by_day" in data["data"]

    def test_get_performance_days_parameter(self, client: TestClient) -> None:
        """测试天数参数."""
        response = client.get("/api/statistics/performance?days=7")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["capital_history"]) <= 7
```

### 运行命令

```bash
# 启动开发服务器
uvicorn src.dashboard.app:app --reload --host 0.0.0.0 --port 8000

# 测试预测列表
curl http://localhost:8000/api/predictions

# 测试分页
curl "http://localhost:8000/api/predictions?page=1&per_page=10"

# 测试验证状态筛选
curl "http://localhost:8000/api/predictions?validated=true"

# 测试预测详情
curl http://localhost:8000/api/predictions/1

# 测试准确率统计
curl http://localhost:8000/api/predictions/accuracy

# 测试系统概览
curl http://localhost:8000/api/statistics/overview

# 测试每日统计
curl http://localhost:8000/api/statistics/daily

# 测试图表数据
curl "http://localhost:8000/api/statistics/performance?days=30"

# 查看 API 文档
open http://localhost:8000/docs

# 运行测试
pytest tests/test_dashboard/test_routes/test_predictions.py -v
pytest tests/test_dashboard/test_routes/test_statistics.py -v
```

### References

- [Source: architecture.md#API Response Format] - 统一响应格式规范
- [Source: architecture.md#Database Schema] - predictions 和 statistics 表结构
- [Source: epics.md#Story 7.4] - 原始 Story 定义
- [Source: src/models/prediction.py] - Prediction 数据模型
- [Source: src/models/statistics.py] - Statistics 数据模型
- [Source: src/models/api_response.py] - API 响应模型
- [Source: src/storage/repositories/prediction_repo.py] - PredictionRepository 实现
- [Source: src/storage/repositories/statistics_repo.py] - StatisticsRepository 实现
- [Source: src/core/state.py] - ThreadSafeState 实现
- [Source: 7-3-position-and-trade-api.md] - 前一个故事实现参考

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

N/A

### Completion Notes List

1. 2026-02-17: 初始实现完成 - 所有 API 端点和测试通过 (28/28 tests)
2. 2026-02-17: 代码审查修复 - 修复 ThreadSafeState 单例问题，使用 `get_state_manager()` 获取单例实例

### File List

| File | Status | Description |
|------|--------|-------------|
| `src/models/prediction_response.py` | 新增 | 预测 API 响应模型 |
| `src/models/statistics_response.py` | 新增 | 统计 API 响应模型 |
| `src/models/__init__.py` | 更新 | 导出新模型 |
| `src/dashboard/routes/predictions.py` | 新增 | 预测 API 路由 |
| `src/dashboard/routes/statistics.py` | 新增/修复 | 统计 API 路由 (修复单例问题) |
| `tests/test_dashboard/test_routes/test_predictions.py` | 新增 | 预测路由测试 (14 tests) |
| `tests/test_dashboard/test_routes/test_statistics.py` | 新增 | 统计路由测试 (14 tests) |
