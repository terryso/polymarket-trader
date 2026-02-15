# Polymarket Trader - Claude Code 项目指南

## 项目概述

LLM 驱动的 Polymarket 自动交易系统，包含 Python 后端和 React 前端 Dashboard。

## 技术栈

- **后端**: Python 3.10+, FastAPI, Pydantic, aiosqlite
- **前端**: React 18, TypeScript, Vite, TailwindCSS, shadcn/ui
- **测试**: pytest (Python), Vitest + Testing Library (React)

---

## 环境设置

### Python 后端

```bash
# 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt -r requirements-dev.txt
```

### React 前端

```bash
cd dashboard
npm install
```

---

## 运行测试

### Python 后端测试

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/test_config.py -v
python -m pytest tests/test_exceptions.py -v
python -m pytest tests/test_logger.py -v

# 运行带覆盖率报告
python -m pytest tests/ --cov=src --cov-report=html

# 运行特定测试类
python -m pytest tests/test_config.py::TestSettings -v
```

### React 前端测试

```bash
cd dashboard

# 运行所有测试（单次）
npm test

# 运行测试监视模式
npm run test:watch

# 运行特定测试文件
npx vitest run src/components/dashboard/StatCard.test.tsx
```

---

## 代码质量

### Python

```bash
# 格式化代码
black src/ tests/

# 排序 imports
isort src/ tests/

# 类型检查
mypy src/

# Lint
flake8 src/ tests/
```

### React

```bash
cd dashboard

# Lint
npm run lint
```

---

## 项目结构

```
polymarket-trader/
├── src/                    # Python 后端源码
│   ├── config.py           # 配置管理
│   ├── exceptions.py       # 自定义异常
│   ├── utils/logger.py     # 日志配置
│   ├── api/                # API 路由
│   ├── core/               # 核心逻辑
│   ├── trading/            # 交易逻辑
│   ├── analysis/           # 分析模块
│   └── storage/            # 数据存储
├── tests/                  # Python 测试
│   ├── conftest.py         # Pytest 配置和 fixtures
│   ├── test_config.py      # 配置测试
│   ├── test_exceptions.py  # 异常测试
│   └── test_logger.py      # 日志测试
├── dashboard/              # React 前端
│   ├── src/
│   │   ├── components/     # React 组件
│   │   ├── pages/          # 页面组件
│   │   ├── lib/            # 工具函数
│   │   └── test/           # 测试配置
│   └── package.json
├── requirements.txt        # Python 依赖
├── requirements-dev.txt    # Python 开发依赖
└── pyproject.toml          # Python 项目配置
```

---

## 常用命令速查

| 任务 | 命令 |
|------|------|
| 激活 Python 虚拟环境 | `source .venv/bin/activate` |
| 运行 Python 测试 | `python -m pytest tests/ -v` |
| 安装前端依赖 | `cd dashboard && npm install` |
| 运行前端测试 | `cd dashboard && npm test` |
| 启动前端开发服务器 | `cd dashboard && npm run dev` |

---

## 注意事项

- 虚拟环境 `.venv/` 已在 `.gitignore` 中，无需提交
- 前端测试使用 Vitest，配置在 `dashboard/vitest.config.ts`
- Python 测试使用 pytest，配置在 `pyproject.toml`
