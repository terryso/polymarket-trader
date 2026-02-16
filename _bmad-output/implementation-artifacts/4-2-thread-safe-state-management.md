# Story 4.2: 线程安全状态管理

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **开发者**,
I want **实现线程安全的状态管理器**,
So that **系统状态在并发环境下安全更新**.

## Acceptance Criteria

**Given** 基础设施已完成
**When** 实现 `src/core/state.py`
**Then** 创建 `ThreadSafeState` 类管理以下状态:
- `current_capital`: 当前资金
- `daily_pnl`: 当日盈亏
- `consecutive_losses`: 连续亏损次数
- `open_positions_count`: 当前持仓数量
- `trading_enabled`: 是否允许交易
- `reduced_mode`: 是否处于降级模式

**And** 使用 `asyncio.Lock` 保证线程安全
**And** 实现方法:
- `get_state()` - 获取当前状态快照
- `update_capital(amount)` - 更新资金
- `record_trade_result(is_win)` - 记录交易结果
- `reset_daily()` - 每日重置

**And** 状态持久化到 `system_state` 表

## Tasks / Subtasks

- [x] Task 1: 定义状态数据模型 (AC: 1)
  - [x] 1.1 创建 `StateSnapshot` Pydantic 模型包含所有状态字段
  - [x] 1.2 添加 `model_config = ConfigDict(frozen=True)` 确保不可变
  - [x] 1.3 添加 `to_dict()` 方法用于序列化
  - [x] 1.4 添加 `from_dict()` 类方法用于反序列化

- [x] Task 2: 实现 ThreadSafeState 类 (AC: 1, 2)
  - [x] 2.1 创建 `ThreadSafeState` 类
  - [x] 2.2 初始化私有状态变量 (`_capital`, `_daily_pnl`, `_consecutive_losses`, `_open_positions_count`, `_trading_enabled`, `_reduced_mode`)
  - [x] 2.3 初始化 `asyncio.Lock` 实例
  - [x] 2.4 从配置加载初始资金 (`settings.initial_capital`)

- [x] Task 3: 实现状态访问方法 (AC: 3)
  - [x] 3.1 实现 `get_state()` 返回 `StateSnapshot` 副本
  - [x] 3.2 实现 `update_capital(amount: float)` 更新资金和每日盈亏
  - [x] 3.3 实现 `record_trade_result(is_win: bool)` 更新连续亏损计数
  - [x] 3.4 实现 `reset_daily()` 重置每日状态
  - [x] 3.5 实现 `set_trading_enabled(enabled: bool)` 设置交易开关
  - [x] 3.6 实现 `set_reduced_mode(reduced: bool)` 设置降级模式
  - [x] 3.7 实现 `increment_open_positions()` 和 `decrement_open_positions()`

- [x] Task 4: 实现状态持久化 (AC: 4)
  - [x] 4.1 实现 `persist()` 方法将状态保存到 `system_state` 表
  - [x] 4.2 实现 `restore()` 类方法从 `system_state` 表恢复状态
  - [x] 4.3 使用 JSON 序列化状态值
  - [x] 4.4 持久化时记录 `updated_at` 时间戳

- [x] Task 5: 更新模块导出 (AC: All)
  - [x] 5.1 更新 `src/core/__init__.py` 导出 `ThreadSafeState` 和 `StateSnapshot`
  - [x] 5.2 添加 `__all__` 列表

- [x] Task 6: 编写单元测试 (AC: All)
  - [x] 6.1 创建 `tests/test_core/test_state.py`
  - [x] 6.2 测试初始状态正确性
  - [x] 6.3 测试 `get_state()` 返回不可变副本
  - [x] 6.4 测试 `update_capital()` 更新资金和 PnL
  - [x] 6.5 测试 `record_trade_result()` 更新连续亏损
  - [x] 6.6 测试 `reset_daily()` 重置状态
  - [x] 6.7 测试并发访问安全性 (使用 `asyncio.gather`)
  - [x] 6.8 测试持久化和恢复功能

- [x] Task 7: 代码质量检查 (AC: All)
  - [x] 7.1 运行 `mypy src/core/state.py` 无错误
  - [x] 7.2 运行 `black --check src/core/state.py` 通过
  - [x] 7.3 运行 `isort --check src/core/state.py` 通过
  - [x] 7.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md#Core Dependencies]

**状态管理使用 asyncio.Lock:**
- 使用 `asyncio.Lock` 而非 `threading.Lock` (异步环境)
- 所有状态访问方法都是异步的 (`async`)
- 使用 `async with self._lock:` 保护临界区

### 状态字段定义 [Source: epics.md#Story 4.2]

| 字段 | 类型 | 初始值 | 说明 |
|------|------|--------|------|
| `current_capital` | float | `settings.initial_capital` | 当前资金 |
| `daily_pnl` | float | 0.0 | 当日盈亏 |
| `consecutive_losses` | int | 0 | 连续亏损次数 |
| `open_positions_count` | int | 0 | 当前持仓数量 |
| `trading_enabled` | bool | True | 是否允许交易 |
| `reduced_mode` | bool | False | 是否处于降级模式 |

### system_state 表结构 [Source: src/storage/database.py]

```sql
CREATE TABLE system_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**存储格式:**
- key: `trading_state`
- value: JSON 序列化的状态字典

### 实现模板

**src/core/state.py:**

```python
"""Thread-safe state management for the Polymarket Trader application.

This module provides a thread-safe state manager that handles trading state
including capital, PnL, and risk control flags.
"""

from __future__ import annotations

__all__ = ["StateSnapshot", "ThreadSafeState", "get_state_manager"]

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.config import settings
from src.storage.database import get_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StateSnapshot(BaseModel):
    """Immutable snapshot of trading state.

    Attributes:
        current_capital: Current capital in USD
        daily_pnl: Daily profit/loss
        consecutive_losses: Number of consecutive losing trades
        open_positions_count: Number of currently open positions
        trading_enabled: Whether trading is enabled
        reduced_mode: Whether system is in reduced position mode
        updated_at: Timestamp of last update
    """

    model_config = ConfigDict(frozen=True)

    current_capital: float
    daily_pnl: float = 0.0
    consecutive_losses: int = 0
    open_positions_count: int = 0
    trading_enabled: bool = True
    reduced_mode: bool = False
    updated_at: datetime | None = None


class ThreadSafeState:
    """Thread-safe state manager for trading state.

    Uses asyncio.Lock to ensure safe concurrent access to state.
    Supports persistence to database for recovery.

    Attributes:
        _capital: Current capital
        _daily_pnl: Daily profit/loss
        _consecutive_losses: Consecutive loss count
        _open_positions_count: Open positions count
        _trading_enabled: Trading enabled flag
        _reduced_mode: Reduced mode flag
        _lock: Async lock for thread safety
    """

    def __init__(self, initial_capital: float | None = None) -> None:
        """Initialize state manager.

        Args:
            initial_capital: Initial capital amount (defaults to settings.initial_capital)
        """
        self._capital: float = initial_capital or settings.initial_capital
        self._daily_pnl: float = 0.0
        self._consecutive_losses: int = 0
        self._open_positions_count: int = 0
        self._trading_enabled: bool = True
        self._reduced_mode: bool = False
        self._lock: asyncio.Lock = asyncio.Lock()

    async def get_state(self) -> StateSnapshot:
        """Get current state snapshot.

        Returns:
            StateSnapshot: Immutable copy of current state
        """
        async with self._lock:
            return StateSnapshot(
                current_capital=self._capital,
                daily_pnl=self._daily_pnl,
                consecutive_losses=self._consecutive_losses,
                open_positions_count=self._open_positions_count,
                trading_enabled=self._trading_enabled,
                reduced_mode=self._reduced_mode,
                updated_at=datetime.utcnow(),
            )

    async def update_capital(self, amount: float) -> None:
        """Update capital and daily PnL.

        Args:
            amount: Amount to add (positive) or subtract (negative)
        """
        async with self._lock:
            self._capital += amount
            self._daily_pnl += amount
            logger.info(f"💰 Capital updated: ${self._capital:.2f} (daily PnL: ${self._daily_pnl:.2f})")

    async def record_trade_result(self, is_win: bool) -> None:
        """Record trade result for consecutive loss tracking.

        Args:
            is_win: Whether the trade was profitable
        """
        async with self._lock:
            if is_win:
                self._consecutive_losses = 0
                logger.info("📊 Trade result: WIN, consecutive losses reset to 0")
            else:
                self._consecutive_losses += 1
                logger.warning(f"📊 Trade result: LOSS, consecutive losses: {self._consecutive_losses}")

    async def reset_daily(self) -> None:
        """Reset daily state (called at market open or day start)."""
        async with self._lock:
            self._daily_pnl = 0.0
            self._consecutive_losses = 0
            logger.info("📊 Daily state reset: daily_pnl=0, consecutive_losses=0")

    async def set_trading_enabled(self, enabled: bool) -> None:
        """Set trading enabled flag.

        Args:
            enabled: Whether trading should be enabled
        """
        async with self._lock:
            self._trading_enabled = enabled
            status = "enabled" if enabled else "DISABLED"
            logger.info(f"🚦 Trading {status}")

    async def set_reduced_mode(self, reduced: bool) -> None:
        """Set reduced mode flag.

        Args:
            reduced: Whether to enter reduced mode
        """
        async with self._lock:
            self._reduced_mode = reduced
            status = "ENTERING" if reduced else "EXITING"
            logger.warning(f"⚠️ {status} reduced mode")

    async def increment_open_positions(self) -> None:
        """Increment open positions count."""
        async with self._lock:
            self._open_positions_count += 1
            logger.info(f"📊 Open positions: {self._open_positions_count}")

    async def decrement_open_positions(self) -> None:
        """Decrement open positions count."""
        async with self._lock:
            self._open_positions_count = max(0, self._open_positions_count - 1)
            logger.info(f"📊 Open positions: {self._open_positions_count}")

    async def persist(self) -> None:
        """Persist current state to database."""
        snapshot = await self.get_state()
        state_dict = snapshot.model_dump(mode="json")

        async with get_connection() as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO system_state (key, value, updated_at)
                VALUES (?, ?, ?)
                """,
                ("trading_state", json.dumps(state_dict), datetime.utcnow().isoformat()),
            )
            await conn.commit()
            logger.info("💾 State persisted to database")

    @classmethod
    async def restore(cls, initial_capital: float | None = None) -> "ThreadSafeState":
        """Restore state from database.

        Args:
            initial_capital: Fallback initial capital if no state in database

        Returns:
            ThreadSafeState: Restored state manager instance
        """
        instance = cls(initial_capital)

        try:
            async with get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT value FROM system_state WHERE key = ?",
                    ("trading_state",),
                )
                row = await cursor.fetchone()

                if row:
                    state_dict = json.loads(row[0])
                    instance._capital = state_dict.get("current_capital", instance._capital)
                    instance._daily_pnl = state_dict.get("daily_pnl", 0.0)
                    instance._consecutive_losses = state_dict.get("consecutive_losses", 0)
                    instance._open_positions_count = state_dict.get("open_positions_count", 0)
                    instance._trading_enabled = state_dict.get("trading_enabled", True)
                    instance._reduced_mode = state_dict.get("reduced_mode", False)
                    logger.info(f"🔄 State restored from database: capital=${instance._capital:.2f}")
                else:
                    logger.info("📊 No saved state found, using defaults")
        except Exception as e:
            logger.warning(f"⚠️ Failed to restore state: {e}, using defaults")

        return instance


# Module-level singleton
_state_manager: ThreadSafeState | None = None


def get_state_manager() -> ThreadSafeState:
    """Get state manager singleton instance.

    Returns:
        ThreadSafeState: The state manager instance
    """
    global _state_manager
    if _state_manager is None:
        _state_manager = ThreadSafeState()
    return _state_manager
```

### 项目结构 [Source: architecture.md#Project Structure]

**新建文件:**
```
src/core/
├── __init__.py           # 修改: 导出 ThreadSafeState 和 StateSnapshot
└── state.py              # 新建: ThreadSafeState 实现

tests/test_core/
├── __init__.py           # 新建
└── test_state.py         # 新建: ThreadSafeState 测试
```

### 测试策略

```python
# tests/test_core/test_state.py
"""Tests for ThreadSafeState."""

from __future__ import annotations

import asyncio

import pytest

from src.core.state import StateSnapshot, ThreadSafeState


class TestStateSnapshot:
    """测试 StateSnapshot 模型."""

    def test_create_snapshot(self) -> None:
        """测试创建状态快照."""
        snapshot = StateSnapshot(current_capital=200.0)
        assert snapshot.current_capital == 200.0
        assert snapshot.daily_pnl == 0.0
        assert snapshot.consecutive_losses == 0

    def test_snapshot_is_frozen(self) -> None:
        """测试快照不可变."""
        snapshot = StateSnapshot(current_capital=200.0)
        with pytest.raises(Exception):  # ValidationError
            snapshot.current_capital = 300.0


class TestThreadSafeState:
    """测试 ThreadSafeState."""

    @pytest.fixture
    def state(self) -> ThreadSafeState:
        """创建测试用状态管理器."""
        return ThreadSafeState(initial_capital=200.0)

    @pytest.mark.asyncio
    async def test_initial_state(self, state: ThreadSafeState) -> None:
        """测试初始状态."""
        snapshot = await state.get_state()
        assert snapshot.current_capital == 200.0
        assert snapshot.daily_pnl == 0.0
        assert snapshot.consecutive_losses == 0
        assert snapshot.trading_enabled is True
        assert snapshot.reduced_mode is False

    @pytest.mark.asyncio
    async def test_update_capital(self, state: ThreadSafeState) -> None:
        """测试更新资金."""
        await state.update_capital(10.0)
        snapshot = await state.get_state()
        assert snapshot.current_capital == 210.0
        assert snapshot.daily_pnl == 10.0

        await state.update_capital(-5.0)
        snapshot = await state.get_state()
        assert snapshot.current_capital == 205.0
        assert snapshot.daily_pnl == 5.0

    @pytest.mark.asyncio
    async def test_record_win_resets_consecutive_losses(self, state: ThreadSafeState) -> None:
        """测试盈利重置连续亏损."""
        await state.record_trade_result(False)
        await state.record_trade_result(False)
        assert (await state.get_state()).consecutive_losses == 2

        await state.record_trade_result(True)
        assert (await state.get_state()).consecutive_losses == 0

    @pytest.mark.asyncio
    async def test_record_loss_increments_consecutive_losses(self, state: ThreadSafeState) -> None:
        """测试亏损增加连续亏损计数."""
        await state.record_trade_result(False)
        assert (await state.get_state()).consecutive_losses == 1

        await state.record_trade_result(False)
        assert (await state.get_state()).consecutive_losses == 2

    @pytest.mark.asyncio
    async def test_reset_daily(self, state: ThreadSafeState) -> None:
        """测试每日重置."""
        await state.update_capital(50.0)
        await state.record_trade_result(False)
        await state.record_trade_result(False)

        await state.reset_daily()
        snapshot = await state.get_state()
        assert snapshot.daily_pnl == 0.0
        assert snapshot.consecutive_losses == 0
        # Capital should NOT be reset
        assert snapshot.current_capital == 250.0

    @pytest.mark.asyncio
    async def test_set_trading_enabled(self, state: ThreadSafeState) -> None:
        """测试设置交易开关."""
        await state.set_trading_enabled(False)
        assert (await state.get_state()).trading_enabled is False

        await state.set_trading_enabled(True)
        assert (await state.get_state()).trading_enabled is True

    @pytest.mark.asyncio
    async def test_set_reduced_mode(self, state: ThreadSafeState) -> None:
        """测试设置降级模式."""
        await state.set_reduced_mode(True)
        assert (await state.get_state()).reduced_mode is True

        await state.set_reduced_mode(False)
        assert (await state.get_state()).reduced_mode is False

    @pytest.mark.asyncio
    async def test_concurrent_access(self, state: ThreadSafeState) -> None:
        """测试并发访问安全性."""
        async def update_capital_task(amount: float, times: int) -> None:
            for _ in range(times):
                await state.update_capital(amount)

        # 并发执行 10 个任务，每个任务增加 1.0，执行 100 次
        tasks = [update_capital_task(1.0, 100) for _ in range(10)]
        await asyncio.gather(*tasks)

        snapshot = await state.get_state()
        assert snapshot.current_capital == 200.0 + 1000.0  # 200 + 10*100

    @pytest.mark.asyncio
    async def test_open_positions_count(self, state: ThreadSafeState) -> None:
        """测试持仓计数."""
        await state.increment_open_positions()
        assert (await state.get_state()).open_positions_count == 1

        await state.increment_open_positions()
        assert (await state.get_state()).open_positions_count == 2

        await state.decrement_open_positions()
        assert (await state.get_state()).open_positions_count == 1

    @pytest.mark.asyncio
    async def test_decrement_positions_does_not_go_negative(self, state: ThreadSafeState) -> None:
        """测试持仓计数不会变为负数."""
        await state.decrement_open_positions()
        assert (await state.get_state()).open_positions_count == 0
```

### 依赖关系

**本故事依赖:**
- Story 1.2: 配置管理系统 (已完成 - `settings.initial_capital`)
- Story 1.6: 数据库初始化 (已完成 - `system_state` 表)

**后续故事依赖本故事:**
- Story 4.3: 熔断机制实现 (需要 ThreadSafeState 管理熔断状态)
- Story 4.4: 交易前风险检查 (需要 ThreadSafeState 获取当前状态)
- Story 5.2: Paper Trading 执行器 (需要 ThreadSafeState 更新资金)

### 前一个故事学习 [Source: 4-1-risk-control-configuration.md]

**从 Story 4.1 学到的模式:**

1. **使用 Pydantic v2** - `BaseModel`, `ConfigDict`, `Field`
2. **完整 docstring** - 包含 Args, Returns, Raises, Example
3. **单元测试覆盖** - 正常情况 + 边界情况 + 错误情况
4. **`__all__` 导出列表** - 明确模块公共 API
5. **类型注解使用 `float | None`** - 而非 `Optional[float]`
6. **日志使用 emoji** - `💰`, `📊`, `⚠️`, `🚦`, `💾`, `🔄`

### 实现注意事项

**关键点:**

1. **异步锁** - 使用 `asyncio.Lock` 而非 `threading.Lock`，因为整个系统是异步的
2. **状态不可变** - `get_state()` 返回 `StateSnapshot` 不可变副本，防止外部修改
3. **资金 vs 每日盈亏** - `reset_daily()` 只重置 `daily_pnl`，不重置 `current_capital`
4. **持仓计数边界** - `decrement_open_positions()` 不会让计数变为负数
5. **持久化格式** - 使用 JSON 序列化，便于调试和跨语言兼容

**Pydantic v2 最佳实践:**

```python
# 冻结模型（不可变）
class StateSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    ...

# 序列化为 JSON 兼容字典
state_dict = snapshot.model_dump(mode="json")
```

### References

- [Source: architecture.md#Core Dependencies] - 状态管理技术栈
- [Source: architecture.md#Project Structure] - src/core/ 目录结构
- [Source: src/storage/database.py] - system_state 表结构
- [Source: src/config.py] - RiskControlSettings 和 TradingSettings
- [Source: epics.md#Story 4.2] - 原始 Story 定义
- [Source: 4-1-risk-control-configuration.md] - 前一个故事参考

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- All acceptance criteria met
- All 7 tasks and subtasks completed
- `to_dict()` and `from_dict()` methods added to StateSnapshot for serialization/deserialization
- Full test coverage with 416 lines of tests including concurrency tests
- All code quality checks passed (mypy, black, isort)

### File List

- `src/core/state.py` - ThreadSafeState and StateSnapshot implementation (416 lines)
- `src/core/__init__.py` - Module exports
- `tests/test_core/__init__.py` - Test module init
- `tests/test_core/test_state.py` - Unit tests (416 lines)
