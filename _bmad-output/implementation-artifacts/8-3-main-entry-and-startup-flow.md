# Story 8.3: 主入口与启动流程

**Story ID:** 8-3-main-entry-and-startup-flow
**Epic:** Epic 8 - 系统调度与自动化运行
**Status:** done
**Created:** 2026-02-17

---

## User Story

As a **开发者**,
I want **实现主入口点统一启动所有系统组件**,
So that **系统可以通过单个命令启动**.

---

## Context

这是 Epic 8 的第三个故事，在调度器配置 (Story 8.1) 和定时任务配置 (Story 8.2) 完成后，需要实现统一的主入口点来协调所有系统组件的启动和关闭。

### Prerequisites
- Epic 1-7 已完成
- Story 8.1: APScheduler 调度器配置 (已完成)
- Story 8.2: 定时任务配置 (已完成)
- 现有 FastAPI 应用结构 (src/dashboard/app.py)
- 现有配置系统 (src/config.py)
- 现有状态管理 (src/core/state.py)
- 现有数据库初始化 (src/storage/database.py)

---

## Acceptance Criteria

### AC1: 创建主入口模块

**Given** 调度器和任务已配置
**When** 实现 `src/main.py`
**Then** 创建主入口函数包含:
- `async def main()` - 异步主函数
- 支持 `--mode` (paper/live) 命令行参数
- 支持 `--config` (配置文件路径) 命令行参数
- 完整的启动流程编排

### AC2: 实现启动流程

**Given** 主入口函数已创建
**When** 系统启动时
**Then** 执行以下启动步骤:

```python
async def main():
    # 1. 解析命令行参数
    args = parse_args()

    # 2. 加载配置
    config = load_config(args.config)

    # 3. 初始化日志
    setup_logger(config)

    # 4. 初始化数据库
    await init_db()

    # 5. 初始化状态管理器
    state = ThreadSafeState(config)

    # 6. 启动 FastAPI (后台任务)
    start_dashboard()

    # 7. 启动调度器
    scheduler = Scheduler(config)
    scheduler.start()

    # 8. 等待关闭信号
    await wait_for_shutdown()
```

### AC3: 优雅关闭处理

**Given** 系统正在运行
**When** 收到关闭信号 (SIGTERM, SIGINT)
**Then** 执行优雅关闭:
- 停止接收新任务
- 等待当前任务完成 (最多 30 秒)
- 关闭调度器
- 关闭 FastAPI 服务器
- 持久化系统状态
- 记录关闭日志

### AC4: PID 文件管理

**Given** 系统启动
**When** 主入口运行时
**Then** 实现 PID 文件管理:
- 启动时写入 `.bot.pid` 文件
- 关闭时删除 PID 文件
- 检测已有实例运行 (避免重复启动)

### AC5: 单元测试

**Given** 主入口实现完成
**When** 编写单元测试
**Then** 创建 `tests/test_main.py` 包含:
- 测试命令行参数解析
- 测试启动流程
- 测试优雅关闭
- 测试信号处理

---

## Technical Design

### File Structure

```
src/
├── main.py                    # 新增: 主入口模块
├── core/
│   ├── __init__.py
│   ├── scheduler.py           # 已有: 调度器
│   └── state.py               # 已有: 状态管理
├── config.py                  # 已有: 配置管理
├── storage/
│   └── database.py            # 已有: 数据库
└── dashboard/
    └── app.py                 # 已有: FastAPI 应用
tests/
├── test_main.py               # 新增: 主入口测试
```

### Main Entry Design

```python
# src/main.py

import asyncio
import argparse
import signal
import sys
from pathlib import Path
from typing import Optional

from src.config import settings
from src.utils.logger import get_logger, setup_logger
from src.storage.database import init_db
from src.core.state import ThreadSafeState
from src.core.scheduler import Scheduler
from src.dashboard.app import create_app

logger = get_logger(__name__)


class Application:
    """主应用程序类"""

    def __init__(self, mode: str = "paper", config_path: Optional[str] = None):
        self.mode = mode
        self.config_path = config_path
        self.state: Optional[ThreadSafeState] = None
        self.scheduler: Optional[Scheduler] = None
        self._shutdown_event = asyncio.Event()
        self._dashboard_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """初始化所有组件"""
        logger.info("Initializing application...")

        # 1. 初始化日志
        setup_logger(settings)

        # 2. 初始化数据库
        await init_db()
        logger.info("Database initialized")

        # 3. 初始化状态管理器
        self.state = ThreadSafeState(settings)
        logger.info("State manager initialized")

        # 4. 初始化调度器
        self.scheduler = Scheduler()
        logger.info("Scheduler initialized")

    async def start_dashboard(self) -> None:
        """启动 FastAPI Dashboard (后台任务)"""
        import uvicorn
        from src.dashboard.app import app

        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=False,
        )
        server = uvicorn.Server(config)

        # 在后台运行
        self._dashboard_task = asyncio.create_task(server.serve())
        logger.info("Dashboard started on http://0.0.0.0:8000")

    async def start(self) -> None:
        """启动所有组件"""
        try:
            # 初始化
            await self.initialize()

            # 写入 PID 文件
            self._write_pid_file()

            # 启动 Dashboard
            await self.start_dashboard()

            # 启动调度器
            self.scheduler.start()
            logger.info("Scheduler started")

            # 注册信号处理器
            self._register_signal_handlers()

            logger.info(f"Application started in {self.mode} mode")

            # 等待关闭信号
            await self._shutdown_event.wait()

        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            raise
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """优雅关闭所有组件"""
        logger.info("Shutting down application...")

        # 1. 关闭调度器
        if self.scheduler:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler shutdown complete")

        # 2. 关闭 Dashboard
        if self._dashboard_task:
            self._dashboard_task.cancel()
            try:
                await self._dashboard_task
            except asyncio.CancelledError:
                pass
            logger.info("Dashboard shutdown complete")

        # 3. 持久化状态
        if self.state:
            await self.state.persist()
            logger.info("State persisted")

        # 4. 删除 PID 文件
        self._remove_pid_file()

        logger.info("Application shutdown complete")

    def _register_signal_handlers(self) -> None:
        """注册信号处理器"""
        loop = asyncio.get_event_loop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self._handle_signal(s))
            )

    async def _handle_signal(self, sig: signal.Signals) -> None:
        """处理关闭信号"""
        logger.info(f"Received signal {sig.name}, initiating shutdown...")
        self._shutdown_event.set()

    def _write_pid_file(self) -> None:
        """写入 PID 文件"""
        pid_file = Path(".bot.pid")
        pid_file.write_text(str(sys.getpid()))
        logger.debug(f"PID file written: {sys.getpid()}")

    def _remove_pid_file(self) -> None:
        """删除 PID 文件"""
        pid_file = Path(".bot.pid")
        if pid_file.exists():
            pid_file.unlink()
            logger.debug("PID file removed")


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Polymarket Trader - LLM-powered automated trading system"
    )
    parser.add_argument(
        "--mode",
        choices=["paper", "live"],
        default="paper",
        help="Trading mode: paper (simulation) or live (real trading)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configuration file"
    )
    return parser.parse_args()


async def async_main() -> None:
    """异步主入口"""
    args = parse_args()

    app = Application(mode=args.mode, config_path=args.config)
    await app.start()


def main() -> None:
    """同步入口点 (供命令行调用)"""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### pyproject.toml Updates

```toml
# 添加命令行入口点
[project.scripts]
polymarket-trader = "src.main:main"
```

---

## Dependencies

### Python Packages
- 已有: `asyncio`, `argparse`, `signal`, `sys`, `pathlib`
- 已有: `uvicorn` (用于 FastAPI 服务器)

### Internal Dependencies
- `src/config.py` - 配置管理
- `src/utils/logger.py` - 日志系统
- `src/storage/database.py` - 数据库初始化
- `src/core/state.py` - 状态管理
- `src/core/scheduler.py` - 调度器
- `src/dashboard/app.py` - FastAPI 应用

---

## Test Cases

### Test File: `tests/test_main.py`

```python
import pytest
import asyncio
import signal
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
import sys

from src.main import Application, parse_args, main


class TestParseArgs:
    """测试命令行参数解析"""

    def test_default_args(self):
        """测试默认参数"""
        with patch.object(sys, 'argv', ['main.py']):
            args = parse_args()
            assert args.mode == "paper"
            assert args.config is None

    def test_live_mode(self):
        """测试 live 模式参数"""
        with patch.object(sys, 'argv', ['main.py', '--mode', 'live']):
            args = parse_args()
            assert args.mode == "live"

    def test_custom_config(self):
        """测试自定义配置文件"""
        with patch.object(sys, 'argv', ['main.py', '--config', '/path/to/config.env']):
            args = parse_args()
            assert args.config == "/path/to/config.env"


class TestApplication:
    """测试 Application 类"""

    @pytest.fixture
    def app(self):
        """创建应用实例"""
        return Application(mode="paper")

    def test_initialization(self, app):
        """测试初始化"""
        assert app.mode == "paper"
        assert app.state is None
        assert app.scheduler is None
        assert app._shutdown_event.is_set() is False

    @pytest.mark.asyncio
    async def test_initialize(self, app):
        """测试初始化流程"""
        with patch('src.main.init_db', new_callable=AsyncMock) as mock_init_db, \
             patch('src.main.ThreadSafeState') as mock_state, \
             patch('src.main.Scheduler') as mock_scheduler:

            await app.initialize()

            mock_init_db.assert_called_once()
            assert app.state is not None
            assert app.scheduler is not None

    @pytest.mark.asyncio
    async def test_shutdown(self, app):
        """测试关闭流程"""
        app.scheduler = MagicMock()
        app.scheduler.shutdown = Mock()
        app.state = MagicMock()
        app.state.persist = AsyncMock()
        app._dashboard_task = None

        await app.shutdown()

        app.scheduler.shutdown.assert_called_once()
        app.state.persist.assert_called_once()

    def test_write_pid_file(self, app, tmp_path):
        """测试 PID 文件写入"""
        with patch('src.main.Path') as mock_path:
            mock_pid_file = MagicMock()
            mock_path.return_value = mock_pid_file

            app._write_pid_file()

            mock_pid_file.write_text.assert_called_once()

    def test_remove_pid_file(self, app):
        """测试 PID 文件删除"""
        with patch('src.main.Path') as mock_path:
            mock_pid_file = MagicMock()
            mock_pid_file.exists.return_value = True
            mock_path.return_value = mock_pid_file

            app._remove_pid_file()

            mock_pid_file.unlink.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_signal(self, app):
        """测试信号处理"""
        app._shutdown_event.set = Mock()

        await app._handle_signal(signal.SIGTERM)

        app._shutdown_event.set.assert_called_once()


class TestMain:
    """测试主入口"""

    def test_main_entry_point(self):
        """测试主入口点"""
        with patch('src.main.asyncio.run') as mock_run:
            main()
            mock_run.assert_called_once()

    def test_main_keyboard_interrupt(self):
        """测试键盘中断处理"""
        with patch('src.main.asyncio.run', side_effect=KeyboardInterrupt):
            # 不应该抛出异常
            main()
```

---

## Implementation Notes

1. **异步设计**: 使用 `asyncio` 作为主循环，支持异步组件
2. **信号处理**: 注册 SIGTERM 和 SIGINT 信号处理器实现优雅关闭
3. **PID 文件**: 防止重复启动，便于进程管理
4. **模块化**: 将启动逻辑封装在 `Application` 类中，便于测试和维护
5. **命令行入口**: 通过 `pyproject.toml` 配置 `polymarket-trader` 命令
6. **后台服务**: Dashboard (FastAPI) 作为后台任务运行

---

## Definition of Done

- [ ] `src/main.py` 实现完成
- [ ] `pyproject.toml` 添加命令行入口点
- [ ] `tests/test_main.py` 测试通过
- [ ] 支持命令行参数 (`--mode`, `--config`)
- [ ] 优雅关闭处理正确
- [ ] PID 文件管理正常
- [ ] 代码通过 `pytest`、`mypy src/` 和 `ruff check .`
- [ ] 代码覆盖率 >= 90%

---

## Next Story

完成后继续: **Story 8.4: 自动恢复机制** - 实现系统崩溃后自动恢复到之前状态的功能
