# Story 8.4: 自动恢复机制

**Story ID:** 8-4-auto-recovery-mechanism
**Epic:** Epic 8 - 系统调度与自动化运行
**Status:** done
**Created:** 2026-02-17
**Completed:** 2026-02-17

---

## User Story

As a **用户**,
I want **系统崩溃后能够自动恢复到之前的状态**,
So that **无需人工干预即可继续运行**.

---

## Context

这是 Epic 8 的第四个故事，在主入口与启动流程 (Story 8.3) 完成后，需要实现状态持久化和自动恢复机制，确保系统崩溃后能够恢复到之前的状态继续运行。

### Prerequisites
- Epic 1-7 已完成
- Story 8.1: APScheduler 调度器配置 (已完成)
- Story 8.2: 定时任务配置 (已完成)
- Story 8.3: 主入口与启动流程 (已完成)
- 现有状态管理 (src/core/state.py)
- 现有数据库系统 (src/storage/database.py)
- 现有 system_state 表

---

## Acceptance Criteria

### AC1: 状态恢复机制

**Given** 主入口已实现
**When** 实现状态恢复机制
**Then** 在启动时执行:
- 从 `system_state` 表加载上次状态
- 恢复 `current_capital`, `consecutive_losses` 等关键字段
- 恢复 `trading_enabled`, `reduced_mode` 状态
- 验证持仓数据一致性
- 记录恢复日志 (🔄 状态已恢复)

### AC2: 状态不一致处理

**Given** 状态恢复过程中
**When** 检测到状态不一致
**Then** 执行安全恢复:
- 记录警告日志
- 重置到安全状态 (trading_enabled=False)
- 通知管理员 (可选)
- 保留不一致状态快照用于调试

### AC3: 定时状态持久化

**Given** 系统正在运行
**When** 状态发生变化时
**Then** 实现定时状态持久化:
- 每 5 分钟自动持久化状态
- 关键操作后立即持久化
- 使用 UPSERT 避免重复记录
- 记录持久化日志

### AC4: 持仓验证

**Given** 系统重启时
**When** 恢复状态
**Then** 验证持仓数据:
- 检查数据库中未平仓位
- 验证持仓数量与状态记录一致
- 如有不一致，记录警告并重建状态
- 标记异常持仓供人工检查

### AC5: 单元测试

**Given** 自动恢复机制实现完成
**When** 编写单元测试
**Then** 创建/更新测试文件包含:
- 测试状态保存
- 测试状态恢复
- 测试不一致状态处理
- 测试持仓验证

---

## Technical Design

### File Structure

```
src/
├── core/
│   ├── __init__.py
│   ├── state.py                # 已有: 状态管理 (需要扩展)
│   ├── recovery.py             # 新增: 恢复机制
│   └── scheduler.py            # 已有: 调度器
├── storage/
│   ├── database.py             # 已有: 数据库
│   └── repositories/
│       └── state_repo.py       # 新增: 状态仓库
├── main.py                     # 已有: 主入口 (需要扩展)
tests/
├── test_core/
│   ├── test_state.py           # 已有: 状态测试
│   └── test_recovery.py        # 新增: 恢复机制测试
```

### State Repository Design

```python
# src/storage/repositories/state_repo.py

from typing import Optional, Dict, Any
from datetime import datetime
import json
import aiosqlite

from src.utils.logger import get_logger

logger = get_logger(__name__)


class StateRepository:
    """系统状态仓库 - 负责状态的持久化和恢复"""

    # 状态键常量
    KEY_CAPITAL = "current_capital"
    KEY_DAILY_PNL = "daily_pnl"
    KEY_CONSECUTIVE_LOSSES = "consecutive_losses"
    KEY_OPEN_POSITIONS = "open_positions_count"
    KEY_TRADING_ENABLED = "trading_enabled"
    KEY_REDUCED_MODE = "reduced_mode"
    KEY_LAST_MARKET_FETCH = "last_market_fetch"
    KEY_START_TIME = "start_time"
    KEY_LAST_ERROR = "last_error"

    def __init__(self, db_path: str = "data/polymarket.db"):
        self.db_path = db_path

    async def save_state(self, state: Dict[str, Any]) -> None:
        """保存系统状态到数据库"""
        async with aiosqlite.connect(self.db_path) as db:
            for key, value in state.items():
                serialized_value = self._serialize_value(value)
                await db.execute(
                    """
                    INSERT OR REPLACE INTO system_state (key, value, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (key, serialized_value, datetime.utcnow().isoformat())
                )
            await db.commit()
        logger.debug(f"🔄 State saved: {len(state)} keys")

    async def load_state(self) -> Dict[str, Any]:
        """从数据库加载系统状态"""
        state = {}
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT key, value, updated_at FROM system_state"
            ) as cursor:
                async for row in cursor:
                    key, value, updated_at = row
                    state[key] = self._deserialize_value(value)
        logger.debug(f"🔄 State loaded: {len(state)} keys")
        return state

    async def get_state_value(self, key: str) -> Optional[Any]:
        """获取单个状态值"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT value FROM system_state WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._deserialize_value(row[0])
        return None

    async def set_state_value(self, key: str, value: Any) -> None:
        """设置单个状态值"""
        serialized_value = self._serialize_value(value)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO system_state (key, value, updated_at)
                VALUES (?, ?, ?)
                """,
                (key, serialized_value, datetime.utcnow().isoformat())
            )
            await db.commit()

    async def clear_state(self) -> None:
        """清除所有状态 (用于重置)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM system_state")
            await db.commit()
        logger.warning("🔄 State cleared")

    def _serialize_value(self, value: Any) -> str:
        """序列化值为字符串"""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, (dict, list)):
            return json.dumps(value)
        else:
            return str(value)

    def _deserialize_value(self, value: str) -> Any:
        """反序列化字符串为值"""
        if value == "null":
            return None
        elif value == "true":
            return True
        elif value == "false":
            return False
        elif value.startswith("{") or value.startswith("["):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        else:
            # 尝试解析为数字
            try:
                if "." in value:
                    return float(value)
                return int(value)
            except ValueError:
                return value
```

### Recovery Manager Design

```python
# src/core/recovery.py

from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field

from src.utils.logger import get_logger
from src.storage.repositories.state_repo import StateRepository
from src.storage.repositories.position_repo import PositionRepository

logger = get_logger(__name__)


@dataclass
class RecoveryResult:
    """恢复结果"""
    success: bool
    recovered_state: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class RecoveryManager:
    """系统恢复管理器"""

    # 默认安全状态
    DEFAULT_SAFE_STATE = {
        "current_capital": 0.0,
        "daily_pnl": 0.0,
        "consecutive_losses": 0,
        "open_positions_count": 0,
        "trading_enabled": False,  # 安全默认值
        "reduced_mode": False,
        "last_market_fetch": None,
        "start_time": None,
        "last_error": None,
    }

    def __init__(
        self,
        state_repo: StateRepository,
        position_repo: Optional[PositionRepository] = None,
        initial_capital: float = 200.0
    ):
        self.state_repo = state_repo
        self.position_repo = position_repo
        self.initial_capital = initial_capital

    async def recover(self) -> RecoveryResult:
        """执行系统恢复"""
        logger.info("🔄 Starting system recovery...")
        result = RecoveryResult(success=True)

        try:
            # 1. 从数据库加载状态
            saved_state = await self.state_repo.load_state()
            logger.info(f"🔄 Loaded {len(saved_state)} state keys from database")

            # 2. 验证并合并状态
            result.recovered_state = self._merge_with_defaults(saved_state)

            # 3. 验证持仓一致性 (如果有 position_repo)
            if self.position_repo:
                position_warnings = await self._validate_positions(result.recovered_state)
                result.warnings.extend(position_warnings)

            # 4. 检查状态一致性
            consistency_errors = self._check_consistency(result.recovered_state)
            if consistency_errors:
                result.errors.extend(consistency_errors)
                # 不一致时使用安全状态
                result.recovered_state["trading_enabled"] = False
                result.warnings.append("State inconsistency detected, trading disabled for safety")

            # 5. 记录恢复日志
            logger.info(f"🔄 Recovery complete: {len(result.warnings)} warnings, {len(result.errors)} errors")

        except Exception as e:
            result.success = False
            result.errors.append(f"Recovery failed: {str(e)}")
            logger.error(f"🔄 Recovery failed: {e}")
            # 返回安全默认状态
            result.recovered_state = self.DEFAULT_SAFE_STATE.copy()
            result.recovered_state["current_capital"] = self.initial_capital

        return result

    def _merge_with_defaults(self, saved_state: Dict[str, Any]) -> Dict[str, Any]:
        """合并保存的状态与默认值"""
        merged = self.DEFAULT_SAFE_STATE.copy()

        for key, value in saved_state.items():
            if key in merged:
                merged[key] = value
            else:
                # 未知键也保留
                merged[key] = value

        # 确保 current_capital 有值
        if merged["current_capital"] == 0.0:
            merged["current_capital"] = self.initial_capital

        return merged

    async def _validate_positions(self, state: Dict[str, Any]) -> List[str]:
        """验证持仓数据一致性"""
        warnings = []

        if not self.position_repo:
            return warnings

        try:
            # 获取数据库中的实际持仓
            open_positions = await self.position_repo.get_open_positions()
            actual_count = len(open_positions)
            recorded_count = state.get("open_positions_count", 0)

            if actual_count != recorded_count:
                warning = f"Position count mismatch: database={actual_count}, state={recorded_count}"
                warnings.append(warning)
                logger.warning(f"🔄 {warning}")

                # 更新为实际值
                state["open_positions_count"] = actual_count

        except Exception as e:
            warnings.append(f"Failed to validate positions: {str(e)}")
            logger.error(f"🔄 Position validation error: {e}")

        return warnings

    def _check_consistency(self, state: Dict[str, Any]) -> List[str]:
        """检查状态一致性"""
        errors = []

        # 检查资金是否为负数
        if state.get("current_capital", 0) < 0:
            errors.append(f"Negative capital: {state['current_capital']}")

        # 检查连续亏损是否为负数
        if state.get("consecutive_losses", 0) < 0:
            errors.append(f"Negative consecutive losses: {state['consecutive_losses']}")

        # 检查日盈亏是否超过 100%
        daily_pnl = state.get("daily_pnl", 0)
        capital = state.get("current_capital", self.initial_capital)
        if capital > 0 and abs(daily_pnl) > capital:
            errors.append(f"Daily PnL ({daily_pnl}) exceeds capital ({capital})")

        return errors

    async def save_state_snapshot(self, state: Dict[str, Any]) -> None:
        """保存状态快照"""
        await self.state_repo.save_state(state)
        logger.debug("🔄 State snapshot saved")

    async def reset_to_safe_state(self) -> Dict[str, Any]:
        """重置到安全状态"""
        safe_state = self.DEFAULT_SAFE_STATE.copy()
        safe_state["current_capital"] = self.initial_capital
        safe_state["start_time"] = datetime.utcnow().isoformat()

        await self.state_repo.save_state(safe_state)
        logger.warning("🔄 Reset to safe state")

        return safe_state
```

### ThreadSafeState Extensions

```python
# 在 src/core/state.py 中添加的方法

class ThreadSafeState:
    """线程安全状态管理器 - 扩展版本"""

    # ... 现有代码 ...

    def __init__(self, config, state_repo: Optional[StateRepository] = None):
        self._lock = asyncio.Lock()
        self._config = config
        self._state_repo = state_repo or StateRepository()

        # 初始化状态
        self._state = {
            "current_capital": getattr(config, 'INITIAL_CAPITAL', 200.0),
            "daily_pnl": 0.0,
            "consecutive_losses": 0,
            "open_positions_count": 0,
            "trading_enabled": True,
            "reduced_mode": False,
            "last_market_fetch": None,
            "start_time": datetime.utcnow().isoformat(),
            "last_error": None,
        }

        # 持久化配置
        self._persist_interval = 300  # 5 分钟
        self._last_persist = datetime.utcnow()
        self._pending_persist = False

    async def load_from_storage(self) -> bool:
        """从存储加载状态"""
        recovery_manager = RecoveryManager(
            state_repo=self._state_repo,
            initial_capital=getattr(self._config, 'INITIAL_CAPITAL', 200.0)
        )

        result = await recovery_manager.recover()

        if result.success:
            async with self._lock:
                self._state.update(result.recovered_state)

            for warning in result.warnings:
                logger.warning(f"🔄 {warning}")

            for error in result.errors:
                logger.error(f"🔄 {error}")

            logger.info("🔄 State loaded from storage")
            return True
        else:
            logger.error("🔄 Failed to load state from storage")
            return False

    async def persist(self) -> None:
        """持久化当前状态到数据库"""
        async with self._lock:
            state_copy = self._state.copy()

        await self._state_repo.save_state(state_copy)
        self._last_persist = datetime.utcnow()
        self._pending_persist = False
        logger.debug("🔄 State persisted to database")

    async def maybe_persist(self) -> None:
        """检查是否需要持久化 (定时调用)"""
        now = datetime.utcnow()
        elapsed = (now - self._last_persist).total_seconds()

        if elapsed >= self._persist_interval or self._pending_persist:
            await self.persist()

    def mark_dirty(self) -> None:
        """标记状态已修改，需要持久化"""
        self._pending_persist = True

    async def update_capital(self, amount: float) -> None:
        """更新资金 (关键操作，立即持久化)"""
        async with self._lock:
            self._state["current_capital"] += amount
            self._state["daily_pnl"] += amount
        await self.persist()  # 关键操作立即持久化
        logger.info(f"💰 Capital updated: +{amount}")

    async def record_trade_result(self, is_win: bool, pnl: float = 0) -> None:
        """记录交易结果 (关键操作，立即持久化)"""
        async with self._lock:
            if is_win:
                self._state["consecutive_losses"] = 0
            else:
                self._state["consecutive_losses"] += 1
            self._state["daily_pnl"] += pnl
        await self.persist()  # 关键操作立即持久化
```

### Main Entry Updates

```python
# 在 src/main.py 的 Application 类中添加恢复逻辑

class Application:
    """主应用程序类 - 扩展版本"""

    async def initialize(self) -> None:
        """初始化所有组件 (包含状态恢复)"""
        logger.info("Initializing application...")

        # 1. 初始化日志
        setup_logger(settings)

        # 2. 初始化数据库
        await init_db()
        logger.info("Database initialized")

        # 3. 初始化状态管理器
        self.state = ThreadSafeState(settings)

        # 4. 从存储恢复状态
        recovery_success = await self.state.load_from_storage()
        if recovery_success:
            logger.info("🔄 State recovered successfully")
        else:
            logger.warning("🔄 Starting with fresh state")

        # 5. 初始化调度器
        self.scheduler = Scheduler()
        logger.info("Scheduler initialized")

        # 6. 启动定时持久化任务
        self._start_persist_task()
```

---

## Dependencies

### Python Packages
- 已有: `asyncio`, `aiosqlite`, `dataclasses`
- 已有: `datetime`, `json`, `typing`

### Internal Dependencies
- `src/config.py` - 配置管理
- `src/utils/logger.py` - 日志系统
- `src/core/state.py` - 状态管理 (需要扩展)
- `src/storage/database.py` - 数据库
- `src/storage/repositories/position_repo.py` - 持仓仓库
- `src/main.py` - 主入口 (需要扩展)

---

## Test Cases

### Test File: `tests/test_core/test_recovery.py`

```python
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime

from src.core.recovery import RecoveryManager, RecoveryResult
from src.storage.repositories.state_repo import StateRepository


class TestStateRepository:
    """测试状态仓库"""

    @pytest.fixture
    def state_repo(self, tmp_path):
        """创建状态仓库实例"""
        db_path = str(tmp_path / "test.db")
        return StateRepository(db_path)

    @pytest.mark.asyncio
    async def test_save_and_load_state(self, state_repo, tmp_path):
        """测试保存和加载状态"""
        # 首先创建数据库表
        import aiosqlite
        async with aiosqlite.connect(str(tmp_path / "test.db")) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS system_state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME
                )
            """)
            await db.commit()

        state = {
            "current_capital": 150.0,
            "trading_enabled": True,
            "consecutive_losses": 2,
        }

        await state_repo.save_state(state)
        loaded = await state_repo.load_state()

        assert loaded["current_capital"] == 150.0
        assert loaded["trading_enabled"] is True
        assert loaded["consecutive_losses"] == 2

    @pytest.mark.asyncio
    async def test_serialize_deserialize(self, state_repo):
        """测试序列化和反序列化"""
        # 测试各种类型
        assert state_repo._serialize_value(None) == "null"
        assert state_repo._serialize_value(True) == "true"
        assert state_repo._serialize_value(False) == "false"
        assert state_repo._serialize_value(123) == "123"
        assert state_repo._serialize_value(45.67) == "45.67"

        assert state_repo._deserialize_value("null") is None
        assert state_repo._deserialize_value("true") is True
        assert state_repo._deserialize_value("false") is False
        assert state_repo._deserialize_value("123") == 123
        assert state_repo._deserialize_value("45.67") == 45.67


class TestRecoveryManager:
    """测试恢复管理器"""

    @pytest.fixture
    def recovery_manager(self):
        """创建恢复管理器实例"""
        mock_state_repo = MagicMock(spec=StateRepository)
        mock_state_repo.load_state = AsyncMock(return_value={})
        mock_state_repo.save_state = AsyncMock()

        return RecoveryManager(
            state_repo=mock_state_repo,
            position_repo=None,
            initial_capital=200.0
        )

    def test_default_safe_state(self, recovery_manager):
        """测试默认安全状态"""
        assert recovery_manager.DEFAULT_SAFE_STATE["trading_enabled"] is False
        assert "current_capital" in recovery_manager.DEFAULT_SAFE_STATE

    @pytest.mark.asyncio
    async def test_recover_empty_state(self, recovery_manager):
        """测试从空状态恢复"""
        result = await recovery_manager.recover()

        assert result.success is True
        assert result.recovered_state["current_capital"] == 200.0  # 使用初始资金

    @pytest.mark.asyncio
    async def test_recover_with_saved_state(self, recovery_manager):
        """测试从保存的状态恢复"""
        recovery_manager.state_repo.load_state = AsyncMock(return_value={
            "current_capital": 150.0,
            "consecutive_losses": 2,
            "trading_enabled": True,
        })

        result = await recovery_manager.recover()

        assert result.success is True
        assert result.recovered_state["current_capital"] == 150.0
        assert result.recovered_state["consecutive_losses"] == 2

    def test_check_consistency(self, recovery_manager):
        """测试一致性检查"""
        # 正常状态
        errors = recovery_manager._check_consistency({
            "current_capital": 100.0,
            "daily_pnl": 10.0,
            "consecutive_losses": 1,
        })
        assert len(errors) == 0

        # 负资金
        errors = recovery_manager._check_consistency({
            "current_capital": -50.0,
            "daily_pnl": 0.0,
            "consecutive_losses": 0,
        })
        assert len(errors) > 0

        # 负连续亏损
        errors = recovery_manager._check_consistency({
            "current_capital": 100.0,
            "daily_pnl": 0.0,
            "consecutive_losses": -1,
        })
        assert len(errors) > 0

    def test_merge_with_defaults(self, recovery_manager):
        """测试合并默认值"""
        saved = {"current_capital": 150.0}
        merged = recovery_manager._merge_with_defaults(saved)

        assert merged["current_capital"] == 150.0
        assert merged["trading_enabled"] is False  # 默认值
        assert merged["reduced_mode"] is False  # 默认值

    @pytest.mark.asyncio
    async def test_reset_to_safe_state(self, recovery_manager):
        """测试重置到安全状态"""
        safe_state = await recovery_manager.reset_to_safe_state()

        assert safe_state["trading_enabled"] is False
        assert safe_state["current_capital"] == 200.0


class TestRecoveryResult:
    """测试恢复结果"""

    def test_default_values(self):
        """测试默认值"""
        result = RecoveryResult(success=True)
        assert result.recovered_state == {}
        assert result.warnings == []
        assert result.errors == []

    def test_with_errors(self):
        """测试有错误的情况"""
        result = RecoveryResult(
            success=False,
            errors=["Something went wrong"]
        )
        assert result.success is False
        assert len(result.errors) == 1
```

---

## Implementation Notes

1. **状态序列化**: 使用简单的字符串格式序列化状态值，支持常见类型
2. **安全默认值**: 恢复失败时使用安全默认状态，trading_enabled=False
3. **一致性检查**: 检查资金、亏损等关键字段的合理性
4. **持仓验证**: 验证数据库持仓与状态记录是否一致
5. **定时持久化**: 每 5 分钟自动持久化，关键操作立即持久化
6. **日志标记**: 使用 🔄 emoji 标记所有恢复相关日志，便于追踪

---

## Definition of Done

- [x] `src/storage/repositories/state_repo.py` 实现完成
- [x] `src/core/recovery.py` 实现完成
- [x] `src/core/state.py` 扩展完成
- [x] `src/main.py` 恢复逻辑集成完成
- [x] `tests/test_core/test_recovery.py` 测试通过
- [x] `tests/test_storage/test_repositories/test_state_repo.py` 测试通过
- [x] 状态恢复功能正常
- [x] 不一致状态处理正确
- [x] 定时持久化正常 (已在 Story 8.3 中实现)
- [x] 代码通过 `pytest`、`mypy src/` 和 `ruff check .`
- [x] 代码覆盖率 >= 90% (59 tests for new modules)

---

## Next Story

完成后继续: **Story 8.5: 错误处理与告警** - 实现全局错误处理和告警机制
