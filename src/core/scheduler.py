"""APScheduler scheduler wrapper for the Polymarket Trader application.

This module provides a Scheduler class that wraps APScheduler's AsyncIOScheduler
for managing scheduled tasks in the trading system.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import settings
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from apscheduler.job import Job

logger = get_logger(__name__)


class Scheduler:
    """APScheduler wrapper for managing scheduled tasks.

    This class provides a simplified interface for APScheduler's AsyncIOScheduler,
    with configuration from application settings.

    Attributes:
        _scheduler: The underlying AsyncIOScheduler instance (lazy-loaded).
        _is_running: Whether the scheduler is currently running.

    Example:
        >>> from src.core.scheduler import scheduler
        >>> scheduler.start()
        >>> scheduler.add_job(my_func, IntervalTrigger(seconds=60), id="my_job")
        >>> scheduler.shutdown()
    """

    def __init__(self) -> None:
        """Initialize the Scheduler wrapper."""
        self._scheduler: AsyncIOScheduler | None = None
        self._is_running: bool = False

    def _create_scheduler(self) -> AsyncIOScheduler:
        """Create and configure the scheduler instance.

        Returns:
            Configured AsyncIOScheduler instance.
        """
        # Ensure data directory exists for jobstore
        jobstore_db_path = Path(settings.scheduler.jobstores_db)
        jobstore_db_path.parent.mkdir(parents=True, exist_ok=True)

        # Configure jobstores - using MemoryJobStore for simplicity
        # SQLite can have issues with async, using memory store for now
        jobstores = {
            "default": MemoryJobStore(),
        }

        # Configure executors
        executors = {
            "default": ThreadPoolExecutor(
                max_workers=settings.scheduler.executors_pool_size
            )
        }

        # Configure job defaults
        job_defaults = {
            "coalesce": True,  # Merge missed jobs
            "max_instances": 1,  # Max concurrent instances per job
        }

        scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=settings.scheduler.timezone,
        )

        logger.info(
            "Scheduler configured",
            extra={
                "timezone": settings.scheduler.timezone,
                "jobstore": "memory",
                "executor_pool_size": settings.scheduler.executors_pool_size,
            },
        )

        return scheduler

    @property
    def scheduler(self) -> AsyncIOScheduler:
        """Get the scheduler instance (lazy loading).

        Returns:
            The AsyncIOScheduler instance.
        """
        if self._scheduler is None:
            self._scheduler = self._create_scheduler()
        return self._scheduler

    def start(self) -> None:
        """Start the scheduler.

        If the scheduler is already running, a warning will be logged
        and no action will be taken.
        """
        if self._is_running:
            logger.warning("Scheduler is already running")
            return

        self.scheduler.start()
        self._is_running = True
        logger.info("Scheduler started")

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler gracefully.

        Args:
            wait: Whether to wait for running jobs to complete.
        """
        if not self._is_running:
            logger.warning("Scheduler is not running")
            return

        self.scheduler.shutdown(wait=wait)
        self._is_running = False
        logger.info("Scheduler shutdown complete", extra={"wait": wait})

    def add_job(
        self,
        func: Callable[..., Any],
        trigger: Any,
        id: str,
        name: str | None = None,
        replace_existing: bool = True,
        **kwargs: Any,
    ) -> str:
        """Add a scheduled job.

        Args:
            func: The function to execute.
            trigger: The trigger for the job (IntervalTrigger, CronTrigger, etc.).
            id: Unique identifier for the job.
            name: Human-readable name for the job.
            replace_existing: Whether to replace an existing job with the same ID.
            **kwargs: Additional arguments passed to APScheduler.

        Returns:
            The job ID.
        """
        job: Job = self.scheduler.add_job(
            func=func,
            trigger=trigger,
            id=id,
            name=name or id,
            replace_existing=replace_existing,
            **kwargs,
        )
        logger.info(
            f"Job added: {id}",
            extra={"job_id": id, "job_name": name},
        )
        return str(job.id)

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job.

        Args:
            job_id: The ID of the job to remove.

        Returns:
            True if the job was removed, False if it wasn't found.
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Job removed: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id}: {e}")
            return False

    def get_jobs(self) -> list[str]:
        """Get all scheduled job IDs.

        Returns:
            List of job IDs.
        """
        return [job.id for job in self.scheduler.get_jobs()]

    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job.

        Args:
            job_id: The ID of the job to pause.

        Returns:
            True if the job was paused, False if it wasn't found.
        """
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Job paused: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to pause job {job_id}: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job.

        Args:
            job_id: The ID of the job to resume.

        Returns:
            True if the job was resumed, False if it wasn't found.
        """
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Job resumed: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to resume job {job_id}: {e}")
            return False

    @property
    def is_running(self) -> bool:
        """Check if the scheduler is running.

        Returns:
            True if the scheduler is running, False otherwise.
        """
        return self._is_running


# Singleton instance for global access
scheduler = Scheduler()
