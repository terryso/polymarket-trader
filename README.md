# Polymarket Trader

[![BMAD](https://bmad-badge.vercel.app/terryso/polymarket-trader.svg)](https://github.com/bmad-code-org/BMAD-METHOD)

LLM 驱动的 Polymarket 自动交易系统，支持纸上交易和实盘交易模式。

## 功能特性

- **LLM 智能分析** - 使用 GLM-4/5 进行市场分析和交易决策
- **自动交易** - 支持纸上交易（模拟）和实盘交易两种模式
- **风险管理** - 止损、止盈、熔断机制、仓位控制
- **退出策略** - 自动止盈、止损、信号退出、时间退出
- **Telegram 通知** - 实时交易通知和远程命令控制
- **Web Dashboard** - React 前端实时监控持仓和交易历史

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10+, FastAPI, Pydantic, aiosqlite |
| 前端 | React 18, TypeScript, Vite, TailwindCSS, shadcn/ui |
| LLM | GLM-4/5 (OpenAI 兼容协议) |
| 交易 | py-clob-client, Web3 |
| 测试 | pytest (Python), Vitest + Testing Library (React) |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+ (前端)
- Polymarket 账户和 API 密钥

### 1. 克隆项目

```bash
git clone https://github.com/terryso/polymarket-trader.git
cd polymarket-trader
```

### 2. Python 后端设置

```bash
# 创建并激活虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt -r requirements-dev.txt

# 以可编辑模式安装项目
pip install -e .
```

### 3. React 前端设置

```bash
# 切换到 Node.js 23
nvm use 23

cd dashboard
npm install
```

### 4. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 设置文件权限
chmod 600 .env
```

编辑 `.env` 文件，填入你的配置：

```bash
# LLM 配置 (必需)
LLM_API_KEY=your_glm_api_key
LLM_MODEL=glm-4

# Polymarket 配置 (必需)
PK=your_private_key
YOUR_PROXY_WALLET=your_proxy_wallet_address
BOT_TRADER_ADDRESS=your_trader_address

# 交易模式
TRADING_MODE=paper  # paper=模拟, live=实盘
```

## 运行测试

### Python 后端测试

```bash
source .venv/bin/activate

# 单元测试 (默认，快速)
pytest tests/ -v

# 集成测试 (需要网络)
pytest tests/integration/ -v -m integration

# 所有测试
pytest tests/ -v -m ""

# 带覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

### React 前端测试

```bash
nvm use 23
cd dashboard

npm test              # 单次运行
npm run test:watch    # 监视模式
```

## 代码质量

```bash
# Python
black src/ tests/     # 格式化
isort src/ tests/     # 排序 imports
mypy src/             # 类型检查
ruff check .          # Lint

# React
cd dashboard && npm run lint
```

## 主要配置项

| 配置 | 说明 | 默认值 |
|------|------|--------|
| `TRADING_MODE` | 交易模式 (paper/live) | paper |
| `TRADE_UNIT` | 基础交易单位 (USD) | 10.0 |
| `MIN_CONFIDENCE` | 最小置信度 | 0.75 |
| `MIN_EDGE` | 最小边缘值 | 0.10 |
| `MAX_OPEN_MARKETS` | 最大持仓数量 | 3 |
| `TAKE_PROFIT_PCT` | 止盈百分比 | 0.50 |
| `STOP_LOSS_PCT` | 止损百分比 | -0.30 |
| `TELEGRAM_ENABLED` | 启用 Telegram 通知 | false |

完整配置请参考 [.env.example](.env.example)。

## 项目结构

```
polymarket-trader/
├── src/                    # Python 后端
│   ├── api/                # API 客户端 (Polymarket)
│   ├── core/               # 核心逻辑
│   ├── trading/            # 交易执行
│   ├── analysis/           # 市场分析
│   ├── storage/            # 数据存储
│   └── dashboard/          # FastAPI 后端
├── dashboard/              # React 前端
│   └── src/
│       ├── components/     # React 组件
│       └── pages/          # 页面
├── tests/                  # Python 测试
│   └── integration/        # 集成测试
├── requirements.txt        # Python 依赖
└── pyproject.toml          # 项目配置
```

## 安全注意事项

- **永远不要**提交 `.env` 文件到版本控制
- 设置 `.env` 文件权限: `chmod 600 .env`
- 私钥和 API 密钥需妥善保管
- 实盘交易前建议先用纸上交易模式测试

## License

MIT
