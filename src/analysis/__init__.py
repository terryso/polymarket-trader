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

    >>> from src.analysis import PerformanceAnalyzer
    >>> analyzer = PerformanceAnalyzer(prediction_repo, trade_repo, position_repo)
    >>> report = await analyzer.generate_insight_report()

    >>> from src.analysis import WebResearcher, ResearchError
    >>> researcher = WebResearcher()
    >>> summary = await researcher.research_market("Will Bitcoin reach $100k?")

    >>> from src.analysis import MultiSourceSearchEngine, SearchResult
    >>> engine = MultiSourceSearchEngine()
    >>> results = await engine.search("Bitcoin price prediction 2026")
"""

from __future__ import annotations

from src.analysis.llm_analyzer import AnalysisError, LLMAnalyzer
from src.analysis.market_filter import (
    FilterResult,
    FilterStatistics,
    MarketFilter,
)
from src.analysis.performance_analyzer import (
    CategoryPerformance,
    ConfidenceAnalysis,
    EdgeAnalysis,
    ImprovementSuggestion,
    PatternInsight,
    PatternType,
    PerformanceAnalyzer,
    PerformanceInsightReport,
    PerformanceLevel,
    PerformanceMetrics,
    SuggestionPriority,
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
from src.analysis.search_sources import (
    BigModelSearchSource,
    BingSearchSource,
    DuckDuckGoSearchSource,
    GoogleSearchSource,
    MultiSourceSearchEngine,
    SearchAggregationError,
    SearchSource,
    SearchResult,
)
from src.analysis.web_researcher import ResearchError, WebResearcher

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
    # Performance analyzer (Story 6.5)
    "PerformanceAnalyzer",
    "PerformanceLevel",
    "PatternType",
    "SuggestionPriority",
    "PerformanceMetrics",
    "CategoryPerformance",
    "ConfidenceAnalysis",
    "EdgeAnalysis",
    "PatternInsight",
    "ImprovementSuggestion",
    "PerformanceInsightReport",
    # Web researcher
    "WebResearcher",
    "ResearchError",
    # Multi-source search engine
    "MultiSourceSearchEngine",
    "SearchResult",
    "SearchSource",
    "SearchAggregationError",
    "GoogleSearchSource",
    "BingSearchSource",
    "DuckDuckGoSearchSource",
    "BigModelSearchSource",
]
