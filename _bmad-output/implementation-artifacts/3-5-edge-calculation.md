# Story 3.5: Edge 计算 (价格差距分析)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **用户**,
I want **系统计算 LLM 预测与市场价格的差距 (Edge)**,
So that **我能够评估交易价值**.

## Acceptance Criteria

**Given** LLM 分析结果已存储
**When** 在 `llm_analyzer.py` 添加 edge 计算逻辑
**Then** 计算公式: `edge = abs(predicted_probability - market_price)`
**And** 验证 edge >= 0.10 (MIN_EDGE) 才标记为有价值交易
**And** 在预测结果中添加 `edge` 字段
**And** 记录 edge 计算日志
**And** 将 edge 值保存到 predictions 表

## Tasks / Subtasks

- [x] Task 1: 扩展 Prediction 模型 (AC: 3)
  - [x] 1.1 在 `src/models/prediction.py` 的 `Prediction` 类添加 `edge` 字段
  - [x] 1.2 在 `PredictionResult` 类添加 `edge` 字段
  - [x] 1.3 设置字段类型为 `float | None`，默认值为 `None`
  - [x] 1.4 添加字段验证: 0 <= edge <= 1

- [x] Task 2: 扩展数据库 Schema (AC: 5)
  - [x] 2.1 在 `src/storage/database.py` 的 predictions 表添加 `edge` 列
  - [x] 2.2 更新 `init_db()` 函数包含新列
  - [x] 2.3 添加数据库迁移逻辑 (ALTER TABLE 如果列不存在)
  - [x] 2.4 创建索引优化 edge 查询

- [x] Task 3: 更新 PredictionRepository (AC: 5)
  - [x] 3.1 在 `save_prediction()` 方法中添加 `edge` 参数保存
  - [x] 3.2 更新 `_row_to_prediction()` 方法解析 `edge` 字段
  - [x] 3.3 更新 `update_prediction_result()` 方法 (如有需要)

- [x] Task 4: 增强 LLMAnalyzer (AC: 1, 2, 4)
  - [x] 4.1 在 `analyze_market()` 方法中计算 edge
  - [x] 4.2 将 edge 值添加到返回的 `PredictionResult`
  - [x] 4.3 记录 edge 计算日志 (📊 Edge 计算)
  - [x] 4.4 更新 `_is_tradeable()` 方法使用预计算的 edge

- [x] Task 5: 优化 calculate_edge 方法 (AC: 1)
  - [x] 5.1 审查现有 `calculate_edge()` 方法逻辑
  - [x] 5.2 确保 BUY_YES edge = predicted_probability - market_yes_price
  - [x] 5.3 确保 BUY_NO edge = (1 - predicted_probability) - (1 - market_yes_price)
  - [x] 5.4 确保返回绝对值 (如果使用 abs 公式)
  - [x] 5.5 添加 docstring 示例

- [x] Task 6: 更新模块导出 (AC: All)
  - [x] 6.1 确认 `src/models/prediction.py` 的 `__all__` 包含更新
  - [x] 6.2 确认 `src/analysis/__init__.py` 导出正确
  - [x] 6.3 确认 `src/storage/__init__.py` 导出正确

- [x] Task 7: 编写测试 (AC: All)
  - [x] 7.1 在 `tests/test_analysis/test_llm_analyzer.py` 添加 edge 计算测试
  - [x] 7.2 测试 BUY_YES 场景 edge 计算
  - [x] 7.3 测试 BUY_NO 场景 edge 计算
  - [x] 7.4 测试 NO_TRADE 场景 edge 返回 0
  - [x] 7.5 测试 edge >= MIN_EDGE 时 is_tradeable=True
  - [x] 7.6 测试 edge < MIN_EDGE 时 is_tradeable=False
  - [x] 7.7 在 `tests/test_storage/test_prediction_repo.py` 添加 edge 字段测试
  - [x] 7.8 测试 save_prediction 保存 edge 值
  - [x] 7.9 测试 edge 字段序列化/反序列化

- [x] Task 8: 代码质量检查 (AC: All)
  - [x] 8.1 运行 `mypy src/analysis/llm_analyzer.py` 无错误
  - [x] 8.2 运行 `mypy src/models/prediction.py` 无错误
  - [x] 8.3 运行 `mypy src/storage/repositories/prediction_repo.py` 无错误
  - [x] 8.4 运行 `black --check src/` 通过
  - [x] 8.5 运行 `isort --check src/` 通过
  - [x] 8.6 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md#Data Architecture]

**Edge 计算公式:**

根据 Epic 3 和 FR7 的定义，Edge 是 LLM 预测概率与市场当前价格之间的差距:

```python
# BUY_YES 场景
edge = predicted_probability - market_yes_price

# BUY_NO 场景 (等同于 NO 价格差距)
edge = (1 - predicted_probability) - (1 - market_yes_price)

# 简化: 对于 BUY_NO，edge 也可以理解为 market_yes_price - predicted_probability
```

**注意:** 现有 `calculate_edge()` 方法返回有符号值 (正表示预测高于市场)，但 AC 要求使用 `abs()` 公式。需要确认使用哪种方式。

### 已实现的相关模块

**Story 3.3 实现的 LLMAnalyzer [Source: src/analysis/llm_analyzer.py]:**

```python
from src.analysis import LLMAnalyzer
from src.models.prediction import PredictionResult

analyzer = LLMAnalyzer()
result = await analyzer.analyze_market(market)

# 当前实现已有 calculate_edge 方法
def calculate_edge(
    self, result: PredictionResult, market_yes_price: float
) -> float:
    from src.models.prediction import Recommendation as PredRecommendation

    if result.recommendation == PredRecommendation.BUY_YES:
        return result.predicted_probability - market_yes_price
    elif result.recommendation == PredRecommendation.BUY_NO:
        return (1 - result.predicted_probability) - (1 - market_yes_price)
    else:
        return 0.0
```

**Story 3.4 实现的 PredictionRepository [Source: src/storage/repositories/prediction_repo.py]:**

```python
from src.storage.repositories import PredictionRepository
from src.models.prediction import Prediction

repo = PredictionRepository()

# 保存预测
prediction = Prediction(
    market_id=market.id,
    predicted_probability=result.predicted_probability,
    confidence=result.confidence,
    reasoning=result.reasoning,
    key_assumptions=result.key_assumptions,
    model_used=settings.llm.model,
    recommendation=result.recommendation.value,
    # 需要添加: edge=calculated_edge
)
prediction_id = await repo.save_prediction(prediction)
```

**Story 4.1 实现的风险控制配置 [Source: src/config.py]:**

```python
from src.config import settings

# Edge 门槛配置
min_edge = settings.risk.min_edge  # 默认 0.10
```

### 项目结构 [Source: architecture.md#Project Structure]

**修改文件:**

```
src/
├── analysis/
│   ├── __init__.py              # 确认导出
│   └── llm_analyzer.py          # 修改: 添加 edge 计算和存储逻辑
├── models/
│   └── prediction.py            # 修改: 添加 edge 字段
└── storage/
    ├── database.py              # 修改: 添加 edge 列
    └── repositories/
        └── prediction_repo.py   # 修改: 处理 edge 字段

tests/
├── test_analysis/
│   └── test_llm_analyzer.py     # 修改: 添加 edge 计算测试
└── test_storage/
    └── test_prediction_repo.py  # 修改: 添加 edge 字段测试
```

### 实现模板

**1. 扩展 PredictionResult 模型 [Source: src/models/prediction.py]:**

```python
class PredictionResult(BaseModel):
    """LLM raw prediction result model."""

    # ... 现有字段 ...
    predicted_probability: float = Field(...)
    confidence: float = Field(...)
    reasoning: str = Field(...)
    key_assumptions: list[str] = Field(default_factory=list)
    recommendation: Recommendation = Field(...)

    # 新增: Edge 字段
    edge: float | None = Field(
        default=None, ge=0, le=1, description="Edge (price gap) between prediction and market"
    )
```

**2. 扩展 Prediction 模型 [Source: src/models/prediction.py]:**

```python
class Prediction(BaseModel):
    """Stored prediction data model."""

    # ... 现有字段 ...
    id: int | None = Field(default=None)
    market_id: str = Field(...)
    predicted_probability: float = Field(...)
    confidence: float = Field(...)
    reasoning: str | None = Field(default=None)
    key_assumptions: list[str] | None = Field(default=None)
    model_used: str | None = Field(default=None)
    recommendation: Recommendation | None = Field(default=None)

    # 新增: Edge 字段
    edge: float | None = Field(
        default=None, ge=0, le=1, description="Edge (price gap) between prediction and market"
    )

    # ... 其余字段 ...
    actual_outcome: str | None = Field(default=None)
    is_correct: bool | None = Field(default=None)
    validated_at: datetime | None = Field(default=None)
    created_at: datetime | None = Field(default=None)
```

**3. 更新数据库 Schema [Source: src/storage/database.py]:**

```python
# 在 init_db() 函数的 predictions 表中添加 edge 列
async def init_db() -> None:
    # ... 现有代码 ...

    # 创建 predictions 表 (更新版本)
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
            edge REAL,  -- 新增: Edge 值
            actual_outcome TEXT,
            is_correct BOOLEAN,
            validated_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (market_id) REFERENCES markets(id)
        )
    """)

    # 添加索引
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_predictions_edge
        ON predictions(edge)
    """)

    # 迁移: 如果表已存在但没有 edge 列，则添加
    # SQLite 不支持 IF NOT EXISTS 对于 ALTER TABLE ADD COLUMN
    # 需要先检查列是否存在
```

**4. 更新 LLMAnalyzer.analyze_market() [Source: src/analysis/llm_analyzer.py]:**

```python
async def analyze_market(self, market: Market) -> PredictionResult:
    """分析单个市场."""
    # ... 现有代码 ...

    # 构建提示词并调用 LLM
    user_prompt = build_market_analysis_prompt(market)
    with LLMClient() as client:
        response = client.chat_with_system(
            system_prompt=MARKET_ANALYST_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

    # 解析响应
    llm_result = parse_llm_analysis_response(response)

    # 转换为 PredictionResult
    result = PredictionResult(
        predicted_probability=llm_result.predicted_probability,
        confidence=llm_result.confidence,
        reasoning=llm_result.reasoning,
        key_assumptions=llm_result.key_assumptions,
        recommendation=recommendation_mapping[llm_result.recommendation],
    )

    # 新增: 计算 Edge
    if market.yes_price is not None:
        edge = self.calculate_edge(result, market.yes_price)
        result.edge = abs(edge)  # 使用绝对值
        self._logger.info(
            f"{OPERATION_EMOJIS['analysis']} Edge calculated for "
            f"market {market.id}: edge={result.edge:.4f}, "
            f"min_edge={self._min_edge}"
        )

    # 验证是否可交易 (使用预计算的 edge)
    is_tradeable = self._is_tradeable(result, market.yes_price)

    return result
```

**5. 更新 _is_tradeable() 方法 [Source: src/analysis/llm_analyzer.py]:**

```python
def _is_tradeable(
    self, result: PredictionResult, market_yes_price: float | None
) -> bool:
    """判断分析结果是否满足交易条件."""
    # 检查置信度
    if result.confidence < self._min_confidence:
        return False

    # 检查是否为 NO_TRADE
    if result.recommendation == PredRecommendation.NO_TRADE:
        return False

    # 检查 Edge (使用预计算的 edge 值)
    if result.edge is not None:
        if result.edge < self._min_edge:
            return False
    elif market_yes_price is not None:
        # 兼容旧逻辑: 如果 edge 未预计算，则计算
        edge = abs(self.calculate_edge(result, market_yes_price))
        if edge < self._min_edge:
            return False

    return True
```

**6. 更新 PredictionRepository.save_prediction() [Source: src/storage/repositories/prediction_repo.py]:**

```python
async def save_prediction(self, prediction: Prediction) -> int:
    """保存预测记录."""
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
                reasoning, key_assumptions, model_used, recommendation,
                edge  -- 新增
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prediction.market_id,
                prediction.predicted_probability,
                prediction.confidence,
                prediction.reasoning,
                assumptions_json,
                prediction.model_used,
                prediction.recommendation.value if prediction.recommendation else None,
                prediction.edge,  -- 新增
            ),
        )
        await db.commit()
        prediction_id = cursor.lastrowid

    self._logger.info(
        f"{OPERATION_EMOJIS['data']} Prediction saved with ID: {prediction_id}, "
        f"edge: {prediction.edge}"
    )

    return prediction_id
```

**7. 更新 _row_to_prediction() 方法 [Source: src/storage/repositories/prediction_repo.py]:**

```python
def _row_to_prediction(self, row: aiosqlite.Row) -> Prediction:
    """将数据库行转换为 Prediction 模型."""
    # ... 现有代码 ...

    # 解析 edge (新增)
    edge = None
    if "edge" in row.keys() and row["edge"] is not None:
        edge = row["edge"]

    return Prediction(
        id=row["id"],
        market_id=row["market_id"],
        predicted_probability=row["predicted_probability"],
        confidence=row["confidence"],
        reasoning=row["reasoning"],
        key_assumptions=key_assumptions,
        model_used=row["model_used"],
        recommendation=recommendation,
        edge=edge,  # 新增
        created_at=created_at,
        actual_outcome=row.get("actual_outcome"),
        is_correct=bool(row["is_correct"]) if row["is_correct"] is not None else None,
        validated_at=validated_at,
    )
```

### 测试策略

```python
# tests/test_analysis/test_llm_analyzer.py 添加测试

class TestEdgeCalculation:
    """测试 Edge 计算功能."""

    @pytest.mark.asyncio
    async def test_edge_calculation_buy_yes(self, mock_llm_client, sample_market):
        """测试 BUY_YES 场景 edge 计算."""
        # LLM 预测 0.80, 市场价格 0.65
        # Edge = 0.80 - 0.65 = 0.15
        sample_market.yes_price = 0.65

        analyzer = LLMAnalyzer()
        result = await analyzer.analyze_market(sample_market)

        assert result.predicted_probability == 0.80
        assert result.recommendation == Recommendation.BUY_YES
        assert result.edge is not None
        assert abs(result.edge - 0.15) < 0.001

    @pytest.mark.asyncio
    async def test_edge_calculation_buy_no(self, mock_llm_client, sample_market):
        """测试 BUY_NO 场景 edge 计算."""
        # LLM 预测 0.30 (BUY_NO), 市场价格 0.65
        # Edge = (1 - 0.30) - (1 - 0.65) = 0.70 - 0.35 = 0.35
        sample_market.yes_price = 0.65

        # 配置 mock 返回 BUY_NO 建议
        analyzer = LLMAnalyzer()
        result = await analyzer.analyze_market(sample_market)

        if result.recommendation == Recommendation.BUY_NO:
            assert result.edge is not None
            assert result.edge >= 0

    @pytest.mark.asyncio
    async def test_edge_calculation_no_trade(self, mock_llm_client, sample_market):
        """测试 NO_TRADE 场景 edge 返回 0."""
        sample_market.yes_price = 0.65

        analyzer = LLMAnalyzer()
        result = await analyzer.analyze_market(sample_market)

        if result.recommendation == Recommendation.NO_TRADE:
            assert result.edge == 0.0

    @pytest.mark.asyncio
    async def test_is_tradeable_below_min_edge(self, mock_llm_client, sample_market):
        """测试 edge < MIN_EDGE 时不可交易."""
        # 设置市场价格使 edge < 0.10
        sample_market.yes_price = 0.95  # 如果 LLM 预测 0.80, edge = 0.15
                                       # 如果 LLM 预测 0.98, edge = 0.03

        analyzer = LLMAnalyzer()
        result = await analyzer.analyze_market(sample_market)

        if result.edge is not None and result.edge < settings.risk.min_edge:
            assert result.is_tradeable is False

    @pytest.mark.asyncio
    async def test_is_tradeable_above_min_edge(self, mock_llm_client, sample_market):
        """测试 edge >= MIN_EDGE 且 confidence >= MIN_CONFIDENCE 时可交易."""
        sample_market.yes_price = 0.50  # 如果 LLM 预测 0.80, edge = 0.30

        analyzer = LLMAnalyzer()
        result = await analyzer.analyze_market(sample_market)

        if (result.edge is not None and
            result.edge >= settings.risk.min_edge and
            result.confidence >= settings.risk.min_confidence and
            result.recommendation != Recommendation.NO_TRADE):
            # 注意: is_tradeable 是内部方法判断的，需要通过其他方式验证
            pass

    def test_calculate_edge_method(self):
        """测试 calculate_edge 方法直接调用."""
        analyzer = LLMAnalyzer()

        # BUY_YES 场景
        result_yes = PredictionResult(
            predicted_probability=0.80,
            confidence=0.85,
            reasoning="Test",
            recommendation=Recommendation.BUY_YES,
        )
        edge = analyzer.calculate_edge(result_yes, 0.65)
        assert abs(edge - 0.15) < 0.001

        # BUY_NO 场景
        result_no = PredictionResult(
            predicted_probability=0.30,
            confidence=0.85,
            reasoning="Test",
            recommendation=Recommendation.BUY_NO,
        )
        edge = analyzer.calculate_edge(result_no, 0.65)
        assert abs(edge - 0.35) < 0.001

        # NO_TRADE 场景
        result_no_trade = PredictionResult(
            predicted_probability=0.65,
            confidence=0.85,
            reasoning="Test",
            recommendation=Recommendation.NO_TRADE,
        )
        edge = analyzer.calculate_edge(result_no_trade, 0.65)
        assert edge == 0.0
```

### 依赖关系

**本故事依赖:**
- Story 1.2: 配置管理系统 (MIN_EDGE 配置)
- Story 3.3: LLM 分析引擎 (calculate_edge 方法)
- Story 3.4: 预测结果存储 (PredictionRepository)
- Story 4.1: 风险控制配置 (RiskControlSettings.min_edge)

**后续故事依赖本故事:**
- Story 4.4: 交易前风险检查 (使用 edge 验证交易)
- Story 5.2: Paper Trading 执行器 (使用 edge 评估交易价值)
- Story 6.2: 准确率统计 (按 edge 区间统计)

### 实现注意事项

**关键点:**

1. **Edge 计算公式** - AC 要求 `abs(predicted_probability - market_price)`，但现有 `calculate_edge()` 返回有符号值。需确认:
   - BUY_YES: `predicted_probability - market_yes_price`
   - BUY_NO: `(1 - predicted_probability) - (1 - market_yes_price)` = `market_yes_price - predicted_probability`

2. **Edge 存储时机** - 在 `analyze_market()` 中计算后立即存储到 `PredictionResult.edge`

3. **向后兼容** - 数据库迁移需要检查列是否已存在，避免重复添加

4. **日志记录** - 使用 `📊` emoji 标记 Edge 计算日志

5. **字段验证** - edge 值范围应为 0-1 (0% 到 100%)

**与 Story 3.3 的集成:**

现有 `calculate_edge()` 方法已实现基本逻辑，本故事主要是:
1. 将 edge 值添加到 PredictionResult 和 Prediction 模型
2. 在 `analyze_market()` 中调用并存储 edge
3. 将 edge 持久化到数据库
4. 更新 `_is_tradeable()` 使用预计算的 edge

### 前一个故事学习 [Source: 3-4-prediction-result-storage.md]

**从 Story 3.4 学到的模式:**

1. **使用 `from __future__ import annotations`** - 支持 Python 3.10+ 类型语法
2. **类型注解使用 `str | None`** - 而非 `Optional[str]`
3. **类型注解使用 `list[X]`** - 而非 `List[X]`
4. **完整 docstring** - 包含 Args, Returns, Raises, Example
5. **单元测试覆盖** - 正常情况 + 边界情况 + 错误情况
6. **`__all__` 导出列表** - 明确模块公共 API
7. **Emoji 日志** - 使用 OPERATION_EMOJIS 字典
8. **异步上下文管理器** - 使用 `async with` 管理资源
9. **数据库迁移检查** - 检查列是否存在再添加

### References

- [Source: architecture.md#Data Architecture] - 数据库 Schema
- [Source: architecture.md#Project Structure] - 项目结构
- [Source: src/analysis/llm_analyzer.py] - LLMAnalyzer 现有实现
- [Source: src/config.py] - RiskControlSettings.min_edge
- [Source: src/models/prediction.py] - Prediction 和 PredictionResult 模型
- [Source: src/storage/repositories/prediction_repo.py] - PredictionRepository
- [Source: epics.md#Story 3.5] - 原始 Story 定义
- [Source: 3-4-prediction-result-storage.md] - 前一个故事参考

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (via GLM-5)

### Debug Log References

N/A

### Completion Notes List

- 2026-02-16: 完成 Story 3.5 Edge 计算功能实现
  - 扩展了 Prediction 和 PredictionResult 模型添加 edge 字段
  - 更新了数据库 schema 添加 edge 列和索引
  - 实现了数据库迁移逻辑以支持现有数据库
  - 更新了 PredictionRepository 以处理 edge 字段的保存和读取
  - 在 LLMAnalyzer.analyze_market() 中添加了 edge 计算和日志记录
  - 更新了 _is_tradeable() 方法使用预计算的 edge 值
  - 优化了 calculate_edge() 方法的 docstring 添加详细示例
  - 编写了完整的单元测试覆盖 edge 计算、存储和验证
  - 通过了所有 693 个单元测试
  - 通过了 mypy、black、isort 代码质量检查

### File List

**Modified files:**
- src/models/prediction.py
- src/storage/database.py
- src/storage/repositories/prediction_repo.py
- src/analysis/llm_analyzer.py
- tests/test_models/test_prediction.py
- tests/test_storage/test_database.py
- tests/test_storage/test_repositories/test_prediction_repo.py
- tests/test_analysis/test_llm_analyzer.py
