"""Core logic modules: state management, scheduler, circuit breaker, tasks, recovery, error handling, alerting."""

from src.core.alerting import (
    Alert,
    AlertChannel,
    AlertLevel,
    AlertManager,
    LogAlertChannel,
    WebhookAlertChannel,
)
from src.core.circuit_breaker import (
    BreakerTrigger,
    BreakerTriggerType,
    CircuitBreaker,
    CircuitBreakerResult,
)
from src.core.error_handler import (
    ErrorHandler,
    get_error_handler,
    setup_async_exception_handler,
    setup_error_handler,
    setup_global_exception_handler,
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
    # Alerting
    "Alert",
    "AlertChannel",
    "AlertLevel",
    "AlertManager",
    "LogAlertChannel",
    "WebhookAlertChannel",
    # Circuit breaker
    "BreakerTrigger",
    "BreakerTriggerType",
    "CircuitBreaker",
    "CircuitBreakerResult",
    # Error handling
    "ErrorHandler",
    "get_error_handler",
    "setup_error_handler",
    "setup_global_exception_handler",
    "setup_async_exception_handler",
    # Recovery
    "RecoveryManager",
    "RecoveryResult",
    # Scheduler
    "Scheduler",
    "scheduler",
    # State
    "StateSnapshot",
    "ThreadSafeState",
    "get_state_manager",
    # Tasks
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
