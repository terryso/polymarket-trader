# Story 3.4: 预测结果存储

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **开发者**,
I want **将 LLM 分析结果持久化到数据库**,
So that **预测历史可追溯和分析**.

## Acceptance Criteria

**Given** LLM 分析引擎已实现
**When** 扩展数据库和创建预测仓库
**Then** 在 `database.py` 添加 `predictions` 表:
```sql
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    predicted_probability REAL,
    confidence REAL,
    reasoning TEXT,
    key_assumptions TEXT,
    model_used TEXT,
    recommendation TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (market_id) REFERENCES markets(id)
);
```
**And** 实现 `src/storage/repositories/prediction_repo.py`:
- `save_prediction(prediction: Prediction)` - 保存预测
- `get_predictions_by_market(market_id: str)` - 获取市场预测
- `get_pending_predictions()` - 获取待验证预测
**And** 关联 market_id 外键

## Tasks / Subtasks

- [ ] Task 1: 扩展数据库 Schema (AC: 1)
  - [ ] 1.1 在 `src/storage/database.py` 添加 `predictions` 表创建语句
  - [ ] 1.2 确保 `predictions` 表与 `markets` 表外键关联
  - [ ] 1.3 更新 `init_db()` 函数包含新表
  - [ ] 1.4 添加数据库迁移逻辑 (如果需要)

- [ ] Task 2: 创建预测仓库目录结构 (AC: 2)
  - [ ] 2.1 创建 `src/storage/repositories/` 目录
  - [ ] 2.2 创建 `src/storage/repositories/__init__.py`
  - [ ] 2.3 创建 `src/storage/repositories/prediction_repo.py`

- [ ] Task 3: 实现 PredictionRepository 类 (AC: 2)
  - [ ] 3.1 创建 `PredictionRepository` 类
  - [ ] 3.2 实现 `__init__()` 初始化数据库连接
  - [ ] 3.3 初始化日志器
  - [ ] 3.4 定义 `__all__` 导出列表

- [ ] Task 4: 实现 save_prediction 方法 (AC: 2)
  - [ ] 4.1 定义方法签名 `async def save_prediction(prediction: Prediction) -> int`
  - [ ] 4.2 将 `key_assumptions` 列表序列化为 JSON 字符串
  - [ ] 4.3 使用 UPSERT 避免重复 (按 market_id + created_at)
  - [ ] 4.4 返回插入的 prediction_id
  - [ ] 4.5 记录保存日志 (📊 预测已保存)

- [ ] Task 5: 实现 get_predictions_by_market 方法 (AC: 2)
  - [ ] 5.1 定义方法签名 `async def get_predictions_by_market(market_id: str) -> list[Prediction]`
  - [ ] 5.2 查询指定市场的所有预测
  - [ ] 5.3 按创建时间倒序排列
  - [ ] 5.4 反序列化 `key_assumptions` JSON
  - [ ] 5.5 返回 `Prediction` 模型列表

- [ ] Task 6: 实现 get_pending_predictions 方法 (AC: 2)
  - [ ] 6.1 定义方法签名 `async def get_pending_predictions() -> list[Prediction]`
  - [ ] 6.2 查询关联市场未结算的预测 (resolution_status IS NULL)
  - [ ] 6.3 返回待验证的预测列表
  - [ ] 6.4 记录查询日志

- [ ] Task 7: 实现 get_latest_prediction 方法 (AC: 2)
  - [ ] 7.1 定义方法签名 `async def get_latest_prediction(market_id: str) -> Prediction | None`
  - [ ] 7.2 获取指定市场的最新预测
  - [ ] 7.3 返回单个 `Prediction` 或 `None`

- [ ] Task 8: 实现 update_prediction_result 方法 (AC: 2)
  - [ ] 8.1 定义方法签名 `async def update_prediction_result(prediction_id: int, actual_outcome: str, is_correct: bool)`
  - [ ] 8.2 更新预测的验证结果字段
  - [ ] 8.3 记录更新日志 (用于 Story 6.1)

- [ ] Task 9: 更新模块导出 (AC: All)
  - [ ] 9.1 更新 `src/storage/__init__.py` 导出 `PredictionRepository`
  - [ ] 9.2 更新 `src/storage/repositories/__init__.py`
  - [ ] 9.3 确保 Prediction 模型有数据库兼容字段

- [ ] Task 10: 编写测试 (AC: All)
  - [ ] 10.1 创建 `tests/test_storage/test_prediction_repo.py`
  - [ ] 10.2 测试 `save_prediction()` 成功场景
  - [ ] 10.3 测试 `get_predictions_by_market()` 查询
  - [ ] 10.4 测试 `get_pending_predictions()` 查询
  - [ ] 10.5 测试 `get_latest_prediction()` 查询
  - [ ] 10.6 测试 `update_prediction_result()` 更新
  - [ ] 10.7 测试外键约束 (market_id 必须存在)
  - [ ] 10.8 测试 JSON 序列化/反序列化

- [ ] Task 11: 代码质量检查 (AC: All)
  - [ ] 11.1 运行 `mypy src/storage/repositories/prediction_repo.py` 无错误
  - [ ] 11.2 运行 `black --check src/storage/repositories/` 通过
  - [ ] 11.3 运行 `isort --check src/storage/repositories/` 通过
  - [ ] 11.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md#Data Architecture]

**数据库 Schema (predictions 表):**

```sql
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    predicted_probability REAL,
    confidence REAL,
    reasoning TEXT,
    key_assumptions TEXT,        -- JSON 序列化的列表
    model_used TEXT,
    recommendation TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (market_id) REFERENCES markets(id)
);
```

**扩展字段 (用于预测追踪 - Story 6.1):**

```sql
-- 后续 Story 6.1 需要添加的字段
ALTER TABLE predictions ADD COLUMN actual_outcome TEXT;
ALTER TABLE predictions ADD COLUMN is_correct BOOLEAN;
ALTER TABLE predictions ADD COLUMN validated_at DATETIME;
```

### 已实现的相关模块

**Story 1.6 实现的数据库操作 [Source: src/storage/database.py]:**

```python
from src.storage.database import get_db_connection, init_db

# 数据库连接
async with get_db_connection() as db:
    await db.execute("SELECT * FROM predictions")
    rows = await db.fetchall()
```

**Story 1.7 实现的 Prediction 模型 [Source: src/models/prediction.py]:**

```python
from src.models.prediction import Prediction, PredictionResult

class Prediction(BaseModel):
    """预测记录数据模型."""
    id: int | None = None
    market_id: str
    predicted_probability: float
    confidence: float
    reasoning: str | None = None
    key_assumptions: list[str] | None = None
    model_used: str | None = None
    recommendation: str | None = None
    created_at: datetime | None = None

    # 预测追踪字段 (Story 6.1 使用)
    actual_outcome: str | None = None
    is_correct: bool | None = None
    validated_at: datetime | None = None
```

**Story 3.3 实现的 LLMAnalyzer [Source: src/analysis/llm_analyzer.py]:**

```python
from src.analysis import LLMAnalyzer
from src.models.prediction import PredictionResult

analyzer = LLMAnalyzer()
result = await analyzer.analyze_market(market)

# result 是 PredictionResult，需要转换为 Prediction 存储
prediction = Prediction(
    market_id=market.id,
    predicted_probability=result.predicted_probability,
    confidence=result.confidence,
    reasoning=result.reasoning,
    key_assumptions=result.key_assumptions,
    model_used="glm-4",  # 从配置获取
    recommendation=result.recommendation.value,
)
```

### 项目结构 [Source: architecture.md#Project Structure]

**新增/修改文件:**

```
src/storage/
├── __init__.py                  # 更新: 导出 PredictionRepository
├── database.py                  # 更新: 添加 predictions 表
└── repositories/                # 新增: 数据仓库目录
    ├── __init__.py              # 新增
    └── prediction_repo.py       # 新增: 预测仓库

tests/test_storage/
├── __init__.py                  # 已存在
├── test_database.py             # 已存在
└── test_prediction_repo.py      # 新增: 预测仓库测试
```

### 实现模板

**prediction_repo.py 完整模板:**

```python
# src/storage/repositories/prediction_repo.py
"""Prediction repository for database operations.

This module provides the PredictionRepository class for persisting
and querying LLM prediction records.

Usage:
    from src.storage.repositories import PredictionRepository

    repo = PredictionRepository()
    prediction_id = await repo.save_prediction(prediction)
    predictions = await repo.get_predictions_by_market(market_id)
"""

from __future__ import annotations

__all__ = ["PredictionRepository"]

import json
from datetime import datetime, timezone

import aiosqlite

from src.models.prediction import Prediction
from src.storage.database import get_db_path
from src.utils.logger import OPERATION_EMOJIS, get_logger


class PredictionRepository:
    """预测记录数据仓库.

    提供预测记录的持久化和查询功能。

    Attributes:
        _db_path: 数据库文件路径
        _logger: 日志器

    Example:
        >>> repo = PredictionRepository()
        >>> prediction_id = await repo.save_prediction(prediction)
        >>> predictions = await repo.get_predictions_by_market("market-123")
    """

    def __init__(self, db_path: str | None = None) -> None:
        """初始化预测仓库.

        Args:
            db_path: 数据库文件路径 (可选，默认使用配置路径)
        """
        self._db_path = db_path or get_db_path()
        self._logger = get_logger(__name__)

    async def save_prediction(self, prediction: Prediction) -> int:
        """保存预测记录.

        Args:
            prediction: 预测记录模型

        Returns:
            插入的预测记录 ID

        Raises:
            aiosqlite.Error: 数据库操作错误

        Example:
            >>> prediction = Prediction(
            ...     market_id="market-123",
            ...     predicted_probability=0.75,
            ...     confidence=0.85,
            ...     reasoning="Strong indicators...",
            ... )
            >>> prediction_id = await repo.save_prediction(prediction)
        """
        self._logger.info(
            f"{OPERATION_EMOJIS['data']} Saving prediction for market: "
            f"{prediction.market_id}"
        )

        # 序列化 key_assumptions
        assumptions_json = (
            json.dumps(prediction.key_assumptions)
            if prediction.key_assumptions
            else None
        )

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO predictions (
                    market_id, predicted_probability, confidence,
                    reasoning, key_assumptions, model_used, recommendation
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prediction.market_id,
                    prediction.predicted_probability,
                    prediction.confidence,
                    prediction.reasoning,
                    assumptions_json,
                    prediction.model_used,
                    prediction.recommendation,
                ),
            )
            await db.commit()
            prediction_id = cursor.lastrowid

        self._logger.info(
            f"{OPERATION_EMOJIS['data']} Prediction saved with ID: {prediction_id}"
        )

        return prediction_id

    async def get_predictions_by_market(
        self, market_id: str
    ) -> list[Prediction]:
        """获取指定市场的所有预测记录.

        Args:
            market_id: 市场 ID

        Returns:
            预测记录列表，按创建时间倒序

        Example:
            >>> predictions = await repo.get_predictions_by_market("market-123")
            >>> len(predictions)
            5
        """
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM predictions
                WHERE market_id = ?
                ORDER BY created_at DESC
                """,
                (market_id,),
            )
            rows = await cursor.fetchall()

        return [self._row_to_prediction(row) for row in rows]

    async def get_pending_predictions(self) -> list[Prediction]:
        """获取待验证的预测记录.

        返回关联市场尚未结算的预测记录。

        Returns:
            待验证的预测记录列表

        Example:
            >>> pending = await repo.get_pending_predictions()
            >>> len(pending)
            10
        """
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT p.* FROM predictions p
                JOIN markets m ON p.market_id = m.id
                WHERE m.resolution_status IS NULL
                ORDER BY p.created_at DESC
                """
            )
            rows = await cursor.fetchall()

        self._logger.info(
            f"{OPERATION_EMOJIS['data']} Found {len(rows)} pending predictions"
        )

        return [self._row_to_prediction(row) for row in rows]

    async def get_latest_prediction(
        self, market_id: str
    ) -> Prediction | None:
        """获取指定市场的最新预测.

        Args:
            market_id: 市场 ID

        Returns:
            最新预测记录，如果不存在返回 None

        Example:
            >>> latest = await repo.get_latest_prediction("market-123")
            >>> latest.predicted_probability
            0.75
        """
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM predictions
                WHERE market_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (market_id,),
            )
            row = await cursor.fetchone()

        return self._row_to_prediction(row) if row else None

    async def update_prediction_result(
        self,
        prediction_id: int,
        actual_outcome: str,
        is_correct: bool,
    ) -> None:
        """更新预测的验证结果.

        Args:
            prediction_id: 预测记录 ID
            actual_outcome: 实际结果 (YES/NO)
            is_correct: 预测是否正确

        Example:
            >>> await repo.update_prediction_result(1, "YES", True)
        """
        self._logger.info(
            f"{OPERATION_EMOJIS['data']} Updating prediction {prediction_id}: "
            f"outcome={actual_outcome}, correct={is_correct}"
        )

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                UPDATE predictions
                SET actual_outcome = ?,
                    is_correct = ?,
                    validated_at = ?
                WHERE id = ?
                """,
                (
                    actual_outcome,
                    is_correct,
                    datetime.now(timezone.utc).isoformat(),
                    prediction_id,
                ),
            )
            await db.commit()

    def _row_to_prediction(self, row: aiosqlite.Row) -> Prediction:
        """将数据库行转换为 Prediction 模型.

        Args:
            row: 数据库行

        Returns:
            Prediction 模型实例
        """
        # 反序列化 key_assumptions
        key_assumptions = None
        if row["key_assumptions"]:
            key_assumptions = json.loads(row["key_assumptions"])

        # 解析 created_at
        created_at = None
        if row["created_at"]:
            created_at = datetime.fromisoformat(row["created_at"])

        # 解析 validated_at
        validated_at = None
        if "validated_at" in row.keys() and row["validated_at"]:
            validated_at = datetime.fromisoformat(row["validated_at"])

        return Prediction(
            id=row["id"],
            market_id=row["market_id"],
            predicted_probability=row["predicted_probability"],
            confidence=row["confidence"],
            reasoning=row["reasoning"],
            key_assumptions=key_assumptions,
            model_used=row["model_used"],
            recommendation=row["recommendation"],
            created_at=created_at,
            actual_outcome=row["actual_outcome"]
            if "actual_outcome" in row.keys()
            else None,
            is_correct=bool(row["is_correct"])
            if "is_correct" in row.keys() and row["is_correct"] is not None
            else None,
            validated_at=validated_at,
        )
```

**database.py 更新 (添加 predictions 表):**

```python
# 在 init_db() 函数中添加:

async def init_db() -> None:
    """初始化数据库和表结构."""
    # ... 现有代码 ...

    # 创建 predictions 表
    await db.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_id TEXT NOT NULL,
            predicted_probability REAL,
            confidence REAL,
            reasoning TEXT,
            key_assumptions TEXT,
            model_used TEXT,
            recommendation TEXT,
            actual_outcome TEXT,
            is_correct BOOLEAN,
            validated_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (market_id) REFERENCES markets(id)
        )
    """)

    # 创建索引
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_predictions_market_id
        ON predictions(market_id)
    """)

    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_predictions_created_at
        ON predictions(created_at)
    """)
```

### 测试策略

```python
# tests/test_storage/test_prediction_repo.py
"""Tests for prediction repository."""

from __future__ import annotations

import pytest
import aiosqlite
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import os

from src.storage.repositories.prediction_repo import PredictionRepository
from src.models.prediction import Prediction
from src.models.market import Market


@pytest.fixture
async def temp_db():
    """创建临时数据库."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # 初始化表结构
    async with aiosqlite.connect(db_path) as db:
        # 创建 markets 表
        await db.execute("""
            CREATE TABLE markets (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT,
                yes_price REAL,
                no_price REAL,
                liquidity REAL,
                deadline DATETIME,
                resolution_status TEXT,
                resolution_outcome TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建 predictions 表
        await db.execute("""
            CREATE TABLE predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                predicted_probability REAL,
                confidence REAL,
                reasoning TEXT,
                key_assumptions TEXT,
                model_used TEXT,
                recommendation TEXT,
                actual_outcome TEXT,
                is_correct BOOLEAN,
                validated_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (market_id) REFERENCES markets(id)
            )
        """)
        await db.commit()

    yield db_path

    # 清理
    os.unlink(db_path)


@pytest.fixture
async def repo(temp_db) -> PredictionRepository:
    """创建仓库实例."""
    return PredictionRepository(db_path=temp_db)


@pytest.fixture
async def sample_market(temp_db) -> str:
    """创建示例市场并返回 ID."""
    async with aiosqlite.connect(temp_db) as db:
        await db.execute(
            """
            INSERT INTO markets (id, title, yes_price, no_price)
            VALUES (?, ?, ?, ?)
            """,
            ("test-market-123", "Will X happen?", 0.65, 0.35),
        )
        await db.commit()
    return "test-market-123"


class TestPredictionRepository:
    """测试 PredictionRepository 类."""

    @pytest.mark.asyncio
    async def test_save_prediction(
        self, repo: PredictionRepository, sample_market: str
    ) -> None:
        """测试保存预测."""
        prediction = Prediction(
            market_id=sample_market,
            predicted_probability=0.75,
            confidence=0.85,
            reasoning="Strong indicators...",
            key_assumptions=["Economic stability", "Policy support"],
            model_used="glm-4",
            recommendation="BUY_YES",
        )

        prediction_id = await repo.save_prediction(prediction)
        assert prediction_id > 0

    @pytest.mark.asyncio
    async def test_get_predictions_by_market(
        self, repo: PredictionRepository, sample_market: str
    ) -> None:
        """测试获取市场预测."""
        # 保存两个预测
        prediction1 = Prediction(
            market_id=sample_market,
            predicted_probability=0.75,
            confidence=0.85,
            recommendation="BUY_YES",
        )
        prediction2 = Prediction(
            market_id=sample_market,
            predicted_probability=0.70,
            confidence=0.80,
            recommendation="BUY_YES",
        )

        await repo.save_prediction(prediction1)
        await repo.save_prediction(prediction2)

        # 获取预测
        predictions = await repo.get_predictions_by_market(sample_market)

        assert len(predictions) == 2
        # 按时间倒序，最新的在前
        assert predictions[0].predicted_probability == 0.70
        assert predictions[1].predicted_probability == 0.75

    @pytest.mark.asyncio
    async def test_get_latest_prediction(
        self, repo: PredictionRepository, sample_market: str
    ) -> None:
        """测试获取最新预测."""
        # 保存两个预测
        prediction1 = Prediction(
            market_id=sample_market,
            predicted_probability=0.75,
            confidence=0.85,
            recommendation="BUY_YES",
        )
        prediction2 = Prediction(
            market_id=sample_market,
            predicted_probability=0.70,
            confidence=0.80,
            recommendation="BUY_YES",
        )

        await repo.save_prediction(prediction1)
        await repo.save_prediction(prediction2)

        # 获取最新预测
        latest = await repo.get_latest_prediction(sample_market)

        assert latest is not None
        assert latest.predicted_probability == 0.70  # 最新的

    @pytest.mark.asyncio
    async def test_get_latest_prediction_not_found(
        self, repo: PredictionRepository
    ) -> None:
        """测试获取不存在市场的预测."""
        latest = await repo.get_latest_prediction("non-existent-market")
        assert latest is None

    @pytest.mark.asyncio
    async def test_key_assumptions_serialization(
        self, repo: PredictionRepository, sample_market: str
    ) -> None:
        """测试 key_assumptions JSON 序列化."""
        prediction = Prediction(
            market_id=sample_market,
            predicted_probability=0.75,
            confidence=0.85,
            key_assumptions=["Assumption 1", "Assumption 2", "Assumption 3"],
            recommendation="BUY_YES",
        )

        await repo.save_prediction(prediction)
        predictions = await repo.get_predictions_by_market(sample_market)

        assert len(predictions) == 1
        assert predictions[0].key_assumptions == [
            "Assumption 1",
            "Assumption 2",
            "Assumption 3",
        ]

    @pytest.mark.asyncio
    async def test_update_prediction_result(
        self, repo: PredictionRepository, sample_market: str
    ) -> None:
        """测试更新预测结果."""
        prediction = Prediction(
            market_id=sample_market,
            predicted_probability=0.75,
            confidence=0.85,
            recommendation="BUY_YES",
        )

        prediction_id = await repo.save_prediction(prediction)

        # 更新结果
        await repo.update_prediction_result(
            prediction_id=prediction_id,
            actual_outcome="YES",
            is_correct=True,
        )

        # 验证更新
        predictions = await repo.get_predictions_by_market(sample_market)
        assert predictions[0].actual_outcome == "YES"
        assert predictions[0].is_correct is True
        assert predictions[0].validated_at is not None

    @pytest.mark.asyncio
    async def test_get_pending_predictions(
        self, repo: PredictionRepository, temp_db: str, sample_market: str
    ) -> None:
        """测试获取待验证预测."""
        # 保存预测
        prediction = Prediction(
            market_id=sample_market,
            predicted_probability=0.75,
            confidence=0.85,
            recommendation="BUY_YES",
        )
        await repo.save_prediction(prediction)

        # 市场未结算，应该在待验证列表中
        pending = await repo.get_pending_predictions()
        assert len(pending) == 1

        # 更新市场为已结算
        async with aiosqlite.connect(temp_db) as db:
            await db.execute(
                "UPDATE markets SET resolution_status = 'RESOLVED' WHERE id = ?",
                (sample_market,),
            )
            await db.commit()

        # 市场已结算，不应该在待验证列表中
        pending = await repo.get_pending_predictions()
        assert len(pending) == 0
```

### 依赖关系

**本故事依赖:**
- Story 1.2: 配置管理系统 (数据库路径)
- Story 1.6: 数据库初始化 (init_db, get_db_connection)
- Story 1.7: Pydantic 数据模型 (Prediction)
- Story 3.3: LLM 分析引擎 (PredictionResult)

**后续故事依赖本故事:**
- Story 3.5: Edge 计算 (需要 save_prediction 存储预测)
- Story 5.3: 交易决策流程 (需要 save_prediction 存储预测)
- Story 6.1: 预测结果验证机制 (需要 get_pending_predictions, update_prediction_result)
- Story 6.2: 准确率统计 (需要预测数据)

### 实现注意事项

**关键点:**

1. **异步数据库操作** - 所有方法使用 `async/await` 和 aiosqlite
2. **JSON 序列化** - `key_assumptions` 需要序列化为 JSON 字符串存储
3. **外键约束** - 保存预测前必须确保 market_id 存在于 markets 表
4. **索引优化** - 为 `market_id` 和 `created_at` 创建索引提高查询性能
5. **日志记录** - 使用 emoji 标记操作状态 (📊 数据操作)

**与 Story 3.3 的集成:**

```python
from src.analysis import LLMAnalyzer
from src.storage.repositories import PredictionRepository
from src.config import settings

async def analyze_and_save(market: Market) -> Prediction:
    """分析市场并保存预测."""
    analyzer = LLMAnalyzer()
    repo = PredictionRepository()

    # 1. LLM 分析
    result = await analyzer.analyze_market(market)

    # 2. 转换为 Prediction 模型
    prediction = Prediction(
        market_id=market.id,
        predicted_probability=result.predicted_probability,
        confidence=result.confidence,
        reasoning=result.reasoning,
        key_assumptions=result.key_assumptions,
        model_used=settings.llm.model,
        recommendation=result.recommendation.value,
    )

    # 3. 保存到数据库
    prediction_id = await repo.save_prediction(prediction)
    prediction.id = prediction_id

    return prediction
```

### 前一个故事学习 [Source: 3-3-llm-analysis-engine.md]

**从 Story 3.3 学到的模式:**

1. **使用 `from __future__ import annotations`** - 支持 Python 3.10+ 类型语法
2. **类型注解使用 `str | None`** - 而非 `Optional[str]`
3. **类型注解使用 `list[X]`** - 而非 `List[X]`
4. **完整 docstring** - 包含 Args, Returns, Raises, Example
5. **单元测试覆盖** - 正常情况 + 边界情况 + 错误情况
6. **`__all__` 导出列表** - 明确模块公共 API
7. **Emoji 日志** - 使用 OPERATION_EMOJIS 字典
8. **异步上下文管理器** - 使用 `async with` 管理资源

### References

- [Source: architecture.md#Data Architecture] - 数据库 Schema
- [Source: architecture.md#Project Structure] - 项目结构
- [Source: src/storage/database.py] - 数据库操作
- [Source: src/models/prediction.py] - Prediction 模型
- [Source: src/analysis/llm_analyzer.py] - LLMAnalyzer 输出 PredictionResult
- [Source: epics.md#Story 3.4] - 原始 Story 定义
- [Source: 3-3-llm-analysis-engine.md] - 前一个故事参考

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
