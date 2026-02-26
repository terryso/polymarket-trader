---
title: '持仓数据源重构 - Polymarket 作为单一数据源'
slug: 'position-single-source-truth'
created: '2026-02-26'
status: 'completed'

## Review Notes
- Adversarial review completed
- Findings: 10 total, 7 fixed, 3 skipped (noise/info)
- Resolution approach: auto-fix
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - Python 3.10+
  - FastAPI >=0.109.0
  - Pydantic v2
  - aiosqlite >=0.19.0
  - py-clob-client >=0.1.0
  - pytest + pytest-asyncio
files_to_modify:
  - src/trading/position_sync.py
  - src/trading/position_manager.py
  - src/trading/live_trading.py
  - src/trading/paper_trading.py
  - src/api/polymarket.py
  - src/dashboard/routes/positions.py
  - src/core/tasks.py
  - src/config.py
code_patterns:
  - Repository pattern for data access
  - Service layer for business logic
  - Async/await for all I/O
  - Pydantic v2 models with model_config
  - Dependency injection via constructors
  - Type annotations (mypy strict mode)
test_patterns:
  - Mirror src/ structure in tests/
  - pytest fixtures in conftest.py
  - AsyncMock for async operations
  - @pytest.mark.asyncio for async tests
  - Mock Polymarket API responses
---

# Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源

**Created:** 2026-02-26

## Overview

### Problem Statement

当前系统存在两个独立的持仓数据源（本地数据库和 Polymarket API），经常出现数据不一致的情况。用户需要手动触发同步操作来保持数据一致，这是一个糟糕的设计。

具体问题：
- 本地数据库和 Polymarket 链上持仓经常不一致
- 需要手动/定期执行"同步"操作
- 交易执行后本地创建持仓，但 API 调用可能失败，导致状态不一致
- 用户在其他平台（网页/App）操作后本地无法感知

### Solution

将 Polymarket API 作为持仓数据的**单一数据源 (Single Source of Truth)**，本地数据库从"数据源"转变为"缓存层"：

1. **移除"同步"概念** - `PositionSyncService` 改为 `PositionCacheService`，不再有"同步"操作
2. **关键操作前获取最新数据** - 交易/卖出前从 API 获取当前持仓状态
3. **本地数据库改变用途** - 作为缓存用于展示（带 TTL），存储历史记录

```
推荐设计:
┌─────────────┐    读取/刷新   ┌───────────────┐
│  本地缓存    │ ←─────────── │  Polymarket   │
│  (Cache)    │              │ (Source of    │
└─────────────┘              │   Truth)      │
      ↓                      └───────────────┘
   仅用于展示                      ↓
                              交易决策
```

### Scope

**In Scope:**
- 重构持仓获取逻辑（`PositionManager`, `PositionSyncService`）
- 改进交易执行流程（`LiveTradingExecutor`, `PaperTradingExecutor`）
- 更新 Dashboard 持仓展示（从缓存读取，带 TTL）
- 更新相关测试
- 添加可观测性（日志、缓存状态）

**Out of Scope:**
- 交易算法/策略的改动
- 前端 UI 的大改动
- 其他非持仓相关的模块（如通知、风险管理）

## Context for Development

### Codebase Patterns

**架构模式：**
- Repository pattern for data access (`PositionRepository`)
- Service layer for business logic (`PositionManager`, `PositionSyncService`)
- Async/await for all I/O operations
- Pydantic v2 models with `model_config = ConfigDict(...)`
- Dependency injection through constructors
- Type annotations required (mypy strict mode)

**数据流现状：**
```
Polymarket API (get_balances)
         ↓
PositionSyncService.sync_positions()  ← 手动/定时触发
         ↓
PositionRepository (CRUD操作)
         ↓
PositionManager (业务逻辑处理)
         ↓
Dashboard API (前端展示)
```

### Files to Reference

| File | Purpose | 改动类型 |
| ---- | ------- | -------- |
| `src/trading/position_sync.py` | 当前同步服务，362行 | **重构** → PositionCacheService |
| `src/trading/position_manager.py` | 持仓管理，567行 | **重构** - 添加 API 获取方法 |
| `src/trading/live_trading.py` | Live 交易执行器，644行 | **修改** - 交易前验证持仓 |
| `src/trading/paper_trading.py` | Paper 交易执行器 | **修改** - 保持接口一致 |
| `src/api/polymarket.py` | API 客户端，~500行 | **保留** - 已有 get_balances |
| `src/dashboard/routes/positions.py` | 持仓 API 路由，447行 | **修改** - 移除 sync 端点或改变语义 |
| `src/core/tasks.py` | 定时任务管理 | **修改** - 添加缓存刷新任务 |
| `src/config.py` | 配置管理 | **修改** - 添加缓存 TTL 配置 |

### Technical Decisions

**1. 持仓缓存策略：**
- 缓存 TTL: 60 秒（可配置，通过 `POSITION_CACHE_TTL` 环境变量）
- 最小刷新间隔: 10 秒（防止频繁刷新，`POSITION_CACHE_MIN_INTERVAL`）
- Dashboard 读取时：如果缓存过期，从 API 刷新
- 交易执行时：始终从 API 获取最新数据（不使用缓存）

**2. API 调用位置与职责划分：**
- `PositionCacheService`: 缓存管理，Dashboard 数据获取入口
- `PositionManager`: 交易相关操作，提供 `fetch_positions_from_api()` 用于交易决策
- 调用者应根据场景选择：展示用 CacheService，交易决策用 Manager

**3. 本地数据库保留用途：**
- 缓存持仓数据（使用 system_state 表存储全局 `cache_updated_at` 时间戳）
- 存储已关闭的持仓历史记录
- 存储 PnL 计算结果

**4. 缓存状态枚举：**
```python
class CacheFreshness(str, Enum):
    FRESH = "fresh"      # 缓存有效
    STALE = "stale"      # 缓存过期但 API 失败，使用旧数据
    EXPIRED = "expired"  # 缓存过期且无数据
```

**5. Paper 模式处理：**
- `fetch_positions_from_api()` 在 Paper 模式下返回本地数据库持仓
- `PositionCacheService` 在 Paper 模式下直接使用本地数据，不调用 API
- 架构保持一致，便于理解

**6. 并发控制：**
- 使用 `_refreshing` 标志防止并发刷新
- 交易完成后调用 `cache_service.mark_stale()` 标记缓存需要刷新

**7. 移除/重命名的概念：**
- `PositionSyncService` → `PositionCacheService`
- `sync_positions()` → `refresh_cache()`
- `get_sync_status()` → `get_cache_status()`
- `/api/positions/sync` → `/api/positions/refresh`
- `last_position_sync` → `cache_updated_at`

## Implementation Plan

### Tasks

**阶段 1: 基础设施 (配置 + 数据模型)**

- [x] Task 1.1: 添加缓存配置
  - File: `src/config.py`
  - Action: 在 Settings 类中添加配置项
    ```python
    position_cache_ttl: int = Field(default=60, description="Position cache TTL in seconds")
    position_cache_min_interval: int = Field(default=10, description="Minimum interval between cache refreshes")
    ```
  - Notes: 可通过 `POSITION_CACHE_TTL` 和 `POSITION_CACHE_MIN_INTERVAL` 环境变量覆盖

- [x] Task 1.2: 添加缓存状态枚举
  - File: `src/models/position.py` 或新建 `src/models/cache.py`
  - Action: 添加 `CacheFreshness` 枚举
    ```python
    class CacheFreshness(str, Enum):
        FRESH = "fresh"
        STALE = "stale"
        EXPIRED = "expired"
    ```
  - Notes: 用于响应中标记缓存状态

- [x] Task 1.3: 重命名 PositionSyncService 为 PositionCacheService
  - File: `src/trading/position_sync.py`
  - Action:
    1. 重命名类 `PositionSyncService` → `PositionCacheService`
    2. 重命名 `PositionSyncResult` → `CacheRefreshResult`
    3. 重命名 `PositionSyncStatus` → `CacheStatus`
    4. 更新 `__all__` 导出
    5. 添加 deprecated alias 保持向后兼容
  - Notes:
    ```python
    # Deprecated aliases for backward compatibility
    PositionSyncService = PositionCacheService
    PositionSyncResult = CacheRefreshResult
    PositionSyncStatus = CacheStatus
    ```

**阶段 2: 核心缓存服务重构**

- [x] Task 2.1: 重构 sync_positions 为 refresh_cache
  - File: `src/trading/position_sync.py`
  - Action:
    1. 重命名方法 `sync_positions()` → `refresh_cache()`
    2. 修改方法逻辑：不再比较本地数据，而是直接用 API 数据覆盖缓存
    3. 更新 `cache_updated_at` 时间戳（存储在 system_state 表）
    4. 添加最小刷新间隔检查（使用 `position_cache_min_interval`）
    5. 移除 "sync" 相关的日志消息，改为 "refresh/cache"
  - Notes: Paper 模式下使用本地数据，不调用 API

- [x] Task 2.2: 添加缓存读取方法
  - File: `src/trading/position_sync.py`
  - Action: 在 `PositionCacheService` 中添加新方法
    ```python
    async def get_positions(
        self,
        force_refresh: bool = False
    ) -> tuple[list[Position], CacheFreshness]:
        """获取持仓（带缓存）。

        Returns:
            tuple of (positions, freshness) - freshness 指示缓存状态
        """
    ```
  - Notes: 需要检查 `cache_updated_at` 与当前时间比较

- [x] Task 2.3: 添加 get_cache_status 方法
  - File: `src/trading/position_sync.py`
  - Action: 重命名 `get_sync_status()` → `get_cache_status()`，添加以下字段
    ```python
    @dataclass
    class CacheStatus:
        cache_updated_at: datetime | None
        cache_age_seconds: int
        cache_freshness: CacheFreshness
        is_refreshing: bool
        can_refresh: bool
        last_error: str | None
        total_positions: int
    ```

- [x] Task 2.4: 添加 mark_stale 方法
  - File: `src/trading/position_sync.py`
  - Action: 添加方法用于交易完成后标记缓存需要刷新
    ```python
    async def mark_stale(self) -> None:
        """标记缓存为过期，下次读取时会刷新。"""
    ```
  - Notes: 交易执行器在完成交易后调用此方法

**阶段 3: PositionManager 重构**

- [x] Task 3.1: 添加 fetch_positions_from_api 方法
  - File: `src/trading/position_manager.py`
  - Action: 在 `PositionManager` 中添加新方法
    ```python
    async def fetch_positions_from_api(self) -> list[Position]:
        """直接从 Polymarket API 获取持仓（不使用缓存）。

        Paper 模式下返回本地数据库持仓。
        用于交易决策。
        """
    ```
  - Notes: 需要注入 `PolymarketClient`；Paper 模式下返回本地数据

- [x] Task 3.2: 添加 get_position_by_market_from_api 方法
  - File: `src/trading/position_manager.py`
  - Action: 添加新方法，从 API 获取特定市场的持仓
    ```python
    async def get_position_by_market_from_api(self, market_id: str) -> Position | None:
        """从 API 获取特定市场的持仓（不使用缓存）。

        Paper 模式下查询本地数据库。
        """
    ```
  - Depends on: Task 3.1

**阶段 4: 交易执行器修改**

- [x] Task 4.1: LiveTradingExecutor 交易前验证持仓
  - File: `src/trading/live_trading.py`
  - Action: 修改 `execute_trade()` 方法
    1. 在执行交易前，调用 `position_manager.get_position_by_market_from_api(market.id)`
    2. 如果 API 返回已有持仓，跳过交易（而不是只检查本地数据库）
    3. 更新日志消息
    4. 交易成功后调用 `cache_service.mark_stale()`
  - Depends on: Task 3.2
  - Notes: 保持现有的错误处理逻辑

- [x] Task 4.2: LiveTradingExecutor 卖出前验证持仓
  - File: `src/trading/live_trading.py`
  - Action: 修改 `sell_position()` 方法
    1. 在执行卖出前，从 API 获取最新 shares 数量
    2. 使用 API 返回的 shares 而不是本地数据库的值
    3. 卖出成功后调用 `cache_service.mark_stale()`
  - Depends on: Task 3.2
  - Notes: 确保卖出数量不超过实际持有量

- [x] Task 4.3: PaperTradingExecutor 保持接口一致
  - File: `src/trading/paper_trading.py`
  - Action:
    1. 添加相同的 `fetch_positions_from_api` 调用点（Paper 模式下使用本地数据）
    2. 确保接口与 LiveTradingExecutor 一致
    3. 交易成功后调用 `cache_service.mark_stale()`
  - Notes: Paper 模式下 `fetch_positions_from_api` 返回本地数据

**阶段 5: Dashboard API 修改**

- [x] Task 5.1: 修改持仓列表 API 使用缓存
  - File: `src/dashboard/routes/positions.py`
  - Action: 修改 `list_positions()` 端点
    1. 使用 `PositionCacheService.get_positions()` 获取数据
    2. 返回响应中包含 `cache_freshness` 字段
    3. 添加 `?force_refresh=true` 查询参数
  - Notes: 响应模型需要添加 `freshness` 字段

- [x] Task 5.2: 重命名同步 API 端点
  - File: `src/dashboard/routes/positions.py`
  - Action:
    1. `POST /api/positions/sync` → `POST /api/positions/refresh`
    2. `GET /api/positions/sync/status` → `GET /api/positions/cache/status`
    3. 更新响应模型字段名（添加 `cache_age_seconds`, `cache_freshness`）
    4. 保留旧端点作为 deprecated（返回 301 或 warning header）
  - Notes: 检查前端是否使用这些端点

- [x] Task 5.3: 更新手动退出逻辑
  - File: `src/dashboard/routes/positions.py`
  - Action: 修改 `manual_exit_position()` 端点
    1. 在退出前从 API 获取最新持仓状态
    2. 确保退出的是真实存在的持仓
    3. 退出成功后调用 `cache_service.mark_stale()`
  - Notes: Live 模式下可能需要调用真正的卖出 API

**阶段 6: 定时任务更新**

- [x] Task 6.1: 添加缓存刷新定时任务（推荐，非可选）
  - File: `src/core/tasks.py`
  - Action: 添加新的定时任务
    ```python
    def register_refresh_position_cache_job(
        scheduler: Scheduler,
        cache_service: PositionCacheService,
        interval_seconds: int = 300  # 默认 5 分钟
    ) -> str:
        """定期刷新持仓缓存，确保数据新鲜度。"""
    ```
  - Notes: 间隔应大于 `position_cache_ttl`，建议 5 分钟

- [x] Task 6.2: 添加启动时缓存预热
  - File: `src/main.py` 或 `src/core/tasks.py`
  - Action: 在应用启动时调用 `cache_service.refresh_cache()`
  - Notes: 使用 `lifespan` 或 `on_event("startup")` 钩子

**阶段 7: 可观测性**

- [x] Task 7.1: 添加缓存日志
  - File: `src/trading/position_sync.py`
  - Action: 在关键操作添加结构化日志
    - 缓存命中/未命中
    - API 调用延迟
    - 刷新成功/失败
  - Notes: 使用现有 logger 格式，添加 emoji

- [x] Task 7.2: 添加缓存指标（可选）
  - File: `src/trading/position_sync.py` 或新建 `src/metrics/`
  - Action: 添加缓存统计
    - `cache_hits_total`
    - `cache_misses_total`
    - `api_call_duration_seconds`
  - Notes: 可通过 `/api/positions/cache/status` 暴露

**阶段 8: 测试更新**

- [x] Task 8.1: 更新 PositionCacheService 测试
  - File: `tests/test_trading/test_position_cache.py`（重命名自 test_position_sync.py）
  - Action:
    1. 重命名测试类和方法
    2. 添加缓存 TTL 相关测试
    3. 添加 `get_positions()` 方法测试
    4. 测试缓存过期逻辑
    5. 测试 `mark_stale()` 方法
    6. 测试最小刷新间隔
  - Notes: 保持现有的 Mock 策略

- [x] Task 8.2: 更新 PositionManager 测试
  - File: `tests/test_trading/test_position_manager.py`
  - Action:
    1. 添加 `fetch_positions_from_api()` 测试
    2. 添加 `get_position_by_market_from_api()` 测试
    3. 测试 Paper 模式下返回本地数据
    4. Mock PolymarketClient
  - Depends on: Task 3.1, Task 3.2
  - Notes: 使用 AsyncMock

- [x] Task 8.3: 更新 LiveTradingExecutor 测试
  - File: `tests/test_trading/test_live_trading.py`（如存在）
  - Action:
    1. 添加交易前 API 验证测试
    2. 添加卖出前 API 验证测试
    3. 测试 API 不可用时的行为
    4. 测试 `mark_stale()` 被调用
  - Depends on: Task 4.1, Task 4.2
  - Notes: 确保测试覆盖错误场景

- [x] Task 8.4: 更新 Dashboard 路由测试
  - File: `tests/test_dashboard/test_routes/test_positions.py`
  - Action:
    1. 更新端点路径测试
    2. 添加缓存刷新测试
    3. 测试 `force_refresh` 参数
    4. 测试 `cache_freshness` 响应字段
  - Notes: 使用 FastAPI TestClient

**阶段 9: 迁移与文档**

- [x] Task 9.1: 检查前端 API 使用
  - Action: 确认前端是否使用 `/api/positions/sync` 端点
  - Notes: 如果使用，需要同步更新前端代码

- [x] Task 9.2: 更新 CLAUDE.md（如需要）
  - File: `CLAUDE.md`
  - Action: 如有相关说明需要更新
  - Notes: 可选

### Acceptance Criteria

**AC-1: 持仓数据一致性**
- [ ] Given 系统在 Live 模式运行，when 用户在 Polymarket 网页上卖出持仓，then 系统在下次获取持仓时（最多 60 秒内）能够正确反映变化
- [ ] Given 系统在 Live 模式运行，when 用户通过 Dashboard 查看持仓，then 显示的持仓与 Polymarket 链上数据一致（允许 60 秒延迟）

**AC-2: 交易执行安全性**
- [ ] Given 用户已在 Polymarket 持有某市场持仓，when 系统尝试买入同一市场，then 交易被跳过（而不是重复买入）
- [ ] Given 用户在 Polymarket 持有 100 shares，when 系统尝试卖出 150 shares，then 卖出被拒绝或只卖出 100 shares

**AC-3: 缓存机制**
- [ ] Given 缓存 TTL 设置为 60 秒，when 用户在 60 秒内多次查看持仓，then 只调用一次 Polymarket API
- [ ] Given 缓存已过期，when 用户查看持仓，then 自动从 API 刷新缓存
- [ ] Given 用户指定 `force_refresh=true`，when 查看持仓，then 强制从 API 刷新（忽略缓存，但受最小刷新间隔限制）
- [ ] Given 用户在 10 秒内连续请求 `force_refresh=true`，when 第二次请求，then 返回缓存数据（受最小刷新间隔保护）

**AC-4: Paper 模式兼容性**
- [ ] Given 系统在 Paper 模式运行，when 用户查看持仓，then 显示本地模拟持仓（不调用真实 API）
- [ ] Given 系统在 Paper 模式运行，when 用户执行交易，then 使用本地持仓数据
- [ ] Given 系统在 Paper 模式运行，when 调用 `fetch_positions_from_api()`，then 返回本地数据库持仓

**AC-5: API 端点更新**
- [ ] Given 客户端调用 `POST /api/positions/refresh`，then 缓存被刷新并返回结果
- [ ] Given 客户端调用 `GET /api/positions/cache/status`，then 返回缓存状态（包括 `cache_updated_at`, `cache_age_seconds`, `cache_freshness`）
- [ ] Given 客户端调用 `POST /api/positions/sync`（旧端点），then 请求被处理并返回 deprecation warning

**AC-6: 向后兼容性**
- [ ] Given 旧代码引用 `PositionSyncService`，then 代码仍能运行（使用 deprecated alias）
- [ ] Given 旧代码调用 `POST /api/positions/sync`，then 请求被重定向到新端点或返回 deprecated 警告

**AC-7: 错误处理**
- [ ] Given Polymarket API 不可用，when 用户查看持仓，then 显示缓存数据并返回 `freshness: "stale"`
- [ ] Given Polymarket API 返回错误，when 系统尝试交易，then 交易被取消并记录错误
- [ ] Given 缓存为空且 API 不可用，when 用户查看持仓，then 返回空列表和 `freshness: "expired"`

**AC-8: 并发安全**
- [ ] Given 两个请求同时触发缓存刷新，when 并发执行，then 只有一个请求实际调用 API
- [ ] Given 交易刚完成，when 用户立即查看持仓，then 显示交易前的缓存数据（直到下次刷新）
- [ ] Given 交易完成后，when 缓存被标记为 stale，then 下次读取时会刷新

**AC-9: 启动行为**
- [ ] Given 系统刚启动，when 启动完成，then 缓存已被预热（后台刷新完成或进行中）
- [ ] Given 系统刚启动且 API 不可用，when 启动完成，then 系统正常运行，缓存为空

## Additional Context

### Dependencies

**外部依赖：**
- `py_clob_client` - Polymarket CLOB API 客户端（已有，用于获取持仓）
- `aiosqlite` - 异步 SQLite 操作（已有）

**内部依赖：**
- `src/config.py` - 添加 `POSITION_CACHE_TTL` 和 `POSITION_CACHE_MIN_INTERVAL` 配置
- `src/exceptions.py` - 可复用现有异常
- `src/models/position.py` - 添加 `CacheFreshness` 枚举

**API 依赖：**
- `PolymarketClient.get_balances()` - 已实现，可直接使用

**前端依赖检查：**
- 需确认前端是否使用 `/api/positions/sync` 端点（Task 9.1）

### Testing Strategy

**单元测试：**
- `test_position_cache.py` - 测试缓存刷新、TTL、get_positions 方法、mark_stale、最小刷新间隔
- `test_position_manager.py` - 测试 API 获取方法、Paper 模式行为
- `test_live_trading.py` - 测试交易前验证逻辑、mark_stale 调用
- `test_positions.py` (routes) - 测试 API 端点、freshness 字段

**集成测试：**
- `test_position_manager_integration.py` - 使用真实数据库测试缓存持久化
- 可选：使用 Polymarket 测试环境（如有）进行端到端测试

**手动测试步骤：**
1. 启动系统，确认 Dashboard 显示正确持仓（缓存预热）
2. 在 Polymarket 网页上执行买入/卖出
3. 等待 60 秒或手动刷新，确认 Dashboard 更新
4. 尝试买入已有持仓的市场，确认被跳过
5. 切换到 Paper 模式，确认使用本地数据
6. 快速连续点击刷新，确认 API 调用被限流
7. 断开网络，确认显示缓存数据并标记 stale

### Notes

**风险评估：**

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| API 速率限制 | 缓存刷新过于频繁可能触发限制 | TTL 60秒 + 最小刷新间隔 10秒 |
| API 不可用 | 无法获取最新持仓 | 显示缓存数据并标记 stale |
| Paper/Live 切换 | 数据混乱 | 切换时清除缓存 |
| 并发问题 | 同时刷新缓存 | 使用 `_refreshing` 标志 + `mark_stale()` |
| 前端兼容性 | 旧端点失效 | Task 9.1 检查，保留 deprecated 端点 |

**已知限制：**
- Live 模式下，持仓数据最多有 60 秒延迟
- Paper 模式无法检测外部变化（因为无真实 API）
- 最小刷新间隔可能导致 `force_refresh` 请求返回缓存数据

**未来考虑（Out of Scope）：**
- WebSocket 实时推送持仓变化（需要 Polymarket 支持）
- 多账户支持
- 持仓历史图表
- Prometheus metrics 导出

---

## Review Notes

- **Adversarial review completed**: 2026-02-27
- **Findings**: 10 total
  - Fixed: 7 (F1-F6, F8)
  - Skipped: 3 (F7, F9, F10 - noise/info)
- **Resolution approach**: auto-fix

### Fixed Issues

| ID | Description | Fix |
|----|-------------|-----|
| F1 | `asyncio.run()` in lambda could cause event loop issues | Added `_refresh_position_cache_task_sync()` wrapper |
| F2 | New `PositionCacheService` instance per request | Added singleton pattern with `_reset_instance()` |
| F3 | Hardcoded 300s refresh interval | Now uses `settings.position_cache.ttl * 5` |
| F4 | `_refreshing` flag not atomic | Replaced with `asyncio.Lock` |
| F5 | Missing response model docs | Added comprehensive field descriptions |
| F6 | Prewarm failure handling | Already handled - returns False and logs warning |
| F8 | `force_refresh` parameter behavior unclear | Improved docstring with detailed behavior |

### Test Updates

- Added `reset_singleton` fixture to `test_position_sync.py`
- Updated `client` fixture in `test_positions.py` to reset singleton
- Fixed `test_refresh_cache_already_refreshing` to use lock acquisition

