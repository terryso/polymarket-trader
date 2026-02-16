# Story 6.3: 学习日志生成

Status: ready-for-dev

## Story

As a **用户**,
I want **系统在每笔交易后自动生成详细分析报告**,
So that **我可以回顾和改进策略**.

## Acceptance Criteria

**Given** 交易执行和预测追踪已实现 (Story 5.3, Story 6.1, Story 6.2)
**When** 实现 `src/trading/learning_log.py`
**Then** 创建 `LearningLogGenerator` 类:
- `generate_trade_report(trade, prediction, market)` - 生成单笔交易报告
- `generate_daily_report(date)` - 生成每日报告

**And** 单笔报告包含:
- 市场信息 (标题、描述、截止日期)
- 市场价格 vs LLM 预测
- 置信度、Edge、分析理由
- 交易决策 (买入方向、金额、价格)
- 持仓状态

**And** 每日报告包含:
- 当日交易汇总
- PnL 统计
- 胜率统计
- 关键学习点

**And** 报告存储为 JSON 到 `logs/reports/` 目录
**And** 报告文件命名: `trade_{id}_{timestamp}.json`, `daily_{date}.json`

## Tasks / Subtasks

- [ ] Task 1: 定义学习日志数据模型 (AC: 1, 2, 3)
  - [ ] 1.1 创建 `TradeReport` 数据类 (单笔交易报告)
  - [ ] 1.2 创建 `DailyReport` 数据类 (每日报告)
  - [ ] 1.3 创建 `MarketInfo` 数据类 (市场信息摘要)
  - [ ] 1.4 创建 `TradingSummary` 数据类 (交易汇总)
  - [ ] 1.5 创建 `LearningInsight` 数据类 (学习洞察)
  - [ ] 1.6 更新 `__all__` 导出

- [ ] Task 2: 实现 LearningLogGenerator 类 (AC: 1)
  - [ ] 2.1 创建 `src/trading/learning_log.py` 文件
  - [ ] 2.2 实现 `__init__` 方法 (依赖注入)
  - [ ] 2.3 创建 `logs/reports/` 目录初始化逻辑
  - [ ] 2.4 实现文件存储辅助方法

- [ ] Task 3: 实现单笔交易报告生成 (AC: 1, 2)
  - [ ] 3.1 实现 `generate_trade_report(trade, prediction, market)` 方法
  - [ ] 3.2 提取市场信息 (标题、描述、截止日期)
  - [ ] 3.3 计算价格差距 (市场价格 vs LLM 预测)
  - [ ] 3.4 整理置信度、Edge、分析理由
  - [ ] 3.5 记录交易决策 (买入方向、金额、价格)
  - [ ] 3.6 获取当前持仓状态
  - [ ] 3.7 生成 JSON 格式报告
  - [ ] 3.8 存储到 `logs/reports/trade_{id}_{timestamp}.json`

- [ ] Task 4: 实现每日报告生成 (AC: 1, 3)
  - [ ] 4.1 实现 `generate_daily_report(date)` 方法
  - [ ] 4.2 获取当日所有交易记录
  - [ ] 4.3 计算 PnL 统计 (总盈亏、胜率)
  - [ ] 4.4 统计交易数量、胜率
  - [ ] 4.5 生成关键学习点 (基于交易结果)
  - [ ] 4.6 生成 JSON 格式报告
  - [ ] 4.7 存储到 `logs/reports/daily_{date}.json`

- [ ] Task 5: 实现报告存储机制 (AC: 4, 5)
  - [ ] 5.1 实现 `_save_report(filename, content)` 私有方法
  - [ ] 5.2 确保目录存在 (自动创建 `logs/reports/`)
  - [ ] 5.3 实现 JSON 格式化 (pretty print)
  - [ ] 5.4 实现文件命名规范
  - [ ] 5.5 添加文件写入错误处理

- [ ] Task 6: 集成到交易流程 (AC: 1)
  - [ ] 6.1 在 `TradingExecutor` 中注入 `LearningLogGenerator`
  - [ ] 6.2 在交易执行后调用 `generate_trade_report()`
  - [ ] 6.3 添加日志记录 (📝 emoji)

- [ ] Task 7: 编写单元测试 (AC: All)
  - [ ] 7.1 创建 `tests/test_trading/test_learning_log.py`
  - [ ] 7.2 测试 `generate_trade_report()` 方法
  - [ ] 7.3 测试 `generate_daily_report()` 方法
  - [ ] 7.4 测试报告存储 (文件写入)
  - [ ] 7.5 测试边界情况 (无交易、空数据)
  - [ ] 7.6 Mock 所有外部依赖

- [ ] Task 8: 代码质量检查 (AC: All)
  - [ ] 8.1 运行 `mypy src/trading/learning_log.py` 无错误
  - [ ] 8.2 运行 `black --check` 通过
  - [ ] 8.3 运行 `isort --check` 通过
  - [ ] 8.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md, epics.md]

**学习日志生成流程:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                   学习日志生成流程                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  generate_trade_report(trade, prediction, market) -> TradeReport    │
│                                                                     │
│  1. 提取市场信息                                                     │
│     market_info = MarketInfo(                                       │
│         title=market.title,                                         │
│         description=market.description,                             │
│         deadline=market.deadline                                    │
│     )                                                               │
│                                                                     │
│  2. 计算预测与价格差距                                               │
│     price_diff = abs(prediction.predicted_probability - price)      │
│                                                                     │
│  3. 整理分析信息                                                     │
│     analysis = {                                                    │
│         predicted_probability: ...,                                 │
│         confidence: ...,                                            │
│         edge: ...,                                                  │
│         reasoning: prediction.reasoning                             │
│     }                                                               │
│                                                                     │
│  4. 整理交易信息                                                     │
│     trade_info = {                                                  │
│         direction: trade.trade_type,                                │
│         amount: trade.amount,                                       │
│         price: trade.price,                                         │
│         shares: trade.shares                                        │
│     }                                                               │
│                                                                     │
│  5. 获取持仓状态                                                     │
│     position = await position_repo.get_by_market(market.id)         │
│                                                                     │
│  6. 生成并保存报告                                                   │
│     report = TradeReport(...)                                       │
│     self._save_report(f"trade_{trade.id}_{ts}.json", report)        │
│                                                                     │
│  7. 返回报告                                                         │
│     return report                                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 已有组件 (必须复用)

**Trade Model** [Source: src/models/trade.py]
```python
class TradeType(str, Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    SELL = "SELL"

class TradeMode(str, Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"

class Trade(BaseModel):
    id: int | None
    market_id: str
    trade_type: TradeType
    mode: TradeMode
    amount: float
    price: float
    shares: float | None
    status: str | None  # PENDING/FILLED/CANCELLED
    llm_prediction_id: int | None
    position_id: int | None
    created_at: datetime | None
```

**Prediction Model** [Source: src/models/prediction.py]
```python
class Prediction(BaseModel):
    id: int | None
    market_id: str
    predicted_probability: float  # 0-1
    confidence: float             # 0-1
    reasoning: str | None
    key_assumptions: list[str] | None
    model_used: str | None
    recommendation: Recommendation | None
    edge: float | None
    actual_outcome: str | None
    is_correct: bool | None
    validated_at: datetime | None
    created_at: datetime | None
```

**Market Model** [Source: src/models/market.py]
```python
class Market(BaseModel):
    id: str
    title: str
    description: str | None
    category: MarketCategory | None
    yes_price: float | None
    no_price: float | None
    liquidity: float | None
    deadline: datetime | None
    resolution_status: str | None
    resolution_outcome: str | None
    created_at: datetime | None
    updated_at: datetime | None
```

**TradeRepository** [Source: src/storage/repositories/trade_repo.py]
```python
class TradeRepository:
    async def save_trade(trade: Trade, upsert: bool = True) -> int
    async def get_trades_by_market(market_id: str) -> list[Trade]
    async def get_trades_by_mode(mode: TradeMode) -> list[Trade]
    async def get_recent_trades(limit: int) -> list[Trade]
    # Story 6.3 需要添加:
    async def get_trades_by_date(date: date) -> list[Trade]
```

**PositionRepository** [Source: src/storage/repositories/position_repo.py]
```python
class PositionRepository:
    async def get_by_market(market_id: str) -> Position | None
    async def get_open_positions() -> list[Position]
```

### 新增数据模型

**src/trading/learning_log.py:**

```python
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any

@dataclass
class MarketInfo:
    """Market information for report.

    Attributes:
        id: Market ID
        title: Market title
        description: Market description
        category: Market category
        deadline: Market deadline
        yes_price: Current YES price
        no_price: Current NO price
    """
    id: str
    title: str
    description: str | None
    category: str | None
    deadline: datetime | None
    yes_price: float | None
    no_price: float | None


@dataclass
class AnalysisInfo:
    """LLM analysis information for report.

    Attributes:
        predicted_probability: LLM predicted probability
        confidence: LLM confidence level
        edge: Price edge (prediction - market price)
        reasoning: LLM reasoning
        key_assumptions: Key assumptions from LLM
        recommendation: Trade recommendation
    """
    predicted_probability: float
    confidence: float
    edge: float | None
    reasoning: str | None
    key_assumptions: list[str] | None
    recommendation: str | None


@dataclass
class TradeInfo:
    """Trade execution information for report.

    Attributes:
        trade_id: Trade ID
        trade_type: Type of trade (BUY_YES, BUY_NO, SELL)
        mode: Trading mode (PAPER, LIVE)
        amount: Trade amount in USD
        price: Execution price
        shares: Number of shares
        status: Trade status
        executed_at: Trade execution time
    """
    trade_id: int
    trade_type: str
    mode: str
    amount: float
    price: float
    shares: float | None
    status: str | None
    executed_at: datetime


@dataclass
class PositionInfo:
    """Position information for report.

    Attributes:
        position_id: Position ID
        outcome: Position outcome (YES/NO)
        shares: Number of shares held
        avg_price: Average entry price
        current_value: Current position value
        pnl: Unrealized PnL
    """
    position_id: int | None
    outcome: str | None
    shares: float | None
    avg_price: float | None
    current_value: float | None
    pnl: float | None


@dataclass
class TradeReport:
    """Complete trade report.

    Attributes:
        report_type: Type of report (always "trade")
        generated_at: Report generation timestamp
        market: Market information
        analysis: LLM analysis information
        trade: Trade execution information
        position: Position information after trade
        price_comparison: Price comparison data
    """
    report_type: str = "trade"
    generated_at: datetime = field(default_factory=datetime.now)
    market: MarketInfo | None = None
    analysis: AnalysisInfo | None = None
    trade: TradeInfo | None = None
    position: PositionInfo | None = None
    price_comparison: dict[str, Any] = field(default_factory=dict)


@dataclass
class TradingSummary:
    """Daily trading summary.

    Attributes:
        total_trades: Total number of trades
        winning_trades: Number of winning trades
        losing_trades: Number of losing trades
        win_rate: Win rate (0-1)
        total_pnl: Total PnL in USD
        total_volume: Total trading volume
    """
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float | None
    total_pnl: float
    total_volume: float


@dataclass
class LearningInsight:
    """Learning insight from trading.

    Attributes:
        category: Insight category (success, failure, pattern, etc.)
        description: Insight description
        related_trades: List of related trade IDs
        recommendation: Improvement recommendation
    """
    category: str
    description: str
    related_trades: list[int]
    recommendation: str | None


@dataclass
class DailyReport:
    """Daily trading report.

    Attributes:
        report_type: Type of report (always "daily")
        report_date: Report date
        generated_at: Report generation timestamp
        summary: Trading summary
        trades: List of trade IDs
        insights: List of learning insights
    """
    report_type: str = "daily"
    report_date: date = field(default_factory=date.today)
    generated_at: datetime = field(default_factory=datetime.now)
    summary: TradingSummary | None = None
    trades: list[int] = field(default_factory=list)
    insights: list[LearningInsight] = field(default_factory=list)
```

### 实现模板

**src/trading/learning_log.py:**

```python
"""Learning log generator for trading reports."""

import json
from datetime import datetime, date
from pathlib import Path
from typing import TYPE_CHECKING

from src.utils.logger import get_logger, OPERATION_EMOJIS

if TYPE_CHECKING:
    from src.models.trade import Trade
    from src.models.prediction import Prediction
    from src.models.market import Market
    from src.storage.repositories.trade_repo import TradeRepository
    from src.storage.repositories.position_repo import PositionRepository

logger = get_logger(__name__)


@dataclass
class MarketInfo:
    # ... (as defined above)
    pass


@dataclass
class AnalysisInfo:
    # ... (as defined above)
    pass


@dataclass
class TradeInfo:
    # ... (as defined above)
    pass


@dataclass
class PositionInfo:
    # ... (as defined above)
    pass


@dataclass
class TradeReport:
    # ... (as defined above)
    pass


@dataclass
class TradingSummary:
    # ... (as defined above)
    pass


@dataclass
class LearningInsight:
    # ... (as defined above)
    pass


@dataclass
class DailyReport:
    # ... (as defined above)
    pass


__all__ = [
    "MarketInfo",
    "AnalysisInfo",
    "TradeInfo",
    "PositionInfo",
    "TradeReport",
    "TradingSummary",
    "LearningInsight",
    "DailyReport",
    "LearningLogGenerator",
]


class LearningLogGenerator:
    """Generates learning logs and reports for trading activities."""

    def __init__(
        self,
        trade_repo: "TradeRepository",
        position_repo: "PositionRepository",
        reports_dir: Path | None = None,
    ) -> None:
        """Initialize the learning log generator.

        Args:
            trade_repo: Trade repository for fetching trade data
            position_repo: Position repository for fetching position data
            reports_dir: Directory for storing reports (default: logs/reports/)
        """
        self._trade_repo = trade_repo
        self._position_repo = position_repo
        self._reports_dir = reports_dir or Path("logs/reports")
        self._ensure_reports_dir()

    def _ensure_reports_dir(self) -> None:
        """Ensure the reports directory exists."""
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def _save_report(self, filename: str, content: dict) -> Path:
        """Save a report to a JSON file.

        Args:
            filename: Name of the file (without path)
            content: Report content as dictionary

        Returns:
            Path to the saved file
        """
        filepath = self._reports_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, default=str, ensure_ascii=False)
        logger.info(
            f"{OPERATION_EMOJIS['data']} Report saved: {filepath}"
        )
        return filepath

    def _market_to_info(self, market: "Market") -> MarketInfo:
        """Convert Market model to MarketInfo dataclass."""
        return MarketInfo(
            id=market.id,
            title=market.title,
            description=market.description,
            category=market.category.value if market.category else None,
            deadline=market.deadline,
            yes_price=market.yes_price,
            no_price=market.no_price,
        )

    def _prediction_to_analysis(self, prediction: "Prediction") -> AnalysisInfo:
        """Convert Prediction model to AnalysisInfo dataclass."""
        return AnalysisInfo(
            predicted_probability=prediction.predicted_probability,
            confidence=prediction.confidence,
            edge=prediction.edge,
            reasoning=prediction.reasoning,
            key_assumptions=prediction.key_assumptions,
            recommendation=(
                prediction.recommendation.value
                if prediction.recommendation else None
            ),
        )

    def _trade_to_info(self, trade: "Trade") -> TradeInfo:
        """Convert Trade model to TradeInfo dataclass."""
        return TradeInfo(
            trade_id=trade.id,
            trade_type=trade.trade_type.value,
            mode=trade.mode.value,
            amount=trade.amount,
            price=trade.price,
            shares=trade.shares,
            status=trade.status,
            executed_at=trade.created_at or datetime.now(),
        )

    async def _get_position_info(self, market_id: str) -> PositionInfo | None:
        """Get position information for a market."""
        position = await self._position_repo.get_by_market(market_id)
        if not position:
            return None

        return PositionInfo(
            position_id=position.id,
            outcome=position.outcome,
            shares=position.shares,
            avg_price=position.avg_price,
            current_value=position.current_value,
            pnl=position.pnl,
        )

    async def generate_trade_report(
        self,
        trade: "Trade",
        prediction: "Prediction",
        market: "Market",
    ) -> TradeReport:
        """Generate a detailed report for a single trade.

        Args:
            trade: The executed trade
            prediction: The LLM prediction that led to the trade
            market: The market being traded

        Returns:
            TradeReport containing all trade details
        """
        logger.info(
            f"{OPERATION_EMOJIS['data']} Generating trade report for "
            f"trade {trade.id}"
        )

        # Get position info
        position_info = await self._get_position_info(market.id)

        # Calculate price comparison
        market_price = (
            market.yes_price
            if trade.trade_type.value == "BUY_YES"
            else market.no_price
        )
        price_comparison = {
            "market_price": market_price,
            "predicted_probability": prediction.predicted_probability,
            "edge": prediction.edge,
            "price_diff": abs(
                prediction.predicted_probability - (market_price or 0)
            ),
        }

        # Create report
        report = TradeReport(
            generated_at=datetime.now(),
            market=self._market_to_info(market),
            analysis=self._prediction_to_analysis(prediction),
            trade=self._trade_to_info(trade),
            position=position_info,
            price_comparison=price_comparison,
        )

        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trade_{trade.id}_{timestamp}.json"
        self._save_report(filename, self._report_to_dict(report))

        return report

    def _report_to_dict(self, report: TradeReport | DailyReport) -> dict:
        """Convert report dataclass to dictionary for JSON serialization."""
        # Implementation for converting dataclass to dict
        result = {
            "report_type": report.report_type,
            "generated_at": report.generated_at.isoformat(),
        }

        if isinstance(report, TradeReport):
            if report.market:
                result["market"] = {
                    "id": report.market.id,
                    "title": report.market.title,
                    "description": report.market.description,
                    "category": report.market.category,
                    "deadline": (
                        report.market.deadline.isoformat()
                        if report.market.deadline else None
                    ),
                    "yes_price": report.market.yes_price,
                    "no_price": report.market.no_price,
                }
            if report.analysis:
                result["analysis"] = {
                    "predicted_probability": report.analysis.predicted_probability,
                    "confidence": report.analysis.confidence,
                    "edge": report.analysis.edge,
                    "reasoning": report.analysis.reasoning,
                    "key_assumptions": report.analysis.key_assumptions,
                    "recommendation": report.analysis.recommendation,
                }
            if report.trade:
                result["trade"] = {
                    "trade_id": report.trade.trade_id,
                    "trade_type": report.trade.trade_type,
                    "mode": report.trade.mode,
                    "amount": report.trade.amount,
                    "price": report.trade.price,
                    "shares": report.trade.shares,
                    "status": report.trade.status,
                    "executed_at": report.trade.executed_at.isoformat(),
                }
            if report.position:
                result["position"] = {
                    "position_id": report.position.position_id,
                    "outcome": report.position.outcome,
                    "shares": report.position.shares,
                    "avg_price": report.position.avg_price,
                    "current_value": report.position.current_value,
                    "pnl": report.position.pnl,
                }
            result["price_comparison"] = report.price_comparison

        elif isinstance(report, DailyReport):
            result["report_date"] = report.report_date.isoformat()
            if report.summary:
                result["summary"] = {
                    "total_trades": report.summary.total_trades,
                    "winning_trades": report.summary.winning_trades,
                    "losing_trades": report.summary.losing_trades,
                    "win_rate": report.summary.win_rate,
                    "total_pnl": report.summary.total_pnl,
                    "total_volume": report.summary.total_volume,
                }
            result["trades"] = report.trades
            result["insights"] = [
                {
                    "category": insight.category,
                    "description": insight.description,
                    "related_trades": insight.related_trades,
                    "recommendation": insight.recommendation,
                }
                for insight in report.insights
            ]

        return result

    async def generate_daily_report(
        self,
        report_date: date | None = None,
    ) -> DailyReport:
        """Generate a daily summary report.

        Args:
            report_date: Date to generate report for (default: today)

        Returns:
            DailyReport containing daily trading summary
        """
        report_date = report_date or date.today()
        logger.info(
            f"{OPERATION_EMOJIS['data']} Generating daily report for "
            f"{report_date}"
        )

        # Get trades for the date
        trades = await self._trade_repo.get_trades_by_date(report_date)

        # Calculate summary
        if trades:
            total_volume = sum(t.amount for t in trades)
            # For PnL, we need to get position changes
            # Simplified: use trade count and basic stats
            summary = TradingSummary(
                total_trades=len(trades),
                winning_trades=0,  # TODO: Calculate from closed positions
                losing_trades=0,   # TODO: Calculate from closed positions
                win_rate=None,     # TODO: Calculate
                total_pnl=0.0,     # TODO: Calculate from positions
                total_volume=total_volume,
            )
        else:
            summary = TradingSummary(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=None,
                total_pnl=0.0,
                total_volume=0.0,
            )

        # Generate insights (simplified)
        insights: list[LearningInsight] = []
        if trades:
            insights.append(LearningInsight(
                category="activity",
                description=f"Executed {len(trades)} trades on {report_date}",
                related_trades=[t.id for t in trades if t.id],
                recommendation=None,
            ))

        # Create report
        report = DailyReport(
            report_date=report_date,
            generated_at=datetime.now(),
            summary=summary,
            trades=[t.id for t in trades if t.id],
            insights=insights,
        )

        # Save report
        filename = f"daily_{report_date.isoformat()}.json"
        self._save_report(filename, self._report_to_dict(report))

        return report
```

### 扩展 TradeRepository

**src/storage/repositories/trade_repo.py (新增方法):**

```python
async def get_trades_by_date(self, date: date) -> list[Trade]:
    """Get all trades for a specific date.

    Args:
        date: The date to get trades for

    Returns:
        List of trades executed on the given date
    """
    start = datetime.combine(date, datetime.min.time())
    end = datetime.combine(date, datetime.max.time())

    async with self._get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT * FROM trades
            WHERE created_at >= ? AND created_at <= ?
            ORDER BY created_at DESC
            """,
            (start.isoformat(), end.isoformat()),
        )
        rows = await cursor.fetchall()
        return [self._row_to_trade(row) for row in rows]
```

### 项目结构 [Source: architecture.md#Project Structure]

**修改文件:**
```
src/
├── trading/
│   └── learning_log.py          # 新增: 学习日志生成器
└── storage/
    └── repositories/
        └── trade_repo.py         # 修改: 添加 get_trades_by_date 方法

tests/
└── test_trading/
    └── test_learning_log.py      # 新增: 学习日志测试

logs/
└── reports/                      # 新增: 报告存储目录
    ├── trade_{id}_{ts}.json
    └── daily_{date}.json
```

### 依赖关系

**本故事依赖:**
- Story 5.1: 交易记录数据模型 (Trade 模型)
- Story 5.2: Paper Trading 执行器 (交易执行)
- Story 5.3: 交易决策流程 (TradingExecutor)
- Story 6.1: 预测结果验证机制 (Prediction 模型)
- Story 6.2: 准确率统计 (可选，用于每日报告)

**后续故事依赖本故事:**
- Story 6.5: 表现分析与洞察 (需要学习日志数据)

### 前一个故事学习 [Source: 6-2-accuracy-statistics.md]

**从 Story 6.2 学到的模式:**

1. **数据类返回结果** - 使用 `@dataclass` 定义返回类型
2. **依赖注入** - 所有依赖通过构造函数注入
3. **日志标准化** - 使用 emoji 📊 标记统计日志
4. **类型注解** - 使用 `TYPE_CHECKING` 避免循环导入
5. **`__all__` 导出** - 明确模块公共 API
6. **空值处理** - 当无数据时返回合理的默认值

### 实现注意事项

**关键点:**

1. **文件命名规范** - 使用 `trade_{id}_{timestamp}.json` 和 `daily_{date}.json`
2. **目录创建** - 确保 `logs/reports/` 目录在初始化时创建
3. **JSON 序列化** - 处理 datetime 和 Enum 序列化
4. **异步操作** - 所有数据库操作使用 async
5. **错误处理** - 文件写入失败不应影响主流程

**错误处理:**

| 场景 | 处理方式 |
|------|----------|
| 无交易记录 | 返回空报告 (trades=[]) |
| 文件写入失败 | 记录错误日志，不抛出异常 |
| 关联数据缺失 | 使用 None 或默认值 |
| 日期格式错误 | 使用 ISO 8601 格式 |

**日志级别:**

| 级别 | 场景 | Emoji |
|------|------|-------|
| INFO | 报告生成开始、完成 | 📝 |
| DEBUG | 详细报告信息 | 📝 |
| WARNING | 无数据情况 | ⚠️ |
| ERROR | 文件写入失败 | ❌ |

### 测试策略

```python
# tests/test_trading/test_learning_log.py
"""Tests for LearningLogGenerator."""

import pytest
from datetime import datetime, date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.trading.learning_log import (
    LearningLogGenerator,
    TradeReport,
    DailyReport,
    MarketInfo,
    AnalysisInfo,
    TradeInfo,
)
from src.models.trade import Trade, TradeType, TradeMode
from src.models.prediction import Prediction, Recommendation
from src.models.market import Market, MarketCategory


class TestLearningLogGenerator:
    """Tests for LearningLogGenerator."""

    @pytest.fixture
    def temp_reports_dir(self, tmp_path: Path) -> Path:
        """Create a temporary reports directory."""
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        return reports_dir

    @pytest.fixture
    def generator(
        self,
        temp_reports_dir: Path
    ) -> LearningLogGenerator:
        """Create a LearningLogGenerator instance."""
        trade_repo = AsyncMock()
        position_repo = AsyncMock()
        return LearningLogGenerator(
            trade_repo=trade_repo,
            position_repo=position_repo,
            reports_dir=temp_reports_dir,
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
            price=0.55,
            shares=18.18,
            status="FILLED",
            created_at=datetime(2026, 2, 16, 10, 30, 0),
        )

    @pytest.fixture
    def sample_prediction(self) -> Prediction:
        """Create a sample prediction."""
        return Prediction(
            id=1,
            market_id="market-1",
            predicted_probability=0.75,
            confidence=0.85,
            reasoning="Strong evidence suggests YES outcome",
            key_assumptions=["Trend continues", "No major disruptions"],
            recommendation=Recommendation.BUY_YES,
            edge=0.20,
        )

    @pytest.fixture
    def sample_market(self) -> Market:
        """Create a sample market."""
        return Market(
            id="market-1",
            title="Will X happen by Y date?",
            description="A prediction market about X",
            category=MarketCategory.POLITICS,
            yes_price=0.55,
            no_price=0.45,
            deadline=datetime(2026, 3, 1),
        )

    @pytest.mark.asyncio
    async def test_generate_trade_report(
        self,
        generator: LearningLogGenerator,
        sample_trade: Trade,
        sample_prediction: Prediction,
        sample_market: Market,
    ) -> None:
        """Test generating a trade report."""
        generator._position_repo.get_by_market = AsyncMock(return_value=None)

        report = await generator.generate_trade_report(
            sample_trade, sample_prediction, sample_market
        )

        assert report.report_type == "trade"
        assert report.market is not None
        assert report.market.title == "Will X happen by Y date?"
        assert report.analysis is not None
        assert report.analysis.confidence == 0.85
        assert report.trade is not None
        assert report.trade.trade_type == "BUY_YES"

    @pytest.mark.asyncio
    async def test_generate_trade_report_saves_file(
        self,
        generator: LearningLogGenerator,
        sample_trade: Trade,
        sample_prediction: Prediction,
        sample_market: Market,
        temp_reports_dir: Path,
    ) -> None:
        """Test that trade report is saved to file."""
        generator._position_repo.get_by_market = AsyncMock(return_value=None)

        await generator.generate_trade_report(
            sample_trade, sample_prediction, sample_market
        )

        # Check file was created
        report_files = list(temp_reports_dir.glob("trade_1_*.json"))
        assert len(report_files) == 1

        # Verify content
        with open(report_files[0]) as f:
            content = json.load(f)
        assert content["report_type"] == "trade"
        assert content["market"]["title"] == "Will X happen by Y date?"

    @pytest.mark.asyncio
    async def test_generate_daily_report(
        self,
        generator: LearningLogGenerator,
        sample_trade: Trade,
    ) -> None:
        """Test generating a daily report."""
        generator._trade_repo.get_trades_by_date = AsyncMock(
            return_value=[sample_trade]
        )

        report = await generator.generate_daily_report(
            date(2026, 2, 16)
        )

        assert report.report_type == "daily"
        assert report.report_date == date(2026, 2, 16)
        assert report.summary is not None
        assert report.summary.total_trades == 1
        assert len(report.trades) == 1

    @pytest.mark.asyncio
    async def test_generate_daily_report_empty(
        self,
        generator: LearningLogGenerator,
    ) -> None:
        """Test generating a daily report with no trades."""
        generator._trade_repo.get_trades_by_date = AsyncMock(return_value=[])

        report = await generator.generate_daily_report(
            date(2026, 2, 16)
        )

        assert report.summary.total_trades == 0
        assert report.trades == []

    @pytest.mark.asyncio
    async def test_generate_daily_report_saves_file(
        self,
        generator: LearningLogGenerator,
        sample_trade: Trade,
        temp_reports_dir: Path,
    ) -> None:
        """Test that daily report is saved to file."""
        generator._trade_repo.get_trades_by_date = AsyncMock(
            return_value=[sample_trade]
        )

        await generator.generate_daily_report(date(2026, 2, 16))

        # Check file was created
        report_file = temp_reports_dir / "daily_2026-02-16.json"
        assert report_file.exists()

        # Verify content
        with open(report_file) as f:
            content = json.load(f)
        assert content["report_type"] == "daily"
```

### References

- [Source: architecture.md#Database Schema] - trades 表定义
- [Source: epics.md#Story 6.3] - 原始 Story 定义
- [Source: src/models/trade.py] - Trade 模型定义
- [Source: src/models/prediction.py] - Prediction 模型定义
- [Source: src/models/market.py] - Market 模型定义
- [Source: src/storage/repositories/trade_repo.py] - TradeRepository 参考
- [Source: 6-2-accuracy-statistics.md] - 前一个故事实现参考
