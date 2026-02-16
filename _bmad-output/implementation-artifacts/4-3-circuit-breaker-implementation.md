# Story 4.3: 熔断机制实现

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **用户**,
I want **系统在触发熔断条件时自动降低或停止交易**,
So that **我的资金免受重大损失**.

## Acceptance Criteria

**Given** 状态管理器已实现
**When** 实现 `src/core/circuit_breaker.py`
**Then** 实现以下熔断规则:

1. **连续亏损熔断:**
   - 连续亏损 3 次 → 降低仓位至 10%
   - 记录熔断触发日志 (⚠️)

2. **日亏损熔断:**
   - 当日亏损 >= 30% → 停止交易
   - 设置 `trading_enabled = False`

3. **资金门槛熔断:**
   - 资金 < $100 → 降低仓位至 10%
   - 记录警告日志

**And** 实现 `CircuitBreaker` 类:
- `check_trading_allowed()` - 检查是否允许交易
- `get_position_ratio()` - 获取当前仓位比例
- `record_loss()` - 记录亏损
- `reset()` - 重置熔断状态

## Tasks / Subtasks

- [x] Task 1: 创建 CircuitBreaker 类 (AC: 1, 2, 3)
  - [x] 1.1 创建 `src/core/circuit_breaker.py` 文件
  - [x] 1.2 定义 `CircuitBreaker` 类，接受 `ThreadSafeState` 和配置参数
  - [x] 1.3 初始化私有属性: `_state`, `_triggered_breakers` (触发记录)
  - [x] 1.4 从 `settings.risk` 加载熔断配置参数

- [x] Task 2: 实现连续亏损熔断 (AC: 1)
  - [x] 2.1 实现 `_check_consecutive_losses()` 私有方法
  - [x] 2.2 检查 `state.consecutive_losses >= consecutive_losses_limit`
  - [x] 2.3 触发时调用 `state.set_reduced_mode(True)` 并记录日志
  - [x] 2.4 将触发记录添加到 `_triggered_breakers`

- [x] Task 3: 实现日亏损熔断 (AC: 2)
  - [x] 3.1 实现 `_check_daily_loss()` 私有方法
  - [x] 3.2 计算日亏损比例: `abs(daily_pnl) / initial_capital`
  - [x] 3.3 检查 `日亏损比例 >= daily_loss_limit`
  - [x] 3.4 触发时调用 `state.set_trading_enabled(False)` 并记录日志
  - [x] 3.5 将触发记录添加到 `_triggered_breakers`

- [x] Task 4: 实现资金门槛熔断 (AC: 3)
  - [x] 4.1 实现 `_check_capital_threshold()` 私有方法
  - [x] 4.2 检查 `current_capital < capital_threshold`
  - [x] 4.3 触发时调用 `state.set_reduced_mode(True)` 并记录日志
  - [x] 4.4 将触发记录添加到 `_triggered_breakers`

- [x] Task 5: 实现公共接口方法 (AC: 4)
  - [x] 5.1 实现 `check_trading_allowed()` 方法执行所有熔断检查
  - [x] 5.2 实现 `get_position_ratio()` 方法返回当前建议仓位比例
  - [x] 5.3 实现 `record_loss(amount: float)` 方法更新亏损状态
  - [x] 5.4 实现 `reset()` 方法重置熔断状态
  - [x] 5.5 实现 `get_triggered_breakers()` 方法获取已触发的熔断列表

- [x] Task 6: 更新模块导出 (AC: All)
  - [x] 6.1 更新 `src/core/__init__.py` 导出 `CircuitBreaker`
  - [x] 6.2 更新 `__all__` 列表

- [x] Task 7: 编写单元测试 (AC: All)
  - [x] 7.1 创建 `tests/test_core/test_circuit_breaker.py`
  - [x] 7.2 测试初始状态（无熔断）
  - [x] 7.3 测试连续亏损熔断触发
  - [x] 7.4 测试日亏损熔断触发
  - [x] 7.5 测试资金门槛熔断触发
  - [x] 7.6 测试熔断恢复逻辑
  - [x] 7.7 测试 `get_position_ratio()` 返回正确比例
  - [x] 7.8 测试多个熔断同时触发场景

- [x] Task 8: 代码质量检查 (AC: All)
  - [x] 8.1 运行 `mypy src/core/circuit_breaker.py` 无错误
  - [x] 8.2 运行 `black --check src/core/circuit_breaker.py` 通过
  - [x] 8.3 运行 `isort --check src/core/circuit_breaker.py` 通过
  - [x] 8.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md#Core Dependencies]

**熔断机制位于 `src/core/` 目录:**
- 文件位置: `src/core/circuit_breaker.py`
- 与 `ThreadSafeState` 紧密集成
- 使用配置参数从 `settings.risk` 加载

### 熔断配置参数 [Source: src/config.py#RiskControlSettings]

| 参数 | 环境变量 | 默认值 | 说明 |
|------|----------|--------|------|
| `consecutive_losses_limit` | `CONSECUTIVE_LOSSES_LIMIT` | 3 | 连续亏损触发熔断 |
| `reduce_ratio_after_losses` | `REDUCE_RATIO_AFTER_LOSSES` | 0.10 | 连续亏损后降级比例 |
| `daily_loss_limit` | `DAILY_LOSS_LIMIT` | 0.30 | 日亏损停止门槛 (30%) |
| `capital_threshold` | `CAPITAL_THRESHOLD` | 100.0 | 低资金门槛 ($100) |
| `reduce_ratio_low_capital` | `REDUCE_RATIO_LOW_CAPITAL` | 0.10 | 低资金时降级比例 |
| `initial_capital` | `INITIAL_CAPITAL` | 200.0 | 初始资金 |

### 熔断规则逻辑

```
┌─────────────────────────────────────────────────────────────────┐
│                     熔断检查流程                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 连续亏损检查                                                │
│     if consecutive_losses >= 3:                                │
│         → set_reduced_mode(True)                               │
│         → position_ratio = 0.10                                │
│                                                                 │
│  2. 日亏损检查                                                  │
│     if abs(daily_pnl) / initial_capital >= 0.30:              │
│         → set_trading_enabled(False)                           │
│         → STOP TRADING                                         │
│                                                                 │
│  3. 资金门槛检查                                                │
│     if current_capital < 100:                                  │
│         → set_reduced_mode(True)                               │
│         → position_ratio = 0.10                                │
│                                                                 │
│  check_trading_allowed() 返回:                                 │
│     - allowed: bool (是否允许交易)                              │
│     - position_ratio: float (建议仓位比例)                      │
│     - reasons: list[str] (熔断原因列表)                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 实现模板

**src/core/circuit_breaker.py:**

```python
"""Circuit breaker implementation for risk control.

This module provides a circuit breaker that monitors trading state
and triggers protective measures when risk thresholds are exceeded.

Example:
    >>> from src.core.circuit_breaker import CircuitBreaker
    >>> from src.core.state import ThreadSafeState
    >>>
    >>> state = ThreadSafeState(initial_capital=200.0)
    >>> breaker = CircuitBreaker(state)
    >>>
    >>> # Check if trading is allowed
    >>> result = await breaker.check_trading_allowed()
    >>> if result.allowed:
    ...     position_ratio = result.position_ratio
    ...     # Execute trade with position_ratio
"""

from __future__ import annotations

__all__ = ["CircuitBreaker", "CircuitBreakerResult", "BreakerTriggerType"]

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from src.config import settings
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.core.state import ThreadSafeState

logger = get_logger(__name__)


class BreakerTriggerType(str, Enum):
    """Types of circuit breaker triggers."""

    CONSECUTIVE_LOSSES = "consecutive_losses"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    CAPITAL_THRESHOLD = "capital_threshold"


@dataclass
class BreakerTrigger:
    """Record of a circuit breaker trigger event."""

    trigger_type: BreakerTriggerType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: str = ""


@dataclass
class CircuitBreakerResult:
    """Result of circuit breaker check.

    Attributes:
        allowed: Whether trading is allowed
        position_ratio: Suggested position ratio (0-1)
        reasons: List of reasons if trading is not allowed or restricted
        triggers: List of triggered breakers
    """

    allowed: bool
    position_ratio: float = 1.0
    reasons: list[str] = field(default_factory=list)
    triggers: list[BreakerTrigger] = field(default_factory=list)


class CircuitBreaker:
    """Circuit breaker for risk control.

    Monitors trading state and triggers protective measures when
    risk thresholds are exceeded.

    The circuit breaker checks three conditions:
    1. Consecutive losses: Reduces position size after 3+ consecutive losses
    2. Daily loss limit: Stops trading when daily loss exceeds 30%
    3. Capital threshold: Reduces position size when capital falls below $100

    Attributes:
        _state: ThreadSafeState instance to monitor
        _consecutive_losses_limit: Threshold for consecutive loss breaker
        _reduce_ratio_after_losses: Position ratio after consecutive losses
        _daily_loss_limit: Daily loss percentage threshold
        _capital_threshold: Low capital threshold
        _reduce_ratio_low_capital: Position ratio for low capital
        _initial_capital: Initial capital for percentage calculations
        _triggered_breakers: List of triggered breaker events

    Example:
        >>> state = ThreadSafeState(initial_capital=200.0)
        >>> breaker = CircuitBreaker(state)
        >>> result = await breaker.check_trading_allowed()
        >>> print(f"Allowed: {result.allowed}, Ratio: {result.position_ratio}")
    """

    def __init__(
        self,
        state: "ThreadSafeState",
        consecutive_losses_limit: int | None = None,
        reduce_ratio_after_losses: float | None = None,
        daily_loss_limit: float | None = None,
        capital_threshold: float | None = None,
        reduce_ratio_low_capital: float | None = None,
        initial_capital: float | None = None,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            state: ThreadSafeState instance to monitor
            consecutive_losses_limit: Override config value (for testing)
            reduce_ratio_after_losses: Override config value (for testing)
            daily_loss_limit: Override config value (for testing)
            capital_threshold: Override config value (for testing)
            reduce_ratio_low_capital: Override config value (for testing)
            initial_capital: Override config value (for testing)
        """
        self._state = state
        self._consecutive_losses_limit = (
            consecutive_losses_limit
            if consecutive_losses_limit is not None
            else settings.risk.consecutive_losses_limit
        )
        self._reduce_ratio_after_losses = (
            reduce_ratio_after_losses
            if reduce_ratio_after_losses is not None
            else settings.risk.reduce_ratio_after_losses
        )
        self._daily_loss_limit = (
            daily_loss_limit
            if daily_loss_limit is not None
            else settings.risk.daily_loss_limit
        )
        self._capital_threshold = (
            capital_threshold
            if capital_threshold is not None
            else settings.risk.capital_threshold
        )
        self._reduce_ratio_low_capital = (
            reduce_ratio_low_capital
            if reduce_ratio_low_capital is not None
            else settings.risk.reduce_ratio_low_capital
        )
        self._initial_capital = (
            initial_capital
            if initial_capital is not None
            else settings.initial_capital
        )
        self._triggered_breakers: list[BreakerTrigger] = []

    async def check_trading_allowed(self) -> CircuitBreakerResult:
        """Check if trading is allowed and get position ratio.

        Runs all circuit breaker checks and returns the result.

        Returns:
            CircuitBreakerResult with allowed status, position ratio, and reasons

        Example:
            >>> result = await breaker.check_trading_allowed()
            >>> if not result.allowed:
            ...     print(f"Trading stopped: {result.reasons}")
        """
        reasons: list[str] = []
        triggers: list[BreakerTrigger] = []
        position_ratio = 1.0
        allowed = True

        # Get current state
        state_snapshot = await self._state.get_state()

        # Check daily loss limit first (most severe)
        daily_loss_trigger = await self._check_daily_loss(state_snapshot)
        if daily_loss_trigger:
            triggers.append(daily_loss_trigger)
            reasons.append(
                f"Daily loss limit exceeded: {abs(state_snapshot.daily_pnl):.2f} / "
                f"{self._initial_capital * self._daily_loss_limit:.2f}"
            )
            allowed = False
            # Daily loss is the most severe, return immediately
            self._triggered_breakers.extend(triggers)
            return CircuitBreakerResult(
                allowed=False,
                position_ratio=0.0,
                reasons=reasons,
                triggers=triggers,
            )

        # Check consecutive losses
        consecutive_trigger = await self._check_consecutive_losses(state_snapshot)
        if consecutive_trigger:
            triggers.append(consecutive_trigger)
            reasons.append(
                f"Consecutive losses exceeded: {state_snapshot.consecutive_losses} / "
                f"{self._consecutive_losses_limit}"
            )
            position_ratio = min(position_ratio, self._reduce_ratio_after_losses)

        # Check capital threshold
        capital_trigger = await self._check_capital_threshold(state_snapshot)
        if capital_trigger:
            triggers.append(capital_trigger)
            reasons.append(
                f"Capital below threshold: ${state_snapshot.current_capital:.2f} < "
                f"${self._capital_threshold:.2f}"
            )
            position_ratio = min(position_ratio, self._reduce_ratio_low_capital)

        # Update state if in reduced mode
        if position_ratio < 1.0 and not state_snapshot.reduced_mode:
            await self._state.set_reduced_mode(True)

        # Log if trading is restricted
        if reasons:
            logger.warning(f"Circuit breaker triggered: {reasons}")

        # Store triggers
        self._triggered_breakers.extend(triggers)

        return CircuitBreakerResult(
            allowed=allowed,
            position_ratio=position_ratio,
            reasons=reasons,
            triggers=triggers,
        )

    async def _check_consecutive_losses(
        self, state_snapshot
    ) -> BreakerTrigger | None:
        """Check consecutive losses breaker.

        Args:
            state_snapshot: Current state snapshot

        Returns:
            BreakerTrigger if triggered, None otherwise
        """
        if state_snapshot.consecutive_losses >= self._consecutive_losses_limit:
            logger.warning(
                f"Consecutive losses breaker triggered: "
                f"{state_snapshot.consecutive_losses} losses"
            )
            return BreakerTrigger(
                trigger_type=BreakerTriggerType.CONSECUTIVE_LOSSES,
                details=f"Consecutive losses: {state_snapshot.consecutive_losses}",
            )
        return None

    async def _check_daily_loss(self, state_snapshot) -> BreakerTrigger | None:
        """Check daily loss limit breaker.

        Args:
            state_snapshot: Current state snapshot

        Returns:
            BreakerTrigger if triggered, None otherwise
        """
        # Only check if there's a loss (negative daily_pnl)
        if state_snapshot.daily_pnl >= 0:
            return None

        loss_ratio = abs(state_snapshot.daily_pnl) / self._initial_capital
        if loss_ratio >= self._daily_loss_limit:
            logger.critical(
                f"Daily loss limit breaker triggered: "
                f"{loss_ratio * 100:.1f}% loss (limit: {self._daily_loss_limit * 100:.1f}%)"
            )
            await self._state.set_trading_enabled(False)
            return BreakerTrigger(
                trigger_type=BreakerTriggerType.DAILY_LOSS_LIMIT,
                details=f"Daily loss: {loss_ratio * 100:.1f}%",
            )
        return None

    async def _check_capital_threshold(
        self, state_snapshot
    ) -> BreakerTrigger | None:
        """Check capital threshold breaker.

        Args:
            state_snapshot: Current state snapshot

        Returns:
            BreakerTrigger if triggered, None otherwise
        """
        if state_snapshot.current_capital < self._capital_threshold:
            logger.warning(
                f"Capital threshold breaker triggered: "
                f"${state_snapshot.current_capital:.2f} < ${self._capital_threshold:.2f}"
            )
            return BreakerTrigger(
                trigger_type=BreakerTriggerType.CAPITAL_THRESHOLD,
                details=f"Capital: ${state_snapshot.current_capital:.2f}",
            )
        return None

    async def get_position_ratio(self) -> float:
        """Get current suggested position ratio.

        This is a convenience method that calls check_trading_allowed()
        and returns only the position ratio.

        Returns:
            float: Suggested position ratio (0-1)

        Example:
            >>> ratio = await breaker.get_position_ratio()
            >>> trade_amount = capital * ratio
        """
        result = await self.check_trading_allowed()
        return result.position_ratio

    async def record_loss(self, amount: float) -> None:
        """Record a loss and update state.

        This method updates the capital and records the trade result.
        The circuit breaker checks will be performed on the next
        check_trading_allowed() call.

        Args:
            amount: Loss amount (positive value)

        Example:
            >>> await breaker.record_loss(10.0)  # Record $10 loss
        """
        await self._state.update_capital(-abs(amount))
        await self._state.record_trade_result(is_win=False)

    def reset(self) -> None:
        """Reset circuit breaker state.

        Clears all triggered breaker records. Does not reset ThreadSafeState.

        Example:
            >>> breaker.reset()
        """
        self._triggered_breakers.clear()
        logger.info("Circuit breaker reset")

    def get_triggered_breakers(self) -> list[BreakerTrigger]:
        """Get list of triggered breakers.

        Returns:
            List of BreakerTrigger records

        Example:
            >>> triggers = breaker.get_triggered_breakers()
            >>> for trigger in triggers:
            ...     print(f"{trigger.trigger_type}: {trigger.details}")
        """
        return list(self._triggered_breakers)
```

### 项目结构 [Source: architecture.md#Project Structure]

**新建文件:**
```
src/core/
├── __init__.py              # 修改: 导出 CircuitBreaker
├── state.py                 # 已有: ThreadSafeState
└── circuit_breaker.py       # 新建: CircuitBreaker 实现

tests/test_core/
├── __init__.py              # 已有
├── test_state.py            # 已有: ThreadSafeState 测试
└── test_circuit_breaker.py  # 新建: CircuitBreaker 测试
```

### 测试策略

```python
# tests/test_core/test_circuit_breaker.py
"""Tests for CircuitBreaker."""

from __future__ import annotations

import pytest

from src.core.circuit_breaker import (
    BreakerTriggerType,
    CircuitBreaker,
    CircuitBreakerResult,
)
from src.core.state import ThreadSafeState


class TestCircuitBreaker:
    """测试 CircuitBreaker."""

    @pytest.fixture
    async def state(self) -> ThreadSafeState:
        """创建测试用状态管理器."""
        return ThreadSafeState(initial_capital=200.0)

    @pytest.fixture
    async def breaker(self, state: ThreadSafeState) -> CircuitBreaker:
        """创建测试用熔断器."""
        return CircuitBreaker(
            state,
            consecutive_losses_limit=3,
            reduce_ratio_after_losses=0.10,
            daily_loss_limit=0.30,
            capital_threshold=100.0,
            reduce_ratio_low_capital=0.10,
            initial_capital=200.0,
        )

    @pytest.mark.asyncio
    async def test_initial_state_no_breaker(
        self, breaker: CircuitBreaker
    ) -> None:
        """测试初始状态无熔断."""
        result = await breaker.check_trading_allowed()
        assert result.allowed is True
        assert result.position_ratio == 1.0
        assert len(result.reasons) == 0

    @pytest.mark.asyncio
    async def test_consecutive_losses_trigger(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """测试连续亏损熔断."""
        # 模拟 3 次亏损
        for _ in range(3):
            await state.record_trade_result(False)

        result = await breaker.check_trading_allowed()
        assert result.allowed is True  # 仍可交易，但降低仓位
        assert result.position_ratio == 0.10
        assert BreakerTriggerType.CONSECUTIVE_LOSSES in [
            t.trigger_type for t in result.triggers
        ]

    @pytest.mark.asyncio
    async def test_daily_loss_limit_trigger(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """测试日亏损熔断."""
        # 模拟日亏损 30%+ ($60+)
        await state.update_capital(-70.0)

        result = await breaker.check_trading_allowed()
        assert result.allowed is False  # 停止交易
        assert result.position_ratio == 0.0
        assert BreakerTriggerType.DAILY_LOSS_LIMIT in [
            t.trigger_type for t in result.triggers
        ]

    @pytest.mark.asyncio
    async def test_capital_threshold_trigger(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """测试资金门槛熔断."""
        # 模拟资金低于 $100
        await state.update_capital(-120.0)

        result = await breaker.check_trading_allowed()
        assert result.allowed is True  # 仍可交易，但降低仓位
        assert result.position_ratio == 0.10
        assert BreakerTriggerType.CAPITAL_THRESHOLD in [
            t.trigger_type for t in result.triggers
        ]

    @pytest.mark.asyncio
    async def test_multiple_breakers_trigger(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """测试多个熔断同时触发."""
        # 模拟连续亏损
        for _ in range(3):
            await state.record_trade_result(False)
        # 模拟资金低于门槛
        await state.update_capital(-120.0)

        result = await breaker.check_trading_allowed()
        assert result.allowed is True  # 仍可交易，但降低仓位
        assert result.position_ratio == 0.10  # 最低比例
        assert len(result.triggers) == 2

    @pytest.mark.asyncio
    async def test_record_loss(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """测试记录亏损."""
        await breaker.record_loss(50.0)
        snapshot = await state.get_state()
        assert snapshot.current_capital == 150.0
        assert snapshot.consecutive_losses == 1

    @pytest.mark.asyncio
    async def test_reset_clears_triggers(
        self, state: ThreadSafeState, breaker: CircuitBreaker
    ) -> None:
        """测试重置清除触发记录."""
        # 触发熔断
        for _ in range(3):
            await state.record_trade_result(False)
        await breaker.check_trading_allowed()

        # 重置
        breaker.reset()
        assert len(breaker.get_triggered_breakers()) == 0

    @pytest.mark.asyncio
    async def test_get_position_ratio(
        self, breaker: CircuitBreaker
    ) -> None:
        """测试获取仓位比例."""
        ratio = await breaker.get_position_ratio()
        assert ratio == 1.0
```

### 依赖关系

**本故事依赖:**
- Story 1.2: 配置管理系统 (已完成 - `settings.risk`)
- Story 4.2: 线程安全状态管理 (已完成 - `ThreadSafeState`)

**后续故事依赖本故事:**
- Story 4.4: 交易前风险检查 (需要 CircuitBreaker 检查交易状态)
- Story 5.2: Paper Trading 执行器 (需要 CircuitBreaker 记录亏损)
- Story 5.3: 交易决策流程 (需要 CircuitBreaker 获取仓位比例)

### 前一个故事学习 [Source: 4-2-thread-safe-state-management.md]

**从 Story 4.2 学到的模式:**

1. **使用 Pydantic v2** - `BaseModel`, `ConfigDict`, `Field`
2. **完整 docstring** - 包含 Args, Returns, Raises, Example
3. **数据类使用 dataclass** - 简单数据结构可用 `@dataclass`
4. **枚举使用 Enum** - `BreakerTriggerType` 继承 `str` 和 `Enum`
5. **`__all__` 导出列表** - 明确模块公共 API
6. **类型注解使用 `|` 联合** - 而非 `Optional`
7. **日志使用 emoji** - `⚠️`, `🔥`, `📊`, `🚦`
8. **异步方法** - 所有涉及状态的方法都是 `async`

### 实现注意事项

**关键点:**

1. **熔断优先级** - 日亏损熔断 > 连续亏损熔断 / 资金门槛熔断
2. **日亏损立即停止** - 日亏损熔断是最严重的，应立即返回
3. **仓位比例取最小** - 多个熔断触发时，取最小的仓位比例
4. **状态同步** - 触发熔断时需同步更新 `ThreadSafeState`
5. **记录保持** - `_triggered_breakers` 保留历史记录供查询

**类型设计:**

```python
# 枚举用于固定值集合
class BreakerTriggerType(str, Enum):
    CONSECUTIVE_LOSSES = "consecutive_losses"
    ...

# 数据类用于简单数据容器
@dataclass
class BreakerTrigger:
    trigger_type: BreakerTriggerType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: str = ""

# 复杂结果使用 dataclass
@dataclass
class CircuitBreakerResult:
    allowed: bool
    position_ratio: float = 1.0
    reasons: list[str] = field(default_factory=list)
    triggers: list[BreakerTrigger] = field(default_factory=list)
```

**日志级别使用:**

| 级别 | 场景 |
|------|------|
| INFO | 正常检查、重置 |
| WARNING | 连续亏损、资金门槛熔断 |
| CRITICAL | 日亏损熔断（停止交易） |

### References

- [Source: architecture.md#Core Dependencies] - 熔断机制位置
- [Source: architecture.md#Project Structure] - src/core/ 目录结构
- [Source: src/config.py#RiskControlSettings] - 熔断配置参数
- [Source: src/core/state.py] - ThreadSafeState 接口
- [Source: epics.md#Story 4.3] - 原始 Story 定义
- [Source: 4-2-thread-safe-state-management.md] - 前一个故事参考

## Dev Agent Record

### Agent Model Used

Claude (GLM-5)

### Debug Log References

N/A

### Completion Notes List

1. **CircuitBreaker Implementation Complete** - Created `src/core/circuit_breaker.py` with full implementation:
   - Three circuit breaker types: consecutive losses, daily loss limit, capital threshold
   - Dataclasses for `BreakerTrigger`, `CircuitBreakerResult`, and enum `BreakerTriggerType`
   - Full async support with proper integration with `ThreadSafeState`
   - Configuration loaded from `settings.risk` with override support for testing

2. **Priority Logic** - Implemented priority-based checking:
   - Daily loss limit check runs first (most severe, stops trading)
   - Consecutive losses and capital threshold checks follow
   - Position ratio takes minimum of all triggered breakers

3. **Test Coverage** - 29 comprehensive tests covering:
   - Initial state (no breaker)
   - Each breaker type trigger and threshold edge cases
   - Multiple breakers triggering together
   - Priority handling (daily loss takes precedence)
   - Recovery/reset logic
   - All public API methods

4. **Code Quality** - All checks pass:
   - mypy type checking: Success
   - black formatting: Passes
   - isort imports: Passes
   - Full test suite: 753 tests pass (including 29 new tests)

### File List

- `src/core/circuit_breaker.py` (new) - CircuitBreaker implementation
- `src/core/__init__.py` (modified) - Added CircuitBreaker exports
- `tests/test_core/test_circuit_breaker.py` (new) - 29 unit tests
