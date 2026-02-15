# Story 2.2: 市场数据获取与存储

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **用户**,
I want **系统能够自动获取 Polymarket 市场数据并存储到数据库**,
So that **我有本地市场数据可供分析和筛选**.

## Acceptance Criteria

**Given** Polymarket API 客户端已实现 (Story 2.1)
**When** 实现市场获取功能
**Then** 调用 PolymarketClient 获取活跃市场
**And** 将市场数据转换为 Market 模型
**And** 存储到 `markets` 表（使用 UPSERT 避免重复）
**And** 记录获取的市场数量到日志
**And** 更新 `system_state` 表记录最后获取时间
**And** 处理 API 错误和空结果
**And** 返回获取的市场数量

## Tasks / Subtasks

- [x] Task 1: 创建市场数据仓库基础结构 (AC: 1)
  - [x] 1.1 创建 `src/storage/repositories/__init__.py`
  - [x] 1.2 创建 `src/storage/repositories/market_repo.py`
  - [x] 1.3 实现 `MarketRepository` 类
  - [x] 1.4 添加数据库连接依赖注入
  - [x] 1.5 添加类型注解 (Python 3.10+ 语法)

- [x] Task 2: 实现市场存储方法 (AC: 1, 2, 3)
  - [x] 2.1 实现 `save_market(market: Market)` - 保存单个市场
  - [x] 2.2 实现 `save_markets(markets: list[Market])` - 批量保存市场
  - [x] 2.3 使用 UPSERT (INSERT OR REPLACE) 避免重复
  - [x] 2.4 实现 `update_timestamp(key: str)` - 更新系统状态时间戳
  - [x] 2.5 使用 ISO 8601 格式存储日期时间

- [x] Task 3: 实现市场数据获取服务 (AC: 1, 2)
  - [x] 3.1 创建 `src/storage/market_fetcher.py`
  - [x] 3.2 实现 `MarketFetcher` 类
  - [x] 3.3 注入 PolymarketClient 和 MarketRepository 依赖
  - [x] 3.4 实现 `fetch_and_store_markets()` 方法
  - [x] 3.5 优先使用 Gamma API (`get_active_markets()`)
  - [x] 3.6 将 GammaMarket 转换为 Market 模型
  - [x] 3.7 调用仓库保存数据

- [x] Task 4: 集成重试机制和错误处理 (AC: 6)
  - [x] 4.1 为 `fetch_and_store_markets()` 添加 @retry 装饰器
  - [x] 4.2 处理 NetworkError, RateLimitError, RequestTimeoutError
  - [x] 4.3 处理空结果场景 (返回 0 个市场)
  - [x] 4.4 处理数据库写入错误
  - [x] 4.5 记录错误日志

- [x] Task 5: 实现日志记录 (AC: 4)
  - [x] 5.1 使用 get_logger 获取 logger 实例
  - [x] 5.2 记录获取开始/结束日志
  - [x] 5.3 使用数据 Emoji (📊) 和网络 Emoji (🌐)
  - [x] 5.4 记录获取的市场数量
  - [x] 5.5 记录跳过/失败的市场数量

- [x] Task 6: 更新模块导出 (AC: All)
  - [x] 6.1 更新 `src/storage/__init__.py` 导出 MarketFetcher
  - [x] 6.2 更新 `src/storage/repositories/__init__.py` 导出 MarketRepository
  - [x] 6.3 添加模块级 docstring

- [x] Task 7: 编写测试 (AC: All)
  - [x] 7.1 创建 `tests/test_storage/__init__.py`
  - [x] 7.2 创建 `tests/test_storage/test_repositories/__init__.py`
  - [x] 7.3 创建 `tests/test_storage/test_repositories/test_market_repo.py`
  - [x] 7.4 测试 save_market() 成功和失败场景
  - [x] 7.5 测试 save_markets() 批量保存
  - [x] 7.6 测试 UPSERT 行为 (重复 ID 不报错)
  - [x] 7.7 创建 `tests/test_storage/test_market_fetcher.py`
  - [x] 7.8 测试 fetch_and_store_markets() 成功场景
  - [x] 7.9 测试 API 错误处理
  - [x] 7.10 测试空结果处理
  - [x] 7.11 使用 Mock 避免真实 API 调用

- [x] Task 8: 代码质量检查 (AC: All)
  - [x] 8.1 运行 `mypy src/storage/` 无错误
  - [x] 8.2 运行 `black --check src/storage/` 通过
  - [x] 8.3 运行 `isort --check src/storage/` 通过
  - [x] 8.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md#Data Architecture]

**数据库操作 (aiosqlite):**

```python
import aiosqlite
from src.storage.database import get_connection

async def save_market(market: Market) -> None:
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT OR REPLACE INTO markets (
                id, title, description, category,
                yes_price, no_price, liquidity, deadline,
                resolution_status, resolution_outcome,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                market.id,
                market.title,
                market.description,
                market.category.value if market.category else None,
                market.yes_price,
                market.no_price,
                market.liquidity,
                market.deadline.isoformat() if market.deadline else None,
                market.resolution_status,
                market.resolution_outcome,
                market.created_at.isoformat() if market.created_at else None,
                datetime.utcnow().isoformat(),
            ),
        )
        await conn.commit()
```

**重要提示:**
- 使用 `INSERT OR REPLACE` 实现 UPSERT
- 日期时间使用 ISO 8601 格式存储
- 更新 `updated_at` 字段为当前时间
- 保留 `created_at` 如果已存在

### 现有 PolymarketClient [Source: src/api/polymarket.py]

**推荐使用 Gamma API (带筛选):**

```python
from src.api import PolymarketClient, GammaMarket

client = PolymarketClient()

# 获取活跃市场 (推荐) - 带筛选和排序
active_markets = client.get_active_markets(
    limit=100,
    min_liquidity=10000,  # 可选：最小流动性
    order_by="volume24hr",
    ascending=False,
)

# 转换为 Market 模型
for gamma_market in active_markets:
    market = gamma_market.to_market()
    # 存储到数据库...
```

**GammaMarket 字段:**

| 字段 | 类型 | 描述 |
|------|------|------|
| condition_id | str | 市场 ID |
| question | str | 市场问题/标题 |
| slug | str | URL slug |
| active | bool | 是否活跃 |
| closed | bool | 是否已关闭 |
| accepting_orders | bool | 是否接受订单 |
| enable_order_book | bool | 是否启用订单簿 |
| clob_token_ids | list[str] | Token IDs (用于交易) |
| volume_24h | float \| None | 24 小时交易量 |
| liquidity | float \| None | 流动性 |
| category | str \| None | 类别 |
| end_date | datetime \| None | 截止日期 |

**备选: CLOB API (无筛选):**

```python
# 获取所有市场 (无筛选)
markets = client.get_markets()
```

### 现有数据库 Schema [Source: src/storage/database.py]

**markets 表:**

```sql
CREATE TABLE markets (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    yes_price REAL,
    no_price REAL,
    liquidity REAL,
    deadline DATETIME,
    resolution_status TEXT,
    resolution_outcome TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**system_state 表:**

```sql
CREATE TABLE system_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**更新 system_state 示例:**

```python
async def update_last_fetch_time(conn: aiosqlite.Connection) -> None:
    await conn.execute(
        """
        INSERT OR REPLACE INTO system_state (key, value, updated_at)
        VALUES ('last_market_fetch', ?, ?)
        """,
        (datetime.utcnow().isoformat(), datetime.utcnow().isoformat()),
    )
    await conn.commit()
```

### 现有异常类 [Source: src/exceptions.py]

```python
from src.exceptions import (
    DatabaseError,
    NetworkError,
    RateLimitError,
    RequestTimeoutError,
)

# 数据库错误
try:
    await conn.execute(...)
except aiosqlite.Error as e:
    raise DatabaseError(
        message="Failed to save market",
        operation="save_market",
        original_exception=e,
    )
```

### 重试装饰器 [Source: src/utils/retry.py]

```python
from src.utils.retry import retry
from src.exceptions import NetworkError, RateLimitError, RequestTimeoutError

class MarketFetcher:
    @retry(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        exceptions=(NetworkError, RateLimitError, RequestTimeoutError)
    )
    async def fetch_and_store_markets(self) -> int:
        """获取并存储市场数据，带重试机制。"""
        ...
```

### 日志系统 [Source: src/utils/logger.py]

```python
from src.utils.logger import get_logger, OPERATION_EMOJIS

logger = get_logger(__name__)

# 使用数据 Emoji 和网络 Emoji
logger.info(f"{OPERATION_EMOJIS['network']} Fetching markets from Polymarket...")
logger.info(f"{OPERATION_EMOJIS['data']} ✅ Stored {count} markets")
logger.warning(f"{OPERATION_EMOJIS['data']} ⚠️ Skipped {skipped} invalid markets")
logger.error(f"{OPERATION_EMOJIS['data']} ❌ Failed to save market: {error}")
```

**Emoji 参考:**

| 操作 | Emoji |
|------|-------|
| 网络 | 🌐 |
| 数据 | 📊 |
| 成功 | ✅ |
| 警告 | ⚠️ |
| 错误 | ❌ |

### 类型注解规范 [Source: project-context.md#Python]

```python
# ✅ 正确 - Python 3.10+ 语法
from __future__ import annotations

class MarketRepository:
    async def save_market(self, market: Market) -> None:
        ...

    async def save_markets(self, markets: list[Market]) -> int:
        ...

    async def get_market(self, market_id: str) -> Market | None:
        ...

# ❌ 错误 - 不要使用旧语法
from typing import Optional, List

def save_markets(self, markets: List[Market]) -> Optional[int]:  # 错误
    ...
```

### 项目结构 [Source: architecture.md#Project Structure]

**新增文件:**
```
src/storage/
├── __init__.py           # 更新: 导出 MarketFetcher
├── database.py           # 已存在: 数据库管理
├── market_fetcher.py     # 新增: 市场数据获取服务
└── repositories/
    ├── __init__.py       # 新增: 仓库模块
    └── market_repo.py    # 新增: 市场数据仓库

tests/test_storage/
├── __init__.py           # 新增
├── test_repositories/
│   ├── __init__.py       # 新增
│   └── test_market_repo.py  # 新增: MarketRepository 测试
└── test_market_fetcher.py   # 新增: MarketFetcher 测试
```

### 实现模板

**MarketRepository:**

```python
# src/storage/repositories/market_repo.py
"""Market data repository for database operations.

This module provides CRUD operations for market data using
the repository pattern.
"""

from __future__ import annotations

__all__ = ["MarketRepository"]

from datetime import datetime
from typing import Any

import aiosqlite

from src.exceptions import DatabaseError
from src.models import Market
from src.storage.database import get_connection
from src.utils.logger import OPERATION_EMOJIS, get_logger

logger = get_logger(__name__)


class MarketRepository:
    """Repository for market data operations.

    Provides methods to save, retrieve, and manage market data
    in the SQLite database.

    Example:
        >>> repo = MarketRepository()
        >>> market = Market(id="test", title="Test Market")
        >>> await repo.save_market(market)
    """

    async def save_market(self, market: Market) -> None:
        """Save a single market to the database.

        Uses UPSERT (INSERT OR REPLACE) to handle duplicates.

        Args:
            market: Market model to save

        Raises:
            DatabaseError: If save operation fails
        """
        ...

    async def save_markets(self, markets: list[Market]) -> int:
        """Save multiple markets to the database.

        Args:
            markets: List of Market models to save

        Returns:
            Number of markets saved

        Raises:
            DatabaseError: If save operation fails
        """
        ...

    async def update_last_fetch_time(self) -> None:
        """Update the last market fetch timestamp in system_state."""
        ...
```

**MarketFetcher:**

```python
# src/storage/market_fetcher.py
"""Market data fetching and storage service.

This module orchestrates fetching market data from Polymarket
and storing it in the local database.
"""

from __future__ import annotations

__all__ = ["MarketFetcher"]

from src.api import PolymarketClient
from src.exceptions import NetworkError, RateLimitError, RequestTimeoutError
from src.storage.repositories.market_repo import MarketRepository
from src.utils.logger import OPERATION_EMOJIS, get_logger
from src.utils.retry import retry

logger = get_logger(__name__)


class MarketFetcher:
    """Service for fetching and storing market data.

    Orchestrates the flow of data from Polymarket API to local storage.

    Attributes:
        _client: Polymarket API client
        _repo: Market data repository

    Example:
        >>> fetcher = MarketFetcher()
        >>> count = await fetcher.fetch_and_store_markets()
        >>> print(f"Stored {count} markets")
    """

    def __init__(
        self,
        client: PolymarketClient | None = None,
        repo: MarketRepository | None = None,
    ) -> None:
        """Initialize the market fetcher.

        Args:
            client: PolymarketClient instance (optional, creates new if None)
            repo: MarketRepository instance (optional, creates new if None)
        """
        self._client = client or PolymarketClient()
        self._repo = repo or MarketRepository()

    @retry(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        exceptions=(NetworkError, RateLimitError, RequestTimeoutError),
    )
    async def fetch_and_store_markets(
        self,
        limit: int = 100,
        min_liquidity: float | None = None,
    ) -> int:
        """Fetch markets from Polymarket and store in database.

        Uses Gamma API for filtered, active markets.

        Args:
            limit: Maximum number of markets to fetch (default: 100)
            min_liquidity: Minimum liquidity filter (default: None)

        Returns:
            Number of markets stored

        Raises:
            NetworkError: If API request fails after retries
            RateLimitError: If rate limit is exceeded
            RequestTimeoutError: If request times out
        """
        ...
```

### 测试策略

```python
# tests/test_storage/test_repositories/test_market_repo.py
"""Tests for MarketRepository."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from src.models import Market, MarketCategory
from src.storage.repositories.market_repo import MarketRepository
from src.exceptions import DatabaseError


class TestMarketRepository:
    """Tests for MarketRepository class."""

    @pytest.fixture
    def repo(self) -> MarketRepository:
        """Create a MarketRepository instance for testing."""
        return MarketRepository()

    @pytest.fixture
    def sample_market(self) -> Market:
        """Create a sample Market for testing."""
        return Market(
            id="test-market-123",
            title="Will X happen?",
            category=MarketCategory.POLITICS,
            yes_price=0.65,
            no_price=0.35,
            liquidity=50000.0,
        )

    @pytest.mark.asyncio
    async def test_save_market_success(
        self, repo: MarketRepository, sample_market: Market
    ) -> None:
        """Test successful market save."""
        with patch("src.storage.repositories.market_repo.get_connection") as mock_conn:
            mock_context = AsyncMock()
            mock_conn.return_value.__aenter__.return_value = mock_context

            await repo.save_market(sample_market)

            # Verify execute was called with correct SQL
            mock_context.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_markets_batch(
        self, repo: MarketRepository, sample_market: Market
    ) -> None:
        """Test batch save of multiple markets."""
        markets = [sample_market, sample_market.model_copy(update={"id": "test-2"})]

        with patch("src.storage.repositories.market_repo.get_connection") as mock_conn:
            mock_context = AsyncMock()
            mock_conn.return_value.__aenter__.return_value = mock_context

            count = await repo.save_markets(markets)

            assert count == 2

    # More tests...
```

### 前一个故事学习 [Source: 2-1-polymarket-api-client.md]

**从 Story 2.1 学到的模式:**

1. **使用 `from __future__ import annotations`** - 支持 Python 3.10+ 类型语法
2. **类型注解使用 `str | None`** - 而非 `Optional[str]`
3. **类型注解使用 `list[Type]`** - 而非 `List[Type]`
4. **使用 @retry 装饰器** - 为网络操作添加重试机制
5. **使用 OPERATION_EMOJIS** - 标准化日志 Emoji
6. **GammaMarket.to_market()** - 转换为 Market 模型
7. **优先使用 Gamma API** - 获取活跃市场

**Gamma API 优势:**
- 支持筛选 (min_liquidity, min_volume_24h)
- 支持排序 (order_by, ascending)
- 返回活跃市场 (active=true, closed=false)
- 包含更多字段 (volume_24h, clob_token_ids)

### 依赖关系

**本故事依赖:**
- Story 1.2: 配置管理系统
- Story 1.3: 日志系统 (get_logger, OPERATION_EMOJIS)
- Story 1.4: 自定义异常体系 (DatabaseError, NetworkError, etc.)
- Story 1.5: 重试机制 (@retry 装饰器)
- Story 1.6: 数据库初始化 (markets, system_state 表)
- Story 1.7: Pydantic 数据模型 (Market, MarketCategory)
- Story 2.1: Polymarket API 客户端 (PolymarketClient, GammaMarket)

**后续故事依赖本故事:**
- Story 2.3: 市场筛选规则引擎 (需要本地市场数据)
- Story 2.4: 市场数据仓库 (将扩展本故事的 MarketRepository)
- Story 3.3: LLM 分析引擎 (需要市场数据)

### 实现注意事项

**关键点:**

1. **UPSERT 逻辑**: 使用 `INSERT OR REPLACE` 确保重复数据不报错
2. **时间戳更新**: 每次保存更新 `updated_at` 字段
3. **系统状态**: 记录 `last_market_fetch` 到 `system_state` 表
4. **错误隔离**: 单个市场保存失败不应影响其他市场
5. **日志详细**: 记录成功、跳过、失败的数量

**性能考虑:**

1. **批量保存**: 使用事务批量保存提高效率
2. **连接管理**: 使用 `get_connection()` 上下文管理器
3. **内存优化**: 大量市场时分批处理

### References

- [Source: architecture.md#Data Architecture] - 数据库操作模式
- [Source: architecture.md#API & Communication Patterns] - 错误处理
- [Source: architecture.md#Logging Patterns] - 日志格式和 Emoji
- [Source: src/api/polymarket.py] - PolymarketClient 和 GammaMarket
- [Source: src/storage/database.py] - 数据库管理
- [Source: src/models/market.py] - Market 模型
- [Source: src/exceptions.py] - 异常类定义
- [Source: src/utils/retry.py] - 重试装饰器
- [Source: src/utils/logger.py] - 日志系统
- [Source: epics.md#Story 2.2] - 原始 Story 定义
- [Source: 2-1-polymarket-api-client.md] - 前一个故事学习

## Dev Agent Record

### Agent Model Used

GLM-5 (via Happy)

### Debug Log References

无

### Completion Notes List

- ✅ 实现了 MarketRepository 类，提供市场数据的 CRUD 操作
- ✅ 使用 INSERT OR REPLACE 实现 UPSERT 逻辑，避免重复数据报错
- ✅ 实现了 MarketFetcher 服务，协调 API 获取和数据库存储
- ✅ 集成了 @retry 装饰器，支持网络错误重试
- ✅ 使用 OPERATION_EMOJIS 标准化日志输出
- ✅ 所有 384 个测试通过，无回归
- ✅ mypy、black、isort 代码质量检查通过

### File List

**新增文件:**
- `src/storage/market_fetcher.py` - 市场数据获取服务
- `src/storage/repositories/market_repo.py` - 市场数据仓库
- `tests/test_storage/test_repositories/__init__.py` - 测试模块初始化
- `tests/test_storage/test_repositories/test_market_repo.py` - MarketRepository 测试
- `tests/test_storage/test_market_fetcher.py` - MarketFetcher 测试

**修改文件:**
- `src/storage/__init__.py` - 导出 MarketFetcher 和 MarketRepository
- `src/storage/repositories/__init__.py` - 导出 MarketRepository
- `src/storage/database.py` - SQL 字符串格式化 (非功能性变更)

## Change Log

- 2026-02-16: Code Review 修复 (Story 2.2)
  - 修复 SQL 注入风险: `get_all_markets()` 使用参数化查询
  - 修复异常包装: 意外错误使用 BotError 而非 NetworkError
  - 添加缺失的 RequestTimeoutError 测试用例
  - 修复 MockGammaMarket.to_market() 与实际实现一致性
- 2026-02-15: 实现市场数据获取与存储功能 (Story 2.2)
  - 创建 MarketRepository 和 MarketFetcher
  - 集成重试机制和错误处理
  - 添加完整测试覆盖 (26 个新测试)
