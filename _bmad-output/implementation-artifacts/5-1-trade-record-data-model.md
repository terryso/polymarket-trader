# Story 5.1: 交易记录数据模型

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **开发者**,
I want **定义交易记录的数据模型和数据库表**,
So that **交易数据可以持久化存储**.

## Acceptance Criteria

**Given** Epic 1-4 已完成
**When** 扩展数据库和交易模型
**Then** 在 `database.py` 添加 `trades` 表:
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    trade_type TEXT NOT NULL,  -- BUY_YES/BUY_NO/SELL
    mode TEXT NOT NULL,        -- PAPER/LIVE
    amount REAL NOT NULL,
    price REAL NOT NULL,
    shares REAL,
    status TEXT,               -- PENDING/FILLED/CANCELLED
    llm_prediction_id INTEGER,
    position_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (market_id) REFERENCES markets(id),
    FOREIGN KEY (llm_prediction_id) REFERENCES predictions(id),
    FOREIGN KEY (position_id) REFERENCES positions(id)
);
```

**And** 在 `src/models/trade.py` 扩展 `Trade` 模型 (已有，需验证字段匹配)

**And** 实现 `src/storage/repositories/trade_repo.py`:
- `save_trade(trade: Trade) -> Trade` - 保存交易
- `get_trades_by_market(market_id)` - 获取市场交易
- `get_trades_by_mode(mode)` - 按模式获取交易
- `get_recent_trades(limit)` - 获取最近交易
- `get_trade_by_id(trade_id)` - 根据 ID 获取交易

## Tasks / Subtasks

- [x] Task 1: 扩展数据库 Schema (AC: 1)
  - [x] 1.1 在 `src/storage/database.py` 的 `init_db()` 方法中添加 `trades` 表创建语句
  - [x] 1.2 为 `trades` 表创建索引 (market_id, mode, created_at)
  - [x] 1.3 添加外键约束检查逻辑
  - [x] 1.4 验证与现有 markets, predictions, positions 表的外键关系

- [x] Task 2: 验证 Trade 模型 (AC: 2)
  - [x] 2.1 检查 `src/models/trade.py` 中 Trade 模型是否包含所有必需字段
  - [x] 2.2 验证 TradeType 枚举包含 BUY_YES, BUY_NO, SELL
  - [x] 2.3 验证 TradeMode 枚举包含 PAPER, LIVE
  - [x] 2.4 验证 TradeStatus 枚举包含 PENDING, FILLED, CANCELLED
  - [x] 2.5 确保所有字段有正确的 Pydantic 验证 (price: 0-1, amount: >= 0)

- [x] Task 3: 创建 TradeRepository (AC: 3)
  - [x] 3.1 创建 `src/storage/repositories/trade_repo.py` 文件
  - [x] 3.2 实现 `TradeRepository` 类
  - [x] 3.3 实现 `save(trade: Trade) -> Trade` 方法 - 保存交易
  - [x] 3.4 实现 `get_by_id(trade_id: int) -> Trade | None` 方法
  - [x] 3.5 实现 `get_by_market(market_id: str) -> list[Trade]` 方法
  - [x] 3.6 实现 `get_by_mode(mode: TradeMode) -> list[Trade]` 方法
  - [x] 3.7 实现 `get_recent(limit: int = 50) -> list[Trade]` 方法
  - [x] 3.8 实现 `_row_to_trade(row: aiosqlite.Row) -> Trade` 辅助方法
  - [x] 3.9 添加完整的类型注解和 docstring

- [x] Task 4: 更新模块导出 (AC: All)
  - [x] 4.1 更新 `src/storage/repositories/__init__.py` 导出 `TradeRepository`
  - [x] 4.2 更新 `__all__` 列表

- [x] Task 5: 编写单元测试 (AC: All)
  - [x] 5.1 创建 `tests/test_storage/test_repositories/test_trade_repo.py`
  - [x] 5.2 测试 TradeRepository CRUD 操作
  - [x] 5.3 测试按市场 ID 查询交易
  - [x] 5.4 测试按交易模式筛选
  - [x] 5.5 测试获取最近交易
  - [x] 5.6 测试外键约束 (关联 prediction, position)

- [x] Task 6: 代码质量检查 (AC: All)
  - [x] 6.1 运行 `mypy src/storage/repositories/trade_repo.py` 无错误
  - [x] 6.2 运行 `black --check` 通过
  - [x] 6.3 运行 `isort --check` 通过
  - [x] 6.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md#Database Schema]

**trades 表结构:**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY | 自增主键 |
| `market_id` | TEXT NOT NULL | 市场ID (外键 -> markets) |
| `trade_type` | TEXT NOT NULL | 交易类型 (BUY_YES/BUY_NO/SELL) |
| `mode` | TEXT NOT NULL | 交易模式 (PAPER/LIVE) |
| `amount` | REAL NOT NULL | 交易金额 (USD) |
| `price` | REAL NOT NULL | 价格 (0-1) |
| `shares` | REAL | 交易份额 |
| `status` | TEXT | 状态 (PENDING/FILLED/CANCELLED) |
| `llm_prediction_id` | INTEGER | LLM 预测 ID (外键 -> predictions) |
| `position_id` | INTEGER | 持仓 ID (外键 -> positions) |
| `created_at` | DATETIME | 创建时间 |

### 已有模型 [Source: src/models/trade.py]

项目已实现 `Trade` 模型:

```python
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

class Trade(BaseModel):
    id: int
    market_id: str
    trade_type: TradeType
    mode: TradeMode
    amount: float  # >= 0
    price: float   # 0-1
    shares: float | None
    status: TradeStatus
    llm_prediction_id: int | None
    position_id: int | None
    created_at: datetime | None
```

### 交易数据流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     交易记录数据流程                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  save(trade: Trade) -> Trade                                   │
│                                                                 │
│  1. 验证 Trade 模型                                             │
│     - Pydantic 自动验证所有字段                                 │
│                                                                 │
│  2. 插入数据库                                                  │
│     INSERT INTO trades (...) VALUES (...)                      │
│                                                                 │
│  3. 获取生成的 ID                                               │
│     trade_id = cursor.lastrowid                                │
│                                                                 │
│  4. 记录日志                                                    │
│     logger.info(f"💰 Trade saved: id={trade_id}")              │
│                                                                 │
│  5. 返回带 ID 的 Trade                                          │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  get_by_market(market_id: str) -> list[Trade]                  │
│                                                                 │
│  1. 查询数据库                                                  │
│     SELECT * FROM trades WHERE market_id = ?                   │
│     ORDER BY created_at DESC                                   │
│                                                                 │
│  2. 转换为 Trade 模型列表                                       │
│                                                                 │
│  3. 返回结果                                                    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  get_by_mode(mode: TradeMode) -> list[Trade]                   │
│                                                                 │
│  1. 查询数据库                                                  │
│     SELECT * FROM trades WHERE mode = ?                        │
│     ORDER BY created_at DESC                                   │
│                                                                 │
│  2. 转换为 Trade 模型列表                                       │
│                                                                 │
│  3. 返回结果                                                    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  get_recent(limit: int = 50) -> list[Trade]                    │
│                                                                 │
│  1. 查询数据库                                                  │
│     SELECT * FROM trades ORDER BY created_at DESC LIMIT ?      │
│                                                                 │
│  2. 转换为 Trade 模型列表                                       │
│                                                                 │
│  3. 返回结果                                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 实现模板

**src/storage/repositories/trade_repo.py:**

```python
"""Trade repository for database operations.

This module provides the TradeRepository class for managing
trade records in the SQLite database.

Story 5.1: 交易记录数据模型

Example:
    >>> from src.storage.repositories import TradeRepository
    >>> from src.models.trade import Trade, TradeType, TradeMode, TradeStatus
    >>>
    >>> repo = TradeRepository()
    >>> trade = await repo.save(Trade(
    ...     id=0,
    ...     market_id="btc-100k",
    ...     trade_type=TradeType.BUY_YES,
    ...     mode=TradeMode.PAPER,
    ...     amount=100.0,
    ...     price=0.45,
    ...     status=TradeStatus.FILLED,
    ... ))
"""

from __future__ import annotations

__all__ = ["TradeRepository"]

from datetime import datetime
from typing import TYPE_CHECKING

import aiosqlite

from src.exceptions import DatabaseError
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.storage.database import get_connection
from src.utils.logger import OPERATION_EMOJIS, get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = get_logger(__name__)


class TradeRepository:
    """Repository for Trade CRUD operations.

    Provides async methods for managing trade records in the database.

    Example:
        >>> repo = TradeRepository()
        >>> trade = await repo.save(Trade(...))
        >>> trades = await repo.get_by_market("market-123")
    """

    def __init__(self) -> None:
        """Initialize the TradeRepository."""
        pass

    async def save(self, trade: Trade) -> Trade:
        """Save a trade record to the database.

        Args:
            trade: Trade to save (id will be assigned if 0)

        Returns:
            Saved trade with assigned id

        Raises:
            DatabaseError: If database operation fails

        Example:
            >>> trade = Trade(
            ...     id=0,
            ...     market_id="btc-100k",
            ...     trade_type=TradeType.BUY_YES,
            ...     mode=TradeMode.PAPER,
            ...     amount=100.0,
            ...     price=0.45,
            ...     status=TradeStatus.FILLED,
            ... )
            >>> saved = await repo.save(trade)
        """
        logger.info(
            f"{OPERATION_EMOJIS['trade']} Saving trade: "
            f"market={trade.market_id}, type={trade.trade_type.value}, "
            f"mode={trade.mode.value}"
        )

        try:
            async with get_connection() as conn:
                cursor = await conn.execute(
                    """
                    INSERT INTO trades (
                        market_id, trade_type, mode, amount, price, shares,
                        status, llm_prediction_id, position_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trade.market_id,
                        trade.trade_type.value,
                        trade.mode.value,
                        trade.amount,
                        trade.price,
                        trade.shares,
                        trade.status.value,
                        trade.llm_prediction_id,
                        trade.position_id,
                        trade.created_at.isoformat() if trade.created_at else None,
                    ),
                )
                await conn.commit()
                trade_id = cursor.lastrowid or 0

            logger.info(
                f"{OPERATION_EMOJIS['trade']} Trade saved with ID: {trade_id}"
            )

            return Trade(id=trade_id, **trade.model_dump(exclude={"id"}))
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['trade']} Failed to save trade: {e}"
            )
            raise DatabaseError(
                message=f"Failed to save trade for market: {trade.market_id}",
                operation="save_trade",
                original_exception=e,
            ) from e

    async def get_by_id(self, trade_id: int) -> Trade | None:
        """Get a trade by its ID.

        Args:
            trade_id: Trade identifier

        Returns:
            Trade if found, None otherwise

        Example:
            >>> trade = await repo.get_by_id(1)
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    "SELECT * FROM trades WHERE id = ?",
                    (trade_id,),
                )
                row = await cursor.fetchone()

            if row is None:
                return None
            return self._row_to_trade(row)
        except aiosqlite.Error as e:
            logger.error(f"Failed to get trade {trade_id}: {e}")
            raise

    async def get_by_market(self, market_id: str) -> list[Trade]:
        """Get all trades for a specific market.

        Args:
            market_id: Market identifier

        Returns:
            List of trades, ordered by created_at descending

        Example:
            >>> trades = await repo.get_by_market("btc-100k")
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    """
                    SELECT * FROM trades
                    WHERE market_id = ?
                    ORDER BY created_at DESC
                    """,
                    (market_id,),
                )
                rows = await cursor.fetchall()

            trades = [self._row_to_trade(row) for row in rows]
            logger.info(
                f"{OPERATION_EMOJIS['data']} Found {len(trades)} trades "
                f"for market: {market_id}"
            )
            return trades
        except aiosqlite.Error as e:
            logger.error(
                f"Failed to get trades for market {market_id}: {e}"
            )
            raise

    async def get_by_mode(self, mode: TradeMode) -> list[Trade]:
        """Get all trades for a specific trading mode.

        Args:
            mode: Trading mode (PAPER or LIVE)

        Returns:
            List of trades, ordered by created_at descending

        Example:
            >>> paper_trades = await repo.get_by_mode(TradeMode.PAPER)
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    """
                    SELECT * FROM trades
                    WHERE mode = ?
                    ORDER BY created_at DESC
                    """,
                    (mode.value,),
                )
                rows = await cursor.fetchall()

            trades = [self._row_to_trade(row) for row in rows]
            logger.info(
                f"{OPERATION_EMOJIS['data']} Found {len(trades)} trades "
                f"for mode: {mode.value}"
            )
            return trades
        except aiosqlite.Error as e:
            logger.error(f"Failed to get trades for mode {mode}: {e}")
            raise

    async def get_recent(self, limit: int = 50) -> list[Trade]:
        """Get most recent trades.

        Args:
            limit: Maximum number of trades to return (default: 50)

        Returns:
            List of recent trades, ordered by created_at descending

        Example:
            >>> recent_trades = await repo.get_recent(10)
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    """
                    SELECT * FROM trades
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = await cursor.fetchall()

            trades = [self._row_to_trade(row) for row in rows]
            logger.info(
                f"{OPERATION_EMOJIS['data']} Retrieved {len(trades)} recent trades"
            )
            return trades
        except aiosqlite.Error as e:
            logger.error(f"Failed to get recent trades: {e}")
            raise

    def _row_to_trade(self, row: aiosqlite.Row) -> Trade:
        """Convert a database row to a Trade model.

        Args:
            row: Database row from trades table

        Returns:
            Trade model instance
        """
        # Parse created_at
        created_at: datetime | None = None
        if row["created_at"]:
            try:
                created_at = datetime.fromisoformat(row["created_at"])
            except ValueError:
                created_at = None

        return Trade(
            id=row["id"],
            market_id=row["market_id"],
            trade_type=TradeType(row["trade_type"]),
            mode=TradeMode(row["mode"]),
            amount=row["amount"],
            price=row["price"],
            shares=row["shares"],
            status=TradeStatus(row["status"]),
            llm_prediction_id=row["llm_prediction_id"],
            position_id=row["position_id"],
            created_at=created_at,
        )
```

### 项目结构 [Source: architecture.md#Project Structure]

**新建/修改文件:**
```
src/
├── models/
│   └── trade.py                   # 已有: 验证字段匹配
├── storage/
│   ├── database.py                # 修改: 添加 trades 表
│   └── repositories/
│       ├── __init__.py            # 修改: 导出 TradeRepository
│       └── trade_repo.py          # 新建: TradeRepository 实现

tests/
└── test_storage/
    └── test_repositories/
        ├── __init__.py            # 新建或已有
        └── test_trade_repo.py     # 新建: TradeRepository 测试
```

### 参考: PositionRepository 实现 [Source: src/storage/repositories/position_repo.py]

参考现有的 PositionRepository 实现模式:
- 使用 `async with get_connection() as conn` 获取连接
- 使用 `conn.row_factory = aiosqlite.Row` 设置行工厂
- 使用 `OPERATION_EMOJIS` 日志 emoji
- 抛出 `DatabaseError` 处理数据库错误
- 实现 `_row_to_model` 辅助方法转换数据库行

### 参考: PredictionRepository 实现 [Source: src/storage/repositories/prediction_repo.py]

参考现有的 PredictionRepository 实现模式:
- `save_prediction` 方法使用 UPSERT 逻辑 (先删除再插入)
- 使用 `json.dumps`/`json.loads` 处理 JSON 字段
- 完整的 docstring 包含 Example
- `__all__` 导出列表

### 测试策略

```python
# tests/test_storage/test_repositories/test_trade_repo.py
"""Tests for TradeRepository."""

import pytest

from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.storage.repositories.trade_repo import TradeRepository


class TestTradeRepository:
    """测试 TradeRepository."""

    @pytest.fixture
    async def repo(self) -> TradeRepository:
        """创建测试用交易仓库."""
        return TradeRepository()

    @pytest.fixture
    async def sample_trade(self) -> Trade:
        """创建示例交易."""
        return Trade(
            id=0,
            market_id="test-market-1",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=100.0,
            price=0.45,
            shares=222.22,
            status=TradeStatus.FILLED,
            llm_prediction_id=None,
            position_id=None,
        )

    @pytest.mark.asyncio
    async def test_save_trade(
        self, repo: TradeRepository, sample_trade: Trade
    ) -> None:
        """测试保存交易."""
        saved = await repo.save(sample_trade)

        assert saved.id > 0
        assert saved.market_id == sample_trade.market_id
        assert saved.trade_type == sample_trade.trade_type
        assert saved.mode == sample_trade.mode
        assert saved.amount == sample_trade.amount
        assert saved.price == sample_trade.price
        assert saved.shares == sample_trade.shares
        assert saved.status == sample_trade.status

    @pytest.mark.asyncio
    async def test_get_by_id(
        self, repo: TradeRepository, sample_trade: Trade
    ) -> None:
        """测试根据 ID 获取交易."""
        saved = await repo.save(sample_trade)

        found = await repo.get_by_id(saved.id)

        assert found is not None
        assert found.id == saved.id
        assert found.market_id == saved.market_id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo: TradeRepository) -> None:
        """测试获取不存在的交易."""
        found = await repo.get_by_id(99999)

        assert found is None

    @pytest.mark.asyncio
    async def test_get_by_market(
        self, repo: TradeRepository
    ) -> None:
        """测试按市场查询交易."""
        # 创建两个不同市场的交易
        trade1 = Trade(
            id=0, market_id="market-a", trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER, amount=50.0, price=0.5,
            status=TradeStatus.FILLED,
        )
        trade2 = Trade(
            id=0, market_id="market-b", trade_type=TradeType.BUY_NO,
            mode=TradeMode.PAPER, amount=30.0, price=0.3,
            status=TradeStatus.FILLED,
        )
        trade3 = Trade(
            id=0, market_id="market-a", trade_type=TradeType.SELL,
            mode=TradeMode.PAPER, amount=20.0, price=0.6,
            status=TradeStatus.FILLED,
        )

        await repo.save(trade1)
        await repo.save(trade2)
        await repo.save(trade3)

        # 查询 market-a 的交易
        market_a_trades = await repo.get_by_market("market-a")

        assert len(market_a_trades) == 2
        assert all(t.market_id == "market-a" for t in market_a_trades)

    @pytest.mark.asyncio
    async def test_get_by_mode(
        self, repo: TradeRepository
    ) -> None:
        """测试按模式筛选交易."""
        # 创建不同模式的交易
        paper_trade = Trade(
            id=0, market_id="market-1", trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER, amount=50.0, price=0.5,
            status=TradeStatus.FILLED,
        )
        live_trade = Trade(
            id=0, market_id="market-2", trade_type=TradeType.BUY_YES,
            mode=TradeMode.LIVE, amount=100.0, price=0.6,
            status=TradeStatus.FILLED,
        )

        await repo.save(paper_trade)
        await repo.save(live_trade)

        # 查询 PAPER 模式交易
        paper_trades = await repo.get_by_mode(TradeMode.PAPER)

        assert len(paper_trades) >= 1
        assert all(t.mode == TradeMode.PAPER for t in paper_trades)

    @pytest.mark.asyncio
    async def test_get_recent(
        self, repo: TradeRepository
    ) -> None:
        """测试获取最近交易."""
        # 创建多个交易
        for i in range(5):
            trade = Trade(
                id=0, market_id=f"market-{i}", trade_type=TradeType.BUY_YES,
                mode=TradeMode.PAPER, amount=float(i * 10), price=0.5,
                status=TradeStatus.FILLED,
            )
            await repo.save(trade)

        # 获取最近 3 条
        recent = await repo.get_recent(3)

        assert len(recent) == 3
        # 应按 created_at 降序排列
```

### 依赖关系

**本故事依赖:**
- Story 1.2: 配置管理系统 (已完成 - `settings`)
- Story 1.6: 数据库初始化 (已完成 - `init_db`)
- Story 1.7: Pydantic 数据模型 (已完成 - `Trade` 模型)
- Story 3.4: 预测结果存储 (已完成 - `predictions` 表)
- Story 4.5: 持仓管理 (已完成 - `positions` 表)

**后续故事依赖本故事:**
- Story 5.2: Paper Trading 执行器 (需要 TradeRepository 保存交易)
- Story 5.3: 交易决策流程 (需要 TradeRepository 记录交易)
- Story 5.5: 统计数据记录 (需要 TradeRepository 查询交易)

### 前一个故事学习 [Source: 4-5-position-management.md]

**从 Story 4.5 学到的模式:**

1. **Repository 模式** - 所有数据库操作封装在 Repository 类中
2. **`__all__` 导出列表** - 明确模块公共 API
3. **类型注解使用 `|` 联合** - 而非 `Optional`
4. **日志使用 emoji** - `✅`, `⚠️`, `❌`, `📊`, `💰`
5. **异步方法** - 所有涉及数据库的方法都是 `async`
6. **`_row_to_model` 辅助方法** - 统一处理数据库行转换
7. **`save` 返回带 ID 的模型** - 返回新创建的完整对象
8. **抛出 `DatabaseError`** - 包装 aiosqlite.Error

### 实现注意事项

**关键点:**

1. **外键约束** - trades 表引用 markets, predictions, positions 表
2. **字段匹配** - 确保 Trade 模型字段与数据库表一致
3. **枚举序列化** - 使用 `.value` 将枚举转换为字符串存储
4. **时区处理** - 使用 UTC 时间存储
5. **索引设计** - 为常用查询字段创建索引

**错误处理:**

| 场景 | 抛出异常 |
|------|----------|
| 数据库连接失败 | DatabaseError |
| 插入失败 (外键约束) | DatabaseError |
| 查询失败 | DatabaseError (或重新抛出) |

**日志级别:**

| 级别 | 场景 |
|------|------|
| INFO | 保存交易、查询结果数量 |
| DEBUG | 详细调试信息 |
| ERROR | 数据库操作失败 |

### References

- [Source: architecture.md#Database Schema] - trades 表定义
- [Source: architecture.md#Project Structure] - src/storage/repositories/ 目录结构
- [Source: src/models/trade.py] - Trade 模型定义
- [Source: src/storage/database.py] - 数据库连接和初始化
- [Source: src/storage/repositories/position_repo.py] - Repository 实现参考
- [Source: src/storage/repositories/prediction_repo.py] - Repository 实现参考
- [Source: src/exceptions.py] - DatabaseError 异常类
- [Source: epics.md#Story 5.1] - 原始 Story 定义

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

N/A - 所有测试通过，无需调试

### Completion Notes List

- 2026-02-16: Story 5.1 实现完成
  - 在 `database.py` 添加了 `trades` 表，包含所有必需字段和索引
  - 验证了 `Trade` 模型已存在且字段完全匹配 AC 要求
  - 实现了 `TradeRepository` 类，包含所有 CRUD 方法
  - 更新了 `__init__.py` 导出 `TradeRepository`
  - 创建了完整的单元测试套件 (24 个测试全部通过)
  - 通过所有代码质量检查 (mypy, black, isort)
  - 运行完整测试套件 (852 个测试全部通过)

### File List

**新建文件:**
- `src/storage/repositories/trade_repo.py` - TradeRepository 实现
- `tests/test_storage/test_repositories/test_trade_repo.py` - TradeRepository 测试

**修改文件:**
- `src/storage/database.py` - 添加 trades 表和索引
- `src/storage/repositories/__init__.py` - 导出 TradeRepository
