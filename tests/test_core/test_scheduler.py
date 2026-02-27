"""Unit tests for the Scheduler class.

Tests cover scheduler initialization, lifecycle management (start/shutdown),
and job management operations (add/remove/pause/resume).
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from apscheduler.triggers.interval import IntervalTrigger

from src.core.scheduler import Scheduler
from src.core.scheduler import scheduler as global_scheduler


class TestScheduler:
    """Scheduler class unit tests."""

    def test_scheduler_initialization(self) -> None:
        """Test scheduler initialization."""
        s = Scheduler()
        assert s._scheduler is None  # Lazy loading
        assert s._is_running is False

    def test_scheduler_lazy_loading(self) -> None:
        """Test scheduler lazy loading."""
        s = Scheduler()
        scheduler_instance = s.scheduler
        assert scheduler_instance is not None
        assert s._scheduler is scheduler_instance

    def test_start_scheduler(self) -> None:
        """Test starting scheduler."""
        s = Scheduler()
        mock_scheduler = MagicMock()
        s._scheduler = mock_scheduler

        s.start()

        mock_scheduler.start.assert_called_once()
        assert s._is_running is True

    def test_start_already_running(self) -> None:
        """Test starting an already running scheduler."""
        s = Scheduler()
        mock_scheduler = MagicMock()
        s._scheduler = mock_scheduler
        s._is_running = True

        # Should not raise exception, just log warning
        s.start()

        mock_scheduler.start.assert_not_called()
        assert s._is_running is True

    def test_shutdown_scheduler(self) -> None:
        """Test shutting down scheduler."""
        s = Scheduler()
        mock_scheduler = MagicMock()
        s._scheduler = mock_scheduler
        s._is_running = True

        s.shutdown(wait=True)

        mock_scheduler.shutdown.assert_called_once_with(wait=True)
        assert s._is_running is False

    def test_shutdown_not_running(self) -> None:
        """Test shutting down a non-running scheduler."""
        s = Scheduler()
        s._is_running = False

        # Should not raise exception
        s.shutdown()
        assert s._is_running is False

    def test_add_job(self) -> None:
        """Test adding a job."""
        s = Scheduler()
        mock_scheduler = MagicMock()
        mock_job = MagicMock()
        mock_job.id = "test_job"
        mock_scheduler.add_job.return_value = mock_job
        s._scheduler = mock_scheduler

        trigger = IntervalTrigger(seconds=60)

        job_id = s.add_job(
            func=lambda: None,
            trigger=trigger,
            id="test_job",
            name="Test Job",
        )

        assert job_id == "test_job"
        mock_scheduler.add_job.assert_called_once()

    def test_remove_job(self) -> None:
        """Test removing a job."""
        s = Scheduler()
        mock_scheduler = MagicMock()
        s._scheduler = mock_scheduler

        result = s.remove_job("test_job")

        assert result is True
        mock_scheduler.remove_job.assert_called_once_with("test_job")

    def test_remove_job_not_found(self) -> None:
        """Test removing a non-existent job."""
        s = Scheduler()
        mock_scheduler = MagicMock()
        mock_scheduler.remove_job.side_effect = Exception("Job not found")
        s._scheduler = mock_scheduler

        result = s.remove_job("nonexistent_job")

        assert result is False

    def test_get_jobs(self) -> None:
        """Test getting job list."""
        s = Scheduler()
        mock_scheduler = MagicMock()
        mock_job1 = MagicMock()
        mock_job1.id = "job1"
        mock_job2 = MagicMock()
        mock_job2.id = "job2"
        mock_scheduler.get_jobs.return_value = [mock_job1, mock_job2]
        s._scheduler = mock_scheduler

        jobs = s.get_jobs()

        assert jobs == ["job1", "job2"]

    def test_pause_job(self) -> None:
        """Test pausing a job."""
        s = Scheduler()
        mock_scheduler = MagicMock()
        s._scheduler = mock_scheduler

        result = s.pause_job("test_job")

        assert result is True
        mock_scheduler.pause_job.assert_called_once_with("test_job")

    def test_pause_job_not_found(self) -> None:
        """Test pausing a non-existent job."""
        s = Scheduler()
        mock_scheduler = MagicMock()
        mock_scheduler.pause_job.side_effect = Exception("Job not found")
        s._scheduler = mock_scheduler

        result = s.pause_job("nonexistent_job")

        assert result is False

    def test_resume_job(self) -> None:
        """Test resuming a job."""
        s = Scheduler()
        mock_scheduler = MagicMock()
        s._scheduler = mock_scheduler

        result = s.resume_job("test_job")

        assert result is True
        mock_scheduler.resume_job.assert_called_once_with("test_job")

    def test_resume_job_not_found(self) -> None:
        """Test resuming a non-existent job."""
        s = Scheduler()
        mock_scheduler = MagicMock()
        mock_scheduler.resume_job.side_effect = Exception("Job not found")
        s._scheduler = mock_scheduler

        result = s.resume_job("nonexistent_job")

        assert result is False

    def test_is_running_property(self) -> None:
        """Test is_running property."""
        s = Scheduler()
        assert s.is_running is False

        s._is_running = True
        assert s.is_running is True


class TestSchedulerSingleton:
    """Test scheduler singleton."""

    def test_singleton_instance_exists(self) -> None:
        """Test singleton instance exists."""
        assert global_scheduler is not None
        assert isinstance(global_scheduler, Scheduler)

    def test_singleton_is_same_instance(self) -> None:
        """Test singleton is same instance."""
        from src.core.scheduler import scheduler as another_ref

        assert global_scheduler is another_ref


class TestSchedulerConfiguration:
    """Test scheduler configuration."""

    def test_scheduler_uses_config_timezone(self) -> None:
        """Test scheduler uses configured timezone."""
        s = Scheduler()
        # Access the scheduler to trigger lazy loading
        scheduler_instance = s.scheduler

        # Verify timezone is set (default is UTC from config)
        # datetime.timezone.utc has no 'zone' attribute, check via str()
        import datetime

        assert scheduler_instance.timezone == datetime.timezone.utc

    def test_scheduler_configuration_creates_data_dir(self, tmp_path: Path) -> None:
        """Test scheduler creates data directory if needed."""
        with patch("src.core.scheduler.settings") as mock_settings:
            mock_scheduler_settings = MagicMock()
            mock_scheduler_settings.timezone = "UTC"
            mock_scheduler_settings.jobstores_db = str(
                tmp_path / "data" / "scheduler.db"
            )
            mock_scheduler_settings.executors_pool_size = 10
            mock_settings.scheduler = mock_scheduler_settings

            s = Scheduler()
            s._create_scheduler()

            # Data directory should be created
            assert (tmp_path / "data").exists()
