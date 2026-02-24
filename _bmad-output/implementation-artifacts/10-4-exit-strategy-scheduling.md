# Story 10.4: 退出策略调度

Status: review

## Story

As a **用户**,
I want **系统能够定期自动检查并执行退出策略**,
So that **退出策略完全自动化运行**.

## Acceptance Criteria

1. **Given** 退出条件检查器已实现 (Story 10.3)
   **When** 在 `src/core/scheduler.py` 添加退出检查任务
   **Then** 添加定时任务 `check_exit_strategies`

2. **定时任务 `check_exit_strategies` 实现:**
   - 频率: 每 5 分钟 (可配置, 通过 `EXIT_CHECK_INTERVAL_MINUTES` 环境变量)
   - 任务流程:
     ```python
     async def check_exit_strategies():
         # 1. 获取所有未平仓位
         positions = await position_manager.get_open_positions()

         # 2. 对每个持仓检查退出条件
         for position in positions:
             market = await market_repo.get_market(position.market_id)

             # 检查退出条件
             result = await exit_checker.check_exit_conditions(position, market)

             if result.should_exit:
                 # 执行卖出
                 await live_executor.sell_position(
                     position=position,
                     market=market,
                     reason=result.reason
                 )
     ```

3. **任务失败处理:**
   - 单个持仓退出失败不影响其他持仓
   - 记录失败日志并重试 (最多 3 次)
   - 连续失败触发告警

4. **主入口集成:**
   - 在 `src/main.py` 的 `register_scheduled_tasks()` 方法中添加退出策略调度任务
   - 任务在 scheduler 启动后自动运行

5. **任务执行统计:**
   - 记录检查数量、退出数量、失败数量
   - 每次任务完成后记录摘要日志

## Tasks / Subtasks

- [x] Task 1: 创建退出策略检查任务函数 (AC: #1, #2)
  - [x] 1.1 在 `src/main.py` 创建 `_check_exit_strategies_async` 异步函数
  - [x] 1.2 实现获取所有未平仓持仓逻辑
  - [x] 1.3 实现遍历持仓检查退出条件
  - [x] 1.4 实现触发卖出逻辑
  - [x] 1.5 添加日志记录 (包含 🔍 emoji)

- [x] Task 2: 实现错误处理和隔离 (AC: #3)
  - [x] 2.1 为每个持仓处理使用 try-except 隔离
  - [x] 2.2 单个持仓失败时继续处理其他持仓
  - [x] 2.3 记录失败详情到日志
  - [x] 2.4 集成 AlertManager 进行连续失败告警
- [x] Task 3: 注册定时任务 (AC: #4)
  - [x] 3.1 在 `register_scheduled_tasks()` 添加退出策略任务
  - [x] 3.2 使用 `IntervalTrigger` 配置 5 分钟间隔
  - [x] 3.3 使用配置项 `settings.exit_strategy.exit_check_interval_minutes`
  - [x] 3.4 创建同步包装函数
- [x] Task 4: 实现任务执行统计 (AC: #5)
  - [x] 4.1 统计检查的持仓数量
  - [x] 4.2 统计触发退出的持仓数量
  - [x] 4.3 统计退出失败的持仓数量
  - [x] 4.4 任务完成后记录摘要日志
- [x] Task 5: 添加单元测试 (AC: All)
  - [x] 5.1 测试无持仓时任务正常运行
  - [x] 5.2 测试持仓不满足退出条件时不卖出
  - [x] 5.3 测试持仓满足退出条件时执行卖出
  - [x] 5.4 测试单个持仓卖出失败不影响其他持仓
  - [x] 5.5 测试任务执行统计日志- [ ] Task 1: 创建退出策略检查任务函数 (AC: #1, #2)
  - [ ] 1.1 在 `src/main.py` 创建 `_check_exit_strategies_async` 异步函数
  - [ ] 1.2 实现获取所有未平仓持仓逻辑
  - [ ] 1.3 实现遍历持仓检查退出条件
  - [ ] 1.4 实现触发卖出逻辑
  - [ ] 1.5 添加日志记录 (包含 🔍 emoji)

- [ ] Task 2: 实现错误处理和隔离 (AC: #3)
  - [ ] 2.1 为每个持仓处理使用 try-except 隔离
  - [ ] 2.2 单个持仓失败时继续处理其他持仓
  - [ ] 2.3 记录失败详情到日志
  - [ ] 2.4 集成 AlertManager 进行连续失败告警

- [ ] Task 3: 注册定时任务 (AC: #4)
  - [ ] 3.1 在 `register_scheduled_tasks()` 添加退出策略任务
  - [ ] 3.2 使用 `IntervalTrigger` 配置 5 分钟间隔
  - [ ] 3.3 使用配置项 `settings.exit_strategy.exit_check_interval_minutes`
  - [ ] 3.4 创建同步包装函数

- [ ] Task 4: 实现任务执行统计 (AC: #5)
  - [ ] 4.1 统计检查的持仓数量
  - [ ] 4.2 统计触发退出的持仓数量
  - [ ] 4.3 统计退出失败的持仓数量
  - [ ] 4.4 任务完成后记录摘要日志

- [ ] Task 5: 添加单元测试 (AC: All)
  - [ ] 5.1 测试无持仓时任务正常运行
  - [ ] 5.2 测试持仓不满足退出条件时不卖出
  - [ ] 5.3 测试持仓满足退出条件时执行卖出
  - [ ] 5.4 测试单个持仓卖出失败不影响其他持仓
  - [ ] 5.5 测试任务执行统计日志

## Dev Notes

### 依赖关系

**前置依赖:**
- Story 10.1: 卖出执行器 - `LiveTradingExecutor.sell_position()` 已实现
- Story 10.2: 退出策略配置 - `ExitStrategySettings` 已实现
- Story 10.3: 退出条件检查器 - `ExitChecker` 已实现

**后续依赖:**
- Story 10.5: 退出通知集成 - 使用本 Story 的卖出触发

### 现有组件

**ExitChecker (`src/trading/exit_checker.py`):**
```python
class ExitChecker:
    async def check_exit_conditions(
        self,
        position: Position,
        market: Market,
        latest_prediction: Any | None = None,
    ) -> ExitCheckResult:
        """检查单个持仓是否应该退出"""
```

**ExitCheckResult:**
```python
@dataclass
class ExitCheckResult:
    should_exit: bool
    reason: str  # take_profit, stop_loss, time_exit, signal_exit
    priority: int
    position_id: int
    pnl_pct: float | None
```

**LiveTradingExecutor (`src/trading/live_trading.py`):**
```python
class LiveTradingExecutor:
    async def sell_position(
        self,
        position: Position,
        market: Market,
        reason: str = "manual",
        shares: float | None = None,
    ) -> SellResult:
        """卖出持仓"""
```

**PositionManager (`src/trading/position_manager.py`):**
```python
class PositionManager:
    async def get_open_positions(self) -> list[Position]:
        """获取所有未平仓持仓"""
```

**ExitStrategySettings (`src/config.py`):**
```python
class ExitStrategySettings(BaseEnvSettings):
    exit_check_interval_minutes: int = 5
```

### 实现参考

```python
# src/main.py - 在 register_scheduled_tasks() 中添加

async def _check_exit_strategies_async() -> None:
    """定期检查并执行退出策略。

    Story 10.4: 退出策略调度
    """
    try:
        from src.api.polymarket import PolymarketClient
        from src.storage.repositories.market_repo import MarketRepository
        from src.storage.repositories.position_repo import PositionRepository
        from src.trading.exit_checker import ExitChecker
        from src.trading.live_trading import LiveTradingExecutor
        from src.trading.position_manager import PositionManager

        if not self.state:
            logger.warning("State not initialized, skipping exit strategy check")
            return

        # 初始化组件
        position_repo = PositionRepository()
        market_repo = MarketRepository()
        position_manager = PositionManager(
            repository=position_repo,
            state=self.state,
        )
        exit_checker = ExitChecker()

        # 获取所有未平仓持仓
        open_positions = await position_manager.get_open_positions()

        if not open_positions:
            logger.debug("🔍 No open positions to check for exit")
            return

        # 统计变量
        checked_count = 0
        exit_count = 0
        fail_count = 0

        # 遍历检查每个持仓
        for position in open_positions:
            try:
                checked_count += 1

                # 获取市场信息
                market = await market_repo.get_market(position.market_id)
                if not market:
                    logger.warning(
                        f"🔍 Market {position.market_id} not found for position {position.id}"
                    )
                    continue

                # 检查退出条件
                result = await exit_checker.check_exit_conditions(position, market)

                if result.should_exit:
                    logger.info(
                        f"🔍 Exit triggered for position {position.id}: "
                        f"reason={result.reason}, pnl_pct={result.pnl_pct:.2%}"
                    )

                    # 执行卖出 (仅 live 模式)
                    if settings.trading_mode.lower() == "live":
                        client = PolymarketClient()
                        live_executor = LiveTradingExecutor(
                            client=client,
                            trade_repo=TradeRepository(),
                            position_manager=position_manager,
                            state=self.state,
                        )

                        sell_result = await live_executor.sell_position(
                            position=position,
                            market=market,
                            reason=result.reason,
                        )

                        if sell_result.success:
                            exit_count += 1
                            logger.info(
                                f"💰 Exit executed: position {position.id}, "
                                f"realized_pnl={sell_result.realized_pnl:.2f}"
                            )
                        else:
                            fail_count += 1
                            logger.error(
                                f"❌ Exit failed for position {position.id}: "
                                f"{sell_result.error_message}"
                            )
                    else:
                        # Paper 模式下只记录日志
                        exit_count += 1
                        logger.info(
                            f"📝 Paper mode: Would exit position {position.id} "
                            f"due to {result.reason}"
                        )

            except Exception as e:
                fail_count += 1
                logger.error(
                    f"❌ Failed to check/exit position {position.id}: {e}"
                )
                # 继续处理其他持仓

        # 记录摘要
        logger.info(
            f"🔍 Exit strategy check complete: "
            f"checked={checked_count}, exited={exit_count}, failed={fail_count}"
        )

    except Exception as e:
        logger.error(f"❌ Exit strategy check task failed: {e}")


def check_exit_strategies_task() -> None:
    """Sync wrapper for exit strategy check."""
    asyncio.run(_check_exit_strategies_async())
```

### 任务注册

```python
# 在 register_scheduled_tasks() 方法末尾添加

# Task 7: Check exit strategies periodically
self.scheduler.add_job(
    check_exit_strategies_task,
    IntervalTrigger(minutes=app_settings.exit_strategy.exit_check_interval_minutes),
    id="check_exit_strategies",
    name="Check Exit Strategies",
)

logger.info("Exit strategy task registered")
```

### 配置项

确保 `src/config.py` 中的 `ExitStrategySettings` 包含:

```python
class ExitStrategySettings(BaseEnvSettings):
    """退出策略配置"""

    # 检查间隔 (分钟)
    exit_check_interval_minutes: int = Field(
        default=5,
        alias="EXIT_CHECK_INTERVAL_MINUTES",
        description="退出策略检查间隔 (分钟)",
    )
```

### 日志格式

- 检查开始: `🔍 Checking exit strategies for {n} open positions`
- 退出触发: `🔍 Exit triggered for position {id}: reason={reason}, pnl_pct={pct}`
- 卖出成功: `💰 Exit executed: position {id}, realized_pnl={pnl}`
- 卖出失败: `❌ Exit failed for position {id}: {error}`
- 检查完成: `🔍 Exit strategy check complete: checked={n}, exited={m}, failed={k}`

### 错误隔离策略

每个持仓的处理应该独立，失败不影响其他持仓:

```python
for position in positions:
    try:
        # 检查和卖出逻辑
        ...
    except Exception as e:
        logger.error(f"Failed to process position {position.id}: {e}")
        fail_count += 1
        # 继续下一个持仓，不中断循环
        continue
```

### Project Structure Notes

- 主要修改文件: `src/main.py`
- 遵循现有的任务注册模式
- 测试放在 `tests/test_main.py` 或新建 `tests/test_core/test_exit_scheduling.py`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 10.4] - Story 需求
- [Source: _bmad-output/implementation-artifacts/10-1-sell-executor.md] - 卖出执行器实现
- [Source: _bmad-output/implementation-artifacts/10-3-exit-condition-checker.md] - 退出条件检查器
- [Source: src/core/scheduler.py] - 调度器实现
- [Source: src/main.py] - 主入口和任务注册
- [Source: src/config.py] - ExitStrategySettings 配置
- [Source: src/trading/exit_checker.py] - ExitChecker 类

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (GLM-5)

### Debug Log References

### Completion Notes List
- Implemented exit strategy scheduling task (Task 1-4)
- Added `_check_exit_strategies_async` function in main.py
- Added `check_exit_strategies_task` sync wrapper function
- Implemented error handling with try-except isolation (Task 2)
- Integrated AlertManager for consecutive failure alerts (Task 2)
- Registered scheduled task with IntervalTrigger (Task 3)
- Added execution statistics logging (Task 4)
- Added comprehensive unit tests (Task 5)

### File List
- src/main.py (modified)
- tests/test_main.py (modified - updated task count to 7)
- tests/test_core/test_exit_scheduling.py (created)

## Change Log
- 2026-02-25: Story implementation complete - all 5 tasks and subtasks completed
