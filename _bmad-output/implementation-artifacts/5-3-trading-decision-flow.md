# Story 5.3: 交易决策流程

Status: review

## Story

As a **用户**,
I want **系统能够基于 LLM 分析和风险检查自动做出交易决策**,
So that **交易过程完全自动化**.

## Acceptance Criteria

**Given** Paper Trading 执行器和风险控制器已实现 (Story 5.2, Story 4.4)
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

## Tasks / Subtasks

- [x] Task 1: 创建 TradingExecutor 类结构 (AC: 1)
  - [x] 1.1 创建 `src/trading/executor.py` 文件
  - [x] 1.2 定义 `TradingExecutor` 类
  - [x] 1.3 实现构造函数，注入所需依赖 (LLMAnalyzer, RiskController, PaperTradingExecutor, ThreadSafeState)
  - [x] 1.4 定义 `TradingDecision` 数据类用于返回决策结果
  - [x] 1.5 定义 `TradeMode` 枚举 (PAPER/LIVE) 如果尚未存在 - 已存在于 src/models/trade.py

- [x] Task 2: 实现 process_market 核心方法 (AC: 2)
  - [x] 2.1 实现 `process_market(market: Market)` 方法签名
  - [x] 2.2 调用 `llm_analyzer.analyze_market(market)` 获取 LLM 分析结果
  - [x] 2.3 调用 `risk_controller.check_trade_allowed(prediction, market)` 进行风险检查
  - [x] 2.4 如果不允许交易，记录原因并返回
  - [x] 2.5 调用 `_calculate_position_size(position_ratio)` 计算交易金额
  - [x] 2.6 调用 `paper_executor.execute_trade(market, prediction, amount)` 执行交易
  - [x] 2.7 记录交易日志 (使用 emoji)
  - [x] 2.8 返回 TradingDecision 结果

- [x] Task 3: 实现 process_markets 批量处理方法
  - [x] 3.1 实现 `process_markets(markets: list[Market])` 方法
  - [x] 3.2 遍历市场列表，逐个调用 `process_market`
  - [x] 3.3 收集所有交易决策结果
  - [x] 3.4 记录批量处理统计日志
  - [x] 3.5 返回 `list[TradingDecision]`

- [x] Task 4: 实现辅助方法
  - [x] 4.1 实现 `_calculate_position_size(position_ratio: float) -> float` - 根据比例计算仓位
  - [x] 4.2 跳过原因记录在 process_market 中 (日志)
  - [x] 4.3 交易结果记录在 process_market 中 (日志)

- [x] Task 5: 实现错误处理和边界情况 (AC: 3)
  - [x] 5.1 处理 LLM 分析失败情况
  - [x] 5.2 处理风险检查异常情况
  - [x] 5.3 处理 Paper Trading 执行失败情况
  - [x] 5.4 实现全局异常捕获，确保单个市场失败不影响其他市场

- [x] Task 6: 更新模块导出 (AC: All)
  - [x] 6.1 更新 `src/trading/__init__.py` 导出 `TradingExecutor`
  - [x] 6.2 更新 `__all__` 列表

- [x] Task 7: 编写单元测试 (AC: All)
  - [x] 7.1 创建 `tests/test_trading/test_executor.py`
  - [x] 7.2 测试 process_market 成功场景 (完整流程)
  - [x] 7.3 测试风险检查拒绝交易场景
  - [x] 7.4 测试 LLM 分析失败场景
  - [x] 7.5 测试 Paper Trading 执行失败场景
  - [x] 7.6 测试 process_markets 批量处理
  - [x] 7.7 测试仓位计算逻辑
  - [x] 7.8 Mock 所有外部依赖

- [x] Task 8: 代码质量检查 (AC: All)
  - [x] 8.1 运行 `mypy src/trading/executor.py` 无错误
  - [x] 8.2 运行 `black --check` 通过
  - [x] 8.3 运行 `isort --check` 通过
  - [x] 8.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md]

**交易决策流程设计原则:**
- 端到端自动化: 从市场输入到交易执行无需人工干预
- 风险优先: 风险检查不通过则不执行交易
- 可配置模式: 支持 PAPER 和 LIVE 两种模式
- 错误隔离: 单个市场处理失败不影响其他市场

### 已有组件 (必须复用)

**LLMAnalyzer** [Source: src/analysis/llm_analyzer.py]
```python
class LLMAnalyzer:
    async def analyze_market(self, market: Market) -> PredictionResult: ...
```

**RiskController** [Source: src/trading/risk_control.py]
```python
class RiskCheckResult:
    allowed: bool
    reason: str
    position_ratio: float

class RiskController:
    def check_trade_allowed(
        self, prediction: PredictionResult, market: Market
    ) -> RiskCheckResult: ...
```

**PaperTradingExecutor** [Source: src/trading/paper_trading.py]
```python
class PaperTradeResult:
    trade: Trade | None
    position: Position | None
    success: bool
    error_message: str | None

class PaperTradingExecutor:
    async def execute_trade(
        self, market: Market, prediction: PredictionResult, amount: float,
        prediction_id: int | None = None
    ) -> PaperTradeResult: ...
```

**ThreadSafeState** [Source: src/core/state.py]
```python
class ThreadSafeState:
    async def get_state(self) -> StateSnapshot: ...
    async def update_capital(self, amount: float) -> None: ...
```

**Settings** [Source: src/config.py]
```python
class Settings:
    INITIAL_CAPITAL: float = 200.0
    MAX_SINGLE_RATIO: float = 0.20
    MIN_BET: float = 5.0
    TRADE_MODE: str = "PAPER"  # PAPER or LIVE
```

### 数据模型 [Source: src/models/]

**Market** [Source: src/models/market.py]
```python
class Market(BaseModel):
    id: str
    title: str
    description: str | None
    category: str | None
    yes_price: float | None
    no_price: float | None
    liquidity: float | None
    deadline: datetime | None
```

**PredictionResult** [Source: src/models/prediction.py]
```python
class Recommendation(str, Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    NO_TRADE = "NO_TRADE"

class PredictionResult(BaseModel):
    predicted_probability: float
    confidence: float
    reasoning: str
    key_assumptions: list[str]
    recommendation: Recommendation
    edge: float | None
    id: int | None  # 数据库 ID (如果已保存)
```

**Trade** [Source: src/models/trade.py]
```python
class TradeType(str, Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    SELL = "SELL"

class TradeMode(str, Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"

class Trade(BaseModel):
    id: int
    market_id: str
    trade_type: TradeType
    mode: TradeMode
    amount: float
    price: float
    shares: float | None
    status: TradeStatus
    llm_prediction_id: int | None
    position_id: int | None
    created_at: datetime | None
```

### 交易决策流程图

```
┌─────────────────────────────────────────────────────────────────────┐
│                     交易决策流程 (Trading Decision Flow)             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  process_market(market: Market) -> TradingDecision                 │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 1. LLM 分析                                                  │   │
│  │    prediction = await llm_analyzer.analyze_market(market)   │   │
│  │                                                              │   │
│  │    On Error:                                                 │   │
│  │    - Log error (🧠 LLM 分析失败)                             │   │
│  │    - Return TradingDecision(success=False, error="...")      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                           │                                         │
│                           ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 2. 风险检查                                                  │   │
│  │    check = risk_controller.check_trade_allowed(              │   │
│  │        prediction, market                                    │   │
│  │    )                                                         │   │
│  │                                                              │   │
│  │    If not check.allowed:                                     │   │
│  │    - Log skip reason (⚠️ 交易被拒绝: {reason})               │   │
│  │    - Return TradingDecision(skipped=True, reason="...")      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                           │                                         │
│                           ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 3. 计算仓位                                                  │   │
│  │    state = await self._state.get_state()                     │   │
│  │    capital = state.current_capital                           │   │
│  │    amount = capital * check.position_ratio                   │   │
│  │                                                              │   │
│  │    Validate:                                                 │   │
│  │    - amount >= MIN_BET ($5)                                  │   │
│  │    - amount <= capital * MAX_SINGLE_RATIO (20%)              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                           │                                         │
│                           ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 4. 执行交易 (Paper Trading)                                  │   │
│  │    result = await paper_executor.execute_trade(              │   │
│  │        market, prediction, amount, prediction.id             │   │
│  │    )                                                         │   │
│  │                                                              │   │
│  │    If not result.success:                                    │   │
│  │    - Log error (❌ 交易执行失败)                              │   │
│  │    - Return TradingDecision(success=False, error="...")      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                           │                                         │
│                           ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 5. 记录结果                                                  │   │
│  │    logger.info(                                              │   │
│  │        f"✅ 交易完成: {market.id} "                           │   │
│  │        f"{result.trade.trade_type.value} "                   │   │
│  │        f"${amount:.2f}"                                      │   │
│  │    )                                                         │   │
│  │                                                              │   │
│  │    Return TradingDecision(                                   │   │
│  │        success=True,                                         │   │
│  │        trade=result.trade,                                   │   │
│  │        position=result.position                              │   │
│  │    )                                                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 实现模板

**src/trading/executor.py:**

```python
"""Trading executor for the Polymarket Trader application.

This module provides the TradingExecutor class that orchestrates
the complete trading decision flow from LLM analysis to trade execution.

Story 5.3: 交易决策流程

Example:
    >>> from src.trading.executor import TradingExecutor
    >>> from src.analysis.llm_analyzer import LLMAnalyzer
    >>> from src.trading.risk_control import RiskController
    >>> from src.trading.paper_trading import PaperTradingExecutor
    >>> from src.core.state import ThreadSafeState
    >>>
    >>> # Initialize components
    >>> llm_analyzer = LLMAnalyzer()
    >>> risk_controller = RiskController(state)
    >>> paper_executor = PaperTradingExecutor(trade_repo, position_manager, state)
    >>>
    >>> executor = TradingExecutor(
    ...     llm_analyzer=llm_analyzer,
    ...     risk_controller=risk_controller,
    ...     paper_executor=paper_executor,
    ...     state=state,
    ...     settings=settings
    ... )
    >>>
    >>> # Process a single market
    >>> decision = await executor.process_market(market)
    >>> if decision.success and decision.trade:
    ...     print(f"Trade executed: {decision.trade.id}")
"""

from __future__ import annotations

__all__ = ["TradingExecutor", "TradingDecision"]

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.config import Settings
from src.exceptions import TradingError
from src.models.trade import Trade
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.analysis.llm_analyzer import LLMAnalyzer
    from src.core.state import ThreadSafeState
    from src.models.market import Market
    from src.models.position import Position
    from src.models.prediction import PredictionResult
    from src.trading.paper_trading import PaperTradeResult, PaperTradingExecutor
    from src.trading.risk_control import RiskCheckResult, RiskController


logger = get_logger(__name__)


@dataclass
class TradingDecision:
    """Result of a trading decision for a single market.

    Attributes:
        market_id: ID of the processed market
        success: Whether the decision process completed successfully
        skipped: Whether the trade was skipped (e.g., risk check failed)
        trade: The executed trade (if any)
        position: The opened position (if any)
        prediction: The LLM prediction (if analysis was performed)
        reason: Reason for skip or failure
        error_message: Error message if process failed
    """

    market_id: str
    success: bool = True
    skipped: bool = False
    trade: Trade | None = None
    position: "Position | None" = None
    prediction: "PredictionResult | None" = None
    reason: str | None = None
    error_message: str | None = None


class TradingExecutor:
    """Trading executor that orchestrates the complete trading decision flow.

    Coordinates LLM analysis, risk checking, and trade execution to
    automatically process markets and make trading decisions.

    Attributes:
        _llm_analyzer: LLMAnalyzer for market analysis
        _risk_controller: RiskController for risk checks
        _paper_executor: PaperTradingExecutor for trade execution
        _state: ThreadSafeState for capital tracking
        _settings: Application settings

    Example:
        >>> executor = TradingExecutor(
        ...     llm_analyzer=analyzer,
        ...     risk_controller=controller,
        ...     paper_executor=paper_exec,
        ...     state=state,
        ...     settings=settings
        ... )
        >>> decision = await executor.process_market(market)
        >>> if decision.success and not decision.skipped:
        ...     print(f"Trade executed: {decision.trade.id}")
    """

    def __init__(
        self,
        llm_analyzer: "LLMAnalyzer",
        risk_controller: "RiskController",
        paper_executor: "PaperTradingExecutor",
        state: "ThreadSafeState",
        settings: Settings,
    ) -> None:
        """Initialize trading executor.

        Args:
            llm_analyzer: LLM analyzer for market predictions
            risk_controller: Risk controller for trade validation
            paper_executor: Paper trading executor for trade execution
            state: Thread-safe state for capital tracking
            settings: Application settings
        """
        self._llm_analyzer = llm_analyzer
        self._risk_controller = risk_controller
        self._paper_executor = paper_executor
        self._state = state
        self._settings = settings
        self._logger = get_logger(__name__)
        self._logger.info(
            f"TradingExecutor initialized (mode={settings.TRADE_MODE})"
        )

    async def process_market(self, market: "Market") -> TradingDecision:
        """Process a single market and make a trading decision.

        Executes the complete trading flow:
        1. LLM analysis -> get prediction
        2. Risk check -> validate trade allowed
        3. Position sizing -> calculate amount
        4. Trade execution -> execute paper trade

        Args:
            market: Market to process

        Returns:
            TradingDecision with result of the trading decision

        Example:
            >>> decision = await executor.process_market(market)
            >>> if decision.success and decision.trade:
            ...     print(f"Trade ID: {decision.trade.id}")
        """
        self._logger.info(f"🔍 Processing market: {market.id} - {market.title}")

        try:
            # 1. LLM Analysis
            self._logger.debug(f"🧠 Analyzing market {market.id}...")
            prediction = await self._llm_analyzer.analyze_market(market)
            self._logger.info(
                f"🧠 LLM analysis complete: recommendation={prediction.recommendation.value}, "
                f"confidence={prediction.confidence:.2%}"
            )

            # 2. Risk Check
            self._logger.debug(f"⚠️ Running risk check for market {market.id}...")
            risk_check = self._risk_controller.check_trade_allowed(
                prediction, market
            )

            if not risk_check.allowed:
                self._logger.info(
                    f"⚠️ Trade rejected for market {market.id}: {risk_check.reason}"
                )
                return TradingDecision(
                    market_id=market.id,
                    success=True,
                    skipped=True,
                    prediction=prediction,
                    reason=risk_check.reason,
                )

            # 3. Calculate Position Size
            amount = await self._calculate_position_size(risk_check.position_ratio)
            self._logger.info(
                f"📊 Position size calculated: ${amount:.2f} "
                f"(ratio={risk_check.position_ratio:.2%})"
            )

            # 4. Execute Trade (Paper Trading)
            self._logger.debug(f"💰 Executing paper trade for market {market.id}...")
            result = await self._paper_executor.execute_trade(
                market=market,
                prediction=prediction,
                amount=amount,
                prediction_id=prediction.id,
            )

            if not result.success:
                self._logger.error(
                    f"❌ Trade execution failed for market {market.id}: "
                    f"{result.error_message}"
                )
                return TradingDecision(
                    market_id=market.id,
                    success=False,
                    prediction=prediction,
                    error_message=result.error_message,
                )

            # 5. Log Success
            self._logger.info(
                f"✅ Trade completed for market {market.id}: "
                f"{result.trade.trade_type.value} "
                f"{result.trade.shares:.2f} shares @ ${result.trade.price:.4f} "
                f"= ${amount:.2f}"
            )

            return TradingDecision(
                market_id=market.id,
                success=True,
                skipped=False,
                trade=result.trade,
                position=result.position,
                prediction=prediction,
            )

        except Exception as e:
            self._logger.error(
                f"❌ Unexpected error processing market {market.id}: {e}"
            )
            return TradingDecision(
                market_id=market.id,
                success=False,
                error_message=f"Unexpected error: {e}",
            )

    async def process_markets(self, markets: list["Market"]) -> list[TradingDecision]:
        """Process multiple markets and make trading decisions.

        Args:
            markets: List of markets to process

        Returns:
            List of TradingDecision results for each market

        Example:
            >>> decisions = await executor.process_markets(markets)
            >>> successful = [d for d in decisions if d.success and d.trade]
            >>> print(f"Executed {len(successful)} trades")
        """
        self._logger.info(f"📋 Processing {len(markets)} markets...")

        decisions: list[TradingDecision] = []

        for i, market in enumerate(markets, 1):
            self._logger.debug(f"Processing market {i}/{len(markets)}: {market.id}")
            decision = await self.process_market(market)
            decisions.append(decision)

        # Log summary
        successful = sum(1 for d in decisions if d.success and d.trade)
        skipped = sum(1 for d in decisions if d.skipped)
        failed = sum(1 for d in decisions if not d.success)

        self._logger.info(
            f"📊 Batch processing complete: "
            f"{successful} trades executed, {skipped} skipped, {failed} failed"
        )

        return decisions

    async def _calculate_position_size(self, position_ratio: float) -> float:
        """Calculate position size based on ratio and current capital.

        Args:
            position_ratio: Ratio of capital to use (0-1)

        Returns:
            Position size in USD

        Raises:
            TradingError: If calculated amount is below minimum bet
        """
        state = await self._state.get_state()
        capital = state.current_capital

        # Calculate raw amount
        amount = capital * position_ratio

        # Apply constraints
        min_bet = self._settings.MIN_BET
        max_amount = capital * self._settings.MAX_SINGLE_RATIO

        # Ensure minimum bet
        if amount < min_bet:
            self._logger.warning(
                f"Calculated amount ${amount:.2f} below minimum ${min_bet:.2f}, "
                f"adjusting to minimum"
            )
            amount = min_bet

        # Ensure maximum single ratio
        if amount > max_amount:
            self._logger.warning(
                f"Calculated amount ${amount:.2f} above maximum ${max_amount:.2f}, "
                f"adjusting to maximum"
            )
            amount = max_amount

        # Final validation
        if amount < min_bet:
            raise TradingError(
                f"Cannot meet minimum bet requirement: "
                f"capital=${capital:.2f}, min_bet=${min_bet:.2f}"
            )

        return amount
```

### 项目结构 [Source: architecture.md#Project Structure]

**新建/修改文件:**
```
src/
└── trading/
    ├── __init__.py              # 修改: 导出 TradingExecutor
    ├── executor.py              # 新建: TradingExecutor 实现
    ├── paper_trading.py         # 已有: 复用
    ├── position_manager.py      # 已有: 复用
    └── risk_control.py          # 已有: 复用

tests/
└── test_trading/
    ├── __init__.py              # 已有
    ├── test_paper_trading.py    # 已有
    └── test_executor.py         # 新建: TradingExecutor 测试
```

### 依赖关系

**本故事依赖:**
- Story 1.2: 配置管理系统 (已完成 - `Settings`)
- Story 3.3: LLM 分析引擎 (已完成 - `LLMAnalyzer`)
- Story 4.2: 线程安全状态管理 (已完成 - `ThreadSafeState`)
- Story 4.4: 交易前风险检查 (已完成 - `RiskController`)
- Story 5.2: Paper Trading 执行器 (已完成 - `PaperTradingExecutor`)

**后续故事依赖本故事:**
- Story 5.4: 模拟持仓 PnL 计算 (需要 TradingExecutor 创建的持仓)
- Story 5.5: 统计数据记录 (需要 TradingExecutor 产生的交易记录)
- Story 8.2: 定时任务配置 (需要 TradingExecutor 处理市场)

### 前一个故事学习 [Source: 5-2-paper-trading-executor.md]

**从 Story 5.2 学到的模式:**

1. **依赖注入** - 所有依赖通过构造函数注入
2. **数据类返回结果** - 使用 `@dataclass` 定义返回类型
3. **错误隔离** - 返回结果包含 `success` 和 `error_message`
4. **日志标准化** - 使用 emoji 标记不同类型的日志
5. **类型注解** - 使用 `TYPE_CHECKING` 避免循环导入
6. **`__all__` 导出** - 明确模块公共 API

### 实现注意事项

**关键点:**

1. **流程顺序** - 必须按 LLM 分析 -> 风险检查 -> 仓位计算 -> 交易执行 的顺序
2. **错误隔离** - 单个市场失败不影响其他市场的处理
3. **日志完整** - 每个步骤都有相应的日志记录
4. **仓位约束** - 确保交易金额在 MIN_BET 和 MAX_SINGLE_RATIO 之间

**错误处理:**

| 场景 | 处理方式 | 返回结果 |
|------|----------|----------|
| LLM 分析失败 | 捕获异常，记录日志 | success=False, error_message |
| 风险检查拒绝 | 记录跳过原因 | success=True, skipped=True, reason |
| 仓位计算失败 | 抛出 TradingError | success=False, error_message |
| 交易执行失败 | 返回失败结果 | success=False, error_message |
| 意外异常 | 捕获并记录 | success=False, error_message |

**日志级别:**

| 级别 | 场景 | Emoji |
|------|------|-------|
| INFO | 处理开始、完成、跳过 | 🔍 ✅ ⚠️ |
| DEBUG | 步骤详情 | 🧠 📊 💰 |
| WARNING | 仓位调整 | ⚠️ |
| ERROR | 失败情况 | ❌ |

### 测试策略

```python
# tests/test_trading/test_executor.py
"""Tests for TradingExecutor."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.config import Settings
from src.models.market import Market
from src.models.prediction import PredictionResult, Recommendation
from src.models.trade import Trade, TradeType, TradeMode, TradeStatus
from src.models.position import Position, PositionOutcome, PositionStatus
from src.trading.executor import TradingExecutor, TradingDecision
from src.trading.risk_control import RiskCheckResult
from src.trading.paper_trading import PaperTradeResult


class TestTradingExecutor:
    """测试 TradingExecutor."""

    @pytest.fixture
    def mock_llm_analyzer(self) -> AsyncMock:
        """Mock LLMAnalyzer."""
        analyzer = AsyncMock()
        analyzer.analyze_market.return_value = PredictionResult(
            predicted_probability=0.70,
            confidence=0.85,
            reasoning="Strong indicators",
            key_assumptions=["Assumption 1"],
            recommendation=Recommendation.BUY_YES,
            edge=0.25,
            id=1,
        )
        return analyzer

    @pytest.fixture
    def mock_risk_controller(self) -> MagicMock:
        """Mock RiskController."""
        controller = MagicMock()
        controller.check_trade_allowed.return_value = RiskCheckResult(
            allowed=True,
            reason="",
            position_ratio=0.20,
        )
        return controller

    @pytest.fixture
    def mock_paper_executor(self) -> AsyncMock:
        """Mock PaperTradingExecutor."""
        executor = AsyncMock()
        executor.execute_trade.return_value = PaperTradeResult(
            trade=Trade(
                id=1,
                market_id="test-market",
                trade_type=TradeType.BUY_YES,
                mode=TradeMode.PAPER,
                amount=40.0,
                price=0.45,
                shares=88.89,
                status=TradeStatus.FILLED,
            ),
            position=Position(
                id=1,
                market_id="test-market",
                outcome=PositionOutcome.YES,
                shares=88.89,
                avg_price=0.45,
                initial_value=40.0,
                current_value=40.0,
                pnl=0.0,
                status=PositionStatus.OPEN,
            ),
            success=True,
        )
        return executor

    @pytest.fixture
    def mock_state(self) -> AsyncMock:
        """Mock ThreadSafeState."""
        from dataclasses import dataclass

        @dataclass
        class StateSnapshot:
            current_capital: float = 200.0

        state = AsyncMock()
        state.get_state.return_value = StateSnapshot(current_capital=200.0)
        return state

    @pytest.fixture
    def settings(self) -> Settings:
        """创建测试设置."""
        return Settings(
            INITIAL_CAPITAL=200.0,
            MIN_BET=5.0,
            MAX_SINGLE_RATIO=0.20,
            TRADE_MODE="PAPER",
        )

    @pytest.fixture
    def executor(
        self,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
        mock_state: AsyncMock,
        settings: Settings,
    ) -> TradingExecutor:
        """创建测试用执行器."""
        return TradingExecutor(
            llm_analyzer=mock_llm_analyzer,
            risk_controller=mock_risk_controller,
            paper_executor=mock_paper_executor,
            state=mock_state,
            settings=settings,
        )

    @pytest.fixture
    def sample_market(self) -> Market:
        """创建示例市场."""
        return Market(
            id="test-market",
            title="Test Market",
            description="Test Description",
            category="politics",
            yes_price=0.45,
            no_price=0.55,
            liquidity=50000.0,
        )

    @pytest.mark.asyncio
    async def test_process_market_success(
        self,
        executor: TradingExecutor,
        sample_market: Market,
        mock_llm_analyzer: AsyncMock,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
    ) -> None:
        """测试完整流程成功."""
        decision = await executor.process_market(sample_market)

        assert decision.success is True
        assert decision.skipped is False
        assert decision.trade is not None
        assert decision.position is not None
        assert decision.prediction is not None

        # Verify all steps were called
        mock_llm_analyzer.analyze_market.assert_called_once_with(sample_market)
        mock_risk_controller.check_trade_allowed.assert_called_once()
        mock_paper_executor.execute_trade.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_market_risk_check_rejected(
        self,
        executor: TradingExecutor,
        sample_market: Market,
        mock_risk_controller: MagicMock,
        mock_paper_executor: AsyncMock,
    ) -> None:
        """测试风险检查拒绝交易."""
        mock_risk_controller.check_trade_allowed.return_value = RiskCheckResult(
            allowed=False,
            reason="Confidence too low",
            position_ratio=0.0,
        )

        decision = await executor.process_market(sample_market)

        assert decision.success is True
        assert decision.skipped is True
        assert decision.trade is None
        assert "Confidence too low" in decision.reason

        # Verify trade was not executed
        mock_paper_executor.execute_trade.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_market_llm_analysis_fails(
        self,
        executor: TradingExecutor,
        sample_market: Market,
        mock_llm_analyzer: AsyncMock,
        mock_paper_executor: AsyncMock,
    ) -> None:
        """测试 LLM 分析失败."""
        mock_llm_analyzer.analyze_market.side_effect = Exception("API error")

        decision = await executor.process_market(sample_market)

        assert decision.success is False
        assert decision.error_message is not None
        assert "API error" in decision.error_message

        # Verify trade was not executed
        mock_paper_executor.execute_trade.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_market_execution_fails(
        self,
        executor: TradingExecutor,
        sample_market: Market,
        mock_paper_executor: AsyncMock,
    ) -> None:
        """测试交易执行失败."""
        mock_paper_executor.execute_trade.return_value = PaperTradeResult(
            trade=None,
            position=None,
            success=False,
            error_message="Database error",
        )

        decision = await executor.process_market(sample_market)

        assert decision.success is False
        assert "Database error" in decision.error_message

    @pytest.mark.asyncio
    async def test_process_markets_batch(
        self,
        executor: TradingExecutor,
        sample_market: Market,
    ) -> None:
        """测试批量处理多个市场."""
        markets = [
            Market(
                id=f"market-{i}",
                title=f"Market {i}",
                yes_price=0.45 + i * 0.05,
                no_price=0.55 - i * 0.05,
                liquidity=50000.0,
            )
            for i in range(3)
        ]

        decisions = await executor.process_markets(markets)

        assert len(decisions) == 3
        assert all(d.success for d in decisions)

    @pytest.mark.asyncio
    async def test_calculate_position_size(
        self,
        executor: TradingExecutor,
        mock_state: AsyncMock,
    ) -> None:
        """测试仓位计算."""
        from dataclasses import dataclass

        @dataclass
        class StateSnapshot:
            current_capital: float = 200.0

        mock_state.get_state.return_value = StateSnapshot(current_capital=200.0)

        # 20% of $200 = $40
        amount = await executor._calculate_position_size(0.20)
        assert amount == 40.0

    @pytest.mark.asyncio
    async def test_calculate_position_size_below_minimum(
        self,
        executor: TradingExecutor,
        mock_state: AsyncMock,
        settings: Settings,
    ) -> None:
        """测试仓位计算低于最小值时调整到最小值."""
        from dataclasses import dataclass

        @dataclass
        class StateSnapshot:
            current_capital: float = 200.0

        mock_state.get_state.return_value = StateSnapshot(current_capital=200.0)

        # 1% of $200 = $2, but min is $5
        amount = await executor._calculate_position_size(0.01)
        assert amount == settings.MIN_BET
```

### References

- [Source: architecture.md#Trading Flow] - 交易流程设计规范
- [Source: architecture.md#Project Structure] - src/trading/ 目录结构
- [Source: epics.md#Story 5.3] - 原始 Story 定义
- [Source: src/analysis/llm_analyzer.py] - LLMAnalyzer 实现
- [Source: src/trading/risk_control.py] - RiskController 实现
- [Source: src/trading/paper_trading.py] - PaperTradingExecutor 实现
- [Source: src/core/state.py] - ThreadSafeState 实现
- [Source: src/config.py] - Settings 配置
- [Source: src/models/market.py] - Market 模型
- [Source: src/models/prediction.py] - PredictionResult, Recommendation
- [Source: src/models/trade.py] - Trade 模型
- [Source: src/models/position.py] - Position 模型
- [Source: 5-2-paper-trading-executor.md] - 前一个故事实现参考

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None

### Completion Notes List

1. **实现完成** - TradingExecutor 类已实现，包含完整的交易决策流程:
   - LLM 分析 -> 风险检查 -> 仓位计算 -> 交易执行
   - 批量处理方法 process_markets
   - 辅助方法 _calculate_position_size

2. **错误处理** - 实现了全面的错误处理:
   - LLM 分析失败: 返回 TradingDecision(success=False, error_message)
   - 风险检查拒绝: 返回 TradingDecision(success=True, skipped=True, reason)
   - 交易执行失败: 返回 TradingDecision(success=False, error_message)
   - 全局异常捕获: 确保单个市场失败不影响其他市场

3. **类型安全** - 使用 TYPE_CHECKING 避免循环导入，使用 getattr 安全获取 prediction.id

4. **测试覆盖** - 21 个单元测试全部通过:
   - 成功场景测试
   - 风险检查拒绝测试
   - LLM 分析失败测试
   - 交易执行失败测试
   - 批量处理测试
   - 仓位计算边界测试
   - TradingDecision 数据类测试

5. **代码质量** - 所有检查通过:
   - mypy: 无类型错误
   - black: 格式化通过
   - isort: import 排序通过
   - 完整测试套件: 906 个测试全部通过

### File List

- src/trading/executor.py (新建)
- src/trading/__init__.py (修改 - 导出 TradingExecutor, TradingDecision)
- tests/test_trading/test_executor.py (新建)
