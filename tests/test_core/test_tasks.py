"""Tests for the scheduled task configuration module.

Story 8.2: 定时任务配置

This module tests the TaskManager and task registration functions.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.core.scheduler import Scheduler
from src.core.tasks import (
    TaskManager,
    _check_positions_task,
    _daily_statistics_task,
    _fetch_markets_task,
    _persist_state_task,
    _reset_daily_state_task,
    _validate_predictions_task,
    register_all_tasks,
    register_check_positions_job,
    register_daily_statistics_job,
    register_fetch_markets_job,
    register_persist_state_job,
    register_reset_daily_state_job,
    register_validate_predictions_job,
    task_manager,
)


class TestTaskManager:
    """Tests for TaskManager class."""

    def test_task_manager_init(self) -> None:
        """Test TaskManager initialization."""
        manager = TaskManager()
        assert manager._tasks == {}

    def test_register_all_tasks(self) -> None:
        """Test registering all tasks."""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock(return_value="job_id")

        mock_client = Mock()
        mock_analyzer = Mock()
        mock_manager = Mock()
        mock_state = Mock()

        manager = TaskManager()
        job_ids = manager.register_all_tasks(
            scheduler=mock_scheduler,
            polymarket_client=mock_client,
            llm_analyzer=mock_analyzer,
            position_manager=mock_manager,
            state=mock_state,
        )

        # Should have registered 7 jobs (6 original + 1 position cache refresh)
        assert len(job_ids) == 7
        assert mock_scheduler.add_job.call_count == 7

    def test_register_all_tasks_with_optional_deps(self) -> None:
        """Test registering all tasks with optional dependencies."""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock(return_value="job_id")

        mock_client = Mock()
        mock_analyzer = Mock()
        mock_manager = Mock()
        mock_state = Mock()
        mock_filter = Mock()
        mock_tracker = Mock()
        mock_repo = Mock()

        manager = TaskManager()
        job_ids = manager.register_all_tasks(
            scheduler=mock_scheduler,
            polymarket_client=mock_client,
            llm_analyzer=mock_analyzer,
            position_manager=mock_manager,
            state=mock_state,
            market_filter=mock_filter,
            prediction_tracker=mock_tracker,
            statistics_repo=mock_repo,
        )

        assert len(job_ids) == 7


class TestRegisterFetchMarketsJob:
    """Tests for register_fetch_markets_job function."""

    def test_register_fetch_markets_job(self) -> None:
        """Test registering fetch_markets job."""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock(return_value="fetch_markets")

        mock_client = Mock()
        mock_analyzer = Mock()

        job_id = register_fetch_markets_job(
            scheduler=mock_scheduler,
            client=mock_client,
            llm_analyzer=mock_analyzer,
        )

        assert job_id == "fetch_markets"
        mock_scheduler.add_job.assert_called_once()

        # Check the job was registered with correct ID
        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        assert call_kwargs["id"] == "fetch_markets"
        assert call_kwargs["name"] == "Fetch Markets from Polymarket"

    def test_register_fetch_markets_job_with_filter(self) -> None:
        """Test registering fetch_markets job with custom filter."""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock(return_value="fetch_markets")

        mock_client = Mock()
        mock_analyzer = Mock()
        mock_filter = Mock()

        job_id = register_fetch_markets_job(
            scheduler=mock_scheduler,
            client=mock_client,
            llm_analyzer=mock_analyzer,
            market_filter=mock_filter,
        )

        assert job_id == "fetch_markets"


class TestRegisterCheckPositionsJob:
    """Tests for register_check_positions_job function."""

    def test_register_check_positions_job(self) -> None:
        """Test registering check_positions job."""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock(return_value="check_positions")

        mock_manager = Mock()

        job_id = register_check_positions_job(
            scheduler=mock_scheduler,
            manager=mock_manager,
        )

        assert job_id == "check_positions"
        mock_scheduler.add_job.assert_called_once()

        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        assert call_kwargs["id"] == "check_positions"
        assert call_kwargs["name"] == "Check Positions and Update PnL"


class TestRegisterDailyStatisticsJob:
    """Tests for register_daily_statistics_job function."""

    def test_register_daily_statistics_job(self) -> None:
        """Test registering daily_statistics job."""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock(return_value="daily_statistics")

        mock_state = Mock()

        job_id = register_daily_statistics_job(
            scheduler=mock_scheduler,
            state=mock_state,
        )

        assert job_id == "daily_statistics"
        mock_scheduler.add_job.assert_called_once()

        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        assert call_kwargs["id"] == "daily_statistics"
        assert call_kwargs["name"] == "Daily Statistics Update"

    def test_register_daily_statistics_job_with_repo(self) -> None:
        """Test registering daily_statistics job with custom repo."""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock(return_value="daily_statistics")

        mock_state = Mock()
        mock_repo = Mock()

        job_id = register_daily_statistics_job(
            scheduler=mock_scheduler,
            state=mock_state,
            statistics_repo=mock_repo,
        )

        assert job_id == "daily_statistics"


class TestRegisterValidatePredictionsJob:
    """Tests for register_validate_predictions_job function."""

    def test_register_validate_predictions_job(self) -> None:
        """Test registering validate_predictions job."""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock(return_value="validate_predictions")

        job_id = register_validate_predictions_job(scheduler=mock_scheduler)

        assert job_id == "validate_predictions"
        mock_scheduler.add_job.assert_called_once()

        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        assert call_kwargs["id"] == "validate_predictions"
        assert call_kwargs["name"] == "Validate Predictions against Resolved Markets"

    def test_register_validate_predictions_job_with_tracker(self) -> None:
        """Test registering validate_predictions job with custom tracker."""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock(return_value="validate_predictions")

        mock_tracker = Mock()

        job_id = register_validate_predictions_job(
            scheduler=mock_scheduler,
            prediction_tracker=mock_tracker,
        )

        assert job_id == "validate_predictions"


class TestRegisterResetDailyStateJob:
    """Tests for register_reset_daily_state_job function."""

    def test_register_reset_daily_state_job(self) -> None:
        """Test registering reset_daily_state job."""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock(return_value="reset_daily_state")

        mock_state = Mock()

        job_id = register_reset_daily_state_job(
            scheduler=mock_scheduler,
            state=mock_state,
        )

        assert job_id == "reset_daily_state"
        mock_scheduler.add_job.assert_called_once()

        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        assert call_kwargs["id"] == "reset_daily_state"
        assert call_kwargs["name"] == "Reset Daily State"


class TestRegisterPersistStateJob:
    """Tests for register_persist_state_job function."""

    def test_register_persist_state_job(self) -> None:
        """Test registering persist_state job."""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock(return_value="persist_state")

        mock_state = Mock()

        job_id = register_persist_state_job(
            scheduler=mock_scheduler,
            state=mock_state,
        )

        assert job_id == "persist_state"
        mock_scheduler.add_job.assert_called_once()

        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        assert call_kwargs["id"] == "persist_state"
        assert call_kwargs["name"] == "Persist State to Database"


class TestRegisterAllTasks:
    """Tests for register_all_tasks convenience function."""

    def test_register_all_tasks_function(self) -> None:
        """Test register_all_tasks convenience function."""
        mock_scheduler = Mock(spec=Scheduler)
        mock_scheduler.add_job = Mock(return_value="job_id")

        mock_client = Mock()
        mock_analyzer = Mock()
        mock_manager = Mock()
        mock_state = Mock()

        job_ids = register_all_tasks(
            scheduler=mock_scheduler,
            polymarket_client=mock_client,
            llm_analyzer=mock_analyzer,
            position_manager=mock_manager,
            state=mock_state,
        )

        assert len(job_ids) == 7
        assert mock_scheduler.add_job.call_count == 7


class TestFetchMarketsTask:
    """Tests for _fetch_markets_task function."""

    @pytest.mark.asyncio
    async def test_fetch_markets_task_success(self) -> None:
        """Test successful market fetching task."""
        # Create mock market
        mock_market = Mock()
        mock_market.id = "test-market-id"

        mock_client = Mock()
        mock_client.get_markets = Mock(return_value=[mock_market])

        mock_analyzer = Mock()
        mock_analyzer.analyze_market = AsyncMock()

        # Mock market filter
        with patch("src.analysis.market_filter.MarketFilter") as MockFilter:
            mock_filter = Mock()
            mock_result = Mock()
            mock_result.markets = [mock_market]
            mock_result.statistics = Mock()
            mock_filter.filter_markets = Mock(return_value=mock_result)
            MockFilter.return_value = mock_filter

            await _fetch_markets_task(
                client=mock_client,
                llm_analyzer=mock_analyzer,
                market_filter=None,
            )

            mock_client.get_markets.assert_called_once()
            mock_filter.filter_markets.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_markets_task_no_markets(self) -> None:
        """Test market fetching task when no markets returned."""
        mock_client = Mock()
        mock_client.get_markets = Mock(return_value=[])

        mock_analyzer = Mock()

        await _fetch_markets_task(
            client=mock_client,
            llm_analyzer=mock_analyzer,
            market_filter=None,
        )

        mock_client.get_markets.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_markets_task_failure(self) -> None:
        """Test market fetching task handles errors gracefully."""
        mock_client = Mock()
        mock_client.get_markets = Mock(side_effect=Exception("API Error"))

        mock_analyzer = Mock()

        # Should not raise exception
        await _fetch_markets_task(
            client=mock_client,
            llm_analyzer=mock_analyzer,
            market_filter=None,
        )

        mock_client.get_markets.assert_called_once()


class TestCheckPositionsTask:
    """Tests for _check_positions_task function."""

    @pytest.mark.asyncio
    async def test_check_positions_task_success(self) -> None:
        """Test successful position checking task."""
        mock_position = Mock()
        mock_position.id = 1

        mock_manager = Mock()
        mock_manager.get_open_positions = AsyncMock(return_value=[mock_position])

        await _check_positions_task(manager=mock_manager)

        mock_manager.get_open_positions.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_positions_task_no_positions(self) -> None:
        """Test position checking task when no positions."""
        mock_manager = Mock()
        mock_manager.get_open_positions = AsyncMock(return_value=[])

        await _check_positions_task(manager=mock_manager)

        mock_manager.get_open_positions.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_positions_task_failure(self) -> None:
        """Test position checking task handles errors gracefully."""
        mock_manager = Mock()
        mock_manager.get_open_positions = AsyncMock(
            side_effect=Exception("Database Error")
        )

        # Should not raise exception
        await _check_positions_task(manager=mock_manager)

        mock_manager.get_open_positions.assert_called_once()


class TestDailyStatisticsTask:
    """Tests for _daily_statistics_task function."""

    @pytest.mark.asyncio
    async def test_daily_statistics_task_success(self) -> None:
        """Test successful daily statistics task."""
        mock_state = Mock()
        mock_state.get_state = AsyncMock(
            return_value=Mock(
                current_capital=200.0,
                daily_pnl=10.0,
            )
        )

        mock_repo = Mock()
        mock_repo.save = AsyncMock()

        await _daily_statistics_task(
            state=mock_state,
            statistics_repo=mock_repo,
        )

        mock_state.get_state.assert_called_once()
        mock_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_daily_statistics_task_creates_repo_if_none(self) -> None:
        """Test daily statistics task creates repo if not provided."""
        mock_state = Mock()
        mock_state.get_state = AsyncMock(
            return_value=Mock(
                current_capital=200.0,
                daily_pnl=10.0,
            )
        )

        with patch(
            "src.storage.repositories.statistics_repo.StatisticsRepository"
        ) as MockRepo:
            mock_repo = Mock()
            mock_repo.save = AsyncMock()
            MockRepo.return_value = mock_repo

            await _daily_statistics_task(
                state=mock_state,
                statistics_repo=None,
            )

            MockRepo.assert_called_once()

    @pytest.mark.asyncio
    async def test_daily_statistics_task_failure(self) -> None:
        """Test daily statistics task handles errors gracefully."""
        mock_state = Mock()
        mock_state.get_state = AsyncMock(side_effect=Exception("State Error"))

        # Should not raise exception
        await _daily_statistics_task(
            state=mock_state,
            statistics_repo=None,
        )

        mock_state.get_state.assert_called_once()


class TestValidatePredictionsTask:
    """Tests for _validate_predictions_task function."""

    @pytest.mark.asyncio
    async def test_validate_predictions_task_success(self) -> None:
        """Test successful prediction validation task."""
        mock_tracker = Mock()
        mock_tracker.check_resolved_markets = AsyncMock(return_value=[])

        await _validate_predictions_task(prediction_tracker=mock_tracker)

        mock_tracker.check_resolved_markets.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_predictions_task_creates_tracker_if_none(self) -> None:
        """Test prediction validation task creates tracker if not provided."""
        with patch("src.analysis.prediction_tracker.PredictionTracker") as MockTracker:
            mock_tracker = Mock()
            mock_tracker.check_resolved_markets = AsyncMock(return_value=[])
            MockTracker.return_value = mock_tracker

            with (
                patch("src.storage.repositories.market_repo.MarketRepository"),
                patch("src.storage.repositories.prediction_repo.PredictionRepository"),
            ):
                await _validate_predictions_task(prediction_tracker=None)

                MockTracker.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_predictions_task_failure(self) -> None:
        """Test prediction validation task handles errors gracefully."""
        mock_tracker = Mock()
        mock_tracker.check_resolved_markets = AsyncMock(
            side_effect=Exception("Tracker Error")
        )

        # Should not raise exception
        await _validate_predictions_task(prediction_tracker=mock_tracker)

        mock_tracker.check_resolved_markets.assert_called_once()


class TestResetDailyStateTask:
    """Tests for _reset_daily_state_task function."""

    @pytest.mark.asyncio
    async def test_reset_daily_state_task_success(self) -> None:
        """Test successful daily state reset task."""
        mock_state = Mock()
        mock_state.reset_daily = AsyncMock()

        await _reset_daily_state_task(state=mock_state)

        mock_state.reset_daily.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_daily_state_task_failure(self) -> None:
        """Test daily state reset task handles errors gracefully."""
        mock_state = Mock()
        mock_state.reset_daily = AsyncMock(side_effect=Exception("Reset Error"))

        # Should not raise exception
        await _reset_daily_state_task(state=mock_state)

        mock_state.reset_daily.assert_called_once()


class TestPersistStateTask:
    """Tests for _persist_state_task function."""

    @pytest.mark.asyncio
    async def test_persist_state_task_success(self) -> None:
        """Test successful state persistence task."""
        mock_state = Mock()
        mock_state.persist = AsyncMock()

        await _persist_state_task(state=mock_state)

        mock_state.persist.assert_called_once()

    @pytest.mark.asyncio
    async def test_persist_state_task_failure(self) -> None:
        """Test state persistence task handles errors gracefully."""
        mock_state = Mock()
        mock_state.persist = AsyncMock(side_effect=Exception("DB Error"))

        # Should not raise exception
        await _persist_state_task(state=mock_state)

        mock_state.persist.assert_called_once()


class TestTaskManagerSingleton:
    """Tests for module-level task_manager singleton."""

    def test_task_manager_singleton_exists(self) -> None:
        """Test that task_manager singleton is available."""
        from src.core.tasks import task_manager as tm

        assert tm is not None
        assert isinstance(tm, TaskManager)

    def test_task_manager_singleton_is_same_instance(self) -> None:
        """Test that task_manager singleton is always the same instance."""
        from src.core import task_manager as tm1
        from src.core.tasks import task_manager as tm2

        assert tm1 is tm2
