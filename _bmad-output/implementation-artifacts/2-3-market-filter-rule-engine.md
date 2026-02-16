# Story 2.3: 市场筛选规则引擎

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **用户**,
I want **系统根据筛选规则过滤市场**,
So that **只保留适合分析的高质量市场**.

## Acceptance Criteria

**Given** 市场数据已存储在数据库
**When** 实现 `src/analysis/market_filter.py`
**Then** 实现以下筛选规则:
- 流动性筛选: `liquidity >= MIN_LIQUIDITY` (默认 $10,000)
- 截止日期筛选: `deadline >= MIN_DEADLINE_DAYS` (默认 7 天)
- 目标领域筛选: 政治、商业、科技、经济、加密货币
**And** 实现排除规则:
- 标题包含 "price", "USD", "tomorrow"
- 流动性 < $5,000
- 截止日期 < 3 天
- 描述中有争议性条款
**And** 返回 `filtered_markets` 列表
**And** 记录筛选统计（原始数量 → 筛选后数量）
**And** 处理空结果和边界情况

## Tasks / Subtasks

- [x] Task 1: 创建筛选器基础结构 (AC: 1)
  - [x] 1.1 创建 `src/analysis/__init__.py` (如不存在)
  - [x] 1.2 创建 `src/analysis/market_filter.py`
  - [x] 1.3 实现 `MarketFilter` 类
  - [x] 1.4 定义 `FilterRule` 数据类用于规则配置
  - [x] 1.5 添加类型注解 (Python 3.10+ 语法)

- [x] Task 2: 实现流动性筛选 (AC: 1)
  - [x] 2.1 实现 `_filter_by_liquidity()` 方法
  - [x] 2.2 使用配置 `MIN_LIQUIDITY` (默认 $10,000)
  - [x] 2.3 硬性排除: 流动性 < $5,000
  - [x] 2.4 记录因流动性排除的市场数量

- [x] Task 3: 实现截止日期筛选 (AC: 1)
  - [x] 3.1 实现 `_filter_by_deadline()` 方法
  - [x] 3.2 使用配置 `MIN_DEADLINE_DAYS` (默认 7 天)
  - [x] 3.3 硬性排除: 截止日期 < 3 天
  - [x] 3.4 处理无截止日期的市场 (默认排除)
  - [x] 3.5 记录因截止日期排除的市场数量

- [x] Task 4: 实现类别筛选 (AC: 1)
  - [x] 4.1 实现 `_filter_by_category()` 方法
  - [x] 4.2 定义目标类别: POLITICS, BUSINESS, TECH, ECONOMICS, CRYPTO
  - [x] 4.3 处理无类别的市场 (默认保留)
  - [x] 4.4 记录因类别排除的市场数量

- [x] Task 5: 实现排除规则 (AC: 2)
  - [x] 5.1 实现 `_apply_exclusion_rules()` 方法
  - [x] 5.2 标题关键词排除: "price", "USD", "tomorrow" (大小写不敏感)
  - [x] 5.3 争议性条款排除: 可配置的关键词列表
  - [x] 5.4 记录因排除规则跳过的市场

- [x] Task 6: 实现主筛选流程 (AC: 3, 4)
  - [x] 6.1 实现 `filter_markets(markets: list[Market])` 方法
  - [x] 6.2 按顺序应用所有筛选规则
  - [x] 6.3 收集并返回 `filtered_markets` 列表
  - [x] 6.4 记录完整筛选统计 (原始 → 最终)
  - [x] 6.5 返回 `FilterResult` 包含筛选后列表和统计信息

- [x] Task 7: 集成配置系统 (AC: 1, 2)
  - [x] 7.1 在 `src/config.py` 添加筛选配置项
  - [x] 7.2 `MIN_LIQUIDITY: float = 10000.0`
  - [x] 7.3 `MIN_DEADLINE_DAYS: int = 7`
  - [x] 7.4 `EXCLUDED_KEYWORDS: list[str]` 配置
  - [x] 7.5 更新 `.env.example` 文件

- [x] Task 8: 添加日志记录 (AC: 4)
  - [x] 8.1 使用 get_logger 获取 logger 实例
  - [x] 8.2 使用数据 Emoji (📊) 记录筛选统计
  - [x] 8.3 记录每个筛选阶段的通过/排除数量
  - [x] 8.4 记录最终筛选结果

- [x] Task 9: 更新模块导出 (AC: All)
  - [x] 9.1 更新 `src/analysis/__init__.py` 导出 MarketFilter
  - [x] 9.2 更新 `src/__init__.py` (如需要)
  - [x] 9.3 添加模块级 docstring

- [x] Task 10: 编写测试 (AC: All)
  - [x] 10.1 创建 `tests/test_analysis/__init__.py`
  - [x] 10.2 创建 `tests/test_analysis/test_market_filter.py`
  - [x] 10.3 测试流动性筛选 (边界值: $5,000, $10,000)
  - [x] 10.4 测试截止日期筛选 (边界值: 3天, 7天)
  - [x] 10.5 测试类别筛选
  - [x] 10.6 测试排除规则 (关键词匹配)
  - [x] 10.7 测试空列表处理
  - [x] 10.8 测试无截止日期/无类别市场
  - [x] 10.9 使用 pytest.fixture 创建测试数据

- [x] Task 11: 代码质量检查 (AC: All)
  - [x] 11.1 运行 `mypy src/analysis/` 无错误
  - [x] 11.2 运行 `black --check src/analysis/` 通过
  - [x] 11.3 运行 `isort --check src/analysis/` 通过
  - [x] 11.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md#Data Architecture]

**筛选器设计:**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from src.models import Market, MarketCategory
from src.config import Settings


@dataclass
class FilterStatistics:
    """筛选统计信息"""
    total_input: int
    passed_liquidity: int
    passed_deadline: int
    passed_category: int
    passed_exclusion: int
    final_count: int


@dataclass
class FilterResult:
    """筛选结果"""
    markets: list[Market]
    statistics: FilterStatistics


class MarketFilter:
    """市场筛选器，根据规则过滤市场列表。"""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._min_liquidity = self._settings.MIN_LIQUIDITY
        self._min_deadline_days = self._settings.MIN_DEADLINE_DAYS

    def filter_markets(self, markets: list[Market]) -> FilterResult:
        """筛选市场列表，返回符合条件的市场。"""
        ...
```

### 筛选规则详解 [Source: epics.md#Story 2.3]

**硬性排除规则 (Hard Exclusion):**
这些规则会立即排除市场，不考虑其他条件：

| 规则 | 阈值 | 说明 |
|------|------|------|
| 最低流动性 | < $5,000 | 流动性太低无法有效交易 |
| 最近截止 | < 3 天 | 没有足够时间进行分析和交易 |

**软性筛选规则 (Soft Filter):**
这些规则用于筛选出高质量市场：

| 规则 | 阈值 | 说明 |
|------|------|------|
| 流动性 | >= $10,000 | 确保有足够的流动性 |
| 截止日期 | >= 7 天 | 有足够时间进行分析 |
| 类别 | 目标类别 | 政治、商业、科技、经济、加密货币 |

**关键词排除规则:**

| 类型 | 关键词 | 说明 |
|------|--------|------|
| 价格相关 | "price", "USD" | 价格预测类市场 |
| 时间相关 | "tomorrow" | 太短期的市场 |
| 争议性 | 可配置 | 需要避免的敏感话题 |

### 现有 Market 模型 [Source: src/models/market.py]

```python
from src.models import Market, MarketCategory

class Market(BaseModel):
    id: str
    title: str
    description: str | None = None
    category: MarketCategory | None = None
    yes_price: float | None = None
    no_price: float | None = None
    liquidity: float | None = None
    deadline: datetime | None = None
    resolution_status: str | None = None
    resolution_outcome: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


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

### 配置扩展 [Source: src/config.py]

需要在 `Settings` 类中添加以下配置项：

```python
# 在 Settings 类中添加

# ========== Market Filter Configuration ==========
MIN_LIQUIDITY: float = Field(
    default=10000.0,
    description="Minimum liquidity for market selection (USD)"
)
MIN_DEADLINE_DAYS: int = Field(
    default=7,
    description="Minimum days until market deadline"
)
HARD_EXCLUDE_LIQUIDITY: float = Field(
    default=5000.0,
    description="Hard exclusion liquidity threshold (USD)"
)
HARD_EXCLUDE_DEADLINE_DAYS: int = Field(
    default=3,
    description="Hard exclusion deadline threshold (days)"
)
EXCLUDED_KEYWORDS: list[str] = Field(
    default=["price", "USD", "tomorrow"],
    description="Keywords to exclude from market titles"
)
CONTROVERSIAL_KEYWORDS: list[str] = Field(
    default=[],
    description="Controversial keywords to exclude"
)
TARGET_CATEGORIES: list[str] = Field(
    default=["politics", "business", "tech", "economics", "crypto"],
    description="Target market categories for analysis"
)
```

### 日志系统 [Source: src/utils/logger.py]

```python
from src.utils.logger import get_logger, OPERATION_EMOJIS

logger = get_logger(__name__)

# 使用数据 Emoji 记录筛选统计
logger.info(f"{OPERATION_EMOJIS['data']} Filtering {len(markets)} markets...")
logger.info(f"{OPERATION_EMOJIS['data']} ✅ Passed liquidity filter: {count}")
logger.info(f"{OPERATION_EMOJIS['data']} ⚠️ Excluded by deadline: {count}")
logger.info(f"{OPERATION_EMOJIS['data']} ✅ Final filtered markets: {count}")
```

### 类型注解规范 [Source: project-context.md#Python]

```python
# ✅ 正确 - Python 3.10+ 语法
from __future__ import annotations

class MarketFilter:
    def filter_markets(self, markets: list[Market]) -> FilterResult:
        ...

    def _filter_by_liquidity(
        self, markets: list[Market], min_liquidity: float
    ) -> tuple[list[Market], int]:
        ...

# ❌ 错误 - 不要使用旧语法
from typing import Optional, List, Tuple

def filter_markets(self, markets: List[Market]) -> Tuple[List[Market], int]:  # 错误
    ...
```

### 项目结构 [Source: architecture.md#Project Structure]

**新增文件:**
```
src/analysis/
├── __init__.py           # 新增: 导出 MarketFilter
└── market_filter.py      # 新增: 市场筛选器

tests/test_analysis/
├── __init__.py           # 新增
└── test_market_filter.py # 新增: MarketFilter 测试
```

### 实现模板

**MarketFilter:**

```python
# src/analysis/market_filter.py
"""Market filtering engine for selecting high-quality markets.

This module implements the market filter that selects markets
suitable for LLM analysis based on liquidity, deadline, category,
and exclusion rules.
"""

from __future__ import annotations

__all__ = ["MarketFilter", "FilterResult", "FilterStatistics"]

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from src.config import Settings
from src.models import Market, MarketCategory
from src.utils.logger import OPERATION_EMOJIS, get_logger

logger = get_logger(__name__)


@dataclass
class FilterStatistics:
    """Statistics about the filtering process.

    Attributes:
        total_input: Total markets input to filter
        passed_liquidity: Markets passing liquidity filter
        passed_deadline: Markets passing deadline filter
        passed_category: Markets passing category filter
        passed_exclusion: Markets passing exclusion rules
        final_count: Final count of filtered markets
    """
    total_input: int = 0
    passed_liquidity: int = 0
    passed_deadline: int = 0
    passed_category: int = 0
    passed_exclusion: int = 0
    final_count: int = 0


@dataclass
class FilterResult:
    """Result of market filtering.

    Attributes:
        markets: List of filtered markets
        statistics: Filtering statistics
    """
    markets: list[Market] = field(default_factory=list)
    statistics: FilterStatistics = field(default_factory=FilterStatistics)


class MarketFilter:
    """Market filter for selecting high-quality markets.

    Filters markets based on:
    - Liquidity (minimum threshold)
    - Deadline (minimum days remaining)
    - Category (target categories)
    - Exclusion rules (keywords, etc.)

    Example:
        >>> filter = MarketFilter(settings)
        >>> result = filter.filter_markets(markets)
        >>> print(f"Filtered {len(result.markets)} markets")
    """

    # Target categories for analysis
    TARGET_CATEGORIES: set[MarketCategory] = {
        MarketCategory.POLITICS,
        MarketCategory.BUSINESS,
        MarketCategory.TECH,
        MarketCategory.ECONOMICS,
        MarketCategory.CRYPTO,
    }

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the market filter.

        Args:
            settings: Application settings (optional, uses defaults if None)
        """
        self._settings = settings or Settings()
        self._min_liquidity = self._settings.MIN_LIQUIDITY
        self._min_deadline_days = self._settings.MIN_DEADLINE_DAYS

    def filter_markets(self, markets: list[Market]) -> FilterResult:
        """Filter markets based on configured rules.

        Args:
            markets: List of markets to filter

        Returns:
            FilterResult containing filtered markets and statistics
        """
        if not markets:
            logger.info(f"{OPERATION_EMOJIS['data']} No markets to filter")
            return FilterResult()

        stats = FilterStatistics(total_input=len(markets))
        logger.info(
            f"{OPERATION_EMOJIS['data']} Filtering {len(markets)} markets..."
        )

        # Step 1: Hard exclusion by liquidity
        current = self._hard_exclude_by_liquidity(markets)
        stats.passed_liquidity = len(current)

        # Step 2: Hard exclusion by deadline
        current = self._hard_exclude_by_deadline(current)
        stats.passed_deadline = len(current)

        # Step 3: Soft filter by liquidity
        current = self._filter_by_liquidity(current)
        stats.passed_liquidity = len(current)

        # Step 4: Soft filter by deadline
        current = self._filter_by_deadline(current)
        stats.passed_deadline = len(current)

        # Step 5: Filter by category
        current = self._filter_by_category(current)
        stats.passed_category = len(current)

        # Step 6: Apply exclusion rules
        current = self._apply_exclusion_rules(current)
        stats.passed_exclusion = len(current)

        stats.final_count = len(current)

        logger.info(
            f"{OPERATION_EMOJIS['data']} ✅ Filtered {stats.final_count} / "
            f"{stats.total_input} markets"
        )

        return FilterResult(markets=current, statistics=stats)

    def _hard_exclude_by_liquidity(self, markets: list[Market]) -> list[Market]:
        """Hard exclude markets below minimum liquidity threshold."""
        ...

    def _hard_exclude_by_deadline(self, markets: list[Market]) -> list[Market]:
        """Hard exclude markets with deadline too close."""
        ...

    def _filter_by_liquidity(self, markets: list[Market]) -> list[Market]:
        """Filter markets by minimum liquidity."""
        ...

    def _filter_by_deadline(self, markets: list[Market]) -> list[Market]:
        """Filter markets by minimum deadline days."""
        ...

    def _filter_by_category(self, markets: list[Market]) -> list[Market]:
        """Filter markets by target categories."""
        ...

    def _apply_exclusion_rules(self, markets: list[Market]) -> list[Market]:
        """Apply keyword and other exclusion rules."""
        ...
```

### 测试策略

```python
# tests/test_analysis/test_market_filter.py
"""Tests for MarketFilter."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.analysis.market_filter import MarketFilter, FilterResult, FilterStatistics
from src.models import Market, MarketCategory


class TestMarketFilter:
    """Tests for MarketFilter class."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings."""
        settings = MagicMock()
        settings.MIN_LIQUIDITY = 10000.0
        settings.MIN_DEADLINE_DAYS = 7
        settings.HARD_EXCLUDE_LIQUIDITY = 5000.0
        settings.HARD_EXCLUDE_DEADLINE_DAYS = 3
        settings.EXCLUDED_KEYWORDS = ["price", "USD", "tomorrow"]
        return settings

    @pytest.fixture
    def market_filter(self, mock_settings: MagicMock) -> MarketFilter:
        """Create a MarketFilter instance for testing."""
        return MarketFilter(settings=mock_settings)

    @pytest.fixture
    def sample_market(self) -> Market:
        """Create a sample Market for testing."""
        return Market(
            id="test-market-123",
            title="Will X happen?",
            category=MarketCategory.POLITICS,
            liquidity=50000.0,
            deadline=datetime.utcnow() + timedelta(days=14),
        )

    def test_filter_empty_list(self, market_filter: MarketFilter) -> None:
        """Test filtering an empty list."""
        result = market_filter.filter_markets([])
        assert result.markets == []
        assert result.statistics.total_input == 0

    def test_filter_by_liquidity_pass(
        self, market_filter: MarketFilter, sample_market: Market
    ) -> None:
        """Test liquidity filter passes high liquidity market."""
        sample_market.liquidity = 15000.0
        result = market_filter.filter_markets([sample_market])
        assert len(result.markets) == 1

    def test_filter_by_liquidity_fail(
        self, market_filter: MarketFilter, sample_market: Market
    ) -> None:
        """Test liquidity filter rejects low liquidity market."""
        sample_market.liquidity = 8000.0  # Below 10000
        result = market_filter.filter_markets([sample_market])
        assert len(result.markets) == 0

    # More tests...
```

### 前一个故事学习 [Source: 2-2-market-data-fetch-and-store.md]

**从 Story 2.2 学到的模式:**

1. **使用 `from __future__ import annotations`** - 支持 Python 3.10+ 类型语法
2. **类型注解使用 `str | None`** - 而非 `Optional[str]`
3. **类型注解使用 `list[Type]`** - 而非 `List[Type]`
4. **使用 dataclass 定义数据结构** - FilterStatistics, FilterResult
5. **使用 OPERATION_EMOJIS** - 标准化日志 Emoji
6. **依赖注入模式** - 构造函数接受 settings 参数
7. **返回结果对象** - 而非元组，便于扩展

**关键实现模式:**

```python
# 使用 dataclass 定义结果类型
@dataclass
class FilterResult:
    markets: list[Market] = field(default_factory=list)
    statistics: FilterStatistics = field(default_factory=FilterStatistics)

# 依赖注入
def __init__(self, settings: Settings | None = None) -> None:
    self._settings = settings or Settings()

# 日志记录
logger.info(f"{OPERATION_EMOJIS['data']} Filtering {len(markets)} markets...")
```

### 依赖关系

**本故事依赖:**
- Story 1.2: 配置管理系统 (Settings 类)
- Story 1.3: 日志系统 (get_logger, OPERATION_EMOJIS)
- Story 1.7: Pydantic 数据模型 (Market, MarketCategory)
- Story 2.2: 市场数据获取与存储 (提供 Market 数据)

**后续故事依赖本故事:**
- Story 3.3: LLM 分析引擎 (需要筛选后的市场)
- Story 5.3: 交易决策流程 (需要高质量市场)

### 实现注意事项

**关键点:**

1. **硬性排除优先**: 先应用硬性排除规则，再做软性筛选
2. **边界值处理**:
   - 流动性 = $10,000 应该通过
   - 截止日期 = 7 天应该通过
3. **空值处理**: 处理无 liquidity、无 deadline、无 category 的市场
4. **统计信息**: 每个阶段记录通过数量，便于调试
5. **日志详细**: 记录每个筛选阶段的详情

**性能考虑:**

1. **顺序筛选**: 按成本从低到高排序筛选规则
2. **短路评估**: 硬性排除后立即跳过后续检查
3. **内存优化**: 使用生成器处理大量市场

### References

- [Source: architecture.md#Data Architecture] - 筛选器设计模式
- [Source: architecture.md#API & Communication Patterns] - 错误处理
- [Source: architecture.md#Logging Patterns] - 日志格式和 Emoji
- [Source: src/config.py] - 配置系统
- [Source: src/models/market.py] - Market 模型
- [Source: src/utils/logger.py] - 日志系统
- [Source: epics.md#Story 2.3] - 原始 Story 定义
- [Source: 2-2-market-data-fetch-and-store.md] - 前一个故事学习

## Dev Agent Record

### Agent Model Used

GLM-5

### Debug Log References

无

### Completion Notes List

- 实现了完整的 `MarketFilter` 类，包含：
  - 硬性排除规则：流动性 < $5,000，截止日期 < 3 天
  - 软性筛选规则：流动性 >= $10,000，截止日期 >= 7 天
  - 类别筛选：POLITICS, BUSINESS, TECHNOLOGY, ECONOMICS, CRYPTO
  - 关键词排除：price, USD, tomorrow (大小写不敏感，单词边界匹配)
  - 描述争议性条款排除（从配置读取）
- 使用 `FilterStatistics` 和 `FilterResult` dataclass 封装结果
- 统计字段区分硬性排除和软性筛选
- 集成现有配置系统 `MarketFilterSettings`
- 支持从配置读取 `excluded_keywords` 和 `controversial_keywords`
- 使用 `OPERATION_EMOJIS` 记录筛选统计
- 编写 57 个测试用例，覆盖率 100%
- 代码通过 mypy, black, isort 检查

### Code Review Fixes Applied

**2026-02-16 - 对抗性代码审查修复:**

1. **HIGH-2**: 实现描述中的争议性条款排除
   - 新增 `_contains_keyword()` 方法使用正则单词边界匹配
   - 修改 `_apply_exclusion_rules()` 同时检查标题和描述
   - 从配置读取 `controversial_keywords` 列表

2. **MEDIUM-3**: 修复统计字段被覆盖问题
   - 重命名统计字段区分硬性排除和软性筛选
   - `passed_hard_liquidity`, `passed_hard_deadline` - 硬性排除后数量
   - `passed_soft_liquidity`, `passed_soft_deadline` - 软性筛选后数量

3. **MEDIUM-4**: 改进关键词匹配使用单词边界
   - 使用正则 `\b` 避免误匹配（如 "priceless" 匹配 "price"）
   - 新增测试验证精确单词匹配

4. **MEDIUM-6**: 集成配置项
   - `MarketFilterSettings` 新增 `excluded_keywords` 配置
   - `MarketFilterSettings` 新增 `controversial_keywords` 配置

### File List

**新增文件:**
- `src/analysis/market_filter.py` - 市场筛选器实现
- `tests/test_analysis/__init__.py` - 测试模块初始化
- `tests/test_analysis/test_market_filter.py` - MarketFilter 测试

**修改文件:**
- `src/analysis/__init__.py` - 导出 MarketFilter, FilterResult, FilterStatistics
- `src/config.py` - 新增 excluded_keywords 和 controversial_keywords 配置项
