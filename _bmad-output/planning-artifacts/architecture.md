---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - '_bmad-output/prd/polymarket-trader-prd-v1.md'
  - '_bmad-output/brainstorming/brainstorming-session-2026-02-15.md'
workflowType: 'architecture'
project_name: 'polymarket-trader'
user_name: 'Nick'
date: '2026-02-15'
lastStep: 8
status: 'complete'
completedAt: '2026-02-15'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

---

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

| 优先级 | 功能 | 阶段 |
|--------|------|------|
| **P0** | LLM 分析引擎、Paper Trading、风险控制、市场筛选 | MVP |
| **P1** | 预测追踪、学习日志、Web Dashboard | MVP |
| **P2** | 真钱交易、实时数据 API、通知系统 | Phase 2 |
| **P3** | 回测系统、自适应参数、多 LLM 验证 | Phase 3 |

**Non-Functional Requirements:**

| 类别 | 需求 |
|------|------|
| **性能** | 99% uptime、LLM 响应 < 30s、Dashboard < 2s |
| **安全** | API Key 加密存储、私钥保护、日志脱敏 |
| **可维护性** | 配置外置、完善日志、自动恢复 |

**Scale & Complexity:**

- Primary domain: 后端服务 + CLI/Web 接口
- Complexity level: 中等
- Estimated architectural components: 6-8 个核心模块

### Technical Constraints & Dependencies

| 约束 | 描述 |
|------|------|
| 运行环境 | Mac Mini 本地部署 |
| 数据库 | SQLite |
| LLM | 云端 API（GLM - OpenAI 兼容协议） |
| 运行模式 | 24/7 无人值守 |
| 数据获取 | 仅使用官方 API，无爬虫 |

### Cross-Cutting Concerns Identified

| 关注点 | 描述 |
|--------|------|
| 错误处理 | API 故障重试、LLM 调用失败处理 |
| 日志记录 | 交易日志、分析日志、审计日志 |
| 配置管理 | 外置配置文件（风险参数、API keys） |
| 状态恢复 | 崩溃后自动重启、状态持久化 |
| 安全 | 密钥管理、数据脱敏 |

---

## Starter Template Evaluation

### Primary Technology Domain

**后端服务 + CLI/Web 接口**，基于项目需求分析

- 本地部署（Mac Mini）
- 24/7 无人值守运行
- Polymarket API 集成 (py-clob-client)
- LLM API 集成 (GLM - OpenAI 兼容协议)

### Reference Project Analysis

**参考项目：** Polymarket-spike-bot-v1

| 可复用组件 | 价值 |
|------------|------|
| py-clob-client | Polymarket 官方客户端 |
| ThreadSafeState 模式 | 线程安全状态管理 |
| .env 配置模式 | 环境变量管理 |
| 日志架构 | colorlog + RotatingFileHandler |
| 重试机制 | API 调用健壮性 |

### Selected Approach: 自定义架构（基于参考项目）

**选择理由：**

1. **py-clob-client 是 Python 库** - 必须用 Python
2. **无合适 starter** - 没有现成的 "LLM + Polymarket 交易" starter
3. **参考项目已有良好基础** - 可复用核心模式
4. **模块化改进** - 在参考项目基础上模块化

### Project Structure

```
polymarket-trader/
├── src/
│   ├── __init__.py
│   ├── main.py              # 入口点
│   ├── config.py            # 配置管理
│   ├── exceptions.py        # 自定义异常
│   ├── models/
│   │   ├── __init__.py
│   │   ├── trade.py         # TradeInfo, PositionInfo
│   │   └── prediction.py    # 预测相关数据类
│   ├── core/
│   │   ├── __init__.py
│   │   ├── state.py         # ThreadSafeState
│   │   ├── scheduler.py     # 调度器
│   │   └── circuit_breaker.py  # 熔断机制
│   ├── api/
│   │   ├── __init__.py
│   │   ├── polymarket.py    # Polymarket API 客户端
│   │   └── llm.py           # LLM API 客户端 (GLM)
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── market_filter.py # 市场筛选
│   │   └── llm_analyzer.py  # LLM 分析引擎
│   ├── trading/
│   │   ├── __init__.py
│   │   ├── paper_trading.py # Paper Trading
│   │   ├── executor.py      # 交易执行
│   │   └── risk_control.py  # 风险控制
│   ├── storage/
│   │   ├── __init__.py
│   │   └── database.py      # SQLite 操作
│   ├── dashboard/
│   │   ├── __init__.py
│   │   └── app.py           # FastAPI Dashboard
│   └── utils/
│       ├── __init__.py
│       ├── logger.py        # 日志配置
│       └── retry.py         # 重试装饰器
├── logs/
├── data/
│   └── polymarket.db        # SQLite 数据库
├── .env.example
├── requirements.txt
└── README.md
```

### Core Dependencies

```txt
# Polymarket
py-clob-client>=0.1.0
web3>=5.31.0

# LLM (OpenAI 兼容协议 - GLM)
openai>=1.0.0

# Web Framework
fastapi>=0.109.0
uvicorn>=0.27.0

# Database
aiosqlite>=0.19.0

# HTTP & Config
requests>=2.31.0
python-dotenv>=1.0.0
pydantic>=2.0.0

# Logging
colorlog>=6.7.0

# Scheduling
apscheduler>=3.10.0

# Utilities
halo>=0.0.31
```

### Initialization Command

```bash
# 创建项目结构
mkdir -p polymarket-trader/{src/{models,core,api,analysis,trading,storage,dashboard,utils},logs,data}

# 创建 __init__.py 文件
touch polymarket-trader/src/__init__.py
touch polymarket-trader/src/models/__init__.py
touch polymarket-trader/src/core/__init__.py
touch polymarket-trader/src/api/__init__.py
touch polymarket-trader/src/analysis/__init__.py
touch polymarket-trader/src/trading/__init__.py
touch polymarket-trader/src/storage/__init__.py
touch polymarket-trader/src/dashboard/__init__.py
touch polymarket-trader/src/utils/__init__.py

# 初始化虚拟环境
cd polymarket-trader
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# 安装依赖
pip install py-clob-client web3 openai fastapi uvicorn aiosqlite requests python-dotenv pydantic colorlog apscheduler halo
```

### Configuration Template

```env
# .env.example

# ========== LLM Configuration ==========
LLM_API_BASE=https://open.bigmodel.cn/api/paas/v4
LLM_API_KEY=your_glm_api_key_here
LLM_MODEL=glm-4

# ========== Polymarket Configuration ==========
PK=your_private_key_here
YOUR_PROXY_WALLET=your_proxy_wallet_address
BOT_TRADER_ADDRESS=your_trader_address

# ========== Trading Parameters ==========
TRADE_UNIT=10.0
SLIPPAGE_TOLERANCE=0.02
PCT_PROFIT=0.03
PCT_LOSS=-0.025
INITIAL_CAPITAL=200

# ========== Risk Control ==========
MAX_SINGLE_RATIO=0.20
MIN_CONFIDENCE=0.75
MIN_EDGE=0.10
MAX_CONCURRENT_TRADES=3
DAILY_LOSS_LIMIT=0.30

# ========== Market Filter ==========
MIN_LIQUIDITY=10000
MIN_DEADLINE_DAYS=7
```

### Architectural Decisions Summary

| 决策 | 选择 | 理由 |
|------|------|------|
| **语言** | Python 3.10+ | py-clob-client, LLM 生态 |
| **Web 框架** | FastAPI | 轻量、异步、自动 API 文档 |
| **数据库** | SQLite + aiosqlite | 本地部署、轻量级、异步支持 |
| **调度器** | APScheduler | 定时任务、简单可靠 |
| **LLM** | OpenAI 兼容协议 (GLM) | 用户的 provider 是 GLM |
| **日志** | colorlog + RotatingFileHandler | 参考项目验证 |

---

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**

| 决策 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3.10+ | py-clob-client 依赖 |
| 数据模型 | Pydantic v2 | FastAPI 集成、数据验证 |
| 数据库 | SQLite + aiosqlite | 本地部署、异步支持 |
| 安全方案 | .env + cryptography | 平衡安全与复杂度 |

**Important Decisions (Shape Architecture):**

| 决策 | 选择 | 理由 |
|------|------|------|
| 重试策略 | 指数退避 | API 调用健壮性 |
| Dashboard | React 18 SPA | 支持复杂交互 |
| 前端框架 | React + Vite + TypeScript | 用户偏好、生态丰富 |

**Deferred Decisions (Post-MVP):**

| 决策 | 延迟理由 |
|------|----------|
| 通知系统 | Phase 2 功能 |
| 多 LLM 交叉验证 | Phase 3 功能 |
| 回测系统 | Phase 3 功能 |

---

### Data Architecture

**Database:** SQLite 3.x + aiosqlite (异步)

**Database Schema:**

```sql
-- 市场表
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

-- 预测表 (LLM 分析结果)
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    predicted_probability REAL,
    confidence REAL,
    reasoning TEXT,
    key_assumptions TEXT,
    model_used TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (market_id) REFERENCES markets(id)
);

-- 交易表
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    trade_type TEXT NOT NULL,
    mode TEXT NOT NULL,
    amount REAL NOT NULL,
    price REAL NOT NULL,
    shares REAL,
    status TEXT,
    llm_prediction_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (market_id) REFERENCES markets(id),
    FOREIGN KEY (llm_prediction_id) REFERENCES predictions(id)
);

-- 持仓表
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    shares REAL NOT NULL,
    avg_price REAL NOT NULL,
    initial_value REAL,
    current_value REAL,
    pnl REAL,
    status TEXT,
    opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    closed_at DATETIME,
    FOREIGN KEY (market_id) REFERENCES markets(id)
);

-- 统计表
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

-- 系统状态表
CREATE TABLE system_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Data Modeling:** Pydantic v2
- 数据验证和序列化
- FastAPI 集成
- 类型安全

---

### Authentication & Security

**API Key 保护方案:**

| 层级 | 措施 |
|------|------|
| 存储 | .env 文件 (chmod 600) |
| 加密 | cryptography 库加密敏感字段 |
| 运行时 | 解密到内存，不写入日志 |

**日志脱敏规则:**

| 信息类型 | 脱敏规则 | 示例 |
|----------|----------|------|
| API Key | 只显示前4位 | `sk-xxxx****xxxx` |
| 私钥 | 完全隐藏 | `[PRIVATE_KEY]` |
| 钱包地址 | 前6后4位 | `0x1234...5678` |

---

### API & Communication Patterns

**错误处理层次:**

```
BotError (基类)
├── ConfigurationError  # 配置错误
├── NetworkError        # 网络错误
├── TradingError        # 交易错误
└── ValidationError     # 验证错误
```

**重试策略配置:**

| 参数 | 值 | 说明 |
|------|-----|------|
| max_attempts | 3 | 最大重试次数 |
| base_delay | 1s | 初始延迟 |
| max_delay | 30s | 最大延迟 |
| exponential_backoff | True | 指数退避 |
| 适用异常 | NetworkError, RateLimitError, TimeoutError | - |

**重试装饰器示例:**

```python
@retry(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_backoff=True,
    exceptions=(NetworkError, RateLimitError, TimeoutError)
)
async def call_api(...):
    ...
```

---

### Frontend Architecture

**技术栈:**

| 类别 | 选择 | 版本 |
|------|------|------|
| 框架 | React | 18.x |
| 构建工具 | Vite | 5.x |
| 语言 | TypeScript | 5.x |
| 路由 | React Router | 6.x |
| 数据获取 | TanStack Query | 5.x |
| 样式 | Tailwind CSS | 3.x |
| 组件库 | shadcn/ui | latest |
| 图表 | Recharts | 2.x |

**前端项目结构:**

```
dashboard/
├── src/
│   ├── components/     # 可复用组件
│   │   ├── ui/         # shadcn/ui 组件
│   │   └── charts/     # 图表组件
│   ├── pages/          # 页面组件
│   │   ├── Home.tsx
│   │   ├── Positions.tsx
│   │   ├── Trades.tsx
│   │   └── Predictions.tsx
│   ├── hooks/          # 自定义 hooks
│   ├── api/            # API 调用
│   ├── types/          # TypeScript 类型
│   └── App.tsx
├── package.json
└── vite.config.ts
```

**Dashboard 页面:**

| 路由 | 页面 | 功能 |
|------|------|------|
| `/` | Home | 系统状态概览、收益统计 |
| `/positions` | Positions | 当前持仓列表、PnL 显示 |
| `/trades` | Trades | 交易历史记录 |
| `/predictions` | Predictions | 预测记录、准确率统计 |
| `/settings` | Settings | 配置查看（脱敏） |

---

### Infrastructure & Deployment

**运行环境:**

| 配置 | 值 |
|------|-----|
| 部署位置 | Mac Mini 本地 |
| Python 版本 | 3.10+ |
| 虚拟环境 | venv |
| 运行模式 | 24/7 无人值守 |

**调度配置:**

| 任务 | 频率 | 描述 |
|------|------|------|
| 市场获取 | 每 1-4 小时 | 从 Polymarket API 获取市场列表 |
| LLM 分析 | 按需 | 对筛选后的市场进行分析 |
| 持仓检查 | 每 1 分钟 | 检查止盈/止损条件 |
| 统计更新 | 每日 | 更新收益统计 |

**日志配置:**

| 配置 | 值 |
|------|-----|
| 控制台输出 | colorlog 彩色日志 |
| 文件日志 | RotatingFileHandler |
| 文件大小 | 10MB |
| 备份数量 | 5 个 |
| 日志级别 | INFO |

---

### Decision Impact Analysis

**实现顺序:**

1. 项目初始化 + 基础结构
2. 配置管理 + 日志系统
3. 数据库 + 模型定义
4. Polymarket API 客户端
5. LLM API 客户端
6. 市场筛选模块
7. LLM 分析引擎
8. 风险控制模块
9. Paper Trading 模块
10. 交易执行模块
11. FastAPI 后端
12. React Dashboard 前端

**跨组件依赖:**

```
配置管理 ─────────────────────────────────────────┐
                                                   ▼
日志系统 ◄──────────────────────────────────── 所有组件
                                                   ▲
数据库 ────────────────────────────────────────────┤
                                                   │
Polymarket API ──► 市场筛选 ──► LLM 分析 ──► 风险控制 ──► 交易执行
      │                                              │
      └──────────────── Paper Trading ◄─────────────┘
                            │
                            ▼
                      FastAPI Dashboard
```

---

## Implementation Patterns & Consistency Rules

### Naming Patterns

| 类别 | 规则 | 示例 |
|------|------|------|
| **数据库表** | snake_case 复数 | `markets`, `predictions`, `trades` |
| **数据库列** | snake_case | `market_id`, `created_at`, `predicted_probability` |
| **Python 文件** | snake_case | `market_filter.py`, `llm_analyzer.py` |
| **Python 类** | PascalCase | `TradeInfo`, `MarketFilter`, `LLMAnalyzer` |
| **Python 函数/变量** | snake_case | `get_markets()`, `filter_by_liquidity()` |
| **Python 常量** | UPPER_SNAKE_CASE | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| **API 端点** | kebab-case 复数 | `/api/markets`, `/api/trades` |
| **React 组件** | PascalCase | `MarketCard.tsx`, `TradeList.tsx` |
| **React 文件** | PascalCase | `MarketCard.tsx`, `TradeList.tsx` |
| **TypeScript 接口** | PascalCase | `Market`, `Trade`, `Prediction` |

---

### Structure Patterns

**项目组织:**

```
polymarket-trader/
├── src/                      # Python 后端
│   ├── models/               # Pydantic 模型
│   ├── api/                  # API 客户端
│   ├── core/                 # 核心逻辑
│   ├── analysis/             # 分析模块
│   ├── trading/              # 交易模块
│   ├── storage/              # 数据库操作
│   ├── dashboard/            # FastAPI 后端
│   └── utils/                # 工具函数
├── dashboard/                # React 前端
│   └── src/
│       ├── components/       # UI 组件
│       ├── pages/            # 页面
│       ├── hooks/            # 自定义 hooks
│       ├── api/              # API 调用
│       └── types/            # TypeScript 类型
├── tests/                    # 测试 (镜像 src 结构)
│   ├── test_models/
│   ├── test_api/
│   └── ...
├── logs/                     # 日志目录
├── data/                     # 数据库文件
├── .env                      # 配置文件
├── .env.example              # 配置模板
├── requirements.txt          # Python 依赖
└── README.md
```

---

### Format Patterns

**API 响应格式:**

```json
// 成功响应
{
  "success": true,
  "data": { ... }
}

// 错误响应
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid market ID"
  }
}

// 列表响应
{
  "success": true,
  "data": [...],
  "meta": {
    "total": 100,
    "page": 1,
    "per_page": 20
  }
}
```

**日期时间格式:** ISO 8601
- API: `2026-02-15T10:30:00Z`
- 数据库: `2026-02-15 10:30:00`
- 显示: `2026-02-15 10:30`

**金额格式:**
- API/数据库: 浮点数 `123.45`
- 显示: `$123.45`

**概率格式:**
- API/数据库: 0-1 范围 `0.75`
- 显示: `75%`

---

### Logging Patterns

**日志格式:**

```
{timestamp} | {level:8} | {thread:12} | {module} | {emoji} {message}
```

**示例:**

```
2026-02-15 10:30:00 | INFO     | MainThread  | polymarket_trader.api.polymarket | ✅ Fetched 50 markets
2026-02-15 10:30:05 | WARNING  | MainThread  | polymarket_trader.analysis.filter | ⚠️ Market filtered: low liquidity
2026-02-15 10:30:10 | ERROR    | MainThread  | polymarket_trader.api.llm | ❌ LLM API error: timeout
2026-02-15 10:30:15 | INFO     | MainThread  | polymarket_trader.trading.executor | 💰 Trade executed: BUY YES @ 0.65
```

**日志级别使用:**

| 级别 | 用途 |
|------|------|
| DEBUG | 详细调试信息 |
| INFO | 正常操作信息 |
| WARNING | 警告但不影响运行 |
| ERROR | 错误但可恢复 |
| CRITICAL | 严重错误需关注 |

**Emoji 日志:**

| 操作 | Emoji |
|------|-------|
| 成功 | ✅ |
| 警告 | ⚠️ |
| 错误 | ❌ |
| 交易 | 💰 |
| 分析 | 🧠 |
| 数据 | 📊 |
| 网络 | 🌐 |

---

### Error Handling Patterns

**异常层次:**

```python
class BotError(Exception):
    """基础异常"""
    pass

class ConfigurationError(BotError):
    """配置错误"""
    pass

class NetworkError(BotError):
    """网络错误"""
    pass

class TradingError(BotError):
    """交易错误"""
    pass

class ValidationError(BotError):
    """验证错误"""
    pass
```

**错误处理模式:**

```python
try:
    result = await api_call()
except NetworkError as e:
    logger.error(f"❌ Network error: {e}")
    # 重试或降级处理
except ValidationError as e:
    logger.warning(f"⚠️ Validation error: {e}")
    # 跳过或修正数据
except Exception as e:
    logger.critical(f"🔥 Unexpected error: {e}")
    raise
```

---

### Code Style Guidelines

**Python:**

- 使用 `black` 格式化
- 使用 `isort` 排序 import
- 使用 `mypy` 类型检查
- 最大行宽: 88 字符
- 使用 `f-string` 格式化字符串

**TypeScript:**

- 使用 `prettier` 格式化
- 使用 `eslint` 检查
- 使用严格模式
- 优先使用 `interface` 而非 `type`
- 使用 `async/await` 而非 `.then()`

---

### Pattern Examples

**✅ Good Examples:**

```python
# Python 函数命名
def get_markets_by_category(category: str) -> list[Market]:
    ...

# Python 类命名
class MarketFilter:
    ...

# API 端点
@router.get("/api/markets/{market_id}")
async def get_market(market_id: str):
    ...
```

```typescript
// React 组件
export function MarketCard({ market }: { market: Market }) {
  ...
}

// TypeScript 接口
interface Trade {
  id: string;
  marketId: string;
  amount: number;
}
```

**❌ Anti-Patterns:**

```python
# 不要用 camelCase
def getMarketsByCategory(category):
    ...

# 不要用单数表名
CREATE TABLE market (...)

# 不要用不一致的命名
def Get_Markets():
    ...
```

---

## Project Structure & Boundaries

### Complete Project Directory Structure

```
polymarket-trader/
├── README.md                           # 项目说明
├── .env                                # 环境变量 (gitignore)
├── .env.example                        # 环境变量模板
├── .gitignore                          # Git 忽略文件
├── requirements.txt                    # Python 依赖
├── pyproject.toml                      # 项目配置 (black, isort, mypy)
│
├── src/                                # Python 源代码
│   ├── __init__.py
│   ├── main.py                         # 主入口点
│   ├── config.py                       # 配置管理
│   ├── exceptions.py                   # 自定义异常
│   │
│   ├── models/                         # Pydantic 数据模型
│   │   ├── __init__.py
│   │   ├── market.py                   # Market, MarketCategory
│   │   ├── prediction.py               # Prediction, PredictionResult
│   │   ├── trade.py                    # Trade, TradeType, TradeMode
│   │   ├── position.py                 # Position, PositionStatus
│   │   └── statistics.py               # Statistics, DailyStats
│   │
│   ├── core/                           # 核心逻辑
│   │   ├── __init__.py
│   │   ├── state.py                    # ThreadSafeState
│   │   ├── scheduler.py                # APScheduler 配置
│   │   └── circuit_breaker.py          # 熔断机制
│   │
│   ├── api/                            # 外部 API 客户端
│   │   ├── __init__.py
│   │   ├── base.py                     # 基础 API 类
│   │   ├── polymarket.py               # Polymarket API 客户端
│   │   └── llm.py                      # LLM API 客户端 (GLM)
│   │
│   ├── analysis/                       # 分析模块
│   │   ├── __init__.py
│   │   ├── market_filter.py            # 市场筛选器
│   │   ├── llm_analyzer.py             # LLM 分析引擎
│   │   └── prompts.py                  # LLM 提示词模板
│   │
│   ├── trading/                        # 交易模块
│   │   ├── __init__.py
│   │   ├── paper_trading.py            # Paper Trading 模式
│   │   ├── executor.py                 # 交易执行器
│   │   ├── risk_control.py             # 风险控制
│   │   └── position_manager.py         # 持仓管理
│   │
│   ├── storage/                        # 数据存储
│   │   ├── __init__.py
│   │   ├── database.py                 # SQLite 数据库操作
│   │   ├── migrations.py               # 数据库迁移
│   │   └── repositories/               # 数据仓库
│   │       ├── __init__.py
│   │       ├── market_repo.py
│   │       ├── prediction_repo.py
│   │       ├── trade_repo.py
│   │       └── position_repo.py
│   │
│   ├── dashboard/                      # FastAPI 后端
│   │   ├── __init__.py
│   │   ├── app.py                      # FastAPI 应用
│   │   ├── routes/                     # API 路由
│   │   │   ├── __init__.py
│   │   │   ├── markets.py
│   │   │   ├── trades.py
│   │   │   ├── positions.py
│   │   │   ├── predictions.py
│   │   │   └── statistics.py
│   │   └── dependencies.py             # 依赖注入
│   │
│   └── utils/                          # 工具函数
│       ├── __init__.py
│       ├── logger.py                   # 日志配置
│       ├── retry.py                    # 重试装饰器
│       ├── crypto.py                   # 加密工具
│       └── helpers.py                  # 辅助函数
│
├── dashboard/                          # React 前端
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx                    # 入口文件
│       ├── App.tsx                     # 根组件
│       ├── index.css                   # 全局样式
│       │
│       ├── components/                 # UI 组件
│       │   ├── ui/                     # shadcn/ui 组件
│       │   ├── charts/                 # 图表组件
│       │   ├── MarketCard.tsx
│       │   ├── TradeList.tsx
│       │   └── StatsCard.tsx
│       │
│       ├── pages/                      # 页面组件
│       │   ├── Home.tsx
│       │   ├── Positions.tsx
│       │   ├── Trades.tsx
│       │   ├── Predictions.tsx
│       │   └── Settings.tsx
│       │
│       ├── hooks/                      # 自定义 hooks
│       ├── api/                        # API 调用
│       ├── types/                      # TypeScript 类型
│       └── lib/                        # 工具库
│
├── tests/                              # 测试
│   ├── conftest.py
│   ├── test_models/
│   ├── test_api/
│   ├── test_analysis/
│   ├── test_trading/
│   └── test_storage/
│
├── logs/                               # 日志目录
│   └── polymarket_trader.log
│
├── data/                               # 数据目录
│   └── polymarket.db                   # SQLite 数据库
│
└── scripts/                            # 脚本
    ├── setup.sh                        # 初始化脚本
    ├── run.sh                          # 运行脚本
    └── backup_db.sh                    # 数据库备份脚本
```

---

### Requirements to Structure Mapping

| 功能需求 | 模块位置 | 关键文件 |
|----------|----------|----------|
| **F1: LLM 分析引擎** | `src/analysis/` | `llm_analyzer.py`, `prompts.py` |
| **F2: Paper Trading** | `src/trading/` | `paper_trading.py` |
| **F3: 风险控制** | `src/trading/`, `src/core/` | `risk_control.py`, `circuit_breaker.py` |
| **F4: 市场筛选** | `src/analysis/` | `market_filter.py` |
| **F5: 预测追踪** | `src/storage/` | `prediction_repo.py` |
| **F6: 学习日志** | `src/trading/` | `executor.py` |
| **F7: Web Dashboard** | `src/dashboard/`, `dashboard/` | `app.py`, `pages/*.tsx` |

---

### Architectural Boundaries

**API Boundaries:**

| 边界 | 描述 |
|------|------|
| Polymarket API | `src/api/polymarket.py` - 外部 API 封装 |
| LLM API | `src/api/llm.py` - GLM API 封装 |
| Dashboard API | `src/dashboard/routes/` - 内部 REST API |

**Component Boundaries:**

| 层级 | 组件 | 职责 |
|------|------|------|
| 数据层 | `src/storage/` | 数据持久化 |
| 服务层 | `src/api/`, `src/analysis/`, `src/trading/` | 业务逻辑 |
| 表现层 | `src/dashboard/`, `dashboard/` | API 端点 + UI |

**Data Flow:**

```
外部 API (Polymarket/LLM)
        ↓
    数据模型 (models/)
        ↓
    业务逻辑 (analysis/trading/)
        ↓
    数据存储 (storage/)
        ↓
    Dashboard API (dashboard/routes/)
        ↓
    前端显示 (dashboard/src/)
```

---

### Integration Points

**Internal Communication:**

- 模块间通过 Pydantic 模型传递数据
- 使用依赖注入模式（FastAPI）
- 日志系统贯穿所有模块

**External Integrations:**

| 集成 | 位置 | 协议 |
|------|------|------|
| Polymarket | `src/api/polymarket.py` | REST + WebSocket |
| GLM LLM | `src/api/llm.py` | REST (OpenAI 兼容) |
| SQLite | `src/storage/database.py` | 本地文件 |

---

## Architecture Validation Results

### Coherence Validation ✅

| 检查项 | 状态 | 说明 |
|--------|------|------|
| **决策兼容性** | ✅ | Python + FastAPI + SQLite + React 全部兼容 |
| **版本兼容性** | ✅ | 所有库版本明确且兼容 |
| **模式一致性** | ✅ | 命名、结构、通信模式一致 |
| **结构对齐** | ✅ | 项目结构支持所有架构决策 |

### Requirements Coverage Validation ✅

**功能需求覆盖:**

| 需求 | 状态 | 架构支持 |
|------|------|----------|
| F1: LLM 分析引擎 | ✅ | `src/analysis/llm_analyzer.py` |
| F2: Paper Trading | ✅ | `src/trading/paper_trading.py` |
| F3: 风险控制 | ✅ | `src/trading/risk_control.py` + `src/core/circuit_breaker.py` |
| F4: 市场筛选 | ✅ | `src/analysis/market_filter.py` |
| F5: 预测追踪 | ✅ | `src/storage/repositories/prediction_repo.py` |
| F6: 学习日志 | ✅ | `src/trading/executor.py` + 日志系统 |
| F7: Web Dashboard | ✅ | `src/dashboard/` + `dashboard/` |

**非功能需求覆盖:**

| NFR | 状态 | 架构支持 |
|-----|------|----------|
| 99% uptime | ✅ | APScheduler + 自动恢复 |
| LLM 响应 < 30s | ✅ | 超时配置 + 重试机制 |
| Dashboard < 2s | ✅ | FastAPI + React Vite |
| API Key 加密 | ✅ | cryptography + .env |
| 日志脱敏 | ✅ | `src/utils/logger.py` |

### Implementation Readiness Validation ✅

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 关键决策已记录 | ✅ | 全部带版本号 |
| 实现模式完整 | ✅ | 命名、结构、格式、日志模式齐全 |
| 一致性规则清晰 | ✅ | 有示例和反例 |
| 项目结构完整 | ✅ | 所有文件和目录已定义 |

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**✅ Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**✅ Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** ✅ READY FOR IMPLEMENTATION

**Confidence Level:** HIGH

**Key Strengths:**
- 清晰的模块化架构
- 完整的风险控制设计
- Paper Testing 优先策略
- 参考项目验证的技术方案

**Areas for Future Enhancement:**
- Phase 2: 通知系统
- Phase 3: 回测系统
- Phase 3: 多 LLM 交叉验证
- Phase 3: 自适应参数

### Implementation Handoff

**First Implementation Priority:**

```bash
# 1. 创建项目结构
mkdir -p polymarket-trader/{src/{models,core,api,analysis,trading,storage,dashboard,utils},logs,data,tests,scripts}

# 2. 初始化虚拟环境
cd polymarket-trader
python -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install py-clob-client web3 openai fastapi uvicorn aiosqlite requests python-dotenv pydantic colorlog apscheduler halo

# 4. 创建配置文件
cp .env.example .env
# 编辑 .env 填入 API keys

# 5. 初始化数据库
python -c "from src.storage.database import init_db; init_db()"
```

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and boundaries
- Refer to this document for all architectural questions

