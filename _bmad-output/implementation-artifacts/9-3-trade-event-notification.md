# Story 9.3: 交易事件通知集成

Status: review

## Story

As a **用户**,
I want **在每笔交易执行时收到 Telegram 通知**,
So that **我能实时了解所有交易状态**.

## Acceptance Criteria

**Given** 通知发送器和交易执行器已实现 (Story 9.2, Epic 5)
**When** 在 `src/trading/executor.py` 集成通知
**Then** 在以下事件触发通知 (每笔交易都通知):
- 交易下单成功 -> 发送交易通知
- 交易下单失败 -> 发送错误通知
- 持仓平仓 -> 发送平仓通知 (含盈亏)
**And** 通知内容包含:
- 市场名称
- 交易方向 (BUY YES/NO)
- 金额、价格、份额
- 当前持仓状态
- 时间戳
**And** 使用 emoji 增强可读性 (💰 ✅ ❌ 📊)

## Tasks / Subtasks

- [x] Task 1: 修改 TradingExecutor 构造函数 (AC: #1)
  - [x] 1.1 添加 `notifier: TelegramNotifier | None` 参数
  - [x] 1.2 存储 notifier 到实例变量
  - [x] 1.3 记录日志说明通知是否启用
  - [x] 1.4 保持向后兼容 (notifier 可选)

- [x] Task 2: 实现交易成功通知 (AC: #1, #2)
  - [x] 2.1 在 `process_market()` 交易成功后调用 `notifier.send_trade_notification()`
  - [x] 2.2 传递 `trade` 和 `market` 参数
  - [x] 2.3 处理通知发送失败 (不影响主流程)
  - [x] 2.4 记录通知发送状态日志

- [x] Task 3: 实现交易失败通知 (AC: #1)
  - [x] 3.1 在 `process_market()` 交易失败后调用 `notifier.send_error_notification()`
  - [x] 3.2 构造有意义的错误消息
  - [x] 3.3 处理通知发送失败 (不影响主流程)

- [x] Task 4: 实现持仓平仓通知 (AC: #1, #2)
  - [x] 4.1 在 `src/trading/position_manager.py` 添加 `close_position()` 方法 (如果不存在)
  - [x] 4.2 在 `close_position()` 中调用 `notifier.send_position_closed_notification()`
  - [x] 4.3 通知内容包含盈亏信息
  - [x] 4.4 扩展 `TelegramNotifier` 添加 `send_position_closed_notification()` 方法

- [x] Task 5: 扩展 TelegramNotifier (AC: #4)
  - [x] 5.1 添加 `send_position_closed_notification(position, market, pnl)` 方法
  - [x] 5.2 创建 `_format_position_closed_message()` 格式化方法
  - [x] 5.3 平仓通知消息格式:
    ```
    📊 *持仓平仓*
    市场: Will Trump win 2028?
    方向: YES
    成本: $10.00
    收益: $12.50
    盈亏: +$2.50 (+25%)
    ```
  - [x] 5.4 更新 `src/notifications/__init__.py` (如需要)

- [x] Task 6: 编写测试 (AC: All)
  - [x] 6.1 创建 `tests/test_trading/test_executor_notifications.py`
  - [x] 6.2 测试交易成功通知发送
  - [x] 6.3 测试交易失败通知发送
  - [x] 6.4 测试 notifier 为 None 时行为
  - [x] 6.5 测试通知发送失败不影响主流程
  - [x] 6.6 扩展 `tests/test_notifications/test_telegram_notifier.py` 添加平仓通知测试

- [x] Task 7: 代码质量检查 (AC: All)
  - [x] 7.1 运行 `mypy src/trading/executor.py` 无错误
  - [x] 7.2 运行 `mypy src/notifications/telegram_notifier.py` 无错误
  - [x] 7.3 运行 `black --check src/trading/` 通过
  - [x] 7.4 运行 `isort --check src/trading/` 通过
  - [x] 7.5 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: epics.md#Story 9.3]

**通知触发时机:**
- 交易下单成功 -> `send_trade_notification(trade, market)`
- 交易下单失败 -> `send_error_notification(error)`
- 持仓平仓 -> `send_position_closed_notification(position, market, pnl)`

**通知内容:**
- 市场名称
- 交易方向 (BUY YES/NO)
- 金额、价格、份额
- 当前持仓状态
- 时间戳

### 现有依赖 [Source: Story 9.2]

**TelegramNotifier 已实现的方法:**
- `send_message(text, parse_mode)` - 发送普通消息
- `send_trade_notification(trade, market)` - 发送交易通知
- `send_analysis_notification(prediction, market)` - 发送分析通知
- `send_error_notification(error)` - 发送错误告警
- `send_system_notification(event, details)` - 发送系统事件通知

**需要新增的方法:**
- `send_position_closed_notification(position, market, pnl)` - 发送平仓通知

### 现有交易执行流程 [Source: src/trading/executor.py]

**TradingExecutor.process_market() 流程:**
```python
async def process_market(self, market: "Market") -> TradingDecision:
    # 1. LLM Analysis
    prediction = await self._llm_analyzer.analyze_market(market)

    # 2. Risk Check
    risk_check = await self._risk_controller.check_trade_allowed(prediction, market)
    if not risk_check.allowed:
        return TradingDecision(skipped=True, reason=reason)

    # 3. Calculate Position Size
    amount = await self._calculate_position_size(risk_check.position_ratio)

    # 4. Execute Trade (Paper Trading)
    result = await self._paper_executor.execute_trade(...)

    if not result.success:
        # 发送失败通知
        return TradingDecision(success=False, error_message=result.error_message)

    # 发送成功通知
    return TradingDecision(success=True, trade=result.trade)
```

### 实现模板

**TradingExecutor 修改:**

```python
# src/trading/executor.py
"""Trading executor for the Polymarket Trader application.

... (existing docstring)

Story 5.3: 交易决策流程
Story 9.3: 交易事件通知集成
"""

from __future__ import annotations

__all__ = ["TradingExecutor", "TradingDecision"]

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.config import settings
from src.exceptions import TradingError
from src.models.trade import Trade
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.analysis.llm_analyzer import LLMAnalyzer
    from src.core.state import ThreadSafeState
    from src.models.market import Market
    from src.models.position import Position
    from src.models.prediction import PredictionResult
    from src.notifications.telegram_notifier import TelegramNotifier
    from src.trading.paper_trading import PaperTradeResult, PaperTradingExecutor
    from src.trading.risk_control import RiskCheckResult, RiskController


class TradingExecutor:
    """Trading executor that orchestrates the complete trading decision flow.

    ... (existing docstring)

    Story 9.3: Added Telegram notification support for trade events.

    Attributes:
        _llm_analyzer: LLMAnalyzer for market analysis
        _risk_controller: RiskController for risk checks
        _paper_executor: PaperTradingExecutor for trade execution
        _state: ThreadSafeState for capital tracking
        _notifier: Optional TelegramNotifier for trade notifications
    """

    def __init__(
        self,
        llm_analyzer: "LLMAnalyzer",
        risk_controller: "RiskController",
        paper_executor: "PaperTradingExecutor",
        state: "ThreadSafeState",
        notifier: "TelegramNotifier | None" = None,
    ) -> None:
        """Initialize trading executor.

        Args:
            llm_analyzer: LLM analyzer for market predictions
            risk_controller: Risk controller for trade validation
            paper_executor: Paper trading executor for trade execution
            state: Thread-safe state for capital tracking
            notifier: Optional Telegram notifier for trade notifications
        """
        self._llm_analyzer = llm_analyzer
        self._risk_controller = risk_controller
        self._paper_executor = paper_executor
        self._state = state
        self._notifier = notifier
        self._logger = get_logger(__name__)

        # Log notification status
        if self._notifier:
            self._logger.info(
                f"TradingExecutor initialized (mode={settings.trading_mode}, "
                f"notifications=enabled)"
            )
        else:
            self._logger.info(
                f"TradingExecutor initialized (mode={settings.trading_mode}, "
                f"notifications=disabled)"
            )

    async def process_market(self, market: "Market") -> TradingDecision:
        """Process a single market and make a trading decision.

        ... (existing docstring)

        Story 9.3: Added notification support for trade events.
        """
        self._logger.info(f"Processing market: {market.id} - {market.title}")

        try:
            # 1. LLM Analysis
            self._logger.debug(f"Analyzing market {market.id}...")
            prediction = await self._llm_analyzer.analyze_market(market)
            self._logger.info(
                f"LLM analysis complete: recommendation={prediction.recommendation.value}, "
                f"confidence={prediction.confidence:.2%}"
            )

            # 2. Risk Check
            self._logger.debug(f"Running risk check for market {market.id}...")
            risk_check = await self._risk_controller.check_trade_allowed(
                prediction, market
            )

            if not risk_check.allowed:
                reason = (
                    risk_check.reasons[0] if risk_check.reasons else "Unknown reason"
                )
                self._logger.info(f"Trade rejected for market {market.id}: {reason}")
                return TradingDecision(
                    market_id=market.id,
                    success=True,
                    skipped=True,
                    prediction=prediction,
                    reason=reason,
                )

            # 3. Calculate Position Size
            amount = await self._calculate_position_size(risk_check.position_ratio)
            self._logger.info(
                f"Position size calculated: ${amount:.2f} "
                f"(ratio={risk_check.position_ratio:.2%})"
            )

            # 4. Execute Trade (Paper Trading)
            self._logger.debug(f"Executing paper trade for market {market.id}...")
            prediction_id = getattr(prediction, "id", None)
            result = await self._paper_executor.execute_trade(
                market=market,
                prediction=prediction,
                amount=amount,
                prediction_id=prediction_id,
            )

            if not result.success:
                self._logger.error(
                    f"Trade execution failed for market {market.id}: "
                    f"{result.error_message}"
                )

                # Story 9.3: Send failure notification
                await self._notify_trade_failed(
                    market=market,
                    error_message=result.error_message or "Unknown error",
                )

                return TradingDecision(
                    market_id=market.id,
                    success=False,
                    prediction=prediction,
                    error_message=result.error_message,
                )

            # 5. Log Success
            trade = result.trade
            assert trade is not None  # Type guard for mypy
            self._logger.info(
                f"Trade completed for market {market.id}: "
                f"{trade.trade_type.value} "
                f"{trade.shares:.2f} shares @ ${trade.price:.4f} "
                f"= ${amount:.2f}"
            )

            # Story 9.3: Send success notification
            await self._notify_trade_success(trade=trade, market=market)

            return TradingDecision(
                market_id=market.id,
                success=True,
                skipped=False,
                trade=result.trade,
                position=result.position,
                prediction=prediction,
            )

        except Exception as e:
            self._logger.error(f"Unexpected error processing market {market.id}: {e}")

            # Story 9.3: Send error notification
            await self._notify_trade_failed(
                market=market,
                error_message=f"Unexpected error: {e}",
            )

            return TradingDecision(
                market_id=market.id,
                success=False,
                error_message=f"Unexpected error: {e}",
            )

    async def _notify_trade_success(
        self,
        trade: Trade,
        market: "Market",
    ) -> None:
        """Send trade success notification.

        Story 9.3: 交易事件通知集成

        Args:
            trade: The executed trade
            market: The market for the trade
        """
        if not self._notifier:
            return

        try:
            success = await self._notifier.send_trade_notification(trade, market)
            if success:
                self._logger.debug(f"Trade notification sent for trade {trade.id}")
            else:
                self._logger.warning(
                    f"Failed to send trade notification for trade {trade.id}"
                )
        except Exception as e:
            # Don't let notification failure affect main flow
            self._logger.error(f"Error sending trade notification: {e}")

    async def _notify_trade_failed(
        self,
        market: "Market",
        error_message: str,
    ) -> None:
        """Send trade failure notification.

        Story 9.3: 交易事件通知集成

        Args:
            market: The market that failed
            error_message: The error message
        """
        if not self._notifier:
            return

        try:
            error_msg = f"Trade failed for {market.title}: {error_message}"
            success = await self._notifier.send_error_notification(error_msg)
            if success:
                self._logger.debug("Trade failure notification sent")
            else:
                self._logger.warning("Failed to send trade failure notification")
        except Exception as e:
            # Don't let notification failure affect main flow
            self._logger.error(f"Error sending trade failure notification: {e}")
```

**TelegramNotifier 扩展:**

```python
# src/notifications/telegram_notifier.py (添加新方法)

async def send_position_closed_notification(
    self,
    position: "Position",
    market: "Market",
    pnl: float,
    pnl_pct: float,
) -> bool:
    """Send a position closed notification.

    Story 9.3: 交易事件通知集成

    Args:
        position: The closed position
        market: The market for the position
        pnl: Profit/loss amount in USD
        pnl_pct: Profit/loss percentage

    Returns:
        True if sent successfully, False otherwise
    """
    message = self._format_position_closed_message(
        position, market, pnl, pnl_pct
    )
    return await self.send_message(message)

def _format_position_closed_message(
    self,
    position: "Position",
    market: "Market",
    pnl: float,
    pnl_pct: float,
) -> str:
    """Format a position closed notification message.

    Args:
        position: The closed position
        market: The market for the position
        pnl: Profit/loss amount in USD
        pnl_pct: Profit/loss percentage

    Returns:
        Formatted Markdown message
    """
    from datetime import datetime

    pnl_emoji = "\U0001f4c8" if pnl >= 0 else "\U0001f4c9"  # chart_up / chart_down
    pnl_sign = "+" if pnl >= 0 else ""

    lines = [
        "\U0001f4ca *持仓平仓*",
        f"市场: {market.title}",
        f"方向: {position.outcome.value}",
        f"份额: {position.shares:.2f}",
        f"成本: ${position.initial_value:.2f}",
        f"收益: ${position.current_value:.2f}",
        f"盈亏: {pnl_emoji} {pnl_sign}${pnl:.2f} ({pnl_sign}{pnl_pct:.1%})",
        f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    return "\n".join(lines)
```

### 项目结构 [Source: architecture.md#Project Structure]

**修改文件:**
```
src/trading/
├── executor.py              # 修改: 添加通知集成
└── position_manager.py      # 修改: 添加平仓通知 (如需要)

src/notifications/
└── telegram_notifier.py     # 修改: 添加平仓通知方法

tests/test_trading/
└── test_executor_notifications.py  # 新增: 通知集成测试

tests/test_notifications/
└── test_telegram_notifier.py       # 修改: 添加平仓通知测试
```

### 数据模型 [Source: src/models/]

**Position 模型关键字段:**
```python
class Position(BaseModel):
    id: int
    market_id: str
    outcome: PositionOutcome  # YES, NO
    shares: float
    avg_price: float
    initial_value: float | None
    current_value: float | None
    pnl: float | None
    status: PositionStatus  # OPEN, CLOSED
    opened_at: datetime | None
    closed_at: datetime | None
```

### 依赖关系

**本故事依赖:**
- Story 9.1: Telegram Bot 配置与初始化 (TelegramClient)
- Story 9.2: 通知消息发送 (TelegramNotifier)
- Story 5.2: Paper Trading 执行器 (PaperTradingExecutor)
- Story 5.3: 交易决策流程 (TradingExecutor)
- Story 1.3: 日志系统 (get_logger)
- Story 1.7: Pydantic 数据模型 (Trade, Market, Position)

**后续故事依赖本故事:**
- Story 9.4: LLM 分析结果通知 (需要通知模式)

### 实现注意事项

**关键点:**

1. **可选依赖注入**: TelegramNotifier 是可选的，不影响核心交易功能
2. **错误隔离**: 通知发送失败不影响交易执行
3. **向后兼容**: 现有代码无需修改即可继续工作
4. **日志记录**: 记录通知发送状态，便于调试

**与现有代码的集成:**
- TradingExecutor 通过构造函数接收 notifier
- 主入口 (main.py) 负责创建和注入 notifier
- 通知发送使用 try/except 包装，确保异常不传播

**平仓通知的实现:**
- 需要在 PositionManager 中添加通知支持
- 或者通过 TradingExecutor 处理平仓后通知
- 建议在 PositionManager 中添加 notifier 参数

### 前一个故事学习 [Source: 9-2-notification-message-sending.md]

**从 Story 9.2 学到的模式:**

1. **依赖注入**: TelegramNotifier 接收 TelegramClient 实例
2. **配置开关**: 使用 `settings.telegram.enabled` 控制发送
3. **错误处理**: 发送失败不抛出异常，只记录日志
4. **消息格式**: 使用 Markdown 格式，支持 emoji
5. **返回值**: 发送方法返回 bool 表示成功/失败

### 测试策略

```python
# tests/test_trading/test_executor_notifications.py
"""Tests for TradingExecutor notification integration.

Story 9.3: 交易事件通知集成
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.trading.executor import TradingExecutor, TradingDecision
from src.models.trade import Trade, TradeType, TradeMode, TradeStatus
from src.models.market import Market
from src.models.prediction import PredictionResult, Recommendation


class TestTradingExecutorNotifications:
    """Tests for TradingExecutor notification integration."""

    @pytest.fixture
    def mock_components(self) -> dict:
        """Create mock components for TradingExecutor."""
        return {
            "llm_analyzer": AsyncMock(),
            "risk_controller": AsyncMock(),
            "paper_executor": AsyncMock(),
            "state": AsyncMock(),
        }

    @pytest.fixture
    def mock_notifier(self) -> AsyncMock:
        """Create a mock TelegramNotifier."""
        notifier = AsyncMock()
        notifier.send_trade_notification = AsyncMock(return_value=True)
        notifier.send_error_notification = AsyncMock(return_value=True)
        return notifier

    @pytest.fixture
    def sample_market(self) -> Market:
        """Create a sample market."""
        return Market(
            id="market-1",
            title="Will Trump win 2028?",
            yes_price=0.65,
        )

    @pytest.fixture
    def sample_trade(self) -> Trade:
        """Create a sample trade."""
        return Trade(
            id=1,
            market_id="market-1",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=10.0,
            price=0.65,
            shares=15.38,
            status=TradeStatus.FILLED,
        )

    def test_init_with_notifier(
        self,
        mock_components: dict,
        mock_notifier: AsyncMock,
    ) -> None:
        """Test initialization with notifier."""
        with patch("src.trading.executor.settings") as mock_settings:
            mock_settings.trading_mode = "PAPER"

            executor = TradingExecutor(
                notifier=mock_notifier,
                **mock_components,
            )

            assert executor._notifier is mock_notifier

    def test_init_without_notifier(
        self,
        mock_components: dict,
    ) -> None:
        """Test initialization without notifier."""
        with patch("src.trading.executor.settings") as mock_settings:
            mock_settings.trading_mode = "PAPER"

            executor = TradingExecutor(**mock_components)

            assert executor._notifier is None

    @pytest.mark.asyncio
    async def test_notify_on_trade_success(
        self,
        mock_components: dict,
        mock_notifier: AsyncMock,
        sample_market: Market,
        sample_trade: Trade,
    ) -> None:
        """Test notification sent on trade success."""
        with patch("src.trading.executor.settings") as mock_settings:
            mock_settings.trading_mode = "PAPER"
            mock_settings.risk.min_bet = 5.0
            mock_settings.risk.max_single_ratio = 0.2

            # Setup mocks
            mock_components["llm_analyzer"].analyze_market = AsyncMock(
                return_value=PredictionResult(
                    predicted_probability=0.75,
                    confidence=0.85,
                    reasoning="Test",
                    key_assumptions=[],
                    recommendation=Recommendation.BUY_YES,
                )
            )
            mock_components["risk_controller"].check_trade_allowed = AsyncMock(
                return_value=MagicMock(allowed=True, position_ratio=0.1, reasons=[])
            )
            mock_components["state"].get_state = AsyncMock(
                return_value=MagicMock(current_capital=200.0)
            )
            mock_components["paper_executor"].execute_trade = AsyncMock(
                return_value=MagicMock(
                    success=True,
                    trade=sample_trade,
                    position=MagicMock(),
                )
            )

            executor = TradingExecutor(
                notifier=mock_notifier,
                **mock_components,
            )

            await executor.process_market(sample_market)

            # Verify notification was sent
            mock_notifier.send_trade_notification.assert_called_once()
            call_args = mock_notifier.send_trade_notification.call_args
            assert call_args[0][0] == sample_trade
            assert call_args[0][1] == sample_market

    @pytest.mark.asyncio
    async def test_notify_on_trade_failure(
        self,
        mock_components: dict,
        mock_notifier: AsyncMock,
        sample_market: Market,
    ) -> None:
        """Test notification sent on trade failure."""
        with patch("src.trading.executor.settings") as mock_settings:
            mock_settings.trading_mode = "PAPER"
            mock_settings.risk.min_bet = 5.0
            mock_settings.risk.max_single_ratio = 0.2

            # Setup mocks
            mock_components["llm_analyzer"].analyze_market = AsyncMock(
                return_value=PredictionResult(
                    predicted_probability=0.75,
                    confidence=0.85,
                    reasoning="Test",
                    key_assumptions=[],
                    recommendation=Recommendation.BUY_YES,
                )
            )
            mock_components["risk_controller"].check_trade_allowed = AsyncMock(
                return_value=MagicMock(allowed=True, position_ratio=0.1, reasons=[])
            )
            mock_components["state"].get_state = AsyncMock(
                return_value=MagicMock(current_capital=200.0)
            )
            mock_components["paper_executor"].execute_trade = AsyncMock(
                return_value=MagicMock(
                    success=False,
                    trade=None,
                    position=None,
                    error_message="Test error",
                )
            )

            executor = TradingExecutor(
                notifier=mock_notifier,
                **mock_components,
            )

            await executor.process_market(sample_market)

            # Verify error notification was sent
            mock_notifier.send_error_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_notification_when_notifier_is_none(
        self,
        mock_components: dict,
        sample_market: Market,
        sample_trade: Trade,
    ) -> None:
        """Test no notification when notifier is None."""
        with patch("src.trading.executor.settings") as mock_settings:
            mock_settings.trading_mode = "PAPER"
            mock_settings.risk.min_bet = 5.0
            mock_settings.risk.max_single_ratio = 0.2

            # Setup mocks
            mock_components["llm_analyzer"].analyze_market = AsyncMock(
                return_value=PredictionResult(
                    predicted_probability=0.75,
                    confidence=0.85,
                    reasoning="Test",
                    key_assumptions=[],
                    recommendation=Recommendation.BUY_YES,
                )
            )
            mock_components["risk_controller"].check_trade_allowed = AsyncMock(
                return_value=MagicMock(allowed=True, position_ratio=0.1, reasons=[])
            )
            mock_components["state"].get_state = AsyncMock(
                return_value=MagicMock(current_capital=200.0)
            )
            mock_components["paper_executor"].execute_trade = AsyncMock(
                return_value=MagicMock(
                    success=True,
                    trade=sample_trade,
                    position=MagicMock(),
                )
            )

            executor = TradingExecutor(**mock_components)

            await executor.process_market(sample_market)

            # No exception should be raised

    @pytest.mark.asyncio
    async def test_notification_failure_does_not_affect_trade(
        self,
        mock_components: dict,
        mock_notifier: AsyncMock,
        sample_market: Market,
        sample_trade: Trade,
    ) -> None:
        """Test that notification failure doesn't affect trade result."""
        with patch("src.trading.executor.settings") as mock_settings:
            mock_settings.trading_mode = "PAPER"
            mock_settings.risk.min_bet = 5.0
            mock_settings.risk.max_single_ratio = 0.2

            # Setup mocks
            mock_components["llm_analyzer"].analyze_market = AsyncMock(
                return_value=PredictionResult(
                    predicted_probability=0.75,
                    confidence=0.85,
                    reasoning="Test",
                    key_assumptions=[],
                    recommendation=Recommendation.BUY_YES,
                )
            )
            mock_components["risk_controller"].check_trade_allowed = AsyncMock(
                return_value=MagicMock(allowed=True, position_ratio=0.1, reasons=[])
            )
            mock_components["state"].get_state = AsyncMock(
                return_value=MagicMock(current_capital=200.0)
            )
            mock_components["paper_executor"].execute_trade = AsyncMock(
                return_value=MagicMock(
                    success=True,
                    trade=sample_trade,
                    position=MagicMock(),
                )
            )

            # Make notification fail
            mock_notifier.send_trade_notification = AsyncMock(
                side_effect=Exception("Network error")
            )

            executor = TradingExecutor(
                notifier=mock_notifier,
                **mock_components,
            )

            # Should not raise exception
            result = await executor.process_market(sample_market)

            # Trade should still be successful
            assert result.success is True
            assert result.trade == sample_trade
```

### References

- [Source: epics.md#Story 9.3] - 原始 Story 定义
- [Source: 9-2-notification-message-sending.md] - 前一个故事实现
- [Source: src/trading/executor.py] - TradingExecutor 现有实现
- [Source: src/trading/paper_trading.py] - PaperTradingExecutor 实现
- [Source: src/notifications/telegram_notifier.py] - TelegramNotifier 实现
- [Source: src/models/trade.py] - Trade 数据模型
- [Source: src/models/market.py] - Market 数据模型
- [Source: src/models/position.py] - Position 数据模型
- [Source: architecture.md#Logging Patterns] - 日志格式和 emoji

## Dev Agent Record

### Agent Model Used

GLM-5

### Debug Log References

None

### Completion Notes List

- Task 1: 完成 TradingExecutor 构造函数修改，添加 notifier 参数并保持向后兼容
- Task 2: 实现交易成功通知，在 process_market 成功后发送通知
- Task 3: 实现交易失败通知，在 process_market 失败和异常时发送通知
- Task 4: 在 PositionManager.close_position 中添加可选的 market 参数和通知支持
- Task 5: 扩展 TelegramNotifier 添加 send_position_closed_notification 和 _format_position_closed_message 方法
- Task 6: 创建 test_executor_notifications.py 测试文件（11 个测试），扩展 test_telegram_notifier.py 添加 6 个平仓通知测试
- Task 7: 通过 mypy、black、isort 检查，所有相关测试通过（109 个）

### File List

- src/trading/executor.py (modified) - 添加 notifier 参数和通知方法
- src/trading/position_manager.py (modified) - 添加 notifier 参数和通知支持
- src/notifications/telegram_notifier.py (modified) - 添加平仓通知方法
- tests/test_trading/test_executor_notifications.py (new) - 通知集成测试
- tests/test_notifications/test_telegram_notifier.py (modified) - 平仓通知测试

## Change Log

- 2026-02-18: 完成 Story 9.3 交易事件通知集成实现
