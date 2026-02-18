# Story 9.7: Telegram 命令处理 - 统计查询

Status: review

## Story

As a **用户**,
I want **通过 Telegram 命令查看交易统计**,
So that **我能了解胜率、盈亏等关键指标**.

## Acceptance Criteria

**Given** `/positions` 命令已实现 (Story 9.6)
**When** 添加 `/stats` 命令
**Then** 返回交易统计数据:
```
📈 *交易统计*

*总体表现*
总交易: 25
胜: 15 | 负: 10
胜率: 60%
总盈亏: +$45.20

*近期表现 (7天)*
交易: 8
胜率: 75%
盈亏: +$18.50

*LLM 预测*
总预测: 30
已验证: 20
准确率: 70%
```
**And** 数据来自 Statistics 表和 Predictions 表
**And** 支持参数 `/stats 30` 查看最近 30 天

## Tasks / Subtasks

- [x] Task 1: 扩展命令处理模块 (AC: #1)
  - [x] 1.1 在 `src/telegram_commands/handlers.py` 添加 `create_stats_handler()`
  - [x] 1.2 在 `setup_command_handlers()` 中注册 `/stats` 命令
  - [x] 1.3 导入必要的 repository (StatisticsRepository, PredictionRepository, TradeRepository)

- [x] Task 2: 实现统计查询逻辑 (AC: #1, #2)
  - [x] 2.1 从 StatisticsRepository 获取总体统计数据
  - [x] 2.2 从 TradeRepository 获取近期交易数据 (默认 7 天)
  - [x] 2.3 从 PredictionRepository 获取预测准确率数据
  - [x] 2.4 解析命令参数获取天数 (默认 7 天)

- [x] Task 3: 实现统计消息格式化 (AC: #1)
  - [x] 3.1 在 `src/telegram_commands/formatters.py` 添加 `format_stats_message()`
  - [x] 3.2 格式化总体表现 (总交易、胜率、总盈亏)
  - [x] 3.3 格式化近期表现 (交易数、胜率、盈亏)
  - [x] 3.4 格式化 LLM 预测 (总预测、已验证、准确率)
  - [x] 3.5 添加 emoji 增强可读性

- [x] Task 4: 实现参数解析 (AC: #3)
  - [x] 4.1 解析 `/stats` 命令后的数字参数
  - [x] 4.2 默认为 7 天
  - [x] 4.3 参数范围限制 (1-365 天)

- [x] Task 5: 更新帮助信息 (AC: #1)
  - [x] 5.1 在 `format_help_message()` 中确认 `/stats` 已列出
  - [x] 5.2 确保帮助信息显示正确的命令描述

- [x] Task 6: 编写测试 (AC: All)
  - [x] 6.1 在 `tests/test_telegram_commands/test_handlers.py` 添加 stats handler 测试
  - [x] 6.2 测试默认 7 天统计
  - [x] 6.3 测试自定义天数统计
  - [x] 6.4 测试无数据情况
  - [x] 6.5 测试未授权用户访问
  - [x] 6.6 测试 formatter 函数

- [x] Task 7: 代码质量检查 (AC: All)
  - [x] 7.1 运行 `mypy src/telegram_commands/` 无错误
  - [x] 7.2 运行 `black --check src/telegram_commands/` 通过
  - [x] 7.3 运行 `isort --check src/telegram_commands/` 通过
  - [x] 7.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: epics.md#Story 9.7]

**`/stats` 命令响应格式:**

```markdown
📈 *交易统计*

*总体表现*
总交易: 25
胜: 15 | 负: 10
胜率: 60%
总盈亏: +$45.20

*近期表现 (7天)*
交易: 8
胜率: 75%
盈亏: +$18.50

*LLM 预测*
总预测: 30
已验证: 20
准确率: 70%
```

**命令参数支持:**
- `/stats` - 默认 7 天
- `/stats 30` - 最近 30 天

### 现有依赖 [Source: Story 9.5, 9.6]

**命令处理框架已实现:**
- `src/telegram_commands/__init__.py` - 模块导出
- `src/telegram_commands/handlers.py` - 命令处理函数
- `src/telegram_commands/formatters.py` - 消息格式化

**已有的处理模式:**
```python
def create_positions_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    # 1. 验证授权
    # 2. 获取数据
    # 3. 格式化消息
    # 4. 发送响应
```

### 数据模型 [Source: src/models/statistics.py]

**Statistics 模型:**
```python
class Statistics(BaseModel):
    id: int
    date: datetime.date
    mode: TradeMode
    starting_capital: float
    ending_capital: float | None
    total_pnl: float | None
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float | None
    created_at: datetime.datetime | None
```

### 数据访问 [Source: src/storage/repositories/statistics_repo.py]

**StatisticsRepository 方法:**
```python
async def get_by_date_range(
    self, start: date, end: date, mode: TradeMode
) -> list[Statistics]:
    """Get statistics for a date range."""

async def get_latest(self, mode: TradeMode, limit: int = 30) -> list[Statistics]:
    """Get most recent statistics."""
```

### 数据访问 [Source: src/storage/repositories/prediction_repo.py]

**PredictionRepository 方法:**
```python
async def count(self) -> int:
    """Get total count of predictions."""

async def get_all_validated(self) -> list[Prediction]:
    """Get all validated predictions (is_correct is not None)."""

async def get_validated_by_date_range(
    self, start_date: datetime, end_date: datetime
) -> list[Prediction]:
    """Get validated predictions within a date range."""
```

### 数据访问 [Source: src/storage/repositories/trade_repo.py]

**TradeRepository 方法:**
```python
async def get_by_date_range(
    self,
    start_date: date,
    end_date: date,
    mode: TradeMode | None = None,
) -> list[Trade]:
    """Get trades within a date range."""

async def count_by_mode(self, mode: TradeMode) -> int:
    """Count trades by trading mode."""
```

### 实现模板

**handlers.py 扩展:**

```python
# 在 src/telegram_commands/handlers.py 中添加

from datetime import date, timedelta

from src.config import settings
from src.storage.repositories import (
    PredictionRepository,
    StatisticsRepository,
    TradeRepository,
)


def create_stats_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a stats command handler.

    Args:
        authorized_chat_id: Authorized chat ID for access control

    Returns:
        Async function that handles /stats command
    """

    async def stats_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /stats command."""
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

        # Parse days parameter (default 7)
        days = 7
        if context.args and len(context.args) > 0:
            try:
                days = int(context.args[0])
                # Limit to 1-365 days
                days = max(1, min(365, days))
            except ValueError:
                pass  # Keep default

        # Get repositories
        stats_repo = StatisticsRepository()
        trade_repo = TradeRepository()
        prediction_repo = PredictionRepository()

        # Determine trading mode
        mode = TradeMode.PAPER if settings.paper_trading else TradeMode.LIVE

        # Calculate date ranges
        today = date.today()
        recent_start = today - timedelta(days=days)

        # Get overall statistics (all time)
        all_stats = await stats_repo.get_latest(mode, limit=365)

        # Calculate overall totals
        total_trades = sum(s.total_trades for s in all_stats)
        total_winning = sum(s.winning_trades for s in all_stats)
        total_losing = sum(s.losing_trades for s in all_stats)
        total_pnl = sum(s.total_pnl or 0 for s in all_stats)
        overall_win_rate = (
            total_winning / total_trades * 100 if total_trades > 0 else 0.0
        )

        # Get recent statistics
        recent_stats = await stats_repo.get_by_date_range(recent_start, today, mode)

        # Calculate recent totals
        recent_trades = sum(s.total_trades for s in recent_stats)
        recent_winning = sum(s.winning_trades for s in recent_stats)
        recent_win_rate = (
            recent_winning / recent_trades * 100 if recent_trades > 0 else 0.0
        )
        recent_pnl = sum(s.total_pnl or 0 for s in recent_stats)

        # Get prediction statistics
        total_predictions = await prediction_repo.count()
        validated_predictions = await prediction_repo.get_all_validated()

        validated_count = len(validated_predictions)
        correct_count = sum(1 for p in validated_predictions if p.is_correct)
        accuracy = correct_count / validated_count * 100 if validated_count > 0 else 0.0

        # Format and send message
        message = format_stats_message(
            total_trades=total_trades,
            total_winning=total_winning,
            total_losing=total_losing,
            win_rate=overall_win_rate,
            total_pnl=total_pnl,
            recent_trades=recent_trades,
            recent_win_rate=recent_win_rate,
            recent_pnl=recent_pnl,
            days=days,
            total_predictions=total_predictions,
            validated_count=validated_count,
            accuracy=accuracy,
        )
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Stats command processed for chat_id: {chat_id}")

    return stats_handler


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
    stats_handler = create_stats_handler(authorized_chat_id)  # NEW

    # Register handlers
    application.add_handler(CommandHandler("status", status_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("help", help_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("positions", positions_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("stats", stats_handler))  # type: ignore[arg-type]

    logger.info("Command handlers registered: /status, /help, /positions, /stats")
```

**formatters.py 扩展:**

```python
# 在 src/telegram_commands/formatters.py 中添加


def format_stats_message(
    total_trades: int,
    total_winning: int,
    total_losing: int,
    win_rate: float,
    total_pnl: float,
    recent_trades: int,
    recent_win_rate: float,
    recent_pnl: float,
    days: int,
    total_predictions: int,
    validated_count: int,
    accuracy: float,
) -> str:
    """Format a trading statistics message.

    Args:
        total_trades: Total number of trades
        total_winning: Number of winning trades
        total_losing: Number of losing trades
        win_rate: Win rate percentage
        total_pnl: Total profit/loss
        recent_trades: Number of recent trades
        recent_win_rate: Recent win rate percentage
        recent_pnl: Recent profit/loss
        days: Number of days for recent period
        total_predictions: Total predictions count
        validated_count: Validated predictions count
        accuracy: Prediction accuracy percentage

    Returns:
        Formatted Markdown message

    Example:
        >>> msg = format_stats_message(
        ...     total_trades=25, total_winning=15, total_losing=10,
        ...     win_rate=60.0, total_pnl=45.20,
        ...     recent_trades=8, recent_win_rate=75.0, recent_pnl=18.50,
        ...     days=7, total_predictions=30, validated_count=20, accuracy=70.0
        ... )
        >>> "*交易统计*" in msg
        True
    """
    # Format PnL with sign
    pnl_sign = "+" if total_pnl >= 0 else ""
    recent_pnl_sign = "+" if recent_pnl >= 0 else ""

    lines = [
        "\U0001f4c8 *交易统计*",  # chart_increasing emoji
        "",
        "*总体表现*",
        f"总交易: {total_trades}",
        f"胜: {total_winning} | 负: {total_losing}",
        f"胜率: {win_rate:.0f}%",
        f"总盈亏: {pnl_sign}${total_pnl:.2f}",
        "",
        f"*近期表现 ({days}天)*",
        f"交易: {recent_trades}",
        f"胜率: {recent_win_rate:.0f}%",
        f"盈亏: {recent_pnl_sign}${recent_pnl:.2f}",
        "",
        "*LLM 预测*",
        f"总预测: {total_predictions}",
        f"已验证: {validated_count}",
        f"准确率: {accuracy:.0f}%",
    ]

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
    "create_stats_handler",  # NEW
    "format_status_message",
    "format_help_message",
    "format_unauthorized_message",
    "format_positions_message",
    "format_stats_message",  # NEW
]
```

### 项目结构

**修改的文件:**
```
src/telegram_commands/
├── __init__.py              # 添加新导出
├── handlers.py              # 添加 create_stats_handler
└── formatters.py            # 添加 format_stats_message

tests/test_telegram_commands/
└── test_handlers.py         # 添加 stats handler 测试
```

### 依赖关系

**本故事依赖:**
- Story 9.5: Telegram 命令处理 - 状态查询 (命令处理框架)
- Story 9.6: Telegram 命令处理 - 持仓查询 (命令处理模式)
- Story 5.5: 统计数据记录 (StatisticsRepository)
- Story 3.4: 预测结果存储 (PredictionRepository)
- Story 5.1: 交易记录数据模型 (TradeRepository)

**后续故事依赖本故事:**
- Story 9.8: 市场查询命令 (命令处理模式)

### 测试策略

```python
# tests/test_telegram_commands/test_handlers.py 添加

class TestStatsHandler:
    """Tests for stats command handler."""

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
    async def test_stats_handler_default_days(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test stats handler with default 7 days."""
        with patch(
            "src.telegram_commands.handlers.StatisticsRepository"
        ) as MockStatsRepo, patch(
            "src.telegram_commands.handlers.TradeRepository"
        ) as MockTradeRepo, patch(
            "src.telegram_commands.handlers.PredictionRepository"
        ) as MockPredictionRepo, patch(
            "src.telegram_commands.handlers.settings"
        ) as mock_settings:
            mock_settings.paper_trading = True

            # Setup mock statistics repo
            mock_stats_repo = MagicMock()
            mock_stats_repo.get_latest = AsyncMock(return_value=[
                Statistics(
                    id=1,
                    date=date.today(),
                    mode=TradeMode.PAPER,
                    starting_capital=200.0,
                    ending_capital=210.0,
                    total_pnl=10.0,
                    total_trades=5,
                    winning_trades=3,
                    losing_trades=2,
                    win_rate=0.6,
                )
            ])
            mock_stats_repo.get_by_date_range = AsyncMock(return_value=[
                Statistics(
                    id=1,
                    date=date.today(),
                    mode=TradeMode.PAPER,
                    starting_capital=200.0,
                    ending_capital=205.0,
                    total_pnl=5.0,
                    total_trades=2,
                    winning_trades=2,
                    losing_trades=0,
                    win_rate=1.0,
                )
            ])
            MockStatsRepo.return_value = mock_stats_repo

            # Setup mock prediction repo
            mock_pred_repo = MagicMock()
            mock_pred_repo.count = AsyncMock(return_value=10)
            mock_pred_repo.get_all_validated = AsyncMock(return_value=[])
            MockPredictionRepo.return_value = mock_pred_repo

            handler = create_stats_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "*交易统计*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_stats_handler_custom_days(
        self, mock_update: MagicMock
    ) -> None:
        """Test stats handler with custom days parameter."""
        mock_context = MagicMock()
        mock_context.args = ["30"]

        with patch(
            "src.telegram_commands.handlers.StatisticsRepository"
        ) as MockStatsRepo, patch(
            "src.telegram_commands.handlers.PredictionRepository"
        ) as MockPredictionRepo, patch(
            "src.telegram_commands.handlers.settings"
        ) as mock_settings:
            mock_settings.paper_trading = True

            mock_stats_repo = MagicMock()
            mock_stats_repo.get_latest = AsyncMock(return_value=[])
            mock_stats_repo.get_by_date_range = AsyncMock(return_value=[])
            MockStatsRepo.return_value = mock_stats_repo

            mock_pred_repo = MagicMock()
            mock_pred_repo.count = AsyncMock(return_value=0)
            mock_pred_repo.get_all_validated = AsyncMock(return_value=[])
            MockPredictionRepo.return_value = mock_pred_repo

            handler = create_stats_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            # Verify 30 days was used
            mock_stats_repo.get_by_date_range.assert_called_once()
            call_args = mock_stats_repo.get_by_date_range.call_args
            assert "30" in str(call_args)

    @pytest.mark.asyncio
    async def test_stats_handler_unauthorized(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test stats handler with unauthorized user."""
        handler = create_stats_handler("999888777")
        await handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "*未授权访问*" in call_args.args[0]


class TestStatsFormatter:
    """Tests for stats message formatter."""

    def test_format_stats_message_with_data(self) -> None:
        """Test stats message with data."""
        message = format_stats_message(
            total_trades=25,
            total_winning=15,
            total_losing=10,
            win_rate=60.0,
            total_pnl=45.20,
            recent_trades=8,
            recent_win_rate=75.0,
            recent_pnl=18.50,
            days=7,
            total_predictions=30,
            validated_count=20,
            accuracy=70.0,
        )

        assert "*交易统计*" in message
        assert "总交易: 25" in message
        assert "胜: 15 | 负: 10" in message
        assert "胜率: 60%" in message
        assert "+$45.20" in message
        assert "*近期表现 (7天)*" in message
        assert "交易: 8" in message
        assert "胜率: 75%" in message
        assert "+$18.50" in message
        assert "*LLM 预测*" in message
        assert "总预测: 30" in message
        assert "已验证: 20" in message
        assert "准确率: 70%" in message

    def test_format_stats_message_no_data(self) -> None:
        """Test stats message with no data."""
        message = format_stats_message(
            total_trades=0,
            total_winning=0,
            total_losing=0,
            win_rate=0.0,
            total_pnl=0.0,
            recent_trades=0,
            recent_win_rate=0.0,
            recent_pnl=0.0,
            days=7,
            total_predictions=0,
            validated_count=0,
            accuracy=0.0,
        )

        assert "*交易统计*" in message
        assert "总交易: 0" in message
        assert "胜率: 0%" in message

    def test_format_stats_message_negative_pnl(self) -> None:
        """Test stats message with negative PnL."""
        message = format_stats_message(
            total_trades=10,
            total_winning=3,
            total_losing=7,
            win_rate=30.0,
            total_pnl=-25.50,
            recent_trades=5,
            recent_win_rate=20.0,
            recent_pnl=-15.00,
            days=7,
            total_predictions=10,
            validated_count=5,
            accuracy=40.0,
        )

        assert "-$25.50" in message
        assert "-$15.00" in message
```

### 实现注意事项

**关键点:**

1. **参数解析**: 解析 `/stats` 命令后的数字参数，默认 7 天，限制 1-365 天
2. **多数据源**: 需要从 StatisticsRepository、TradeRepository 和 PredictionRepository 获取数据
3. **汇总计算**: 需要对多条 Statistics 记录进行汇总计算
4. **准确率计算**: 准确率 = 正确预测数 / 已验证预测数
5. **胜率计算**: 胜率 = 胜场数 / 总交易数
6. **空数据处理**: 需要处理没有统计数据的情况

**与 /positions 命令的区别:**
- `/positions` 显示当前持仓 (实时数据)
- `/stats` 显示历史统计 (汇总数据)
- `/stats` 支持时间范围参数

### 前一个故事学习 [Source: 9-6-cmd-positions-query.md]

**从 Story 9.6 学到的模式:**

1. **工厂函数创建 handler**: 通过依赖注入传入 authorized_chat_id
2. **授权验证统一**: 每个命令都需要验证 Chat ID
3. **格式化函数独立**: 格式化逻辑与业务逻辑分离
4. **参数解析**: 使用 `context.args` 获取命令参数
5. **异步数据获取**: 多个 repository 调用可以并行或顺序执行

### References

- [Source: epics.md#Story 9.7] - 原始 Story 定义
- [Source: src/telegram_commands/handlers.py] - 命令处理框架
- [Source: src/telegram_commands/formatters.py] - 消息格式化模式
- [Source: src/storage/repositories/statistics_repo.py] - StatisticsRepository
- [Source: src/storage/repositories/prediction_repo.py] - PredictionRepository
- [Source: src/storage/repositories/trade_repo.py] - TradeRepository
- [Source: src/models/statistics.py] - Statistics 模型
- [Source: architecture.md#Logging Patterns] - 日志格式和 emoji

## Dev Agent Record

### Agent Model Used

Claude GLM-5

### Debug Log References

None

### Completion Notes List

- Implemented `/stats` Telegram command handler for querying trading statistics
- Added `create_stats_handler()` in handlers.py following the established pattern from /status and /positions commands
- Added `format_stats_message()` in formatters.py for consistent message formatting
- Implemented parameter parsing for optional days argument (default 7 days, range 1-365)
- Statistics aggregated from StatisticsRepository (trading stats) and PredictionRepository (LLM prediction accuracy)
- All 38 telegram_commands tests pass
- Code quality checks (mypy, black, isort) pass

### File List

- src/telegram_commands/__init__.py (modified)
- src/telegram_commands/handlers.py (modified)
- src/telegram_commands/formatters.py (modified)
- tests/test_telegram_commands/test_handlers.py (modified)

### Change Log

- 2026-02-18: Implemented Story 9.7 - Telegram /stats command for trading statistics query
