"""Tests for Statistics model.

This module tests the Statistics and DailyStats models including:
- Statistics model creation
- DailyStats model creation
- DailyStats.from_statistics factory method
- Field validation
- DateTime and Date serialization
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from src.models import DailyStats, Statistics, TradeMode


class TestStatistics:
    """Tests for Statistics model."""

    def test_create_statistics_minimal(self) -> None:
        """Test creating statistics with required fields only."""
        stats = Statistics(
            id=1,
            date=date(2026, 2, 15),
            mode=TradeMode.PAPER,
            starting_capital=10000.0,
            total_trades=5,
            winning_trades=3,
            losing_trades=2,
        )

        assert stats.id == 1
        assert stats.date == date(2026, 2, 15)
        assert stats.mode == TradeMode.PAPER
        assert stats.starting_capital == 10000.0
        assert stats.ending_capital is None
        assert stats.total_pnl is None
        assert stats.total_trades == 5
        assert stats.winning_trades == 3
        assert stats.losing_trades == 2
        assert stats.win_rate is None
        assert stats.created_at is None

    def test_create_statistics_full(self) -> None:
        """Test creating statistics with all fields."""
        stats = Statistics(
            id=1,
            date=date(2026, 2, 15),
            mode=TradeMode.PAPER,
            starting_capital=10000.0,
            ending_capital=10150.0,
            total_pnl=150.0,
            total_trades=5,
            winning_trades=3,
            losing_trades=2,
            win_rate=0.6,
            created_at=datetime(2026, 2, 15, 23, 59, 59),
        )

        assert stats.id == 1
        assert stats.date == date(2026, 2, 15)
        assert stats.mode == TradeMode.PAPER
        assert stats.starting_capital == 10000.0
        assert stats.ending_capital == 10150.0
        assert stats.total_pnl == 150.0
        assert stats.total_trades == 5
        assert stats.winning_trades == 3
        assert stats.losing_trades == 2
        assert stats.win_rate == 0.6
        assert stats.created_at == datetime(2026, 2, 15, 23, 59, 59)

    def test_starting_capital_validation_negative(self) -> None:
        """Test starting_capital validation rejects negative values."""
        with pytest.raises(ValueError):
            Statistics(
                id=1,
                date=date(2026, 2, 15),
                mode=TradeMode.PAPER,
                starting_capital=-1000.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
            )

    def test_total_trades_validation_negative(self) -> None:
        """Test total_trades validation rejects negative values."""
        with pytest.raises(ValueError):
            Statistics(
                id=1,
                date=date(2026, 2, 15),
                mode=TradeMode.PAPER,
                starting_capital=1000.0,
                total_trades=-1,
                winning_trades=0,
                losing_trades=0,
            )

    def test_winning_trades_validation_negative(self) -> None:
        """Test winning_trades validation rejects negative values."""
        with pytest.raises(ValueError):
            Statistics(
                id=1,
                date=date(2026, 2, 15),
                mode=TradeMode.PAPER,
                starting_capital=1000.0,
                total_trades=0,
                winning_trades=-1,
                losing_trades=0,
            )

    def test_win_rate_validation_invalid(self) -> None:
        """Test win_rate validation rejects values > 1."""
        with pytest.raises(ValueError):
            Statistics(
                id=1,
                date=date(2026, 2, 15),
                mode=TradeMode.PAPER,
                starting_capital=1000.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=1.5,
            )

    def test_win_rate_validation_negative(self) -> None:
        """Test win_rate validation rejects negative values."""
        with pytest.raises(ValueError):
            Statistics(
                id=1,
                date=date(2026, 2, 15),
                mode=TradeMode.PAPER,
                starting_capital=1000.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=-0.1,
            )

    def test_total_pnl_can_be_negative(self) -> None:
        """Test total_pnl can be negative (loss)."""
        stats = Statistics(
            id=1,
            date=date(2026, 2, 15),
            mode=TradeMode.PAPER,
            starting_capital=10000.0,
            total_pnl=-100.0,
            total_trades=3,
            winning_trades=1,
            losing_trades=2,
        )
        assert stats.total_pnl == -100.0

    def test_date_serialization(self) -> None:
        """Test date serialization to ISO 8601 (YYYY-MM-DD)."""
        stats = Statistics(
            id=1,
            date=date(2026, 2, 15),
            mode=TradeMode.PAPER,
            starting_capital=1000.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
        )

        # model_dump with mode='json' returns ISO string
        data = stats.model_dump(mode="json")
        assert data["date"] == "2026-02-15"

    def test_datetime_serialization(self) -> None:
        """Test datetime serialization to ISO 8601."""
        stats = Statistics(
            id=1,
            date=date(2026, 2, 15),
            mode=TradeMode.PAPER,
            starting_capital=1000.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            created_at=datetime(2026, 2, 15, 23, 59, 59),
        )

        # model_dump with mode='json' returns ISO string
        data = stats.model_dump(mode="json")
        assert data["created_at"] == "2026-02-15T23:59:59"

    def test_mode_from_string(self) -> None:
        """Test mode creation from string."""
        stats = Statistics(
            id=1,
            date=date(2026, 2, 15),
            mode="LIVE",
            starting_capital=1000.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
        )
        assert stats.mode == TradeMode.LIVE

    def test_model_json_export(self) -> None:
        """Test JSON export."""
        stats = Statistics(
            id=1,
            date=date(2026, 2, 15),
            mode=TradeMode.PAPER,
            starting_capital=10000.0,
            total_trades=5,
            winning_trades=3,
            losing_trades=2,
        )
        json_str = stats.model_dump_json()

        assert '"id":1' in json_str
        assert '"date":"2026-02-15"' in json_str
        assert '"mode":"PAPER"' in json_str

    def test_model_config_validate_assignment(self) -> None:
        """Test that validate_assignment is enabled."""
        stats = Statistics(
            id=1,
            date=date(2026, 2, 15),
            mode=TradeMode.PAPER,
            starting_capital=1000.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
        )

        # Should validate on assignment
        with pytest.raises(ValueError):
            stats.win_rate = 1.5

        # Valid assignment should work
        stats.win_rate = 0.6
        assert stats.win_rate == 0.6


class TestDailyStats:
    """Tests for DailyStats model."""

    def test_create_daily_stats_minimal(self) -> None:
        """Test creating daily stats with required fields only."""
        daily = DailyStats(
            date=date(2026, 2, 15),
            mode=TradeMode.PAPER,
            starting_capital=10000.0,
            trades_count=5,
            win_count=3,
            loss_count=2,
        )

        assert daily.date == date(2026, 2, 15)
        assert daily.mode == TradeMode.PAPER
        assert daily.starting_capital == 10000.0
        assert daily.ending_capital is None
        assert daily.daily_pnl is None
        assert daily.daily_return_pct is None
        assert daily.trades_count == 5
        assert daily.win_count == 3
        assert daily.loss_count == 2
        assert daily.win_rate_pct is None

    def test_create_daily_stats_full(self) -> None:
        """Test creating daily stats with all fields."""
        daily = DailyStats(
            date=date(2026, 2, 15),
            mode=TradeMode.PAPER,
            starting_capital=10000.0,
            ending_capital=10150.0,
            daily_pnl=150.0,
            daily_return_pct=1.5,
            trades_count=5,
            win_count=3,
            loss_count=2,
            win_rate_pct=60.0,
        )

        assert daily.date == date(2026, 2, 15)
        assert daily.mode == TradeMode.PAPER
        assert daily.starting_capital == 10000.0
        assert daily.ending_capital == 10150.0
        assert daily.daily_pnl == 150.0
        assert daily.daily_return_pct == 1.5
        assert daily.trades_count == 5
        assert daily.win_count == 3
        assert daily.loss_count == 2
        assert daily.win_rate_pct == 60.0

    def test_from_statistics_basic(self) -> None:
        """Test DailyStats creation from Statistics."""
        stats = Statistics(
            id=1,
            date=date(2026, 2, 15),
            mode=TradeMode.PAPER,
            starting_capital=10000.0,
            ending_capital=10150.0,
            total_pnl=150.0,
            total_trades=5,
            winning_trades=3,
            losing_trades=2,
            win_rate=0.6,
        )

        daily = DailyStats.from_statistics(stats)

        assert daily.date == date(2026, 2, 15)
        assert daily.mode == TradeMode.PAPER
        assert daily.starting_capital == 10000.0
        assert daily.ending_capital == 10150.0
        assert daily.daily_pnl == 150.0
        assert daily.daily_return_pct == 1.5  # (150 / 10000) * 100
        assert daily.trades_count == 5
        assert daily.win_count == 3
        assert daily.loss_count == 2
        assert daily.win_rate_pct == 60.0  # 0.6 * 100

    def test_from_statistics_no_ending_capital(self) -> None:
        """Test DailyStats from Statistics without ending_capital."""
        stats = Statistics(
            id=1,
            date=date(2026, 2, 15),
            mode=TradeMode.PAPER,
            starting_capital=10000.0,
            total_trades=5,
            winning_trades=3,
            losing_trades=2,
        )

        daily = DailyStats.from_statistics(stats)

        assert daily.ending_capital is None
        assert daily.daily_pnl is None
        assert daily.daily_return_pct is None

    def test_from_statistics_no_win_rate(self) -> None:
        """Test DailyStats from Statistics without win_rate."""
        stats = Statistics(
            id=1,
            date=date(2026, 2, 15),
            mode=TradeMode.PAPER,
            starting_capital=10000.0,
            ending_capital=10150.0,
            total_pnl=150.0,
            total_trades=5,
            winning_trades=3,
            losing_trades=2,
        )

        daily = DailyStats.from_statistics(stats)

        assert daily.win_rate_pct is None

    def test_from_statistics_negative_return(self) -> None:
        """Test DailyStats from Statistics with loss."""
        stats = Statistics(
            id=1,
            date=date(2026, 2, 15),
            mode=TradeMode.PAPER,
            starting_capital=10000.0,
            ending_capital=9850.0,
            total_pnl=-150.0,
            total_trades=3,
            winning_trades=1,
            losing_trades=2,
            win_rate=0.33,
        )

        daily = DailyStats.from_statistics(stats)

        assert daily.daily_pnl == -150.0
        assert daily.daily_return_pct == -1.5  # (-150 / 10000) * 100
        assert daily.win_rate_pct == 33.0

    def test_date_serialization(self) -> None:
        """Test date serialization to ISO 8601 (YYYY-MM-DD)."""
        daily = DailyStats(
            date=date(2026, 2, 15),
            mode=TradeMode.PAPER,
            starting_capital=1000.0,
            trades_count=0,
            win_count=0,
            loss_count=0,
        )

        # model_dump with mode='json' returns ISO string
        data = daily.model_dump(mode="json")
        assert data["date"] == "2026-02-15"

    def test_win_rate_pct_validation_invalid(self) -> None:
        """Test win_rate_pct validation rejects values > 100."""
        with pytest.raises(ValueError):
            DailyStats(
                date=date(2026, 2, 15),
                mode=TradeMode.PAPER,
                starting_capital=1000.0,
                trades_count=0,
                win_count=0,
                loss_count=0,
                win_rate_pct=150.0,
            )

    def test_model_config_validate_assignment(self) -> None:
        """Test that validate_assignment is enabled."""
        daily = DailyStats(
            date=date(2026, 2, 15),
            mode=TradeMode.PAPER,
            starting_capital=1000.0,
            trades_count=0,
            win_count=0,
            loss_count=0,
        )

        # Should validate on assignment
        with pytest.raises(ValueError):
            daily.win_rate_pct = 150.0

        # Valid assignment should work
        daily.win_rate_pct = 60.0
        assert daily.win_rate_pct == 60.0
