# Story 5.2: Paper Trading 执行器

Status: done

## Story

As a **用户**,
I want **系统能够模拟执行交易而不下真实订单**,
So that **我可以验证策略而不冒真钱风险**.

## Acceptance Criteria

**Given** 交易记录模型已实现 (Story 5.1)
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

## Tasks / Subtasks

- [x] Task 1: 创建 PaperTradingExecutor 类结构 (AC: 1)
  - [x] 1.1 创建 `src/trading/paper_trading.py` 文件
  - [x] 1.2 定义 `PaperTradingExecutor` 类
  - [x] 1.3 实现构造函数，注入所需依赖 (TradeRepository, PositionManager, ThreadSafeState)
  - [x] 1.4 定义 `PaperTradeResult` 数据类用于返回交易结果

- [x] Task 2: 实现 execute_trade 核心方法 (AC: 2)
  - [x] 2.1 实现 `execute_trade(market, prediction, amount)` 方法签名
  - [x] 2.2 根据 prediction.recommendation 确定 trade_type (BUY_YES/BUY_NO)
  - [x] 2.3 从 market 获取当前价格 (yes_price 或 no_price)
  - [x] 2.4 计算 shares = amount / price
  - [x] 2.5 创建 Trade 对象 (mode=PAPER, status=FILLED)
  - [x] 2.6 保存 Trade 到数据库 (使用 TradeRepository)
  - [x] 2.7 调用 PositionManager.open_position() 创建持仓
  - [x] 2.8 更新 Trade 的 position_id 关联
  - [x] 2.9 记录交易日志 (使用 emoji 💰)
  - [x] 2.10 返回 PaperTradeResult

- [x] Task 3: 实现辅助方法
  - [x] 3.1 实现 `_get_trade_type(recommendation)` - 将 Recommendation 转换为 TradeType
  - [x] 3.2 实现 `_get_price(market, trade_type)` - 根据交易类型获取价格
  - [x] 3.3 实现 `_calculate_shares(amount, price)` - 计算份额
  - [x] 3.4 实现 `_determine_outcome(trade_type)` - 确定持仓方向 (YES/NO)

- [x] Task 4: 更新模块导出 (AC: All)
  - [x] 4.1 更新 `src/trading/__init__.py` 导出 `PaperTradingExecutor`
  - [x] 4.2 更新 `__all__` 列表

- [x] Task 5: 编写单元测试 (AC: All)
  - [x] 5.1 创建 `tests/test_trading/test_paper_trading.py`
  - [x] 5.2 测试 execute_trade 成功场景 (BUY_YES)
  - [x] 5.3 测试 execute_trade 成功场景 (BUY_NO)
  - [x] 5.4 测试 Trade 记录创建和保存
  - [x] 5.5 测试 Position 创建
  - [x] 5.6 测试 shares 计算
  - [x] 5.7 测试错误处理 (无效 recommendation, 无效价格)
  - [x] 5.8 Mock 所有外部依赖

- [x] Task 6: 代码质量检查 (AC: All)
  - [x] 6.1 运行 `mypy src/trading/paper_trading.py` 无错误
  - [x] 6.2 运行 `black --check` 通过
  - [x] 6.3 运行 `isort --check` 通过
  - [x] 6.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md]

**Paper Trading 设计原则:**
- 不连接真实 Polymarket API
- 模拟即时成交 (status=FILLED)
- 虚拟资金追踪 (通过 ThreadSafeState)
- 完整记录到数据库 (trades, positions 表)

### 已有组件 (必须复用)

**TradeRepository** [Source: src/storage/repositories/trade_repo.py]
```python
class TradeRepository:
    async def save(self, trade: Trade) -> Trade: ...
    async def get_by_id(self, trade_id: int) -> Trade | None: ...
    async def get_by_market(self, market_id: str) -> list[Trade]: ...
```

**PositionManager** [Source: src/trading/position_manager.py]
```python
class PositionManager:
    async def open_position(
        self, market_id: str, outcome: PositionOutcome,
        shares: float, price: float
    ) -> Position: ...
    async def get_position_by_market(self, market_id: str) -> Position | None: ...
```

**ThreadSafeState** [Source: src/core/state.py]
```python
class ThreadSafeState:
    async def update_capital(self, amount: float) -> None: ...
    async def increment_open_positions(self) -> None: ...
    async def get_state(self) -> StateSnapshot: ...
```

### 数据模型 [Source: src/models/]

**Trade** [Source: src/models/trade.py]
```python
class TradeType(str, Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    SELL = "SELL"

class TradeMode(str, Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"

class TradeStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"

class Trade(BaseModel):
    id: int
    market_id: str
    trade_type: TradeType
    mode: TradeMode
    amount: float  # >= 0
    price: float   # 0-1
    shares: float | None
    status: TradeStatus
    llm_prediction_id: int | None
    position_id: int | None
    created_at: datetime | None
```

**Position** [Source: src/models/position.py]
```python
class PositionOutcome(str, Enum):
    YES = "YES"
    NO = "NO"

class PositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class Position(BaseModel):
    id: int
    market_id: str
    outcome: PositionOutcome
    shares: float
    avg_price: float
    initial_value: float | None
    current_value: float | None
    pnl: float | None
    status: PositionStatus
    opened_at: datetime | None
    closed_at: datetime | None
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
```

**Market** [Source: src/models/market.py]
```python
class Market(BaseModel):
    id: str
    title: str
    description: str | None
    category: str | None
    yes_price: float | None  # 0-1
    no_price: float | None   # 0-1
    liquidity: float | None
    deadline: datetime | None
    ...
```

### 交易执行流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                     Paper Trading 执行流程                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  execute_trade(market, prediction, amount)                      │
│                                                                 │
│  1. 确定 TradeType                                              │
│     if recommendation == BUY_YES → TradeType.BUY_YES           │
│     if recommendation == BUY_NO  → TradeType.BUY_NO            │
│     if recommendation == NO_TRADE → raise TradingError         │
│                                                                 │
│  2. 获取价格                                                    │
│     if BUY_YES → price = market.yes_price                      │
│     if BUY_NO  → price = market.no_price                       │
│                                                                 │
│  3. 计算份额                                                    │
│     shares = amount / price                                    │
│                                                                 │
│  4. 创建 Trade 记录                                             │
│     trade = Trade(                                             │
│         id=0,                                                  │
│         market_id=market.id,                                   │
│         trade_type=trade_type,                                 │
│         mode=TradeMode.PAPER,                                  │
│         amount=amount,                                         │
│         price=price,                                           │
│         shares=shares,                                         │
│         status=TradeStatus.FILLED,  # 即时成交                 │
│         llm_prediction_id=prediction.id,                       │
│     )                                                          │
│     saved_trade = await trade_repo.save(trade)                 │
│                                                                 │
│  5. 创建 Position                                               │
│     outcome = YES if BUY_YES else NO                           │
│     position = await position_manager.open_position(           │
│         market_id=market.id,                                   │
│         outcome=outcome,                                       │
│         shares=shares,                                         │
│         price=price                                            │
│     )                                                          │
│                                                                 │
│  6. 更新 Trade 关联 Position                                    │
│     saved_trade.position_id = position.id                      │
│     await trade_repo.save(saved_trade)  # 或单独 update 方法   │
│                                                                 │
│  7. 记录日志                                                    │
│     logger.info(f"💰 PAPER TRADE: {trade_type.value} "         │
│                 f"{shares:.2f} shares @ {price:.4f} "           │
│                 f"= ${amount:.2f}")                            │
│                                                                 │
│  8. 返回结果                                                    │
│     return PaperTradeResult(                                   │
│         trade=saved_trade,                                     │
│         position=position,                                     │
│         success=True                                           │
│     )                                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 实现模板

**src/trading/paper_trading.py:**

```python
"""Paper Trading executor for the Polymarket Trader application.

This module provides the PaperTradingExecutor class that simulates
trade execution without placing real orders.

Story 5.2: Paper Trading 执行器

Example:
    >>> from src.trading.paper_trading import PaperTradingExecutor
    >>> from src.storage.repositories import TradeRepository
    >>> from src.trading.position_manager import PositionManager
    >>> from src.core.state import ThreadSafeState
    >>>
    >>> trade_repo = TradeRepository()
    >>> state = ThreadSafeState(initial_capital=200.0)
    >>> position_manager = PositionManager(position_repo, state)
    >>> executor = PaperTradingExecutor(trade_repo, position_manager, state)
    >>>
    >>> # Execute a paper trade
    >>> result = await executor.execute_trade(market, prediction, 50.0)
    >>> print(f"Trade ID: {result.trade.id}, Shares: {result.trade.shares}")
"""

from __future__ import annotations

__all__ = ["PaperTradingExecutor", "PaperTradeResult"]

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.exceptions import TradingError, ValidationError
from src.models.position import PositionOutcome
from src.models.prediction import Recommendation
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.core.state import ThreadSafeState
    from src.models.market import Market
    from src.models.position import Position
    from src.models.prediction import PredictionResult
    from src.storage.repositories.trade_repo import TradeRepository
    from src.trading.position_manager import PositionManager


logger = get_logger(__name__)


@dataclass
class PaperTradeResult:
    """Result of a paper trade execution.

    Attributes:
        trade: The executed trade record
        position: The opened position (if any)
        success: Whether the trade was successful
        error_message: Error message if trade failed
    """

    trade: Trade | None = None
    position: "Position | None" = None
    success: bool = True
    error_message: str | None = None


class PaperTradingExecutor:
    """Paper trading executor that simulates trade execution.

    Executes trades in PAPER mode without connecting to real Polymarket API.
    Creates trade records and positions for tracking and analysis.

    Attributes:
        _trade_repo: TradeRepository for saving trade records
        _position_manager: PositionManager for creating positions
        _state: ThreadSafeState for capital tracking

    Example:
        >>> executor = PaperTradingExecutor(trade_repo, position_manager, state)
        >>> result = await executor.execute_trade(market, prediction, 50.0)
        >>> if result.success:
        ...     print(f"Trade executed: {result.trade.id}")
    """

    def __init__(
        self,
        trade_repo: "TradeRepository",
        position_manager: "PositionManager",
        state: "ThreadSafeState",
    ) -> None:
        """Initialize paper trading executor.

        Args:
            trade_repo: Repository for trade records
            position_manager: Manager for position lifecycle
            state: Thread-safe state manager for capital tracking
        """
        self._trade_repo = trade_repo
        self._position_manager = position_manager
        self._state = state
        self._logger = get_logger(__name__)
        self._logger.info("PaperTradingExecutor initialized")

    async def execute_trade(
        self,
        market: "Market",
        prediction: "PredictionResult",
        amount: float,
        prediction_id: int | None = None,
    ) -> PaperTradeResult:
        """Execute a paper trade.

        Simulates trade execution by:
        1. Creating a Trade record (mode=PAPER, status=FILLED)
        2. Calculating shares based on amount and price
        3. Creating a Position via PositionManager
        4. Linking Trade to Position

        Args:
            market: Market to trade
            prediction: LLM prediction with recommendation
            amount: Trade amount in USD
            prediction_id: Optional prediction database ID for linking

        Returns:
            PaperTradeResult with trade and position details

        Raises:
            ValidationError: If parameters are invalid
            TradingError: If trade execution fails

        Example:
            >>> result = await executor.execute_trade(market, prediction, 50.0)
            >>> if result.success:
            ...     print(f"Bought {result.trade.shares:.2f} shares")
        """
        try:
            # Validate inputs
            if amount <= 0:
                raise ValidationError(f"Trade amount must be positive, got {amount}")

            # 1. Determine trade type from recommendation
            trade_type = self._get_trade_type(prediction.recommendation)

            # 2. Get price from market
            price = self._get_price(market, trade_type)
            if price is None or price <= 0 or price >= 1:
                raise ValidationError(
                    f"Invalid price for market {market.id}: {price}"
                )

            # 3. Calculate shares
            shares = self._calculate_shares(amount, price)

            # 4. Create Trade record
            trade = Trade(
                id=0,
                market_id=market.id,
                trade_type=trade_type,
                mode=TradeMode.PAPER,
                amount=amount,
                price=price,
                shares=shares,
                status=TradeStatus.FILLED,  # Paper trades are immediately filled
                llm_prediction_id=prediction_id,
                position_id=None,  # Will be updated after position creation
            )

            # 5. Save trade
            saved_trade = await self._trade_repo.save(trade)
            self._logger.info(
                f"💰 PAPER TRADE created: id={saved_trade.id}, "
                f"type={trade_type.value}, {shares:.2f} shares @ {price:.4f} = ${amount:.2f}"
            )

            # 6. Create position
            outcome = self._determine_outcome(trade_type)
            position = await self._position_manager.open_position(
                market_id=market.id,
                outcome=outcome,
                shares=shares,
                price=price,
            )

            # 7. Update trade with position_id
            saved_trade.position_id = position.id
            # Note: We may need to add an update method to TradeRepository
            # For now, we can save again to update
            await self._trade_repo.save(saved_trade)

            self._logger.info(
                f"✅ Paper trade completed: trade_id={saved_trade.id}, "
                f"position_id={position.id}"
            )

            return PaperTradeResult(
                trade=saved_trade,
                position=position,
                success=True,
            )

        except (ValidationError, TradingError) as e:
            self._logger.error(f"❌ Paper trade failed: {e}")
            return PaperTradeResult(
                trade=None,
                position=None,
                success=False,
                error_message=str(e),
            )
        except Exception as e:
            self._logger.error(f"❌ Unexpected error in paper trade: {e}")
            return PaperTradeResult(
                trade=None,
                position=None,
                success=False,
                error_message=f"Unexpected error: {e}",
            )

    def _get_trade_type(self, recommendation: Recommendation) -> TradeType:
        """Convert LLM recommendation to trade type.

        Args:
            recommendation: LLM recommendation

        Returns:
            Corresponding TradeType

        Raises:
            TradingError: If recommendation is NO_TRADE
        """
        if recommendation == Recommendation.BUY_YES:
            return TradeType.BUY_YES
        elif recommendation == Recommendation.BUY_NO:
            return TradeType.BUY_NO
        else:
            raise TradingError(
                f"Cannot execute trade with recommendation: {recommendation.value}"
            )

    def _get_price(self, market: "Market", trade_type: TradeType) -> float | None:
        """Get price from market based on trade type.

        Args:
            market: Market to get price from
            trade_type: Type of trade

        Returns:
            Price (0-1) or None if not available
        """
        if trade_type == TradeType.BUY_YES:
            return market.yes_price
        else:  # BUY_NO
            return market.no_price

    def _calculate_shares(self, amount: float, price: float) -> float:
        """Calculate number of shares from amount and price.

        Args:
            amount: Trade amount in USD
            price: Price per share (0-1)

        Returns:
            Number of shares
        """
        if price <= 0:
            raise ValidationError(f"Price must be positive, got {price}")
        return amount / price

    def _determine_outcome(self, trade_type: TradeType) -> PositionOutcome:
        """Determine position outcome from trade type.

        Args:
            trade_type: Type of trade

        Returns:
            Corresponding PositionOutcome
        """
        if trade_type == TradeType.BUY_YES:
            return PositionOutcome.YES
        else:  # BUY_NO
            return PositionOutcome.NO
```

### 项目结构 [Source: architecture.md#Project Structure]

**新建/修改文件:**
```
src/
└── trading/
    ├── __init__.py              # 修改: 导出 PaperTradingExecutor
    ├── paper_trading.py         # 新建: PaperTradingExecutor 实现
    ├── position_manager.py      # 已有: 复用
    └── risk_control.py          # 已有: 复用

tests/
└── test_trading/
    ├── __init__.py              # 已有
    └── test_paper_trading.py    # 新建: PaperTradingExecutor 测试
```

### 依赖关系

**本故事依赖:**
- Story 1.2: 配置管理系统 (已完成 - `settings`)
- Story 4.2: 线程安全状态管理 (已完成 - `ThreadSafeState`)
- Story 4.5: 持仓管理 (已完成 - `PositionManager`)
- Story 5.1: 交易记录数据模型 (已完成 - `TradeRepository`, `Trade` 模型)

**后续故事依赖本故事:**
- Story 5.3: 交易决策流程 (需要 PaperTradingExecutor 执行交易)
- Story 5.4: 模拟持仓 PnL 计算 (需要 Paper Trading 创建的持仓)
- Story 5.5: 统计数据记录 (需要 Paper Trading 产生的交易记录)

### 前一个故事学习 [Source: 5-1-trade-record-data-model.md]

**从 Story 5.1 学到的模式:**

1. **Repository 模式** - 所有数据库操作封装在 Repository 类中
2. **`__all__` 导出列表** - 明确模块公共 API
3. **类型注解使用 `|` 联合** - 而非 `Optional`
4. **日志使用 emoji** - `✅`, `⚠️`, `❌`, `📊`, `💰`
5. **异步方法** - 所有涉及数据库的方法都是 `async`
6. **抛出特定异常** - `ValidationError` 用于参数验证, `TradingError` 用于交易错误
7. **返回带 ID 的模型** - save 方法返回完整对象

### 实现注意事项

**关键点:**

1. **交易类型映射** - Recommendation.BUY_YES -> TradeType.BUY_YES, Recommendation.BUY_NO -> TradeType.BUY_NO
2. **价格获取** - BUY_YES 使用 yes_price, BUY_NO 使用 no_price
3. **份额计算** - shares = amount / price
4. **即时成交** - Paper Trading 模拟即时成交, status 直接设为 FILLED
5. **关联关系** - Trade 通过 position_id 关联 Position, 通过 llm_prediction_id 关联 Prediction

**错误处理:**

| 场景 | 抛出异常 | 返回结果 |
|------|----------|----------|
| amount <= 0 | ValidationError | success=False |
| recommendation == NO_TRADE | TradingError | success=False |
| price 为 None 或无效 | ValidationError | success=False |
| Position 创建失败 | TradingError | success=False |
| 数据库错误 | 捕获后返回 | success=False |

**日志级别:**

| 级别 | 场景 |
|------|------|
| INFO | 交易创建、交易完成 |
| ERROR | 交易失败、意外错误 |

### 测试策略

```python
# tests/test_trading/test_paper_trading.py
"""Tests for PaperTradingExecutor."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.market import Market
from src.models.prediction import PredictionResult, Recommendation
from src.models.trade import Trade, TradeType, TradeMode, TradeStatus
from src.models.position import Position, PositionOutcome, PositionStatus
from src.trading.paper_trading import PaperTradingExecutor, PaperTradeResult


class TestPaperTradingExecutor:
    """测试 PaperTradingExecutor."""

    @pytest.fixture
    def mock_trade_repo(self) -> AsyncMock:
        """Mock TradeRepository."""
        repo = AsyncMock()
        repo.save.return_value = Trade(
            id=1,
            market_id="test-market",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=50.0,
            price=0.45,
            shares=111.11,
            status=TradeStatus.FILLED,
        )
        return repo

    @pytest.fixture
    def mock_position_manager(self) -> AsyncMock:
        """Mock PositionManager."""
        manager = AsyncMock()
        manager.open_position.return_value = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=111.11,
            avg_price=0.45,
            initial_value=50.0,
            current_value=50.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
        )
        return manager

    @pytest.fixture
    def mock_state(self) -> AsyncMock:
        """Mock ThreadSafeState."""
        return AsyncMock()

    @pytest.fixture
    def executor(
        self,
        mock_trade_repo: AsyncMock,
        mock_position_manager: AsyncMock,
        mock_state: AsyncMock,
    ) -> PaperTradingExecutor:
        """创建测试用执行器."""
        return PaperTradingExecutor(
            mock_trade_repo, mock_position_manager, mock_state
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

    @pytest.fixture
    def sample_prediction(self) -> PredictionResult:
        """创建示例预测."""
        return PredictionResult(
            predicted_probability=0.70,
            confidence=0.85,
            reasoning="Strong indicators",
            key_assumptions=["Assumption 1"],
            recommendation=Recommendation.BUY_YES,
            edge=0.25,
        )

    @pytest.mark.asyncio
    async def test_execute_trade_buy_yes(
        self,
        executor: PaperTradingExecutor,
        sample_market: Market,
        sample_prediction: PredictionResult,
        mock_trade_repo: AsyncMock,
        mock_position_manager: AsyncMock,
    ) -> None:
        """测试 BUY_YES 交易."""
        result = await executor.execute_trade(
            sample_market, sample_prediction, 50.0
        )

        assert result.success is True
        assert result.trade is not None
        assert result.trade.trade_type == TradeType.BUY_YES
        assert result.trade.mode == TradeMode.PAPER
        assert result.trade.status == TradeStatus.FILLED
        assert result.trade.price == 0.45
        assert result.trade.shares == pytest.approx(50.0 / 0.45, rel=0.01)

        # Verify position was created with correct outcome
        mock_position_manager.open_position.assert_called_once()
        call_args = mock_position_manager.open_position.call_args
        assert call_args.kwargs["outcome"] == PositionOutcome.YES

    @pytest.mark.asyncio
    async def test_execute_trade_buy_no(
        self,
        executor: PaperTradingExecutor,
        sample_market: Market,
        mock_trade_repo: AsyncMock,
        mock_position_manager: AsyncMock,
    ) -> None:
        """测试 BUY_NO 交易."""
        prediction = PredictionResult(
            predicted_probability=0.30,
            confidence=0.80,
            reasoning="NO is more likely",
            recommendation=Recommendation.BUY_NO,
            edge=0.25,
        )

        result = await executor.execute_trade(sample_market, prediction, 50.0)

        assert result.success is True
        assert result.trade.trade_type == TradeType.BUY_NO
        assert result.trade.price == 0.55  # no_price
        assert result.trade.shares == pytest.approx(50.0 / 0.55, rel=0.01)

    @pytest.mark.asyncio
    async def test_execute_trade_no_trade_recommendation(
        self,
        executor: PaperTradingExecutor,
        sample_market: Market,
    ) -> None:
        """测试 NO_TRADE 推荐应失败."""
        prediction = PredictionResult(
            predicted_probability=0.50,
            confidence=0.60,
            reasoning="No clear edge",
            recommendation=Recommendation.NO_TRADE,
            edge=0.02,
        )

        result = await executor.execute_trade(sample_market, prediction, 50.0)

        assert result.success is False
        assert "NO_TRADE" in result.error_message or "Cannot execute" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_trade_invalid_amount(
        self,
        executor: PaperTradingExecutor,
        sample_market: Market,
        sample_prediction: PredictionResult,
    ) -> None:
        """测试无效金额应失败."""
        result = await executor.execute_trade(sample_market, sample_prediction, -10.0)

        assert result.success is False
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_execute_trade_none_price(
        self,
        executor: PaperTradingExecutor,
        sample_prediction: PredictionResult,
    ) -> None:
        """测试价格为 None 应失败."""
        market_no_price = Market(
            id="no-price-market",
            title="No Price Market",
            yes_price=None,
            no_price=None,
        )

        result = await executor.execute_trade(market_no_price, sample_prediction, 50.0)

        assert result.success is False
        assert "price" in result.error_message.lower()
```

### References

- [Source: architecture.md#Paper Trading] - Paper Trading 设计规范
- [Source: architecture.md#Project Structure] - src/trading/ 目录结构
- [Source: epics.md#Story 5.2] - 原始 Story 定义
- [Source: src/storage/repositories/trade_repo.py] - TradeRepository 实现
- [Source: src/trading/position_manager.py] - PositionManager 实现
- [Source: src/core/state.py] - ThreadSafeState 实现
- [Source: src/models/trade.py] - Trade 模型
- [Source: src/models/position.py] - Position 模型
- [Source: src/models/prediction.py] - PredictionResult, Recommendation
- [Source: src/models/market.py] - Market 模型
- [Source: 5-1-trade-record-data-model.md] - 前一个故事实现参考

## Dev Agent Record

### Agent Model Used

GLM-5

### Debug Log References

None

### Completion Notes List

- 所有 6 个任务已完成
- 代码覆盖率: 100%
- 28 个单元测试全部通过
- 完整测试套件 885 个测试全部通过
- mypy, black, isort 检查全部通过

### File List

- `src/trading/paper_trading.py` - 新建: PaperTradingExecutor 实现
- `src/trading/__init__.py` - 修改: 导出 PaperTradingExecutor 和 PaperTradeResult
- `tests/test_trading/test_paper_trading.py` - 新建: PaperTradingExecutor 测试
