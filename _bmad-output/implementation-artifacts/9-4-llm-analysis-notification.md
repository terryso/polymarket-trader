# Story 9.4: LLM 分析结果通知

Status: done

## Story

As a **用户**,
I want **在 LLM 完成市场分析时收到通知**,
So that **我能了解系统的分析决策**.

## Acceptance Criteria

**Given** 通知发送器和 LLM 分析器已实现 (Story 9.2, Epic 3)
**When** 在 `src/analysis/llm_analyzer.py` 集成通知
**Then** 在以下情况发送分析通知:
- LLM 分析完成且置信度 >= MIN_CONFIDENCE
- 预测方向与市场价格差距 >= MIN_EDGE
**And** 通知内容包含:
- 市场名称
- 市场价格 vs 预测概率
- 置信度、Edge
- 关键假设 (最多 3 条)
- 交易建议
```
🧠 *市场分析*
市场: Will BTC reach $100k?
市场价格: YES 0.55
预测概率: YES 0.75 (±0.10)
置信度: 85%
Edge: 20%
建议: BUY YES
```
**And** 可配置是否发送所有分析或仅可交易信号

## Tasks / Subtasks

- [x] Task 1: 修改 LLMAnalyzer 构造函数 (AC: #1)
  - [x] 1.1 添加 `notifier: TelegramNotifier | None` 参数
  - [x] 1.2 存储 notifier 到实例变量
  - [x] 1.3 记录日志说明通知是否启用
  - [x] 1.4 保持向后兼容 (notifier 可选)

- [x] Task 2: 实现分析完成通知 (AC: #1, #2)
  - [x] 2.1 在 `analyze_market()` 方法完成后检查是否发送通知
  - [x] 2.2 获取配置 `settings.risk.min_confidence` 和 `settings.risk.min_edge`
  - [x] 2.3 当置信度 >= MIN_CONFIDENCE 且 edge >= MIN_EDGE 时发送通知
  - [x] 2.4 调用 `notifier.send_analysis_notification(prediction, market)`
  - [x] 2.5 处理通知发送失败 (不影响主流程)

- [x] Task 3: 扩展 TelegramNotifier 分析消息 (AC: #2)
  - [x] 3.1 检查现有 `send_analysis_notification()` 方法是否满足需求
  - [x] 3.2 确保 `_format_analysis_message()` 包含:
    - 市场名称
    - 市场价格 vs 预测概率
    - 置信度、Edge
    - 关键假设 (最多 3 条)
    - 交易建议
  - [x] 3.3 如需要，更新消息格式模板

- [x] Task 4: 实现可配置通知策略 (AC: #4)
  - [x] 4.1 在 `src/config.py` 添加 `TELEGRAM_NOTIFY_ALL_ANALYSES` 配置项
  - [x] 4.2 默认为 False (仅发送可交易信号)
  - [x] 4.3 当为 True 时，发送所有分析结果 (包括不可交易的)
  - [x] 4.4 更新 `.env.example` 添加新配置项说明

- [x] Task 5: 编写测试 (AC: All)
  - [x] 5.1 创建 `tests/test_analysis/test_llm_analyzer_notifications.py`
  - [x] 5.2 测试可交易信号通知发送
  - [x] 5.3 测试不可交易信号时不发送通知 (默认配置)
  - [x] 5.4 测试 `TELEGRAM_NOTIFY_ALL_ANALYSES=True` 时发送所有通知
  - [x] 5.5 测试 notifier 为 None 时行为
  - [x] 5.6 测试通知发送失败不影响分析结果
  - [ ] 5.7 扩展 `tests/test_notifications/test_telegram_notifier.py` 添加分析通知测试 (skipped: existing tests sufficient)

- [x] Task 6: 代码质量检查 (AC: All)
  - [x] 6.1 运行 `mypy src/analysis/llm_analyzer.py` 无错误
  - [x] 6.2 运行 `mypy src/notifications/telegram_notifier.py` 无错误
  - [x] 6.3 运行 `black --check src/analysis/` 通过
  - [x] 6.4 运行 `isort --check src/analysis/` 通过
  - [x] 6.5 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: epics.md#Story 9.4]

**通知触发条件:**
- 置信度 >= MIN_CONFIDENCE (默认 75%)
- Edge >= MIN_EDGE (默认 10%)

**通知内容:**
```markdown
🧠 *市场分析*
市场: Will BTC reach $100k?
市场价格: YES 0.55
预测概率: YES 0.75 (±0.10)
置信度: 85%
Edge: 20%

*关键假设:*
- Economy stable
- No major news
- Technical indicators bullish

建议: BUY YES
```

### 现有依赖 [Source: Story 9.2, Story 9.3]

**TelegramNotifier 已实现的方法:**
- `send_message(text, parse_mode)` - 发送普通消息
- `send_analysis_notification(prediction, market)` - 发送分析结果通知
- `send_trade_notification(trade, market)` - 发送交易通知
- `send_error_notification(error)` - 发送错误告警
- `send_position_closed_notification(position, market, pnl, pnl_pct)` - 发送平仓通知

**分析通知格式化方法:**
- `_format_analysis_message(prediction, market)` - 已实现

### 现有 LLM 分析流程 [Source: src/analysis/llm_analyzer.py]

**LLMAnalyzer.analyze_market() 流程:**
```python
async def analyze_market(self, market: "Market") -> PredictionResult:
    # 1. 构造提示词
    prompt = self._build_prompt(market)

    # 2. 调用 LLM API
    response = await self._llm_client.chat_with_system(
        system_prompt=MARKET_ANALYSIS_SYSTEM_PROMPT,
        user_prompt=prompt,
    )

    # 3. 解析响应
    result = self._parse_response(response, market)

    # 4. 计算 Edge
    result.edge = self._calculate_edge(result, market)

    return result
```

### 配置项 [Source: src/config.py]

**现有风险控制配置:**
```python
# 置信度门槛
MIN_CONFIDENCE: float = 0.75
MIN_EDGE: float = 0.10
```

**需要新增的配置:**
```python
# Telegram 分析通知配置
TELEGRAM_NOTIFY_ALL_ANALYSES: bool = False  # 仅发送可交易信号
```

### 实现模板

**LLMAnalyzer 修改:**

```python
# src/analysis/llm_analyzer.py
"""LLM-based market analyzer for the Polymarket Trader application.

... (existing docstring)

Story 3.3: LLM 分析引擎
Story 9.4: LLM 分析结果通知
"""

from __future__ import annotations

__all__ = ["LLMAnalyzer"]

from typing import TYPE_CHECKING

from src.config import settings
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.api.llm import LLMClient
    from src.models.market import Market
    from src.models.prediction import PredictionResult
    from src.notifications.telegram_notifier import TelegramNotifier


class LLMAnalyzer:
    """LLM-based market analyzer.

    ... (existing docstring)

    Story 9.4: Added Telegram notification support for analysis results.

    Attributes:
        _llm_client: LLM API client
        _logger: Logger instance
        _notifier: Optional TelegramNotifier for analysis notifications
    """

    def __init__(
        self,
        llm_client: "LLMClient",
        notifier: "TelegramNotifier | None" = None,
    ) -> None:
        """Initialize the LLM analyzer.

        Args:
            llm_client: LLM API client for making predictions
            notifier: Optional Telegram notifier for analysis notifications
        """
        self._llm_client = llm_client
        self._notifier = notifier
        self._logger = get_logger(__name__)

        if self._notifier:
            self._logger.info("LLMAnalyzer initialized (notifications=enabled)")
        else:
            self._logger.info("LLMAnalyzer initialized (notifications=disabled)")

    async def analyze_market(self, market: "Market") -> "PredictionResult":
        """Analyze a market and return a prediction.

        ... (existing docstring)

        Story 9.4: Added notification support for analysis results.
        """
        self._logger.info(f"Analyzing market: {market.id} - {market.title}")

        try:
            # 1. Build prompt
            prompt = self._build_prompt(market)

            # 2. Call LLM API
            response = await self._llm_client.chat_with_system(
                system_prompt=MARKET_ANALYSIS_SYSTEM_PROMPT,
                user_prompt=prompt,
            )

            # 3. Parse response
            result = self._parse_response(response, market)

            # 4. Calculate edge
            result.edge = self._calculate_edge(result, market)

            # 5. Log result
            self._logger.info(
                f"Analysis complete for {market.id}: "
                f"recommendation={result.recommendation.value}, "
                f"confidence={result.confidence:.2%}, "
                f"edge={result.edge:.2%}"
            )

            # Story 9.4: Send notification
            await self._notify_analysis_result(result, market)

            return result

        except Exception as e:
            self._logger.error(f"Error analyzing market {market.id}: {e}")
            raise

    async def _notify_analysis_result(
        self,
        prediction: "PredictionResult",
        market: "Market",
    ) -> None:
        """Send analysis result notification if conditions are met.

        Story 9.4: LLM 分析结果通知

        Args:
            prediction: The LLM prediction result
            market: The analyzed market
        """
        if not self._notifier:
            return

        try:
            # Check if we should send notification
            should_notify = self._should_notify_analysis(prediction)

            if not should_notify:
                self._logger.debug(
                    f"Skipping notification for {market.id}: "
                    f"not a tradeable signal"
                )
                return

            # Send notification
            success = await self._notifier.send_analysis_notification(
                prediction, market
            )
            if success:
                self._logger.debug(
                    f"Analysis notification sent for {market.id}"
                )
            else:
                self._logger.warning(
                    f"Failed to send analysis notification for {market.id}"
                )

        except Exception as e:
            # Don't let notification failure affect main flow
            self._logger.error(f"Error sending analysis notification: {e}")

    def _should_notify_analysis(self, prediction: "PredictionResult") -> bool:
        """Determine if analysis result should trigger notification.

        Args:
            prediction: The LLM prediction result

        Returns:
            True if notification should be sent
        """
        # If configured to notify all analyses, always return True
        if settings.telegram.notify_all_analyses:
            return True

        # Otherwise, only notify for tradeable signals
        min_confidence = settings.risk.min_confidence
        min_edge = settings.risk.min_edge

        # Check confidence threshold
        if prediction.confidence < min_confidence:
            return False

        # Check edge threshold
        if prediction.edge is not None and prediction.edge < min_edge:
            return False

        # Check recommendation is not NO_TRADE
        if prediction.recommendation.value == "NO_TRADE":
            return False

        return True
```

**Config 扩展:**

```python
# src/config.py (添加新配置项)

class TelegramSettings(BaseSettings):
    """Telegram configuration settings."""

    bot_token: str | None = Field(
        default=None,
        alias="TELEGRAM_BOT_TOKEN",
        description="Telegram Bot Token",
    )
    chat_id: str | None = Field(
        default=None,
        alias="TELEGRAM_CHAT_ID",
        description="Authorized Chat ID",
    )
    enabled: bool = Field(
        default=False,
        alias="TELEGRAM_ENABLED",
        description="Enable Telegram notifications",
    )
    notify_all_analyses: bool = Field(
        default=False,
        alias="TELEGRAM_NOTIFY_ALL_ANALYSES",
        description="Notify all analyses (not just tradeable signals)",
    )
```

### 项目结构 [Source: architecture.md#Project Structure]

**修改文件:**
```
src/analysis/
├── llm_analyzer.py          # 修改: 添加通知集成
└── ...

src/config.py                # 修改: 添加 notify_all_analyses 配置

tests/test_analysis/
└── test_llm_analyzer_notifications.py  # 新增: 通知集成测试

tests/test_notifications/
└── test_telegram_notifier.py          # 修改: 添加分析通知测试
```

### 数据模型 [Source: src/models/]

**PredictionResult 模型关键字段:**
```python
class PredictionResult(BaseModel):
    predicted_probability: float  # 0-1
    confidence: float             # 0-1
    reasoning: str
    key_assumptions: list[str]
    recommendation: Recommendation  # BUY_YES, BUY_NO, NO_TRADE
    edge: float | None           # 0-1
```

**Recommendation 枚举:**
```python
class Recommendation(str, Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    NO_TRADE = "NO_TRADE"
```

### 依赖关系

**本故事依赖:**
- Story 9.1: Telegram Bot 配置与初始化 (TelegramClient)
- Story 9.2: 通知消息发送 (TelegramNotifier)
- Story 9.3: 交易事件通知集成 (通知模式参考)
- Story 3.3: LLM 分析引擎 (LLMAnalyzer)
- Story 1.3: 日志系统 (get_logger)
- Story 1.7: Pydantic 数据模型 (Market, PredictionResult)

**后续故事依赖本故事:**
- Story 9.5: 命令处理 - 状态查询 (需要理解分析通知模式)

### 实现注意事项

**关键点:**

1. **可选依赖注入**: TelegramNotifier 是可选的，不影响核心分析功能
2. **错误隔离**: 通知发送失败不影响分析结果
3. **向后兼容**: 现有代码无需修改即可继续工作
4. **配置灵活**: 支持配置是否发送所有分析或仅可交易信号
5. **条件判断**: 只有满足交易条件时才发送通知 (默认)

**通知策略:**
- 默认: 仅发送可交易信号 (置信度 >= 75%, edge >= 10%, 非 NO_TRADE)
- 可配置: `TELEGRAM_NOTIFY_ALL_ANALYSES=True` 发送所有分析

**与 Story 9.3 的区别:**
- Story 9.3: 交易执行时通知 (交易成功/失败)
- Story 9.4: 分析完成时通知 (分析结果，不一定交易)

### 前一个故事学习 [Source: 9-3-trade-event-notification.md]

**从 Story 9.3 学到的模式:**

1. **可选依赖注入**: notifier 参数可选，默认为 None
2. **错误隔离**: 通知发送使用 try/except 包装，确保异常不传播
3. **日志记录**: 记录通知发送状态，便于调试
4. **私有通知方法**: 使用 `_notify_*` 私有方法封装通知逻辑
5. **条件检查**: 发送前检查是否应该发送

### 测试策略

```python
# tests/test_analysis/test_llm_analyzer_notifications.py
"""Tests for LLMAnalyzer notification integration.

Story 9.4: LLM 分析结果通知
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.analysis.llm_analyzer import LLMAnalyzer
from src.models.market import Market
from src.models.prediction import PredictionResult, Recommendation


class TestLLMAnalyzerNotifications:
    """Tests for LLMAnalyzer notification integration."""

    @pytest.fixture
    def mock_llm_client(self) -> AsyncMock:
        """Create a mock LLM client."""
        return AsyncMock()

    @pytest.fixture
    def mock_notifier(self) -> AsyncMock:
        """Create a mock TelegramNotifier."""
        notifier = AsyncMock()
        notifier.send_analysis_notification = AsyncMock(return_value=True)
        return notifier

    @pytest.fixture
    def sample_market(self) -> Market:
        """Create a sample market."""
        return Market(
            id="market-1",
            title="Will BTC reach $100k?",
            yes_price=0.55,
        )

    @pytest.fixture
    def tradeable_prediction(self) -> PredictionResult:
        """Create a tradeable prediction."""
        return PredictionResult(
            predicted_probability=0.75,
            confidence=0.85,
            reasoning="Strong indicators",
            key_assumptions=["Economy stable", "No major news"],
            recommendation=Recommendation.BUY_YES,
            edge=0.20,
        )

    @pytest.fixture
    def non_tradeable_prediction(self) -> PredictionResult:
        """Create a non-tradeable prediction (low confidence)."""
        return PredictionResult(
            predicted_probability=0.55,
            confidence=0.60,  # Below 75% threshold
            reasoning="Uncertain",
            key_assumptions=[],
            recommendation=Recommendation.BUY_YES,
            edge=0.05,
        )

    def test_init_with_notifier(
        self,
        mock_llm_client: AsyncMock,
        mock_notifier: AsyncMock,
    ) -> None:
        """Test initialization with notifier."""
        with patch("src.analysis.llm_analyzer.get_logger"):
            analyzer = LLMAnalyzer(
                llm_client=mock_llm_client,
                notifier=mock_notifier,
            )
            assert analyzer._notifier is mock_notifier

    def test_init_without_notifier(
        self,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Test initialization without notifier."""
        with patch("src.analysis.llm_analyzer.get_logger"):
            analyzer = LLMAnalyzer(llm_client=mock_llm_client)
            assert analyzer._notifier is None

    @pytest.mark.asyncio
    async def test_notify_tradeable_signal(
        self,
        mock_llm_client: AsyncMock,
        mock_notifier: AsyncMock,
        sample_market: Market,
        tradeable_prediction: PredictionResult,
    ) -> None:
        """Test notification sent for tradeable signal."""
        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                analyzer = LLMAnalyzer(
                    llm_client=mock_llm_client,
                    notifier=mock_notifier,
                )

                # Call _should_notify_analysis
                should_notify = analyzer._should_notify_analysis(tradeable_prediction)
                assert should_notify is True

    @pytest.mark.asyncio
    async def test_no_notify_non_tradeable(
        self,
        mock_llm_client: AsyncMock,
        mock_notifier: AsyncMock,
        sample_market: Market,
        non_tradeable_prediction: PredictionResult,
    ) -> None:
        """Test no notification for non-tradeable signal."""
        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                analyzer = LLMAnalyzer(
                    llm_client=mock_llm_client,
                    notifier=mock_notifier,
                )

                should_notify = analyzer._should_notify_analysis(non_tradeable_prediction)
                assert should_notify is False

    @pytest.mark.asyncio
    async def test_notify_all_when_configured(
        self,
        mock_llm_client: AsyncMock,
        mock_notifier: AsyncMock,
        sample_market: Market,
        non_tradeable_prediction: PredictionResult,
    ) -> None:
        """Test notification sent for all analyses when configured."""
        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = True
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                analyzer = LLMAnalyzer(
                    llm_client=mock_llm_client,
                    notifier=mock_notifier,
                )

                should_notify = analyzer._should_notify_analysis(non_tradeable_prediction)
                assert should_notify is True

    @pytest.mark.asyncio
    async def test_notification_failure_does_not_affect_analysis(
        self,
        mock_llm_client: AsyncMock,
        mock_notifier: AsyncMock,
        sample_market: Market,
        tradeable_prediction: PredictionResult,
    ) -> None:
        """Test that notification failure doesn't affect analysis result."""
        with patch("src.analysis.llm_analyzer.get_logger"):
            with patch("src.analysis.llm_analyzer.settings") as mock_settings:
                mock_settings.telegram.notify_all_analyses = False
                mock_settings.risk.min_confidence = 0.75
                mock_settings.risk.min_edge = 0.10

                # Make notification fail
                mock_notifier.send_analysis_notification = AsyncMock(
                    side_effect=Exception("Network error")
                )

                analyzer = LLMAnalyzer(
                    llm_client=mock_llm_client,
                    notifier=mock_notifier,
                )

                # Should not raise exception
                await analyzer._notify_analysis_result(
                    tradeable_prediction, sample_market
                )
```

### References

- [Source: epics.md#Story 9.4] - 原始 Story 定义
- [Source: 9-3-trade-event-notification.md] - 前一个故事实现 (通知模式参考)
- [Source: 9-2-notification-message-sending.md] - TelegramNotifier 实现
- [Source: src/analysis/llm_analyzer.py] - LLMAnalyzer 现有实现
- [Source: src/notifications/telegram_notifier.py] - TelegramNotifier 实现
- [Source: src/models/prediction.py] - PredictionResult 数据模型
- [Source: src/models/market.py] - Market 数据模型
- [Source: architecture.md#Logging Patterns] - 日志格式和 emoji
- [Source: src/config.py] - 配置管理

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
