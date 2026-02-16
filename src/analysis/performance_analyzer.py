"""Performance Analyzer Module.

Story 6.5: 表现分析与洞察

This module provides performance analysis and insight generation
for trading strategy optimization.

Usage:
    from src.analysis.performance_analyzer import PerformanceAnalyzer

    analyzer = PerformanceAnalyzer(prediction_repo, trade_repo, position_repo)
    report = await analyzer.generate_insight_report()
    print(f"Win rate: {report.metrics.win_rate:.1%}")
"""

from __future__ import annotations

__all__ = [
    "PerformanceLevel",
    "PatternType",
    "SuggestionPriority",
    "PerformanceMetrics",
    "CategoryPerformance",
    "ConfidenceAnalysis",
    "EdgeAnalysis",
    "PatternInsight",
    "ImprovementSuggestion",
    "PerformanceInsightReport",
    "PerformanceAnalyzer",
]

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.models.market import Market
    from src.models.prediction import Prediction
    from src.storage.repositories.position_repo import PositionRepository
    from src.storage.repositories.prediction_repo import PredictionRepository
    from src.storage.repositories.trade_repo import TradeRepository

logger = get_logger(__name__)


# Emoji for performance analysis logging
ANALYSIS_EMOJI = "\U0001f9e0"  # Brain emoji


class PerformanceLevel(str, Enum):
    """Performance level classification.

    Attributes:
        EXCELLENT: Win rate >= 70%
        GOOD: Win rate >= 55%
        AVERAGE: Win rate >= 45%
        POOR: Win rate < 45%
    """

    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"


class PatternType(str, Enum):
    """Type of identified pattern.

    Attributes:
        SUCCESS: Pattern indicating successful trades
        FAILURE: Pattern indicating failed trades
        NEUTRAL: Neutral pattern
    """

    SUCCESS = "success"
    FAILURE = "failure"
    NEUTRAL = "neutral"


class SuggestionPriority(str, Enum):
    """Priority level for improvement suggestions.

    Attributes:
        HIGH: High priority, should address immediately
        MEDIUM: Medium priority, should address soon
        LOW: Low priority, nice to have
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


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
        analysis_period: Period of analysis (start_date, end_date)
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
class ImprovementSuggestion:
    """Improvement suggestion with priority.

    Attributes:
        category: Category of improvement (risk, strategy, confidence, etc.)
        priority: Priority level (high/medium/low)
        title: Short title for the suggestion
        description: Detailed description
        action: Concrete action to take
    """

    category: str
    priority: SuggestionPriority
    title: str
    description: str
    action: str


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
        recommendations: List of recommendation strings
        suggestions: List of improvement suggestions
    """

    generated_at: datetime
    metrics: PerformanceMetrics
    category_performance: list[CategoryPerformance]
    confidence_analysis: list[ConfidenceAnalysis]
    edge_analysis: list[EdgeAnalysis]
    patterns: list[PatternInsight]
    recommendations: list[str]
    suggestions: list[ImprovementSuggestion] = field(default_factory=list)


class PerformanceAnalyzer:
    """Analyzer for trading performance and strategy insights.

    This class provides methods to analyze trading performance,
    identify patterns, and generate recommendations for improvement.

    Example:
        >>> analyzer = PerformanceAnalyzer(
        ...     prediction_repo, trade_repo, position_repo
        ... )
        >>> report = await analyzer.generate_insight_report()
        >>> print(f"Win rate: {report.metrics.win_rate:.1%}")
        Win rate: 62.5%
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
        predictions_with_markets = (
            await self._prediction_repo.get_validated_with_market()
        )

        # Get all trades (using paper trades for analysis)
        from src.models.trade import TradeMode

        trades = await self._trade_repo.get_by_mode(TradeMode.PAPER)

        # Get closed positions for PnL
        positions = await self._position_repo.get_open_positions()
        closed_positions = [p for p in positions if p.status.value == "CLOSED"]

        # Calculate trade-based metrics
        total_trades = len(trades)

        # Calculate PnL from positions
        winning_trades = sum(1 for p in closed_positions if p.pnl and p.pnl > 0)
        losing_trades = sum(1 for p in closed_positions if p.pnl and p.pnl < 0)

        total_pnl = sum(p.pnl or 0 for p in closed_positions)
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0.0

        max_profit = max((p.pnl or 0 for p in closed_positions), default=0.0)
        max_loss = min((p.pnl or 0 for p in closed_positions), default=0.0)

        # Calculate win rate from predictions
        validated = [p for p, _ in predictions_with_markets if p.is_correct is not None]
        if validated:
            correct_predictions = sum(1 for p in validated if p.is_correct)
            win_rate = correct_predictions / len(validated)
            winning_trades = correct_predictions
            losing_trades = len(validated) - correct_predictions
        else:
            win_rate = 0.0

        # Calculate average confidence and edge
        avg_confidence = (
            sum(p.confidence for p in validated) / len(validated) if validated else 0.0
        )
        avg_edge = (
            sum(p.edge or 0 for p in validated) / len(validated) if validated else 0.0
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
            total_trades=len(validated) if validated else total_trades,
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

    async def get_best_performing_categories(
        self, limit: int = 3
    ) -> list[CategoryPerformance]:
        """Get the best performing market categories.

        Args:
            limit: Maximum number of categories to return

        Returns:
            List of CategoryPerformance sorted by win rate (descending)

        Example:
            >>> best = await analyzer.get_best_performing_categories()
            >>> print(best[0].category)
            politics
        """
        logger.info(f"{ANALYSIS_EMOJI} Getting best performing categories...")

        all_categories = await self._get_category_performance()

        # Sort by win rate descending, then by total trades descending
        sorted_categories = sorted(
            all_categories,
            key=lambda x: (x.win_rate, x.total_trades),
            reverse=True,
        )

        # Filter to only categories with meaningful data
        meaningful = [c for c in sorted_categories if c.total_trades >= 2]

        return meaningful[:limit]

    async def get_worst_performing_categories(
        self, limit: int = 3
    ) -> list[CategoryPerformance]:
        """Get the worst performing market categories.

        Args:
            limit: Maximum number of categories to return

        Returns:
            List of CategoryPerformance sorted by win rate (ascending)

        Example:
            >>> worst = await analyzer.get_worst_performing_categories()
            >>> print(worst[0].category)
            crypto
        """
        logger.info(f"{ANALYSIS_EMOJI} Getting worst performing categories...")

        all_categories = await self._get_category_performance()

        # Sort by win rate ascending, then by total trades descending
        sorted_categories = sorted(
            all_categories,
            key=lambda x: (x.win_rate, -x.total_trades),
        )

        # Filter to only categories with meaningful data
        meaningful = [c for c in sorted_categories if c.total_trades >= 2]

        return meaningful[:limit]

    async def _get_category_performance(self) -> list[CategoryPerformance]:
        """Get performance metrics for all categories.

        Returns:
            List of CategoryPerformance for all categories
        """
        predictions_with_markets = (
            await self._prediction_repo.get_validated_with_market()
        )

        # Group by category
        category_stats: dict[str, dict] = defaultdict(
            lambda: {"total": 0, "correct": 0, "pnl": 0.0, "confidence": 0.0}
        )

        for pred, market in predictions_with_markets:
            if pred.is_correct is None:
                continue

            category = market.category.value if market.category else "unknown"
            stats = category_stats[category]
            stats["total"] += 1
            if pred.is_correct:
                stats["correct"] += 1
            stats["confidence"] += pred.confidence

        # Build CategoryPerformance list
        results: list[CategoryPerformance] = []
        for category, stats in category_stats.items():
            total = stats["total"]
            if total == 0:
                continue

            results.append(
                CategoryPerformance(
                    category=category,
                    total_trades=total,
                    winning_trades=stats["correct"],
                    win_rate=stats["correct"] / total,
                    total_pnl=stats["pnl"],
                    avg_pnl=stats["pnl"] / total if total > 0 else 0.0,
                    avg_confidence=stats["confidence"] / total if total > 0 else 0.0,
                )
            )

        return results

    async def get_confidence_accuracy_correlation(self) -> list[ConfidenceAnalysis]:
        """Get accuracy statistics grouped by confidence ranges.

        Confidence ranges:
        - 0.8-1.0: High confidence (>= 0.8)
        - 0.75-0.8: Medium-high confidence
        - < 0.75: Low confidence

        Returns:
            List of ConfidenceAnalysis for each confidence range

        Example:
            >>> correlation = await analyzer.get_confidence_accuracy_correlation()
            >>> print(correlation[0].accuracy)
            0.75
        """
        logger.info(f"{ANALYSIS_EMOJI} Analyzing confidence-accuracy correlation...")

        predictions_with_markets = (
            await self._prediction_repo.get_validated_with_market()
        )

        # Define confidence ranges
        ranges = [
            ("0.8-1.0", 0.8, 1.01),  # High confidence
            ("0.75-0.8", 0.75, 0.8),  # Medium-high confidence
            ("< 0.75", 0.0, 0.75),  # Low confidence
        ]

        results: list[ConfidenceAnalysis] = []
        for label, min_c, max_c in ranges:
            items = [
                (p, m)
                for p, m in predictions_with_markets
                if min_c <= p.confidence < max_c and p.is_correct is not None
            ]

            if not items:
                continue

            correct = sum(1 for p, _ in items if p.is_correct)
            results.append(
                ConfidenceAnalysis(
                    confidence_range=label,
                    min_confidence=min_c,
                    max_confidence=min(max_c, 1.0),
                    sample_size=len(items),
                    accuracy=correct / len(items),
                    avg_pnl=0.0,  # Would need position data join
                )
            )

        logger.info(
            f"{ANALYSIS_EMOJI} Confidence-accuracy correlation: "
            f"{len(results)} ranges analyzed"
        )

        return results

    async def get_edge_success_correlation(self) -> list[EdgeAnalysis]:
        """Get success statistics grouped by edge ranges.

        Edge ranges:
        - >= 0.2: High edge
        - 0.1-0.2: Medium edge
        - < 0.1: Low edge

        Returns:
            List of EdgeAnalysis for each edge range

        Example:
            >>> correlation = await analyzer.get_edge_success_correlation()
            >>> print(correlation[0].success_rate)
            0.80
        """
        logger.info(f"{ANALYSIS_EMOJI} Analyzing edge-success correlation...")

        predictions_with_markets = (
            await self._prediction_repo.get_validated_with_market()
        )

        # Define edge ranges
        ranges = [
            (">= 0.2", 0.2, 1.01),  # High edge
            ("0.1-0.2", 0.1, 0.2),  # Medium edge
            ("< 0.1", 0.0, 0.1),  # Low edge
        ]

        results: list[EdgeAnalysis] = []
        for label, min_e, max_e in ranges:
            items = [
                (p, m)
                for p, m in predictions_with_markets
                if p.edge is not None
                and min_e <= p.edge < max_e
                and p.is_correct is not None
            ]

            if not items:
                continue

            correct = sum(1 for p, _ in items if p.is_correct)
            results.append(
                EdgeAnalysis(
                    edge_range=label,
                    min_edge=min_e,
                    max_edge=min(max_e, 1.0),
                    sample_size=len(items),
                    success_rate=correct / len(items),
                    avg_return=0.0,  # Would need position data join
                )
            )

        logger.info(
            f"{ANALYSIS_EMOJI} Edge-success correlation: "
            f"{len(results)} ranges analyzed"
        )

        return results

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
        predictions_with_markets = (
            await self._prediction_repo.get_validated_with_market()
        )

        if not predictions_with_markets:
            logger.info(
                f"{ANALYSIS_EMOJI} No data available for pattern identification"
            )
            return patterns

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
                    patterns.append(
                        PatternInsight(
                            pattern_type=PatternType.SUCCESS,
                            title=f"Strong performance in {category}",
                            description=f"{rate:.0%} accuracy in {category} markets ({correct}/{total})",
                            examples=[m.title for _, m in items[:3]],
                            recommendation=f"Consider focusing more on {category} markets",
                        )
                    )
                elif rate < 0.4:
                    patterns.append(
                        PatternInsight(
                            pattern_type=PatternType.FAILURE,
                            title=f"Struggling in {category}",
                            description=f"Only {rate:.0%} accuracy in {category} markets ({correct}/{total})",
                            examples=[m.title for _, m in items[:3]],
                            recommendation=f"Consider avoiding {category} markets or refining analysis",
                        )
                    )

        # Analyze confidence vs accuracy
        high_conf_items = [
            (p, m)
            for p, m in predictions_with_markets
            if p.confidence >= 0.8 and p.is_correct is not None
        ]
        if high_conf_items:
            high_conf_correct = sum(1 for p, _ in high_conf_items if p.is_correct)
            high_conf_rate = high_conf_correct / len(high_conf_items)
            patterns.append(
                PatternInsight(
                    pattern_type=(
                        PatternType.SUCCESS
                        if high_conf_rate >= 0.7
                        else PatternType.FAILURE
                    ),
                    title="High confidence prediction accuracy",
                    description=f"Predictions with >= 80% confidence have {high_conf_rate:.0%} accuracy",
                    recommendation=(
                        "Trust high confidence predictions"
                        if high_conf_rate >= 0.7
                        else "Re-evaluate confidence calibration"
                    ),
                )
            )

        # Analyze low confidence predictions
        low_conf_items = [
            (p, m)
            for p, m in predictions_with_markets
            if p.confidence < 0.75 and p.is_correct is not None
        ]
        if low_conf_items:
            low_conf_correct = sum(1 for p, _ in low_conf_items if p.is_correct)
            low_conf_rate = low_conf_correct / len(low_conf_items)
            if low_conf_rate < 0.5:
                patterns.append(
                    PatternInsight(
                        pattern_type=PatternType.FAILURE,
                        title="Low confidence predictions underperforming",
                        description=f"Predictions with < 75% confidence have only {low_conf_rate:.0%} accuracy",
                        recommendation="Consider skipping trades with confidence below 75%",
                    )
                )

        # Analyze edge vs success
        high_edge_items = [
            (p, m)
            for p, m in predictions_with_markets
            if p.edge is not None and p.edge >= 0.2 and p.is_correct is not None
        ]
        if high_edge_items:
            high_edge_correct = sum(1 for p, _ in high_edge_items if p.is_correct)
            high_edge_rate = high_edge_correct / len(high_edge_items)
            patterns.append(
                PatternInsight(
                    pattern_type=(
                        PatternType.SUCCESS
                        if high_edge_rate >= 0.6
                        else PatternType.NEUTRAL
                    ),
                    title="High edge predictions performance",
                    description=f"Predictions with >= 20% edge have {high_edge_rate:.0%} success rate",
                    recommendation=(
                        "Prioritize high edge opportunities"
                        if high_edge_rate >= 0.6
                        else "High edge doesn't guarantee success - review edge calculation"
                    ),
                )
            )

        logger.info(f"{ANALYSIS_EMOJI} Identified {len(patterns)} patterns")
        return patterns

    def generate_insights(
        self,
        metrics: PerformanceMetrics,
        patterns: list[PatternInsight],
        category_performance: list[CategoryPerformance],
        confidence_analysis: list[ConfidenceAnalysis],
        edge_analysis: list[EdgeAnalysis],
    ) -> list[str]:
        """Generate insight descriptions based on analysis results.

        Args:
            metrics: Performance metrics
            patterns: Identified patterns
            category_performance: Performance by category
            confidence_analysis: Confidence analysis results
            edge_analysis: Edge analysis results

        Returns:
            List of insight description strings

        Example:
            >>> insights = analyzer.generate_insights(metrics, patterns, [], [], [])
            >>> for insight in insights:
            ...     print(f"- {insight}")
            - Overall win rate of 65% indicates good performance
        """
        logger.info(f"{ANALYSIS_EMOJI} Generating insights...")

        insights: list[str] = []

        # Overall performance insight
        if metrics.total_trades > 0:
            level_desc = {
                PerformanceLevel.EXCELLENT: "excellent",
                PerformanceLevel.GOOD: "good",
                PerformanceLevel.AVERAGE: "average",
                PerformanceLevel.POOR: "needs improvement",
            }
            insights.append(
                f"Overall win rate of {metrics.win_rate:.1%} indicates {level_desc[metrics.performance_level]} performance"
            )
        else:
            insights.append("No validated trades available for analysis")

        # Confidence calibration insight
        if confidence_analysis:
            high_conf = next(
                (c for c in confidence_analysis if c.confidence_range == "0.8-1.0"),
                None,
            )
            if high_conf and high_conf.sample_size >= 5:
                if high_conf.accuracy >= 0.7:
                    insights.append(
                        f"High confidence predictions (>= 80%) are well-calibrated "
                        f"with {high_conf.accuracy:.1%} accuracy"
                    )
                else:
                    insights.append(
                        f"High confidence predictions are underperforming "
                        f"({high_conf.accuracy:.1%} accuracy) - consider recalibrating confidence"
                    )

        # Edge effectiveness insight
        if edge_analysis:
            high_edge = next(
                (e for e in edge_analysis if e.edge_range == ">= 0.2"), None
            )
            if high_edge and high_edge.sample_size >= 3:
                if high_edge.success_rate >= 0.6:
                    insights.append(
                        f"High edge trades (>= 20%) show {high_edge.success_rate:.1%} "
                        f"success rate - edge calculation is effective"
                    )
                else:
                    insights.append(
                        f"High edge trades show only {high_edge.success_rate:.1%} "
                        f"success - edge calculation may need refinement"
                    )

        # Category insights
        if category_performance:
            best = max(category_performance, key=lambda x: x.win_rate)
            worst = min(category_performance, key=lambda x: x.win_rate)
            if best.total_trades >= 3:
                insights.append(
                    f"Best performing category: {best.category} ({best.win_rate:.1%} win rate)"
                )
            if worst.total_trades >= 3 and worst.win_rate < 0.5:
                insights.append(
                    f"Needs attention: {worst.category} category has {worst.win_rate:.1%} win rate"
                )

        # Pattern-based insights
        for pattern in patterns:
            if pattern.pattern_type == PatternType.SUCCESS:
                insights.append(f"Success pattern: {pattern.description}")
            elif pattern.pattern_type == PatternType.FAILURE:
                insights.append(f"Warning: {pattern.description}")

        logger.info(f"{ANALYSIS_EMOJI} Generated {len(insights)} insights")
        return insights

    def get_improvement_suggestions(
        self,
        metrics: PerformanceMetrics,
        patterns: list[PatternInsight],
        category_performance: list[CategoryPerformance],
        confidence_analysis: list[ConfidenceAnalysis],
        edge_analysis: list[EdgeAnalysis],
    ) -> list[ImprovementSuggestion]:
        """Generate improvement suggestions based on analysis.

        Args:
            metrics: Performance metrics
            patterns: Identified patterns
            category_performance: Performance by category
            confidence_analysis: Confidence analysis results
            edge_analysis: Edge analysis results

        Returns:
            List of ImprovementSuggestion with prioritized actions

        Example:
            >>> suggestions = analyzer.get_improvement_suggestions(metrics, patterns, [], [], [])
            >>> for s in suggestions:
            ...     print(f"[{s.priority}] {s.title}")
            [high] Improve win rate
        """
        logger.info(f"{ANALYSIS_EMOJI} Generating improvement suggestions...")

        suggestions: list[ImprovementSuggestion] = []

        # Based on overall performance
        if metrics.win_rate < 0.5 and metrics.total_trades >= 5:
            suggestions.append(
                ImprovementSuggestion(
                    category="strategy",
                    priority=SuggestionPriority.HIGH,
                    title="Improve win rate",
                    description=f"Current win rate of {metrics.win_rate:.1%} is below 50%",
                    action="Review recent losing trades to identify common issues",
                )
            )

        if metrics.avg_confidence < 0.7:
            suggestions.append(
                ImprovementSuggestion(
                    category="confidence",
                    priority=SuggestionPriority.MEDIUM,
                    title="Increase prediction confidence",
                    description=f"Average confidence is {metrics.avg_confidence:.1%}",
                    action="Focus on markets with clearer signals and stronger analysis",
                )
            )

        if metrics.avg_edge < 0.1:
            suggestions.append(
                ImprovementSuggestion(
                    category="edge",
                    priority=SuggestionPriority.MEDIUM,
                    title="Focus on higher edge opportunities",
                    description=f"Average edge is {metrics.avg_edge:.1%}",
                    action="Set minimum edge threshold at 10% for trade entry",
                )
            )

        # Risk management suggestions
        if abs(metrics.max_loss) > metrics.max_profit * 2:
            suggestions.append(
                ImprovementSuggestion(
                    category="risk",
                    priority=SuggestionPriority.HIGH,
                    title="Review risk management",
                    description=f"Max loss (${abs(metrics.max_loss):.2f}) exceeds max profit (${metrics.max_profit:.2f}) by 2x",
                    action="Implement stop-loss rules or reduce position sizes",
                )
            )

        # Category-based suggestions
        for cat_perf in category_performance:
            if cat_perf.total_trades >= 3 and cat_perf.win_rate < 0.4:
                suggestions.append(
                    ImprovementSuggestion(
                        category="category",
                        priority=SuggestionPriority.MEDIUM,
                        title=f"Improve {cat_perf.category} performance",
                        description=f"{cat_perf.category} has {cat_perf.win_rate:.1%} win rate",
                        action=f"Consider avoiding {cat_perf.category} markets or refine analysis approach",
                    )
                )

        # Confidence-based suggestions
        low_conf = next(
            (c for c in confidence_analysis if c.confidence_range == "< 0.75"), None
        )
        if low_conf and low_conf.sample_size >= 3 and low_conf.accuracy < 0.5:
            suggestions.append(
                ImprovementSuggestion(
                    category="confidence",
                    priority=SuggestionPriority.MEDIUM,
                    title="Filter low confidence predictions",
                    description=f"Low confidence predictions have {low_conf.accuracy:.1%} accuracy",
                    action="Consider skipping trades with confidence below 75%",
                )
            )

        # Edge-based suggestions
        low_edge = next((e for e in edge_analysis if e.edge_range == "< 0.1"), None)
        if low_edge and low_edge.sample_size >= 3 and low_edge.success_rate < 0.5:
            suggestions.append(
                ImprovementSuggestion(
                    category="edge",
                    priority=SuggestionPriority.MEDIUM,
                    title="Avoid low edge trades",
                    description=f"Low edge trades have {low_edge.success_rate:.1%} success rate",
                    action="Set minimum edge threshold at 10% for trade entry",
                )
            )

        # Pattern-based suggestions
        for pattern in patterns:
            if pattern.pattern_type == PatternType.FAILURE and pattern.recommendation:
                suggestions.append(
                    ImprovementSuggestion(
                        category="pattern",
                        priority=SuggestionPriority.LOW,
                        title=f"Address: {pattern.title}",
                        description=pattern.description,
                        action=pattern.recommendation,
                    )
                )

        logger.info(
            f"{ANALYSIS_EMOJI} Generated {len(suggestions)} improvement suggestions"
        )
        return suggestions

    def generate_recommendations(
        self,
        metrics: PerformanceMetrics,
        patterns: list[PatternInsight],
        suggestions: list[ImprovementSuggestion] | None = None,
    ) -> list[str]:
        """Generate improvement recommendations.

        Args:
            metrics: Performance metrics
            patterns: Identified patterns
            suggestions: Optional list of improvement suggestions

        Returns:
            List of recommendation strings

        Example:
            >>> recommendations = analyzer.generate_recommendations(metrics, patterns)
            >>> for r in recommendations:
            ...     print(f"- {r}")
            - Focus on high-confidence predictions
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

        # Based on suggestions if provided
        if suggestions:
            for suggestion in suggestions:
                if suggestion.priority == SuggestionPriority.HIGH:
                    recommendations.append(suggestion.action)

        # Remove duplicates while preserving order
        seen: set[str] = set()
        unique_recommendations: list[str] = []
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
        category_performance = await self._get_category_performance()
        confidence_analysis = await self.get_confidence_accuracy_correlation()
        edge_analysis = await self.get_edge_success_correlation()

        # Generate suggestions and recommendations
        suggestions = self.get_improvement_suggestions(
            metrics, patterns, category_performance, confidence_analysis, edge_analysis
        )
        recommendations = self.generate_recommendations(metrics, patterns, suggestions)

        # Create report
        report = PerformanceInsightReport(
            generated_at=datetime.now(),
            metrics=metrics,
            category_performance=category_performance,
            confidence_analysis=confidence_analysis,
            edge_analysis=edge_analysis,
            patterns=patterns,
            recommendations=recommendations,
            suggestions=suggestions,
        )

        # Save report to file
        report_filename = f"insights_{datetime.now().strftime('%Y-%m-%d')}.json"
        report_path = self._reports_dir / report_filename

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(self._report_to_dict(report), f, indent=2, ensure_ascii=False)
            logger.info(f"{ANALYSIS_EMOJI} Insight report saved to {report_path}")
        except OSError as e:
            logger.warning(
                f"{ANALYSIS_EMOJI} Could not save report to {report_path}: {e}"
            )

        logger.info(
            f"{ANALYSIS_EMOJI} 表现分析完成: "
            f"win_rate={metrics.win_rate:.1%}, "
            f"patterns={len(patterns)}, "
            f"recommendations={len(recommendations)}"
        )

        return report

    def _report_to_dict(self, report: PerformanceInsightReport) -> dict:
        """Convert report to dictionary for JSON serialization.

        Args:
            report: PerformanceInsightReport to convert

        Returns:
            Dictionary representation of the report
        """
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
                "analysis_period": [
                    (
                        report.metrics.analysis_period[0].isoformat()
                        if report.metrics.analysis_period[0]
                        else None
                    ),
                    (
                        report.metrics.analysis_period[1].isoformat()
                        if report.metrics.analysis_period[1]
                        else None
                    ),
                ],
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
            "suggestions": [
                {
                    "category": s.category,
                    "priority": s.priority.value,
                    "title": s.title,
                    "description": s.description,
                    "action": s.action,
                }
                for s in report.suggestions
            ],
        }
