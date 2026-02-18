# Story 9.9: Telegram 命令处理 - 交易历史

Status: ready-for-dev

## Story

As a **用户**,
I want **通过 Telegram 命令查看最近交易历史**,
So that **我能回顾近期的交易活动**.

## Acceptance Criteria

**Given** `/markets` 命令已实现 (Story 9.8)
**When** 添加 `/history` 命令
**Then** 返回最近交易记录:
```
📜 *最近交易* (10 笔)

1. *BUY YES* Will Trump win?
   $10.00 @ 0.65 | 2小时前
   状态: ✅ 持仓中

2. *SELL NO* BTC > $100k?
   $8.00 @ 0.55 | 5小时前
   状态: ✅ 已平仓 +$1.20

3. *BUY YES* Fed rate cut?
   $5.00 @ 0.72 | 1天前
   状态: ❌ 已取消
```
**And** 支持参数:
- `/history 20` - 显示最近 20 笔
- `/history paper` - 只看 Paper Trading
- `/history live` - 只看 Live Trading
**And** 数据来自 Trades 表

## Tasks / Subtasks

- [ ] Task 1: 扩展命令处理模块 (AC: #1)
  - [ ] 1.1 在 `src/telegram_commands/handlers.py` 添加 `create_history_handler()`
  - [ ] 1.2 在 `setup_command_handlers()` 中注册 `/history` 命令
  - [ ] 1.3 导入 TradeRepository

- [ ] Task 2: 实现交易历史查询逻辑 (AC: #1, #2)
  - [ ] 2.1 从 TradeRepository 获取交易记录 (`get_recent_trades()`)
  - [ ] 2.2 解析命令参数获取数量限制 (默认 10 笔)
  - [ ] 2.3 解析命令参数获取模式筛选 (paper/live)
  - [ ] 2.4 按时间倒序返回交易

- [ ] Task 3: 实现交易历史消息格式化 (AC: #1)
  - [ ] 3.1 在 `src/telegram_commands/formatters.py` 添加 `format_history_message()`
  - [ ] 3.2 格式化交易类型 (BUY YES/BUY NO/SELL)
  - [ ] 3.3 格式化金额、价格、时间 (相对时间)
  - [ ] 3.4 格式化状态 (持仓中/已平仓/已取消)
  - [ ] 3.5 添加 emoji 增强可读性
  - [ ] 3.6 处理空交易列表情况

- [ ] Task 4: 实现参数解析 (AC: #2)
  - [ ] 4.1 解析 `/history` 命令后的数字参数 (数量限制)
  - [ ] 4.2 解析 `/history` 命令后的模式参数 (paper/live)
  - [ ] 4.3 默认显示 10 笔交易
  - [ ] 4.4 数量限制范围 (1-50 笔)

- [ ] Task 5: 更新帮助信息 (AC: #1)
  - [ ] 5.1 在 `format_help_message()` 中添加 `/history` 命令描述
  - [ ] 5.2 确保帮助信息显示正确的命令参数说明

- [ ] Task 6: 编写测试 (AC: All)
  - [ ] 6.1 在 `tests/test_telegram_commands/test_handlers.py` 添加 history handler 测试
  - [ ] 6.2 测试默认 10 笔交易
  - [ ] 6.3 测试自定义数量限制
  - [ ] 6.4 测试模式筛选 (paper/live)
  - [ ] 6.5 测试无交易情况
  - [ ] 6.6 测试未授权用户访问
  - [ ] 6.7 测试 formatter 函数

- [ ] Task 7: 代码质量检查 (AC: All)
  - [ ] 7.1 运行 `mypy src/telegram_commands/` 无错误
  - [ ] 7.2 运行 `black --check src/telegram_commands/` 通过
  - [ ] 7.3 运行 `isort --check src/telegram_commands/` 通过
  - [ ] 7.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: epics.md#Story 9.9]

**`/history` 命令响应格式:**

```markdown
📜 *最近交易* (10 笔)

1. *BUY YES* Will Trump win?
   $10.00 @ 0.65 | 2小时前
   状态: ✅ 持仓中

2. *SELL NO* BTC > $100k?
   $8.00 @ 0.55 | 5小时前
   状态: ✅ 已平仓 +$1.20

3. *BUY YES* Fed rate cut?
   $5.00 @ 0.72 | 1天前
   状态: ❌ 已取消
```

**命令参数支持:**
- `/history` - 默认显示最近 10 笔交易
- `/history 20` - 显示最近 20 笔
- `/history paper` - 只看 Paper Trading
- `/history live` - 只看 Live Trading

### 现有依赖 [Source: Story 9.5, 9.6, 9.7, 9.8]

**命令处理框架已实现:**
- `src/telegram_commands/__init__.py` - 模块导出
- `src/telegram_commands/handlers.py` - 命令处理函数
- `src/telegram_commands/formatters.py` - 消息格式化

**已有的处理模式:**
```python
def create_markets_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    # 1. 验证授权
    # 2. 解析参数
    # 3. 获取数据
    # 4. 格式化消息
    # 5. 发送响应
```

### 数据模型 [Source: src/models/trade.py]

**Trade 模型:**
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
    id: int | None
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

### 数据访问 [Source: src/storage/repositories/trade_repo.py]

**TradeRepository 方法:**
```python
async def get_recent_trades(
    self,
    limit: int = 10,
    mode: TradeMode | None = None,
) -> list[Trade]:
    """Get recent trades, optionally filtered by mode.

    Args:
        limit: Maximum number of trades to return
        mode: Optional filter by trade mode (PAPER/LIVE)

    Returns:
        List of recent trades ordered by created_at descending
    """
```

### 实现模板

**handlers.py 扩展:**

```python
# 在 src/telegram_commands/handlers.py 中添加

from datetime import datetime, timedelta

from src.config import settings
from src.models import TradeMode
from src.storage.repositories import TradeRepository


def create_history_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a history command handler.

    Args:
        authorized_chat_id: Authorized chat ID for access control

    Returns:
        Async function that handles /history command
    """

    async def history_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /history command."""
        if not update.effective_chat or not update.message:
            return

        chat_id = update.effective_chat.id

        # Verify authorization
        if authorized_chat_id and str(chat_id) != str(authorized_chat_id):
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text(
                format_unauthorized_message(),
                parse_mode="Markdown",
            )
            return

        # Parse parameters
        limit = 10  # Default limit
        mode: TradeMode | None = None

        if context.args:
            for arg in context.args:
                # Try to parse as number (limit)
                try:
                    limit = int(arg)
                    # Limit range: 1-50
                    limit = max(1, min(50, limit))
                    continue
                except ValueError:
                    pass

                # Try to parse as mode
                if arg.lower() == "paper":
                    mode = TradeMode.PAPER
                elif arg.lower() == "live":
                    mode = TradeMode.LIVE

        # Get repositories
        trade_repo = TradeRepository()

        # Get recent trades
        trades = await trade_repo.get_recent_trades(limit=limit, mode=mode)

        # Format and send message
        message = format_history_message(trades, mode)
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"History command processed for chat_id: {chat_id}")

    return history_handler


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
    history_handler = create_history_handler(authorized_chat_id)  # NEW

    # Register handlers
    application.add_handler(CommandHandler("status", status_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("help", help_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("positions", positions_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("stats", stats_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("markets", markets_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("history", history_handler))  # type: ignore[arg-type]

    logger.info("Command handlers registered: /status, /help, /positions, /stats, /markets, /history")
```

**formatters.py 扩展:**

```python
# 在 src/telegram_commands/formatters.py 中添加

from datetime import datetime, timedelta


def _format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time string.

    Args:
        dt: Datetime to format

    Returns:
        Human-readable relative time string (e.g., "2小时前", "1天前")
    """
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    diff = now - dt

    if diff < timedelta(minutes=1):
        return "刚刚"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes}分钟前"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours}小时前"
    elif diff < timedelta(days=30):
        days = diff.days
        return f"{days}天前"
    else:
        return dt.strftime("%Y-%m-%d")


def format_history_message(
    trades: list["Trade"],
    mode: "TradeMode | None" = None,
) -> str:
    """Format a trade history message.

    Args:
        trades: List of Trade models to display
        mode: Optional mode filter that was applied

    Returns:
        Formatted Markdown message

    Example:
        >>> from src.models import Trade, TradeType, TradeMode, TradeStatus
        >>> from datetime import datetime
        >>> trades = [Trade(
        ...     id=1,
        ...     market_id="m1",
        ...     trade_type=TradeType.BUY_YES,
        ...     mode=TradeMode.PAPER,
        ...     amount=10.0,
        ...     price=0.65,
        ...     status=TradeStatus.FILLED,
        ...     created_at=datetime.now()
        ... )]
        >>> msg = format_history_message(trades)
        >>> "*最近交易*" in msg
        True
    """
    if not trades:
        mode_text = f" ({mode.value})" if mode else ""
        return f"\U0001f4dc *最近交易*{mode_text}\n\n暂无交易记录"

    # Header
    mode_text = f" ({mode.value})" if mode else ""
    lines = [
        f"\U0001f4dc *最近交易*{mode_text} ({len(trades)} 笔)",
        "",
    ]

    # Format each trade
    for i, trade in enumerate(trades, 1):
        # Trade type emoji and text
        if trade.trade_type.value == "BUY_YES":
            type_emoji = "\U0001f7e2"  # Green circle for YES
            type_text = "BUY YES"
        elif trade.trade_type.value == "BUY_NO":
            type_emoji = "\U0001f534"  # Red circle for NO
            type_text = "BUY NO"
        else:  # SELL
            type_emoji = "\U0001f4b8"  # Money with wings
            type_text = "SELL"

        # Format status
        if trade.status.value == "FILLED":
            # Check if position is still open or closed
            # This would need additional logic to determine
            status_text = "\U00002705 持仓中"  # Check mark - in position
            status_emoji = "\U00002705"
        elif trade.status.value == "CANCELLED":
            status_text = "\U0000274c 已取消"  # X mark
            status_emoji = "\U0000274c"
        else:
            status_text = "\U000023f3 处理中"  # Hourglass
            status_emoji = "\U000023f3"

        # Format amount and price
        amount_str = f"${trade.amount:.2f}"
        price_str = f"{trade.price:.2f}"

        # Format time
        time_str = ""
        if trade.created_at:
            time_str = _format_relative_time(trade.created_at)

        # Market title placeholder (would need to join with Market)
        market_title = f"Market {trade.market_id[:20]}..."

        lines.extend([
            f"{i}. {type_emoji} *{type_text}* {market_title}",
            f"   {amount_str} @ {price_str} | {time_str}",
            f"   状态: {status_text}",
            "",
        ])

    return "\n".join(lines)
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
    "create_history_handler",  # NEW
    "format_status_message",
    "format_help_message",
    "format_unauthorized_message",
    "format_positions_message",
    "format_stats_message",
    "format_markets_message",
    "format_history_message",  # NEW
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
/history [n] [paper|live] - 查看交易历史  # NEW
/help - 显示帮助信息
"""
```

### 项目结构

**修改的文件:**
```
src/telegram_commands/
├── __init__.py              # 添加新导出
├── handlers.py              # 添加 create_history_handler
└── formatters.py            # 添加 format_history_message, _format_relative_time

tests/test_telegram_commands/
└── test_handlers.py         # 添加 history handler 测试
```

### 依赖关系

**本故事依赖:**
- Story 9.5: Telegram 命令处理 - 状态查询 (命令处理框架)
- Story 9.6: Telegram 命令处理 - 持仓查询 (命令处理模式)
- Story 9.7: Telegram 命令处理 - 统计查询 (命令处理模式)
- Story 9.8: Telegram 命令处理 - 市场查询 (命令处理模式)
- Story 5.1: 交易记录数据模型 (TradeRepository, Trade 模型)

**后续故事依赖本故事:**
- Story 9.10: 手动分析触发 (命令处理模式)

### 测试策略

```python
# tests/test_telegram_commands/test_handlers.py 添加

class TestHistoryHandler:
    """Tests for history command handler."""

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
    async def test_history_handler_default_limit(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test history handler with default 10 limit."""
        with patch(
            "src.telegram_commands.handlers.TradeRepository"
        ) as MockTradeRepo:
            # Setup mock trade repo
            mock_trade_repo = MagicMock()
            mock_trade_repo.get_recent_trades = AsyncMock(return_value=[
                Trade(
                    id=i,
                    market_id=f"market-{i}",
                    trade_type=TradeType.BUY_YES,
                    mode=TradeMode.PAPER,
                    amount=10.0 + i,
                    price=0.5 + i * 0.05,
                    shares=10.0,
                    status=TradeStatus.FILLED,
                    created_at=datetime.now() - timedelta(hours=i),
                )
                for i in range(10)
            ])
            MockTradeRepo.return_value = mock_trade_repo

            handler = create_history_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "*最近交易*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_history_handler_custom_limit(
        self, mock_update: MagicMock
    ) -> None:
        """Test history handler with custom limit parameter."""
        mock_context = MagicMock()
        mock_context.args = ["20"]

        with patch(
            "src.telegram_commands.handlers.TradeRepository"
        ) as MockTradeRepo:
            mock_trade_repo = MagicMock()
            mock_trade_repo.get_recent_trades = AsyncMock(return_value=[])
            MockTradeRepo.return_value = mock_trade_repo

            handler = create_history_handler("123456789")
            await handler(mock_update, mock_context)

            # Verify limit parameter was passed
            mock_trade_repo.get_recent_trades.assert_called_once()
            call_kwargs = mock_trade_repo.get_recent_trades.call_args.kwargs
            assert call_kwargs["limit"] == 20

    @pytest.mark.asyncio
    async def test_history_handler_mode_filter(
        self, mock_update: MagicMock
    ) -> None:
        """Test history handler with mode filter."""
        mock_context = MagicMock()
        mock_context.args = ["paper"]

        with patch(
            "src.telegram_commands.handlers.TradeRepository"
        ) as MockTradeRepo:
            mock_trade_repo = MagicMock()
            mock_trade_repo.get_recent_trades = AsyncMock(return_value=[])
            MockTradeRepo.return_value = mock_trade_repo

            handler = create_history_handler("123456789")
            await handler(mock_update, mock_context)

            # Verify mode parameter was passed
            mock_trade_repo.get_recent_trades.assert_called_once()
            call_kwargs = mock_trade_repo.get_recent_trades.call_args.kwargs
            assert call_kwargs["mode"] == TradeMode.PAPER

    @pytest.mark.asyncio
    async def test_history_handler_no_trades(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test history handler with no trades."""
        with patch(
            "src.telegram_commands.handlers.TradeRepository"
        ) as MockTradeRepo:
            mock_trade_repo = MagicMock()
            mock_trade_repo.get_recent_trades = AsyncMock(return_value=[])
            MockTradeRepo.return_value = mock_trade_repo

            handler = create_history_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "暂无交易记录" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_history_handler_unauthorized(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test history handler with unauthorized user."""
        handler = create_history_handler("999888777")
        await handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "*未授权访问*" in call_args.args[0]


class TestHistoryFormatter:
    """Tests for history message formatter."""

    def test_format_history_message_with_data(self) -> None:
        """Test history message with data."""
        trades = [
            Trade(
                id=1,
                market_id="market-1",
                trade_type=TradeType.BUY_YES,
                mode=TradeMode.PAPER,
                amount=10.0,
                price=0.65,
                shares=15.38,
                status=TradeStatus.FILLED,
                created_at=datetime.now() - timedelta(hours=2),
            ),
            Trade(
                id=2,
                market_id="market-2",
                trade_type=TradeType.SELL,
                mode=TradeMode.PAPER,
                amount=8.0,
                price=0.55,
                shares=14.55,
                status=TradeStatus.FILLED,
                created_at=datetime.now() - timedelta(hours=5),
            ),
        ]
        message = format_history_message(trades)

        assert "*最近交易*" in message
        assert "(2 笔)" in message
        assert "BUY YES" in message
        assert "$10.00" in message
        assert "0.65" in message

    def test_format_history_message_no_trades(self) -> None:
        """Test history message with no trades."""
        message = format_history_message([])

        assert "*最近交易*" in message
        assert "暂无交易记录" in message

    def test_format_history_message_with_mode(self) -> None:
        """Test history message with mode filter."""
        message = format_history_message([], mode=TradeMode.PAPER)

        assert "*最近交易* (paper)" in message

    def test_format_relative_time(self) -> None:
        """Test relative time formatting."""
        # Just now
        assert _format_relative_time(datetime.now()) == "刚刚"

        # Minutes ago
        assert "分钟前" in _format_relative_time(
            datetime.now() - timedelta(minutes=30)
        )

        # Hours ago
        assert "小时前" in _format_relative_time(
            datetime.now() - timedelta(hours=5)
        )

        # Days ago
        assert "天前" in _format_relative_time(
            datetime.now() - timedelta(days=2)
        )
```

### 实现注意事项

**关键点:**

1. **参数解析**: 支持数字参数 (数量限制) 和字符串参数 (模式筛选 paper/live)
2. **时间格式化**: 使用相对时间 (如 "2小时前") 而非绝对时间
3. **交易类型显示**: BUY YES 用绿色圆圈, BUY NO 用红色圆圈, SELL 用钱币
4. **状态显示**: 持仓中/已平仓/已取消
5. **空数据处理**: 需要处理没有交易记录的情况
6. **数量限制**: 范围 1-50 笔，默认 10 笔

**与 /stats 命令的区别:**
- `/stats` 显示汇总统计数据
- `/history` 显示具体交易列表
- `/history` 支持模式筛选

### 前一个故事学习 [Source: 9-8-cmd-markets-query.md]

**从 Story 9.8 学到的模式:**

1. **参数解析**: 可以同时解析数字和字符串参数
2. **空数据处理**: 需要优雅地处理没有数据的情况
3. **格式化函数独立**: 格式化逻辑与业务逻辑分离
4. **参数验证**: 对参数范围进行限制 (如数量限制)

### References

- [Source: epics.md#Story 9.9] - 原始 Story 定义
- [Source: src/telegram_commands/handlers.py] - 命令处理框架
- [Source: src/telegram_commands/formatters.py] - 消息格式化模式
- [Source: src/storage/repositories/trade_repo.py] - TradeRepository
- [Source: src/models/trade.py] - Trade 模型和 TradeType/TradeMode/TradeStatus 枚举
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
