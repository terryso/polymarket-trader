"""Tests for DailyStatisticsRecorder.

Story 5.5: 统计数据记录
"""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.state import StateSnapshot
from src.models.statistics import Statistics
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.trading.statistics_recorder import DailyStatisticsRecorder


class TestDailyStatisticsRecorder:
    """Tests for DailyStatisticsRecorder."""

    @pytest.fixture
    def mock_trade_repo(self) -> AsyncMock:
        """Create a mock TradeRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_stats_repo(self) -> AsyncMock:
        """Create a mock StatisticsRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_state_manager(self) -> AsyncMock:
        """Create a mock ThreadSafeState."""
        return AsyncMock()

    @pytest.fixture
    def recorder(
        self,
        mock_trade_repo: AsyncMock,
        mock_stats_repo: AsyncMock,
        mock_state_manager: AsyncMock,
    ) -> DailyStatisticsRecorder:
        """Create a DailyStatisticsRecorder instance."""
        return DailyStatisticsRecorder(
            trade_repo=mock_trade_repo,
            stats_repo=mock_stats_repo,
            state_manager=mock_state_manager,
        )

    @pytest.fixture
    def sample_trades(self) -> list[Trade]:
        """Create sample trades for testing."""
        return [
            Trade(
                id=1,
                market_id="market-1",
                trade_type=TradeType.BUY_YES,
                mode=TradeMode.PAPER,
                amount=20.0,
                price=0.45,
                shares=44.44,
                status=TradeStatus.FILLED,
                created_at=None,
            ),
            Trade(
                id=2,
                market_id="market-2",
                trade_type=TradeType.BUY_NO,
                mode=TradeMode.PAPER,
                amount=15.0,
                price=0.30,
                shares=50.0,
                status=TradeStatus.FILLED,
                created_at=None,
            ),
        ]

    @pytest.mark.asyncio
    async def test_record_daily_stats_no_trades(
        self,
        recorder: DailyStatisticsRecorder,
        mock_trade_repo: AsyncMock,
        mock_stats_repo: AsyncMock,
        mock_state_manager: AsyncMock,
    ) -> None:
        """Test recording stats when no trades exist."""
        # Setup mocks
        mock_trade_repo.get_by_date_range = AsyncMock(return_value=[])
        mock_stats_repo.get_by_date = AsyncMock(return_value=None)
        mock_state_manager.get_state = AsyncMock(
            return_value=StateSnapshot(
                current_capital=200.0,
                daily_pnl=0.0,
            )
        )
        mock_stats_repo.save = AsyncMock(
            return_value=Statistics(
                id=1,
                date=date.today(),
                mode=TradeMode.PAPER,
                starting_capital=200.0,
                ending_capital=200.0,
                total_pnl=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=None,
            )
        )

        # Execute
        result = await recorder.record_daily_stats(TradeMode.PAPER)

        # Verify
        assert result.total_trades == 0
        assert result.ending_capital == 200.0
        assert result.total_pnl == 0.0
        assert result.win_rate is None
        mock_trade_repo.get_by_date_range.assert_called_once()
        mock_stats_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_daily_stats_with_trades_positive_pnl(
        self,
        recorder: DailyStatisticsRecorder,
        mock_trade_repo: AsyncMock,
        mock_stats_repo: AsyncMock,
        mock_state_manager: AsyncMock,
        sample_trades: list[Trade],
    ) -> None:
        """Test recording stats with trades and positive PnL."""
        # Setup mocks
        mock_trade_repo.get_by_date_range = AsyncMock(return_value=sample_trades)
        mock_stats_repo.get_by_date = AsyncMock(return_value=None)
        mock_state_manager.get_state = AsyncMock(
            return_value=StateSnapshot(
                current_capital=210.0,
                daily_pnl=10.0,  # Positive PnL
            )
        )
        mock_stats_repo.save = AsyncMock(
            side_effect=lambda s: Statistics(
                id=1,
                date=s.date,
                mode=s.mode,
                starting_capital=s.starting_capital,
                ending_capital=s.ending_capital,
                total_pnl=s.total_pnl,
                total_trades=s.total_trades,
                winning_trades=s.winning_trades,
                losing_trades=s.losing_trades,
                win_rate=s.win_rate,
            )
        )

        # Execute
        result = await recorder.record_daily_stats(TradeMode.PAPER)

        # Verify
        assert result.total_trades == 2
        assert result.ending_capital == 210.0
        assert result.total_pnl == 10.0
        # With positive PnL, there should be at least some winning trades
        assert result.winning_trades >= 1

    @pytest.mark.asyncio
    async def test_record_daily_stats_with_trades_negative_pnl(
        self,
        recorder: DailyStatisticsRecorder,
        mock_trade_repo: AsyncMock,
        mock_stats_repo: AsyncMock,
        mock_state_manager: AsyncMock,
        sample_trades: list[Trade],
    ) -> None:
        """Test recording stats with trades and negative PnL."""
        # Setup mocks
        mock_trade_repo.get_by_date_range = AsyncMock(return_value=sample_trades)
        mock_stats_repo.get_by_date = AsyncMock(return_value=None)
        mock_state_manager.get_state = AsyncMock(
            return_value=StateSnapshot(
                current_capital=185.0,
                daily_pnl=-15.0,  # Negative PnL
            )
        )
        mock_stats_repo.save = AsyncMock(
            side_effect=lambda s: Statistics(
                id=1,
                date=s.date,
                mode=s.mode,
                starting_capital=s.starting_capital,
                ending_capital=s.ending_capital,
                total_pnl=s.total_pnl,
                total_trades=s.total_trades,
                winning_trades=s.winning_trades,
                losing_trades=s.losing_trades,
                win_rate=s.win_rate,
            )
        )

        # Execute
        result = await recorder.record_daily_stats(TradeMode.PAPER)

        # Verify
        assert result.total_trades == 2
        assert result.ending_capital == 185.0
        assert result.total_pnl == -15.0
        # With negative PnL, there should be more losing trades
        assert result.losing_trades >= 1

    @pytest.mark.asyncio
    async def test_record_daily_stats_uses_yesterday_capital(
        self,
        recorder: DailyStatisticsRecorder,
        mock_trade_repo: AsyncMock,
        mock_stats_repo: AsyncMock,
        mock_state_manager: AsyncMock,
    ) -> None:
        """Test that starting capital is taken from yesterday's stats."""
        yesterday = date.today() - timedelta(days=1)

        # Setup mocks
        mock_trade_repo.get_by_date_range = AsyncMock(return_value=[])
        mock_stats_repo.get_by_date = AsyncMock(
            return_value=Statistics(
                id=1,
                date=yesterday,
                mode=TradeMode.PAPER,
                starting_capital=180.0,
                ending_capital=195.0,  # Yesterday's ending capital
                total_pnl=15.0,
                total_trades=3,
                winning_trades=2,
                losing_trades=1,
                win_rate=0.67,
            )
        )
        mock_state_manager.get_state = AsyncMock(
            return_value=StateSnapshot(
                current_capital=205.0,
                daily_pnl=10.0,
            )
        )
        mock_stats_repo.save = AsyncMock(
            side_effect=lambda s: Statistics(
                id=2,
                date=s.date,
                mode=s.mode,
                starting_capital=s.starting_capital,
                ending_capital=s.ending_capital,
                total_pnl=s.total_pnl,
                total_trades=s.total_trades,
                winning_trades=s.winning_trades,
                losing_trades=s.losing_trades,
                win_rate=s.win_rate,
            )
        )

        # Execute
        result = await recorder.record_daily_stats(TradeMode.PAPER)

        # Verify starting capital comes from yesterday
        assert result.starting_capital == 195.0
        assert result.ending_capital == 205.0

    @pytest.mark.asyncio
    async def test_record_daily_stats_filters_by_mode(
        self,
        recorder: DailyStatisticsRecorder,
        mock_trade_repo: AsyncMock,
        mock_stats_repo: AsyncMock,
        mock_state_manager: AsyncMock,
    ) -> None:
        """Test that trade queries filter by trading mode."""
        # Setup mocks
        mock_trade_repo.get_by_date_range = AsyncMock(return_value=[])
        mock_stats_repo.get_by_date = AsyncMock(return_value=None)
        mock_state_manager.get_state = AsyncMock(
            return_value=StateSnapshot(
                current_capital=200.0,
                daily_pnl=0.0,
            )
        )
        mock_stats_repo.save = AsyncMock(
            return_value=Statistics(
                id=1,
                date=date.today(),
                mode=TradeMode.LIVE,
                starting_capital=200.0,
                ending_capital=200.0,
                total_pnl=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=None,
            )
        )

        # Execute with LIVE mode
        await recorder.record_daily_stats(TradeMode.LIVE)

        # Verify mode filter was used
        call_args = mock_trade_repo.get_by_date_range.call_args
        assert call_args[1]["mode"] == TradeMode.LIVE

    @pytest.mark.asyncio
    async def test_record_daily_stats_only_counts_filled_trades(
        self,
        recorder: DailyStatisticsRecorder,
        mock_trade_repo: AsyncMock,
        mock_stats_repo: AsyncMock,
        mock_state_manager: AsyncMock,
    ) -> None:
        """Test that only FILLED trades are counted."""
        # Create trades with different statuses
        trades = [
            Trade(
                id=1,
                market_id="market-1",
                trade_type=TradeType.BUY_YES,
                mode=TradeMode.PAPER,
                amount=20.0,
                price=0.45,
                shares=44.44,
                status=TradeStatus.FILLED,
            ),
            Trade(
                id=2,
                market_id="market-2",
                trade_type=TradeType.BUY_NO,
                mode=TradeMode.PAPER,
                amount=15.0,
                price=0.30,
                shares=50.0,
                status=TradeStatus.PENDING,  # Not filled
            ),
            Trade(
                id=3,
                market_id="market-3",
                trade_type=TradeType.BUY_YES,
                mode=TradeMode.PAPER,
                amount=10.0,
                price=0.50,
                shares=20.0,
                status=TradeStatus.CANCELLED,  # Not filled
            ),
        ]

        # Setup mocks
        mock_trade_repo.get_by_date_range = AsyncMock(return_value=trades)
        mock_stats_repo.get_by_date = AsyncMock(return_value=None)
        mock_state_manager.get_state = AsyncMock(
            return_value=StateSnapshot(
                current_capital=205.0,
                daily_pnl=5.0,
            )
        )
        mock_stats_repo.save = AsyncMock(
            side_effect=lambda s: Statistics(
                id=1,
                date=s.date,
                mode=s.mode,
                starting_capital=s.starting_capital,
                ending_capital=s.ending_capital,
                total_pnl=s.total_pnl,
                total_trades=s.total_trades,
                winning_trades=s.winning_trades,
                losing_trades=s.losing_trades,
                win_rate=s.win_rate,
            )
        )

        # Execute
        result = await recorder.record_daily_stats(TradeMode.PAPER)

        # Only FILLED trades should be counted
        assert result.total_trades == 1  # Only the FILLED trade

    @pytest.mark.asyncio
    async def test_record_daily_stats_win_rate_calculation(
        self,
        recorder: DailyStatisticsRecorder,
        mock_trade_repo: AsyncMock,
        mock_stats_repo: AsyncMock,
        mock_state_manager: AsyncMock,
    ) -> None:
        """Test that win_rate is calculated correctly."""
        # Create 5 trades
        trades = [
            Trade(
                id=i,
                market_id=f"market-{i}",
                trade_type=TradeType.BUY_YES,
                mode=TradeMode.PAPER,
                amount=10.0,
                price=0.50,
                shares=20.0,
                status=TradeStatus.FILLED,
            )
            for i in range(5)
        ]

        # Setup mocks
        mock_trade_repo.get_by_date_range = AsyncMock(return_value=trades)
        mock_stats_repo.get_by_date = AsyncMock(return_value=None)
        mock_state_manager.get_state = AsyncMock(
            return_value=StateSnapshot(
                current_capital=210.0,
                daily_pnl=10.0,  # Positive PnL
            )
        )
        mock_stats_repo.save = AsyncMock(
            side_effect=lambda s: Statistics(
                id=1,
                date=s.date,
                mode=s.mode,
                starting_capital=s.starting_capital,
                ending_capital=s.ending_capital,
                total_pnl=s.total_pnl,
                total_trades=s.total_trades,
                winning_trades=s.winning_trades,
                losing_trades=s.losing_trades,
                win_rate=s.win_rate,
            )
        )

        # Execute
        result = await recorder.record_daily_stats(TradeMode.PAPER)

        # Verify win_rate is between 0 and 1
        assert result.win_rate is not None
        assert 0.0 <= result.win_rate <= 1.0
        # Verify win_rate = winning_trades / total_trades
        expected_win_rate = result.winning_trades / result.total_trades
        assert abs(result.win_rate - expected_win_rate) < 0.01
