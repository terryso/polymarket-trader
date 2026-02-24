# Story 10.3: 退出条件检查器

Status: done

## Story

As a **用户**,
I want **系统能够自动检查持仓是否满足退出条件**,
So that **在合适的时机自动触发卖出**.

## Acceptance Criteria

1. **Given** 退出策略配置已实现 (Story 10.2)
   **When** 实现 `src/trading/exit_checker.py`
   **Then** 创建 `ExitChecker` 类

2. **`ExitChecker` 类实现:**
   - `check_exit_conditions(position: Position, market: Market) -> ExitCheckResult` - 检查单个持仓是否应该退出
   - `_check_take_profit(position, market)` - 检查止盈条件
   - `_check_stop_loss(position, market)` - 检查止损条件
   - `_check_time_exit(position)` - 检查时间退出条件
   - `_check_signal_exit(position, market)` - 检查信号反转条件
   - `check_all_positions(positions, markets) -> list[ExitCheckResult]` - 批量检查所有持仓

3. **`ExitCheckResult` 数据类包含:**
   - `should_exit: bool` - 是否应该退出
   - `reason: str` - 退出原因 (take_profit, stop_loss, time_exit, signal_exit)
   - `priority: int` - 优先级 (止损=1 > 止盈=2 > 时间=3 > 信号=4)
   - `position_id: int` - 持仓 ID
   - `pnl_pct: float` - 当前 PnL 百分比

4. **退出条件计算:**
   - PnL 百分比: `pnl_pct = (current_value - initial_value) / initial_value`
   - 止盈触发: `pnl_pct >= TAKE_PROFIT_PCT`
   - 止损触发: `pnl_pct <= STOP_LOSS_PCT`
   - 时间退出: `hours_held >= TIME_EXIT_HOURS`

5. **退出优先级 (从高到低):**
   - 止损 (priority=1) - 控制损失优先级最高
   - 止盈 (priority=2) - 锁定利润
   - 时间退出 (priority=3) - 资金周转
   - 信号退出 (priority=4) - 策略调整

6. **日志记录:**
   - 记录检查日志 (包含 emoji 🔍)
   - 记录触发退出时的详细信息

7. **配置集成:**
   - 从 `settings.exit_strategy` 读取配置
   - 支持各项策略的启用/禁用

## Tasks / Subtasks

- [x] Task 1: 创建 ExitCheckResult 数据类 (AC: #3)
  - [x] 1.1 在 `src/trading/exit_checker.py` 创建文件
  - [x] 1.2 定义 `ExitCheckResult` dataclass
  - [x] 1.3 添加字段: should_exit, reason, priority, position_id, pnl_pct
  - [x] 1.4 添加 `ExitReason` 枚举定义

- [x] Task 2: 实现 ExitChecker 类基础结构 (AC: #1, #2)
  - [x] 2.1 创建 `ExitChecker` 类
  - [x] 2.2 添加构造函数接收 `ExitStrategySettings` 配置
  - [x] 2.3 添加 logger 初始化
  - [x] 2.4 实现 `check_exit_conditions` 主方法签名

- [x] Task 3: 实现止盈检查方法 (AC: #2, #4)
  - [x] 3.1 实现 `_check_take_profit` 方法
  - [x] 3.2 计算 PnL 百分比
  - [x] 3.3 检查是否达到止盈阈值
  - [x] 3.4 返回 ExitCheckResult

- [x] Task 4: 实现止损检查方法 (AC: #2, #4)
  - [x] 4.1 实现 `_check_stop_loss` 方法
  - [x] 4.2 检查是否达到止损阈值
  - [x] 4.3 返回 ExitCheckResult

- [x] Task 5: 实现时间退出检查方法 (AC: #2, #4)
  - [x] 5.1 实现 `_check_time_exit` 方法
  - [x] 5.2 计算持仓时间 (小时)
  - [x] 5.3 检查是否超过配置的时间阈值
  - [x] 5.4 返回 ExitCheckResult

- [x] Task 6: 实现信号反转检查方法 (AC: #2)
  - [x] 6.1 实现 `_check_signal_exit` 方法
  - [x] 6.2 获取最新 LLM 预测结果
  - [x] 6.3 比较预测方向与持仓方向
  - [x] 6.4 返回 ExitCheckResult

- [x] Task 7: 实现主检查方法 (AC: #2, #5, #6)
  - [x] 7.1 实现 `check_exit_conditions` 完整逻辑
  - [x] 7.2 按优先级顺序调用各检查方法
  - [x] 7.3 返回最高优先级的退出信号
  - [x] 7.4 添加日志记录 (包含 🔍 emoji)

- [x] Task 8: 实现批量检查方法 (AC: #2)
  - [x] 8.1 实现 `check_all_positions` 方法
  - [x] 8.2 并行或顺序检查多个持仓
  - [x] 8.3 返回所有需要退出的持仓列表
  - [x] 8.4 记录批量检查统计日志

- [x] Task 9: 添加单元测试 (AC: All)
  - [x] 9.1 测试 ExitCheckResult 数据类
  - [x] 9.2 测试止盈检查 (触发和未触发)
  - [x] 9.3 测试止损检查 (触发和未触发)
  - [x] 9.4 测试时间退出检查 (触发和未触发)
  - [x] 9.5 测试信号反转检查
  - [x] 9.6 测试优先级排序
  - [x] 9.7 测试批量检查
  - [x] 9.8 测试配置禁用时跳过检查

## Dev Notes

### 依赖关系

**前置依赖:**
- Story 10.2: 退出策略配置 - `ExitStrategySettings` 已实现

**后续依赖:**
- Story 10.4: 退出策略调度 - 使用 `ExitChecker` 定期检查

### 现有配置结构

**ExitStrategySettings (src/config.py):**
```python
class ExitStrategySettings(BaseEnvSettings):
    take_profit_enabled: bool = True
    take_profit_pct: float = 0.50  # 50% 盈利
    stop_loss_enabled: bool = True
    stop_loss_pct: float = -0.30  # 30% 亏损
    time_exit_enabled: bool = False
    time_exit_hours: int = 72
    signal_exit_enabled: bool = True
    exit_check_interval_minutes: int = 5
```

### 数据模型

**Position (src/models/position.py):**
```python
class Position(BaseModel):
    id: int
    market_id: str
    outcome: PositionOutcome  # YES or NO
    shares: float
    avg_price: float
    initial_value: float | None
    current_value: float | None
    pnl: float | None
    status: PositionStatus
    opened_at: datetime | None
    closed_at: datetime | None
```

**Market (src/models/market.py):**
```python
class Market(BaseModel):
    id: str
    title: str
    yes_price: float | None
    no_price: float | None
    # ...
```

### 退出条件检查实现参考

```python
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timezone
from typing import Any

from src.config import settings, ExitStrategySettings
from src.models.position import Position, PositionOutcome
from src.models.market import Market
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ExitReason(str, Enum):
    """退出原因枚举"""
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TIME_EXIT = "time_exit"
    SIGNAL_EXIT = "signal_exit"


@dataclass
class ExitCheckResult:
    """退出检查结果"""
    should_exit: bool
    reason: str
    priority: int
    position_id: int
    pnl_pct: float | None = None

    # 优先级常量
    PRIORITY_STOP_LOSS = 1
    PRIORITY_TAKE_PROFIT = 2
    PRIORITY_TIME_EXIT = 3
    PRIORITY_SIGNAL_EXIT = 4


class ExitChecker:
    """检查持仓是否满足退出条件"""

    def __init__(self, config: ExitStrategySettings | None = None):
        self.config = config or settings.exit_strategy
        self.logger = get_logger(__name__)

    async def check_exit_conditions(
        self,
        position: Position,
        market: Market,
        latest_prediction: Any | None = None,
    ) -> ExitCheckResult:
        """检查单个持仓是否应该退出"""
        results = []

        # 按优先级顺序检查 (止损优先级最高)
        if self.config.stop_loss_enabled:
            result = self._check_stop_loss(position)
            if result.should_exit:
                return result

        if self.config.take_profit_enabled:
            result = self._check_take_profit(position)
            if result.should_exit:
                return result

        if self.config.time_exit_enabled:
            result = self._check_time_exit(position)
            if result.should_exit:
                return result

        if self.config.signal_exit_enabled and latest_prediction:
            result = self._check_signal_exit(position, latest_prediction)
            if result.should_exit:
                return result

        # 无退出条件触发
        return ExitCheckResult(
            should_exit=False,
            reason="",
            priority=0,
            position_id=position.id,
            pnl_pct=self._calculate_pnl_pct(position),
        )

    def _calculate_pnl_pct(self, position: Position) -> float | None:
        """计算 PnL 百分比"""
        if position.initial_value is None or position.initial_value == 0:
            return None
        if position.current_value is None:
            return None
        return (position.current_value - position.initial_value) / position.initial_value

    def _check_take_profit(self, position: Position) -> ExitCheckResult:
        """检查止盈条件"""
        pnl_pct = self._calculate_pnl_pct(position)
        if pnl_pct is None:
            return self._no_exit(position, pnl_pct)

        if pnl_pct >= self.config.take_profit_pct:
            self.logger.info(
                f"🔍 止盈触发: position_id={position.id}, "
                f"pnl_pct={pnl_pct:.2%}, threshold={self.config.take_profit_pct:.2%}"
            )
            return ExitCheckResult(
                should_exit=True,
                reason=ExitReason.TAKE_PROFIT.value,
                priority=ExitCheckResult.PRIORITY_TAKE_PROFIT,
                position_id=position.id,
                pnl_pct=pnl_pct,
            )

        return self._no_exit(position, pnl_pct)

    def _check_stop_loss(self, position: Position) -> ExitCheckResult:
        """检查止损条件"""
        pnl_pct = self._calculate_pnl_pct(position)
        if pnl_pct is None:
            return self._no_exit(position, pnl_pct)

        if pnl_pct <= self.config.stop_loss_pct:
            self.logger.info(
                f"🔍 止损触发: position_id={position.id}, "
                f"pnl_pct={pnl_pct:.2%}, threshold={self.config.stop_loss_pct:.2%}"
            )
            return ExitCheckResult(
                should_exit=True,
                reason=ExitReason.STOP_LOSS.value,
                priority=ExitCheckResult.PRIORITY_STOP_LOSS,
                position_id=position.id,
                pnl_pct=pnl_pct,
            )

        return self._no_exit(position, pnl_pct)

    def _check_time_exit(self, position: Position) -> ExitCheckResult:
        """检查时间退出条件"""
        if position.opened_at is None:
            return self._no_exit(position, None)

        hours_held = (datetime.now(timezone.utc) - position.opened_at).total_seconds() / 3600

        if hours_held >= self.config.time_exit_hours:
            self.logger.info(
                f"🔍 时间退出触发: position_id={position.id}, "
                f"hours_held={hours_held:.1f}h, threshold={self.config.time_exit_hours}h"
            )
            return ExitCheckResult(
                should_exit=True,
                reason=ExitReason.TIME_EXIT.value,
                priority=ExitCheckResult.PRIORITY_TIME_EXIT,
                position_id=position.id,
                pnl_pct=self._calculate_pnl_pct(position),
            )

        return self._no_exit(position, self._calculate_pnl_pct(position))

    def _check_signal_exit(
        self, position: Position, latest_prediction: Any
    ) -> ExitCheckResult:
        """检查信号反转条件"""
        # 需要比较 LLM 预测方向与持仓方向
        # 如果 LLM 建议相反方向，则触发信号退出
        # 具体实现需要根据 Prediction 模型结构
        return self._no_exit(position, self._calculate_pnl_pct(position))

    def _no_exit(self, position: Position, pnl_pct: float | None) -> ExitCheckResult:
        """返回不退出的结果"""
        return ExitCheckResult(
            should_exit=False,
            reason="",
            priority=0,
            position_id=position.id,
            pnl_pct=pnl_pct,
        )

    async def check_all_positions(
        self,
        positions: list[Position],
        markets: dict[str, Market],
    ) -> list[ExitCheckResult]:
        """批量检查所有持仓"""
        results = []
        exit_count = 0

        for position in positions:
            if position.status != PositionStatus.OPEN:
                continue

            market = markets.get(position.market_id)
            if market is None:
                self.logger.warning(f"🔍 持仓 {position.id} 的市场 {position.market_id} 不存在")
                continue

            result = await self.check_exit_conditions(position, market)
            results.append(result)

            if result.should_exit:
                exit_count += 1

        self.logger.info(
            f"🔍 批量检查完成: 检查 {len(positions)} 个持仓, "
            f"{exit_count} 个触发退出"
        )

        return results
```

### 信号反转检查逻辑

信号反转检查需要对比:
1. 当前持仓方向 (PositionOutcome.YES 或 NO)
2. 最新 LLM 预测建议 (Prediction.recommended_outcome)

如果两者不一致，则触发信号退出。

### 测试策略

1. **单元测试**: Mock Position 和 Market 对象，测试各种退出条件
2. **边界测试**: PnL 刚好等于阈值、持仓时间刚好等于配置时间
3. **配置测试**: 验证各策略启用/禁用时行为正确
4. **优先级测试**: 验证多个条件同时满足时返回最高优先级

### Project Structure Notes

- 新建文件 `src/trading/exit_checker.py`
- 测试文件 `tests/test_trading/test_exit_checker.py`
- 遵循现有 `src/trading/` 目录结构

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 10.3] - Story 需求
- [Source: _bmad-output/implementation-artifacts/10-2-exit-strategy-config.md] - 配置实现
- [Source: src/config.py] - ExitStrategySettings 配置类
- [Source: src/models/position.py] - Position 模型
- [Source: src/models/market.py] - Market 模型
- [Source: src/trading/position_manager.py] - 持仓管理参考

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (GLM-5)

### Debug Log References

N/A

### Completion Notes List

- 实现了 `ExitChecker` 类，包含所有 AC 中要求的检查方法
- 实现了 `ExitCheckResult` 数据类和 `ExitReason` 枚举
- 所有 37 个单元测试通过
- 退出优先级按 AC 要求实现：止损(1) > 止盈(2) > 时间退出(3) > 信号退出(4)
- 支持配置各项策略的启用/禁用
- 日志记录包含 🔍 emoji

### File List

- `src/trading/exit_checker.py` - 新建退出条件检查器
- `tests/test_trading/test_exit_checker.py` - 新建测试文件
- `tests/conftest.py` - 添加 ExitStrategySettings 相关环境变量到清除列表

### Change Log

- 2026-02-25: Story 10.3 用户故事创建
- 2026-02-25: Story 10.3 实现完成，所有测试通过
