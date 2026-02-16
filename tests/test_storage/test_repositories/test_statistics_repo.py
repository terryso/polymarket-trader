"""Tests for StatisticsRepository.

Story 5.5: 统计数据记录
"""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.statistics import Statistics
from src.models.trade import TradeMode
from src.storage.repositories.statistics_repo import StatisticsRepository


class TestStatisticsRepository:
    """Tests for StatisticsRepository CRUD operations."""

    @pytest.fixture
    def repo(self) -> StatisticsRepository:
        """Create a StatisticsRepository instance."""
        return StatisticsRepository()

    @pytest.fixture
    def sample_stats(self) -> Statistics:
        """Create a sample Statistics instance."""
        return Statistics(
            id=0,
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

    @pytest.mark.asyncio
    async def test_save_new_stats(
        self, repo: StatisticsRepository, sample_stats: Statistics
    ) -> None:
        """Test saving a new statistics record."""
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "src.storage.repositories.statistics_repo.get_connection",
            return_value=mock_conn,
        ):
            result = await repo.save(sample_stats)

        assert result.id == 1
        assert result.date == sample_stats.date
        assert result.mode == sample_stats.mode
        assert result.starting_capital == sample_stats.starting_capital
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_update_existing_stats(
        self, repo: StatisticsRepository, sample_stats: Statistics
    ) -> None:
        """Test updating an existing statistics record (upsert)."""
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 2

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "src.storage.repositories.statistics_repo.get_connection",
            return_value=mock_conn,
        ):
            # Save with updated values
            updated_stats = Statistics(
                id=0,
                date=sample_stats.date,
                mode=sample_stats.mode,
                starting_capital=200.0,
                ending_capital=220.0,  # Updated
                total_pnl=20.0,  # Updated
                total_trades=8,  # Updated
                winning_trades=5,
                losing_trades=3,
                win_rate=0.625,  # Updated
            )
            result = await repo.save(updated_stats)

        assert result.id == 2
        assert result.ending_capital == 220.0
        assert result.total_pnl == 20.0

    @pytest.mark.asyncio
    async def test_get_by_date_found(
        self, repo: StatisticsRepository, sample_stats: Statistics
    ) -> None:
        """Test get_by_date when record exists."""
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {
            "id": 1,
            "date": date.today().isoformat(),
            "mode": TradeMode.PAPER.value,
            "starting_capital": 200.0,
            "ending_capital": 210.0,
            "total_pnl": 10.0,
            "total_trades": 5,
            "winning_trades": 3,
            "losing_trades": 2,
            "win_rate": 0.6,
            "created_at": None,
        }[key]

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = None
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "src.storage.repositories.statistics_repo.get_connection",
            return_value=mock_conn,
        ):
            result = await repo.get_by_date(date.today(), TradeMode.PAPER)

        assert result is not None
        assert result.date == date.today()
        assert result.mode == TradeMode.PAPER

    @pytest.mark.asyncio
    async def test_get_by_date_not_found(
        self, repo: StatisticsRepository
    ) -> None:
        """Test get_by_date when record does not exist."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)

        mock_conn = AsyncMock()
        mock_conn.row_factory = None
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "src.storage.repositories.statistics_repo.get_connection",
            return_value=mock_conn,
        ):
            result = await repo.get_by_date(
                date.today() - timedelta(days=365), TradeMode.PAPER
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_date_range(
        self, repo: StatisticsRepository
    ) -> None:
        """Test get_by_date_range returns statistics in order."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Create mock rows for two days
        mock_rows = []
        for dt in [yesterday, today]:
            row = MagicMock()
            row.__getitem__ = lambda self, key, d=dt: {
                "id": 1 if d == yesterday else 2,
                "date": d.isoformat(),
                "mode": TradeMode.PAPER.value,
                "starting_capital": 200.0,
                "ending_capital": 205.0 if d == yesterday else 210.0,
                "total_pnl": 5.0 if d == yesterday else 10.0,
                "total_trades": 3 if d == yesterday else 5,
                "winning_trades": 2 if d == yesterday else 3,
                "losing_trades": 1 if d == yesterday else 2,
                "win_rate": 0.67 if d == yesterday else 0.6,
                "created_at": None,
            }[key]
            mock_rows.append(row)

        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=mock_rows)

        mock_conn = AsyncMock()
        mock_conn.row_factory = None
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "src.storage.repositories.statistics_repo.get_connection",
            return_value=mock_conn,
        ):
            result = await repo.get_by_date_range(
                yesterday, today, TradeMode.PAPER
            )

        assert len(result) == 2
        # Results should be ordered by date ascending
        assert result[0].date == yesterday
        assert result[1].date == today

    @pytest.mark.asyncio
    async def test_get_by_date_range_empty(
        self, repo: StatisticsRepository
    ) -> None:
        """Test get_by_date_range when no records found."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_conn = AsyncMock()
        mock_conn.row_factory = None
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "src.storage.repositories.statistics_repo.get_connection",
            return_value=mock_conn,
        ):
            result = await repo.get_by_date_range(
                date(2020, 1, 1), date(2020, 1, 31), TradeMode.PAPER
            )

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_latest(self, repo: StatisticsRepository) -> None:
        """Test get_latest returns most recent statistics."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        mock_rows = []
        for dt in [today, yesterday]:
            row = MagicMock()
            row.__getitem__ = lambda self, key, d=dt: {
                "id": 2 if d == today else 1,
                "date": d.isoformat(),
                "mode": TradeMode.PAPER.value,
                "starting_capital": 200.0,
                "ending_capital": 210.0 if d == today else 205.0,
                "total_pnl": 10.0 if d == today else 5.0,
                "total_trades": 5 if d == today else 3,
                "winning_trades": 3 if d == today else 2,
                "losing_trades": 2 if d == today else 1,
                "win_rate": 0.6 if d == today else 0.67,
                "created_at": None,
            }[key]
            mock_rows.append(row)

        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=mock_rows)

        mock_conn = AsyncMock()
        mock_conn.row_factory = None
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "src.storage.repositories.statistics_repo.get_connection",
            return_value=mock_conn,
        ):
            result = await repo.get_latest(TradeMode.PAPER, limit=7)

        assert len(result) == 2
        # Results should be ordered by date descending
        assert result[0].date == today
        assert result[1].date == yesterday

    @pytest.mark.asyncio
    async def test_get_latest_with_limit(
        self, repo: StatisticsRepository
    ) -> None:
        """Test get_latest respects the limit parameter."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_conn = AsyncMock()
        mock_conn.row_factory = None
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "src.storage.repositories.statistics_repo.get_connection",
            return_value=mock_conn,
        ):
            await repo.get_latest(TradeMode.PAPER, limit=10)

        # Verify the limit was passed to the query
        call_args = mock_conn.execute.call_args
        assert "10" in str(call_args)
