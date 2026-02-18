# Story 9.6: Telegram 命令处理 - 持仓查询

Status: review

## Story

As a **用户**,
I want **通过 Telegram 命令查看当前持仓**,
So that **我能了解资金分配和风险敞口**.

## Acceptance Criteria

**Given** `/status` 命令已实现 (Story 9.5)
**When** 添加 `/positions` 命令
**Then** 返回当前所有未平仓位:
```
📍 *当前持仓*

1. *Will Trump win 2028?*
   方向: YES | 份额: 15.38
   成本: $10.00 | 现值: $12.50
   盈亏: +$2.50 (+25%)

2. *BTC > $100k by 2025?*
   方向: NO | 份额: 20.00
   成本: $8.00 | 现值: $7.20
   盈亏: -$0.80 (-10%)

*总风险敞口: $18.00*
*总盈亏: +$1.70*
```
**And** 无持仓时返回 "暂无持仓"
**And** 持仓数据来自 Position 实时计算

## Tasks / Subtasks

- [x] Task 1: 扩展命令处理模块 (AC: #1)
  - [x] 1.1 在 `src/telegram_commands/handlers.py` 添加 `create_positions_handler()`
  - [x] 1.2 在 `setup_command_handlers()` 中注册 `/positions` 命令
  - [x] 1.3 导入必要的 repository 和 state manager

- [x] Task 2: 实现持仓查询逻辑 (AC: #1, #3)
  - [x] 2.1 从 PositionRepository 获取所有 open 状态的持仓
  - [x] 2.2 从 MarketRepository 获取每个持仓对应的市场标题
  - [x] 2.3 计算总风险敞口 (initial_value 总和)
  - [x] 2.4 计算总盈亏 (pnl 总和)

- [x] Task 3: 实现持仓消息格式化 (AC: #1, #2)
  - [x] 3.1 在 `src/telegram_commands/formatters.py` 添加 `format_positions_message()`
  - [x] 3.2 格式化单个持仓信息 (市场标题、方向、份额、成本、现值、盈亏)
  - [x] 3.3 格式化汇总信息 (总风险敞口、总盈亏)
  - [x] 3.4 处理无持仓的情况
  - [x] 3.5 添加 emoji 增强可读性

- [x] Task 4: 更新帮助信息 (AC: #1)
  - [x] 4.1 在 `format_help_message()` 中确认 `/positions` 已列出
  - [x] 4.2 确保帮助信息显示正确的命令描述

- [x] Task 5: 编写测试 (AC: All)
  - [x] 5.1 在 `tests/test_telegram_commands/test_handlers.py` 添加 positions handler 测试
  - [x] 5.2 测试有持仓时的消息格式
  - [x] 5.3 测试无持仓时的消息格式
  - [x] 5.4 测试未授权用户访问
  - [x] 5.5 测试 formatter 函数

- [x] Task 6: 代码质量检查 (AC: All)
  - [x] 6.1 运行 `mypy src/telegram_commands/` 无错误
  - [x] 6.2 运行 `black --check src/telegram_commands/` 通过
  - [x] 6.3 运行 `isort --check src/telegram_commands/` 通过
  - [x] 6.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: epics.md#Story 9.6]

**`/positions` 命令响应格式:**

```markdown
📍 *当前持仓*

1. *Will Trump win 2028?*
   方向: YES | 份额: 15.38
   成本: $10.00 | 现值: $12.50
   盈亏: +$2.50 (+25%)

2. *BTC > $100k by 2025?*
   方向: NO | 份额: 20.00
   成本: $8.00 | 现值: $7.20
   盈亏: -$0.80 (-10%)

*总风险敞口: $18.00*
*总盈亏: +$1.70*
```

**无持仓时:**

```markdown
📍 *当前持仓*

暂无持仓
```

### 现有依赖 [Source: Story 9.5]

**命令处理框架已实现:**
- `src/telegram_commands/__init__.py` - 模块导出
- `src/telegram_commands/handlers.py` - 命令处理函数
- `src/telegram_commands/formatters.py` - 消息格式化

**已有的处理模式:**
```python
def create_status_handler(
    state_manager: "ThreadSafeState",
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    # 1. 验证授权
    # 2. 获取数据
    # 3. 格式化消息
    # 4. 发送响应
```

### 数据模型 [Source: src/models/position.py]

**Position 模型:**
```python
class Position(BaseModel):
    id: int
    market_id: str              # 市场引用
    outcome: PositionOutcome    # YES/NO
    shares: float               # 持有份额
    avg_price: float            # 平均成本价 (0-1)
    initial_value: float | None # 初始价值 (USD)
    current_value: float | None # 当前价值 (USD)
    pnl: float | None           # 盈亏 (USD)
    status: PositionStatus      # OPEN/CLOSED
    opened_at: datetime | None
    closed_at: datetime | None
```

**PositionOutcome 枚举:**
```python
class PositionOutcome(str, Enum):
    YES = "YES"
    NO = "NO"
```

### 数据访问 [Source: src/storage/repositories/position_repo.py]

**PositionRepository 方法:**
```python
async def get_open_positions(self) -> list[Position]:
    """Get all open positions.

    Returns:
        List of open positions ordered by opened_at descending
    """
```

### 市场数据访问 [Source: src/storage/repositories/market_repo.py]

**MarketRepository 方法:**
```python
async def get_market(self, market_id: str) -> Market | None:
    """Get a single market by ID."""
```

**Market 模型包含:**
- `id`: 市场 ID
- `title`: 市场标题 (用于显示)

### 实现模板

**handlers.py 扩展:**

```python
# 在 src/telegram_commands/handlers.py 中添加

from src.storage.repositories import MarketRepository, PositionRepository

def create_positions_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a positions command handler.

    Args:
        authorized_chat_id: Authorized chat ID for access control

    Returns:
        Async function that handles /positions command
    """

    async def positions_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /positions command."""
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

        # Get open positions
        position_repo = PositionRepository()
        market_repo = MarketRepository()

        positions = await position_repo.get_open_positions()

        if not positions:
            await update.message.reply_text(
                format_positions_message([], [], 0.0, 0.0),
                parse_mode="Markdown",
            )
            return

        # Enrich positions with market data
        position_data = []
        total_exposure = 0.0
        total_pnl = 0.0

        for position in positions:
            market = await market_repo.get_market(position.market_id)
            market_title = market.title if market else position.market_id

            initial_value = position.initial_value or 0.0
            current_value = position.current_value or 0.0
            pnl = position.pnl or 0.0

            total_exposure += initial_value
            total_pnl += pnl

            position_data.append({
                "market_title": market_title,
                "outcome": position.outcome.value,
                "shares": position.shares,
                "cost": initial_value,
                "current_value": current_value,
                "pnl": pnl,
            })

        # Format and send message
        message = format_positions_message(
            position_data, positions, total_exposure, total_pnl
        )
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Positions command processed for chat_id: {chat_id}")

    return positions_handler


def setup_command_handlers(
    application: Application,
    state_manager: "ThreadSafeState",
    authorized_chat_id: str | None = None,
) -> None:
    """Setup all command handlers for the Telegram bot."""
    # Create handlers with injected dependencies
    status_handler = create_status_handler(state_manager, authorized_chat_id)
    help_handler = create_help_handler(authorized_chat_id)
    positions_handler = create_positions_handler(authorized_chat_id)  # NEW

    # Register handlers
    application.add_handler(CommandHandler("status", status_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("help", help_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("positions", positions_handler))  # type: ignore[arg-type]

    logger.info("Command handlers registered: /status, /help, /positions")
```

**formatters.py 扩展:**

```python
# 在 src/telegram_commands/formatters.py 中添加

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.position import Position


def format_positions_message(
    position_data: list[dict],
    positions: "list[Position]",
    total_exposure: float,
    total_pnl: float,
) -> str:
    """Format a positions message.

    Args:
        position_data: List of dicts with market_title, outcome, shares, etc.
        positions: List of Position models (unused but for type reference)
        total_exposure: Total initial value of all positions
        total_pnl: Total PnL of all positions

    Returns:
        Formatted Markdown message

    Example:
        >>> msg = format_positions_message(
        ...     [{"market_title": "Test", "outcome": "YES", ...}],
        ...     [],
        ...     100.0,
        ...     10.0
        ... )
        >>> "*当前持仓*" in msg
        True
    """
    if not position_data:
        return "\U0001f4cd *当前持仓*\n\n暂无持仓"

    lines = ["\U0001f4cd *当前持仓*"]

    for i, pos in enumerate(position_data, 1):
        # Format PnL with sign
        pnl = pos["pnl"]
        pnl_sign = "+" if pnl >= 0 else ""
        pnl_pct = (pnl / pos["cost"] * 100) if pos["cost"] > 0 else 0.0

        lines.extend([
            "",
            f"{i}. *{pos['market_title']}*",
            f"   方向: {pos['outcome']} | 份额: {pos['shares']:.2f}",
            f"   成本: ${pos['cost']:.2f} | 现值: ${pos['current_value']:.2f}",
            f"   盈亏: {pnl_sign}${pnl:.2f} ({pnl_sign}{pnl_pct:.0f}%)",
        ])

    # Format totals
    total_pnl_sign = "+" if total_pnl >= 0 else ""
    lines.extend([
        "",
        f"*总风险敞口: ${total_exposure:.2f}*",
        f"*总盈亏: {total_pnl_sign}${total_pnl:.2f}*",
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
    "create_positions_handler",  # NEW
    "format_status_message",
    "format_help_message",
    "format_unauthorized_message",
    "format_positions_message",  # NEW
]
```

### 项目结构

**修改的文件:**
```
src/telegram_commands/
├── __init__.py              # 添加新导出
├── handlers.py              # 添加 create_positions_handler
└── formatters.py            # 添加 format_positions_message

tests/test_telegram_commands/
└── test_handlers.py         # 添加 positions handler 测试
```

### 依赖关系

**本故事依赖:**
- Story 9.5: Telegram 命令处理 - 状态查询 (命令处理框架)
- Story 4.5: 持仓管理 (PositionRepository)
- Story 2.4: 市场数据仓库 (MarketRepository)

**后续故事依赖本故事:**
- Story 9.7: 统计查询命令 (命令处理模式)

### 测试策略

```python
# tests/test_telegram_commands/test_handlers.py 添加

class TestPositionsHandler:
    """Tests for positions command handler."""

    @pytest.fixture
    def mock_update(self) -> MagicMock:
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456789
        update.message = AsyncMock()
        return update

    @pytest.mark.asyncio
    async def test_positions_handler_with_positions(
        self, mock_update: MagicMock
    ) -> None:
        """Test positions handler with open positions."""
        with patch(
            "src.telegram_commands.handlers.PositionRepository"
        ) as MockPositionRepo, patch(
            "src.telegram_commands.handlers.MarketRepository"
        ) as MockMarketRepo:
            # Setup mocks
            mock_position_repo = MagicMock()
            mock_position_repo.get_open_positions = AsyncMock(return_value=[
                Position(
                    id=1,
                    market_id="market-1",
                    outcome=PositionOutcome.YES,
                    shares=15.38,
                    avg_price=0.65,
                    initial_value=10.0,
                    current_value=12.5,
                    pnl=2.5,
                    status=PositionStatus.OPEN,
                )
            ])
            MockPositionRepo.return_value = mock_position_repo

            mock_market_repo = MagicMock()
            mock_market_repo.get_market = AsyncMock(return_value=Market(
                id="market-1",
                title="Will Trump win 2028?",
            ))
            MockMarketRepo.return_value = mock_market_repo

            handler = create_positions_handler("123456789")
            await handler(mock_update, MagicMock())

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "*当前持仓*" in call_args.args[0]
            assert "Will Trump win 2028?" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_positions_handler_empty(
        self, mock_update: MagicMock
    ) -> None:
        """Test positions handler with no positions."""
        with patch(
            "src.telegram_commands.handlers.PositionRepository"
        ) as MockPositionRepo:
            mock_position_repo = MagicMock()
            mock_position_repo.get_open_positions = AsyncMock(return_value=[])
            MockPositionRepo.return_value = mock_position_repo

            handler = create_positions_handler("123456789")
            await handler(mock_update, MagicMock())

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "暂无持仓" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_positions_handler_unauthorized(
        self, mock_update: MagicMock
    ) -> None:
        """Test positions handler with unauthorized user."""
        handler = create_positions_handler("999888777")
        await handler(mock_update, MagicMock())

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "*未授权访问*" in call_args.args[0]


class TestPositionsFormatter:
    """Tests for positions message formatter."""

    def test_format_positions_message_empty(self) -> None:
        """Test positions message with no positions."""
        message = format_positions_message([], [], 0.0, 0.0)
        assert "*当前持仓*" in message
        assert "暂无持仓" in message

    def test_format_positions_message_with_data(self) -> None:
        """Test positions message with positions."""
        position_data = [
            {
                "market_title": "Test Market",
                "outcome": "YES",
                "shares": 100.0,
                "cost": 50.0,
                "current_value": 60.0,
                "pnl": 10.0,
            }
        ]
        message = format_positions_message(
            position_data, [], 50.0, 10.0
        )
        assert "*当前持仓*" in message
        assert "Test Market" in message
        assert "YES" in message
        assert "+$10.00" in message
        assert "*总风险敞口: $50.00*" in message
        assert "*总盈亏: +$10.00*" in message
```

### 实现注意事项

**关键点:**

1. **异步数据获取**: 持仓和市场数据都是异步获取，需要在 handler 中使用 await
2. **市场标题缓存**: 可以考虑后续优化，但 MVP 阶段直接查询即可
3. **盈亏百分比计算**: 使用 initial_value 作为分母计算百分比
4. **消息长度**: Telegram 消息限制 4096 字符，大量持仓时需注意
5. **错误处理**: 单个市场查询失败不应影响整体显示

**性能考虑:**
- 当前实现对每个持仓都查询一次市场，N 个持仓 = N 次查询
- 后续可优化为批量查询或 JOIN 查询

### 前一个故事学习 [Source: 9-5-cmd-status-query.md]

**从 Story 9.5 学到的模式:**

1. **工厂函数创建 handler**: 通过依赖注入传入 state_manager 和 authorized_chat_id
2. **授权验证统一**: 每个命令都需要验证 Chat ID
3. **格式化函数独立**: 格式化逻辑与业务逻辑分离
4. **Markdown 格式**: 使用 emoji 和加粗增强可读性
5. **日志记录**: 记录命令处理结果

### References

- [Source: epics.md#Story 9.6] - 原始 Story 定义
- [Source: src/telegram_commands/handlers.py] - 命令处理框架
- [Source: src/telegram_commands/formatters.py] - 消息格式化模式
- [Source: src/storage/repositories/position_repo.py] - PositionRepository
- [Source: src/storage/repositories/market_repo.py] - MarketRepository
- [Source: src/models/position.py] - Position 模型
- [Source: architecture.md#Logging Patterns] - 日志格式和 emoji

## Dev Agent Record

### Agent Model Used

GLM-5 (via Claude Code Agent)

### Debug Log References

None

### Completion Notes List

- Successfully implemented `/positions` command handler for Telegram bot
- Added `create_positions_handler()` factory function with authorization check
- Added `format_positions_message()` formatter function with support for empty positions and multiple positions
- Formatter includes emoji for visual enhancement and proper PnL formatting with sign
- Added comprehensive tests covering: positions with data, empty positions, unauthorized access, no restriction, no effective_chat, market not found
- All 26 telegram_commands tests pass
- Code quality checks pass: mypy (no issues), black (formatted), isort (no issues)
- Help message already included `/positions` command

### File List

- src/telegram_commands/__init__.py
- src/telegram_commands/handlers.py
- src/telegram_commands/formatters.py
- tests/test_telegram_commands/test_handlers.py

### Change Log

- 2026-02-18: Implemented Story 9.6 - Telegram /positions command
