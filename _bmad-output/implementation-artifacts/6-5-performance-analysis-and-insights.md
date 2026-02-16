# Story 6.5: 表现分析与洞察

Status: ready-for-dev

## Story

As a **用户**,
I want **系统能够分析我的交易表现并提供改进洞察**,
So that **我能够持续优化策略**.

## Acceptance Criteria

**Given** 预测追踪和学习日志已实现 (Story 6.1, Story 6.2, Story 6.3, Story 6.4)
**When** 实现 `src/analysis/performance_analyzer.py`
**Then** 创建 `PerformanceAnalyzer` 类:
- `analyze_performance()` - 综合表现分析
- `identify_patterns()` - 识别成功/失败模式
- `generate_recommendations()` - 生成改进建议

**And** 分析内容包含:
- 最佳/最差交易类别
- 高置信度预测的准确率
- 低置信度预测的表现
- Edge 大小与成功率关系
- 持仓时间与收益关系

**And** 生成洞察报告存储到 `logs/reports/insights_{date}.json`
**And** 记录分析日志 (🧠 表现分析完成)

## Tasks / Subtasks

- [ ] Task 1: 定义数据模型 (AC: All)
  - [ ] 1.1 创建 `PerformanceMetrics` 数据类 (total_trades, win_rate, avg_pnl, etc.)
  - [ ] 1.2 创建 `CategoryPerformance` 数据类 (category, trades, win_rate, pnl)
  - [ ] 1.3 创建 `ConfidenceAnalysis` 数据类 (confidence_range, accuracy, sample_size)
  - [ ] 1.4 创建 `EdgeAnalysis` 数据类 (edge_range, success_rate, avg_return)
  - [ ] 1.5 创建 `PatternInsight` 数据类 (pattern_type, description, examples)
  - [ ] 1.6 创建 `PerformanceInsightReport` 数据类 (metrics, patterns, recommendations)
  - [ ] 1.7 更新 `__all__` 导出

- [ ] Task 2: 实现 PerformanceAnalyzer 类基础结构 (AC: 1)
  - [ ] 2.1 创建 `src/analysis/performance_analyzer.py` 文件
  - [ ] 2.2 定义 `PerformanceAnalyzer` 类
  - [ ] 2.3 注入依赖 (PredictionRepository, TradeRepository, PositionRepository)
  - [ ] 2.4 添加日志配置 (使用 🧠 emoji)

- [ ] Task 3: 实现综合表现分析 (AC: 1)
  - [ ] 3.1 实现 `analyze_performance()` 方法
  - [ ] 3.2 计算总体指标 (总交易数、胜率、平均 PnL)
  - [ ] 3.3 按类别分组分析 (最佳/最差类别)
  - [ ] 3.4 计算高置信度预测准确率 (confidence >= 0.8)
  - [ ] 3.5 计算低置信度预测表现 (confidence < 0.75)
  - [ ] 3.6 返回 `PerformanceMetrics` 对象

- [ ] Task 4: 实现模式识别 (AC: 1)
  - [ ] 4.1 实现 `identify_patterns()` 方法
  - [ ] 4.2 识别成功模式 (高置信度 + 高 edge 的表现)
  - [ ] 4.3 识别失败模式 (低置信度或低 edge 的表现)
  - [ ] 4.4 分析 Edge 大小与成功率关系
  - [ ] 4.5 分析持仓时间与收益关系
  - [ ] 4.6 返回 `PatternInsight` 列表

- [ ] Task 5: 实现改进建议生成 (AC: 1)
  - [ ] 5.1 实现 `generate_recommendations()` 方法
  - [ ] 5.2 基于模式分析生成策略建议
  - [ ] 5.3 识别需要改进的领域
  - [ ] 5.4 提供具体可执行的建议
  - [ ] 5.5 返回建议字符串列表

- [ ] Task 6: 实现洞察报告生成 (AC: 2, 3)
  - [ ] 6.1 实现 `generate_insight_report()` 方法
  - [ ] 6.2 组合 PerformanceMetrics、PatternInsight、recommendations
  - [ ] 6.3 生成 JSON 格式报告
  - [ ] 6.4 存储到 `logs/reports/insights_{date}.json`
  - [ ] 6.5 确保报告目录存在
  - [ ] 6.6 记录分析完成日志 (🧠 表现分析完成)

- [ ] Task 7: 编写单元测试 (AC: All)
  - [ ] 7.1 创建 `tests/test_analysis/test_performance_analyzer.py`
  - [ ] 7.2 测试 `analyze_performance()` 方法
  - [ ] 7.3 测试 `identify_patterns()` 方法
  - [ ] 7.4 测试 `generate_recommendations()` 方法
  - [ ] 7.5 测试 `generate_insight_report()` 方法
  - [ ] 7.6 测试边界情况 (无数据、单条数据)
  - [ ] 7.7 Mock 所有外部依赖

- [ ] Task 8: 代码质量检查 (AC: All)
  - [ ] 8.1 运行 `mypy src/analysis/performance_analyzer.py` 无错误
  - [ ] 8.2 运行 `black --check` 通过
  - [ ] 8.3 运行 `isort --check` 通过
  - [ ] 8.4 运行完整测试套件确保通过

## Dev Notes

### 技术规范 [Source: architecture.md, epics.md]

**表现分析流程:**

```
+---------------------------------------------------------------------+
|                   表现分析与洞察流程                                  |
+---------------------------------------------------------------------+
|                                                                     |
|  analyze_performance()                                              |
|                                                                     |
|  1. 获取数据                                                        |
|     - 从 predictions 获取已验证预测                                  |
|     - 从 trades 获取交易记录                                        |
|     - 从 positions 获取持仓数据                                     |
|                                                                     |
|  2. 计算总体指标                                                    |
|     - total_trades, winning_trades, win_rate                       |
|     - total_pnl, avg_pnl, max_profit, max_loss                     |
|     - avg_confidence, avg_edge                                     |
|                                                                     |
|  3. 按类别分析                                                      |
|     - 按市场类别分组                                                |
|     - 计算各类别胜率和 PnL                                          |
|     - 识别最佳/最差类别                                            |
|                                                                     |
|  4. 置信度分析                                                      |
|     - 高置信度 (>= 0.8) 准确率                                      |
|     - 中置信度 (0.75-0.8) 准确率                                    |
|     - 低置信度 (< 0.75) 准确率                                      |
|                                                                     |
|  5. Edge 分析                                                       |
|     - Edge >= 0.2 成功率                                           |
|     - Edge 0.1-0.2 成功率                                          |
|     - Edge < 0.1 成功率                                            |
|                                                                     |
|  6. 生成洞察报告                                                    |
|     - 存储到 logs/reports/insights_{date}.json                     |
|                                                                     |
+---------------------------------------------------------------------+
```

### 已有组件 (必须复用)

**PredictionRepository** [Source: src/storage/repositories/prediction_repo.py]
```python
class PredictionRepository:
    # 已实现的方法:
    async def get_all_validated() -> list[Prediction]
    async def get_validated_with_market() -> list[tuple[Prediction, Market]]
    async def get_correct_predictions() -> PredictionQueryResult
    async def get_incorrect_predictions() -> PredictionQueryResult
    async def get_predictions_by_confidence_range(min, max) -> PredictionQueryResult
```

**TradeRepository** [Source: src/storage/repositories/trade_repo.py]
```python
class TradeRepository:
    # 已实现的方法:
    async def get_trades_by_mode(mode) -> list[Trade]
    async def get_recent_trades(limit) -> list[Trade]
    async def get_trades_by_market(market_id) -> list[Trade]
```

**PositionRepository** [Source: src/storage/repositories/position_repo.py]
```python
class PositionRepository:
    # 已实现的方法:
    async def get_open_positions() -> list[Position]
    async def get_closed_positions() -> list[Position]
    async def get_positions_by_market(market_id) -> list[Position]
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

**Trade Model** [Source: src/models/trade.py]
```python
class Trade(BaseModel):
    id: int | None
    market_id: str
    trade_type: TradeType  # BUY_YES, BUY_NO, SELL
    mode: TradeMode        # PAPER, LIVE
    amount: float
    price: float
    shares: float | None
    status: str
    llm_prediction_id: int | None
    position_id: int | None
    created_at: datetime | None
```

**Position Model** [Source: src/models/position.py]
```python
class Position(BaseModel):
    id: int | None
    market_id: str
    outcome: str  # YES/NO
    shares: float
    avg_price: float
    initial_value: float | None
    current_value: float | None
    pnl: float | None
    status: PositionStatus  # OPEN/CLOSED
    opened_at: datetime | None
    closed_at: datetime | None
```

### 新增数据模型

**src/analysis/performance_analyzer.py:**

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal

class PerformanceLevel(str, Enum):
    """Performance level classification."""
    EXCELLENT = "excellent"  # win_rate >= 70%
    GOOD = "good"           # win_rate >= 55%
    AVERAGE = "average"     # win_rate >= 45%
    POOR = "poor"           # win_rate < 45%


class PatternType(str, Enum):
    """Type of identified pattern."""
    SUCCESS = "success"
    FAILURE = "failure"
    NEUTRAL = "neutral"


@dataclass
class PerformanceMetrics:
    """Overall performance metrics.

    Attributes:
        total_trades: Total number of trades
        winning_trades: Number of winning trades
        losing_trades: Number of losing trades
        win_rate: Win rate (0-1)
        total_pnl: Total profit/loss
        avg_pnl: Average profit/loss per trade
        max_profit: Maximum single trade profit
        max_loss: Maximum single trade loss
        avg_confidence: Average prediction confidence
        avg_edge: Average edge
        performance_level: Overall performance level
        analysis_period: Period of analysis
    """
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    max_profit: float
    max_loss: float
    avg_confidence: float
    avg_edge: float
    performance_level: PerformanceLevel
    analysis_period: tuple[datetime | None, datetime | None] = (None, None)


@dataclass
class CategoryPerformance:
    """Performance metrics by market category.

    Attributes:
        category: Market category
        total_trades: Number of trades in this category
        winning_trades: Winning trades in this category
        win_rate: Win rate for this category
        total_pnl: Total PnL for this category
        avg_pnl: Average PnL per trade
        avg_confidence: Average confidence for this category
    """
    category: str
    total_trades: int
    winning_trades: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    avg_confidence: float


@dataclass
class ConfidenceAnalysis:
    """Performance analysis by confidence range.

    Attributes:
        confidence_range: Range label (e.g., "0.8-1.0")
        min_confidence: Minimum confidence
        max_confidence: Maximum confidence
        sample_size: Number of predictions in range
        accuracy: Accuracy rate (0-1)
        avg_pnl: Average PnL for this range
    """
    confidence_range: str
    min_confidence: float
    max_confidence: float
    sample_size: int
    accuracy: float
    avg_pnl: float


@dataclass
class EdgeAnalysis:
    """Performance analysis by edge range.

    Attributes:
        edge_range: Range label (e.g., ">= 0.2")
        min_edge: Minimum edge
        max_edge: Maximum edge
        sample_size: Number of predictions in range
        success_rate: Success rate (0-1)
        avg_return: Average return
    """
    edge_range: str
    min_edge: float
    max_edge: float
    sample_size: int
    success_rate: float
    avg_return: float


@dataclass
class PatternInsight:
    """Identified pattern insight.

    Attributes:
        pattern_type: Type of pattern (success/failure/neutral)
        title: Short title for the pattern
        description: Detailed description
        examples: Example cases
        recommendation: Suggested action
    """
    pattern_type: PatternType
    title: str
    description: str
    examples: list[str] = field(default_factory=list)
    recommendation: str | None = None


@dataclass
class PerformanceInsightReport:
    """Complete performance insight report.

    Attributes:
        generated_at: Report generation timestamp
        metrics: Overall performance metrics
        category_performance: Performance by category
        confidence_analysis: Analysis by confidence range
        edge_analysis: Analysis by edge range
        patterns: Identified patterns
        recommendations: List of recommendations
    """
    generated_at: datetime
    metrics: PerformanceMetrics
    category_performance: list[CategoryPerformance]
    confidence_analysis: list[ConfidenceAnalysis]
    edge_analysis: list[EdgeAnalysis]
    patterns: list[PatternInsight]
    recommendations: list[str]
```

### 实现模板

**src/analysis/performance_analyzer.py:**

```python
"""
Performance Analyzer Module.

This module provides performance analysis and insight generation
for trading strategy optimization.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.market import Market
    from src.models.position import Position
    from src.models.prediction import Prediction
    from src.models.trade import Trade
    from src.storage.repositories.position_repo import PositionRepository
    from src.storage.repositories.prediction_repo import PredictionRepository
    from src.storage.repositories.trade_repo import TradeRepository

logger = logging.getLogger(__name__)


# Emojis for logging
ANALYSIS_EMOJI = "\U0001F9E0"  # 🧠


class PerformanceLevel(str, Enum):
    """Performance level classification."""
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"


class PatternType(str, Enum):
    """Type of identified pattern."""
    SUCCESS = "success"
    FAILURE = "failure"
    NEUTRAL = "neutral"


@dataclass
class PerformanceMetrics:
    """Overall performance metrics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    max_profit: float
    max_loss: float
    avg_confidence: float
    avg_edge: float
    performance_level: PerformanceLevel
    analysis_period: tuple[datetime | None, datetime | None] = (None, None)


@dataclass
class CategoryPerformance:
    """Performance metrics by market category."""
    category: str
    total_trades: int
    winning_trades: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    avg_confidence: float


@dataclass
class ConfidenceAnalysis:
    """Performance analysis by confidence range."""
    confidence_range: str
    min_confidence: float
    max_confidence: float
    sample_size: int
    accuracy: float
    avg_pnl: float


@dataclass
class EdgeAnalysis:
    """Performance analysis by edge range."""
    edge_range: str
    min_edge: float
    max_edge: float
    sample_size: int
    success_rate: float
    avg_return: float


@dataclass
class PatternInsight:
    """Identified pattern insight."""
    pattern_type: PatternType
    title: str
    description: str
    examples: list[str] = field(default_factory=list)
    recommendation: str | None = None


@dataclass
class PerformanceInsightReport:
    """Complete performance insight report."""
    generated_at: datetime
    metrics: PerformanceMetrics
    category_performance: list[CategoryPerformance]
    confidence_analysis: list[ConfidenceAnalysis]
    edge_analysis: list[EdgeAnalysis]
    patterns: list[PatternInsight]
    recommendations: list[str]


__all__ = [
    "PerformanceLevel",
    "PatternType",
    "PerformanceMetrics",
    "CategoryPerformance",
    "ConfidenceAnalysis",
    "EdgeAnalysis",
    "PatternInsight",
    "PerformanceInsightReport",
    "PerformanceAnalyzer",
]


class PerformanceAnalyzer:
    """Analyzer for trading performance and strategy insights.

    This class provides methods to analyze trading performance,
    identify patterns, and generate recommendations for improvement.

    Example:
        >>> analyzer = PerformanceAnalyzer(prediction_repo, trade_repo, position_repo)
        >>> report = await analyzer.generate_insight_report()
        >>> print(report.recommendations)
        ['Focus on high-confidence predictions in politics category']
    """

    def __init__(
        self,
        prediction_repo: PredictionRepository,
        trade_repo: TradeRepository,
        position_repo: PositionRepository,
        reports_dir: str = "logs/reports",
    ) -> None:
        """Initialize the performance analyzer.

        Args:
            prediction_repo: Repository for prediction data
            trade_repo: Repository for trade data
            position_repo: Repository for position data
            reports_dir: Directory to store insight reports
        """
        self._prediction_repo = prediction_repo
        self._trade_repo = trade_repo
        self._position_repo = position_repo
        self._reports_dir = Path(reports_dir)

    async def analyze_performance(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> PerformanceMetrics:
        """Analyze overall trading performance.

        Args:
            start_date: Start of analysis period (optional)
            end_date: End of analysis period (optional)

        Returns:
            PerformanceMetrics with overall performance data

        Example:
            >>> metrics = await analyzer.analyze_performance()
            >>> print(f"Win rate: {metrics.win_rate:.1%}")
            Win rate: 62.5%
        """
        logger.info(f"{ANALYSIS_EMOJI} Starting performance analysis...")

        # Get validated predictions with market info
        predictions_with_markets = await self._prediction_repo.get_validated_with_market()

        # Get all trades
        trades = await self._trade_repo.get_trades_by_mode("PAPER")

        # Get closed positions for PnL
        positions = await self._position_repo.get_closed_positions()

        # Calculate metrics
        total_trades = len(trades)
        winning_trades = sum(1 for p in positions if p.pnl and p.pnl > 0)
        losing_trades = sum(1 for p in positions if p.pnl and p.pnl < 0)

        total_pnl = sum(p.pnl or 0 for p in positions)
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0.0

        max_profit = max((p.pnl or 0 for p in positions), default=0.0)
        max_loss = min((p.pnl or 0 for p in positions), default=0.0)

        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        # Calculate average confidence and edge
        validated = [p for p, _ in predictions_with_markets if p.is_correct is not None]
        avg_confidence = (
            sum(p.confidence for p in validated) / len(validated)
            if validated else 0.0
        )
        avg_edge = (
            sum(p.edge or 0 for p in validated) / len(validated)
            if validated else 0.0
        )

        # Determine performance level
        if win_rate >= 0.70:
            performance_level = PerformanceLevel.EXCELLENT
        elif win_rate >= 0.55:
            performance_level = PerformanceLevel.GOOD
        elif win_rate >= 0.45:
            performance_level = PerformanceLevel.AVERAGE
        else:
            performance_level = PerformanceLevel.POOR

        metrics = PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_pnl=avg_pnl,
            max_profit=max_profit,
            max_loss=max_loss,
            avg_confidence=avg_confidence,
            avg_edge=avg_edge,
            performance_level=performance_level,
            analysis_period=(start_date, end_date),
        )

        logger.info(
            f"{ANALYSIS_EMOJI} Performance analysis complete: "
            f"win_rate={win_rate:.1%}, total_pnl=${total_pnl:.2f}"
        )

        return metrics

    async def identify_patterns(self) -> list[PatternInsight]:
        """Identify success and failure patterns.

        Returns:
            List of PatternInsight with identified patterns

        Example:
            >>> patterns = await analyzer.identify_patterns()
            >>> for p in patterns:
            ...     print(f"{p.pattern_type}: {p.title}")
            success: High confidence politics predictions
            failure: Low edge crypto predictions
        """
        logger.info(f"{ANALYSIS_EMOJI} Identifying patterns...")

        patterns: list[PatternInsight] = []

        # Get data
        predictions_with_markets = await self._prediction_repo.get_validated_with_market()

        # Group by category
        category_results: dict[str, list[tuple[Prediction, Market]]] = defaultdict(list)
        for pred, market in predictions_with_markets:
            category = market.category.value if market.category else "unknown"
            category_results[category].append((pred, market))

        # Analyze each category
        for category, items in category_results.items():
            correct = sum(1 for p, _ in items if p.is_correct)
            total = len(items)
            rate = correct / total if total > 0 else 0

            if total >= 3:  # Need minimum sample size
                if rate >= 0.7:
                    patterns.append(PatternInsight(
                        pattern_type=PatternType.SUCCESS,
                        title=f"Strong performance in {category}",
                        description=f"{rate:.0%} accuracy in {category} markets ({correct}/{total})",
                        examples=[m.title for _, m in items[:3]],
                        recommendation=f"Consider focusing more on {category} markets",
                    ))
                elif rate < 0.4:
                    patterns.append(PatternInsight(
                        pattern_type=PatternType.FAILURE,
                        title=f"Struggling in {category}",
                        description=f"Only {rate:.0%} accuracy in {category} markets ({correct}/{total})",
                        examples=[m.title for _, m in items[:3]],
                        recommendation=f"Consider avoiding {category} markets or refining analysis",
                    ))

        # Analyze confidence vs accuracy
        high_conf_items = [
            (p, m) for p, m in predictions_with_markets
            if p.confidence >= 0.8 and p.is_correct is not None
        ]
        if high_conf_items:
            high_conf_correct = sum(1 for p, _ in high_conf_items if p.is_correct)
            high_conf_rate = high_conf_correct / len(high_conf_items)
            patterns.append(PatternInsight(
                pattern_type=(
                    PatternType.SUCCESS if high_conf_rate >= 0.7
                    else PatternType.FAILURE
                ),
                title="High confidence prediction accuracy",
                description=f"Predictions with >= 80% confidence have {high_conf_rate:.0%} accuracy",
                recommendation=(
                    "Trust high confidence predictions" if high_conf_rate >= 0.7
                    else "Re-evaluate confidence calibration"
                ),
            ))

        logger.info(f"{ANALYSIS_EMOJI} Identified {len(patterns)} patterns")
        return patterns

    def generate_recommendations(
        self,
        metrics: PerformanceMetrics,
        patterns: list[PatternInsight],
    ) -> list[str]:
        """Generate improvement recommendations.

        Args:
            metrics: Performance metrics
            patterns: Identified patterns

        Returns:
            List of recommendation strings

        Example:
            >>> recommendations = analyzer.generate_recommendations(metrics, patterns)
            >>> for r in recommendations:
            ...     print(f"- {r}")
            - Focus on high-confidence predictions
            - Avoid crypto markets
        """
        logger.info(f"{ANALYSIS_EMOJI} Generating recommendations...")

        recommendations: list[str] = []

        # Based on overall performance
        if metrics.win_rate < 0.5:
            recommendations.append(
                "Consider pausing trading and reviewing strategy - win rate below 50%"
            )

        if metrics.avg_confidence < 0.7:
            recommendations.append(
                "Average confidence is low - consider stricter prediction criteria"
            )

        if metrics.avg_edge < 0.1:
            recommendations.append(
                "Average edge is below threshold - focus on higher conviction trades"
            )

        # Based on patterns
        for pattern in patterns:
            if pattern.recommendation:
                recommendations.append(pattern.recommendation)

        # Based on risk metrics
        if abs(metrics.max_loss) > metrics.max_profit * 2:
            recommendations.append(
                "Maximum loss exceeds maximum profit by 2x - review risk management"
            )

        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)

        logger.info(
            f"{ANALYSIS_EMOJI} Generated {len(unique_recommendations)} recommendations"
        )
        return unique_recommendations

    async def generate_insight_report(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> PerformanceInsightReport:
        """Generate complete performance insight report.

        Args:
            start_date: Start of analysis period (optional)
            end_date: End of analysis period (optional)

        Returns:
            PerformanceInsightReport with complete analysis

        Example:
            >>> report = await analyzer.generate_insight_report()
            >>> print(f"Win rate: {report.metrics.win_rate:.1%}")
            >>> print(f"Recommendations: {len(report.recommendations)}")
        """
        logger.info(f"{ANALYSIS_EMOJI} Generating insight report...")

        # Ensure reports directory exists
        self._reports_dir.mkdir(parents=True, exist_ok=True)

        # Run analysis
        metrics = await self.analyze_performance(start_date, end_date)
        patterns = await self.identify_patterns()
        recommendations = self.generate_recommendations(metrics, patterns)

        # Build category performance
        predictions_with_markets = await self._prediction_repo.get_validated_with_market()
        category_stats: dict[str, dict] = defaultdict(lambda: {
            "total": 0, "correct": 0, "pnl": 0.0, "confidence": 0.0
        })

        for pred, market in predictions_with_markets:
            category = market.category.value if market.category else "unknown"
            stats = category_stats[category]
            stats["total"] += 1
            if pred.is_correct:
                stats["correct"] += 1
            stats["confidence"] += pred.confidence

        category_performance = [
            CategoryPerformance(
                category=cat,
                total_trades=stats["total"],
                winning_trades=stats["correct"],
                win_rate=stats["correct"] / stats["total"] if stats["total"] > 0 else 0,
                total_pnl=stats["pnl"],
                avg_pnl=stats["pnl"] / stats["total"] if stats["total"] > 0 else 0,
                avg_confidence=stats["confidence"] / stats["total"] if stats["total"] > 0 else 0,
            )
            for cat, stats in category_stats.items()
        ]

        # Build confidence analysis
        confidence_analysis = await self._analyze_by_confidence(predictions_with_markets)

        # Build edge analysis
        edge_analysis = await self._analyze_by_edge(predictions_with_markets)

        # Create report
        report = PerformanceInsightReport(
            generated_at=datetime.now(),
            metrics=metrics,
            category_performance=category_performance,
            confidence_analysis=confidence_analysis,
            edge_analysis=edge_analysis,
            patterns=patterns,
            recommendations=recommendations,
        )

        # Save report to file
        report_filename = f"insights_{datetime.now().strftime('%Y-%m-%d')}.json"
        report_path = self._reports_dir / report_filename

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self._report_to_dict(report), f, indent=2, ensure_ascii=False)

        logger.info(f"{ANALYSIS_EMOJI} Insight report saved to {report_path}")
        return report

    async def _analyze_by_confidence(
        self,
        predictions_with_markets: list[tuple[Prediction, Market]],
    ) -> list[ConfidenceAnalysis]:
        """Analyze performance by confidence range."""
        ranges = [
            ("0.8-1.0", 0.8, 1.0),
            ("0.75-0.8", 0.75, 0.8),
            ("< 0.75", 0.0, 0.75),
        ]

        results = []
        for label, min_c, max_c in ranges:
            items = [
                (p, m) for p, m in predictions_with_markets
                if min_c <= p.confidence < max_c and p.is_correct is not None
            ]
            if not items:
                continue

            correct = sum(1 for p, _ in items if p.is_correct)
            results.append(ConfidenceAnalysis(
                confidence_range=label,
                min_confidence=min_c,
                max_confidence=max_c,
                sample_size=len(items),
                accuracy=correct / len(items),
                avg_pnl=0.0,  # Would need to join with trades/positions
            ))

        return results

    async def _analyze_by_edge(
        self,
        predictions_with_markets: list[tuple[Prediction, Market]],
    ) -> list[EdgeAnalysis]:
        """Analyze performance by edge range."""
        ranges = [
            (">= 0.2", 0.2, 1.0),
            ("0.1-0.2", 0.1, 0.2),
            ("< 0.1", 0.0, 0.1),
        ]

        results = []
        for label, min_e, max_e in ranges:
            items = [
                (p, m) for p, m in predictions_with_markets
                if p.edge is not None
                and min_e <= p.edge < max_e
                and p.is_correct is not None
            ]
            if not items:
                continue

            correct = sum(1 for p, _ in items if p.is_correct)
            results.append(EdgeAnalysis(
                edge_range=label,
                min_edge=min_e,
                max_edge=max_e,
                sample_size=len(items),
                success_rate=correct / len(items),
                avg_return=0.0,  # Would need to join with trades/positions
            ))

        return results

    def _report_to_dict(self, report: PerformanceInsightReport) -> dict:
        """Convert report to dictionary for JSON serialization."""
        return {
            "generated_at": report.generated_at.isoformat(),
            "metrics": {
                "total_trades": report.metrics.total_trades,
                "winning_trades": report.metrics.winning_trades,
                "losing_trades": report.metrics.losing_trades,
                "win_rate": report.metrics.win_rate,
                "total_pnl": report.metrics.total_pnl,
                "avg_pnl": report.metrics.avg_pnl,
                "max_profit": report.metrics.max_profit,
                "max_loss": report.metrics.max_loss,
                "avg_confidence": report.metrics.avg_confidence,
                "avg_edge": report.metrics.avg_edge,
                "performance_level": report.metrics.performance_level.value,
            },
            "category_performance": [
                {
                    "category": cp.category,
                    "total_trades": cp.total_trades,
                    "winning_trades": cp.winning_trades,
                    "win_rate": cp.win_rate,
                    "total_pnl": cp.total_pnl,
                    "avg_pnl": cp.avg_pnl,
                    "avg_confidence": cp.avg_confidence,
                }
                for cp in report.category_performance
            ],
            "confidence_analysis": [
                {
                    "confidence_range": ca.confidence_range,
                    "min_confidence": ca.min_confidence,
                    "max_confidence": ca.max_confidence,
                    "sample_size": ca.sample_size,
                    "accuracy": ca.accuracy,
                    "avg_pnl": ca.avg_pnl,
                }
                for ca in report.confidence_analysis
            ],
            "edge_analysis": [
                {
                    "edge_range": ea.edge_range,
                    "min_edge": ea.min_edge,
                    "max_edge": ea.max_edge,
                    "sample_size": ea.sample_size,
                    "success_rate": ea.success_rate,
                    "avg_return": ea.avg_return,
                }
                for ea in report.edge_analysis
            ],
            "patterns": [
                {
                    "pattern_type": p.pattern_type.value,
                    "title": p.title,
                    "description": p.description,
                    "examples": p.examples,
                    "recommendation": p.recommendation,
                }
                for p in report.patterns
            ],
            "recommendations": report.recommendations,
        }
```

### 项目结构 [Source: architecture.md#Project Structure]

**新增/修改文件:**
```
src/
└── analysis/
    └── performance_analyzer.py    # 新增: 表现分析器

tests/
└── test_analysis/
    └── test_performance_analyzer.py  # 新增: 分析器测试

logs/
└── reports/
    └── insights_{date}.json       # 生成的洞察报告
```

### 依赖关系

**本故事依赖:**
- Story 6.1: 预测结果验证机制 (已完成 - is_correct, validated_at 字段)
- Story 6.2: 准确率统计 (已完成 - get_validated_with_market)
- Story 6.3: 学习日志生成 (已完成 - 报告格式参考)
- Story 6.4: 预测历史查询 API (已完成 - 查询方法)

**后续故事依赖本故事:**
- Story 7.4: 预测与统计 API (可使用 PerformanceAnalyzer 提供 Dashboard 数据)

### 前一个故事学习 [Source: 6-4-prediction-history-query-api.md]

**从 Story 6.4 学到的模式:**

1. **数据类返回结果** - 使用 `@dataclass` 定义结构化返回类型
2. **依赖注入** - 所有 Repository 通过构造函数注入
3. **日志标准化** - 使用 emoji 🧠 标记分析日志
4. **类型注解** - 使用 `TYPE_CHECKING` 避免循环导入
5. **`__all__` 导出** - 明确模块公共 API
6. **异步方法** - 所有数据库操作使用 async/await

### 实现注意事项

**关键点:**

1. **样本大小要求** - 模式识别需要最小样本量 (>= 3)
2. **JSON 序列化** - datetime 需要转换为 ISO 格式字符串
3. **报告目录** - 确保 `logs/reports/` 目录存在
4. **错误处理** - 处理无数据情况，返回合理默认值

**错误处理:**

| 场景 | 处理方式 |
|------|----------|
| 无交易数据 | 返回空指标，total_trades=0 |
| 无验证预测 | 返回空模式列表 |
| 目录创建失败 | 抛出 IOError |
| JSON 写入失败 | 抛出 IOError |

**日志级别:**

| 级别 | 场景 | Emoji |
|------|------|-------|
| INFO | 分析开始、完成 | 🧠 |
| DEBUG | 详细分析信息 | 🧠 |
| WARNING | 数据不足 | ⚠️ |
| ERROR | 操作失败 | ❌ |

### 测试策略

```python
# tests/test_analysis/test_performance_analyzer.py
"""Tests for PerformanceAnalyzer."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from src.analysis.performance_analyzer import (
    PerformanceAnalyzer,
    PerformanceMetrics,
    PerformanceLevel,
    PatternInsight,
    PatternType,
    PerformanceInsightReport,
)
from src.models.prediction import Prediction
from src.models.market import Market, MarketCategory


class TestPerformanceAnalyzer:
    """测试表现分析器."""

    @pytest.fixture
    def mock_prediction_repo(self):
        """Mock prediction repository."""
        return MagicMock()

    @pytest.fixture
    def mock_trade_repo(self):
        """Mock trade repository."""
        return MagicMock()

    @pytest.fixture
    def mock_position_repo(self):
        """Mock position repository."""
        return MagicMock()

    @pytest.fixture
    def analyzer(
        self,
        mock_prediction_repo,
        mock_trade_repo,
        mock_position_repo,
    ):
        """Create analyzer with mocked dependencies."""
        return PerformanceAnalyzer(
            prediction_repo=mock_prediction_repo,
            trade_repo=mock_trade_repo,
            position_repo=mock_position_repo,
            reports_dir="/tmp/test_reports",
        )

    @pytest.mark.asyncio
    async def test_analyze_performance_no_data(
        self,
        analyzer: PerformanceAnalyzer,
        mock_prediction_repo,
        mock_trade_repo,
        mock_position_repo,
    ) -> None:
        """测试无数据情况."""
        mock_prediction_repo.get_validated_with_market = AsyncMock(return_value=[])
        mock_trade_repo.get_trades_by_mode = AsyncMock(return_value=[])
        mock_position_repo.get_closed_positions = AsyncMock(return_value=[])

        metrics = await analyzer.analyze_performance()

        assert metrics.total_trades == 0
        assert metrics.win_rate == 0.0
        assert metrics.performance_level == PerformanceLevel.POOR

    @pytest.mark.asyncio
    async def test_identify_patterns(
        self,
        analyzer: PerformanceAnalyzer,
        mock_prediction_repo,
    ) -> None:
        """测试模式识别."""
        # Create mock predictions with markets
        mock_market = Market(
            id="test-1",
            title="Test Market",
            category=MarketCategory.POLITICS,
        )
        mock_prediction = Prediction(
            id=1,
            market_id="test-1",
            predicted_probability=0.7,
            confidence=0.85,
            is_correct=True,
        )

        mock_prediction_repo.get_validated_with_market = AsyncMock(
            return_value=[(mock_prediction, mock_market)]
        )

        patterns = await analyzer.identify_patterns()

        assert isinstance(patterns, list)

    def test_generate_recommendations(
        self,
        analyzer: PerformanceAnalyzer,
    ) -> None:
        """测试建议生成."""
        metrics = PerformanceMetrics(
            total_trades=10,
            winning_trades=4,
            losing_trades=6,
            win_rate=0.4,
            total_pnl=-50.0,
            avg_pnl=-5.0,
            max_profit=20.0,
            max_loss=-30.0,
            avg_confidence=0.65,
            avg_edge=0.08,
            performance_level=PerformanceLevel.POOR,
        )

        patterns = [
            PatternInsight(
                pattern_type=PatternType.FAILURE,
                title="Test pattern",
                description="Test description",
                recommendation="Test recommendation",
            )
        ]

        recommendations = analyzer.generate_recommendations(metrics, patterns)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
```

### References

- [Source: architecture.md#Database Schema] - 数据库表定义
- [Source: epics.md#Story 6.5] - 原始 Story 定义
- [Source: src/models/prediction.py] - Prediction 模型定义
- [Source: src/models/trade.py] - Trade 模型定义
- [Source: src/models/position.py] - Position 模型定义
- [Source: src/storage/repositories/prediction_repo.py] - PredictionRepository 实现
- [Source: 6-4-prediction-history-query-api.md] - 前一个故事实现参考
- [Source: 6-3-learning-log-generation.md] - 学习日志格式参考
