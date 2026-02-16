# Story 5.4: 模拟持仓 PnL 计算

Status: done

## Story

As a **用户**,
I want **系统能够计算模拟持仓的实时盈亏**,
So that **我能够评估策略表现**.

## Acceptance Criteria

**Given** Paper Trading 已实现 (Story 5.2, Story 5.3)
**When** 实现持仓 PnL 计算功能
**Then** 在 `position_manager.py` 添加:
- `calculate_pnl(position, current_price: float)` - 计算单个持仓 PnL
- `calculate_total_pnl()` - 计算总 PnL
- `update_all_positions_value(market_prices: dict[str, float])` - 批量更新持仓价值

**And** PnL 计算公式:
- `pnl = shares * (current_price - avg_price)` (BUY_YES)
- `pnl = shares * (current_price - avg_price)` (BUY_NO)
- `pnl_pct = pnl / initial_value`

注: YES 和 NO 持仓使用相同公式，因为持仓直接代表对应结果的份额

**And** 更新 Position 表的 `current_value`, `pnl` 字段
**And** 记录 PnL 变化日志

## Tasks / Subtasks

- [x] Task 1: 扩展 PositionManager 添加 PnL 计算方法 (AC: 1, 2)
  - [x] 1.1 在 `src/trading/position_manager.py` 添加 `calculate_pnl` 方法
  - [x] 1.2 实现 BUY_YES 持仓 PnL 计算: `pnl = shares * (current_price - avg_price)`
  - [x] 1.3 实现 BUY_NO 持仓 PnL 计算: `pnl = shares * (current_price - avg_price)`
  - [x] 1.4 计算 PnL 百分比: `pnl_pct = pnl / initial_value`
  - [x] 1.5 处理 initial_value 为 None 的边界情况
  - [x] 1.6 返回包含 pnl, pnl_pct 的数据类 `PnLResult`

- [x] Task 2: 实现 calculate_total_pnl 方法 (AC: 1)
  - [x] 2.1 添加 `calculate_total_pnl()` 方法到 PositionManager
  - [x] 2.2 获取所有开放持仓
  - [x] 2.3 遍历每个持仓计算其 PnL
  - [x] 2.4 汇总所有持仓的 PnL
  - [x] 2.5 记录总 PnL 日志
  - [x] 2.6 返回 `TotalPnLResult` 数据类

- [x] Task 3: 实现批量更新持仓价值功能 (AC: 3)
  - [x] 3.1 添加 `update_all_positions_value(market_prices: dict[str, float])` 方法
  - [x] 3.2 遍历所有开放持仓
  - [x] 3.3 从 market_prices 字典获取当前价格
  - [x] 3.4 调用 `update_position_value` 更新每个持仓
  - [x] 3.5 记录批量更新日志
  - [x] 3.6 返回更新后的持仓列表

- [x] Task 4: 创建 PnL 结果数据类 (AC: All)
  - [x] 4.1 创建 `PnLResult` 数据类
    - `pnl: float` - 绝对盈亏
    - `pnl_pct: float` - 盈亏百分比
    - `current_value: float` - 当前市值
  - [x] 4.2 创建 `TotalPnLResult` 数据类
    - `total_pnl: float` - 总盈亏
    - `positions_count: int` - 持仓数量
    - `winning_count: int` - 盈利持仓数
    - `losing_count: int` - 亏损持仓数

- [x] Task 5: 更新模块导出 (AC: All)
  - [x] 5.1 更新 `src/trading/__init__.py` 导出 `PnLResult`, `TotalPnLResult`
  - [x] 5.2 更新 `__all__` 列表

- [x] Task 6: 编写单元测试 (AC: All)
  - [x] 6.1 创建/更新 `tests/test_trading/test_position_manager.py`
  - [x] 6.2 测试 BUY_YES 持仓 PnL 计算 (盈利场景)
  - [x] 6.3 测试 BUY_YES 持仓 PnL 计算 (亏损场景)
  - [x] 6.4 测试 BUY_NO 持仓 PnL 计算 (盈利场景)
  - [x] 6.5 测试 BUY_NO 持仓 PnL 计算 (亏损场景)
  - [x] 6.6 测试 PnL 百分比计算
  - [x] 6.7 测试 initial_value 为 None 的边界情况
  - [x] 6.8 测试 calculate_total_pnl 方法
  - [x] 6.9 测试 update_all_positions_value 方法
  - [x] 6.10 Mock 所有外部依赖

- [x] Task 7: 代码质量检查 (AC: All)
  - [x] 7.1 运行 `mypy src/trading/position_manager.py` 无错误
  - [x] 7.2 运行 `black --check` 通过
  - [x] 7.3 运行 `isort --check` 通过
  - [x] 7.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md]

**PnL 计算设计原则:**
- BUY_YES 持仓: 价格上涨盈利，价格下跌亏损
- BUY_NO 持仓: 价格下跌盈利，价格上涨亏损
- 百分比基于初始投资计算
- 实时更新，支持 Dashboard 展示

### 已有组件 (必须复用)

**PositionManager** [Source: src/trading/position_manager.py]
```python
class PositionManager:
    async def get_open_positions(self) -> list[Position]: ...
    async def update_position_value(
        self, position_id: int, current_price: float
    ) -> Position: ...
    async def get_total_exposure(self) -> float: ...
```

**Position** [Source: src/models/position.py]
```python
class PositionOutcome(str, Enum):
    YES = "YES"
    NO = "NO"

class Position(BaseModel):
    id: int
    market_id: str
    outcome: PositionOutcome
    shares: float
    avg_price: float
    initial_value: float | None
    current_value: float | None
    pnl: float | None
    status: PositionStatus
```

**Market** [Source: src/models/market.py]
```python
class Market(BaseModel):
    id: str
    title: str
    yes_price: float | None
    no_price: float | None
```

### PnL 计算逻辑

```
┌─────────────────────────────────────────────────────────────────────┐
│                     PnL 计算逻辑                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  calculate_pnl(position, current_price) -> PnLResult                │
│                                                                     │
│  1. 确定持仓方向                                                     │
│     if position.outcome == YES:                                     │
│         # BUY_YES: 买入 YES 份额，价格上涨盈利                       │
│         pnl = shares * (current_price - avg_price)                 │
│     else:  # NO                                                     │
│         # BUY_NO: 买入 NO 份额，价格下跌盈利                         │
│         # NO 价格 = 1 - YES 价格                                    │
│         pnl = shares * (avg_price - current_price)                 │
│                                                                     │
│  2. 计算当前市值                                                     │
│     current_value = shares * current_price                         │
│                                                                     │
│  3. 计算 PnL 百分比                                                  │
│     if initial_value > 0:                                           │
│         pnl_pct = pnl / initial_value                              │
│     else:                                                           │
│         pnl_pct = 0.0                                               │
│                                                                     │
│  4. 返回结果                                                        │
│     return PnLResult(                                              │
│         pnl=pnl,                                                   │
│         pnl_pct=pnl_pct,                                           │
│         current_value=current_value                                │
│     )                                                              │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  calculate_total_pnl() -> TotalPnLResult                            │
│                                                                     │
│  1. 获取所有开放持仓                                                 │
│     positions = await get_open_positions()                         │
│                                                                     │
│  2. 计算每个持仓的 PnL                                               │
│     total_pnl = 0.0                                                 │
│     winning_count = 0                                               │
│     losing_count = 0                                                │
│                                                                     │
│     for position in positions:                                      │
│         pnl_result = calculate_pnl(position, current_price)        │
│         total_pnl += pnl_result.pnl                                │
│         if pnl_result.pnl > 0:                                      │
│             winning_count += 1                                      │
│         elif pnl_result.pnl < 0:                                    │
│             losing_count += 1                                       │
│                                                                     │
│  3. 返回结果                                                        │
│     return TotalPnLResult(                                         │
│         total_pnl=total_pnl,                                       │
│         positions_count=len(positions),                            │
│         winning_count=winning_count,                               │
│         losing_count=losing_count                                  │
│     )                                                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### PnL 计算示例

**BUY_YES 场景 (价格上涨盈利):**
```
买入: 100 shares YES @ $0.45 = $45 initial_value
当前: YES 价格 = $0.55

pnl = 100 * (0.55 - 0.45) = $10.00
pnl_pct = 10.00 / 45.00 = 22.22%
current_value = 100 * 0.55 = $55.00
```

**BUY_YES 场景 (价格下跌亏损):**
```
买入: 100 shares YES @ $0.45 = $45 initial_value
当前: YES 价格 = $0.35

pnl = 100 * (0.35 - 0.45) = -$10.00
pnl_pct = -10.00 / 45.00 = -22.22%
current_value = 100 * 0.35 = $35.00
```

**BUY_NO 场景 (价格下跌盈利):**
```
买入: 100 shares NO @ $0.55 = $55 initial_value
当前: NO 价格 = $0.65 (YES 价格下跌)

注意: BUY_NO 时 avg_price 是 NO 价格
pnl = 100 * (0.55 - 0.65) = -$10.00
实际: NO 价格上涨意味着 YES 价格下跌，但公式需要对调

修正: BUY_NO 的 PnL 计算:
  - 买入时的 NO 价格为 avg_price (0.55)
  - 当前 NO 价格为 current_price (0.65)
  - NO 价格上涨 = YES 价格下跌 = 对 BUY_NO 有利
  - pnl = shares * (current_price - avg_price) = 100 * (0.65 - 0.55) = $10.00
```

### 实现模板

**src/trading/position_manager.py (扩展):**

```python
# 在现有文件中添加以下内容

from dataclasses import dataclass


@dataclass
class PnLResult:
    """Result of PnL calculation for a single position.

    Attributes:
        pnl: Absolute profit/loss in USD
        pnl_pct: Profit/loss percentage (0-1 range)
        current_value: Current market value in USD
    """

    pnl: float
    pnl_pct: float
    current_value: float


@dataclass
class TotalPnLResult:
    """Result of total PnL calculation across all positions.

    Attributes:
        total_pnl: Total profit/loss across all positions
        positions_count: Number of positions included
        winning_count: Number of profitable positions
        losing_count: Number of losing positions
    """

    total_pnl: float
    positions_count: int
    winning_count: int
    losing_count: int


class PositionManager:
    # ... 现有代码 ...

    def calculate_pnl(
        self, position: Position, current_price: float
    ) -> PnLResult:
        """Calculate PnL for a single position.

        PnL calculation differs based on position outcome:
        - YES: pnl = shares * (current_price - avg_price)
        - NO: pnl = shares * (current_price - avg_price)
              (NO price increases when YES price decreases)

        Args:
            position: Position to calculate PnL for
            current_price: Current market price for the outcome

        Returns:
            PnLResult with pnl, pnl_pct, and current_value

        Example:
            >>> result = manager.calculate_pnl(position, 0.55)
            >>> print(f"PnL: ${result.pnl:.2f} ({result.pnl_pct:.2%})")
        """
        # Calculate current value
        current_value = position.shares * current_price

        # Calculate PnL based on outcome
        # For both YES and NO, we use the same formula since we're
        # buying the outcome directly (YES shares or NO shares)
        pnl = position.shares * (current_price - position.avg_price)

        # Calculate PnL percentage
        initial_value = position.initial_value or 0
        if initial_value > 0:
            pnl_pct = pnl / initial_value
        else:
            pnl_pct = 0.0

        self._logger.debug(
            f"📊 PnL calculated for position {position.id}: "
            f"pnl=${pnl:.2f}, pnl_pct={pnl_pct:.2%}, "
            f"current_value=${current_value:.2f}"
        )

        return PnLResult(
            pnl=pnl,
            pnl_pct=pnl_pct,
            current_value=current_value,
        )

    async def calculate_total_pnl(self) -> TotalPnLResult:
        """Calculate total PnL across all open positions.

        Note: This method uses the current_value stored in each position,
        which should be updated via update_all_positions_value first.

        Returns:
            TotalPnLResult with aggregated PnL statistics

        Example:
            >>> result = await manager.calculate_total_pnl()
            >>> print(f"Total PnL: ${result.total_pnl:.2f}")
        """
        positions = await self.get_open_positions()

        total_pnl = 0.0
        winning_count = 0
        losing_count = 0

        for position in positions:
            pnl = position.pnl or 0
            total_pnl += pnl

            if pnl > 0:
                winning_count += 1
            elif pnl < 0:
                losing_count += 1

        self._logger.info(
            f"📊 Total PnL: ${total_pnl:.2f} "
            f"({winning_count} winning, {losing_count} losing, "
            f"{len(positions)} total)"
        )

        return TotalPnLResult(
            total_pnl=total_pnl,
            positions_count=len(positions),
            winning_count=winning_count,
            losing_count=losing_count,
        )

    async def update_all_positions_value(
        self, market_prices: dict[str, float]
    ) -> list[Position]:
        """Update current value and PnL for all open positions.

        Args:
            market_prices: Dictionary mapping market_id to current price
                          for the outcome held (YES price for YES positions,
                          NO price for NO positions)

        Returns:
            List of updated positions

        Example:
            >>> prices = {"market-1": 0.55, "market-2": 0.40}
            >>> updated = await manager.update_all_positions_value(prices)
            >>> print(f"Updated {len(updated)} positions")
        """
        positions = await self.get_open_positions()
        updated_positions: list[Position] = []

        for position in positions:
            current_price = market_prices.get(position.market_id)

            if current_price is None:
                self._logger.warning(
                    f"⚠️ No price available for market {position.market_id}, "
                    f"skipping position {position.id}"
                )
                continue

            try:
                updated = await self.update_position_value(
                    position.id, current_price
                )
                updated_positions.append(updated)
            except (ValidationError, TradingError) as e:
                self._logger.error(
                    f"❌ Failed to update position {position.id}: {e}"
                )

        self._logger.info(
            f"📊 Updated {len(updated_positions)}/{len(positions)} positions"
        )

        return updated_positions
```

### 项目结构 [Source: architecture.md#Project Structure]

**修改文件:**
```
src/
└── trading/
    ├── __init__.py              # 修改: 导出 PnLResult, TotalPnLResult
    └── position_manager.py      # 修改: 添加 PnL 计算方法

tests/
└── test_trading/
    └── test_position_manager.py # 修改: 添加 PnL 计算测试
```

### 依赖关系

**本故事依赖:**
- Story 4.5: 持仓管理 (已完成 - `PositionManager`, `Position`)
- Story 5.2: Paper Trading 执行器 (已完成 - 创建持仓)
- Story 5.3: 交易决策流程 (已完成 - 交易执行)

**后续故事依赖本故事:**
- Story 5.5: 统计数据记录 (需要 PnL 计算功能)
- Story 7.4: 预测与统计 API (需要展示 PnL 数据)
- Story 8.2: 定时任务配置 (需要定期更新 PnL)

### 前一个故事学习 [Source: 5-3-trading-decision-flow.md]

**从 Story 5.3 学到的模式:**

1. **数据类返回结果** - 使用 `@dataclass` 定义返回类型 (TradingDecision)
2. **依赖注入** - 所有依赖通过构造函数注入
3. **错误隔离** - 返回结果包含 `success` 和 `error_message`
4. **日志标准化** - 使用 emoji 标记不同类型的日志
5. **类型注解** - 使用 `TYPE_CHECKING` 避免循环导入
6. **`__all__` 导出** - 明确模块公共 API
7. **批量处理** - 支持单个和批量操作

### 实现注意事项

**关键点:**

1. **PnL 公式一致性** - YES 和 NO 都使用 `shares * (current_price - avg_price)`
   - 因为持仓直接代表 YES 或 NO 份额，价格变动方向就是盈亏方向
2. **百分比计算** - 基于 initial_value，处理除零情况
3. **价格获取** - 需要从外部传入当前价格（通过 market_prices 字典）
4. **批量更新** - 支持一次性更新所有持仓

**错误处理:**

| 场景 | 处理方式 |
|------|----------|
| initial_value 为 None | pnl_pct = 0.0 |
| 找不到市场价格 | 跳过该持仓，记录警告日志 |
| 更新失败 | 记录错误日志，继续处理其他持仓 |

**日志级别:**

| 级别 | 场景 | Emoji |
|------|------|-------|
| INFO | 总 PnL 计算、批量更新完成 | 📊 |
| DEBUG | 单个持仓 PnL 计算 | 📊 |
| WARNING | 缺少市场价格 | ⚠️ |
| ERROR | 更新失败 | ❌ |

### 测试策略

```python
# tests/test_trading/test_position_manager.py
"""Tests for PositionManager PnL calculations."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.models.position import Position, PositionOutcome, PositionStatus
from src.trading.position_manager import (
    PositionManager,
    PnLResult,
    TotalPnLResult,
)


class TestPnLCalculations:
    """测试 PnL 计算功能."""

    @pytest.fixture
    def manager(self) -> PositionManager:
        """创建测试用持仓管理器."""
        repo = AsyncMock()
        state = AsyncMock()
        return PositionManager(repo, state)

    def test_calculate_pnl_buy_yes_profit(
        self, manager: PositionManager
    ) -> None:
        """测试 BUY_YES 持仓盈利场景."""
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=45.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
        )

        result = manager.calculate_pnl(position, current_price=0.55)

        assert result.pnl == pytest.approx(10.0)  # 100 * (0.55 - 0.45)
        assert result.pnl_pct == pytest.approx(10.0 / 45.0)
        assert result.current_value == pytest.approx(55.0)

    def test_calculate_pnl_buy_yes_loss(
        self, manager: PositionManager
    ) -> None:
        """测试 BUY_YES 持仓亏损场景."""
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=45.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
        )

        result = manager.calculate_pnl(position, current_price=0.35)

        assert result.pnl == pytest.approx(-10.0)  # 100 * (0.35 - 0.45)
        assert result.pnl_pct == pytest.approx(-10.0 / 45.0)
        assert result.current_value == pytest.approx(35.0)

    def test_calculate_pnl_buy_no_profit(
        self, manager: PositionManager
    ) -> None:
        """测试 BUY_NO 持仓盈利场景 (NO 价格上涨)."""
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.NO,
            shares=100.0,
            avg_price=0.55,
            initial_value=55.0,
            current_value=55.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
        )

        # NO 价格从 0.55 上涨到 0.65 = 盈利
        result = manager.calculate_pnl(position, current_price=0.65)

        assert result.pnl == pytest.approx(10.0)  # 100 * (0.65 - 0.55)
        assert result.pnl_pct == pytest.approx(10.0 / 55.0, rel=0.01)
        assert result.current_value == pytest.approx(65.0)

    def test_calculate_pnl_zero_initial_value(
        self, manager: PositionManager
    ) -> None:
        """测试 initial_value 为 0 的边界情况."""
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=None,  # None case
            current_value=None,
            pnl=None,
            status=PositionStatus.OPEN,
        )

        result = manager.calculate_pnl(position, current_price=0.55)

        assert result.pnl == pytest.approx(10.0)
        assert result.pnl_pct == 0.0  # Safe default

    @pytest.mark.asyncio
    async def test_calculate_total_pnl(
        self, manager: PositionManager
    ) -> None:
        """测试总 PnL 计算."""
        # Setup mock
        manager._repo.get_open_positions.return_value = [
            Position(
                id=1,
                market_id="m1",
                outcome=PositionOutcome.YES,
                shares=100.0,
                avg_price=0.45,
                initial_value=45.0,
                current_value=55.0,
                pnl=10.0,
                status=PositionStatus.OPEN,
            ),
            Position(
                id=2,
                market_id="m2",
                outcome=PositionOutcome.NO,
                shares=50.0,
                avg_price=0.60,
                initial_value=30.0,
                current_value=25.0,
                pnl=-5.0,
                status=PositionStatus.OPEN,
            ),
        ]

        result = await manager.calculate_total_pnl()

        assert result.total_pnl == pytest.approx(5.0)  # 10 - 5
        assert result.positions_count == 2
        assert result.winning_count == 1
        assert result.losing_count == 1

    @pytest.mark.asyncio
    async def test_update_all_positions_value(
        self, manager: PositionManager
    ) -> None:
        """测试批量更新持仓价值."""
        positions = [
            Position(
                id=1,
                market_id="m1",
                outcome=PositionOutcome.YES,
                shares=100.0,
                avg_price=0.45,
                initial_value=45.0,
                current_value=45.0,
                pnl=0.0,
                status=PositionStatus.OPEN,
            ),
            Position(
                id=2,
                market_id="m2",
                outcome=PositionOutcome.NO,
                shares=50.0,
                avg_price=0.60,
                initial_value=30.0,
                current_value=30.0,
                pnl=0.0,
                status=PositionStatus.OPEN,
            ),
        ]

        manager._repo.get_open_positions.return_value = positions
        manager._repo.get_by_id.return_value = positions[0]
        manager._repo.update.return_value = positions[0]

        market_prices = {"m1": 0.55, "m2": 0.50}

        # First call returns position, subsequent calls update
        async def mock_get_by_id(pos_id: int) -> Position | None:
            for p in positions:
                if p.id == pos_id:
                    return p
            return None

        manager._repo.get_by_id.side_effect = mock_get_by_id
        manager._repo.update.side_effect = lambda p: p

        updated = await manager.update_all_positions_value(market_prices)

        assert len(updated) == 2
```

### References

- [Source: architecture.md#Database Schema] - positions 表定义
- [Source: architecture.md#Project Structure] - src/trading/ 目录结构
- [Source: epics.md#Story 5.4] - 原始 Story 定义
- [Source: src/trading/position_manager.py] - PositionManager 现有实现
- [Source: src/models/position.py] - Position 模型定义
- [Source: src/models/market.py] - Market 模型定义
- [Source: 5-3-trading-decision-flow.md] - 前一个故事实现参考
- [Source: 5-2-paper-trading-executor.md] - Paper Trading 实现参考
- [Source: 4-5-position-management.md] - PositionManager 基础实现

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None

### Completion Notes List

1. **实现完成** - PositionManager 已扩展 PnL 计算功能:
   - 添加 `PnLResult` 数据类用于单个持仓 PnL 结果
   - 添加 `TotalPnLResult` 数据类用于总 PnL 结果
   - 实现 `calculate_pnl(position, current_price)` 方法
   - 实现 `calculate_total_pnl()` 异步方法
   - 实现 `update_all_positions_value(market_prices)` 批量更新方法

2. **PnL 计算公式**:
   - 对于 YES 和 NO 持仓: `pnl = shares * (current_price - avg_price)`
   - PnL 百分比: `pnl_pct = pnl / initial_value`
   - 处理 initial_value 为 None 或 0 的边界情况

3. **测试覆盖** - 17 个新增 PnL 计算测试全部通过:
   - BUY_YES 盈利/亏损场景
   - BUY_NO 盈利/亏损场景
   - initial_value 为 None/0 的边界情况
   - calculate_total_pnl 方法测试
   - update_all_positions_value 方法测试
   - PnLResult 和 TotalPnLResult 数据类测试

4. **代码质量** - 所有检查通过:
   - mypy: 无类型错误
   - black: 格式化通过
   - isort: import 排序通过
   - 完整测试套件: 923 个测试全部通过

### File List

- src/trading/position_manager.py (修改 - 添加 PnLResult, TotalPnLResult, calculate_pnl, calculate_total_pnl, update_all_positions_value)
- src/trading/__init__.py (修改 - 导出 PnLResult, TotalPnLResult)
- tests/test_trading/test_position_manager.py (修改 - 添加 17 个 PnL 计算测试)
