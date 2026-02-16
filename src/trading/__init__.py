"""Trading modules: paper trading, executor, risk control, position manager.

This package provides trading-related functionality including:
- RiskController: Pre-trade risk checks (Story 4.4)
- PositionManager: Position lifecycle management (Story 4.5)
- PaperTradingExecutor: Paper trading executor (Story 5.2)
- TradingExecutor: Trading decision flow orchestrator (Story 5.3)
- PnLResult: Single position PnL calculation result (Story 5.4)
- TotalPnLResult: Total PnL calculation result (Story 5.4)
- DailyStatisticsRecorder: Daily statistics recorder (Story 5.5)

Example:
    >>> from src.trading import RiskController, PositionManager, PaperTradingExecutor
    >>> from src.trading import TradingExecutor, TradingDecision
    >>> from src.trading import PnLResult, TotalPnLResult
    >>> from src.trading import DailyStatisticsRecorder
    >>> from src.trading.risk_control import RiskCheckResult
"""

from src.trading.executor import TradingDecision, TradingExecutor
from src.trading.paper_trading import PaperTradeResult, PaperTradingExecutor
from src.trading.position_manager import PnLResult, PositionManager, TotalPnLResult
from src.trading.risk_control import RiskCheckFailure, RiskCheckResult, RiskController
from src.trading.statistics_recorder import DailyStatisticsRecorder

__all__ = [
    "RiskController",
    "RiskCheckResult",
    "RiskCheckFailure",
    "PositionManager",
    "PnLResult",
    "TotalPnLResult",
    "PaperTradingExecutor",
    "PaperTradeResult",
    "TradingExecutor",
    "TradingDecision",
    "DailyStatisticsRecorder",
]
