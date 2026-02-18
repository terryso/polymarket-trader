# Story 9.8: Telegram 命令处理 - 市场查询

Status: review

## Story

As a **用户**,
I want **通过 Telegram 命令查看当前关注的市场**,
So that **我能了解系统正在分析哪些市场**.

## Acceptance Criteria

**Given** 查询命令已实现 (Story 9.5, 9.6, 9.7)
**When** 添加 `/markets` 命令
**Then** 返回当前活跃市场列表:
```
🎯 *活跃市场* (5 个)

1. *Will Trump win 2028?*
   价格: YES 0.65 | 流动性: $50k
   截止: 2028-11-07

2. *BTC > $100k by 2025?*
   价格: YES 0.45 | 流动性: $120k
   截止: 2025-12-31

3. *Fed rate cut in March?*
   价格: YES 0.72 | 流动性: $80k
   截止: 2025-03-15
```
**And** 支持参数:
- `/markets 10` - 显示前 10 个市场
- `/markets politics` - 按类别筛选
**And** 数据来自 Markets 表 (已筛选的活跃市场)

## Tasks / Subtasks

- [x] Task 1: 扩展命令处理模块 (AC: #1)
  - [x] 1.1 在 `src/telegram_commands/handlers.py` 添加 `create_markets_handler()`
  - [x] 1.2 在 `setup_command_handlers()` 中注册 `/markets` 命令
  - [x] 1.3 导入 MarketRepository

- [x] Task 2: 实现市场查询逻辑 (AC: #1, #2)
  - [x] 2.1 从 MarketRepository 获取活跃市场 (`get_active_markets()`)
  - [x] 2.2 解析命令参数获取数量限制 (默认 5 个)
  - [x] 2.3 解析命令参数获取类别筛选
  - [x] 2.4 按流动性排序返回市场

- [x] Task 3: 实现市场消息格式化 (AC: #1)
  - [x] 3.1 在 `src/telegram_commands/formatters.py` 添加 `format_markets_message()`
  - [x] 3.2 格式化市场标题 (截断过长标题)
  - [x] 3.3 格式化价格、流动性、截止日期
  - [x] 3.4 添加 emoji 增强可读性
  - [x] 3.5 处理空市场列表情况

- [x] Task 4: 实现参数解析 (AC: #2)
  - [x] 4.1 解析 `/markets` 命令后的数字参数 (数量限制)
  - [x] 4.2 解析 `/markets` 命令后的类别参数
  - [x] 4.3 默认显示 5 个市场
  - [x] 4.4 数量限制范围 (1-20 个)

- [x] Task 5: 更新帮助信息 (AC: #1)
  - [x] 5.1 在 `format_help_message()` 中确认 `/markets` 已列出
  - [x] 5.2 确保帮助信息显示正确的命令描述

- [x] Task 6: 编写测试 (AC: All)
  - [x] 6.1 在 `tests/test_telegram_commands/test_handlers.py` 添加 markets handler 测试
  - [x] 6.2 测试默认 5 个市场
  - [x] 6.3 测试自定义数量限制
  - [x] 6.4 测试类别筛选
  - [x] 6.5 测试无市场情况
  - [x] 6.6 测试未授权用户访问
  - [x] 6.7 测试 formatter 函数

- [x] Task 7: 代码质量检查 (AC: All)
  - [x] 7.1 运行 `mypy src/telegram_commands/` 无错误
  - [x] 7.2 运行 `black --check src/telegram_commands/` 通过
  - [x] 7.3 运行 `isort --check src/telegram_commands/` 通过
  - [x] 7.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: epics.md#Story 9.8]

**`/markets` 命令响应格式:**

```markdown
🎯 *活跃市场* (5 个)

1. *Will Trump win 2028?*
   价格: YES 0.65 | 流动性: $50k
   截止: 2028-11-07

2. *BTC > $100k by 2025?*
   价格: YES 0.45 | 流动性: $120k
   截止: 2025-12-31

3. *Fed rate cut in March?*
   价格: YES 0.72 | 流动性: $80k
   截止: 2025-03-15
```

**命令参数支持:**
- `/markets` - 默认显示 5 个活跃市场
- `/markets 10` - 显示前 10 个市场
- `/markets politics` - 按类别筛选

### 现有依赖 [Source: Story 9.5, 9.6, 9.7]

**命令处理框架已实现:**
- `src/telegram_commands/__init__.py` - 模块导出
- `src/telegram_commands/handlers.py` - 命令处理函数
- `src/telegram_commands/formatters.py` - 消息格式化

**已有的处理模式:**
```python
def create_stats_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    # 1. 验证授权
    # 2. 获取数据
    # 3. 格式化消息
    # 4. 发送响应
```

### 数据模型 [Source: src/models/market.py]

**Market 模型:**
```python
class Market(BaseModel):
    id: str                          # 市场唯一标识
    title: str                       # 市场标题
    description: str | None          # 市场描述
    category: MarketCategory | None  # 类别 (politics, crypto, etc.)
    yes_price: float | None          # YES 价格 (0-1)
    no_price: float | None           # NO 价格 (0-1)
    liquidity: float | None          # 流动性 (USD)
    deadline: datetime | None        # 截止日期
    resolution_status: str | None    # 结算状态
    resolution_outcome: str | None   # 结算结果
    created_at: datetime | None
    updated_at: datetime | None
```

**MarketCategory 枚举:**
```python
class MarketCategory(str, Enum):
    POLITICS = "politics"
    BUSINESS = "business"
    TECHNOLOGY = "technology"
    ECONOMICS = "economics"
    CRYPTO = "crypto"
```

### 数据访问 [Source: src/storage/repositories/market_repo.py]

**MarketRepository 方法:**
```python
async def get_active_markets(self) -> list[Market]:
    """Get all active (unresolved) markets.
    Returns markets where resolution_status IS NULL,
    ordered by deadline ascending.
    """

async def get_markets_by_category(
    self, category: MarketCategory | str
) -> list[Market]:
    """Get markets filtered by category."""
```

### 实现模板

**handlers.py 扩展:**

```python
# 在 src/telegram_commands/handlers.py 中添加

from datetime import datetime

from src.config import settings
from src.models import MarketCategory
from src.storage.repositories import MarketRepository


def create_markets_handler(
    authorized_chat_id: str | None,
) -> "Callable[[Update, CallbackContext], Awaitable[None]]":
    """Create a markets command handler.

    Args:
        authorized_chat_id: Authorized chat ID for access control

    Returns:
        Async function that handles /markets command
    """

    async def markets_handler(update: Update, context: "CallbackContext") -> None:
        """Handle /markets command."""
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
        limit = 5  # Default limit
        category: MarketCategory | None = None

        if context.args:
            for arg in context.args:
                # Try to parse as number (limit)
                try:
                    limit = int(arg)
                    # Limit range: 1-20
                    limit = max(1, min(20, limit))
                    continue
                except ValueError:
                    pass

                # Try to parse as category
                try:
                    category = MarketCategory(arg.lower())
                    continue
                except ValueError:
                    pass

        # Get repositories
        market_repo = MarketRepository()

        # Get active markets
        if category:
            markets = await market_repo.get_markets_by_category(category)
            # Filter to active only
            markets = [m for m in markets if m.resolution_status is None]
        else:
            markets = await market_repo.get_active_markets()

        # Sort by liquidity (highest first) and limit
        markets = sorted(
            markets,
            key=lambda m: m.liquidity or 0,
            reverse=True
        )[:limit]

        # Format and send message
        message = format_markets_message(markets, category)
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Markets command processed for chat_id: {chat_id}")

    return markets_handler


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
    markets_handler = create_markets_handler(authorized_chat_id)  # NEW

    # Register handlers
    application.add_handler(CommandHandler("status", status_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("help", help_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("positions", positions_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("stats", stats_handler))  # type: ignore[arg-type]
    application.add_handler(CommandHandler("markets", markets_handler))  # type: ignore[arg-type]

    logger.info("Command handlers registered: /status, /help, /positions, /stats, /markets")
```

**formatters.py 扩展:**

```python
# 在 src/telegram_commands/formatters.py 中添加

from datetime import datetime


def format_markets_message(
    markets: list["Market"],
    category: "MarketCategory | None" = None,
) -> str:
    """Format an active markets message.

    Args:
        markets: List of Market models to display
        category: Optional category filter that was applied

    Returns:
        Formatted Markdown message

    Example:
        >>> from src.models import Market, MarketCategory
        >>> markets = [Market(id="1", title="Test", yes_price=0.5, liquidity=1000)]
        >>> msg = format_markets_message(markets)
        >>> "*活跃市场*" in msg
        True
    """
    if not markets:
        category_text = f" ({category.value})" if category else ""
        return f"\U0001f3af *活跃市场*{category_text}\n\n暂无活跃市场"

    # Header
    category_text = f" ({category.value})" if category else ""
    lines = [
        f"\U0001f3af *活跃市场*{category_text} ({len(markets)} 个)",
        "",
    ]

    # Format each market
    for i, market in enumerate(markets, 1):
        # Truncate long titles (max 50 chars)
        title = market.title[:50] + "..." if len(market.title) > 50 else market.title

        # Format price
        price_str = f"YES {market.yes_price:.2f}" if market.yes_price is not None else "N/A"

        # Format liquidity (convert to K format for readability)
        if market.liquidity is not None:
            if market.liquidity >= 1000:
                liquidity_str = f"${market.liquidity / 1000:.0f}k"
            else:
                liquidity_str = f"${market.liquidity:.0f}"
        else:
            liquidity_str = "N/A"

        # Format deadline
        if market.deadline:
            deadline_str = market.deadline.strftime("%Y-%m-%d")
        else:
            deadline_str = "N/A"

        lines.extend([
            f"{i}. *{title}*",
            f"   价格: {price_str} | 流动性: {liquidity_str}",
            f"   截止: {deadline_str}",
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
    "create_markets_handler",  # NEW
    "format_status_message",
    "format_help_message",
    "format_unauthorized_message",
    "format_positions_message",
    "format_stats_message",
    "format_markets_message",  # NEW
]
```

### 项目结构

**修改的文件:**
```
src/telegram_commands/
├── __init__.py              # 添加新导出
├── handlers.py              # 添加 create_markets_handler
└── formatters.py            # 添加 format_markets_message

tests/test_telegram_commands/
└── test_handlers.py         # 添加 markets handler 测试
```

### 依赖关系

**本故事依赖:**
- Story 9.5: Telegram 命令处理 - 状态查询 (命令处理框架)
- Story 9.6: Telegram 命令处理 - 持仓查询 (命令处理模式)
- Story 9.7: Telegram 命令处理 - 统计查询 (命令处理模式)
- Story 2.4: 市场数据仓库 (MarketRepository)

**后续故事依赖本故事:**
- Story 9.9: 交易历史命令 (命令处理模式)

### 测试策略

```python
# tests/test_telegram_commands/test_handlers.py 添加

class TestMarketsHandler:
    """Tests for markets command handler."""

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
    async def test_markets_handler_default_limit(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test markets handler with default 5 limit."""
        with patch(
            "src.telegram_commands.handlers.MarketRepository"
        ) as MockMarketRepo:
            # Setup mock market repo
            mock_market_repo = MagicMock()
            mock_market_repo.get_active_markets = AsyncMock(return_value=[
                Market(
                    id=f"market-{i}",
                    title=f"Test Market {i}",
                    category=MarketCategory.POLITICS,
                    yes_price=0.5 + i * 0.05,
                    no_price=0.5 - i * 0.05,
                    liquidity=10000.0 + i * 1000,
                    deadline=datetime(2026, 12, 31),
                )
                for i in range(10)
            ])
            MockMarketRepo.return_value = mock_market_repo

            handler = create_markets_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "*活跃市场*" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_markets_handler_custom_limit(
        self, mock_update: MagicMock
    ) -> None:
        """Test markets handler with custom limit parameter."""
        mock_context = MagicMock()
        mock_context.args = ["10"]

        with patch(
            "src.telegram_commands.handlers.MarketRepository"
        ) as MockMarketRepo:
            mock_market_repo = MagicMock()
            mock_market_repo.get_active_markets = AsyncMock(return_value=[])
            MockMarketRepo.return_value = mock_market_repo

            handler = create_markets_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_markets_handler_category_filter(
        self, mock_update: MagicMock
    ) -> None:
        """Test markets handler with category filter."""
        mock_context = MagicMock()
        mock_context.args = ["politics"]

        with patch(
            "src.telegram_commands.handlers.MarketRepository"
        ) as MockMarketRepo:
            mock_market_repo = MagicMock()
            mock_market_repo.get_markets_by_category = AsyncMock(return_value=[])
            MockMarketRepo.return_value = mock_market_repo

            handler = create_markets_handler("123456789")
            await handler(mock_update, mock_context)

            mock_market_repo.get_markets_by_category.assert_called_once_with(
                MarketCategory.POLITICS
            )

    @pytest.mark.asyncio
    async def test_markets_handler_no_markets(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test markets handler with no active markets."""
        with patch(
            "src.telegram_commands.handlers.MarketRepository"
        ) as MockMarketRepo:
            mock_market_repo = MagicMock()
            mock_market_repo.get_active_markets = AsyncMock(return_value=[])
            MockMarketRepo.return_value = mock_market_repo

            handler = create_markets_handler("123456789")
            await handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "暂无活跃市场" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_markets_handler_unauthorized(
        self, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Test markets handler with unauthorized user."""
        handler = create_markets_handler("999888777")
        await handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "*未授权访问*" in call_args.args[0]


class TestMarketsFormatter:
    """Tests for markets message formatter."""

    def test_format_markets_message_with_data(self) -> None:
        """Test markets message with data."""
        markets = [
            Market(
                id="market-1",
                title="Will Trump win 2028?",
                category=MarketCategory.POLITICS,
                yes_price=0.65,
                no_price=0.35,
                liquidity=50000.0,
                deadline=datetime(2028, 11, 7),
            ),
            Market(
                id="market-2",
                title="BTC > $100k by 2025?",
                category=MarketCategory.CRYPTO,
                yes_price=0.45,
                no_price=0.55,
                liquidity=120000.0,
                deadline=datetime(2025, 12, 31),
            ),
        ]
        message = format_markets_message(markets)

        assert "*活跃市场*" in message
        assert "(2 个)" in message
        assert "Will Trump win 2028?" in message
        assert "YES 0.65" in message
        assert "$50k" in message
        assert "2028-11-07" in message
        assert "BTC > $100k by 2025?" in message

    def test_format_markets_message_no_markets(self) -> None:
        """Test markets message with no markets."""
        message = format_markets_message([])

        assert "*活跃市场*" in message
        assert "暂无活跃市场" in message

    def test_format_markets_message_with_category(self) -> None:
        """Test markets message with category filter."""
        message = format_markets_message([], category=MarketCategory.CRYPTO)

        assert "*活跃市场* (crypto)" in message

    def test_format_markets_message_truncates_long_title(self) -> None:
        """Test that long titles are truncated."""
        long_title = "A" * 100
        markets = [
            Market(
                id="market-1",
                title=long_title,
                yes_price=0.5,
                liquidity=1000.0,
            )
        ]
        message = format_markets_message(markets)

        # Should truncate to 50 chars + "..."
        assert "..." in message
        assert len([line for line in message.split("\n") if "AAAA" in line][0]) < 60

    def test_format_markets_message_liquidity_formatting(self) -> None:
        """Test liquidity formatting in K format."""
        markets = [
            Market(
                id="market-1",
                title="Test",
                yes_price=0.5,
                liquidity=1500.0,  # Should show as $2k
            ),
            Market(
                id="market-2",
                title="Test 2",
                yes_price=0.5,
                liquidity=500.0,  # Should show as $500
            ),
        ]
        message = format_markets_message(markets)

        assert "$2k" in message
        assert "$500" in message
```

### 实现注意事项

**关键点:**

1. **参数解析**: 支持数字参数 (数量限制) 和字符串参数 (类别筛选)
2. **排序**: 按流动性从高到低排序，展示最活跃的市场
3. **标题截断**: 过长的标题需要截断 (最多 50 字符)
4. **流动性格式化**: 大于 1000 的显示为 K 格式 (如 $50k)
5. **类别筛选**: 使用 MarketCategory 枚举验证类别参数
6. **空数据处理**: 需要处理没有活跃市场的情况

**与 /stats 命令的区别:**
- `/stats` 显示汇总统计数据
- `/markets` 显示具体市场列表
- `/markets` 支持类别筛选

### 前一个故事学习 [Source: 9-7-cmd-stats-query.md]

**从 Story 9.7 学到的模式:**

1. **多参数解析**: 可以同时解析数字和字符串参数
2. **数据聚合**: 可以从多个 repository 获取数据
3. **空数据处理**: 需要优雅地处理没有数据的情况
4. **格式化函数独立**: 格式化逻辑与业务逻辑分离

### References

- [Source: epics.md#Story 9.8] - 原始 Story 定义
- [Source: src/telegram_commands/handlers.py] - 命令处理框架
- [Source: src/telegram_commands/formatters.py] - 消息格式化模式
- [Source: src/storage/repositories/market_repo.py] - MarketRepository
- [Source: src/models/market.py] - Market 模型和 MarketCategory 枚举
- [Source: architecture.md#Logging Patterns] - 日志格式和 emoji

## Dev Agent Record

### Agent Model Used

GLM-5

### Debug Log References

None

### Completion Notes List

- Implemented `/markets` command handler following the pattern from Stories 9.5, 9.6, and 9.7
- Added `create_markets_handler()` function with authorization check, parameter parsing, and market data retrieval
- Added `format_markets_message()` function for Markdown message formatting with:
  - Title truncation (max 50 chars)
  - Liquidity formatting ($Xk for values >= 1000)
  - Date formatting (YYYY-MM-DD)
  - Category filter display in header
  - Empty market list handling
- Updated `setup_command_handlers()` to register the new `/markets` command
- Updated `__init__.py` to export new functions
- Added comprehensive tests (21 new test cases) covering:
  - Default limit (5 markets)
  - Custom limit parameter
  - Category filter parameter
  - Empty market list
  - Unauthorized access
  - No chat restriction
  - Limit clamping (1-20 range)
  - Invalid parameter handling
  - Resolved market filtering
  - Liquidity-based sorting
- All code quality checks passed (mypy, black, isort)
- All 61 telegram_commands tests pass

### File List

- src/telegram_commands/__init__.py
- src/telegram_commands/handlers.py
- src/telegram_commands/formatters.py
- tests/test_telegram_commands/test_handlers.py
