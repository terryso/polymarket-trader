"""Core logic modules: state management, scheduler, circuit breaker, tasks, recovery."""

from src.core.circuit_breaker import (
    BreakerTrigger,
    BreakerTriggerType,
    CircuitBreaker,
    CircuitBreakerResult,
)
from src.core.recovery import RecoveryManager, RecoveryResult
from src.core.scheduler import Scheduler, scheduler
from src.core.state import StateSnapshot, ThreadSafeState, get_state_manager
from src.core.tasks import (
    TaskManager,
    register_all_tasks,
    register_check_positions_job,
    register_daily_statistics_job,
    register_fetch_markets_job,
    register_persist_state_job,
    register_reset_daily_state_job,
    register_validate_predictions_job,
    task_manager,
)

__all__ = [
    "BreakerTrigger",
    "BreakerTriggerType",
    "CircuitBreaker",
    "CircuitBreakerResult",
    "RecoveryManager",
    "RecoveryResult",
    "Scheduler",
    "scheduler",
    "StateSnapshot",
    "ThreadSafeState",
    "get_state_manager",
    "TaskManager",
    "task_manager",
    "register_all_tasks",
    "register_fetch_markets_job",
    "register_check_positions_job",
    "register_daily_statistics_job",
    "register_validate_predictions_job",
    "register_reset_daily_state_job",
    "register_persist_state_job",
]
