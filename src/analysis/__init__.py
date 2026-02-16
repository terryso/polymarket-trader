"""Analysis modules: market filter, LLM analyzer, prompts.

This module provides market analysis functionality including filtering
and LLM-based prediction analysis.

Example:
    >>> from src.analysis import MarketFilter, FilterResult, FilterStatistics
    >>> filter = MarketFilter()
    >>> result = filter.filter_markets(markets)
"""

from __future__ import annotations

from src.analysis.market_filter import (
    FilterResult,
    FilterStatistics,
    MarketFilter,
)

__all__ = [
    "MarketFilter",
    "FilterResult",
    "FilterStatistics",
]
