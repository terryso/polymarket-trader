"""Trading modules: paper trading, executor, risk control, position manager.

This package provides trading-related functionality including:
- RiskController: Pre-trade risk checks (Story 4.4)
- PositionManager: Position lifecycle management (Story 4.5)
- Paper trading executor (Story 5.x)
- Trading executor (Story 5.x)

Example:
    >>> from src.trading import RiskController, PositionManager
    >>> from src.trading.risk_control import RiskCheckResult
"""

from src.trading.position_manager import PositionManager
from src.trading.risk_control import RiskCheckFailure, RiskCheckResult, RiskController

__all__ = [
    "RiskController",
    "RiskCheckResult",
    "RiskCheckFailure",
    "PositionManager",
]
