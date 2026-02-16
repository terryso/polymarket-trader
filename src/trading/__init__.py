"""Trading modules: paper trading, executor, risk control, position manager.

This package provides trading-related functionality including:
- RiskController: Pre-trade risk checks (Story 4.4)
- Paper trading executor (Story 5.x)
- Trading executor (Story 5.x)
- Position manager (Story 4.5)

Example:
    >>> from src.trading import RiskController
    >>> from src.trading.risk_control import RiskCheckResult
"""

from src.trading.risk_control import RiskCheckFailure, RiskCheckResult, RiskController

__all__ = ["RiskController", "RiskCheckResult", "RiskCheckFailure"]
