---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
workflowType: 'create-epics-and-stories'
project_name: 'polymarket-trader'
user_name: 'Nick'
date: '2026-02-15'
lastStep: 4
status: 'complete'
completedAt: '2026-02-15'
---

# Polymarket Trader - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Polymarket Trader, decomposing the requirements from the PRD and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

| ID | 需求描述 | 优先级 |
|----|----------|--------|
| **FR1** | 系统能够定时从 Polymarket API 获取市场列表并存储到数据库 | P0 |
| **FR2** | 系统能够根据筛选规则（流动性、截止日期、领域等）过滤出适合分析的市场 | P0 |
| **FR3** | LLM 能够分析市场并输出概率估算、置信度、关键假设和分析理由 | P0 |
| **FR4** | 系统能够在 Paper Trading 模式下模拟交易（记录但不执行真实订单） | P0 |
| **FR5** | 风险控制熔断机制：连续亏损 3 次后降低仓位，日亏损 30% 停止交易 | P0 |
| **FR6** | 风险控制资金门槛：资金低于 $100 时降低仓位至 10% | P0 |
| **FR7** | 置信度门槛：LLM 置信度至少 75%，与市场价格差距至少 10% 才能交易 | P0 |
| **FR8** | 持仓限制：单市场不超过 40%，最多同时持有 3 个市场 | P0 |
| **FR9** | 预测追踪：记录所有预测结果并与市场实际结果对比 | P1 |
| **FR10** | 学习日志：每次交易自动生成详细分析报告并存储 | P1 |
| **FR11** | Web Dashboard：显示系统状态、收益统计、快捷操作 | P1 (✅ UI 完成) |
| **FR12** | Dashboard 后端 API：提供市场、交易、持仓、预测、统计数据的 REST API | P1 |

### NonFunctional Requirements

| ID | 需求描述 | 类别 |
|----|----------|------|
| **NFR1** | 系统可用性 > 99% uptime | 性能 |
| **NFR2** | 市场检查频率每 1-4 小时 | 性能 |
| **NFR3** | LLM 响应时间 < 30 秒 | 性能 |
| **NFR4** | Dashboard 响应时间 < 2 秒 | 性能 |
| **NFR5** | API Key 加密存储，不硬编码 | 安全 |
| **NFR6** | Polymarket 私钥安全存储 | 安全 |
| **NFR7** | 日志脱敏（不记录敏感信息） | 安全 |
| **NFR8** | 配置外置，参数通过配置文件管理 | 可维护性 |
| **NFR9** | 完善的日志记录，便于调试 | 可维护性 |
| **NFR10** | 崩溃后自动恢复、状态持久化 | 可靠性 |

### Additional Requirements

从 Architecture 文档提取的技术需求：

| ID | 需求描述 | 来源 |
|----|----------|------|
| **AR1** | 使用 Python 3.10+ (py-clob-client 依赖) | 架构决策 |
| **AR2** | 使用 FastAPI 作为 Web 框架 | 架构决策 |
| **AR3** | 使用 SQLite + aiosqlite (异步) 作为数据库 | 架构决策 |
| **AR4** | 使用 APScheduler 进行定时任务调度 | 架构决策 |
| **AR5** | 使用 OpenAI 兼容协议连接 GLM LLM API | 架构决策 |
| **AR6** | 使用 colorlog + RotatingFileHandler 进行日志记录 | 架构决策 |
| **AR7** | 实现指数退避重试策略（最大 3 次，最大延迟 30s） | 架构决策 |
| **AR8** | 实现自定义异常层次 (BotError → ConfigurationError, NetworkError, TradingError, ValidationError) | 架构决策 |
| **AR9** | 前端使用 React 18 + Vite + TypeScript + Tailwind CSS + shadcn/ui | 架构决策 |
| **AR10** | API 响应格式统一：成功 `{success, data}`，错误 `{success, error: {code, message}}` | 架构决策 |
| **AR11** | 日期时间格式：ISO 8601 | 架构决策 |
| **AR12** | 数据库 Schema：markets, predictions, trades, positions, statistics, system_state 表 | 架构决策 |

### FR Coverage Map

| FR | Epic | 描述 |
|----|------|------|
| FR1 | Epic 2 | 市场数据获取 |
| FR2 | Epic 2 | 市场筛选 |
| FR3 | Epic 3 | LLM 分析 |
| FR4 | Epic 5 | Paper Trading |
| FR5 | Epic 4 | 熔断机制 - 连续亏损 |
| FR6 | Epic 4 | 熔断机制 - 资金门槛 |
| FR7 | Epic 3 + Epic 4 | 置信度门槛 (分析 + 交易前检查) |
| FR8 | Epic 4 | 持仓限制 |
| FR9 | Epic 6 | 预测追踪 |
| FR10 | Epic 6 | 学习日志 |
| FR11 | Epic 7 | Dashboard UI (已完成) |
| FR12 | Epic 7 | Dashboard API |

## Epic List

### Epic 1: 项目基础设施与配置

**用户价值:** 作为开发者，我希望有一个完整的项目基础结构和配置系统，以便后续功能模块可以快速开发和部署。

**FRs covered:** (基础设施，支撑所有 FR)
**ARs covered:** AR1, AR2, AR3, AR4, AR6, AR7, AR8, AR11, AR12

---

### Epic 2: 市场数据获取与筛选

**用户价值:** 作为用户，我希望系统能够自动从 Polymarket 获取市场数据，并根据规则筛选出适合分析的市场，以便我只关注有价值的交易机会。

**FRs covered:** FR1, FR2

---

### Epic 3: LLM 智能分析引擎

**用户价值:** 作为用户，我希望系统能够使用 LLM 自动分析预测市场，给出概率估算和置信度，以便我能够做出数据驱动的交易决策。

**FRs covered:** FR3, FR7 (部分)
**ARs covered:** AR5

---

### Epic 4: 风险控制与熔断系统

**用户价值:** 作为用户，我希望系统有完善的风险控制机制，以便保护我的资金免受重大损失。

**FRs covered:** FR5, FR6, FR7 (部分), FR8

---

### Epic 5: Paper Trading 模拟交易

**用户价值:** 作为用户，我希望系统能够在 Paper Trading 模式下模拟交易，以便验证策略有效性后再使用真钱交易。

**FRs covered:** FR4

---

### Epic 6: 预测追踪与学习日志

**用户价值:** 作为用户，我希望系统能够追踪所有预测的准确性并生成分析报告，以便我可以持续学习和改进策略。

**FRs covered:** FR9, FR10

---

### Epic 7: Dashboard 后端 API 集成

**用户价值:** 作为用户，我希望 Dashboard 能够通过后端 API 显示实时数据，以便我能够监控系统状态和交易表现。

**FRs covered:** FR11, FR12
**ARs covered:** AR2, AR10

---

### Epic 8: 系统调度与自动化运行

**用户价值:** 作为用户，我希望系统能够 24/7 自动运行并自动恢复，以便实现真正的无人值守交易。

**FRs covered:** NFR1, NFR2, NFR10
**ARs covered:** AR4

---

## Epic 1: 项目基础设施与配置

**目标:** 创建完整的项目基础结构和配置系统，支撑后续所有功能模块的开发和部署。

### Story 1.1: 项目结构初始化

As a **开发者**,
I want **创建完整的 Python 项目目录结构**,
So that **后续功能模块可以在标准化的位置开发和部署**.

**Acceptance Criteria:**

**Given** 项目根目录为 `polymarket-trader/`
**When** 执行项目初始化
**Then** 创建以下目录结构:
- `src/` (包含 `__init__.py`)
- `src/models/`, `src/core/`, `src/api/`, `src/analysis/`, `src/trading/`, `src/storage/`, `src/dashboard/`, `src/utils/`
- `logs/`, `data/`, `tests/`, `scripts/`
**And** 每个 Python 子目录都包含 `__init__.py`
**And** 创建 `requirements.txt` 包含核心依赖

---

### Story 1.2: 配置管理系统

As a **开发者**,
I want **使用 Pydantic + .env 实现配置管理**,
So that **所有配置参数集中管理且类型安全**.

**Acceptance Criteria:**

**Given** 项目结构已创建
**When** 实现 `src/config.py`
**Then** 使用 Pydantic BaseSettings 加载环境变量
**And** 支持以下配置类别:
- LLM 配置 (API_BASE, API_KEY, MODEL)
- Polymarket 配置 (PK, PROXY_WALLET, TRADER_ADDRESS)
- 交易参数 (TRADE_UNIT, SLIPPAGE_TOLERANCE, INITIAL_CAPITAL)
- 风险控制参数 (MAX_SINGLE_RATIO, MIN_CONFIDENCE, DAILY_LOSS_LIMIT)
**And** 创建 `.env.example` 模板文件
**And** 配置支持默认值和验证

---

### Story 1.3: 日志系统

As a **开发者**,
I want **实现彩色日志系统支持控制台和文件输出**,
So that **便于调试和审计**.

**Acceptance Criteria:**

**Given** 配置系统已实现
**When** 实现 `src/utils/logger.py`
**Then** 使用 colorlog 实现彩色控制台输出
**And** 使用 RotatingFileHandler 实现文件日志 (10MB/文件, 5个备份)
**And** 日志格式: `{timestamp} | {level:8} | {thread:12} | {module} | {emoji} {message}`
**And** 支持 emoji 日志 (✅ ⚠️ ❌ 💰 🧠 📊 🌐)
**And** 实现日志脱敏: API Key 只显示前4位, 私钥完全隐藏

---

### Story 1.4: 自定义异常体系

As a **开发者**,
I want **实现自定义异常层次结构**,
So that **错误处理清晰且可区分**.

**Acceptance Criteria:**

**Given** 项目结构已创建
**When** 实现 `src/exceptions.py`
**Then** 创建以下异常层次:
- `BotError` (基类)
- `ConfigurationError` (配置错误)
- `NetworkError` (网络错误)
- `TradingError` (交易错误)
- `ValidationError` (验证错误)
**And** 每个异常支持自定义消息和原始异常

---

### Story 1.5: 重试机制

As a **开发者**,
I want **实现指数退避重试装饰器**,
So that **API 调用更加健壮**.

**Acceptance Criteria:**

**Given** 异常体系已实现
**When** 实现 `src/utils/retry.py`
**Then** 创建 `@retry` 装饰器支持:
- 最大重试次数: 3
- 基础延迟: 1s
- 最大延迟: 30s
- 指数退避
- 可配置重试异常类型
**And** 支持异步函数
**And** 记录重试日志

---

### Story 1.6: 数据库初始化

As a **开发者**,
I want **初始化 SQLite 数据库和 Schema**,
So that **后续模块可以持久化数据**.

**Acceptance Criteria:**

**Given** 配置和日志系统已实现
**When** 实现 `src/storage/database.py`
**Then** 创建 SQLite 数据库文件 `data/polymarket.db`
**And** 使用 aiosqlite 支持异步操作
**And** 实现 `init_db()` 函数创建以下表:
```sql
-- 市场表 (先创建基础表，后续故事可扩展)
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

-- 系统状态表
CREATE TABLE system_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```
**And** 实现数据库连接池管理

---

### Story 1.7: Pydantic 数据模型

As a **开发者**,
I want **定义核心 Pydantic 数据模型**,
So that **数据验证和序列化类型安全**.

**Acceptance Criteria:**

**Given** 数据库已初始化
**When** 实现 `src/models/` 目录下的模型
**Then** 创建以下模型:
- `src/models/market.py`: `Market`, `MarketCategory`
- `src/models/trade.py`: `Trade`, `TradeType`, `TradeMode`
- `src/models/prediction.py`: `Prediction`, `PredictionResult`
- `src/models/position.py`: `Position`, `PositionStatus`
- `src/models/statistics.py`: `Statistics`, `DailyStats`
**And** 所有模型继承 Pydantic BaseModel
**And** 实现日期时间序列化 (ISO 8601)

---

## Epic 2: 市场数据获取与筛选

**目标:** 实现从 Polymarket 自动获取市场数据并根据规则筛选出适合分析的市场。

### Story 2.1: Polymarket API 客户端

As a **开发者**,
I want **实现 Polymarket API 客户端封装**,
So that **系统能够与 Polymarket 进行安全可靠的通信**.

**Acceptance Criteria:**

**Given** Epic 1 基础设施已完成
**When** 实现 `src/api/polymarket.py`
**Then** 使用 py-clob-client 库初始化客户端
**And** 支持代理钱包认证
**And** 实现基础 API 方法:
- `get_markets()` - 获取市场列表
- `get_market(market_id)` - 获取单个市场详情
- `get_order_book(market_id)` - 获取订单簿
**And** 所有 API 调用使用重试装饰器
**And** 记录 API 调用日志（脱敏敏感信息）

---

### Story 2.2: 市场数据获取与存储

As a **用户**,
I want **系统能够自动获取 Polymarket 市场数据并存储到数据库**,
So that **我有本地市场数据可供分析和筛选**.

**Acceptance Criteria:**

**Given** Polymarket API 客户端已实现
**When** 实现市场获取功能
**Then** 调用 `get_markets()` 获取所有活跃市场
**And** 将市场数据转换为 Market 模型
**And** 存储到 `markets` 表（使用 UPSERT 避免重复）
**And** 记录获取的市场数量到日志
**And** 更新 `system_state` 表记录最后获取时间
**And** 处理 API 错误和空结果

---

### Story 2.3: 市场筛选规则引擎

As a **用户**,
I want **系统根据筛选规则过滤市场**,
So that **只保留适合分析的高质量市场**.

**Acceptance Criteria:**

**Given** 市场数据已存储在数据库
**When** 实现 `src/analysis/market_filter.py`
**Then** 实现以下筛选规则:
- 流动性筛选: `liquidity >= MIN_LIQUIDITY` (默认 $10,000)
- 截止日期筛选: `deadline >= MIN_DEADLINE_DAYS` (默认 7 天)
- 目标领域筛选: 政治、商业、科技、经济、加密货币
**And** 实现排除规则:
- 标题包含 "price", "USD", "tomorrow"
- 流动性 < $5,000
- 截止日期 < 3 天
- 描述中有争议性条款
**And** 返回 `filtered_markets` 列表
**And** 记录筛选统计（原始数量 → 筛选后数量）

---

### Story 2.4: 市场数据仓库

As a **开发者**,
I want **实现市场数据仓库模式**,
So that **市场数据访问逻辑集中管理**.

**Acceptance Criteria:**

**Given** 数据库和模型已实现
**When** 实现 `src/storage/repositories/market_repo.py`
**Then** 实现以下方法:
- `save_market(market: Market)` - 保存/更新市场
- `get_market(market_id: str)` - 获取单个市场
- `get_active_markets()` - 获取所有活跃市场
- `get_markets_by_category(category: str)` - 按类别获取
- `update_market_resolution(market_id, outcome)` - 更新结算结果
**And** 使用异步数据库操作
**And** 记录操作日志

---

## Epic 3: LLM 智能分析引擎

**目标:** 实现使用 LLM 自动分析预测市场，给出概率估算和置信度。

### Story 3.1: LLM API 客户端

As a **开发者**,
I want **实现 LLM API 客户端 (OpenAI 兼容协议)**,
So that **系统能够与 GLM 进行安全可靠的通信**.

**Acceptance Criteria:**

**Given** Epic 1 基础设施已完成
**When** 实现 `src/api/llm.py`
**Then** 使用 openai 库连接 GLM API (兼容 OpenAI 协议)
**And** 从配置加载: `LLM_API_BASE`, `LLM_API_KEY`, `LLM_MODEL`
**And** 实现基础方法:
- `chat(messages: list)` - 发送对话请求
- `chat_with_system(system_prompt: str, user_prompt: str)` - 带 system prompt 的对话
**And** 设置超时时间 30 秒 (NFR3)
**And** 使用重试装饰器处理网络错误
**And** API Key 日志脱敏 (只显示前4位)

---

### Story 3.2: LLM 提示词模板

As a **开发者**,
I want **定义结构化的 LLM 提示词模板**,
So that **LLM 能够输出标准化的分析结果**.

**Acceptance Criteria:**

**Given** LLM 客户端已实现
**When** 实现 `src/analysis/prompts.py`
**Then** 创建市场分析提示词模板:
- System Prompt: 定义 LLM 为预测市场分析师角色
- User Prompt Template: 包含市场标题、描述、当前价格、截止日期
**And** 要求 LLM 输出 JSON 格式:
```json
{
  "predicted_probability": 0.xx,
  "confidence": 0.xx,
  "reasoning": "分析理由...",
  "key_assumptions": ["假设1", "假设2"],
  "recommendation": "BUY_YES / BUY_NO / NO_TRADE"
}
```
**And** 输出包含概率估算和置信度 (0-1 范围)

---

### Story 3.3: LLM 分析引擎

As a **用户**,
I want **系统能够使用 LLM 分析市场并给出概��估算**,
So that **我能够获得数据驱动的交易建议**.

**Acceptance Criteria:**

**Given** LLM 客户端和提示词模板已实现
**When** 实现 `src/analysis/llm_analyzer.py`
**Then** 实现 `analyze_market(market: Market)` 方法
**And** 返回 `PredictionResult` 模型包含:
- `predicted_probability`: 预测概率 (0-1)
- `confidence`: 置信度 (0-1)
- `reasoning`: 分析理由
- `key_assumptions`: 关键假设列表
- `recommendation`: 交易建议
**And** 验证输出: 置信度 >= 0.75 (MIN_CONFIDENCE) 才标记为可交易
**And** 记录分析日志 (包含 emoji 🧠)
**And** 处理 LLM 返回格式错误

---

### Story 3.4: 预测结果存储

As a **开发者**,
I want **将 LLM 分析结果持久化到数据库**,
So that **预测历史可追溯和分析**.

**Acceptance Criteria:**

**Given** LLM 分析引擎已实现
**When** 扩展数据库和创建预测仓库
**Then** 在 `database.py` 添加 `predictions` 表:
```sql
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    predicted_probability REAL,
    confidence REAL,
    reasoning TEXT,
    key_assumptions TEXT,
    model_used TEXT,
    recommendation TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (market_id) REFERENCES markets(id)
);
```
**And** 实现 `src/storage/repositories/prediction_repo.py`:
- `save_prediction(prediction: Prediction)` - 保存预测
- `get_predictions_by_market(market_id: str)` - 获取市场预测
- `get_pending_predictions()` - 获取待验证预测
**And** 关联 market_id 外键

---

### Story 3.5: Edge 计算 (价格差距分析)

As a **用户**,
I want **系统计算 LLM 预测与市场价格的差距 (Edge)**,
So that **我能够评估交易价值**.

**Acceptance Criteria:**

**Given** LLM 分析结果已存储
**When** 在 `llm_analyzer.py` 添加 edge 计算逻辑
**Then** 计算公式: `edge = abs(predicted_probability - market_price)`
**And** 验证 edge >= 0.10 (MIN_EDGE) 才标记为有价值交易
**And** 在预测结果中添加 `edge` 字段
**And** 记录 edge 计算日志
**And** 将 edge 值保存到 predictions 表

---

## Epic 4: 风险控制与熔断系统

**目标:** 实现完善的风险控制机制，保护资金免受重大损失。

### Story 4.1: 风险控制配置

As a **开发者**,
I want **定义风险控制参数并集成到配置系统**,
So that **风险规则可配置且易于调整**.

**Acceptance Criteria:**

**Given** Epic 1 配置系统已完成
**When** 扩展 `src/config.py` 添加风险控制配置
**Then** 添加以下配置项:
```python
# 资金管理
INITIAL_CAPITAL: float = 200.0
MAX_SINGLE_RATIO: float = 0.20  # 单笔最大 20%
MIN_BET: float = 5.0

# 熔断机制
CONSECUTIVE_LOSSES_LIMIT: int = 3
REDUCE_RATIO_AFTER_LOSSES: float = 0.10
DAILY_LOSS_LIMIT: float = 0.30  # 日亏损 30% 停止
CAPITAL_THRESHOLD: float = 100.0  # 资金低于 $100
REDUCE_RATIO_LOW_CAPITAL: float = 0.10

# 置信度门槛
MIN_CONFIDENCE: float = 0.75
MIN_EDGE: float = 0.10

# 持仓限制
MAX_POSITION_PER_MARKET: float = 0.40
MAX_OPEN_MARKETS: int = 3
```
**And** 所有参数有默认值和验证 (0-1 范围的参数验证)
**And** 更新 `.env.example`

---

### Story 4.2: 线程安全状态管理

As a **开发者**,
I want **实现线程安全的状态管理器**,
So that **系统状态在并发环境下安全更新**.

**Acceptance Criteria:**

**Given** 基础设施已完成
**When** 实现 `src/core/state.py`
**Then** 创建 `ThreadSafeState` 类管理以下状态:
- `current_capital`: 当前资金
- `daily_pnl`: 当日盈亏
- `consecutive_losses`: 连续亏损次数
- `open_positions_count`: 当前持仓数量
- `trading_enabled`: 是否允许交易
- `reduced_mode`: 是否处于降级模式
**And** 使用 `asyncio.Lock` 保证线程安全
**And** 实现方法:
- `get_state()` - 获取当前状态快照
- `update_capital(amount)` - 更新资金
- `record_trade_result(is_win)` - 记录交易结果
- `reset_daily()` - 每日重置
**And** 状态持久化到 `system_state` 表

---

### Story 4.3: 熔断机制实现

As a **用户**,
I want **系统在触发熔断条件时自动降低或停止交易**,
So that **我的资金免受重大损失**.

**Acceptance Criteria:**

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

---

### Story 4.4: 交易前风险检查

As a **用户**,
I want **在每次交易前进行风险检查**,
So that **只有符合规则的交易才会执行**.

**Acceptance Criteria:**

**Given** 熔断机制已实现
**When** 实现 `src/trading/risk_control.py`
**Then** 实现 `RiskController` 类包含以下检查:

1. **置信度检查:**
   - LLM 置信度 >= MIN_CONFIDENCE (75%)
   - Edge >= MIN_EDGE (10%)

2. **持仓限制检查:**
   - 单市场持仓不超过 40%
   - 当前持仓数 < MAX_OPEN_MARKETS (3)

3. **资金检查:**
   - 交易金额 <= 当前资金 * MAX_SINGLE_RATIO (20%)
   - 交易金额 >= MIN_BET ($5)

**And** 实现 `check_trade_allowed(prediction, market)` 方法返回:
- `allowed: bool`
- `reason: str` (如不允许)
- `position_ratio: float` (建议仓位)
**And** 记录检查结果日志

---

### Story 4.5: 持仓管理

As a **用户**,
I want **系统能够追踪和管理当前持仓**,
So that **我能够了解资金分配和风险敞口**.

**Acceptance Criteria:**

**Given** 风险控制器已实现
**When** 扩展数据库和创建持仓仓库
**Then** 在 `database.py` 添加 `positions` 表:
```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    outcome TEXT NOT NULL,  -- YES/NO
    shares REAL NOT NULL,
    avg_price REAL NOT NULL,
    initial_value REAL,
    current_value REAL,
    pnl REAL,
    status TEXT,  -- OPEN/CLOSED
    opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    closed_at DATETIME,
    FOREIGN KEY (market_id) REFERENCES markets(id)
);
```
**And** 实现 `src/trading/position_manager.py`:
- `open_position(market_id, outcome, shares, price)` - 开仓
- `update_position_value(position_id, current_value)` - 更新市值
- `close_position(position_id, final_value)` - 平仓
- `get_open_positions()` - 获取所有未平仓位
- `get_total_exposure()` - 获取总风险敞口
**And** 实现 `src/storage/repositories/position_repo.py`

---

## Epic 5: Paper Trading 模拟交易

**目标:** 实现在 Paper Trading 模式下模拟交易，验证策略有效性。

### Story 5.1: 交易记录数据模型

As a **开发者**,
I want **定义交易记录的数据模型和数据库表**,
So that **交易数据可以持久化存储**.

**Acceptance Criteria:**

**Given** Epic 1-4 已完成
**When** 扩展数据库和交易模型
**Then** 在 `database.py` 添加 `trades` 表:
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    trade_type TEXT NOT NULL,  -- BUY_YES/BUY_NO/SELL
    mode TEXT NOT NULL,        -- PAPER/LIVE
    amount REAL NOT NULL,
    price REAL NOT NULL,
    shares REAL,
    status TEXT,               -- PENDING/FILLED/CANCELLED
    llm_prediction_id INTEGER,
    position_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (market_id) REFERENCES markets(id),
    FOREIGN KEY (llm_prediction_id) REFERENCES predictions(id),
    FOREIGN KEY (position_id) REFERENCES positions(id)
);
```
**And** 在 `src/models/trade.py` 扩展 `Trade` 模型
**And** 实现 `src/storage/repositories/trade_repo.py`:
- `save_trade(trade: Trade)` - 保存交易
- `get_trades_by_market(market_id)` - 获取市场交易
- `get_trades_by_mode(mode)` - 按模式获取交易
- `get_recent_trades(limit)` - 获取最近交易

---

### Story 5.2: Paper Trading 执行器

As a **用户**,
I want **系统能够模拟执行交易而不下真实订单**,
So that **我可以验证策略而不冒真钱风险**.

**Acceptance Criteria:**

**Given** 交易记录模型已实现
**When** 实现 `src/trading/paper_trading.py`
**Then** 创建 `PaperTradingExecutor` 类:
- `execute_trade(market, prediction, amount)` - 模拟执行交易
**And** 交易执行流程:
1. 创建 Trade 记录 (mode=PAPER)
2. 计算份额: `shares = amount / price`
3. 创建/更新 Position (虚拟持仓)
4. 更新 ThreadSafeState (虚拟资金)
5. 记录交易日志 (💰 PAPER TRADE)
**And** 交易状态设为 FILLED (模拟即时成交)
**And** 关联 LLM 预测记录
**And** 返回交易结果

---

### Story 5.3: 交易决策流程

As a **用户**,
I want **系统能够基于 LLM 分析和风险检查自动做出交易决策**,
So that **交易过程完全自动化**.

**Acceptance Criteria:**

**Given** Paper Trading 执行器和风险控制器已实现
**When** 实现 `src/trading/executor.py`
**Then** 创建 `TradingExecutor` 类实现完整交易流程:
```python
async def process_market(market: Market):
    # 1. LLM 分析
    prediction = await llm_analyzer.analyze_market(market)

    # 2. 风险检查
    check = risk_controller.check_trade_allowed(prediction, market)
    if not check.allowed:
        log_and_skip(check.reason)
        return

    # 3. 计算交易金额
    amount = calculate_position_size(check.position_ratio)

    # 4. 执行交易 (Paper Trading)
    trade = await paper_executor.execute_trade(market, prediction, amount)

    # 5. 记录日志
    log_trade(trade)
```
**And** 支持配置交易模式 (PAPER/LIVE)
**And** 处理异常情况

---

### Story 5.4: 模拟持仓 PnL 计算

As a **用户**,
I want **系统能够计算模拟持仓的实时盈亏**,
So that **我能够评估策略表现**.

**Acceptance Criteria:**

**Given** Paper Trading 已实现
**When** 实现持仓 PnL 计算功能
**Then** 在 `position_manager.py` 添加:
- `calculate_pnl(position, current_price)` - 计算单个持仓 PnL
- `calculate_total_pnl()` - 计算总 PnL
**And** PnL 计算公式:
- `pnl = shares * (current_price - avg_price)` (BUY_YES)
- `pnl = shares * (avg_price - current_price)` (BUY_NO)
- `pnl_pct = pnl / initial_value`
**And** 更新 Position 表的 `current_value`, `pnl` 字段
**And** 记录 PnL 变化日志

---

### Story 5.5: 统计数据记录

As a **用户**,
I want **系统记录每日统计数据**,
So that **我能够追踪长期表现**.

**Acceptance Criteria:**

**Given** 交易和持仓记录已实现
**When** 扩展数据库和实现统计功能
**Then** 在 `database.py` 添加 `statistics` 表:
```sql
CREATE TABLE statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,
    mode TEXT NOT NULL,
    starting_capital REAL,
    ending_capital REAL,
    total_pnl REAL,
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```
**And** 实现 `src/storage/repositories/statistics_repo.py`:
- `save_daily_stats(stats: Statistics)` - 保存每日统计
- `get_stats_by_date_range(start, end)` - 获取时间范围统计
- `get_latest_stats()` - 获取最新统计
**And** 实现每日统计任务:
- 统计当日交易数、胜率、PnL
- 记录到 statistics 表
- 重置当日状态

---

## Epic 6: 预测追踪与学习日志

**目标:** 追踪所有预测的准确性并生成分析报告，持续学习和改进策略。

### Story 6.1: 预测结果验证机制

As a **用户**,
I want **系统能够自动检查已结算市场并验证预测准确性**,
So that **我能够知道 LLM 预测的实际表现**.

**Acceptance Criteria:**

**Given** 预测记录和市场数据已实现
**When** 实现 `src/analysis/prediction_tracker.py`
**Then** 创建 `PredictionTracker` 类:
- `check_resolved_markets()` - 检查已结算市场
- `validate_prediction(prediction, actual_outcome)` - 验证单个预测
- `calculate_accuracy(predictions)` - 计算准确率
**And** 预测验证逻辑:
- 获取 `resolution_status = 'RESOLVED'` 的市场
- 对比预测方向与实际结果
- 记录预测是否正确 (`is_correct` 字段)
**And** 更新 predictions 表添加字段:
```sql
ALTER TABLE predictions ADD COLUMN actual_outcome TEXT;
ALTER TABLE predictions ADD COLUMN is_correct BOOLEAN;
ALTER TABLE predictions ADD COLUMN validated_at DATETIME;
```
**And** 记录验证日志 (📊 预测验证结果)

---

### Story 6.2: 准确率统计

As a **用户**,
I want **系统能够计算并展示 LLM 预测的整体准确率**,
So that **我能够评估 LLM 的分析能力**.

**Acceptance Criteria:**

**Given** 预测验证机制已实现
**When** 实现准确率统计功能
**Then** 在 `prediction_tracker.py` 添加:
- `get_overall_accuracy()` - 获取总体准确率
- `get_accuracy_by_category(category)` - 按类别统计
- `get_accuracy_by_date_range(start, end)` - 按时间范围统计
- `get_confidence_accuracy_correlation()` - 置信度与准确率相关性
**And** 准确率计算:
```python
accuracy = correct_predictions / total_validated_predictions
```
**And** 返回统计结果包含:
- 总预测数、正确数、准确率
- 按类别分组统计
- 按置信度区间统计
**And** 记录统计更新日志

---

### Story 6.3: 学习日志生成

As a **用户**,
I want **系统在每笔交易后自动生成详细分析报告**,
So that **我可以回顾和改进策略**.

**Acceptance Criteria:**

**Given** 交易执行和预测追踪已实现
**When** 实现 `src/trading/learning_log.py`
**Then** 创建 `LearningLogGenerator` 类:
- `generate_trade_report(trade, prediction, market)` - 生成单笔交易报告
- `generate_daily_report(date)` - 生成每日报告
**And** 单笔报告包含:
- 市场信息 (标题、描述、截止日期)
- 市场价格 vs LLM 预测
- 置信度、Edge、分析理由
- 交易决策 (买入方向、金额、价格)
- 持仓状态
**And** 每日报告包含:
- 当日交易汇总
- PnL 统计
- 胜率统计
- 关键学习点
**And** 报告存储为 JSON 到 `logs/reports/` 目录
**And** 报告文件命名: `trade_{id}_{timestamp}.json`, `daily_{date}.json`

---

### Story 6.4: 预测历史查询 API

As a **开发者**,
I want **提供预测历史的查询接口**,
So that **Dashboard 可以展示预测数据**.

**Acceptance Criteria:**

**Given** 预测追踪已实现
**When** 扩展 prediction_repo.py
**Then** 添加查询方法:
- `get_predictions_with_outcome(status)` - 获取带结果的预测
- `get_correct_predictions()` - 获取正确预测
- `get_incorrect_predictions()` - 获取错误预测
- `get_predictions_by_confidence_range(min, max)` - 按置信度范围查询
**And** 支持分页参数 (page, per_page)
**And** 支持排序 (按日期、置信度、准确率)
**And** 返回包含关联市场信息

---

### Story 6.5: 表现分析与洞察

As a **用户**,
I want **系统能够分析我的交易表现并提供改进洞察**,
So that **我能够持续优化策略**.

**Acceptance Criteria:**

**Given** 预测追踪和学习日志已实现
**When** 实现 `src/analysis/performance_analyzer.py`
**Then** 创建 `PerformanceAnalyzer` 类:
- `analyze_performance()` - 综合表现分析
- `identify_patterns()` - 识别成功/失败模式
- `generate_recommendations()` - 生成改进建议
**And** 分析内容包含:
- 最佳/最差交易类别
- 高置信度预测的准确率
- 低置信度预测的表现
- Edge 大小��成功率关系
- 持仓时间与收益关系
**And** 生成洞察报告存储到 `logs/reports/insights_{date}.json`
**And** 记录分析日志 (🧠 表现分析完成)

---

## Epic 7: Dashboard 后端 API 集成

**目标:** 通过后端 API 让 Dashboard 显示实时数据，监控系统状态和交易表现。

### Story 7.1: FastAPI 应用初始化

As a **开发者**,
I want **创建 FastAPI 应用基础结构**,
So that **Dashboard 有可用的后端 API 服务**.

**Acceptance Criteria:**

**Given** Epic 1-6 已完成
**When** 实现 `src/dashboard/app.py`
**Then** 创建 FastAPI 应用实例:
- 配置 CORS 允许前端访问
- 配置响应格式统一 (AR10)
- 添加健康检查端点 `GET /health`
**And** 创建路由目录结构:
```
src/dashboard/
├── __init__.py
├── app.py
├── dependencies.py
└── routes/
    ├── __init__.py
    ├── markets.py
    ├── trades.py
    ├── positions.py
    ├── predictions.py
    └── statistics.py
```
**And** 实现依赖注入 `dependencies.py`:
- `get_db()` - 数据库连接
- `get_state()` - 系统状态
**And** 统一响应格式:
```json
// 成功
{"success": true, "data": {...}}
// 错误
{"success": false, "error": {"code": "XXX", "message": "..."}}
// 列表
{"success": true, "data": [...], "meta": {"total": 100, "page": 1, "per_page": 20}}
```

---

### Story 7.2: 市场数据 API

As a **用户**,
I want **通过 API 获取市场列表和详情**,
So that **Dashboard 能够展示市场信息**.

**Acceptance Criteria:**

**Given** FastAPI 应用已初始化
**When** 实现 `src/dashboard/routes/markets.py`
**Then** 实现以下端点:
- `GET /api/markets` - 获取市场列表 (分页、筛选)
- `GET /api/markets/{market_id}` - 获取单个市场详情
- `GET /api/markets?status=active` - 筛选活跃市场
- `GET /api/markets?category=politics` - 按类别筛选
**And** 响应包含:
- 市场基本信息 (id, title, description, category)
- 价格信息 (yes_price, no_price)
- 流动性、截止日期
- 结算状态 (如有)
**And** 响应时间 < 2 秒 (NFR4)
**And** 使用统一响应格式

---

### Story 7.3: 持仓与交易 API

As a **用户**,
I want **通过 API 获取持仓和交易记录**,
So that **Dashboard 能够展示我的交易活动**.

**Acceptance Criteria:**

**Given** 市场 API 已实现
**When** 实现 `src/dashboard/routes/positions.py` 和 `trades.py`
**Then** 实现持仓端点:
- `GET /api/positions` - 获取当前持仓列表
- `GET /api/positions/{position_id}` - 获取持仓详情
- 响应包含: market_id, outcome, shares, avg_price, current_value, pnl, status

**And** 实现交易端点:
- `GET /api/trades` - 获取交易历史 (分页)
- `GET /api/trades/{trade_id}` - 获取交易详情
- `GET /api/trades?mode=paper` - 按模式筛选
- 响应包含: market_id, trade_type, mode, amount, price, shares, status, created_at

**And** 支持排序 (按时间倒序)
**And** 使用统一响应格式

---

### Story 7.4: 预测与统计 API

As a **用户**,
I want **通过 API 获取预测记录和统计数据**,
So that **Dashboard 能够展示预测准确率和收益统计**.

**Acceptance Criteria:**

**Given** 持仓交易 API 已实现
**When** 实现 `src/dashboard/routes/predictions.py` 和 `statistics.py`
**Then** 实现预测端点:
- `GET /api/predictions` - 获取预测列表
- `GET /api/predictions/{prediction_id}` - 获取预测详情
- `GET /api/predictions/accuracy` - 获取准确率统计
- 响应包含: market_id, predicted_probability, confidence, actual_outcome, is_correct

**And** 实现统计端点:
- `GET /api/statistics/overview` - 获取系统概览
  - 返回: current_capital, total_pnl, win_rate, total_trades
- `GET /api/statistics/daily` - 获取每日统计
- `GET /api/statistics/performance` - 获取表现数据 (用于图表)

**And** 使用统一响应格式

---

### Story 7.5: 系统状态 API

As a **用户**,
I want **通过 API 获取系统运行状态**,
So that **Dashboard 能够监控系统能否正常工作**.

**Acceptance Criteria:**

**Given** 统计 API 已实现
**When** 扩展 `src/dashboard/routes/statistics.py`
**Then** 实现状态端点:
- `GET /api/status` - 获取系统状态
- 返回内容:
  ```json
  {
    "success": true,
    "data": {
      "trading_enabled": true,
      "mode": "PAPER",
      "current_capital": 180.50,
      "daily_pnl": -5.50,
      "open_positions": 2,
      "consecutive_losses": 1,
      "reduced_mode": false,
      "last_market_fetch": "2026-02-15T10:30:00Z",
      "uptime_hours": 72.5
    }
  }
  ```
**And** 添加配置查看端点:
- `GET /api/settings` - 获取当前配置 (脱敏)
- 返回配置但隐藏敏感信息 (API Key, 私钥)

---

### Story 7.6: 前端 API 集成

As a **用户**,
I want **Dashboard 前端连接真实后端 API**,
So that **我能够看到实时数据而非 Mock 数据**.

**Acceptance Criteria:**

**Given** 所有后端 API 已实现
**When** 更新前端 API 集成
**Then** 在 `dashboard/src/api/` 创建:
- `client.ts` - Axios 客户端配置 (baseURL, timeout)
- `markets.ts` - 市场 API 调用
- `positions.ts` - 持仓 API 调用
- `trades.ts` - 交易 API 调用
- `predictions.ts` - 预测 API 调用
- `statistics.ts` - 统计 API 调用
**And** 更新 React Query hooks:
- 使用真实 API 替换 mockData
- 处理加载和错误状态
**And** 更新页面组件:
- Index.tsx 使用 `/api/statistics/overview`
- Positions.tsx 使用 `/api/positions`
- Trades.tsx 使用 `/api/trades`
- Predictions.tsx 使用 `/api/predictions`
- Settings.tsx 使用 `/api/settings`
**And** 添加 API 基础 URL 配置到 `.env`

---

### Story 7.7: 最近活动 API 与前端集成

As a **用户**,
I want **Dashboard 首页显示真实的最近活动记录**,
So that **我能够实时了解系统的交易、预测和系统事件**.

**Acceptance Criteria:**

**Given** Epic 1-6 已完成，Story 7.1-7.6 已实现
**When** 实现最近活动功能
**Then** 后端实现活动记录 API:
- `GET /api/activities` - 获取最近活动列表
- 返回活动类型: trade (交易), prediction (预测), system (系统事件)
- 每条记录包含: id, type, description, time, amount (可选)
- 支持分页和限制返回数量 (默认 10 条)
**And** 前端更新 `RecentActivity.tsx`:
- 调用真实 API 替换 mockData
- 处理加载和空数据状态
- 保持现有 UI 样式和交互
**And** 数据来源:
- trade: 来自 trades 表的最近交易记录
- prediction: 来自 predictions 表的最近预测记录
- system: 来自 system_state 表的系统事件 (启动、停止等)
**And** 使用统一响应格式

---

## Epic 8: 系统调度与自动化运行

**目标:** 实现 24/7 自动运行并自动恢复，真正无人值守交易。

### Story 8.1: APScheduler 调度器配置

As a **开发者**,
I want **配置 APScheduler 实现定时任务调度**,
So that **系统能够按计划自动执行各项任务**.

**Acceptance Criteria:**

**Given** Epic 1-7 已完成
**When** 实现 `src/core/scheduler.py`
**Then** 创建 `Scheduler` 类使用 APScheduler:
- 使用 AsyncIOScheduler (异步调度)
- 支持配置时区
**And** 配置任务存储 (SQLite jobstore)
**And** 记录调度器状态日志
**And** 提供启动/停止方法:
- `start()` - 启动调度器
- `shutdown()` - 优雅关闭
**And** 支持动态添加/移除任务

---

### Story 8.2: 定时任务配置

As a **用户**,
I want **系统按配置的时间间隔执行各项任务**,
So that **市场获取、分析、交易自动进行**.

**Acceptance Criteria:**

**Given** 调度器已配置
**When** 添加定时任务
**Then** 配置以下定时任务:

| 任务 | 频率 | 描述 |
|------|------|------|
| `fetch_markets` | 每 1-4 小时 | 获取市场数据 |
| `analyze_markets` | 按需 (市场获取后) | LLM 分析筛选后的市场 |
| `check_positions` | 每 1 分钟 | 检查持仓状态和 PnL |
| `daily_statistics` | 每日 00:00 | 更新每日统计 |
| `validate_predictions` | 每日 06:00 | 验证已结算市场预测 |
| `reset_daily_state` | 每日 00:00 | 重置每日状态 |

**And** 任务频率可通过配置文件调整
**And** 记录每次任务执行日志 (开始/结束/耗时)

---

### Story 8.3: 主入口与启动流程

As a **开发者**,
I want **实现主入口点统一启动所有系统组件**,
So that **系统可以通过单个命令启动**.

**Acceptance Criteria:**

**Given** 调度器和任务已配置
**When** 实现 `src/main.py`
**Then** 创建主入口函数:
```python
async def main():
    # 1. 加载配置
    config = load_config()

    # 2. 初始化日志
    setup_logger(config)

    # 3. 初始化数据库
    await init_db()

    # 4. 初始化状态管理器
    state = ThreadSafeState(config)

    # 5. 启动 FastAPI (后台)
    start_dashboard()

    # 6. 启动调度器
    scheduler = Scheduler(config)
    scheduler.start()

    # 7. 等待信号
    await wait_for_shutdown()
```
**And** 支持命令行参数:
- `--mode` (paper/live)
- `--config` (配置文件路径)
**And** 优雅关闭处理 (SIGTERM, SIGINT)
**And** 记录启动和关闭日志

---

### Story 8.4: 自动恢复机制

As a **用户**,
I want **系统崩溃后能够自动恢复到之前的状态**,
So that **无需人工干预即可继续运行**.

**Acceptance Criteria:**

**Given** 主入口已实现
**When** 实现状态恢复机制
**Then** 在启动时执行:
- 从 `system_state` 表加载上次状态
- 恢复 `current_capital`, `consecutive_losses` 等
- 恢复 `trading_enabled`, `reduced_mode` 状态
- 验证持仓数据一致性
**And** 记录恢复日志 (🔄 状态已恢复)
**And** 如果状态不一致:
- 记录警告
- 重置到安全状态
**And** 实现定时状态持久化 (每 5 分钟)

---

### Story 8.5: 错误处理与告警

As a **用户**,
I want **系统在遇到错误时能够正确处理并记录**,
So that **问题可追踪且不影响整体运行**.

**Acceptance Criteria:**

**Given** 自动恢复机制已实现
**When** 实现全局错误处理
**Then** 配置全局异常处理器:
- 捕获未处理异常
- 记录详细错误日志 (🔥 CRITICAL)
- 不中断主循环运行
**And** 任务级错误处理:
- 单个任务失败不影响其他任务
- 失败任务自动重试 (最多 3 次)
- 连续失败触发告警
**And** 实现错误告警机制:
- 记录到 `logs/errors.log`
- 设置系统状态 `last_error` 字段
**And** API 错误处理:
- 返回统一错误格式
- 记录 API 错误日志

---

### Story 8.6: 运行脚本与进程管理

As a **用户**,
I want **有便捷的脚本来启动、停止和监控系统**,
So that **日常运维简单可靠**.

**Acceptance Criteria:**

**Given** 所有组件已实现
**When** 创建运行脚本
**Then** 创建 `scripts/run.sh`:
```bash
#!/bin/bash
# 启动系统
source .venv/bin/activate
python -m src.main --mode paper
```
**And** 创建 `scripts/stop.sh`:
```bash
#!/bin/bash
# 优雅停止系统
kill -TERM $(cat .bot.pid)
```
**And** 创建 `scripts/status.sh`:
```bash
#!/bin/bash
# 检查系统状态
curl http://localhost:8000/api/status
```
**And** 支持 PID 文件管理
**And** 记录启动日志到 `logs/bot.log`
**And** 创建 systemd 服务文件模板 (可选)

---

## Summary

### Statistics

| Metric | Count |
|--------|-------|
| **Total Epics** | 8 |
| **Total Stories** | 44 |
| **FR Coverage** | 12/12 (100%) |
| **NFR Coverage** | 10/10 (100%) |
| **AR Coverage** | 12/12 (100%) |

### Story Distribution

| Epic | Stories | Requirements |
|------|---------|--------------|
| Epic 1: 项目基础设施与配置 | 7 | AR1-AR8, AR11, AR12 |
| Epic 2: 市场数据获取与筛选 | 4 | FR1, FR2 |
| Epic 3: LLM 智能分析引擎 | 5 | FR3, FR7 |
| Epic 4: 风险控制与熔断系统 | 5 | FR5, FR6, FR7, FR8 |
| Epic 5: Paper Trading 模拟交易 | 5 | FR4 |
| Epic 6: 预测追踪与学习日志 | 5 | FR9, FR10 |
| Epic 7: Dashboard 后端 API 集成 | 6 | FR11, FR12, AR2, AR10 |
| Epic 8: 系统调度与自动化运行 | 6 | NFR1, NFR2, NFR10, AR4 |
