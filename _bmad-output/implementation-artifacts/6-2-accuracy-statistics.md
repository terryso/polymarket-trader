# Story 6.2: 准确率统计

Status: done

## Story

As a **用户**,
I want **系统能够计算并展示 LLM 预测的整体准确率**,
So that **我能够评估 LLM 的分析能力**.

## Acceptance Criteria

**Given** 预测验证机制已实现 (Story 6.1)
**When** 实现准确率统计功能
**Then** 在 `prediction_tracker.py` 添加:
- `get_overall_accuracy()` - 获取总体准确率
- `get_accuracy_by_category(category)` - 按类别统计
- `get_accuracy_by_date_range(start, end)` - 按时间范围统计
- `get_confidence_accuracy_correlation()` - 置信度与准确率相关性

**And** 准确率计算:
```python
accuracy = correct_predictions / total_validated_predictions
```

**And** 返回统计结果包含:
- 总预测数、正确数、准确率
- 按类别分组统计
- 按置信度区间统计

**And** 记录统计更新日志

## Tasks / Subtasks

- [x] Task 1: 定义准确率统计数据模型 (AC: 2, 3)
  - [x] 1.1 创建 `AccuracyStatistics` 数据类 (总体准确率)
  - [x] 1.2 创建 `CategoryAccuracy` 数据类 (按类别统计)
  - [x] 1.3 创建 `ConfidenceAccuracy` 数据类 (按置信度区间统计)
  - [x] 1.4 创建 `DateRangeAccuracy` 数据类 (按时间范围统计)
  - [x] 1.5 更新 `__all__` 导出

- [x] Task 2: 实现总体准确率统计 (AC: 1)
  - [x] 2.1 实现 `get_overall_accuracy()` 方法
  - [x] 2.2 从 PredictionRepository 获取所有已验证预测
  - [x] 2.3 计算总体准确率
  - [x] 2.4 添加日志记录 (📊 emoji)

- [x] Task 3: 实现按类别统计 (AC: 1)
  - [x] 3.1 实现 `get_accuracy_by_category()` 方法
  - [x] 3.2 扩展 PredictionRepository 添加 `get_validated_with_market()`
  - [x] 3.3 按 market.category 分组统计
  - [x] 3.4 返回每个类别的准确率

- [x] Task 4: 实现按时间范围统计 (AC: 1)
  - [x] 4.1 实现 `get_accuracy_by_date_range()` 方法
  - [x] 4.2 扩展 PredictionRepository 添加 `get_validated_by_date_range()`
  - [x] 4.3 筛选 validated_at 在指定范围内的预测
  - [x] 4.4 计算时间范围内的准确率

- [x] Task 5: 实现置信度与准确率相关性 (AC: 1)
  - [x] 5.1 实现 `get_confidence_accuracy_correlation()` 方法
  - [x] 5.2 按置信度区间分组 (0-0.6, 0.6-0.7, 0.7-0.8, 0.8-0.9, 0.9-1.0)
  - [x] 5.3 计算每个区间的准确率
  - [x] 5.4 计算相关系数 (可选)

- [x] Task 6: 扩展 PredictionRepository (AC: 2, 3)
  - [x] 6.1 添加 `get_all_validated()` 方法
  - [x] 6.2 添加 `get_validated_by_date_range(start, end)` 方法
  - [x] 6.3 添加 `get_validated_with_market()` 方法 (JOIN 查询)
  - [x] 6.4 添加单元测试

- [x] Task 7: 编写单元测试 (AC: All)
  - [x] 7.1 创建/扩展 `tests/test_analysis/test_prediction_tracker.py`
  - [x] 7.2 测试 `get_overall_accuracy()` 方法
  - [x] 7.3 测试 `get_accuracy_by_category()` 方法
  - [x] 7.4 测试 `get_accuracy_by_date_range()` 方法
  - [x] 7.5 测试 `get_confidence_accuracy_correlation()` 方法
  - [x] 7.6 测试边界情况 (无数据、空范围等)
  - [x] 7.7 Mock 所有外部依赖

- [x] Task 8: 代码质量检查 (AC: All)
  - [x] 8.1 运行 `mypy src/analysis/prediction_tracker.py` 无错误
  - [x] 8.2 运行 `black --check` 通过
  - [x] 8.3 运行 `isort --check` 通过
  - [x] 8.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md]

**准确率统计流程:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                   准确率统计流程                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  get_overall_accuracy() -> AccuracyStatistics                       │
│                                                                     │
│  1. 获取所有已验证预测                                               │
│     validated = await prediction_repo.get_all_validated()           │
│                                                                     │
│  2. 计算总体准确率                                                   │
│     total = len(validated)                                          │
│     correct = sum(1 for p in validated if p.is_correct)             │
│     accuracy = correct / total if total > 0 else None               │
│                                                                     │
│  3. 返回统计结果                                                     │
│     return AccuracyStatistics(total, correct, accuracy)             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 已有组件 (必须复用)

**PredictionTracker** [Source: src/analysis/prediction_tracker.py]
```python
class PredictionTracker:
    """已实现的方法 (Story 6.1):"""
    async def check_resolved_markets() -> list[ValidationResult]
    def validate_prediction(prediction, actual_outcome) -> ValidationResult
    def calculate_accuracy(predictions) -> AccuracyResult
    def _get_prediction_direction(prediction) -> str | None
```

**Prediction Model** [Source: src/models/prediction.py]
```python
class Prediction(BaseModel):
    id: int | None
    market_id: str
    predicted_probability: float  # 0-1, >0.5 表示预测 YES
    confidence: float             # 置信度 0-1
    reasoning: str | None
    key_assumptions: list[str] | None
    model_used: str | None
    recommendation: Recommendation | None  # BUY_YES, BUY_NO, NO_TRADE
    edge: float | None
    actual_outcome: str | None
    is_correct: bool | None
    validated_at: datetime | None  # 验证时间
    created_at: datetime | None
```

**Market Model** [Source: src/models/market.py]
```python
class Market(BaseModel):
    id: str
    title: str
    description: str | None
    category: MarketCategory | None  # 按类别统计需要
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
    TECH = "tech"
    ECONOMICS = "economics"
    CRYPTO = "crypto"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    OTHER = "other"
```

**PredictionRepository** [Source: src/storage/repositories/prediction_repo.py]
```python
class PredictionRepository:
    async def save_prediction(prediction: Prediction, upsert: bool = True) -> int
    async def get_predictions_by_market(market_id: str) -> list[Prediction]
    async def get_pending_predictions() -> list[Prediction]
    async def get_latest_prediction(market_id: str) -> Prediction | None
    async def update_prediction_result(
        prediction_id: int,
        actual_outcome: str,
        is_correct: bool
    ) -> bool

    # Story 6.1 新增:
    async def get_unvalidated_predictions() -> list[Prediction]
    async def get_validated_predictions() -> list[Prediction]
```

### 新增数据模型

**src/analysis/prediction_tracker.py (扩展):**

```python
@dataclass
class AccuracyStatistics:
    """Overall accuracy statistics.

    Attributes:
        total: Total validated predictions
        correct: Number of correct predictions
        incorrect: Number of incorrect predictions
        accuracy: Accuracy ratio (0-1), None if no predictions
    """
    total: int
    correct: int
    incorrect: int
    accuracy: float | None


@dataclass
class CategoryAccuracy:
    """Accuracy statistics for a single category.

    Attributes:
        category: Market category
        total: Total validated predictions in this category
        correct: Number of correct predictions
        accuracy: Accuracy ratio (0-1), None if no predictions
    """
    category: str
    total: int
    correct: int
    accuracy: float | None


@dataclass
class ConfidenceAccuracy:
    """Accuracy statistics for a confidence range.

    Attributes:
        confidence_range: Confidence range (e.g., "0.8-0.9")
        total: Total validated predictions in this range
        correct: Number of correct predictions
        accuracy: Accuracy ratio (0-1), None if no predictions
    """
    confidence_range: str
    total: int
    correct: int
    accuracy: float | None


@dataclass
class DateRangeAccuracy:
    """Accuracy statistics for a date range.

    Attributes:
        start_date: Start of date range
        end_date: End of date range
        total: Total validated predictions in this range
        correct: Number of correct predictions
        accuracy: Accuracy ratio (0-1), None if no predictions
    """
    start_date: datetime
    end_date: datetime
    total: int
    correct: int
    accuracy: float | None
```

### 实现模板

**src/analysis/prediction_tracker.py (新增方法):**

```python
from datetime import datetime
from collections import defaultdict

# 更新 __all__
__all__ = [
    "PredictionTracker",
    "ValidationResult",
    "AccuracyResult",
    "AccuracyStatistics",
    "CategoryAccuracy",
    "ConfidenceAccuracy",
    "DateRangeAccuracy",
]

class PredictionTracker:
    # ... 已有方法 ...

    async def get_overall_accuracy(self) -> AccuracyStatistics:
        """Get overall accuracy statistics for all validated predictions.

        Returns:
            AccuracyStatistics with total, correct, incorrect, and accuracy
        """
        self._logger.info(
            f"{OPERATION_EMOJIS['data']} Calculating overall accuracy"
        )

        validated = await self._prediction_repo.get_all_validated()

        if not validated:
            return AccuracyStatistics(
                total=0,
                correct=0,
                incorrect=0,
                accuracy=None,
            )

        correct = sum(1 for p in validated if p.is_correct)
        total = len(validated)
        accuracy = correct / total

        self._logger.info(
            f"{OPERATION_EMOJIS['data']} Overall accuracy: "
            f"{accuracy:.1%} ({correct}/{total})"
        )

        return AccuracyStatistics(
            total=total,
            correct=correct,
            incorrect=total - correct,
            accuracy=accuracy,
        )

    async def get_accuracy_by_category(self) -> list[CategoryAccuracy]:
        """Get accuracy statistics grouped by market category.

        Returns:
            List of CategoryAccuracy for each category with validated predictions
        """
        self._logger.info(
            f"{OPERATION_EMOJIS['data']} Calculating accuracy by category"
        )

        # Get validated predictions with market info
        validated_with_markets = await self._prediction_repo.get_validated_with_market()

        # Group by category
        by_category: dict[str, list[Prediction]] = defaultdict(list)
        for prediction, market in validated_with_markets:
            category = market.category.value if market.category else "other"
            by_category[category].append(prediction)

        # Calculate accuracy for each category
        results: list[CategoryAccuracy] = []
        for category, predictions in by_category.items():
            correct = sum(1 for p in predictions if p.is_correct)
            total = len(predictions)
            accuracy = correct / total if total > 0 else None

            results.append(CategoryAccuracy(
                category=category,
                total=total,
                correct=correct,
                accuracy=accuracy,
            ))

        self._logger.info(
            f"{OPERATION_EMOJIS['data']} Accuracy by category: "
            f"{len(results)} categories"
        )

        return sorted(results, key=lambda x: x.total, reverse=True)

    async def get_accuracy_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> DateRangeAccuracy:
        """Get accuracy statistics for a specific date range.

        Args:
            start_date: Start of date range (validated_at >= start_date)
            end_date: End of date range (validated_at <= end_date)

        Returns:
            DateRangeAccuracy with statistics for the date range
        """
        self._logger.info(
            f"{OPERATION_EMOJIS['data']} Calculating accuracy for date range: "
            f"{start_date.date()} to {end_date.date()}"
        )

        validated = await self._prediction_repo.get_validated_by_date_range(
            start_date, end_date
        )

        if not validated:
            return DateRangeAccuracy(
                start_date=start_date,
                end_date=end_date,
                total=0,
                correct=0,
                accuracy=None,
            )

        correct = sum(1 for p in validated if p.is_correct)
        total = len(validated)
        accuracy = correct / total

        self._logger.info(
            f"{OPERATION_EMOJIS['data']} Date range accuracy: "
            f"{accuracy:.1%} ({correct}/{total})"
        )

        return DateRangeAccuracy(
            start_date=start_date,
            end_date=end_date,
            total=total,
            correct=correct,
            accuracy=accuracy,
        )

    async def get_confidence_accuracy_correlation(self) -> list[ConfidenceAccuracy]:
        """Get accuracy statistics grouped by confidence ranges.

        Confidence ranges:
        - 0.5-0.6: Low confidence
        - 0.6-0.7: Medium-low confidence
        - 0.7-0.8: Medium confidence
        - 0.8-0.9: Medium-high confidence
        - 0.9-1.0: High confidence

        Returns:
            List of ConfidenceAccuracy for each confidence range
        """
        self._logger.info(
            f"{OPERATION_EMOJIS['data']} Calculating confidence-accuracy correlation"
        )

        validated = await self._prediction_repo.get_all_validated()

        # Define confidence ranges
        ranges = [
            (0.5, 0.6, "0.5-0.6"),
            (0.6, 0.7, "0.6-0.7"),
            (0.7, 0.8, "0.7-0.8"),
            (0.8, 0.9, "0.8-0.9"),
            (0.9, 1.0, "0.9-1.0"),
        ]

        results: list[ConfidenceAccuracy] = []

        for min_conf, max_conf, range_label in ranges:
            in_range = [
                p for p in validated
                if min_conf <= p.confidence < max_conf
            ]

            if not in_range:
                continue

            correct = sum(1 for p in in_range if p.is_correct)
            total = len(in_range)
            accuracy = correct / total

            results.append(ConfidenceAccuracy(
                confidence_range=range_label,
                total=total,
                correct=correct,
                accuracy=accuracy,
            ))

        self._logger.info(
            f"{OPERATION_EMOJIS['data']} Confidence-accuracy correlation: "
            f"{len(results)} ranges with data"
        )

        return results
```

### 扩展 PredictionRepository

**src/storage/repositories/prediction_repo.py (新增方法):**

```python
async def get_all_validated(self) -> list[Prediction]:
    """Get all validated predictions (is_correct is not None).

    Returns:
        List of validated predictions
    """
    async with self._get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT * FROM predictions
            WHERE is_correct IS NOT NULL
            ORDER BY validated_at DESC
            """
        )
        rows = await cursor.fetchall()
        return [self._row_to_prediction(row) for row in rows]

async def get_validated_by_date_range(
    self,
    start_date: datetime,
    end_date: datetime,
) -> list[Prediction]:
    """Get validated predictions within a date range.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        List of validated predictions in the date range
    """
    async with self._get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT * FROM predictions
            WHERE is_correct IS NOT NULL
            AND validated_at >= ?
            AND validated_at <= ?
            ORDER BY validated_at DESC
            """,
            (start_date.isoformat(), end_date.isoformat()),
        )
        rows = await cursor.fetchall()
        return [self._row_to_prediction(row) for row in rows]

async def get_validated_with_market(self) -> list[tuple[Prediction, Market]]:
    """Get all validated predictions with their associated market info.

    Returns:
        List of (Prediction, Market) tuples
    """
    async with self._get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT p.*, m.id as market_id_col, m.title, m.description, m.category,
                   m.yes_price, m.no_price, m.liquidity, m.deadline,
                   m.resolution_status, m.resolution_outcome,
                   m.created_at as market_created_at, m.updated_at as market_updated_at
            FROM predictions p
            JOIN markets m ON p.market_id = m.id
            WHERE p.is_correct IS NOT NULL
            ORDER BY p.validated_at DESC
            """
        )
        rows = await cursor.fetchall()

        results: list[tuple[Prediction, Market]] = []
        for row in rows:
            prediction = self._row_to_prediction(row)
            market = self._row_to_market(row)
            results.append((prediction, market))

        return results
```

### 项目结构 [Source: architecture.md#Project Structure]

**修改文件:**
```
src/
├── analysis/
│   └── prediction_tracker.py     # 修改: 添加准确率统计方法
└── storage/
    └── repositories/
        └── prediction_repo.py    # 修改: 添加查询方法

tests/
└── test_analysis/
    └── test_prediction_tracker.py  # 修改: 添加准确率统计测试
```

### 依赖关系

**本故事依赖:**
- Story 6.1: 预测结果验证机制 (已完成 - PredictionTracker, ValidationResult)

**后续故事依赖本故事:**
- Story 6.4: 预测历史查询 API (需要准确率统计方法)
- Story 6.5: 表现分析与洞察 (需要置信度-准确率相关性)

### 前一个故事学习 [Source: 6-1-prediction-result-validation-mechanism.md]

**从 Story 6.1 学到的模式:**

1. **数据类返回结果** - 使用 `@dataclass` 定义返回类型
2. **依赖注入** - 所有依赖通过构造函数注入
3. **日志标准化** - 使用 emoji 📊 标记统计日志
4. **类型注解** - 使用 `TYPE_CHECKING` 避免循环导入
5. **`__all__` 导出** - 明确模块公共 API
6. **空值处理** - 当无数据时返回 accuracy=None

### 实现注意事项

**关键点:**

1. **置信度区间** - 使用半开区间 [min, max)，避免边界重复
2. **类别分组** - 使用 `defaultdict` 简化分组逻辑
3. **排序** - 按预测数量降序排列，便于分析
4. **日期范围** - 使用 validated_at 而非 created_at 进行筛选

**错误处理:**

| 场景 | 处理方式 |
|------|----------|
| 无已验证预测 | 返回 accuracy=None 的结果 |
| 空日期范围 | 返回 total=0 的结果 |
| 查询失败 | 抛出 DatabaseError |
| 无市场关联 | category 视为 "other" |

**日志级别:**

| 级别 | 场景 | Emoji |
|------|------|-------|
| INFO | 统计开始、完成 | 📊 |
| DEBUG | 详细统计信息 | 📊 |
| WARNING | 无数据情况 | ⚠️ |
| ERROR | 操作失败 | ❌ |

### 测试策略

```python
# tests/test_analysis/test_prediction_tracker.py (扩展)
"""Tests for PredictionTracker accuracy statistics."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from src.analysis.prediction_tracker import (
    PredictionTracker,
    AccuracyStatistics,
    CategoryAccuracy,
    ConfidenceAccuracy,
    DateRangeAccuracy,
)
from src.models.prediction import Prediction
from src.models.market import Market, MarketCategory


class TestPredictionTrackerAccuracy:
    """测试准确率统计功能."""

    @pytest.fixture
    def tracker(self) -> PredictionTracker:
        market_repo = AsyncMock()
        prediction_repo = AsyncMock()
        return PredictionTracker(market_repo, prediction_repo)

    @pytest.mark.asyncio
    async def test_get_overall_accuracy(
        self, tracker: PredictionTracker
    ) -> None:
        """测试获取总体准确率."""
        tracker._prediction_repo.get_all_validated = AsyncMock(
            return_value=[
                Prediction(
                    id=1, market_id="m1", predicted_probability=0.7,
                    confidence=0.8, is_correct=True
                ),
                Prediction(
                    id=2, market_id="m2", predicted_probability=0.6,
                    confidence=0.7, is_correct=False
                ),
            ]
        )

        result = await tracker.get_overall_accuracy()

        assert result.total == 2
        assert result.correct == 1
        assert result.incorrect == 1
        assert result.accuracy == 0.5

    @pytest.mark.asyncio
    async def test_get_overall_accuracy_empty(
        self, tracker: PredictionTracker
    ) -> None:
        """测试无数据时的总体准确率."""
        tracker._prediction_repo.get_all_validated = AsyncMock(return_value=[])

        result = await tracker.get_overall_accuracy()

        assert result.total == 0
        assert result.accuracy is None

    @pytest.mark.asyncio
    async def test_get_accuracy_by_category(
        self, tracker: PredictionTracker
    ) -> None:
        """测试按类别统计准确率."""
        tracker._prediction_repo.get_validated_with_market = AsyncMock(
            return_value=[
                (
                    Prediction(id=1, market_id="m1", predicted_probability=0.7,
                              confidence=0.8, is_correct=True),
                    Market(id="m1", title="Test", category=MarketCategory.POLITICS),
                ),
                (
                    Prediction(id=2, market_id="m2", predicted_probability=0.6,
                              confidence=0.7, is_correct=False),
                    Market(id="m2", title="Test", category=MarketCategory.POLITICS),
                ),
                (
                    Prediction(id=3, market_id="m3", predicted_probability=0.8,
                              confidence=0.9, is_correct=True),
                    Market(id="m3", title="Test", category=MarketCategory.TECH),
                ),
            ]
        )

        results = await tracker.get_accuracy_by_category()

        assert len(results) == 2
        politics = next(r for r in results if r.category == "politics")
        assert politics.total == 2
        assert politics.correct == 1
        assert politics.accuracy == 0.5

    @pytest.mark.asyncio
    async def test_get_accuracy_by_date_range(
        self, tracker: PredictionTracker
    ) -> None:
        """测试按时间范围统计准确率."""
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31)

        tracker._prediction_repo.get_validated_by_date_range = AsyncMock(
            return_value=[
                Prediction(
                    id=1, market_id="m1", predicted_probability=0.7,
                    confidence=0.8, is_correct=True
                ),
            ]
        )

        result = await tracker.get_accuracy_by_date_range(start, end)

        assert result.total == 1
        assert result.correct == 1
        assert result.accuracy == 1.0

    @pytest.mark.asyncio
    async def test_get_confidence_accuracy_correlation(
        self, tracker: PredictionTracker
    ) -> None:
        """测试置信度与准确率相关性."""
        tracker._prediction_repo.get_all_validated = AsyncMock(
            return_value=[
                Prediction(
                    id=1, market_id="m1", predicted_probability=0.7,
                    confidence=0.85, is_correct=True
                ),
                Prediction(
                    id=2, market_id="m2", predicted_probability=0.6,
                    confidence=0.75, is_correct=False
                ),
            ]
        )

        results = await tracker.get_confidence_accuracy_correlation()

        assert len(results) >= 1
        # 找到 0.8-0.9 区间
        high_conf = next(
            (r for r in results if r.confidence_range == "0.8-0.9"), None
        )
        assert high_conf is not None
        assert high_conf.total == 1
        assert high_conf.accuracy == 1.0
```

### References

- [Source: architecture.md#Database Schema] - predictions 表定义
- [Source: epics.md#Story 6.2] - 原始 Story 定义
- [Source: src/analysis/prediction_tracker.py] - 现有 PredictionTracker 实现
- [Source: src/models/prediction.py] - Prediction 模型定义
- [Source: src/models/market.py] - Market 模型定义
- [Source: src/storage/repositories/prediction_repo.py] - PredictionRepository 参考
- [Source: 6-1-prediction-result-validation-mechanism.md] - 前一个故事实现参考
