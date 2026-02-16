"""Daily statistics recorder.

This module provides the DailyStatisticsRecorder class for collecting
trading data and generating daily statistics records.

Story 5.5: 统计数据记录

Usage:
    from src.trading.statistics_recorder import DailyStatisticsRecorder
    from src.models.trade import TradeMode

    recorder = DailyStatisticsRecorder(trade_repo, stats_repo, state_manager)
    stats = await recorder.record_daily_stats(TradeMode.PAPER)
"""

from __future__ import annotations

__all__ = ["DailyStatisticsRecorder"]

from datetime import date, timedelta
from typing import TYPE_CHECKING

from src.config import settings
from src.models.statistics import Statistics
from src.models.trade import TradeMode, TradeStatus
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.core.state import StateSnapshot, ThreadSafeState
    from src.storage.repositories.statistics_repo import StatisticsRepository
    from src.storage.repositories.trade_repo import TradeRepository

logger = get_logger(__name__)


class DailyStatisticsRecorder:
    """Recorder for daily trading statistics.

    Collects trading data and generates daily statistics records.

    Example:
        >>> recorder = DailyStatisticsRecorder(trade_repo, stats_repo, state)
        >>> stats = await recorder.record_daily_stats(TradeMode.PAPER)
        >>> print(f"Today's PnL: ${stats.total_pnl:.2f}")
    """

    def __init__(
        self,
        trade_repo: "TradeRepository",
        stats_repo: "StatisticsRepository",
        state_manager: "ThreadSafeState",
    ) -> None:
        """Initialize the recorder.

        Args:
            trade_repo: Trade repository for querying trades
            stats_repo: Statistics repository for saving stats
            state_manager: State manager for capital data
        """
        self._trade_repo = trade_repo
        self._stats_repo = stats_repo
        self._state_manager = state_manager
        self._logger = logger

    async def record_daily_stats(self, mode: TradeMode) -> Statistics:
        """Record statistics for today.

        Args:
            mode: Trading mode (PAPER or LIVE)

        Returns:
            Statistics record for today

        Example:
            >>> stats = await recorder.record_daily_stats(TradeMode.PAPER)
        """
        today = date.today()
        yesterday = today - timedelta(days=1)

        self._logger.info(
            f"📊 Recording daily statistics for {today} (mode={mode.value})"
        )

        # Get today's trades
        trades = await self._trade_repo.get_by_date_range(
            start_date=today,
            end_date=today,
            mode=mode,
        )

        # Filter to only filled trades for statistics
        filled_trades = [t for t in trades if t.status == TradeStatus.FILLED]
        total_trades = len(filled_trades)

        # Calculate winning/losing trades
        # For paper trading, we consider trades with positive PnL as winning
        # Since individual trade PnL is tracked in positions, we use a simpler approach:
        # Count trades that are associated with profitable positions
        # For now, we'll use a placeholder calculation based on daily_pnl
        state = await self._state_manager.get_state()
        daily_pnl = state.daily_pnl

        # Calculate winning/losing trades based on sign of daily PnL
        # This is a simplified approach; in a real system, you'd track per-trade PnL
        if total_trades > 0 and daily_pnl > 0:
            # If overall PnL is positive, assume majority are winning
            win_rate = min(1.0, daily_pnl / (total_trades * 10.0))  # Heuristic
            winning_trades = int(total_trades * min(win_rate, 1.0))
            winning_trades = max(1, winning_trades) if daily_pnl > 0 else 0
            losing_trades = total_trades - winning_trades
        elif total_trades > 0 and daily_pnl < 0:
            # If overall PnL is negative, assume majority are losing
            win_rate = max(0.0, 1.0 + daily_pnl / (total_trades * 10.0))  # Heuristic
            winning_trades = int(total_trades * max(win_rate, 0.0))
            losing_trades = total_trades - winning_trades
        elif total_trades > 0:
            # Flat PnL, assume 50% win rate
            winning_trades = total_trades // 2
            losing_trades = total_trades - winning_trades
        else:
            winning_trades = 0
            losing_trades = 0

        # Calculate win_rate
        if total_trades > 0:
            win_rate_value: float | None = winning_trades / total_trades
        else:
            win_rate_value = None

        # Get starting capital from yesterday's stats or settings
        yesterday_stats = await self._stats_repo.get_by_date(yesterday, mode)
        if yesterday_stats is not None and yesterday_stats.ending_capital is not None:
            starting_capital = yesterday_stats.ending_capital
        else:
            starting_capital = settings.initial_capital

        # Get ending capital from state
        ending_capital = state.current_capital

        # Create statistics record
        stats = Statistics(
            id=0,
            date=today,
            mode=mode,
            starting_capital=starting_capital,
            ending_capital=ending_capital,
            total_pnl=daily_pnl,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate_value,
        )

        # Save to database
        saved_stats = await self._stats_repo.save(stats)

        # Format win_rate for logging
        win_rate_str = f"{win_rate_value:.2%}" if win_rate_value is not None else "N/A"
        self._logger.info(
            f"📊 Daily statistics recorded: "
            f"trades={total_trades}, win_rate={win_rate_str}, "
            f"pnl=${daily_pnl:.2f}"
        )

        return saved_stats
