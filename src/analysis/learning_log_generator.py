"""Learning log generator for trading reports.

Story 6.3: 学习日志生成

This module provides functionality to generate detailed analysis reports
after each trade and daily summary reports for strategy improvement.

Usage:
    from src.analysis.learning_log_generator import LearningLogGenerator

    generator = LearningLogGenerator(trade_repo, position_repo)
    report = await generator.generate_trade_report(trade, prediction, market)
    daily = await generator.generate_daily_report(date.today())
"""

from __future__ import annotations

__all__ = [
    "MarketSnapshot",
    "PredictionSnapshot",
    "TradeSnapshot",
    "PositionSnapshot",
    "TradeReport",
    "TradingSummary",
    "LearningInsight",
    "DailyReport",
    "LearningLogGenerator",
]

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.utils.logger import OPERATION_EMOJIS, get_logger

if TYPE_CHECKING:
    from src.models.market import Market
    from src.models.position import Position
    from src.models.prediction import Prediction
    from src.models.trade import Trade
    from src.storage.repositories.position_repo import PositionRepository
    from src.storage.repositories.trade_repo import TradeRepository

logger = get_logger(__name__)


# ==================== Data Models ====================


@dataclass
class MarketSnapshot:
    """Market information snapshot for report.

    Attributes:
        id: Market ID
        title: Market title
        description: Market description
        category: Market category
        deadline: Market deadline
        yes_price: Current YES price
        no_price: Current NO price
        liquidity: Market liquidity
    """

    id: str
    title: str
    description: str | None
    category: str | None
    deadline: datetime | None
    yes_price: float | None
    no_price: float | None
    liquidity: float | None


@dataclass
class PredictionSnapshot:
    """LLM prediction snapshot for report.

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
class TradeSnapshot:
    """Trade execution snapshot for report.

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
class PositionSnapshot:
    """Position snapshot for report.

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
        market: Market information snapshot
        prediction: Prediction information snapshot
        trade: Trade execution snapshot
        position: Position snapshot after trade
        price_comparison: Price comparison data
    """

    report_type: str = "trade"
    generated_at: datetime = field(default_factory=datetime.now)
    market: MarketSnapshot | None = None
    prediction: PredictionSnapshot | None = None
    trade: TradeSnapshot | None = None
    position: PositionSnapshot | None = None
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


# ==================== Learning Log Generator ====================


class LearningLogGenerator:
    """Generator for learning logs and trading reports.

    Generates detailed reports for individual trades and daily summaries
    to help with strategy review and improvement.

    Example:
        >>> generator = LearningLogGenerator(trade_repo, position_repo)
        >>> report = await generator.generate_trade_report(
        ...     trade, prediction, market
        ... )
        >>> print(f"Report saved: {report.trade.trade_id}")
    """

    def __init__(
        self,
        trade_repo: TradeRepository,
        position_repo: PositionRepository,
        reports_dir: Path | str | None = None,
    ) -> None:
        """Initialize the learning log generator.

        Args:
            trade_repo: Trade repository for fetching trade data
            position_repo: Position repository for fetching position data
            reports_dir: Directory for storing reports (default: logs/reports/)
        """
        self._trade_repo = trade_repo
        self._position_repo = position_repo
        self._reports_dir = Path(reports_dir) if reports_dir else Path("logs/reports")
        self._ensure_reports_dir()

    def _ensure_reports_dir(self) -> None:
        """Ensure the reports directory exists."""
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def _save_report(self, filename: str, content: dict[str, Any]) -> Path:
        """Save a report to a JSON file.

        Args:
            filename: Name of the file (without path)
            content: Report content as dictionary

        Returns:
            Path to the saved file
        """
        filepath = self._reports_dir / filename
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2, default=str, ensure_ascii=False)
            logger.info(f"{OPERATION_EMOJIS['data']} Report saved: {filepath}")
        except OSError as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to save report {filepath}: {e}"
            )
            raise
        return filepath

    def _market_to_snapshot(self, market: Market) -> MarketSnapshot:
        """Convert Market model to MarketSnapshot dataclass.

        Args:
            market: Market model instance

        Returns:
            MarketSnapshot dataclass instance
        """
        return MarketSnapshot(
            id=market.id,
            title=market.title,
            description=market.description,
            category=market.category.value if market.category else None,
            deadline=market.deadline,
            yes_price=market.yes_price,
            no_price=market.no_price,
            liquidity=market.liquidity,
        )

    def _prediction_to_snapshot(
        self, prediction: Prediction, market_price: float | None
    ) -> PredictionSnapshot:
        """Convert Prediction model to PredictionSnapshot dataclass.

        Args:
            prediction: Prediction model instance
            market_price: Current market price for edge calculation

        Returns:
            PredictionSnapshot dataclass instance
        """
        # Calculate edge if not already set
        edge = prediction.edge
        if edge is None and market_price is not None:
            edge = abs(prediction.predicted_probability - market_price)

        return PredictionSnapshot(
            predicted_probability=prediction.predicted_probability,
            confidence=prediction.confidence,
            edge=edge,
            reasoning=prediction.reasoning,
            key_assumptions=prediction.key_assumptions,
            recommendation=(
                prediction.recommendation.value if prediction.recommendation else None
            ),
        )

    def _trade_to_snapshot(self, trade: Trade) -> TradeSnapshot:
        """Convert Trade model to TradeSnapshot dataclass.

        Args:
            trade: Trade model instance

        Returns:
            TradeSnapshot dataclass instance
        """
        return TradeSnapshot(
            trade_id=trade.id,
            trade_type=trade.trade_type.value,
            mode=trade.mode.value,
            amount=trade.amount,
            price=trade.price,
            shares=trade.shares,
            status=trade.status.value if trade.status else None,
            executed_at=trade.created_at or datetime.now(),
        )

    def _position_to_snapshot(
        self, position: Position | None
    ) -> PositionSnapshot | None:
        """Convert Position model to PositionSnapshot dataclass.

        Args:
            position: Position model instance or None

        Returns:
            PositionSnapshot dataclass instance or None
        """
        if position is None:
            return None

        return PositionSnapshot(
            position_id=position.id,
            outcome=position.outcome.value if position.outcome else None,
            shares=position.shares,
            avg_price=position.avg_price,
            current_value=position.current_value,
            pnl=position.pnl,
        )

    def _report_to_dict(self, report: TradeReport | DailyReport) -> dict[str, Any]:
        """Convert report dataclass to dictionary for JSON serialization.

        Args:
            report: TradeReport or DailyReport instance

        Returns:
            Dictionary representation of the report
        """
        result: dict[str, Any] = {
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
                        if report.market.deadline
                        else None
                    ),
                    "yes_price": report.market.yes_price,
                    "no_price": report.market.no_price,
                    "liquidity": report.market.liquidity,
                }
            if report.prediction:
                result["prediction"] = {
                    "predicted_probability": report.prediction.predicted_probability,
                    "confidence": report.prediction.confidence,
                    "edge": report.prediction.edge,
                    "reasoning": report.prediction.reasoning,
                    "key_assumptions": report.prediction.key_assumptions,
                    "recommendation": report.prediction.recommendation,
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

    async def _get_position_info(self, market_id: str) -> Position | None:
        """Get position information for a market.

        Args:
            market_id: Market identifier

        Returns:
            Position if found, None otherwise
        """
        try:
            position = await self._position_repo.get_by_market(market_id)
            return position
        except Exception as e:
            logger.warning(
                f"{OPERATION_EMOJIS['data']} Failed to get position for "
                f"market {market_id}: {e}"
            )
            return None

    async def generate_trade_report(
        self,
        trade: Trade,
        prediction: Prediction,
        market: Market,
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

        # Determine market price based on trade type
        if trade.trade_type.value == "BUY_YES":
            market_price = market.yes_price
        else:
            market_price = market.no_price

        # Calculate price comparison
        price_comparison: dict[str, Any] = {
            "market_price": market_price,
            "predicted_probability": prediction.predicted_probability,
            "edge": prediction.edge,
            "price_diff": (
                abs(prediction.predicted_probability - (market_price or 0))
                if market_price is not None
                else None
            ),
        }

        # Get position info
        position = await self._get_position_info(market.id)

        # Create report
        report = TradeReport(
            generated_at=datetime.now(),
            market=self._market_to_snapshot(market),
            prediction=self._prediction_to_snapshot(prediction, market_price),
            trade=self._trade_to_snapshot(trade),
            position=self._position_to_snapshot(position),
            price_comparison=price_comparison,
        )

        # Save report
        if trade.id is not None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trade_{trade.id}_{timestamp}.json"
            try:
                self._save_report(filename, self._report_to_dict(report))
            except OSError:
                # Log error but don't fail the report generation
                logger.warning(
                    f"{OPERATION_EMOJIS['data']} Could not save trade report, "
                    "continuing without file persistence"
                )

        return report

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
            f"{OPERATION_EMOJIS['data']} Generating daily report for " f"{report_date}"
        )

        # Get trades for the date
        try:
            trades = await self._trade_repo.get_trades_by_date(report_date)
        except Exception as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to get trades for "
                f"{report_date}: {e}"
            )
            trades = []

        # Calculate summary
        if trades:
            total_volume = sum(t.amount for t in trades)
            trade_ids = [t.id for t in trades if t.id is not None]
            summary = TradingSummary(
                total_trades=len(trades),
                winning_trades=0,  # Requires position close data
                losing_trades=0,  # Requires position close data
                win_rate=None,  # Requires position close data
                total_pnl=0.0,  # Requires position close data
                total_volume=total_volume,
            )
        else:
            trade_ids = []
            summary = TradingSummary(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=None,
                total_pnl=0.0,
                total_volume=0.0,
            )

        # Generate insights
        insights: list[LearningInsight] = []
        if trades:
            insights.append(
                LearningInsight(
                    category="activity",
                    description=f"Executed {len(trades)} trades on {report_date}",
                    related_trades=trade_ids,
                    recommendation=None,
                )
            )

            # Analyze trade patterns
            buy_yes_count = sum(1 for t in trades if t.trade_type.value == "BUY_YES")
            buy_no_count = sum(1 for t in trades if t.trade_type.value == "BUY_NO")

            if buy_yes_count > buy_no_count * 2:
                desc = (
                    f"Strong bullish bias: {buy_yes_count} BUY_YES "
                    f"vs {buy_no_count} BUY_NO"
                )
                insights.append(
                    LearningInsight(
                        category="pattern",
                        description=desc,
                        related_trades=trade_ids,
                        recommendation=(
                            "Review if bullish bias aligns with market conditions"
                        ),
                    )
                )
            elif buy_no_count > buy_yes_count * 2:
                desc = (
                    f"Strong bearish bias: {buy_no_count} BUY_NO "
                    f"vs {buy_yes_count} BUY_YES"
                )
                insights.append(
                    LearningInsight(
                        category="pattern",
                        description=desc,
                        related_trades=trade_ids,
                        recommendation=(
                            "Review if bearish bias aligns with market conditions"
                        ),
                    )
                )

            # Volume insight
            avg_trade_size = total_volume / len(trades)
            insights.append(
                LearningInsight(
                    category="volume",
                    description=f"Average trade size: ${avg_trade_size:.2f}",
                    related_trades=trade_ids,
                    recommendation=None,
                )
            )
        else:
            insights.append(
                LearningInsight(
                    category="activity",
                    description=f"No trades executed on {report_date}",
                    related_trades=[],
                    recommendation="Review market conditions and strategy parameters",
                )
            )

        # Create report
        report = DailyReport(
            report_date=report_date,
            generated_at=datetime.now(),
            summary=summary,
            trades=trade_ids,
            insights=insights,
        )

        # Save report
        filename = f"daily_{report_date.isoformat()}.json"
        try:
            self._save_report(filename, self._report_to_dict(report))
        except OSError:
            # Log error but don't fail the report generation
            logger.warning(
                f"{OPERATION_EMOJIS['data']} Could not save daily report, "
                "continuing without file persistence"
            )

        return report
