# Story 8.1: APScheduler 调度器配置

**Story ID:** 8-1-apscheduler-configuration
**Epic:** Epic 8 - 系统调度与自动化运行
**Status:** ready-for-dev
**Created:** 2026-02-17

---

## User Story

As a **开发者**,
I want **配置 APScheduler 实现定时任务调度**,
So that **系统能够按计划自动执行各项任务**.

---

## Context

这是 Epic 8 的第一个故事，为整个系统调度功能奠定基础。APScheduler 是 Python 中流行的调度库，支持多种触发器和任务存储方式。

### Prerequisites
- Epic 1-7 已完成
- 现有 FastAPI 应用结构 (src/dashboard/app.py)
- 现有配置系统 (src/config.py)
- 现有日志系统 (src/utils/logger.py)

---

## Acceptance Criteria

### AC1: 创建 APScheduler 调度器类

**Given** Epic 1-7 已完成
**When** 实现 `src/core/scheduler.py`
**Then** 创建 `Scheduler` 类包含:
- 使用 `AsyncIOScheduler` (异步调度)
- 支持配置时区 (默认 UTC)
- 配置任务存储 (MemoryJobStore)
- 记录调度器状态日志

### AC2: 提供启动/停止方法

**Given** 调度器类已创建
**When** 实现生命周期方法
**Then** 提供以下方法:
- `start()` - 启动调度器
- `shutdown(wait: bool = True)` - 优雅关闭
- 记录启动/停止日志

### AC3: 支持动态任务管理

**Given** 调度器已启动
**When** 需要添加或移除任务
**Then** 提供以下方法:
- `add_job(func, trigger, id, **kwargs)` - 添加任务
- `remove_job(job_id)` - 移除任务
- `get_jobs()` - 获取所有任务
- `pause_job(job_id)` - 暂停任务
- `resume_job(job_id)` - 恢复任务

### AC4: 配置集成

**Given** 调度器已实现
**When** 集成到配置系统
**Then** 在 `src/config.py` 添加调度相关配置:
```python
# Scheduler Configuration
SCHEDULER_TIMEZONE: str = "UTC"
SCHEDULER_JOBSTORES_DB: str = "data/scheduler.db"
SCHEDULER_EXECUTORS_DEFAULT_POOL_SIZE: int = 10
```

### AC5: 单元测试

**Given** 调度器实现完成
**When** 编写单元测试
**Then** 创建 `tests/test_core/test_scheduler.py` 包含:
- 测试调度器初始化
- 测试任务添加/移除
- 测试启动/停止
- 测试时区配置

---

## Technical Design

### File Structure

```
src/
├── core/
│   ├── __init__.py
│   └── scheduler.py       # 新增: Scheduler 类
├── config.py              # 扩展: 添加调度配置
tests/
├── test_core/
│   ├── __init__.py
│   └── test_scheduler.py  # 新增: 调度器测试
```

### Scheduler Class Design

```python
# src/core/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from typing import Callable, Optional, List, Any
import logging

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Scheduler:
    """APScheduler 调度器封装类"""

    def __init__(self):
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._is_running = False

    def _create_scheduler(self) -> AsyncIOScheduler:
        """创建并配置调度器实例"""
        # 使用 MemoryJobStore 而非 SQLiteJobStore
        # 原因: SQLite 的同步 IO 操作与 AsyncIOScheduler 的异步模型存在兼容性问题
        # 在某些情况下可能导致阻塞或死锁
        # MemoryJobStore 对于短期运行的调度任务足够使用
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(
                max_workers=settings.SCHEDULER_EXECUTORS_DEFAULT_POOL_SIZE
            )
        }
        job_defaults = {
            'coalesce': True,  # 合并错过的任务
            'max_instances': 1,  # 每个任务最大并发实例
        }

        scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=settings.SCHEDULER_TIMEZONE
        )

        logger.info(
            "Scheduler configured",
            extra={
                "timezone": settings.SCHEDULER_TIMEZONE,
                "jobstore": "memory",
                "executor_pool_size": settings.SCHEDULER_EXECUTORS_DEFAULT_POOL_SIZE
            }
        )

        return scheduler

    @property
    def scheduler(self) -> AsyncIOScheduler:
        """获取调度器实例 (懒加载)"""
        if self._scheduler is None:
            self._scheduler = self._create_scheduler()
        return self._scheduler

    def start(self) -> None:
        """启动调度器"""
        if self._is_running:
            logger.warning("Scheduler is already running")
            return

        self.scheduler.start()
        self._is_running = True
        logger.info("Scheduler started")

    def shutdown(self, wait: bool = True) -> None:
        """优雅关闭调度器

        Args:
            wait: 是否等待正在执行的任务完成
        """
        if not self._is_running:
            logger.warning("Scheduler is not running")
            return

        self.scheduler.shutdown(wait=wait)
        self._is_running = False
        logger.info("Scheduler shutdown complete", extra={"wait": wait})

    def add_job(
        self,
        func: Callable,
        trigger: Any,
        id: str,
        name: Optional[str] = None,
        replace_existing: bool = True,
        **kwargs
    ) -> str:
        """添加定时任务

        Args:
            func: 要执行的函数
            trigger: 触发器 (IntervalTrigger, CronTrigger 等)
            id: 任务唯一标识
            name: 任务名称
            replace_existing: 是否替换已存在的同名任务
            **kwargs: 传递给 APScheduler 的其他参数

        Returns:
            任务 ID
        """
        job = self.scheduler.add_job(
            func=func,
            trigger=trigger,
            id=id,
            name=name or id,
            replace_existing=replace_existing,
            **kwargs
        )
        logger.info(
            f"Job added: {id}",
            extra={"job_id": id, "job_name": name}
        )
        return job.id

    def remove_job(self, job_id: str) -> bool:
        """移除定时任务

        Args:
            job_id: 任务 ID

        Returns:
            是否成功移除
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Job removed: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id}: {e}")
            return False

    def get_jobs(self) -> List[str]:
        """获取所有任务 ID 列表"""
        return [job.id for job in self.scheduler.get_jobs()]

    def pause_job(self, job_id: str) -> bool:
        """暂停任务"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Job paused: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to pause job {job_id}: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """恢复任务"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Job resumed: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to resume job {job_id}: {e}")
            return False

    @property
    def is_running(self) -> bool:
        """调度器是否正在运行"""
        return self._is_running


# 单例实例
scheduler = Scheduler()
```

### Configuration Updates

```python
# 在 src/config.py 中添加

class Settings(BaseSettings):
    # ... 现有配置 ...

    # Scheduler Configuration
    SCHEDULER_TIMEZONE: str = "UTC"
    SCHEDULER_JOBSTORES_DB: str = "data/scheduler.db"
    SCHEDULER_EXECUTORS_DEFAULT_POOL_SIZE: int = 10
```

---

## Dependencies

### Python Packages
- `apscheduler>=3.10.0` - 需要添加到 requirements.txt

### Internal Dependencies
- `src/config.py` - 配置管理
- `src/utils/logger.py` - 日志系统

---

## Test Cases

### Test File: `tests/test_core/test_scheduler.py`

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.core.scheduler import Scheduler, scheduler


class TestScheduler:
    """Scheduler 类单元测试"""

    def test_scheduler_initialization(self):
        """测试调度器初始化"""
        s = Scheduler()
        assert s._scheduler is None  # 懒加载
        assert s._is_running is False

    def test_scheduler_lazy_loading(self):
        """测试调度器懒加载"""
        s = Scheduler()
        scheduler_instance = s.scheduler
        assert scheduler_instance is not None
        assert s._scheduler is scheduler_instance

    def test_start_scheduler(self):
        """测试启动调度器"""
        s = Scheduler()
        with patch.object(s, '_create_scheduler') as mock_create:
            mock_scheduler = MagicMock()
            mock_create.return_value = mock_scheduler
            s._scheduler = mock_scheduler

            s.start()

            mock_scheduler.start.assert_called_once()
            assert s._is_running is True

    def test_start_already_running(self):
        """测试重复启动调度器"""
        s = Scheduler()
        s._is_running = True

        # 应该不会抛出异常，只是记录警告
        s.start()
        assert s._is_running is True

    def test_shutdown_scheduler(self):
        """测试关闭调度器"""
        s = Scheduler()
        mock_scheduler = MagicMock()
        s._scheduler = mock_scheduler
        s._is_running = True

        s.shutdown(wait=True)

        mock_scheduler.shutdown.assert_called_once_with(wait=True)
        assert s._is_running is False

    def test_shutdown_not_running(self):
        """测试关闭未运行的调度器"""
        s = Scheduler()
        s._is_running = False

        # 应该不会抛出异常
        s.shutdown()
        assert s._is_running is False

    def test_add_job(self):
        """测试添加任务"""
        s = Scheduler()
        mock_scheduler = MagicMock()
        mock_job = MagicMock()
        mock_job.id = "test_job"
        mock_scheduler.add_job.return_value = mock_job
        s._scheduler = mock_scheduler

        from apscheduler.triggers.interval import IntervalTrigger
        trigger = IntervalTrigger(seconds=60)

        job_id = s.add_job(
            func=lambda: None,
            trigger=trigger,
            id="test_job",
            name="Test Job"
        )

        assert job_id == "test_job"
        mock_scheduler.add_job.assert_called_once()

    def test_remove_job(self):
        """测试移除任务"""
        s = Scheduler()
        mock_scheduler = MagicMock()
        s._scheduler = mock_scheduler

        result = s.remove_job("test_job")

        assert result is True
        mock_scheduler.remove_job.assert_called_once_with("test_job")

    def test_remove_job_not_found(self):
        """测试移除不存在的任务"""
        s = Scheduler()
        mock_scheduler = MagicMock()
        mock_scheduler.remove_job.side_effect = Exception("Job not found")
        s._scheduler = mock_scheduler

        result = s.remove_job("nonexistent_job")

        assert result is False

    def test_get_jobs(self):
        """测试获取任务列表"""
        s = Scheduler()
        mock_scheduler = MagicMock()
        mock_job1 = MagicMock()
        mock_job1.id = "job1"
        mock_job2 = MagicMock()
        mock_job2.id = "job2"
        mock_scheduler.get_jobs.return_value = [mock_job1, mock_job2]
        s._scheduler = mock_scheduler

        jobs = s.get_jobs()

        assert jobs == ["job1", "job2"]

    def test_pause_and_resume_job(self):
        """测试暂停和恢复任务"""
        s = Scheduler()
        mock_scheduler = MagicMock()
        s._scheduler = mock_scheduler

        # 暂停
        result = s.pause_job("test_job")
        assert result is True
        mock_scheduler.pause_job.assert_called_once_with("test_job")

        # 恢复
        result = s.resume_job("test_job")
        assert result is True
        mock_scheduler.resume_job.assert_called_once_with("test_job")

    def test_is_running_property(self):
        """测试 is_running 属性"""
        s = Scheduler()
        assert s.is_running is False

        s._is_running = True
        assert s.is_running is True


class TestSchedulerSingleton:
    """测试调度器单例"""

    def test_singleton_instance_exists(self):
        """测试单例实例存在"""
        from src.core.scheduler import scheduler
        assert scheduler is not None
        assert isinstance(scheduler, Scheduler)
```

---

## Implementation Notes

1. **异步支持**: 使用 `AsyncIOScheduler` 以支持异步任务执行
2. **任务存储**: 使用 MemoryJobStore 存储任务 (非持久化)
   - **技术原因**: SQLite JobStore 的同步 IO 操作与 AsyncIOScheduler 的异步模型存在兼容性问题，在某些情况下可能导致阻塞或死锁。MemoryJobStore 对于短期运行的调度任务足够使用，且避免了异步环境下的潜在问题。
   - **未来改进**: 如需持久化，可考虑使用 SQLAlchemyJobStore 配合异步数据库驱动
3. **线程池执行器**: 配置线程池执行器处理阻塞操作
4. **懒加载**: 调度器实例采用懒加载模式，首次访问时才创建
5. **单例模式**: 提供全局单例实例 `scheduler`，方便在应用各处使用

---

## Definition of Done

- [ ] `src/core/scheduler.py` 实现完成
- [ ] `src/core/__init__.py` 更新导出
- [ ] `src/config.py` 添加调度配置
- [ ] `requirements.txt` 添加 `apscheduler>=3.10.0`
- [ ] `tests/test_core/test_scheduler.py` 测试通过
- [ ] 代码通过 `pytest`、`mypy src/` 和 `ruff check .`
- [ ] 代码覆盖率 >= 90%

---

## Next Story

完成后继续: **Story 8.2: 定时任务配置** - 配置具体的定时任务 (市场获取、分析、持仓检查等)
