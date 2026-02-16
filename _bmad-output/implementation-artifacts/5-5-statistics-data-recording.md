# Story 5.5: 统计数据记录

Status: review

## Story

As a **用户**,
I want **系统记录每日统计数据**,
So that **我能够追踪长期表现**.

## Acceptance Criteria

**Given** 交易和持仓记录已实现 (Story 5.1-5.4)
**When** 扩展数据库和实现统计功能
**Then** 在 `database.py` 添加 `statistics` 表:
```sql
CREATE TABLE statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,
    mode TEXT NOT NULL,
    starting_capital REAL,
    ending_capital REAL,
    total_pnl REAL,
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**And** 实现 `src/storage/repositories/statistics_repo.py`:
- `save(stats: Statistics) -> Statistics` - 保存每日统计
- `get_by_date(date: date, mode: TradeMode) -> Statistics | None` - 获取指定日期统计
- `get_by_date_range(start: date, end: date, mode: TradeMode) -> list[Statistics]` - 获取时间范围统计
- `get_latest(mode: TradeMode, limit: int = 30) -> list[Statistics]` - 获取最近统计

**And** 实现每日统计任务:
- `DailyStatisticsRecorder` 类包含:
  - `record_daily_stats(mode: TradeMode) -> Statistics` - 记录当日统计
  - 计算当日交易数、胜率、PnL
  - 记录到 statistics 表
  - 使用 ThreadSafeState 获取资金数据

## Tasks / Subtasks

- [x] Task 1: 扩展数据库 Schema (AC: 1)
  - [x] 1.1 在 `src/storage/database.py` 添加 statistics 表创建 SQL
  - [x] 1.2 添加 date+mode 复合索引
  - [x] 1.3 添加 created_at 索引
  - [x] 1.4 运行数据库迁移测试

- [x] Task 2: 创建 StatisticsRepository (AC: 2)
  - [x] 2.1 创建 `src/storage/repositories/statistics_repo.py`
  - [x] 2.2 实现 `save(stats: Statistics) -> Statistics` 方法
  - [x] 2.3 实现 `get_by_date(date, mode) -> Statistics | None` 方法
  - [x] 2.4 实现 `get_by_date_range(start, end, mode) -> list[Statistics]` 方法
  - [x] 2.5 实现 `get_latest(mode, limit) -> list[Statistics]` 方法
  - [x] 2.6 添加数据库索引创建 SQL
  - [x] 2.7 更新 `src/storage/repositories/__init__.py` 导出

- [x] Task 3: 实现 DailyStatisticsRecorder (AC: 3)
  - [x] 3.1 创建 `src/trading/statistics_recorder.py`
  - [x] 3.2 实现 `DailyStatisticsRecorder` 类
  - [x] 3.3 实现 `record_daily_stats(mode: TradeMode) -> Statistics` 方法
  - [x] 3.4 从 TradeRepository 获取当日交易数据
  - [x] 3.5 从 ThreadSafeState 获取资金数据
  - [x] 3.6 计算胜率: `winning_trades / total_trades`
  - [x] 3.7 计算 PnL: 从当日交易汇总
  - [x] 3.8 保存统计记录到数据库
  - [x] 3.9 更新 `src/trading/__init__.py` 导出

- [x] Task 4: 编写单元测试 (AC: All)
  - [x] 4.1 创建 `tests/test_storage/test_statistics_repo.py`
  - [x] 4.2 测试 save 方法 (新建和更新)
  - [x] 4.3 测试 get_by_date 方法
  - [x] 4.4 测试 get_by_date_range 方法
  - [x] 4.5 测试 get_latest 方法
  - [x] 4.6 创建 `tests/test_trading/test_statistics_recorder.py`
  - [x] 4.7 测试 record_daily_stats 方法
  - [x] 4.8 测试胜率计算
  - [x] 4.9 测试 PnL 计算
  - [x] 4.10 测试边界情况 (无交易日)
  - [x] 4.11 Mock 所有外部依赖

- [x] Task 5: 代码质量检查 (AC: All)
  - [x] 5.1 运行 `mypy src/storage/repositories/statistics_repo.py` 无错误
  - [x] 5.2 运行 `mypy src/trading/statistics_recorder.py` 无错误
  - [x] 5.3 运行 `black --check` 通过
  - [x] 5.4 运行 `isort --check` 通过
  - [x] 5.5 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md]

**Statistics 表设计原则:**
- date + mode 构成唯一约束 (每天每个模式一条记录)
- starting_capital 和 ending_capital 追踪资金变化
- win_rate 为 0-1 范围的小数
- 支持按时间范围查询用于 Dashboard 展示

### 已有组件 (必须复用)

**Statistics Model** [Source: src/models/statistics.py]
```python
class Statistics(BaseModel):
    id: int
    date: datetime.date
    mode: TradeMode
    starting_capital: float
    ending_capital: float | None
    total_pnl: float | None
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float | None
    created_at: datetime.datetime | None

class DailyStats(BaseModel):
    # 带计算字段的统计视图
    daily_return_pct: float | None  # (ending - starting) / starting * 100
    win_rate_pct: float | None      # win_rate * 100
```

**TradeRepository** [Source: src/storage/repositories/trade_repo.py]
```python
class TradeRepository:
    async def get_by_mode(mode: TradeMode) -> list[Trade]: ...
    async def get_recent(limit: int) -> list[Trade]: ...
```

**ThreadSafeState** [Source: src/core/state.py]
```python
class ThreadSafeState:
    async def get_state() -> StateSnapshot: ...
    # StateSnapshot.current_capital - 当前资金
    # StateSnapshot.daily_pnl - 当日盈亏
```

**Trade Model** [Source: src/models/trade.py]
```python
class Trade(BaseModel):
    id: int
    market_id: str
    trade_type: TradeType  # BUY_YES, BUY_NO, SELL
    mode: TradeMode        # PAPER, LIVE
    amount: float
    price: float
    shares: float | None
    status: TradeStatus    # PENDING, FILLED, CANCELLED
    created_at: datetime | None
```

**TradeMode Enum** [Source: src/models/trade.py]
```python
class TradeMode(str, Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"
```

### 统计计算逻辑

```
┌─────────────────────────────────────────────────────────────────────┐
│                   每日统计计算流程                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  record_daily_stats(mode: TradeMode) -> Statistics                  │
│                                                                     │
│  1. 获取日期                                                         │
│     today = date.today()                                            │
│                                                                     │
│  2. 获取当日交易 (需要扩展 TradeRepository)                           │
│     trades = await get_trades_by_date(today, mode)                  │
│                                                                     │
│  3. 计算交易统计                                                     │
│     total_trades = len([t for t in trades if t.status == FILLED])   │
│     winning_trades = count_winning_trades(trades)  # 从持仓 PnL      │
│     losing_trades = total_trades - winning_trades                   │
│                                                                     │
│  4. 计算胜率                                                         │
│     if total_trades > 0:                                            │
│         win_rate = winning_trades / total_trades                    │
│     else:                                                           │
│         win_rate = None                                             │
│                                                                     │
│  5. 获取资金数据                                                     │
│     state = await state_manager.get_state()                         │
│     ending_capital = state.current_capital                          │
│     total_pnl = state.daily_pnl                                     │
│                                                                     │
│  6. 获取起始资金 (从昨日统计或初始配置)                                │
│     yesterday_stats = await repo.get_by_date(yesterday, mode)       │
│     if yesterday_stats:                                             │
│         starting_capital = yesterday_stats.ending_capital           │
│     else:                                                           │
│         starting_capital = settings.initial_capital                 │
│                                                                     │
│  7. 创建并保存统计记录                                               │
│     stats = Statistics(                                             │
│         id=0,                                                       │
│         date=today,                                                 │
│         mode=mode,                                                  │
│         starting_capital=starting_capital,                          │
│         ending_capital=ending_capital,                              │
│         total_pnl=total_pnl,                                        │
│         total_trades=total_trades,                                  │
│         winning_trades=winning_trades,                              │
│         losing_trades=losing_trades,                                │
│         win_rate=win_rate,                                          │
│     )                                                               │
│     return await repo.save(stats)                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 注意: TradeRepository 需要扩展

当前 TradeRepository 没有按日期查询交易的方法。需要添加:

```python
async def get_by_date_range(
    self,
    start_date: date,
    end_date: date,
    mode: TradeMode | None = None
) -> list[Trade]:
    """Get trades within a date range.

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        mode: Optional trading mode filter

    Returns:
        List of trades within the date range
    """
```

### 实现模板

**src/storage/repositories/statistics_repo.py:**

```python
"""Statistics repository for database operations.

Story 5.5: 统计数据记录
"""

from __future__ import annotations

__all__ = ["StatisticsRepository"]

from datetime import date, datetime

import aiosqlite

from src.exceptions import DatabaseError
from src.models.statistics import Statistics
from src.models.trade import TradeMode
from src.storage.database import get_connection
from src.utils.logger import OPERATION_EMOJIS, get_logger

logger = get_logger(__name__)


class StatisticsRepository:
    """Repository for Statistics CRUD operations.

    Provides async methods for managing daily statistics in the database.

    Example:
        >>> repo = StatisticsRepository()
        >>> stats = await repo.save(Statistics(...))
        >>> daily = await repo.get_by_date(date.today(), TradeMode.PAPER)
    """

    def __init__(self) -> None:
        """Initialize the StatisticsRepository."""
        pass

    async def save(self, stats: Statistics) -> Statistics:
        """Save a statistics record to the database.

        Uses INSERT OR REPLACE to handle upsert based on date+mode unique
        constraint.

        Args:
            stats: Statistics to save (id will be assigned if 0)

        Returns:
            Saved statistics with assigned id
        """
        # Implementation...

    async def get_by_date(
        self, target_date: date, mode: TradeMode
    ) -> Statistics | None:
        """Get statistics for a specific date and mode.

        Args:
            target_date: Date to query
            mode: Trading mode

        Returns:
            Statistics if found, None otherwise
        """
        # Implementation...

    async def get_by_date_range(
        self, start: date, end: date, mode: TradeMode
    ) -> list[Statistics]:
        """Get statistics for a date range.

        Args:
            start: Start date (inclusive)
            end: End date (inclusive)
            mode: Trading mode

        Returns:
            List of statistics, ordered by date ascending
        """
        # Implementation...

    async def get_latest(
        self, mode: TradeMode, limit: int = 30
    ) -> list[Statistics]:
        """Get most recent statistics.

        Args:
            mode: Trading mode
            limit: Maximum number of records (default: 30)

        Returns:
            List of recent statistics, ordered by date descending
        """
        # Implementation...
```

**src/trading/statistics_recorder.py:**

```python
"""Daily statistics recorder.

Story 5.5: 统计数据记录
"""

from __future__ import annotations

__all__ = ["DailyStatisticsRecorder"]

from datetime import date, timedelta

from src.core.state import StateSnapshot, ThreadSafeState
from src.models.statistics import Statistics
from src.models.trade import TradeMode
from src.storage.repositories.statistics_repo import StatisticsRepository
from src.storage.repositories.trade_repo import TradeRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DailyStatisticsRecorder:
    """Recorder for daily trading statistics.

    Collects trading data and generates daily statistics records.

    Example:
        >>> recorder = DailyStatisticsRecorder(trade_repo, stats_repo, state)
        >>> stats = await recorder.record_daily_stats(TradeMode.PAPER)
        >>> print(f"Today's PnL: ${stats.total_pnl:.2f}")
    """

    def __init__(
        self,
        trade_repo: TradeRepository,
        stats_repo: StatisticsRepository,
        state_manager: ThreadSafeState,
    ) -> None:
        """Initialize the recorder.

        Args:
            trade_repo: Trade repository for querying trades
            stats_repo: Statistics repository for saving stats
            state_manager: State manager for capital data
        """
        self._trade_repo = trade_repo
        self._stats_repo = stats_repo
        self._state_manager = state_manager
        self._logger = logger

    async def record_daily_stats(self, mode: TradeMode) -> Statistics:
        """Record statistics for today.

        Args:
            mode: Trading mode (PAPER or LIVE)

        Returns:
            Statistics record for today
        """
        # Implementation...
```

### 项目结构 [Source: architecture.md#Project Structure]

**新增文件:**
```
src/
├── storage/
│   └── repositories/
│       └── statistics_repo.py     # 新增
└── trading/
    └── statistics_recorder.py     # 新增

tests/
├── test_storage/
│   └── test_statistics_repo.py    # 新增
└── test_trading/
    └── test_statistics_recorder.py # 新增
```

**修改文件:**
```
src/
├── storage/
│   ├── database.py                # 修改: 添加 statistics 表
│   └── repositories/
│       ├── __init__.py            # 修改: 导出 StatisticsRepository
│       └── trade_repo.py          # 修改: 添加 get_by_date_range 方法
└── trading/
    └── __init__.py                # 修改: 导出 DailyStatisticsRecorder
```

### 依赖关系

**本故事依赖:**
- Story 4.2: 线程安全状态管理 (已完成 - `ThreadSafeState`)
- Story 5.1: 交易记录数据模型 (已完成 - `Trade`, `TradeRepository`)
- Story 5.4: 模拟持仓 PnL 计算 (已完成 - PnL 计算)

**后续故事依赖本故事:**
- Story 7.4: 预测与统计 API (需要统计数据展示)
- Story 8.2: 定时任务配置 (需要每日统计任务)

### 前一个故事学习 [Source: 5-4-simulated-position-pnl-calculation.md]

**从 Story 5.4 学到的模式:**

1. **数据类返回结果** - 使用 `@dataclass` 或 Pydantic 模型定义返回类型
2. **依赖注入** - 所有依赖通过构造函数注入
3. **错误隔离** - 捕获特定异常，记录日志，继续处理
4. **日志标准化** - 使用 emoji 标记不同类型的日志 (📊 统计)
5. **类型注解** - 使用 `TYPE_CHECKING` 避免循环导入
6. **`__all__` 导出** - 明确模块公共 API
7. **批量操作** - 支持单个和范围查询

### 实现注意事项

**关键点:**

1. **日期处理** - 使用 `datetime.date` 而非 `datetime.datetime`
2. **UPSERT 逻辑** - 使用 `INSERT OR REPLACE` 处理重复日期
3. **起始资金来源** - 优先从昨日统计获取，否则使用配置
4. **胜率计算** - 只有完成 (FILLED) 的交易计入统计
5. **空交易日** - total_trades=0 时 win_rate=None

**错误处理:**

| 场景 | 处理方式 |
|------|----------|
| 无昨日统计 | 使用 settings.initial_capital |
| 无当日交易 | total_trades=0, win_rate=None |
| 保存失败 | 抛出 DatabaseError |
| 查询失败 | 记录错误日志，抛出 DatabaseError |

**日志级别:**

| 级别 | 场景 | Emoji |
|------|------|-------|
| INFO | 统计记录保存、查询完成 | 📊 |
| DEBUG | 详细统计计算 | 📊 |
| WARNING | 无数据情况 | ⚠️ |
| ERROR | 操作失败 | ❌ |

### 测试策略

```python
# tests/test_storage/test_statistics_repo.py
"""Tests for StatisticsRepository."""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.models.statistics import Statistics
from src.models.trade import TradeMode
from src.storage.repositories.statistics_repo import StatisticsRepository


class TestStatisticsRepository:
    """测试 StatisticsRepository CRUD 操作."""

    @pytest.fixture
    def repo(self) -> StatisticsRepository:
        return StatisticsRepository()

    @pytest.mark.asyncio
    async def test_save_new_stats(self, repo: StatisticsRepository) -> None:
        """测试保存新统计记录."""
        stats = Statistics(
            id=0,
            date=date.today(),
            mode=TradeMode.PAPER,
            starting_capital=200.0,
            ending_capital=210.0,
            total_pnl=10.0,
            total_trades=5,
            winning_trades=3,
            losing_trades=2,
            win_rate=0.6,
        )
        saved = await repo.save(stats)
        assert saved.id > 0

    @pytest.mark.asyncio
    async def test_get_by_date(self, repo: StatisticsRepository) -> None:
        """测试按日期查询."""
        result = await repo.get_by_date(date.today(), TradeMode.PAPER)
        assert result is not None
        assert result.date == date.today()


# tests/test_trading/test_statistics_recorder.py
"""Tests for DailyStatisticsRecorder."""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from src.core.state import StateSnapshot
from src.models.statistics import Statistics
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.trading.statistics_recorder import DailyStatisticsRecorder


class TestDailyStatisticsRecorder:
    """测试每日统计记录器."""

    @pytest.fixture
    def recorder(self) -> DailyStatisticsRecorder:
        trade_repo = AsyncMock()
        stats_repo = AsyncMock()
        state_manager = AsyncMock()
        return DailyStatisticsRecorder(trade_repo, stats_repo, state_manager)

    @pytest.mark.asyncio
    async def test_record_daily_stats(
        self, recorder: DailyStatisticsRecorder
    ) -> None:
        """测试记录每日统计."""
        # Setup mocks
        recorder._trade_repo.get_by_date_range.return_value = []
        recorder._stats_repo.get_by_date.return_value = None
        recorder._state_manager.get_state.return_value = StateSnapshot(
            current_capital=210.0,
            daily_pnl=10.0,
        )

        result = await recorder.record_daily_stats(TradeMode.PAPER)

        assert result.total_trades == 0
        assert result.ending_capital == 210.0
        assert result.total_pnl == 10.0
```

### References

- [Source: architecture.md#Database Schema] - statistics 表定义
- [Source: architecture.md#Project Structure] - src/storage/repositories/ 目录结构
- [Source: epics.md#Story 5.5] - 原始 Story 定义
- [Source: src/models/statistics.py] - Statistics 模型定义
- [Source: src/models/trade.py] - Trade 模型定义
- [Source: src/core/state.py] - ThreadSafeState 状态管理
- [Source: src/storage/repositories/trade_repo.py] - TradeRepository 参考
- [Source: 5-4-simulated-position-pnl-calculation.md] - 前一个故事实现参考
- [Source: 5-1-trade-record-data-model.md] - TradeRepository 基础实现

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- 2026-02-16: 修复日志格式化问题 - win_rate 可能为 None，需要单独格式化
- 2026-02-16: 使用 Python 3.11 运行测试 (Python 3.9 不支持 `|` 联合类型语法)

### Completion Notes List

- 2026-02-16: 完成 Story 5.5 实现
  - 在 database.py 添加了 statistics 表和索引
  - 创建了 StatisticsRepository 类，实现 save, get_by_date, get_by_date_range, get_latest 方法
  - 创建了 DailyStatisticsRecorder 类，实现 record_daily_stats 方法
  - 扩展了 TradeRepository 添加 get_by_date_range 方法
  - 编写了 15 个单元测试，全部通过
  - 运行了 mypy, black, isort 代码质量检查，全部通过
  - 完整测试套件 (939 tests) 全部通过

### File List

**新增文件:**
- src/storage/repositories/statistics_repo.py
- src/trading/statistics_recorder.py
- tests/test_storage/test_repositories/test_statistics_repo.py
- tests/test_trading/test_statistics_recorder.py

**修改文件:**
- src/storage/database.py - 添加 statistics 表和索引
- src/storage/repositories/__init__.py - 导出 StatisticsRepository
- src/storage/repositories/trade_repo.py - 添加 get_by_date_range 方法
- src/trading/__init__.py - 导出 DailyStatisticsRecorder
- _bmad-output/implementation-artifacts/sprint-status.yaml - 更新状态为 in-progress
