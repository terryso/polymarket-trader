"""Analysis modules: market filter, LLM analyzer, prompts, prediction tracker.

This module provides market analysis functionality including filtering,
LLM-based prediction analysis, and prediction validation tracking.

Example:
    >>> from src.analysis import MarketFilter, FilterResult, FilterStatistics
    >>> filter = MarketFilter()
    >>> result = filter.filter_markets(markets)

    >>> from src.analysis import LLMAnalyzer, AnalysisError
    >>> analyzer = LLMAnalyzer()
    >>> result = await analyzer.analyze_market(market)

    >>> from src.analysis import (
    ...     MARKET_ANALYST_SYSTEM_PROMPT,
    ...     build_market_analysis_prompt,
    ...     parse_llm_analysis_response,
    ...     LLMAnalysisResult,
    ... )

    >>> from src.analysis import PredictionTracker, ValidationResult, AccuracyResult
    >>> tracker = PredictionTracker(market_repo, prediction_repo)
    >>> results = await tracker.check_resolved_markets()
"""

from __future__ import annotations

from src.analysis.llm_analyzer import AnalysisError, LLMAnalyzer
from src.analysis.market_filter import (
    FilterResult,
    FilterStatistics,
    MarketFilter,
)
from src.analysis.prediction_tracker import (
    AccuracyResult,
    PredictionTracker,
    ValidationResult,
)
from src.analysis.prompts import (
    MARKET_ANALYST_SYSTEM_PROMPT,
    LLMAnalysisResult,
    Recommendation,
    build_market_analysis_prompt,
    parse_llm_analysis_response,
    validate_analysis_result,
)

__all__ = [
    # Market filter
    "MarketFilter",
    "FilterResult",
    "FilterStatistics",
    # LLM analyzer
    "LLMAnalyzer",
    "AnalysisError",
    # LLM prompts
    "MARKET_ANALYST_SYSTEM_PROMPT",
    "Recommendation",
    "LLMAnalysisResult",
    "build_market_analysis_prompt",
    "parse_llm_analysis_response",
    "validate_analysis_result",
    # Prediction tracker
    "PredictionTracker",
    "ValidationResult",
    "AccuracyResult",
]
