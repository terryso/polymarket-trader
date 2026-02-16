# Story 4.5: 持仓管理

Status: dev-complete

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **用户**,
I want **系统能够追踪和管理当前持仓**,
So that **我能够了解资金分配和风险敞口**.

## Acceptance Criteria

**Given** 风险控制器已实现
**When** 扩展数据库和创建持仓仓库
**Then** 在 `database.py` 添加 `positions` 表:
```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    outcome TEXT NOT NULL,  -- YES/NO
    shares REAL NOT NULL,
    avg_price REAL NOT NULL,
    initial_value REAL,
    current_value REAL,
    pnl REAL,
    status TEXT,  -- OPEN/CLOSED
    opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    closed_at DATETIME,
    FOREIGN KEY (market_id) REFERENCES markets(id)
);
```

**And** 实现 `src/trading/position_manager.py`:
- `open_position(market_id, outcome, shares, price)` - 开仓
- `update_position_value(position_id, current_value)` - 更新市值
- `close_position(position_id, final_value)` - 平仓
- `get_open_positions()` - 获取所有未平仓位
- `get_total_exposure()` - 获取总风险敞口

**And** 实现 `src/storage/repositories/position_repo.py`

## Tasks / Subtasks

- [ ] Task 1: 扩展数据库 Schema (AC: 1)
  - [ ] 1.1 在 `src/storage/database.py` 的 `init_db()` 方法中添加 `positions` 表创建语句
  - [ ] 1.2 为 `positions` 表创建索引 (market_id, status)
  - [ ] 1.3 添加数据库迁移逻辑检查 positions 表是否存在
  - [ ] 1.4 验证外键约束正确设置

- [ ] Task 2: 创建 PositionRepository (AC: 3)
  - [ ] 2.1 创建 `src/storage/repositories/position_repo.py` 文件
  - [ ] 2.2 实现 `PositionRepository` 类
  - [ ] 2.3 实现 `save(position: Position) -> Position` 方法 - 保存持仓
  - [ ] 2.4 实现 `get_by_id(position_id: int) -> Position | None` 方法
  - [ ] 2.5 实现 `get_by_market(market_id: str) -> Position | None` 方法
  - [ ] 2.6 实现 `get_open_positions() -> list[Position]` 方法
  - [ ] 2.7 实现 `update(position: Position) -> Position` 方法
  - [ ] 2.8 实现 `delete(position_id: int) -> bool` 方法
  - [ ] 2.9 添加完整的类型注解和 docstring

- [ ] Task 3: 创建 PositionManager (AC: 2)
  - [ ] 3.1 创建 `src/trading/position_manager.py` 文件
  - [ ] 3.2 实现 `PositionManager` 类，接受 `PositionRepository` 和 `ThreadSafeState`
  - [ ] 3.3 实现 `open_position(market_id, outcome, shares, price) -> Position` 方法
    - 计算初始价值 `initial_value = shares * price`
    - 设置 `status = OPEN`
    - 设置 `opened_at = now()`
    - 保存到数据库
    - 更新 ThreadSafeState 的 open_positions_count
  - [ ] 3.4 实现 `update_position_value(position_id, current_value) -> Position` 方法
    - 从数据库获取持仓
    - 更新 `current_value` 和 `pnl`
    - 保存并返回
  - [ ] 3.5 实现 `close_position(position_id, final_value) -> Position` 方法
    - 更新 `status = CLOSED`
    - 设置 `closed_at = now()`
    - 计算最终 PnL
    - 更新 ThreadSafeState 的 open_positions_count
  - [ ] 3.6 实现 `get_open_positions() -> list[Position]` 方法
  - [ ] 3.7 实现 `get_total_exposure() -> float` 方法 - 所有未平仓位的 current_value 总和
  - [ ] 3.8 实现 `get_position_by_market(market_id) -> Position | None` 方法

- [ ] Task 4: 更新模块导出 (AC: All)
  - [ ] 4.1 更新 `src/storage/repositories/__init__.py` 导出 `PositionRepository`
  - [ ] 4.2 更新 `src/trading/__init__.py` 导出 `PositionManager`
  - [ ] 4.3 更新 `__all__` 列表

- [ ] Task 5: 编写单元测试 (AC: All)
  - [ ] 5.1 创建 `tests/test_storage/test_repositories/test_position_repo.py`
  - [ ] 5.2 创建 `tests/test_trading/test_position_manager.py`
  - [ ] 5.3 测试 PositionRepository CRUD 操作
  - [ ] 5.4 测试 PositionManager 开仓操作
  - [ ] 5.5 测试 PositionManager 更新持仓价值
  - [ ] 5.6 测试 PositionManager 平仓操作
  - [ ] 5.7 测试获取开放持仓列表
  - [ ] 5.8 测试计算总风险敞口
  - [ ] 5.9 测试与 ThreadSafeState 的集成

- [ ] Task 6: 代码质量检查 (AC: All)
  - [ ] 6.1 运行 `mypy src/trading/position_manager.py src/storage/repositories/position_repo.py` 无错误
  - [ ] 6.2 运行 `black --check` 通过
  - [ ] 6.3 运行 `isort --check` 通过
  - [ ] 6.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md#Database Schema]

**positions 表结构:**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY | 自增主键 |
| `market_id` | TEXT NOT NULL | 市场ID (外键) |
| `outcome` | TEXT NOT NULL | 持仓方向 (YES/NO) |
| `shares` | REAL NOT NULL | 持有份额 |
| `avg_price` | REAL NOT NULL | 平均买入价格 (0-1) |
| `initial_value` | REAL | 初始价值 (USD) |
| `current_value` | REAL | 当前市值 (USD) |
| `pnl` | REAL | 盈亏 (USD) |
| `status` | TEXT | 状态 (OPEN/CLOSED) |
| `opened_at` | DATETIME | 开仓时间 |
| `closed_at` | DATETIME | 平仓时间 |

### 已有模型 [Source: src/models/position.py]

项目已实现 `Position` 模型:

```python
class PositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class PositionOutcome(str, Enum):
    YES = "YES"
    NO = "NO"

class Position(BaseModel):
    id: int
    market_id: str
    outcome: PositionOutcome
    shares: float  # >= 0
    avg_price: float  # 0-1
    initial_value: float | None
    current_value: float | None
    pnl: float | None
    status: PositionStatus
    opened_at: datetime | None
    closed_at: datetime | None
```

### 持仓管理流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     持仓管理流程                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  open_position(market_id, outcome, shares, price)              │
│                                                                 │
│  1. 验证参数                                                    │
│     - shares > 0                                                │
│     - 0 < price < 1                                             │
│     - outcome in [YES, NO]                                      │
│                                                                 │
│  2. 创建 Position 对象                                          │
│     initial_value = shares * price                              │
│     status = OPEN                                               │
│     opened_at = now()                                           │
│                                                                 │
│  3. 保存到数据库                                                │
│     position = await repo.save(position)                        │
│                                                                 │
│  4. 更新状态管理器                                              │
│     await state.increment_open_positions()                      │
│                                                                 │
│  5. 记录日志                                                    │
│     logger.info(f"💰 Position opened: {market_id}")             │
│                                                                 │
│  6. 返回 Position                                               │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  update_position_value(position_id, current_price)             │
│                                                                 │
│  1. 获取持仓                                                    │
│     position = await repo.get_by_id(position_id)                │
│                                                                 │
│  2. 计算当前价值                                                │
│     current_value = position.shares * current_price             │
│                                                                 │
│  3. 计算 PnL                                                    │
│     pnl = current_value - position.initial_value                │
│                                                                 │
│  4. 更新并保存                                                  │
│     position.current_value = current_value                      │
│     position.pnl = pnl                                          │
│     await repo.update(position)                                 │
│                                                                 │
│  5. 返回更新后的 Position                                       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  close_position(position_id, final_price)                       │
│                                                                 │
│  1. 获取持仓                                                    │
│     position = await repo.get_by_id(position_id)                │
│                                                                 │
│  2. 验证状态                                                    │
│     if position.status != OPEN: raise TradingError              │
│                                                                 │
│  3. 计算最终价值                                                │
│     final_value = position.shares * final_price                 │
│     pnl = final_value - position.initial_value                  │
│                                                                 │
│  4. 更新持仓                                                    │
│     position.status = CLOSED                                    │
│     position.current_value = final_value                        │
│     position.pnl = pnl                                          │
│     position.closed_at = now()                                  │
│                                                                 │
│  5. 保存到数据库                                                │
│     await repo.update(position)                                 │
│                                                                 │
│  6. 更新状态管理器                                              │
│     await state.decrement_open_positions()                      │
│     await state.update_capital(pnl)  # 记录盈亏                 │
│                                                                 │
│  7. 记录交易结果                                                │
│     await state.record_trade_result(pnl > 0)                    │
│                                                                 │
│  8. 返回更新后的 Position                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 实现模板

**src/storage/repositories/position_repo.py:**

```python
"""Position repository for database operations.

This module provides the PositionRepository class for managing
position data in the SQLite database.

Story 4.5: 持仓管理
"""

from __future__ import annotations

__all__ = ["PositionRepository"]

import json
from datetime import datetime
from typing import TYPE_CHECKING

from src.models.position import Position, PositionOutcome, PositionStatus
from src.storage.database import get_connection
from src.utils.logger import get_logger

if TYPE_CHECKING:
    import aiosqlite
    from collections.abc import AsyncIterator

logger = get_logger(__name__)


class PositionRepository:
    """Repository for Position CRUD operations.

    Provides async methods for managing positions in the database.

    Example:
        >>> repo = PositionRepository()
        >>> position = await repo.save(Position(...))
        >>> open_positions = await repo.get_open_positions()
    """

    async def save(self, position: Position) -> Position:
        """Save a new position to the database.

        Args:
            position: Position to save (id will be assigned)

        Returns:
            Saved position with assigned id
        """
        async with get_connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO positions (
                    market_id, outcome, shares, avg_price,
                    initial_value, current_value, pnl, status,
                    opened_at, closed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position.market_id,
                    position.outcome.value,
                    position.shares,
                    position.avg_price,
                    position.initial_value,
                    position.current_value,
                    position.pnl,
                    position.status.value,
                    position.opened_at.isoformat() if position.opened_at else None,
                    position.closed_at.isoformat() if position.closed_at else None,
                ),
            )
            await conn.commit()
            position_id = cursor.lastrowid

        logger.debug(f"💰 Saved position {position_id} for market {position.market_id}")
        return Position(id=position_id, **position.model_dump(exclude={"id"}))

    async def get_by_id(self, position_id: int) -> Position | None:
        """Get position by ID.

        Args:
            position_id: Position identifier

        Returns:
            Position if found, None otherwise
        """
        async with get_connection() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM positions WHERE id = ?", (position_id,)
            )
            row = await cursor.fetchone()

        if row is None:
            return None
        return self._row_to_position(row)

    async def get_by_market(
        self, market_id: str, status: PositionStatus | None = None
    ) -> Position | None:
        """Get position by market ID.

        Args:
            market_id: Market identifier
            status: Optional status filter

        Returns:
            Position if found, None otherwise
        """
        async with get_connection() as conn:
            conn.row_factory = aiosqlite.Row
            if status:
                cursor = await conn.execute(
                    "SELECT * FROM positions WHERE market_id = ? AND status = ?",
                    (market_id, status.value),
                )
            else:
                cursor = await conn.execute(
                    "SELECT * FROM positions WHERE market_id = ?", (market_id,)
                )
            row = await cursor.fetchone()

        if row is None:
            return None
        return self._row_to_position(row)

    async def get_open_positions(self) -> list[Position]:
        """Get all open positions.

        Returns:
            List of open positions
        """
        async with get_connection() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM positions WHERE status = ? ORDER BY opened_at DESC",
                (PositionStatus.OPEN.value,),
            )
            rows = await cursor.fetchall()

        return [self._row_to_position(row) for row in rows]

    async def update(self, position: Position) -> Position:
        """Update an existing position.

        Args:
            position: Position to update

        Returns:
            Updated position
        """
        async with get_connection() as conn:
            await conn.execute(
                """
                UPDATE positions SET
                    market_id = ?, outcome = ?, shares = ?, avg_price = ?,
                    initial_value = ?, current_value = ?, pnl = ?, status = ?,
                    opened_at = ?, closed_at = ?
                WHERE id = ?
                """,
                (
                    position.market_id,
                    position.outcome.value,
                    position.shares,
                    position.avg_price,
                    position.initial_value,
                    position.current_value,
                    position.pnl,
                    position.status.value,
                    position.opened_at.isoformat() if position.opened_at else None,
                    position.closed_at.isoformat() if position.closed_at else None,
                    position.id,
                ),
            )
            await conn.commit()

        logger.debug(f"📊 Updated position {position.id}")
        return position

    async def delete(self, position_id: int) -> bool:
        """Delete a position.

        Args:
            position_id: Position identifier

        Returns:
            True if deleted, False if not found
        """
        async with get_connection() as conn:
            cursor = await conn.execute(
                "DELETE FROM positions WHERE id = ?", (position_id,)
            )
            await conn.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.debug(f"Deleted position {position_id}")
        return deleted

    def _row_to_position(self, row: aiosqlite.Row) -> Position:
        """Convert database row to Position model.

        Args:
            row: Database row

        Returns:
            Position model instance
        """
        return Position(
            id=row["id"],
            market_id=row["market_id"],
            outcome=PositionOutcome(row["outcome"]),
            shares=row["shares"],
            avg_price=row["avg_price"],
            initial_value=row["initial_value"],
            current_value=row["current_value"],
            pnl=row["pnl"],
            status=PositionStatus(row["status"]),
            opened_at=datetime.fromisoformat(row["opened_at"])
            if row["opened_at"]
            else None,
            closed_at=datetime.fromisoformat(row["closed_at"])
            if row["closed_at"]
            else None,
        )
```

**src/trading/position_manager.py:**

```python
"""Position management for the Polymarket Trader application.

This module provides the PositionManager class that handles all
position lifecycle operations including opening, updating, and closing.

Story 4.5: 持仓管理

Example:
    >>> from src.trading.position_manager import PositionManager
    >>> from src.storage.repositories.position_repo import PositionRepository
    >>> from src.core.state import ThreadSafeState
    >>>
    >>> repo = PositionRepository()
    >>> state = ThreadSafeState(initial_capital=200.0)
    >>> manager = PositionManager(repo, state)
    >>>
    >>> # Open a position
    >>> position = await manager.open_position(
    ...     market_id="btc-100k",
    ...     outcome=PositionOutcome.YES,
    ...     shares=100.0,
    ...     price=0.45
    ... )
"""

from __future__ import annotations

__all__ = ["PositionManager"]

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.exceptions import TradingError, ValidationError
from src.models.position import Position, PositionOutcome, PositionStatus
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.core.state import ThreadSafeState
    from src.storage.repositories.position_repo import PositionRepository


logger = get_logger(__name__)


class PositionManager:
    """Position lifecycle manager.

    Manages the complete lifecycle of trading positions:
    - Opening new positions
    - Updating position values
    - Closing positions
    - Tracking total exposure

    Attributes:
        _repo: PositionRepository for database operations
        _state: ThreadSafeState for system state tracking

    Example:
        >>> manager = PositionManager(repo, state)
        >>> position = await manager.open_position(
        ...     "market-123", PositionOutcome.YES, 100.0, 0.45
        ... )
        >>> print(f"Opened position {position.id}")
    """

    def __init__(
        self,
        repository: "PositionRepository",
        state: "ThreadSafeState",
    ) -> None:
        """Initialize position manager.

        Args:
            repository: PositionRepository for database operations
            state: ThreadSafeState for system state tracking
        """
        self._repo = repository
        self._state = state
        self._logger = get_logger(__name__)
        self._logger.info("PositionManager initialized")

    async def open_position(
        self,
        market_id: str,
        outcome: PositionOutcome,
        shares: float,
        price: float,
    ) -> Position:
        """Open a new position.

        Args:
            market_id: Market identifier
            outcome: Position outcome (YES or NO)
            shares: Number of shares to purchase
            price: Purchase price per share (0-1)

        Returns:
            Created Position with assigned id

        Raises:
            ValidationError: If parameters are invalid
            TradingError: If position creation fails

        Example:
            >>> position = await manager.open_position(
            ...     "btc-100k", PositionOutcome.YES, 100.0, 0.45
            ... )
        """
        # Validate parameters
        if shares <= 0:
            raise ValidationError(f"Shares must be positive, got {shares}")
        if not 0 < price < 1:
            raise ValidationError(f"Price must be between 0 and 1, got {price}")

        # Check for existing open position in this market
        existing = await self._repo.get_by_market(market_id, PositionStatus.OPEN)
        if existing:
            raise TradingError(
                f"Open position already exists for market {market_id}: "
                f"position_id={existing.id}"
            )

        # Calculate initial value
        initial_value = shares * price

        # Create position object
        now = datetime.now(timezone.utc)
        position = Position(
            id=0,  # Will be assigned by database
            market_id=market_id,
            outcome=outcome,
            shares=shares,
            avg_price=price,
            initial_value=initial_value,
            current_value=initial_value,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=now,
            closed_at=None,
        )

        # Save to database
        saved_position = await self._repo.save(position)

        # Update system state
        await self._state.increment_open_positions()

        self._logger.info(
            f"💰 Position opened: id={saved_position.id}, "
            f"market={market_id}, outcome={outcome.value}, "
            f"shares={shares:.2f}, price={price:.4f}, "
            f"value=${initial_value:.2f}"
        )

        return saved_position

    async def update_position_value(
        self,
        position_id: int,
        current_price: float,
    ) -> Position:
        """Update position's current value and PnL.

        Args:
            position_id: Position identifier
            current_price: Current market price (0-1)

        Returns:
            Updated Position

        Raises:
            ValidationError: If position not found or price invalid
            TradingError: If position is not OPEN

        Example:
            >>> position = await manager.update_position_value(1, 0.55)
            >>> print(f"PnL: ${position.pnl:.2f}")
        """
        if not 0 < current_price < 1:
            raise ValidationError(
                f"Current price must be between 0 and 1, got {current_price}"
            )

        # Get position
        position = await self._repo.get_by_id(position_id)
        if position is None:
            raise ValidationError(f"Position {position_id} not found")

        if position.status != PositionStatus.OPEN:
            raise TradingError(
                f"Cannot update closed position {position_id}"
            )

        # Calculate new values
        current_value = position.shares * current_price
        pnl = current_value - (position.initial_value or 0)

        # Update position
        position.current_value = current_value
        position.pnl = pnl

        updated_position = await self._repo.update(position)

        self._logger.debug(
            f"📊 Position {position_id} updated: "
            f"current_value=${current_value:.2f}, pnl=${pnl:.2f}"
        )

        return updated_position

    async def close_position(
        self,
        position_id: int,
        final_price: float,
    ) -> Position:
        """Close an open position.

        Args:
            position_id: Position identifier
            final_price: Final market price at close (0-1)

        Returns:
            Closed Position with final PnL

        Raises:
            ValidationError: If position not found or price invalid
            TradingError: If position is not OPEN

        Example:
            >>> position = await manager.close_position(1, 0.60)
            >>> print(f"Final PnL: ${position.pnl:.2f}")
        """
        if not 0 < final_price < 1:
            raise ValidationError(
                f"Final price must be between 0 and 1, got {final_price}"
            )

        # Get position
        position = await self._repo.get_by_id(position_id)
        if position is None:
            raise ValidationError(f"Position {position_id} not found")

        if position.status != PositionStatus.OPEN:
            raise TradingError(
                f"Position {position_id} is already closed"
            )

        # Calculate final values
        final_value = position.shares * final_price
        pnl = final_value - (position.initial_value or 0)

        # Update position
        now = datetime.now(timezone.utc)
        position.status = PositionStatus.CLOSED
        position.current_value = final_value
        position.pnl = pnl
        position.closed_at = now

        updated_position = await self._repo.update(position)

        # Update system state
        await self._state.decrement_open_positions()
        await self._state.update_capital(pnl)
        await self._state.record_trade_result(pnl > 0)

        result_emoji = "✅" if pnl >= 0 else "❌"
        self._logger.info(
            f"{result_emoji} Position closed: id={position_id}, "
            f"market={position.market_id}, "
            f"final_value=${final_value:.2f}, pnl=${pnl:.2f}"
        )

        return updated_position

    async def get_open_positions(self) -> list[Position]:
        """Get all open positions.

        Returns:
            List of all open positions

        Example:
            >>> positions = await manager.get_open_positions()
            >>> print(f"Open positions: {len(positions)}")
        """
        positions = await self._repo.get_open_positions()
        self._logger.debug(f"Retrieved {len(positions)} open positions")
        return positions

    async def get_total_exposure(self) -> float:
        """Calculate total exposure across all open positions.

        Returns:
            Total current value of all open positions in USD

        Example:
            >>> exposure = await manager.get_total_exposure()
            >>> print(f"Total exposure: ${exposure:.2f}")
        """
        positions = await self.get_open_positions()
        total = sum(p.current_value or 0 for p in positions)
        self._logger.debug(f"Total exposure: ${total:.2f}")
        return total

    async def get_position_by_market(self, market_id: str) -> Position | None:
        """Get open position for a specific market.

        Args:
            market_id: Market identifier

        Returns:
            Open position if exists, None otherwise

        Example:
            >>> position = await manager.get_position_by_market("btc-100k")
            >>> if position:
            ...     print(f"Position value: ${position.current_value}")
        """
        position = await self._repo.get_by_market(market_id, PositionStatus.OPEN)
        return position
```

### 项目结构 [Source: architecture.md#Project Structure]

**新建文件:**
```
src/
├── storage/
│   └── repositories/
│       ├── __init__.py          # 修改: 导出 PositionRepository
│       └── position_repo.py     # 新建: PositionRepository 实现
├── trading/
│   ├── __init__.py              # 修改: 导出 PositionManager
│   └── position_manager.py      # 新建: PositionManager 实现

tests/
├── test_storage/
│   └── test_repositories/
│       ├── __init__.py          # 新建或已有
│       └── test_position_repo.py # 新建: PositionRepository 测试
└── test_trading/
    └── test_position_manager.py # 新建: PositionManager 测试
```

### ThreadSafeState 集成 [Source: src/core/state.py]

需要确保 ThreadSafeState 有以下方法:

```python
async def increment_open_positions(self) -> None:
    """Increment open positions count."""
    ...

async def decrement_open_positions(self) -> None:
    """Decrement open positions count."""
    ...

async def record_trade_result(self, is_win: bool) -> None:
    """Record trade result for circuit breaker."""
    ...
```

如果这些方法不存在，需要在 Story 4.5 中添加。

### 测试策略

```python
# tests/test_trading/test_position_manager.py
"""Tests for PositionManager."""

from datetime import datetime

import pytest

from src.core.state import ThreadSafeState
from src.models.position import Position, PositionOutcome, PositionStatus
from src.storage.repositories.position_repo import PositionRepository
from src.trading.position_manager import PositionManager


class TestPositionManager:
    """测试 PositionManager."""

    @pytest.fixture
    async def state(self) -> ThreadSafeState:
        """创建测试用状态管理器."""
        return ThreadSafeState(initial_capital=200.0)

    @pytest.fixture
    async def repo(self) -> PositionRepository:
        """创建测试用持仓仓库."""
        return PositionRepository()

    @pytest.fixture
    async def manager(
        self, repo: PositionRepository, state: ThreadSafeState
    ) -> PositionManager:
        """创建测试用持仓管理器."""
        return PositionManager(repo, state)

    @pytest.mark.asyncio
    async def test_open_position(
        self, manager: PositionManager
    ) -> None:
        """测试开仓."""
        position = await manager.open_position(
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            price=0.45,
        )

        assert position.id > 0
        assert position.market_id == "test-market-1"
        assert position.outcome == PositionOutcome.YES
        assert position.shares == 100.0
        assert position.avg_price == 0.45
        assert position.initial_value == 45.0
        assert position.status == PositionStatus.OPEN
        assert position.opened_at is not None

    @pytest.mark.asyncio
    async def test_update_position_value(
        self, manager: PositionManager
    ) -> None:
        """测试更新持仓价值."""
        # Open position first
        position = await manager.open_position(
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            price=0.45,
        )

        # Update value
        updated = await manager.update_position_value(position.id, 0.55)

        assert updated.current_value == 55.0  # 100 * 0.55
        assert updated.pnl == 10.0  # 55 - 45

    @pytest.mark.asyncio
    async def test_close_position(
        self, manager: PositionManager, state: ThreadSafeState
    ) -> None:
        """测试平仓."""
        # Open position first
        position = await manager.open_position(
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            price=0.45,
        )

        initial_capital = (await state.get_state()).current_capital

        # Close position
        closed = await manager.close_position(position.id, 0.60)

        assert closed.status == PositionStatus.CLOSED
        assert closed.current_value == 60.0
        assert closed.pnl == 15.0  # 60 - 45
        assert closed.closed_at is not None

        # Check state updated
        snapshot = await state.get_state()
        assert snapshot.open_positions_count == 0

    @pytest.mark.asyncio
    async def test_get_total_exposure(
        self, manager: PositionManager
    ) -> None:
        """测试计算总风险敞口."""
        # Open multiple positions
        await manager.open_position("m1", PositionOutcome.YES, 100.0, 0.50)
        await manager.open_position("m2", PositionOutcome.NO, 50.0, 0.40)

        # Update one position
        await manager.update_position_value(1, 0.55)

        exposure = await manager.get_total_exposure()
        # 100 * 0.55 + 50 * 0.40 = 55 + 20 = 75
        assert exposure == 75.0
```

### 依赖关系

**本故事依赖:**
- Story 1.2: 配置管理系统 (已完成 - `settings`)
- Story 1.6: 数据库初始化 (已完成 - `init_db`)
- Story 1.7: Pydantic 数据模型 (已完成 - `Position` 模型)
- Story 4.2: 线程安全状态管理 (已完成 - `ThreadSafeState`)

**后续故事依赖本故事:**
- Story 5.2: Paper Trading 执行器 (需要 PositionManager 管理持仓)
- Story 5.3: 交易决策流程 (需要 PositionManager 查询持仓)
- Story 5.4: 模拟持仓 PnL 计算 (需要 PositionManager 更新价值)

### 前一个故事学习 [Source: 4-4-pre-trade-risk-check.md]

**从 Story 4.4 学到的模式:**

1. **使用 dataclass 定义结果类** - 简单数据结构使用 `@dataclass`
2. **完整 docstring** - 包含 Args, Returns, Raises, Example
3. **`__all__` 导出列表** - 明确模块公共 API
4. **类型注解使用 `|` 联合** - 而非 `Optional`
5. **日志使用 emoji** - `✅`, `⚠️`, `❌`, `📊`, `💰`
6. **异步方法** - 所有涉及数据库的方法都是 `async`
7. **验证参数** - 在操作前验证参数有效性
8. **抛出特定异常** - 使用 `ValidationError`, `TradingError`

### 实现注意事项

**关键点:**

1. **外键约束** - positions 表引用 markets 表
2. **唯一性约束** - 每个市场只能有一个 OPEN 状态的持仓
3. **状态同步** - 开仓/平仓时更新 ThreadSafeState
4. **PnL 计算** - `pnl = current_value - initial_value`
5. **时区处理** - 使用 UTC 时间存储

**错误处理:**

| 场景 | 抛出异常 |
|------|----------|
| shares <= 0 | ValidationError |
| price 不在 0-1 范围 | ValidationError |
| 持仓不存在 | ValidationError |
| 重复开仓 | TradingError |
| 平仓已关闭的持仓 | TradingError |

**日志级别:**

| 级别 | 场景 |
|------|------|
| INFO | 开仓、平仓 |
| DEBUG | 更新价值、获取列表 |
| WARNING | 异常情况 |
| ERROR | 数据库操作失败 |

### References

- [Source: architecture.md#Database Schema] - positions 表定义
- [Source: architecture.md#Project Structure] - src/trading/ 目录结构
- [Source: src/models/position.py] - Position 模型定义
- [Source: src/core/state.py] - ThreadSafeState 接口
- [Source: src/exceptions.py] - 异常类定义
- [Source: epics.md#Story 4.5] - 原始 Story 定义
- [Source: 4-4-pre-trade-risk-check.md] - 前一个故事参考

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
