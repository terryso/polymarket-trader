# Story 9.10: Telegram 命令处理 - 手动触发分析

Status: review

## Story

As a **用户**,
I want **通过 Telegram 命令手动触发市场分析**,
So that **我能让系统分析特定的市场**.

## Acceptance Criteria

**Given** 交易历史命令已实现 (Story 9.9)
**When** 添加 `/predict` 命令
**Then** 实现手动分析功能:
- `/predict` - 返回可选市场列表 (带序号)
- `/predict 3` - 对第 3 个市场执行 LLM 分析
- `/predict <market_id>` - 对指定市场 ID 执行分析
**And** 分析完成后自动发送结果通知
**And** 命令响应:
```
🧠 *分析中...*
市场: Will Trump win 2028?
请稍候，LLM 正在分析...
```
**And** 如果分析结果符合交易条件，询问是否执行:
```
分析完成！建议 BUY YES
是否执行交易？回复 /confirm 或 /cancel
```
**And** 记录手动触发日志

## Tasks / Subtasks

- [x] Task 1: 扩展命令处理模块 (AC: #1)
  - [x] 1.1 在 `src/telegram_commands/handlers.py` 添加 `create_predict_handler()`
  - [x] 1.2 添加 `create_confirm_handler()` 和 `create_cancel_handler()` 用于交易确认
  - [x] 1.3 在 `setup_command_handlers()` 中注册 `/predict`, `/confirm`, `/cancel` 命令
  - [x] 1.4 实现会话状态管理 (存储待确认的分析结果)

- [x] Task 2: 实现市场列表展示 (AC: #1)
  - [x] 2.1 从 MarketRepository 获取活跃市场列表
  - [x] 2.2 限制市场列表数量 (默认显示前 10 个)
  - [x] 2.3 格式化市场列表 (序号 + 市场标题 + 价格)
  - [x] 2.4 处理空市场列表情况

- [x] Task 3: 实现参数解析 (AC: #1)
  - [x] 3.1 无参数时返回市场列表
  - [x] 3.2 解析数字参数作为市场序号
  - [x] 3.3 解析字符串参数作为市场 ID
  - [x] 3.4 验证市场存在性

- [x] Task 4: 实现 LLM 分析触发 (AC: #1, #2)
  - [x] 4.1 发送 "分析中..." 提示消息
  - [x] 4.2 调用 `LLMAnalyzer.analyze_market()` 执行分析
  - [x] 4.3 捕获分析异常并返回友好错误信息
  - [x] 4.4 格式化分析结果并发送通知

- [x] Task 5: 实现交易确认流程 (AC: #3)
  - [x] 5.1 当分析结果符合交易条件时存储到会话状态
  - [x] 5.2 发送确认提示消息
  - [x] 5.3 `/confirm` 命令触发生成交易建议 (不执行真实交易)
  - [x] 5.4 `/cancel` 命令取消待确认状态
  - [x] 5.5 设置会话超时 (30 秒)

- [x] Task 6: 实现消息格式化 (AC: #1, #2, #3)
  - [x] 6.1 在 `src/telegram_commands/formatters.py` 添加 `format_predict_market_list()`
  - [x] 6.2 添加 `format_analyzing_message()` - 分析中提示
  - [x] 6.3 添加 `format_predict_result()` - 分析结果
  - [x] 6.4 添加 `format_trade_confirmation()` - 交易确认提示
  - [x] 6.5 添加 `format_trade_cancelled()` - 交易取消提示

- [x] Task 7: 更新帮助信息 (AC: #1)
  - [x] 7.1 在 `format_help_message()` 中添加 `/predict` 命令描述
  - [x] 7.2 添加 `/confirm` 和 `/cancel` 命令说明

- [x] Task 8: 编写测试 (AC: All)
  - [x] 8.1 在 `tests/test_telegram_commands/test_handlers.py` 添加 predict handler 测试
  - [x] 8.2 测试无参数返回市场列表
  - [x] 8.3 测试数字参数 (市场序号)
  - [x] 8.4 测试字符串参数 (市场 ID)
  - [x] 8.5 测试分析成功场景
  - [x] 8.6 测试分析失败场景
  - [x] 8.7 测试交易确认/取消流程
  - [x] 8.8 测试未授权用户访问
  - [x] 8.9 测试 formatter 函数

- [x] Task 9: 代码质量检查 (AC: All)
  - [x] 9.1 运行 `mypy src/telegram_commands/` 无错误
  - [x] 9.2 运行 `black --check src/telegram_commands/` 通过
  - [x] 9.3 运行 `isort --check src/telegram_commands/` 通过
  - [x] 9.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: epics.md#Story 9.10]

**`/predict` 命令流程:**

1. **无参数 - 显示市场列表:**
```markdown
🧠 *选择市场分析*

1. *Will Trump win 2028?*
   YES: 0.65 | 流动性: $50k

2. *BTC > $100k by 2025?*
   YES: 0.45 | 流动性: $120k

3. *Fed rate cut in March?*
   YES: 0.72 | 流动性: $80k

回复 `/predict <序号>` 或 `/predict <市场ID>` 开始分析
```

2. **有参数 - 开始分析:**
```markdown
🧠 *分析中...*
市场: Will Trump win 2028?
请稍候，LLM 正在分析...
```

3. **分析完成 - 可交易信号:**
```markdown
🧠 *市场分析完成*

市场: Will Trump win 2028?
市场价格: YES 0.65
预测概率: YES 0.80 (±0.08)
置信度: 85%
Edge: 15%

建议: BUY YES

是否执行交易？
回复 /confirm 确认 或 /cancel 取消
```

4. **分析完成 - 不可交易:**
```markdown
🧠 *市场分析完成*

市场: Will Trump win 2028?
预测概率: YES 0.55
置信度: 60%
Edge: 5%

建议: NO_TRADE

(置信度或 Edge 未达到交易门槛)
```

**会话状态管理:**
```python
# 存储待确认的交易
pending_confirmations: dict[str, PendingConfirmation] = {}

class PendingConfirmation:
    chat_id: str
    market_id: str
    prediction: PredictionResult
    created_at: datetime
    expires_at: datetime  # 30 秒后过期
```

### 现有依赖 [Source: Story 9.5, 9.6, 9.7, 9.8, 9.9]

**命令处理框架已实现:**
- `src/telegram_commands/__init__.py` - 模块导出
- `src/telegram_commands/handlers.py` - 命令处理函数
- `src/telegram_commands/formatters.py` - 消息格式化

**已有的处理模式:**
```python
def create_xxx_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    # 1. 验证授权
    # 2. 解析参数
    # 3. 获取数据
    # 4. 格式化消息
    # 5. 发送响应
```

### LLM 分析器 [Source: src/analysis/llm_analyzer.py]

**LLMAnalyzer 类:**
```python
class LLMAnalyzer:
    async def analyze_market(self, market: Market) -> PredictionResult:
        """分析单个市场.

        Args:
            market: 要分析的市场

        Returns:
            PredictionResult 包含预测概率、置信度、建议等

        Raises:
            AnalysisError: 如果分析过程中出现错误
        """
```

**PredictionResult 模型:**
```python
class PredictionResult(BaseModel):
    predicted_probability: float  # 预测概率 (0-1)
    confidence: float             # 置信度 (0-1)
    reasoning: str                # 分析理由
    key_assumptions: list[str]    # 关键假设
    recommendation: Recommendation  # 交易建议
    edge: float | None = None     # Edge 值
```

### 数据模型 [Source: src/models/market.py]

**Market 模型:**
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
    resolution_status: str | None
    resolution_outcome: str | None
    created_at: datetime | None
    updated_at: datetime | None
```

### 数据访问 [Source: src/storage/repositories/market_repo.py]

**MarketRepository 方法:**
```python
async def get_active_markets(
    self,
    limit: int = 10,
    offset: int = 0,
) -> list[Market]:
    """获取活跃市场列表.

    Args:
        limit: 返回数量限制
        offset: 偏移量

    Returns:
        活跃市场列表
    """

async def get_market(market_id: str) -> Market | None:
    """获取单个市场.
    """
```

### 实现模板

**handlers.py 扩展:**

```python
# 在 src/telegram_commands/handlers.py 中添加

from datetime import datetime, timedelta
from typing import Any

from src.analysis import LLMAnalyzer, AnalysisError
from src.config import settings
from src.models import Market
from src.models.prediction import PredictionResult, Recommendation
from src.storage.repositories import MarketRepository


# 会话状态 - 存储待确认的交易
_pending_confirmations: dict[str, "PendingConfirmation"] = {}


class PendingConfirmation:
    """待确认的交易请求."""

    def __init__(
        self,
        chat_id: str,
        market: Market,
        prediction: PredictionResult,
    ):
        self.chat_id = chat_id
        self.market = market
        self.prediction = prediction
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=30)

    def is_expired(self) -> bool:
        """检查是否已过期."""
        return datetime.now() > self.expires_at


def create_predict_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a predict command handler.

    Args:
        authorized_chat_id: Authorized chat ID for access control

    Returns:
        Async function that handles /predict command
    """

    async def predict_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /predict command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = update.effective_chat.id
        chat_id_str = str(chat_id)

        # Verify authorization
        if authorized_chat_id and chat_id_str != str(authorized_chat_id):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        market_repo = MarketRepository()
        analyzer = LLMAnalyzer()

        # Parse parameters
        if not context.args or len(context.args) == 0:
            # No args - show market list
            markets = await market_repo.get_active_markets(limit=10)
            message = format_predict_market_list(markets)
            await update.message.reply_text(message, parse_mode="Markdown")
            return

        # Get market by index or ID
        market = None
        arg = context.args[0]

        # Try to parse as index (number)
        try:
            index = int(arg) - 1  # Convert to 0-based index
            if index < 0:
                await update.message.reply_text(
                    "❌ 无效的市场序号，请使用正整数",
                    parse_mode="Markdown",
                )
                return
            markets = await market_repo.get_active_markets(limit=index + 1)
            if index >= len(markets):
                await update.message.reply_text(
                    f"❌ 市场序号 {index + 1} 不存在",
                    parse_mode="Markdown",
                )
                return
            market = markets[index]
        except ValueError:
            # Not a number, try as market ID
            market = await market_repo.get_market(arg)
            if not market:
                await update.message.reply_text(
                    f"❌ 市场不存在: {arg}",
                    parse_mode="Markdown",
                )
                return

        # Send analyzing message
        analyzing_msg = format_analyzing_message(market)
        await update.message.reply_text(analyzing_msg, parse_mode="Markdown")

        # Execute analysis
        try:
            result = await analyzer.analyze_market(market)

            # Check if tradeable
            is_tradeable = result.confidence >= settings.risk.min_confidence
            if result.edge is not None:
                is_tradeable = is_tradeable and result.edge >= settings.risk.min_edge
            is_tradeable = is_tradeable and result.recommendation != Recommendation.NO_TRADE

            if is_tradeable:
                # Store pending confirmation
                _pending_confirmations[chat_id_str] = PendingConfirmation(
                    chat_id=chat_id_str,
                    market=market,
                    prediction=result,
                )
                message = format_predict_result_with_confirm(market, result)
            else:
                message = format_predict_result_no_trade(market, result)

            await update.message.reply_text(message, parse_mode="Markdown")
            logger.info(f"Predict command completed for chat_id: {chat_id}, market: {market.id}")

        except AnalysisError as e:
            logger.error(f"Analysis error for market {market.id}: {e}")
            await update.message.reply_text(
                f"❌ 分析失败: {e.message}",
                parse_mode="Markdown",
            )

    return predict_handler


def create_confirm_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a confirm command handler for trade confirmation."""

    async def confirm_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /confirm command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = str(update.effective_chat.id)

        # Verify authorization
        if authorized_chat_id and chat_id != str(authorized_chat_id):
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Check for pending confirmation
        pending = _pending_confirmations.get(chat_id)
        if not pending:
            await update.message.reply_text(
                "❌ 没有待确认的交易。请先使用 /predict 分析市场。",
                parse_mode="Markdown",
            )
            return

        if pending.is_expired():
            del _pending_confirmations[chat_id]
            await update.message.reply_text(
                "❌ 确认已超时 (30秒)。请重新执行 /predict 分析。",
                parse_mode="Markdown",
            )
            return

        # Generate trade suggestion (NOT executing actual trade)
        message = format_trade_suggestion(pending.market, pending.prediction)
        del _pending_confirmations[chat_id]

        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Trade confirmed for chat_id: {chat_id}")

    return confirm_handler


def create_cancel_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a cancel command handler."""

    async def cancel_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /cancel command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = str(update.effective_chat.id)

        # Verify authorization
        if authorized_chat_id and chat_id != str(authorized_chat_id):
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Check for pending confirmation
        if chat_id in _pending_confirmations:
            del _pending_confirmations[chat_id]
            message = format_trade_cancelled()
        else:
            message = "没有待取消的交易。"

        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Trade cancelled for chat_id: {chat_id}")

    return cancel_handler


def setup_command_handlers(
    application: Application,
    state_manager: "ThreadSafeState",
    authorized_chat_id: str | None = None,
) -> None:
    """Setup all command handlers for the Telegram bot."""
    # Create handlers with injected dependencies
    status_handler = create_status_handler(state_manager, authorized_chat_id)
    help_handler = create_help_handler(authorized_chat_id)
    positions_handler = create_positions_handler(authorized_chat_id)
    stats_handler = create_stats_handler(authorized_chat_id)
    markets_handler = create_markets_handler(authorized_chat_id)
    history_handler = create_history_handler(authorized_chat_id)
    predict_handler = create_predict_handler(authorized_chat_id)  # NEW
    confirm_handler = create_confirm_handler(authorized_chat_id)  # NEW
    cancel_handler = create_cancel_handler(authorized_chat_id)    # NEW

    # Register handlers
    application.add_handler(CommandHandler("status", status_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("help", help_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("positions", positions_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("stats", stats_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("markets", markets_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("history", history_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("predict", predict_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("confirm", confirm_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("cancel", cancel_handler))    # type: ignore[arg-type]

    logger.info(
        "Command handlers registered: /status, /help, /positions, /stats, "
        "/markets, /history, /predict, /confirm, /cancel"
    )
```

**formatters.py 扩展:**

```python
# 在 src/telegram_commands/formatters.py 中添加


def format_predict_market_list(markets: list["Market"]) -> str:
    """Format a market list for predict command.

    Args:
        markets: List of Market models to display

    Returns:
        Formatted Markdown message
    """
    if not markets:
        return "\U0001f9e0 *选择市场分析*\n\n暂无活跃市场"

    lines = [
        "\U0001f9e0 *选择市场分析*",
        "",
    ]

    for i, market in enumerate(markets, 1):
        # Format price
        price_str = ""
        if market.yes_price is not None:
            price_str = f"YES: {market.yes_price:.2f}"
        elif market.no_price is not None:
            price_str = f"NO: {market.no_price:.2f}"

        # Format liquidity
        liquidity_str = ""
        if market.liquidity is not None:
            if market.liquidity >= 1000:
                liquidity_str = f"${market.liquidity / 1000:.0f}k"
            else:
                liquidity_str = f"${market.liquidity:.0f}"

        lines.extend([
            f"{i}. *{market.title[:50]}{'...' if len(market.title) > 50 else ''}*",
            f"   {price_str} | 流动性: {liquidity_str}",
            "",
        ])

    lines.append("回复 `/predict <序号>` 或 `/predict <市场ID>` 开始分析")

    return "\n".join(lines)


def format_analyzing_message(market: "Market") -> str:
    """Format analyzing in progress message.

    Args:
        market: Market being analyzed

    Returns:
        Formatted Markdown message
    """
    return "\n".join([
        "\U0001f9e0 *分析中...*",
        f"市场: {market.title}",
        "请稍候，LLM 正在分析...",
    ])


def format_predict_result_with_confirm(
    market: "Market",
    prediction: "PredictionResult",
) -> str:
    """Format prediction result with trade confirmation.

    Args:
        market: Analyzed market
        prediction: LLM prediction result

    Returns:
        Formatted Markdown message
    """
    # Format recommendation
    if prediction.recommendation.value == "BUY_YES":
        rec_emoji = "\U0001f7e2"  # Green circle
        rec_text = "BUY YES"
    elif prediction.recommendation.value == "BUY_NO":
        rec_emoji = "\U0001f534"  # Red circle
        rec_text = "BUY NO"
    else:
        rec_emoji = "\U000023f9"  # Stop button
        rec_text = "NO_TRADE"

    # Format price
    price_str = f"YES {market.yes_price:.2f}" if market.yes_price else "N/A"

    lines = [
        "\U0001f9e0 *市场分析完成*",
        "",
        f"市场: {market.title}",
        f"市场价格: {price_str}",
        f"预测概率: {prediction.predicted_probability:.0%}",
        f"置信度: {prediction.confidence:.0%}",
    ]

    if prediction.edge is not None:
        lines.append(f"Edge: {prediction.edge:.0%}")

    lines.extend([
        "",
        f"建议: {rec_emoji} *{rec_text}*",
        "",
        "是否执行交易？",
        "回复 /confirm 确认 或 /cancel 取消",
    ])

    return "\n".join(lines)


def format_predict_result_no_trade(
    market: "Market",
    prediction: "PredictionResult",
) -> str:
    """Format prediction result when not tradeable.

    Args:
        market: Analyzed market
        prediction: LLM prediction result

    Returns:
        Formatted Markdown message
    """
    lines = [
        "\U0001f9e0 *市场分析完成*",
        "",
        f"市场: {market.title}",
        f"预测概率: {prediction.predicted_probability:.0%}",
        f"置信度: {prediction.confidence:.0%}",
    ]

    if prediction.edge is not None:
        lines.append(f"Edge: {prediction.edge:.0%}")

    lines.extend([
        "",
        f"建议: NO_TRADE",
        "",
        "_(置信度或 Edge 未达到交易门槛)_",
    ])

    return "\n".join(lines)


def format_trade_suggestion(
    market: "Market",
    prediction: "PredictionResult",
) -> str:
    """Format trade suggestion after confirmation.

    Note: This only shows the suggestion, does NOT execute actual trade.

    Args:
        market: Market to trade
        prediction: LLM prediction result

    Returns:
        Formatted Markdown message
    """
    # Calculate suggested position
    # (In production, this would use risk controller)
    position_ratio = settings.risk.max_single_ratio
    amount = settings.trading.initial_capital * position_ratio

    if prediction.recommendation.value == "BUY_YES":
        direction = "BUY YES"
        price = market.yes_price or 0.5
    else:
        direction = "BUY NO"
        price = market.no_price or (1 - (market.yes_price or 0.5))

    shares = amount / price if price > 0 else 0

    lines = [
        "\U0001f4b0 *交易建议*",
        "",
        f"市场: {market.title}",
        f"方向: {direction}",
        f"建议金额: ${amount:.2f}",
        f"价格: {price:.2f}",
        f"份额: {shares:.2f}",
        "",
        "_注意: 这是手动触发的分析建议。_",
        "_实际交易需要 Paper Trading 或 Live 模式启用。_",
    ]

    return "\n".join(lines)


def format_trade_cancelled() -> str:
    """Format trade cancelled message.

    Returns:
        Formatted Markdown message
    """
    return "\U0000274c *交易已取消*"
```

### 更新 __init__.py

```python
# src/telegram_commands/__init__.py
__all__ = [
    "setup_command_handlers",
    "create_status_handler",
    "create_help_handler",
    "create_positions_handler",
    "create_stats_handler",
    "create_markets_handler",
    "create_history_handler",
    "create_predict_handler",  # NEW
    "create_confirm_handler",  # NEW
    "create_cancel_handler",   # NEW
    "format_status_message",
    "format_help_message",
    "format_unauthorized_message",
    "format_positions_message",
    "format_stats_message",
    "format_markets_message",
    "format_history_message",
    "format_predict_market_list",      # NEW
    "format_analyzing_message",        # NEW
    "format_predict_result_with_confirm",  # NEW
    "format_predict_result_no_trade",  # NEW
    "format_trade_suggestion",         # NEW
    "format_trade_cancelled",          # NEW
]
```

### 更新帮助信息

```python
# 在 format_help_message() 中添加
help_text = """
*可用命令:*

/status - 查看系统状态
/positions - 查看当前持仓
/stats [days] - 查看交易统计
/markets [n] [category] - 查看活跃市场
/history [n] [paper|live] - 查看交易历史
/predict [序号|市场ID] - 手动触发市场分析  # NEW
/confirm - 确认交易建议  # NEW
/cancel - 取消交易建议  # NEW
/help - 显示帮助信息
"""
```

### 项目结构

**修改的文件:**
```
src/telegram_commands/
├── __init__.py              # 添加新导出
├── handlers.py              # 添加 create_predict_handler, create_confirm_handler, create_cancel_handler
└── formatters.py            # 添加 format_predict_* 函数

tests/test_telegram_commands/
└── test_handlers.py         # 添加 predict/confirm/cancel handler 测试
```

### 依赖关系

**本故事依赖:**
- Story 9.5: Telegram 命令处理 - 状态查询 (命令处理框架)
- Story 9.9: Telegram 命令处理 - 交易历史 (命令处理模式)
- Story 3.3: LLM 分析引擎 (LLMAnalyzer)
- Story 2.4: 市场数据仓库 (MarketRepository)

**后续故事依赖本故事:**
- Story 9.11: Telegram 命令处理 - 远程控制 (命令处理模式)

### 测试策略

```python
# tests/test_telegram_commands/test_handlers.py 添加

class TestPredictHandler:
    """Tests for predict command handler."""

    @pytest.fixture
    def mock_update(self) -> MagicMock:
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456789
        update.message = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock callback context."""
        context = MagicMock()
        context.args = []
        return context

    @pytest.mark.asyncio
    async def test_predict_handler_no_args_shows_list(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test predict handler without args shows market list."""
        with (
            patch("src.telegram_commands.handlers.MarketRepository") as MockMarketRepo,
            patch("src.telegram_commands.handlers.LLMAnalyzer"),
        ):
            mock_market_repo = MagicMock()
            mock_market_repo.get_active_markets = AsyncMock(return_value=[
                Market(id=f"market-{i}", title=f"Test Market {i}", yes_price=0.5 + i * 0.1)
                for i in range(5)
            ])
            MockMarketRepo.return_value = mock_market_repo

            handler = create_predict_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args.args[0]
            assert "*选择市场分析*" in call_args

    @pytest.mark.asyncio
    async def test_predict_handler_with_index(
        self, mock_update: MagicMock
    ) -> None:
        """Test predict handler with index parameter."""
        mock_context = MagicMock()
        mock_context.args = ["2"]

        with (
            patch("src.telegram_commands.handlers.MarketRepository") as MockMarketRepo,
            patch("src.telegram_commands.handlers.LLMAnalyzer") as MockAnalyzer,
        ):
            # Setup mock market repo
            mock_market_repo = MagicMock()
            mock_market_repo.get_active_markets = AsyncMock(return_value=[
                Market(id="market-1", title="Test Market 1", yes_price=0.5),
                Market(id="market-2", title="Test Market 2", yes_price=0.6),
            ])
            MockMarketRepo.return_value = mock_market_repo

            # Setup mock analyzer
            mock_analyzer = MagicMock()
            mock_analyzer.analyze_market = AsyncMock(return_value=PredictionResult(
                predicted_probability=0.8,
                confidence=0.85,
                reasoning="Test reasoning",
                key_assumptions=["Assumption 1"],
                recommendation=Recommendation.BUY_YES,
                edge=0.15,
            ))
            MockAnalyzer.return_value = mock_analyzer

            handler = create_predict_handler("123456789")
            await handler(mock_update, mock_context)

            # Verify analyze was called with second market (index 1)
            mock_analyzer.analyze_market.assert_called_once()
            called_market = mock_analyzer.analyze_market.call_args.args[0]
            assert called_market.id == "market-2"

    @pytest.mark.asyncio
    async def test_predict_handler_with_market_id(
        self, mock_update: MagicMock
    ) -> None:
        """Test predict handler with market ID parameter."""
        mock_context = MagicMock()
        mock_context.args = ["market-abc123"]

        with (
            patch("src.telegram_commands.handlers.MarketRepository") as MockMarketRepo,
            patch("src.telegram_commands.handlers.LLMAnalyzer") as MockAnalyzer,
        ):
            # Setup mock market repo
            mock_market_repo = MagicMock()
            mock_market_repo.get_market = AsyncMock(return_value=Market(
                id="market-abc123",
                title="Test Market",
                yes_price=0.6,
            ))
            MockMarketRepo.return_value = mock_market_repo

            # Setup mock analyzer
            mock_analyzer = MagicMock()
            mock_analyzer.analyze_market = AsyncMock(return_value=PredictionResult(
                predicted_probability=0.5,
                confidence=0.6,
                reasoning="Test",
                key_assumptions=[],
                recommendation=Recommendation.NO_TRADE,
                edge=0.05,
            ))
            MockAnalyzer.return_value = mock_analyzer

            handler = create_predict_handler("123456789")
            await handler(mock_update, mock_context)

            # Verify get_market was called with correct ID
            mock_market_repo.get_market.assert_called_once_with("market-abc123")

    @pytest.mark.asyncio
    async def test_predict_handler_market_not_found(
        self, mock_update: MagicMock
    ) -> None:
        """Test predict handler with non-existent market ID."""
        mock_context = MagicMock()
        mock_context.args = ["nonexistent"]

        with (
            patch("src.telegram_commands.handlers.MarketRepository") as MockMarketRepo,
            patch("src.telegram_commands.handlers.LLMAnalyzer"),
        ):
            mock_market_repo = MagicMock()
            mock_market_repo.get_market = AsyncMock(return_value=None)
            MockMarketRepo.return_value = mock_market_repo

            handler = create_predict_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called()
            call_args = mock_update.message.reply_text.call_args.args[0]
            assert "市场不存在" in call_args

    @pytest.mark.asyncio
    async def test_predict_handler_unauthorized(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test predict handler with unauthorized user."""
        handler = create_predict_handler("999888777")
        await handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args.args[0]
        assert "*未授权访问*" in call_args


class TestConfirmCancelHandlers:
    """Tests for confirm and cancel command handlers."""

    @pytest.fixture
    def mock_update(self) -> MagicMock:
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456789
        update.message = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock callback context."""
        return MagicMock(args=[])

    @pytest.mark.asyncio
    async def test_confirm_handler_no_pending(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test confirm handler with no pending confirmation."""
        handler = create_confirm_handler("123456789")
        await handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args.args[0]
        assert "没有待确认的交易" in call_args

    @pytest.mark.asyncio
    async def test_cancel_handler_no_pending(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test cancel handler with no pending confirmation."""
        handler = create_cancel_handler("123456789")
        await handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args.args[0]
        assert "没有待取消的交易" in call_args


class TestPredictFormatters:
    """Tests for predict message formatters."""

    def test_format_predict_market_list_with_data(self) -> None:
        """Test market list formatting with data."""
        markets = [
            Market(id="m1", title="Test Market 1", yes_price=0.65, liquidity=50000),
            Market(id="m2", title="Test Market 2", yes_price=0.45, liquidity=120000),
        ]
        message = format_predict_market_list(markets)

        assert "*选择市场分析*" in message
        assert "Test Market 1" in message
        assert "YES: 0.65" in message
        assert "$50k" in message

    def test_format_predict_market_list_no_markets(self) -> None:
        """Test market list formatting with no markets."""
        message = format_predict_market_list([])

        assert "*选择市场分析*" in message
        assert "暂无活跃市场" in message

    def test_format_analyzing_message(self) -> None:
        """Test analyzing message formatting."""
        market = Market(id="m1", title="Test Market", yes_price=0.5)
        message = format_analyzing_message(market)

        assert "*分析中...*" in message
        assert "Test Market" in message
        assert "LLM 正在分析" in message

    def test_format_trade_cancelled(self) -> None:
        """Test trade cancelled message."""
        message = format_trade_cancelled()
        assert "*交易已取消*" in message
```

### 实现注意事项

**关键点:**

1. **两阶段流程**: `/predict` 触发分析，结果符合交易条件时需 `/confirm` 或 `/cancel`
2. **会话超时**: 待确认状态 30 秒后自动过期
3. **安全考虑**: `/confirm` 只生成建议，不执行真实交易
4. **错误处理**: LLM 分析失败时返回友好错误信息
5. **市场查询**: 支持序号和 ID 两种方式查询市场

**与 /markets 命令的区别:**
- `/markets` 显示市场列表供查看
- `/predict` 显示市场列表供选择分析
- `/predict` 触发实际的 LLM 分析

**会话状态管理:**
- 使用模块级字典存储待确认状态
- 生产环境可考虑使用 Redis 等持久化存储
- 每个用户同时只能有一个待确认交易

### 前一个故事学习 [Source: 9-9-cmd-history-query.md]

**从 Story 9.9 学到的模式:**

1. **参数解析**: 支持多种参数类型 (数字、字符串)
2. **异步数据获取**: 使用 AsyncMock 模拟数据库操作
3. **错误处理**: 处理空数据、无效参数等边界情况
4. **格式化函数独立**: 格式化逻辑与业务逻辑分离

### References

- [Source: epics.md#Story 9.10] - 原始 Story 定义
- [Source: src/telegram_commands/handlers.py] - 命令处理框架
- [Source: src/telegram_commands/formatters.py] - 消息格式化模式
- [Source: src/analysis/llm_analyzer.py] - LLMAnalyzer 类
- [Source: src/storage/repositories/market_repo.py] - MarketRepository
- [Source: src/models/market.py] - Market 模型
- [Source: src/models/prediction.py] - PredictionResult 模型
- [Source: architecture.md#Logging Patterns] - 日志格式和 emoji
- [Source: project-context.md] - 项目实现规范

## Dev Agent Record

### Agent Model Used

GLM-5

### Debug Log References

None

### Completion Notes List

(To be filled during implementation)

### File List

(To be filled during implementation)
