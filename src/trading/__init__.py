"""Trading modules: paper trading, executor, risk control, position manager.

This package provides trading-related functionality including:
- RiskController: Pre-trade risk checks (Story 4.4)
- PositionManager: Position lifecycle management (Story 4.5)
- PaperTradingExecutor: Paper trading executor (Story 5.2)
- Trading executor (Story 5.x)

Example:
    >>> from src.trading import RiskController, PositionManager, PaperTradingExecutor
    >>> from src.trading.risk_control import RiskCheckResult
"""

from src.trading.paper_trading import PaperTradeResult, PaperTradingExecutor
from src.trading.position_manager import PositionManager
from src.trading.risk_control import RiskCheckFailure, RiskCheckResult, RiskController

__all__ = [
    "RiskController",
    "RiskCheckResult",
    "RiskCheckFailure",
    "PositionManager",
    "PaperTradingExecutor",
    "PaperTradeResult",
]
