# Story 6.1: 预测结果验证机制

Status: done

## Story

As a **用户**,
I want **系统能够自动检查已结算市场并验证预测准确性**,
So that **我能够知道 LLM 预测的实际表现**.

## Acceptance Criteria

**Given** 预测记录和市场数据已实现 (Story 2.4, 3.4)
**When** 实现 `src/analysis/prediction_tracker.py`
**Then** 创建 `PredictionTracker` 类:
- `check_resolved_markets()` - 检查已结算市场
- `validate_prediction(prediction, actual_outcome)` - 验证单个预测
- `calculate_accuracy(predictions)` - 计算准确率

**And** 预测验证逻辑:
- 获取 `resolution_status = 'RESOLVED'` 的市场
- 对比预测方向与实际结果
- 记录预测是否正确 (`is_correct` 字段)

**And** 更新 predictions 表添加字段 (已在 Story 3.4 中实现):
```sql
-- 已存在于 predictions 表中
actual_outcome TEXT,
is_correct BOOLEAN,
validated_at DATETIME
```

**And** 记录验证日志 (📊 预测验证结果)

## Tasks / Subtasks

- [x] Task 1: 创建 PredictionTracker 类 (AC: 1, 2, 3)
  - [x] 1.1 创建 `src/analysis/prediction_tracker.py`
  - [x] 1.2 实现 `__init__` 方法，注入依赖 (MarketRepository, PredictionRepository)
  - [x] 1.3 实现 `check_resolved_markets()` 方法
  - [x] 1.4 实现 `validate_prediction(prediction, actual_outcome)` 方法
  - [x] 1.5 实现 `calculate_accuracy(predictions)` 方法
  - [x] 1.6 添加日志记录 (📊 emoji)
  - [x] 1.7 更新 `src/analysis/__init__.py` 导出

- [x] Task 2: 扩展 MarketRepository (AC: 2)
  - [x] 2.1 添加 `get_resolved_markets()` 方法
  - [x] 2.2 返回 `resolution_status = 'RESOLVED'` 的市场
  - [x] 2.3 添加单元测试

- [x] Task 3: 扩展 PredictionRepository (AC: 2)
  - [x] 3.1 添加 `get_unvalidated_predictions()` 方法
  - [x] 3.2 添加 `get_validated_predictions()` 方法
  - [x] 3.3 确认 `update_prediction_result()` 方法已存在 (已在 Story 3.4 实现)
  - [x] 3.4 添加单元测试

- [x] Task 4: 实现预测验证逻辑 (AC: 2)
  - [x] 4.1 定义预测方向判断逻辑
  - [x] 4.2 实现 `predicts_yes(prediction)` 辅助函数
  - [x] 4.3 实现验证结果计算: `is_correct = (预测方向 == 实际结果)`
  - [x] 4.4 处理边界情况 (无预测、部分验证)

- [x] Task 5: 编写单元测试 (AC: All)
  - [x] 5.1 创建 `tests/test_analysis/test_prediction_tracker.py`
  - [x] 5.2 测试 `check_resolved_markets()` 方法
  - [x] 5.3 测试 `validate_prediction()` 方法
  - [x] 5.4 测试 `calculate_accuracy()` 方法
  - [x] 5.5 测试边界情况 (空列表、无已结算市场)
  - [x] 5.6 Mock 所有外部依赖

- [x] Task 6: 代码质量检查 (AC: All)
  - [x] 6.1 运行 `mypy src/analysis/prediction_tracker.py` 无错误
  - [x] 6.2 运行 `black --check` 通过
  - [x] 6.3 运行 `isort --check` 通过
  - [x] 6.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md]

**预测验证流程:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                   预测验证流程                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  check_resolved_markets() -> list[ValidationResult]                 │
│                                                                     │
│  1. 获取已结算市场                                                   │
│     resolved_markets = await market_repo.get_resolved_markets()     │
│                                                                     │
│  2. 遍历每个已结算市场                                               │
│     for market in resolved_markets:                                 │
│                                                                     │
│  3. 获取该市场的预测                                                 │
│     predictions = await prediction_repo.get_predictions_by_market(  │
│         market.id                                                   │
│     )                                                               │
│                                                                     │
│  4. 过滤未验证的预测                                                 │
│     unvalidated = [p for p in predictions if p.validated_at is None]│
│                                                                     │
│  5. 验证每个预测                                                     │
│     for prediction in unvalidated:                                  │
│         result = validate_prediction(prediction, market.outcome)    │
│         await prediction_repo.update_prediction_result(             │
│             prediction.id,                                          │
│             market.resolution_outcome,                              │
│             result.is_correct                                       │
│         )                                                           │
│                                                                     │
│  6. 记录验证日志                                                     │
│     logger.info(f"📊 Validated {len(results)} predictions")         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 已有组件 (必须复用)

**Prediction Model** [Source: src/models/prediction.py]
```python
class Prediction(BaseModel):
    id: int | None
    market_id: str
    predicted_probability: float  # 0-1, >0.5 表示预测 YES
    confidence: float
    reasoning: str | None
    key_assumptions: list[str] | None
    model_used: str | None
    recommendation: Recommendation | None  # BUY_YES, BUY_NO, NO_TRADE
    edge: float | None
    actual_outcome: str | None
    is_correct: bool | None
    validated_at: datetime | None
    created_at: datetime | None

class Recommendation(str, Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    NO_TRADE = "NO_TRADE"
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
    resolution_status: str | None  # "RESOLVED" 表示已结算
    resolution_outcome: str | None  # "YES" 或 "NO"
    created_at: datetime | None
    updated_at: datetime | None
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
```

**MarketRepository** [Source: src/storage/repositories/market_repo.py]
```python
class MarketRepository:
    async def get_market(market_id: str) -> Market | None
    async def get_all_markets(limit: int | None = None) -> list[Market]
    async def get_active_markets() -> list[Market]
    async def update_market_resolution(market_id: str, outcome: str) -> bool
```

### 预测方向判断逻辑

**方法 1: 基于 predicted_probability**
```python
def predicts_yes(prediction: Prediction) -> bool:
    """判断预测是否倾向于 YES 结果.

    预测概率 > 0.5 表示预测 YES 会发生
    预测概率 < 0.5 表示预测 NO 会发生
    预测概率 = 0.5 表示中立，不计入准确率
    """
    if prediction.predicted_probability > 0.5:
        return True  # 预测 YES
    elif prediction.predicted_probability < 0.5:
        return False  # 预测 NO
    else:
        return None  # 中立，不计入
```

**方法 2: 基于 recommendation (更可靠)**
```python
def get_prediction_direction(prediction: Prediction) -> str | None:
    """从推荐获取预测方向.

    BUY_YES -> 预测 YES
    BUY_NO -> 预测 NO
    NO_TRADE -> 不计入
    """
    if prediction.recommendation == Recommendation.BUY_YES:
        return "YES"
    elif prediction.recommendation == Recommendation.BUY_NO:
        return "NO"
    else:
        return None
```

**验证逻辑:**
```python
def validate_prediction(
    prediction: Prediction,
    actual_outcome: str
) -> ValidationResult:
    """验证预测是否正确."""
    predicted_direction = get_prediction_direction(prediction)

    if predicted_direction is None:
        # NO_TRADE 推荐不计入验证
        return ValidationResult(
            prediction_id=prediction.id,
            is_validated=False,
            is_correct=None,
            reason="NO_TRADE recommendation not counted"
        )

    is_correct = (predicted_direction == actual_outcome)

    return ValidationResult(
        prediction_id=prediction.id,
        is_validated=True,
        is_correct=is_correct,
        actual_outcome=actual_outcome
    )
```

### 准确率计算

```python
def calculate_accuracy(predictions: list[Prediction]) -> AccuracyResult:
    """计算已验证预测的准确率."""
    validated = [p for p in predictions if p.is_correct is not None]

    if not validated:
        return AccuracyResult(
            total=0,
            correct=0,
            accuracy=None
        )

    correct = sum(1 for p in validated if p.is_correct)
    total = len(validated)
    accuracy = correct / total

    return AccuracyResult(
        total=total,
        correct=correct,
        accuracy=accuracy
    )
```

### 实现模板

**src/analysis/prediction_tracker.py:**

```python
"""Prediction tracking and validation.

Story 6.1: 预测结果验证机制
"""

from __future__ import annotations

__all__ = ["PredictionTracker", "ValidationResult", "AccuracyResult"]

from dataclasses import dataclass
from datetime import datetime, timezone

from src.models.prediction import Prediction, Recommendation
from src.storage.repositories.market_repo import MarketRepository
from src.storage.repositories.prediction_repo import PredictionRepository
from src.utils.logger import OPERATION_EMOJIS, get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of a single prediction validation.

    Attributes:
        prediction_id: ID of the validated prediction
        is_validated: Whether the prediction was validated
        is_correct: Whether the prediction was correct (None if not validated)
        actual_outcome: Actual market outcome
        reason: Optional reason if not validated
    """
    prediction_id: int
    is_validated: bool
    is_correct: bool | None
    actual_outcome: str | None
    reason: str | None = None


@dataclass
class AccuracyResult:
    """Accuracy calculation result.

    Attributes:
        total: Total validated predictions
        correct: Number of correct predictions
        accuracy: Accuracy ratio (0-1), None if no predictions
    """
    total: int
    correct: int
    accuracy: float | None


class PredictionTracker:
    """Tracker for prediction validation and accuracy.

    Validates predictions against resolved market outcomes and
    calculates accuracy statistics.

    Example:
        >>> tracker = PredictionTracker(market_repo, prediction_repo)
        >>> results = await tracker.check_resolved_markets()
        >>> print(f"Validated {len(results)} predictions")
    """

    def __init__(
        self,
        market_repo: MarketRepository,
        prediction_repo: PredictionRepository,
    ) -> None:
        """Initialize the PredictionTracker.

        Args:
            market_repo: Repository for market data
            prediction_repo: Repository for prediction data
        """
        self._market_repo = market_repo
        self._prediction_repo = prediction_repo
        self._logger = logger

    async def check_resolved_markets(self) -> list[ValidationResult]:
        """Check all resolved markets and validate pending predictions.

        Returns:
            List of validation results for all validated predictions
        """
        # Implementation...

    def validate_prediction(
        self,
        prediction: Prediction,
        actual_outcome: str
    ) -> ValidationResult:
        """Validate a single prediction against actual outcome.

        Args:
            prediction: Prediction to validate
            actual_outcome: Actual market outcome ("YES" or "NO")

        Returns:
            ValidationResult with validation details
        """
        # Implementation...

    def calculate_accuracy(
        self,
        predictions: list[Prediction]
    ) -> AccuracyResult:
        """Calculate accuracy for a list of predictions.

        Only counts validated predictions with is_correct set.

        Args:
            predictions: List of predictions to calculate accuracy for

        Returns:
            AccuracyResult with total, correct, and accuracy ratio
        """
        # Implementation...
```

### 项目结构 [Source: architecture.md#Project Structure]

**新增文件:**
```
src/
└── analysis/
    └── prediction_tracker.py     # 新增

tests/
└── test_analysis/
    └── test_prediction_tracker.py  # 新增
```

**修改文件:**
```
src/
├── analysis/
│   └── __init__.py               # 修改: 导出 PredictionTracker
└── storage/
    └── repositories/
        ├── market_repo.py        # 修改: 添加 get_resolved_markets
        └── prediction_repo.py    # 修改: 添加 get_unvalidated_predictions
```

### 依赖关系

**本故事依赖:**
- Story 2.4: 市场数据仓库 (已完成 - `MarketRepository`)
- Story 3.4: 预测结果存储 (已完成 - `PredictionRepository`, predictions 表)

**后续故事依赖本故事:**
- Story 6.2: 准确率统计 (需要验证后的预测数据)
- Story 6.4: 预测历史查询 API (需要验证状态)
- Story 6.5: 表现分析与洞察 (需要准确率数据)

### 前一个故事学习 [Source: 5-5-statistics-data-recording.md]

**从 Story 5.5 学到的模式:**

1. **数据类返回结果** - 使用 `@dataclass` 定义 `ValidationResult` 和 `AccuracyResult`
2. **依赖注入** - 所有依赖通过构造函数注入
3. **错误隔离** - 单个验证失败不影响其他验证
4. **日志标准化** - 使用 emoji 📊 标记验证日志
5. **类型注解** - 使用 `TYPE_CHECKING` 避免循环导入
6. **`__all__` 导出** - 明确模块公共 API

### 实现注意事项

**关键点:**

1. **NO_TRADE 处理** - recommendation 为 NO_TRADE 的预测不计入验证
2. **中立概率** - predicted_probability = 0.5 的预测不计入
3. **幂等性** - `check_resolved_markets()` 可以重复调用，不会重复验证
4. **日志格式** - 使用 📊 emoji 标记验证相关日志

**错误处理:**

| 场景 | 处理方式 |
|------|----------|
| 无已结算市场 | 返回空列表，记录 INFO 日志 |
| 预测无推荐 | 基于 predicted_probability 判断 |
| 更新失败 | 记录 ERROR 日志，继续处理其他预测 |
| 查询失败 | 抛出 DatabaseError |

**日志级别:**

| 级别 | 场景 | Emoji |
|------|------|-------|
| INFO | 验证开始、完成 | 📊 |
| DEBUG | 单个预测验证详情 | 📊 |
| WARNING | 无数据情况 | ⚠️ |
| ERROR | 操作失败 | ❌ |

### 测试策略

```python
# tests/test_analysis/test_prediction_tracker.py
"""Tests for PredictionTracker."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.analysis.prediction_tracker import (
    PredictionTracker,
    ValidationResult,
    AccuracyResult,
)
from src.models.prediction import Prediction, Recommendation
from src.models.market import Market


class TestPredictionTracker:
    """测试 PredictionTracker 类."""

    @pytest.fixture
    def tracker(self) -> PredictionTracker:
        market_repo = AsyncMock()
        prediction_repo = AsyncMock()
        return PredictionTracker(market_repo, prediction_repo)

    def test_validate_prediction_correct_yes(
        self, tracker: PredictionTracker
    ) -> None:
        """测试正确预测 YES 的情况."""
        prediction = Prediction(
            id=1,
            market_id="test-market",
            predicted_probability=0.75,
            confidence=0.85,
            recommendation=Recommendation.BUY_YES,
        )
        result = tracker.validate_prediction(prediction, "YES")
        assert result.is_correct is True
        assert result.is_validated is True

    def test_validate_prediction_incorrect(
        self, tracker: PredictionTracker
    ) -> None:
        """测试错误预测的情况."""
        prediction = Prediction(
            id=1,
            market_id="test-market",
            predicted_probability=0.75,
            confidence=0.85,
            recommendation=Recommendation.BUY_YES,
        )
        result = tracker.validate_prediction(prediction, "NO")
        assert result.is_correct is False
        assert result.is_validated is True

    def test_validate_prediction_no_trade(
        self, tracker: PredictionTracker
    ) -> None:
        """测试 NO_TRADE 推荐不计入验证."""
        prediction = Prediction(
            id=1,
            market_id="test-market",
            predicted_probability=0.5,
            confidence=0.6,
            recommendation=Recommendation.NO_TRADE,
        )
        result = tracker.validate_prediction(prediction, "YES")
        assert result.is_validated is False
        assert result.is_correct is None

    def test_calculate_accuracy(
        self, tracker: PredictionTracker
    ) -> None:
        """测试准确率计算."""
        predictions = [
            Prediction(
                id=1,
                market_id="m1",
                predicted_probability=0.7,
                confidence=0.8,
                is_correct=True,
            ),
            Prediction(
                id=2,
                market_id="m2",
                predicted_probability=0.6,
                confidence=0.7,
                is_correct=False,
            ),
            Prediction(
                id=3,
                market_id="m3",
                predicted_probability=0.8,
                confidence=0.9,
                is_correct=True,
            ),
        ]
        result = tracker.calculate_accuracy(predictions)
        assert result.total == 3
        assert result.correct == 2
        assert result.accuracy == 2 / 3

    def test_calculate_accuracy_empty(
        self, tracker: PredictionTracker
    ) -> None:
        """测试空列表的准确率计算."""
        result = tracker.calculate_accuracy([])
        assert result.total == 0
        assert result.accuracy is None

    @pytest.mark.asyncio
    async def test_check_resolved_markets(
        self, tracker: PredictionTracker
    ) -> None:
        """测试检查已结算市场."""
        # Setup mocks
        tracker._market_repo.get_resolved_markets = AsyncMock(
            return_value=[
                Market(
                    id="m1",
                    title="Test Market",
                    resolution_status="RESOLVED",
                    resolution_outcome="YES",
                )
            ]
        )
        tracker._prediction_repo.get_predictions_by_market = AsyncMock(
            return_value=[
                Prediction(
                    id=1,
                    market_id="m1",
                    predicted_probability=0.7,
                    confidence=0.8,
                    recommendation=Recommendation.BUY_YES,
                    validated_at=None,
                )
            ]
        )
        tracker._prediction_repo.update_prediction_result = AsyncMock(
            return_value=True
        )

        results = await tracker.check_resolved_markets()

        assert len(results) == 1
        assert results[0].is_correct is True
```

### References

- [Source: architecture.md#Database Schema] - predictions 表定义
- [Source: epics.md#Story 6.1] - 原始 Story 定义
- [Source: src/models/prediction.py] - Prediction 模型定义
- [Source: src/models/market.py] - Market 模型定义
- [Source: src/storage/repositories/prediction_repo.py] - PredictionRepository 参考
- [Source: src/storage/repositories/market_repo.py] - MarketRepository 参考
- [Source: 5-5-statistics-data-recording.md] - 前一个故事实现参考
