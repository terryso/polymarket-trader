"""Tests for LearningLogGenerator.

Story 6.3: 学习日志生成
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.analysis.learning_log_generator import (
    DailyReport,
    LearningInsight,
    LearningLogGenerator,
    MarketSnapshot,
    PositionSnapshot,
    PredictionSnapshot,
    TradeReport,
    TradeSnapshot,
    TradingSummary,
)
from src.models.market import Market, MarketCategory
from src.models.position import Position, PositionOutcome, PositionStatus
from src.models.prediction import Prediction, Recommendation
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType


# ==================== Dataclass Tests ====================


class TestMarketSnapshot:
    """Tests for MarketSnapshot dataclass."""

    def test_market_snapshot_creation(self) -> None:
        """Test MarketSnapshot creation with all fields."""
        snapshot = MarketSnapshot(
            id="market-1",
            title="Will X happen?",
            description="A test market",
            category="politics",
            deadline=datetime(2026, 3, 1),
            yes_price=0.55,
            no_price=0.45,
            liquidity=10000.0,
        )

        assert snapshot.id == "market-1"
        assert snapshot.title == "Will X happen?"
        assert snapshot.description == "A test market"
        assert snapshot.category == "politics"
        assert snapshot.yes_price == 0.55


class TestPredictionSnapshot:
    """Tests for PredictionSnapshot dataclass."""

    def test_prediction_snapshot_creation(self) -> None:
        """Test PredictionSnapshot creation with all fields."""
        snapshot = PredictionSnapshot(
            predicted_probability=0.75,
            confidence=0.85,
            edge=0.20,
            reasoning="Strong indicators",
            key_assumptions=["Trend continues"],
            recommendation="BUY_YES",
        )

        assert snapshot.predicted_probability == 0.75
        assert snapshot.confidence == 0.85
        assert snapshot.edge == 0.20
        assert snapshot.reasoning == "Strong indicators"


class TestTradeSnapshot:
    """Tests for TradeSnapshot dataclass."""

    def test_trade_snapshot_creation(self) -> None:
        """Test TradeSnapshot creation with all fields."""
        snapshot = TradeSnapshot(
            trade_id=1,
            trade_type="BUY_YES",
            mode="PAPER",
            amount=100.0,
            price=0.55,
            shares=181.81,
            status="FILLED",
            executed_at=datetime(2026, 2, 16, 10, 30, 0),
        )

        assert snapshot.trade_id == 1
        assert snapshot.trade_type == "BUY_YES"
        assert snapshot.amount == 100.0


class TestPositionSnapshot:
    """Tests for PositionSnapshot dataclass."""

    def test_position_snapshot_creation(self) -> None:
        """Test PositionSnapshot creation with all fields."""
        snapshot = PositionSnapshot(
            position_id=1,
            outcome="YES",
            shares=181.81,
            avg_price=0.55,
            current_value=100.0,
            pnl=10.0,
        )

        assert snapshot.position_id == 1
        assert snapshot.outcome == "YES"
        assert snapshot.pnl == 10.0

    def test_position_snapshot_none(self) -> None:
        """Test PositionSnapshot can be None."""
        snapshot = None
        assert snapshot is None


class TestTradeReport:
    """Tests for TradeReport dataclass."""

    def test_trade_report_creation(self) -> None:
        """Test TradeReport creation with all fields."""
        market = MarketSnapshot(
            id="market-1",
            title="Test",
            description=None,
            category=None,
            deadline=None,
            yes_price=0.5,
            no_price=0.5,
            liquidity=None,
        )
        prediction = PredictionSnapshot(
            predicted_probability=0.7,
            confidence=0.8,
            edge=None,
            reasoning=None,
            key_assumptions=None,
            recommendation=None,
        )
        trade = TradeSnapshot(
            trade_id=1,
            trade_type="BUY_YES",
            mode="PAPER",
            amount=10.0,
            price=0.5,
            shares=20.0,
            status="FILLED",
            executed_at=datetime.now(),
        )

        report = TradeReport(
            generated_at=datetime.now(),
            market=market,
            prediction=prediction,
            trade=trade,
            position=None,
            price_comparison={"edge": 0.2},
        )

        assert report.report_type == "trade"
        assert report.market is not None
        assert report.market.title == "Test"


class TestTradingSummary:
    """Tests for TradingSummary dataclass."""

    def test_trading_summary_creation(self) -> None:
        """Test TradingSummary creation."""
        summary = TradingSummary(
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=0.6,
            total_pnl=50.0,
            total_volume=1000.0,
        )

        assert summary.total_trades == 10
        assert summary.win_rate == 0.6

    def test_trading_summary_no_trades(self) -> None:
        """Test TradingSummary with no trades."""
        summary = TradingSummary(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=None,
            total_pnl=0.0,
            total_volume=0.0,
        )

        assert summary.total_trades == 0
        assert summary.win_rate is None


class TestLearningInsight:
    """Tests for LearningInsight dataclass."""

    def test_learning_insight_creation(self) -> None:
        """Test LearningInsight creation."""
        insight = LearningInsight(
            category="pattern",
            description="Bullish bias detected",
            related_trades=[1, 2, 3],
            recommendation="Review market conditions",
        )

        assert insight.category == "pattern"
        assert insight.description == "Bullish bias detected"
        assert insight.related_trades == [1, 2, 3]


class TestDailyReport:
    """Tests for DailyReport dataclass."""

    def test_daily_report_creation(self) -> None:
        """Test DailyReport creation."""
        summary = TradingSummary(
            total_trades=5,
            winning_trades=3,
            losing_trades=2,
            win_rate=0.6,
            total_pnl=25.0,
            total_volume=500.0,
        )
        insight = LearningInsight(
            category="activity",
            description="5 trades executed",
            related_trades=[1, 2, 3, 4, 5],
            recommendation=None,
        )

        report = DailyReport(
            report_date=date(2026, 2, 16),
            generated_at=datetime.now(),
            summary=summary,
            trades=[1, 2, 3, 4, 5],
            insights=[insight],
        )

        assert report.report_type == "daily"
        assert report.report_date == date(2026, 2, 16)
        assert report.summary is not None
        assert report.summary.total_trades == 5


# ==================== LearningLogGenerator Tests ====================


class TestLearningLogGenerator:
    """Tests for LearningLogGenerator class."""

    @pytest.fixture
    def temp_reports_dir(self, tmp_path: Path) -> Path:
        """Create a temporary reports directory."""
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        return reports_dir

    @pytest.fixture
    def mock_trade_repo(self) -> AsyncMock:
        """Create a mock TradeRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_position_repo(self) -> AsyncMock:
        """Create a mock PositionRepository."""
        return AsyncMock()

    @pytest.fixture
    def generator(
        self,
        mock_trade_repo: AsyncMock,
        mock_position_repo: AsyncMock,
        temp_reports_dir: Path,
    ) -> LearningLogGenerator:
        """Create a LearningLogGenerator instance."""
        return LearningLogGenerator(
            trade_repo=mock_trade_repo,
            position_repo=mock_position_repo,
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
            amount=100.0,
            price=0.55,
            shares=181.81,
            status=TradeStatus.FILLED,
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
            liquidity=50000.0,
            deadline=datetime(2026, 3, 1),
        )

    @pytest.fixture
    def sample_position(self) -> Position:
        """Create a sample position."""
        return Position(
            id=1,
            market_id="market-1",
            outcome=PositionOutcome.YES,
            shares=181.81,
            avg_price=0.55,
            initial_value=100.0,
            current_value=136.36,
            pnl=36.36,
            status=PositionStatus.OPEN,
        )

    # ==================== generate_trade_report tests ====================

    @pytest.mark.asyncio
    async def test_generate_trade_report(
        self,
        generator: LearningLogGenerator,
        sample_trade: Trade,
        sample_prediction: Prediction,
        sample_market: Market,
        mock_position_repo: AsyncMock,
    ) -> None:
        """Test generating a trade report."""
        mock_position_repo.get_by_market = AsyncMock(return_value=None)

        report = await generator.generate_trade_report(
            sample_trade, sample_prediction, sample_market
        )

        assert report.report_type == "trade"
        assert report.market is not None
        assert report.market.title == "Will X happen by Y date?"
        assert report.prediction is not None
        assert report.prediction.confidence == 0.85
        assert report.trade is not None
        assert report.trade.trade_type == "BUY_YES"

    @pytest.mark.asyncio
    async def test_generate_trade_report_with_position(
        self,
        generator: LearningLogGenerator,
        sample_trade: Trade,
        sample_prediction: Prediction,
        sample_market: Market,
        sample_position: Position,
        mock_position_repo: AsyncMock,
    ) -> None:
        """Test generating a trade report with position info."""
        mock_position_repo.get_by_market = AsyncMock(return_value=sample_position)

        report = await generator.generate_trade_report(
            sample_trade, sample_prediction, sample_market
        )

        assert report.position is not None
        assert report.position.pnl == 36.36

    @pytest.mark.asyncio
    async def test_generate_trade_report_saves_file(
        self,
        generator: LearningLogGenerator,
        sample_trade: Trade,
        sample_prediction: Prediction,
        sample_market: Market,
        mock_position_repo: AsyncMock,
        temp_reports_dir: Path,
    ) -> None:
        """Test that trade report is saved to file."""
        mock_position_repo.get_by_market = AsyncMock(return_value=None)

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
    async def test_generate_trade_report_price_comparison(
        self,
        generator: LearningLogGenerator,
        sample_trade: Trade,
        sample_prediction: Prediction,
        sample_market: Market,
        mock_position_repo: AsyncMock,
    ) -> None:
        """Test price comparison in trade report."""
        mock_position_repo.get_by_market = AsyncMock(return_value=None)

        report = await generator.generate_trade_report(
            sample_trade, sample_prediction, sample_market
        )

        assert report.price_comparison is not None
        assert report.price_comparison["market_price"] == 0.55
        assert report.price_comparison["predicted_probability"] == 0.75
        assert report.price_comparison["edge"] == 0.20

    @pytest.mark.asyncio
    async def test_generate_trade_report_buy_no(
        self,
        generator: LearningLogGenerator,
        sample_prediction: Prediction,
        sample_market: Market,
        mock_position_repo: AsyncMock,
    ) -> None:
        """Test trade report for BUY_NO trade type."""
        trade = Trade(
            id=2,
            market_id="market-1",
            trade_type=TradeType.BUY_NO,
            mode=TradeMode.PAPER,
            amount=50.0,
            price=0.45,
            shares=111.11,
            status=TradeStatus.FILLED,
            created_at=datetime(2026, 2, 16, 11, 0, 0),
        )
        mock_position_repo.get_by_market = AsyncMock(return_value=None)

        report = await generator.generate_trade_report(
            trade, sample_prediction, sample_market
        )

        assert report.trade is not None
        assert report.trade.trade_type == "BUY_NO"
        # Market price should be no_price for BUY_NO
        assert report.price_comparison["market_price"] == 0.45

    # ==================== generate_daily_report tests ====================

    @pytest.mark.asyncio
    async def test_generate_daily_report(
        self,
        generator: LearningLogGenerator,
        sample_trade: Trade,
        mock_trade_repo: AsyncMock,
    ) -> None:
        """Test generating a daily report."""
        mock_trade_repo.get_trades_by_date = AsyncMock(return_value=[sample_trade])

        report = await generator.generate_daily_report(date(2026, 2, 16))

        assert report.report_type == "daily"
        assert report.report_date == date(2026, 2, 16)
        assert report.summary is not None
        assert report.summary.total_trades == 1
        assert len(report.trades) == 1
        assert 1 in report.trades

    @pytest.mark.asyncio
    async def test_generate_daily_report_empty(
        self,
        generator: LearningLogGenerator,
        mock_trade_repo: AsyncMock,
    ) -> None:
        """Test generating a daily report with no trades."""
        mock_trade_repo.get_trades_by_date = AsyncMock(return_value=[])

        report = await generator.generate_daily_report(date(2026, 2, 16))

        assert report.summary is not None
        assert report.summary.total_trades == 0
        assert report.trades == []
        # Should have at least one insight about no trades
        assert len(report.insights) >= 1
        assert any("No trades" in i.description for i in report.insights)

    @pytest.mark.asyncio
    async def test_generate_daily_report_saves_file(
        self,
        generator: LearningLogGenerator,
        sample_trade: Trade,
        mock_trade_repo: AsyncMock,
        temp_reports_dir: Path,
    ) -> None:
        """Test that daily report is saved to file."""
        mock_trade_repo.get_trades_by_date = AsyncMock(return_value=[sample_trade])

        await generator.generate_daily_report(date(2026, 2, 16))

        # Check file was created
        report_file = temp_reports_dir / "daily_2026-02-16.json"
        assert report_file.exists()

        # Verify content
        with open(report_file) as f:
            content = json.load(f)
        assert content["report_type"] == "daily"
        assert content["report_date"] == "2026-02-16"

    @pytest.mark.asyncio
    async def test_generate_daily_report_multiple_trades(
        self,
        generator: LearningLogGenerator,
        mock_trade_repo: AsyncMock,
    ) -> None:
        """Test generating daily report with multiple trades."""
        trades = [
            Trade(
                id=i,
                market_id=f"market-{i}",
                trade_type=TradeType.BUY_YES if i % 2 == 0 else TradeType.BUY_NO,
                mode=TradeMode.PAPER,
                amount=10.0 * i,
                price=0.5,
                shares=20.0 * i,
                status=TradeStatus.FILLED,
                created_at=datetime(2026, 2, 16, 10, i, 0),
            )
            for i in range(1, 6)
        ]
        mock_trade_repo.get_trades_by_date = AsyncMock(return_value=trades)

        report = await generator.generate_daily_report(date(2026, 2, 16))

        assert report.summary is not None
        assert report.summary.total_trades == 5
        assert report.summary.total_volume == 10.0 + 20.0 + 30.0 + 40.0 + 50.0

    @pytest.mark.asyncio
    async def test_generate_daily_report_bullish_bias_insight(
        self,
        generator: LearningLogGenerator,
        mock_trade_repo: AsyncMock,
    ) -> None:
        """Test daily report detects bullish bias pattern."""
        trades = [
            Trade(
                id=i,
                market_id=f"market-{i}",
                trade_type=TradeType.BUY_YES,  # All BUY_YES
                mode=TradeMode.PAPER,
                amount=10.0,
                price=0.5,
                shares=20.0,
                status=TradeStatus.FILLED,
                created_at=datetime(2026, 2, 16, 10, i, 0),
            )
            for i in range(1, 6)
        ]
        mock_trade_repo.get_trades_by_date = AsyncMock(return_value=trades)

        report = await generator.generate_daily_report(date(2026, 2, 16))

        # Should detect bullish bias
        assert any(
            "bullish bias" in i.description.lower() for i in report.insights
        )

    @pytest.mark.asyncio
    async def test_generate_daily_report_bearish_bias_insight(
        self,
        generator: LearningLogGenerator,
        mock_trade_repo: AsyncMock,
    ) -> None:
        """Test daily report detects bearish bias pattern."""
        trades = [
            Trade(
                id=i,
                market_id=f"market-{i}",
                trade_type=TradeType.BUY_NO,  # All BUY_NO
                mode=TradeMode.PAPER,
                amount=10.0,
                price=0.5,
                shares=20.0,
                status=TradeStatus.FILLED,
                created_at=datetime(2026, 2, 16, 10, i, 0),
            )
            for i in range(1, 6)
        ]
        mock_trade_repo.get_trades_by_date = AsyncMock(return_value=trades)

        report = await generator.generate_daily_report(date(2026, 2, 16))

        # Should detect bearish bias
        assert any(
            "bearish bias" in i.description.lower() for i in report.insights
        )

    @pytest.mark.asyncio
    async def test_generate_daily_report_today_default(
        self,
        generator: LearningLogGenerator,
        mock_trade_repo: AsyncMock,
    ) -> None:
        """Test generate_daily_report uses today as default date."""
        mock_trade_repo.get_trades_by_date = AsyncMock(return_value=[])

        report = await generator.generate_daily_report()

        assert report.report_date == date.today()

    # ==================== Helper method tests ====================

    @pytest.mark.asyncio
    async def test_get_position_info_handles_exception(
        self,
        generator: LearningLogGenerator,
        mock_position_repo: AsyncMock,
    ) -> None:
        """Test _get_position_info handles exceptions gracefully."""
        mock_position_repo.get_by_market = AsyncMock(
            side_effect=Exception("Database error")
        )

        result = await generator._get_position_info("market-1")

        assert result is None

    def test_market_to_snapshot(
        self,
        generator: LearningLogGenerator,
        sample_market: Market,
    ) -> None:
        """Test _market_to_snapshot conversion."""
        snapshot = generator._market_to_snapshot(sample_market)

        assert snapshot.id == "market-1"
        assert snapshot.title == "Will X happen by Y date?"
        assert snapshot.category == "politics"
        assert snapshot.yes_price == 0.55

    def test_trade_to_snapshot(
        self,
        generator: LearningLogGenerator,
        sample_trade: Trade,
    ) -> None:
        """Test _trade_to_snapshot conversion."""
        snapshot = generator._trade_to_snapshot(sample_trade)

        assert snapshot.trade_id == 1
        assert snapshot.trade_type == "BUY_YES"
        assert snapshot.amount == 100.0

    def test_position_to_snapshot(
        self,
        generator: LearningLogGenerator,
        sample_position: Position,
    ) -> None:
        """Test _position_to_snapshot conversion."""
        snapshot = generator._position_to_snapshot(sample_position)

        assert snapshot is not None
        assert snapshot.position_id == 1
        assert snapshot.pnl == 36.36

    def test_position_to_snapshot_none(
        self,
        generator: LearningLogGenerator,
    ) -> None:
        """Test _position_to_snapshot with None input."""
        snapshot = generator._position_to_snapshot(None)

        assert snapshot is None

    def test_report_to_dict_trade_report(
        self,
        generator: LearningLogGenerator,
        sample_trade: Trade,
        sample_prediction: Prediction,
        sample_market: Market,
    ) -> None:
        """Test _report_to_dict for TradeReport."""
        report = TradeReport(
            generated_at=datetime(2026, 2, 16, 10, 30, 0),
            market=generator._market_to_snapshot(sample_market),
            prediction=PredictionSnapshot(
                predicted_probability=0.75,
                confidence=0.85,
                edge=0.20,
                reasoning="Test",
                key_assumptions=["A"],
                recommendation="BUY_YES",
            ),
            trade=generator._trade_to_snapshot(sample_trade),
            position=None,
            price_comparison={"edge": 0.20},
        )

        result = generator._report_to_dict(report)

        assert result["report_type"] == "trade"
        assert "market" in result
        assert result["market"]["title"] == "Will X happen by Y date?"

    def test_report_to_dict_daily_report(
        self,
        generator: LearningLogGenerator,
    ) -> None:
        """Test _report_to_dict for DailyReport."""
        report = DailyReport(
            report_date=date(2026, 2, 16),
            generated_at=datetime(2026, 2, 16, 23, 59, 59),
            summary=TradingSummary(
                total_trades=5,
                winning_trades=3,
                losing_trades=2,
                win_rate=0.6,
                total_pnl=50.0,
                total_volume=500.0,
            ),
            trades=[1, 2, 3, 4, 5],
            insights=[
                LearningInsight(
                    category="activity",
                    description="5 trades",
                    related_trades=[1, 2, 3, 4, 5],
                    recommendation=None,
                )
            ],
        )

        result = generator._report_to_dict(report)

        assert result["report_type"] == "daily"
        assert result["report_date"] == "2026-02-16"
        assert "summary" in result
        assert result["summary"]["total_trades"] == 5

    # ==================== Directory handling tests ====================

    def test_ensure_reports_dir_creates_directory(
        self,
        mock_trade_repo: AsyncMock,
        mock_position_repo: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Test that reports directory is created if it doesn't exist."""
        new_dir = tmp_path / "new_reports"
        assert not new_dir.exists()

        LearningLogGenerator(
            trade_repo=mock_trade_repo,
            position_repo=mock_position_repo,
            reports_dir=new_dir,
        )

        assert new_dir.exists()

    @pytest.mark.asyncio
    async def test_save_report_handles_error(
        self,
        generator: LearningLogGenerator,
    ) -> None:
        """Test _save_report handles file write errors."""
        # Use an invalid path to trigger error
        generator._reports_dir = Path("/invalid/path/that/does/not/exist")

        with pytest.raises(OSError):
            generator._save_report("test.json", {"test": "data"})

    # ==================== Trade without ID tests ====================

    @pytest.mark.asyncio
    async def test_generate_trade_report_no_id(
        self,
        generator: LearningLogGenerator,
        sample_prediction: Prediction,
        sample_market: Market,
        mock_position_repo: AsyncMock,
    ) -> None:
        """Test generating report for trade without ID."""
        trade_no_id = Trade(
            id=0,  # Invalid ID
            market_id="market-1",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=100.0,
            price=0.55,
            shares=181.81,
            status=TradeStatus.FILLED,
            created_at=datetime(2026, 2, 16, 10, 30, 0),
        )
        mock_position_repo.get_by_market = AsyncMock(return_value=None)

        report = await generator.generate_trade_report(
            trade_no_id, sample_prediction, sample_market
        )

        assert report.trade is not None
        assert report.trade.trade_id == 0
