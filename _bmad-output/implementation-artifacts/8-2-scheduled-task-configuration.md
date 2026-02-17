# Story 8.2: 定时任务配置

**Story ID:** 8-2-scheduled-task-configuration
**Epic:** Epic 8 - 系统调度与自动化运行
**Status:** done
**Created:** 2026-02-17

---

## User Story

As a **用户**,
I want **系统按配置的时间间隔执行各项任务**,
So that **市场获取、分析、交易自动进行**.

---

## Context

这是 Epic 8 的第二个故事，建立在 Story 8.1 (APScheduler 调度器配置) 的基础上。本故事负责配置具体的定时任务，实现系统的自动化运行。

### Prerequisites
- Story 8.1 已完成 (src/core/scheduler.py)
- Epic 1-7 已完成 (市场数据获取、LLM 分析、交易执行等模块)
- 现有配置系统 (src/config.py)
- 现有日志系统 (src/utils/logger.py)

---

## Acceptance Criteria

### AC1: 配置定时任务频率

**Given** 调度器已配置
**When** 添加定时任务配置
**Then** 在 `src/config.py` 添加以下配置:
```python
# Task Schedule Configuration
SCHEDULE_FETCH_MARKETS_INTERVAL_HOURS: int = 2  # 每 2 小时获取市场
SCHEDULE_CHECK_POSITIONS_INTERVAL_SECONDS: int = 60  # 每 1 分钟检查持仓
SCHEDULE_DAILY_STATISTICS_HOUR: int = 0  # 每日 00:00 更新统计
SCHEDULE_VALIDATE_PREDICTIONS_HOUR: int = 6  # 每日 06:00 验证预测
SCHEDULE_RESET_DAILY_STATE_HOUR: int = 0  # 每日 00:00 重置状态
SCHEDULE_STATE_PERSIST_INTERVAL_MINUTES: int = 5  # 每 5 分钟持久化状态
```

### AC2: 创建任务注册模块

**Given** 任务频率已配置
**When** 实现 `src/core/tasks.py`
**Then** 创建任务注册模块包含:
- `register_all_jobs(scheduler: Scheduler)` - 注册所有定时任务
- 每个任务有独立的注册函数
- 任务执行日志 (开始/结束/耗时)

### AC3: 实现市场获取任务

**Given** 任务注册模块已创建
**When** 实现 `fetch_markets` 任务
**Then** 创建任务函数:
- 任务 ID: `fetch_markets`
- 触发器: IntervalTrigger (每 1-4 小时，默认 2 小时)
- 功能: 调用 Polymarket API 获取市场数据并存储
- 记录任务执行日志 (包含获取的市场数量)

### AC4: 实现市场分析任务

**Given** 市场获取任务已实现
**When** 实现 `analyze_markets` 任务
**Then** 创建任务函数:
- 任务 ID: `analyze_markets`
- 触发器: 由市场获取任务触发 (链式调用)
- 功能: 获取筛选后的市场，调用 LLM 分析
- 记录分析结果日志

### AC5: 实现持仓检查任务

**Given** 持仓管理模块已实现
**When** 实现 `check_positions` 任务
**Then** 创建任务函数:
- 任务 ID: `check_positions`
- 触发器: IntervalTrigger (每 1 分钟)
- 功能: 检查持仓状态，更新 PnL
- 记录持仓状态变化

### AC6: 实现每日统计任务

**Given** 统计记录模块已实现
**When** 实现 `daily_statistics` 任务
**Then** 创建任务函数:
- 任务 ID: `daily_statistics`
- 触发器: CronTrigger (每日 00:00)
- 功能: 统计当日交易数据，记录到 statistics 表
- 记录统计结果日志

### AC7: 实现预测验证任务

**Given** 预测追踪模块已实现
**When** 实现 `validate_predictions` 任务
**Then** 创建任务函数:
- 任务 ID: `validate_predictions`
- 触发器: CronTrigger (每日 06:00)
- 功能: 检查已结算市场，验证预测准确性
- 记录验证结果日志

### AC8: 实现每日状态重置任务

**Given** 状态管理模块已实现
**When** 实现 `reset_daily_state` 任务
**Then** 创建任务函数:
- 任务 ID: `reset_daily_state`
- 触发器: CronTrigger (每日 00:00)
- 功能: 重置每日状态 (daily_pnl, consecutive_losses 等)
- 记录重置日志

### AC9: 实现状态持久化任务

**Given** 状态管理模块已实现
**When** 实现 `persist_state` 任务
**Then** 创建任务函数:
- 任务 ID: `persist_state`
- 触发器: IntervalTrigger (每 5 分钟)
- 功能: 将当前状态持久化到 system_state 表
- 记录持久化日志

### AC10: 单元测试

**Given** 所有任务已实现
**When** 编写单元测试
**Then** 创建 `tests/test_core/test_tasks.py` 包含:
- 测试每个任务的注册
- 测试任务函数的基本功能
- 测试任务执行日志记录

---

## Technical Design

### File Structure

```
src/
├── core/
│   ├── __init__.py
│   ├── scheduler.py       # Story 8.1 已实现
│   └── tasks.py           # 新增: 任务注册和执行
├── config.py              # 扩展: 添加任务调度配置
tests/
├── test_core/
│   ├── __init__.py
│   ├── test_scheduler.py  # Story 8.1 已实现
│   └── test_tasks.py      # 新增: 任务测试
```

### Tasks Module Design

```python
# src/core/tasks.py

"""
定时任务配置模块

本模块负责注册和执行所有定时任务，包括:
- 市场数据获取
- LLM 分析
- 持仓检查
- 每日统计
- 预测验证
- 状态重置
- 状态持久化
"""

import asyncio
import time
from datetime import datetime
from typing import TYPE_CHECKING

from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from src.config import settings
from src.core.scheduler import Scheduler
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.api.polymarket import PolymarketClient
    from src.analysis.llm_analyzer import LLMAnalyzer
    from src.trading.position_manager import PositionManager
    from src.core.state import ThreadSafeState

logger = get_logger(__name__)


def register_all_jobs(
    scheduler: Scheduler,
    polymarket_client: "PolymarketClient",
    llm_analyzer: "LLMAnalyzer",
    position_manager: "PositionManager",
    state: "ThreadSafeState"
) -> None:
    """
    注册所有定时任务

    Args:
        scheduler: 调度器实例
        polymarket_client: Polymarket API 客户端
        llm_analyzer: LLM 分析器
        position_manager: 持仓管理器
        state: 线程安全状态管理器
    """
    logger.info("Registering all scheduled jobs...")

    # 注册市场获取任务
    register_fetch_markets_job(scheduler, polymarket_client)

    # 注册持仓检查任务
    register_check_positions_job(scheduler, position_manager)

    # 注册每日统计任务
    register_daily_statistics_job(scheduler, state)

    # 注册预测验证任务
    register_validate_predictions_job(scheduler, llm_analyzer)

    # 注册每日状态重置任务
    register_reset_daily_state_job(scheduler, state)

    # 注册状态持久化任务
    register_persist_state_job(scheduler, state)

    logger.info(f"All jobs registered: {scheduler.get_jobs()}")


def register_fetch_markets_job(scheduler: Scheduler, client: "PolymarketClient") -> None:
    """注册市场获取任务"""
    trigger = IntervalTrigger(
        hours=settings.SCHEDULE_FETCH_MARKETS_INTERVAL_HOURS
    )
    scheduler.add_job(
        func=lambda: asyncio.run(_fetch_markets_task(client)),
        trigger=trigger,
        id="fetch_markets",
        name="Fetch Markets from Polymarket"
    )
    logger.info(
        f"Job 'fetch_markets' registered with interval: {settings.SCHEDULE_FETCH_MARKETS_INTERVAL_HOURS}h"
    )


async def _fetch_markets_task(client: "PolymarketClient") -> None:
    """市场获取任务执行函数"""
    start_time = time.time()
    logger.info("Job 'fetch_markets' started")

    try:
        # 获取市场数据
        markets = await client.get_markets()

        # 存储到数据库 (由 client 内部处理)
        # client.get_markets() 会自动存储到数据库

        elapsed = time.time() - start_time
        logger.info(
            f"Job 'fetch_markets' completed: {len(markets)} markets fetched in {elapsed:.2f}s"
        )

        # 触发市场分析任务
        # 分析在获取后自动进行
        await _analyze_markets_task(client, markets)

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"Job 'fetch_markets' failed after {elapsed:.2f}s: {e}",
            exc_info=True
        )


async def _analyze_markets_task(client: "PolymarketClient", markets: list) -> None:
    """市场分析任务执行函数 (由 fetch_markets 触发)"""
    start_time = time.time()
    logger.info("Job 'analyze_markets' started")

    try:
        # 筛选市场
        from src.analysis.market_filter import MarketFilter
        market_filter = MarketFilter()
        filtered_markets = market_filter.filter_markets(markets)

        logger.info(f"Filtered markets: {len(filtered_markets)}/{len(markets)}")

        # 对筛选后的市场进行 LLM 分析
        from src.analysis.llm_analyzer import LLMAnalyzer
        from src.config import settings

        analyzer = LLMAnalyzer()

        for market in filtered_markets:
            try:
                prediction = await analyzer.analyze_market(market)
                logger.info(
                    f"Market analyzed: {market.id[:8]}... "
                    f"prediction={prediction.predicted_probability:.2%} "
                    f"confidence={prediction.confidence:.2%}"
                )
            except Exception as e:
                logger.warning(f"Failed to analyze market {market.id}: {e}")

        elapsed = time.time() - start_time
        logger.info(f"Job 'analyze_markets' completed in {elapsed:.2f}s")

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"Job 'analyze_markets' failed after {elapsed:.2f}s: {e}",
            exc_info=True
        )


def register_check_positions_job(scheduler: Scheduler, manager: "PositionManager") -> None:
    """注册持仓检查任务"""
    trigger = IntervalTrigger(
        seconds=settings.SCHEDULE_CHECK_POSITIONS_INTERVAL_SECONDS
    )
    scheduler.add_job(
        func=lambda: asyncio.run(_check_positions_task(manager)),
        trigger=trigger,
        id="check_positions",
        name="Check Positions and Update PnL"
    )
    logger.info(
        f"Job 'check_positions' registered with interval: {settings.SCHEDULE_CHECK_POSITIONS_INTERVAL_SECONDS}s"
    )


async def _check_positions_task(manager: "PositionManager") -> None:
    """持仓检查任务执行函数"""
    start_time = time.time()
    logger.debug("Job 'check_positions' started")

    try:
        # 获取所有未平仓位
        positions = await manager.get_open_positions()

        for position in positions:
            # 更新持仓市值和 PnL
            await manager.update_position_value(position.id)

        elapsed = time.time() - start_time
        logger.debug(
            f"Job 'check_positions' completed: {len(positions)} positions checked in {elapsed:.2f}s"
        )

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"Job 'check_positions' failed after {elapsed:.2f}s: {e}",
            exc_info=True
        )


def register_daily_statistics_job(scheduler: Scheduler, state: "ThreadSafeState") -> None:
    """注册每日统计任务"""
    trigger = CronTrigger(
        hour=settings.SCHEDULE_DAILY_STATISTICS_HOUR,
        minute=0
    )
    scheduler.add_job(
        func=lambda: asyncio.run(_daily_statistics_task(state)),
        trigger=trigger,
        id="daily_statistics",
        name="Daily Statistics Update"
    )
    logger.info(
        f"Job 'daily_statistics' registered at hour: {settings.SCHEDULE_DAILY_STATISTICS_HOUR}"
    )


async def _daily_statistics_task(state: "ThreadSafeState") -> None:
    """每日统计任务执行函数"""
    start_time = time.time()
    logger.info("Job 'daily_statistics' started")

    try:
        from src.storage.repositories.statistics_repo import StatisticsRepository

        repo = StatisticsRepository()

        # 获取当前状态
        current_state = state.get_state()

        # 创建统计记录
        await repo.save_daily_stats({
            "date": datetime.now().date(),
            "mode": "PAPER",  # 从配置获取
            "starting_capital": current_state.get("starting_capital"),
            "ending_capital": current_state.get("current_capital"),
            "total_pnl": current_state.get("daily_pnl"),
            "total_trades": current_state.get("daily_trades", 0),
            "winning_trades": current_state.get("daily_wins", 0),
            "losing_trades": current_state.get("daily_losses", 0),
            "win_rate": current_state.get("daily_wins", 0) / max(current_state.get("daily_trades", 1), 1)
        })

        elapsed = time.time() - start_time
        logger.info(f"Job 'daily_statistics' completed in {elapsed:.2f}s")

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"Job 'daily_statistics' failed after {elapsed:.2f}s: {e}",
            exc_info=True
        )


def register_validate_predictions_job(scheduler: Scheduler, analyzer: "LLMAnalyzer") -> None:
    """注册预测验证任务"""
    trigger = CronTrigger(
        hour=settings.SCHEDULE_VALIDATE_PREDICTIONS_HOUR,
        minute=0
    )
    scheduler.add_job(
        func=lambda: asyncio.run(_validate_predictions_task()),
        trigger=trigger,
        id="validate_predictions",
        name="Validate Predictions against Resolved Markets"
    )
    logger.info(
        f"Job 'validate_predictions' registered at hour: {settings.SCHEDULE_VALIDATE_PREDICTIONS_HOUR}"
    )


async def _validate_predictions_task() -> None:
    """预测验证任务执行函数"""
    start_time = time.time()
    logger.info("Job 'validate_predictions' started")

    try:
        from src.analysis.prediction_tracker import PredictionTracker

        tracker = PredictionTracker()

        # 检查已结算市场并验证预测
        validated_count = await tracker.check_resolved_markets()

        elapsed = time.time() - start_time
        logger.info(
            f"Job 'validate_predictions' completed: {validated_count} predictions validated in {elapsed:.2f}s"
        )

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"Job 'validate_predictions' failed after {elapsed:.2f}s: {e}",
            exc_info=True
        )


def register_reset_daily_state_job(scheduler: Scheduler, state: "ThreadSafeState") -> None:
    """注册每日状态重置任务"""
    trigger = CronTrigger(
        hour=settings.SCHEDULE_RESET_DAILY_STATE_HOUR,
        minute=0
    )
    scheduler.add_job(
        func=lambda: asyncio.run(_reset_daily_state_task(state)),
        trigger=trigger,
        id="reset_daily_state",
        name="Reset Daily State"
    )
    logger.info(
        f"Job 'reset_daily_state' registered at hour: {settings.SCHEDULE_RESET_DAILY_STATE_HOUR}"
    )


async def _reset_daily_state_task(state: "ThreadSafeState") -> None:
    """每日状态重置任务执行函数"""
    start_time = time.time()
    logger.info("Job 'reset_daily_state' started")

    try:
        # 重置每日状态
        state.reset_daily()

        elapsed = time.time() - start_time
        logger.info(f"Job 'reset_daily_state' completed in {elapsed:.2f}s")

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"Job 'reset_daily_state' failed after {elapsed:.2f}s: {e}",
            exc_info=True
        )


def register_persist_state_job(scheduler: Scheduler, state: "ThreadSafeState") -> None:
    """注册状态持久化任务"""
    trigger = IntervalTrigger(
        minutes=settings.SCHEDULE_STATE_PERSIST_INTERVAL_MINUTES
    )
    scheduler.add_job(
        func=lambda: asyncio.run(_persist_state_task(state)),
        trigger=trigger,
        id="persist_state",
        name="Persist State to Database"
    )
    logger.info(
        f"Job 'persist_state' registered with interval: {settings.SCHEDULE_STATE_PERSIST_INTERVAL_MINUTES}min"
    )


async def _persist_state_task(state: "ThreadSafeState") -> None:
    """状态持久化任务执行函数"""
    start_time = time.time()
    logger.debug("Job 'persist_state' started")

    try:
        # 持久化状态到数据库
        await state.persist()

        elapsed = time.time() - start_time
        logger.debug(f"Job 'persist_state' completed in {elapsed:.2f}s")

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"Job 'persist_state' failed after {elapsed:.2f}s: {e}",
            exc_info=True
        )
```

### Configuration Updates

```python
# 在 src/config.py 中添加

class Settings(BaseSettings):
    # ... 现有配置 ...

    # Task Schedule Configuration
    SCHEDULE_FETCH_MARKETS_INTERVAL_HOURS: int = 2
    SCHEDULE_CHECK_POSITIONS_INTERVAL_SECONDS: int = 60
    SCHEDULE_DAILY_STATISTICS_HOUR: int = 0
    SCHEDULE_VALIDATE_PREDICTIONS_HOUR: int = 6
    SCHEDULE_RESET_DAILY_STATE_HOUR: int = 0
    SCHEDULE_STATE_PERSIST_INTERVAL_MINUTES: int = 5
```

---

## Task Schedule Summary

| 任务 ID | 触发器 | 频率 | 描述 |
|---------|--------|------|------|
| `fetch_markets` | IntervalTrigger | 每 2 小时 | 获取 Polymarket 市场数据 |
| `analyze_markets` | 链式调用 | 市场获取后 | LLM 分析筛选后的市场 |
| `check_positions` | IntervalTrigger | 每 1 分钟 | 检查持仓状态和 PnL |
| `daily_statistics` | CronTrigger | 每日 00:00 | 更新每日统计 |
| `validate_predictions` | CronTrigger | 每日 06:00 | 验证已结算市场预测 |
| `reset_daily_state` | CronTrigger | 每日 00:00 | 重置每日状态 |
| `persist_state` | IntervalTrigger | 每 5 分钟 | 持久化状态到数据库 |

---

## Dependencies

### Internal Dependencies
- `src/core/scheduler.py` - 调度器 (Story 8.1)
- `src/api/polymarket.py` - Polymarket API 客户端 (Epic 2)
- `src/analysis/market_filter.py` - 市场筛选 (Epic 2)
- `src/analysis/llm_analyzer.py` - LLM 分析器 (Epic 3)
- `src/trading/position_manager.py` - 持仓管理 (Epic 4)
- `src/core/state.py` - 状态管理 (Epic 4)
- `src/analysis/prediction_tracker.py` - 预测追踪 (Epic 6)
- `src/storage/repositories/statistics_repo.py` - 统计仓库 (Epic 5)
- `src/config.py` - 配置管理 (Epic 1)
- `src/utils/logger.py` - 日志系统 (Epic 1)

---

## Test Cases

### Test File: `tests/test_core/test_tasks.py`

```python
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime

from src.core.tasks import (
    register_all_jobs,
    register_fetch_markets_job,
    register_check_positions_job,
    register_daily_statistics_job,
    register_validate_predictions_job,
    register_reset_daily_state_job,
    register_persist_state_job,
    _fetch_markets_task,
    _check_positions_task,
    _daily_statistics_task,
    _validate_predictions_task,
    _reset_daily_state_task,
    _persist_state_task,
)
from src.core.scheduler import Scheduler


class TestRegisterAllJobs:
    """测试注册所有任务"""

    def test_register_all_jobs(self):
        """测试注册所有任务"""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock()
        mock_scheduler.get_jobs = Mock(return_value=[
            "fetch_markets",
            "check_positions",
            "daily_statistics",
            "validate_predictions",
            "reset_daily_state",
            "persist_state"
        ])

        mock_client = Mock()
        mock_analyzer = Mock()
        mock_manager = Mock()
        mock_state = Mock()

        register_all_jobs(
            mock_scheduler,
            mock_client,
            mock_analyzer,
            mock_manager,
            mock_state
        )

        # 应该调用了 6 次 add_job
        assert mock_scheduler.add_job.call_count == 6

    def test_register_fetch_markets_job(self):
        """测试注册市场获取任务"""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock()
        mock_client = Mock()

        register_fetch_markets_job(mock_scheduler, mock_client)

        mock_scheduler.add_job.assert_called_once()
        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        assert call_kwargs["id"] == "fetch_markets"

    def test_register_check_positions_job(self):
        """测试注册持仓检查任务"""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock()
        mock_manager = Mock()

        register_check_positions_job(mock_scheduler, mock_manager)

        mock_scheduler.add_job.assert_called_once()
        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        assert call_kwargs["id"] == "check_positions"

    def test_register_daily_statistics_job(self):
        """测试注册每日统计任务"""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock()
        mock_state = Mock()

        register_daily_statistics_job(mock_scheduler, mock_state)

        mock_scheduler.add_job.assert_called_once()
        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        assert call_kwargs["id"] == "daily_statistics"

    def test_register_validate_predictions_job(self):
        """测试注册预测验证任务"""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock()
        mock_analyzer = Mock()

        register_validate_predictions_job(mock_scheduler, mock_analyzer)

        mock_scheduler.add_job.assert_called_once()
        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        assert call_kwargs["id"] == "validate_predictions"

    def test_register_reset_daily_state_job(self):
        """测试注册每日状态重置任务"""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock()
        mock_state = Mock()

        register_reset_daily_state_job(mock_scheduler, mock_state)

        mock_scheduler.add_job.assert_called_once()
        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        assert call_kwargs["id"] == "reset_daily_state"

    def test_register_persist_state_job(self):
        """测试注册状态持久化任务"""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock()
        mock_state = Mock()

        register_persist_state_job(mock_scheduler, mock_state)

        mock_scheduler.add_job.assert_called_once()
        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        assert call_kwargs["id"] == "persist_state"


class TestTaskExecution:
    """测试任务执行"""

    @pytest.mark.asyncio
    async def test_fetch_markets_task_success(self):
        """测试市场获取任务成功"""
        mock_client = Mock()
        mock_client.get_markets = AsyncMock(return_value=[Mock(), Mock()])

        # Mock _analyze_markets_task
        with patch("src.core.tasks._analyze_markets_task") as mock_analyze:
            mock_analyze.return_value = AsyncMock()

            await _fetch_markets_task(mock_client)

            mock_client.get_markets.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_markets_task_failure(self):
        """测试市场获取任务失败"""
        mock_client = Mock()
        mock_client.get_markets = AsyncMock(side_effect=Exception("API Error"))

        # 应该不会抛出异常，只是记录错误
        await _fetch_markets_task(mock_client)

        mock_client.get_markets.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_positions_task_success(self):
        """测试持仓检查任务成功"""
        mock_manager = Mock()
        mock_position = Mock()
        mock_position.id = 1
        mock_manager.get_open_positions = AsyncMock(return_value=[mock_position])
        mock_manager.update_position_value = AsyncMock()

        await _check_positions_task(mock_manager)

        mock_manager.get_open_positions.assert_called_once()
        mock_manager.update_position_value.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_daily_statistics_task_success(self):
        """测试每日统计任务成功"""
        mock_state = Mock()
        mock_state.get_state = Mock(return_value={
            "starting_capital": 200.0,
            "current_capital": 180.0,
            "daily_pnl": -20.0,
            "daily_trades": 5,
            "daily_wins": 2,
            "daily_losses": 3
        })

        with patch("src.core.tasks.StatisticsRepository") as MockRepo:
            mock_repo = Mock()
            mock_repo.save_daily_stats = AsyncMock()
            MockRepo.return_value = mock_repo

            await _daily_statistics_task(mock_state)

            mock_repo.save_daily_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_predictions_task_success(self):
        """测试预测验证任务成功"""
        with patch("src.core.tasks.PredictionTracker") as MockTracker:
            mock_tracker = Mock()
            mock_tracker.check_resolved_markets = AsyncMock(return_value=5)
            MockTracker.return_value = mock_tracker

            await _validate_predictions_task()

            mock_tracker.check_resolved_markets.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_daily_state_task_success(self):
        """测试每日状态重置任务成功"""
        mock_state = Mock()
        mock_state.reset_daily = Mock()

        await _reset_daily_state_task(mock_state)

        mock_state.reset_daily.assert_called_once()

    @pytest.mark.asyncio
    async def test_persist_state_task_success(self):
        """测试状态持久化任务成功"""
        mock_state = Mock()
        mock_state.persist = AsyncMock()

        await _persist_state_task(mock_state)

        mock_state.persist.assert_called_once()

    @pytest.mark.asyncio
    async def test_persist_state_task_failure(self):
        """测试状态持久化任务失败"""
        mock_state = Mock()
        mock_state.persist = AsyncMock(side_effect=Exception("DB Error"))

        # 应该不会抛出异常，只是记录错误
        await _persist_state_task(mock_state)

        mock_state.persist.assert_called_once()
```

---

## Implementation Notes

1. **异步任务执行**: 所有任务函数都是异步的，使用 `asyncio.run()` 包装
2. **链式任务**: 市场分析任务 (`analyze_markets`) 由市场获取任务触发，不需要独立调度
3. **错误处理**: 每个任务都有 try-except 块，确保单个任务失败不影响其他任务
4. **日志记录**: 每个任务记录开始、结束、耗时和结果
5. **配置化**: 所有任务频率都可通过配置文件调整
6. **依赖注入**: 任务注册函数接受依赖项作为参数，便于测试

---

## Definition of Done

- [ ] `src/core/tasks.py` 实现完成
- [ ] `src/core/__init__.py` 更新导出
- [ ] `src/config.py` 添加任务调度配置
- [ ] `tests/test_core/test_tasks.py` 测试通过
- [ ] 代码通过 `pytest`、`mypy src/` 和 `ruff check .`
- [ ] 代码覆盖率 >= 90%

---

## Next Story

完成后继续: **Story 8.3: 主入口与启动流程** - 实现主入口点统一启动所有系统组件
