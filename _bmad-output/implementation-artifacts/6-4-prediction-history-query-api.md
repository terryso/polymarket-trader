# Story 6.4: 预测历史查询 API

Status: ready-for-dev

## Story

As a **开发者**,
I want **提供预测历史的查询接口**,
So that **Dashboard 可以展示预测数据**.

## Acceptance Criteria

**Given** 预测追踪已实现 (Story 6.1, Story 6.2)
**When** 扩展 `src/storage/repositories/prediction_repo.py`
**Then** 添加查询方法:
- `get_predictions_with_outcome(status)` - 获取带结果的预测
- `get_correct_predictions()` - 获取正确预测
- `get_incorrect_predictions()` - 获取错误预测
- `get_predictions_by_confidence_range(min, max)` - 按置信度范围查询

**And** 支持分页参数 (page, per_page)
**And** 支持排序 (按日期、置信度、准确率)
**And** 返回包含关联市场信息

## Tasks / Subtasks

- [ ] Task 1: 定义分页和排序数据模型 (AC: 2, 3)
  - [ ] 1.1 创建 `PaginationParams` 数据类 (page, per_page)
  - [ ] 1.2 创建 `SortParams` 数据类 (sort_by, sort_order)
  - [ ] 1.3 创建 `PredictionQueryResult` 数据类 (predictions, total, page, per_page)
  - [ ] 1.4 更新 `__all__` 导出

- [ ] Task 2: 实现基础分页查询 (AC: 2)
  - [ ] 2.1 添加 `_apply_pagination()` 辅助方法
  - [ ] 2.2 添加 `_apply_sorting()` 辅助方法
  - [ ] 2.3 实现分页元数据返回 (total, has_next, has_prev)

- [ ] Task 3: 实现按结果状态查询 (AC: 1)
  - [ ] 3.1 实现 `get_predictions_with_outcome(status)` 方法
  - [ ] 3.2 status 支持: "correct", "incorrect", "pending", "all"
  - [ ] 3.3 添加日志记录 (📊 emoji)
  - [ ] 3.4 支持分页和排序

- [ ] Task 4: 实现便捷查询方法 (AC: 1)
  - [ ] 4.1 实现 `get_correct_predictions()` 方法
  - [ ] 4.2 实现 `get_incorrect_predictions()` 方法
  - [ ] 4.3 两者都支持分页和排序

- [ ] Task 5: 实现按置信度范围查询 (AC: 1)
  - [ ] 5.1 实现 `get_predictions_by_confidence_range(min, max)` 方法
  - [ ] 5.2 验证 min <= max 且在 0-1 范围内
  - [ ] 5.3 支持分页和排序
  - [ ] 5.4 返回包含关联市场信息

- [ ] Task 6: 实现带市场信息的查询 (AC: 4)
  - [ ] 6.1 扩展查询方法返回 `(Prediction, Market)` 元组
  - [ ] 6.2 复用 `_row_to_market()` 方法
  - [ ] 6.3 使用 JOIN 查询提高效率

- [ ] Task 7: 编写单元测试 (AC: All)
  - [ ] 7.1 扩展 `tests/test_storage/test_prediction_repo.py`
  - [ ] 7.2 测试 `get_predictions_with_outcome()` 各状态
  - [ ] 7.3 测试 `get_correct_predictions()` 方法
  - [ ] 7.4 测试 `get_incorrect_predictions()` 方法
  - [ ] 7.5 测试 `get_predictions_by_confidence_range()` 方法
  - [ ] 7.6 测试分页功能
  - [ ] 7.7 测试排序功能
  - [ ] 7.8 测试边界情况 (空结果、无效参数)
  - [ ] 7.9 Mock 所有外部依赖

- [ ] Task 8: 代码质量检查 (AC: All)
  - [ ] 8.1 运行 `mypy src/storage/repositories/prediction_repo.py` 无错误
  - [ ] 8.2 运行 `black --check` 通过
  - [ ] 8.3 运行 `isort --check` 通过
  - [ ] 8.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md, epics.md]

**预测历史查询流程:**

```
+---------------------------------------------------------------------+
|                   预测历史查询流程                                    |
+---------------------------------------------------------------------+
|                                                                     |
|  get_predictions_with_outcome(status, page, per_page, sort)         |
|                                                                     |
|  1. 构建 SQL 查询                                                   |
|     SELECT p.*, m.title, m.category, ...                            |
|     FROM predictions p                                              |
|     JOIN markets m ON p.market_id = m.id                            |
|                                                                     |
|  2. 应用状态过滤                                                    |
|     WHERE p.is_correct = TRUE  (status = "correct")                 |
|     WHERE p.is_correct = FALSE (status = "incorrect")               |
|     WHERE p.validated_at IS NULL (status = "pending")               |
|                                                                     |
|  3. 应用排序                                                        |
|     ORDER BY p.created_at DESC (sort_by = "date", sort_order = "desc")|
|     ORDER BY p.confidence DESC (sort_by = "confidence")             |
|     ORDER BY p.is_correct ASC (sort_by = "accuracy")                |
|                                                                     |
|  4. 计算总数                                                        |
|     SELECT COUNT(*) FROM ...                                        |
|                                                                     |
|  5. 应用分页                                                        |
|     LIMIT per_page OFFSET (page - 1) * per_page                     |
|                                                                     |
|  6. 返回结果                                                        |
|     return PredictionQueryResult(                                   |
|         predictions=[(p, m), ...],                                  |
|         total=100,                                                  |
|         page=1,                                                     |
|         per_page=20                                                 |
|     )                                                               |
|                                                                     |
+---------------------------------------------------------------------+
```

### 已有组件 (必须复用)

**PredictionRepository** [Source: src/storage/repositories/prediction_repo.py]
```python
class PredictionRepository:
    # 已实现的方法:
    async def save_prediction(prediction, upsert=True) -> int
    async def get_predictions_by_market(market_id) -> list[Prediction]
    async def get_pending_predictions() -> list[Prediction]
    async def get_latest_prediction(market_id) -> Prediction | None
    async def update_prediction_result(prediction_id, actual_outcome, is_correct) -> bool

    # Story 6.1 新增:
    async def get_unvalidated_predictions() -> list[Prediction]
    async def get_validated_predictions() -> list[Prediction]

    # Story 6.2 新增:
    async def get_all_validated() -> list[Prediction]
    async def get_validated_by_date_range(start_date, end_date) -> list[Prediction]
    async def get_validated_with_market() -> list[tuple[Prediction, Market]]

    # 辅助方法:
    def _row_to_prediction(row) -> Prediction
    def _row_to_market(row) -> Market
```

**Prediction Model** [Source: src/models/prediction.py]
```python
class Prediction(BaseModel):
    id: int | None
    market_id: str
    predicted_probability: float  # 0-1
    confidence: float             # 0-1
    reasoning: str | None
    key_assumptions: list[str] | None
    model_used: str | None
    recommendation: Recommendation | None
    edge: float | None
    actual_outcome: str | None
    is_correct: bool | None
    validated_at: datetime | None
    created_at: datetime | None
```

**Market Model** [Source: src/models/market.py]
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
```

### 新增数据模型

**src/storage/repositories/prediction_repo.py (扩展):**

```python
from dataclasses import dataclass
from enum import Enum

class PredictionOutcomeStatus(str, Enum):
    """Status filter for prediction queries."""
    ALL = "all"
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PENDING = "pending"


class PredictionSortBy(str, Enum):
    """Sort field for prediction queries."""
    DATE = "date"            # created_at
    CONFIDENCE = "confidence"
    ACCURACY = "accuracy"    # is_correct


class SortOrder(str, Enum):
    """Sort order for queries."""
    ASC = "asc"
    DESC = "desc"


@dataclass
class PaginationParams:
    """Pagination parameters for queries.

    Attributes:
        page: Page number (1-indexed)
        per_page: Items per page
    """
    page: int = 1
    per_page: int = 20


@dataclass
class SortParams:
    """Sort parameters for queries.

    Attributes:
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
    """
    sort_by: PredictionSortBy = PredictionSortBy.DATE
    sort_order: SortOrder = SortOrder.DESC


@dataclass
class PredictionQueryResult:
    """Result of a prediction query with pagination.

    Attributes:
        predictions: List of (Prediction, Market) tuples
        total: Total number of matching records
        page: Current page number
        per_page: Items per page
        has_next: Whether there's a next page
        has_prev: Whether there's a previous page
    """
    predictions: list[tuple[Prediction, Market]]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool
```

### 实现模板

**src/storage/repositories/prediction_repo.py (新增方法):**

```python
from dataclasses import dataclass
from enum import Enum
from typing import Literal

# 更新 __all__
__all__ = [
    "PredictionRepository",
    "PredictionOutcomeStatus",
    "PredictionSortBy",
    "SortOrder",
    "PaginationParams",
    "SortParams",
    "PredictionQueryResult",
]


class PredictionOutcomeStatus(str, Enum):
    """Status filter for prediction queries."""
    ALL = "all"
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PENDING = "pending"


class PredictionSortBy(str, Enum):
    """Sort field for prediction queries."""
    DATE = "date"
    CONFIDENCE = "confidence"
    ACCURACY = "accuracy"


class SortOrder(str, Enum):
    """Sort order for queries."""
    ASC = "asc"
    DESC = "desc"


@dataclass
class PaginationParams:
    page: int = 1
    per_page: int = 20


@dataclass
class SortParams:
    sort_by: PredictionSortBy = PredictionSortBy.DATE
    sort_order: SortOrder = SortOrder.DESC


@dataclass
class PredictionQueryResult:
    predictions: list[tuple[Prediction, Market]]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class PredictionRepository:
    # ... 已有方法 ...

    # ==================== Story 6.4: 预测历史查询 API ====================

    def _get_sort_clause(self, sort: SortParams) -> str:
        """Build SQL ORDER BY clause from sort parameters.

        Args:
            sort: Sort parameters

        Returns:
            SQL ORDER BY clause string
        """
        sort_fields = {
            PredictionSortBy.DATE: "p.created_at",
            PredictionSortBy.CONFIDENCE: "p.confidence",
            PredictionSortBy.ACCURACY: "p.is_correct",
        }

        field = sort_fields.get(sort.sort_by, "p.created_at")
        order = "DESC" if sort.sort_order == SortOrder.DESC else "ASC"

        return f"ORDER BY {field} {order}"

    def _get_status_where_clause(
        self,
        status: PredictionOutcomeStatus,
    ) -> tuple[str, list]:
        """Build SQL WHERE clause for status filter.

        Args:
            status: Status filter

        Returns:
            Tuple of (where_clause, params)
        """
        if status == PredictionOutcomeStatus.CORRECT:
            return "WHERE p.is_correct = 1", []
        elif status == PredictionOutcomeStatus.INCORRECT:
            return "WHERE p.is_correct = 0", []
        elif status == PredictionOutcomeStatus.PENDING:
            return "WHERE p.validated_at IS NULL", []
        else:  # ALL
            return "", []

    async def get_predictions_with_outcome(
        self,
        status: PredictionOutcomeStatus | str = PredictionOutcomeStatus.ALL,
        pagination: PaginationParams | None = None,
        sort: SortParams | None = None,
    ) -> PredictionQueryResult:
        """Get predictions filtered by outcome status.

        Args:
            status: Filter by prediction outcome status
            pagination: Pagination parameters (default: page=1, per_page=20)
            sort: Sort parameters (default: date desc)

        Returns:
            PredictionQueryResult with predictions and pagination info

        Example:
            >>> result = await repo.get_predictions_with_outcome(
            ...     status="correct",
            ...     pagination=PaginationParams(page=1, per_page=10),
            ...     sort=SortParams(sort_by="confidence", sort_order="desc"),
            ... )
            >>> len(result.predictions)
            10
            >>> result.total
            45
        """
        if pagination is None:
            pagination = PaginationParams()
        if sort is None:
            sort = SortParams()

        # Normalize status
        if isinstance(status, str):
            status = PredictionOutcomeStatus(status.lower())

        from src.models.market import Market

        logger.info(
            f"{OPERATION_EMOJIS['data']} Querying predictions with status: "
            f"{status.value}, page={pagination.page}, per_page={pagination.per_page}"
        )

        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row

                # Build WHERE clause
                where_clause, where_params = self._get_status_where_clause(status)
                sort_clause = self._get_sort_clause(sort)

                # Get total count
                count_sql = f"""
                    SELECT COUNT(*) as total
                    FROM predictions p
                    {where_clause}
                """
                cursor = await conn.execute(count_sql, where_params)
                count_row = await cursor.fetchone()
                total = count_row["total"] if count_row else 0

                # Get paginated results with market info
                offset = (pagination.page - 1) * pagination.per_page
                query_sql = f"""
                    SELECT p.*, m.id as market_id_col, m.title, m.description,
                           m.category, m.yes_price, m.no_price, m.liquidity,
                           m.deadline, m.resolution_status, m.resolution_outcome,
                           m.created_at as market_created_at,
                           m.updated_at as market_updated_at
                    FROM predictions p
                    JOIN markets m ON p.market_id = m.id
                    {where_clause}
                    {sort_clause}
                    LIMIT ? OFFSET ?
                """
                cursor = await conn.execute(
                    query_sql,
                    where_params + [pagination.per_page, offset],
                )
                rows = await cursor.fetchall()

            # Convert rows to (Prediction, Market) tuples
            predictions: list[tuple[Prediction, Market]] = []
            for row in rows:
                prediction = self._row_to_prediction(row)
                market = self._row_to_market(row)
                predictions.append((prediction, market))

            # Calculate pagination info
            has_next = (pagination.page * pagination.per_page) < total
            has_prev = pagination.page > 1

            logger.info(
                f"{OPERATION_EMOJIS['data']} Found {len(predictions)} predictions "
                f"(total: {total})"
            )

            return PredictionQueryResult(
                predictions=predictions,
                total=total,
                page=pagination.page,
                per_page=pagination.per_page,
                has_next=has_next,
                has_prev=has_prev,
            )
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to query predictions: {e}"
            )
            raise

    async def get_correct_predictions(
        self,
        pagination: PaginationParams | None = None,
        sort: SortParams | None = None,
    ) -> PredictionQueryResult:
        """Get all correct predictions.

        Convenience method for get_predictions_with_outcome(status="correct").

        Args:
            pagination: Pagination parameters
            sort: Sort parameters

        Returns:
            PredictionQueryResult with correct predictions

        Example:
            >>> result = await repo.get_correct_predictions()
            >>> all(p.is_correct for p, m in result.predictions)
            True
        """
        return await self.get_predictions_with_outcome(
            status=PredictionOutcomeStatus.CORRECT,
            pagination=pagination,
            sort=sort,
        )

    async def get_incorrect_predictions(
        self,
        pagination: PaginationParams | None = None,
        sort: SortParams | None = None,
    ) -> PredictionQueryResult:
        """Get all incorrect predictions.

        Convenience method for get_predictions_with_outcome(status="incorrect").

        Args:
            pagination: Pagination parameters
            sort: Sort parameters

        Returns:
            PredictionQueryResult with incorrect predictions

        Example:
            >>> result = await repo.get_incorrect_predictions()
            >>> all(not p.is_correct for p, m in result.predictions)
            True
        """
        return await self.get_predictions_with_outcome(
            status=PredictionOutcomeStatus.INCORRECT,
            pagination=pagination,
            sort=sort,
        )

    async def get_predictions_by_confidence_range(
        self,
        min_confidence: float,
        max_confidence: float,
        pagination: PaginationParams | None = None,
        sort: SortParams | None = None,
    ) -> PredictionQueryResult:
        """Get predictions within a confidence range.

        Args:
            min_confidence: Minimum confidence (0-1, inclusive)
            max_confidence: Maximum confidence (0-1, inclusive)
            pagination: Pagination parameters
            sort: Sort parameters

        Returns:
            PredictionQueryResult with predictions in confidence range

        Raises:
            ValueError: If confidence values are invalid

        Example:
            >>> result = await repo.get_predictions_by_confidence_range(
            ...     min_confidence=0.8,
            ...     max_confidence=1.0,
            ... )
            >>> all(
            ...     0.8 <= p.confidence <= 1.0
            ...     for p, m in result.predictions
            ... )
            True
        """
        # Validate confidence range
        if not (0 <= min_confidence <= 1):
            raise ValueError(
                f"min_confidence must be between 0 and 1, got {min_confidence}"
            )
        if not (0 <= max_confidence <= 1):
            raise ValueError(
                f"max_confidence must be between 0 and 1, got {max_confidence}"
            )
        if min_confidence > max_confidence:
            raise ValueError(
                f"min_confidence ({min_confidence}) must be <= "
                f"max_confidence ({max_confidence})"
            )

        if pagination is None:
            pagination = PaginationParams()
        if sort is None:
            sort = SortParams()

        from src.models.market import Market

        logger.info(
            f"{OPERATION_EMOJIS['data']} Querying predictions with confidence: "
            f"[{min_confidence}, {max_confidence}]"
        )

        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row

                sort_clause = self._get_sort_clause(sort)

                # Get total count
                count_sql = """
                    SELECT COUNT(*) as total
                    FROM predictions p
                    WHERE p.confidence >= ? AND p.confidence <= ?
                """
                cursor = await conn.execute(
                    count_sql,
                    (min_confidence, max_confidence),
                )
                count_row = await cursor.fetchone()
                total = count_row["total"] if count_row else 0

                # Get paginated results with market info
                offset = (pagination.page - 1) * pagination.per_page
                query_sql = f"""
                    SELECT p.*, m.id as market_id_col, m.title, m.description,
                           m.category, m.yes_price, m.no_price, m.liquidity,
                           m.deadline, m.resolution_status, m.resolution_outcome,
                           m.created_at as market_created_at,
                           m.updated_at as market_updated_at
                    FROM predictions p
                    JOIN markets m ON p.market_id = m.id
                    WHERE p.confidence >= ? AND p.confidence <= ?
                    {sort_clause}
                    LIMIT ? OFFSET ?
                """
                cursor = await conn.execute(
                    query_sql,
                    (min_confidence, max_confidence, pagination.per_page, offset),
                )
                rows = await cursor.fetchall()

            # Convert rows to (Prediction, Market) tuples
            predictions: list[tuple[Prediction, Market]] = []
            for row in rows:
                prediction = self._row_to_prediction(row)
                market = self._row_to_market(row)
                predictions.append((prediction, market))

            # Calculate pagination info
            has_next = (pagination.page * pagination.per_page) < total
            has_prev = pagination.page > 1

            logger.info(
                f"{OPERATION_EMOJIS['data']} Found {len(predictions)} predictions "
                f"in confidence range (total: {total})"
            )

            return PredictionQueryResult(
                predictions=predictions,
                total=total,
                page=pagination.page,
                per_page=pagination.per_page,
                has_next=has_next,
                has_prev=has_prev,
            )
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to query predictions by "
                f"confidence range: {e}"
            )
            raise
```

### 项目结构 [Source: architecture.md#Project Structure]

**修改文件:**
```
src/
└── storage/
    └── repositories/
        └── prediction_repo.py    # 修改: 添加查询方法

tests/
└── test_storage/
    └── test_prediction_repo.py  # 修改: 添加查询方法测试
```

### 依赖关系

**本故事依赖:**
- Story 6.1: 预测结果验证机制 (已完成 - PredictionTracker, ValidationResult)
- Story 6.2: 准确率统计 (已完成 - get_validated_with_market, _row_to_market)

**后续故事依赖本故事:**
- Story 7.4: 预测与统计 API (需要查询方法为 Dashboard 提供数据)

### 前一个故事学习 [Source: 6-3-learning-log-generation.md]

**从 Story 6.3 学到的模式:**

1. **数据类返回结果** - 使用 `@dataclass` 定义 `PredictionQueryResult`
2. **依赖注入** - 所有依赖通过构造函数注入
3. **日志标准化** - 使用 emoji 📊 标记查询日志
4. **类型注解** - 使用 `TYPE_CHECKING` 避免循环导入
5. **`__all__` 导出** - 明确模块公共 API
6. **错误处理** - 抛出 ValueError 处理参数验证错误

### 实现注意事项

**关键点:**

1. **分页 1-indexed** - 页码从 1 开始，便于前端使用
2. **JOIN 查询** - 一次性获取预测和市场信息，减少数据库往返
3. **参数验证** - 置信度范围必须在 0-1 之间，min <= max
4. **枚举类型** - 使用 Enum 限制状态和排序选项

**错误处理:**

| 场景 | 处理方式 |
|------|----------|
| 无匹配结果 | 返回空列表，total=0 |
| 无效分页参数 | 使用默认值 (page=1, per_page=20) |
| 无效置信度范围 | 抛出 ValueError |
| 查询失败 | 抛出 DatabaseError |

**日志级别:**

| 级别 | 场景 | Emoji |
|------|------|-------|
| INFO | 查询开始、完成 | 📊 |
| DEBUG | 详细查询信息 | 📊 |
| WARNING | 无数据情况 | ⚠️ |
| ERROR | 操作失败 | ❌ |

### 测试策略

```python
# tests/test_storage/test_prediction_repo.py (扩展)
"""Tests for PredictionRepository query methods."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from src.storage.repositories.prediction_repo import (
    PredictionRepository,
    PredictionOutcomeStatus,
    PredictionSortBy,
    SortOrder,
    PaginationParams,
    SortParams,
    PredictionQueryResult,
)
from src.models.prediction import Prediction, Recommendation
from src.models.market import Market, MarketCategory


class TestPredictionRepositoryQueries:
    """测试预测查询方法."""

    @pytest.fixture
    def repo(self) -> PredictionRepository:
        return PredictionRepository()

    @pytest.mark.asyncio
    async def test_get_predictions_with_outcome_correct(
        self, repo: PredictionRepository
    ) -> None:
        """测试获取正确预测."""
        # Mock database
        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_conn:
            mock_cursor = AsyncMock()
            mock_cursor.fetchone = AsyncMock(
                return_value={"total": 1}
            )
            mock_cursor.fetchall = AsyncMock(return_value=[])
            mock_conn.return_value.__aenter__.return_value.execute = AsyncMock(
                return_value=mock_cursor
            )

            result = await repo.get_predictions_with_outcome(
                status=PredictionOutcomeStatus.CORRECT
            )

            assert isinstance(result, PredictionQueryResult)
            assert result.total >= 0

    @pytest.mark.asyncio
    async def test_get_correct_predictions(
        self, repo: PredictionRepository
    ) -> None:
        """测试便捷方法 get_correct_predictions."""
        with patch.object(
            repo,
            "get_predictions_with_outcome",
            new_callable=AsyncMock,
        ) as mock_method:
            mock_method.return_value = PredictionQueryResult(
                predictions=[],
                total=0,
                page=1,
                per_page=20,
                has_next=False,
                has_prev=False,
            )

            await repo.get_correct_predictions()

            mock_method.assert_called_once()
            call_kwargs = mock_method.call_args[1]
            assert call_kwargs["status"] == PredictionOutcomeStatus.CORRECT

    @pytest.mark.asyncio
    async def test_get_incorrect_predictions(
        self, repo: PredictionRepository
    ) -> None:
        """测试便捷方法 get_incorrect_predictions."""
        with patch.object(
            repo,
            "get_predictions_with_outcome",
            new_callable=AsyncMock,
        ) as mock_method:
            mock_method.return_value = PredictionQueryResult(
                predictions=[],
                total=0,
                page=1,
                per_page=20,
                has_next=False,
                has_prev=False,
            )

            await repo.get_incorrect_predictions()

            mock_method.assert_called_once()
            call_kwargs = mock_method.call_args[1]
            assert call_kwargs["status"] == PredictionOutcomeStatus.INCORRECT

    @pytest.mark.asyncio
    async def test_get_predictions_by_confidence_range(
        self, repo: PredictionRepository
    ) -> None:
        """测试按置信度范围查询."""
        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_conn:
            mock_cursor = AsyncMock()
            mock_cursor.fetchone = AsyncMock(
                return_value={"total": 1}
            )
            mock_cursor.fetchall = AsyncMock(return_value=[])
            mock_conn.return_value.__aenter__.return_value.execute = AsyncMock(
                return_value=mock_cursor
            )

            result = await repo.get_predictions_by_confidence_range(
                min_confidence=0.8,
                max_confidence=1.0,
            )

            assert isinstance(result, PredictionQueryResult)
            assert result.total >= 0

    def test_get_predictions_by_confidence_range_invalid_min(
        self, repo: PredictionRepository
    ) -> None:
        """测试无效最小置信度."""
        with pytest.raises(ValueError, match="min_confidence"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                repo.get_predictions_by_confidence_range(
                    min_confidence=-0.1,
                    max_confidence=1.0,
                )
            )

    def test_get_predictions_by_confidence_range_invalid_max(
        self, repo: PredictionRepository
    ) -> None:
        """测试无效最大置信度."""
        with pytest.raises(ValueError, match="max_confidence"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                repo.get_predictions_by_confidence_range(
                    min_confidence=0.0,
                    max_confidence=1.5,
                )
            )

    def test_get_predictions_by_confidence_range_min_greater_than_max(
        self, repo: PredictionRepository
    ) -> None:
        """测试最小值大于最大值."""
        with pytest.raises(ValueError, match="min_confidence.*must be <="):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                repo.get_predictions_by_confidence_range(
                    min_confidence=0.9,
                    max_confidence=0.8,
                )
            )

    def test_pagination_params_defaults(self) -> None:
        """测试分页参数默认值."""
        params = PaginationParams()
        assert params.page == 1
        assert params.per_page == 20

    def test_sort_params_defaults(self) -> None:
        """测试排序参数默认值."""
        params = SortParams()
        assert params.sort_by == PredictionSortBy.DATE
        assert params.sort_order == SortOrder.DESC

    def test_get_sort_clause_date(self, repo: PredictionRepository) -> None:
        """测试日期排序子句."""
        sort = SortParams(sort_by=PredictionSortBy.DATE, sort_order=SortOrder.DESC)
        clause = repo._get_sort_clause(sort)
        assert "p.created_at" in clause
        assert "DESC" in clause

    def test_get_sort_clause_confidence(self, repo: PredictionRepository) -> None:
        """测试置信度排序子句."""
        sort = SortParams(sort_by=PredictionSortBy.CONFIDENCE, sort_order=SortOrder.ASC)
        clause = repo._get_sort_clause(sort)
        assert "p.confidence" in clause
        assert "ASC" in clause
```

### References

- [Source: architecture.md#Database Schema] - predictions 表定义
- [Source: epics.md#Story 6.4] - 原始 Story 定义
- [Source: src/models/prediction.py] - Prediction 模型定义
- [Source: src/models/market.py] - Market 模型定义
- [Source: src/storage/repositories/prediction_repo.py] - 现有 PredictionRepository 实现
- [Source: 6-3-learning-log-generation.md] - 前一个故事实现参考
- [Source: 6-2-accuracy-statistics.md] - 准确率统计实现参考
