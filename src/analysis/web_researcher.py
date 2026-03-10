"""Web researcher module using BigModel API for market-related searches.

This module provides the WebResearcher class that performs web searches
to gather additional context for LLM market analysis.

Uses BigModel (智谱AI) web_search API for intelligent search without
requiring browser automation.

Usage:
    from src.analysis import WebResearcher

    researcher = WebResearcher()
    research_summary = await researcher.research_market(
        market_title="Will Bitcoin reach $100k by end of 2026?",
        description="This market resolves to YES if..."
    )
    print(research_summary)
"""

from __future__ import annotations

__all__ = ["WebResearcher", "ResearchError"]

import asyncio
from typing import Any

from src.config import settings
from src.utils.logger import OPERATION_EMOJIS, get_logger


class ResearchError(Exception):
    """Web research error.

    Raised when web research fails.

    Attributes:
        message: Error message
        query: Search query that failed
        original_exception: Original exception (optional)
    """

    def __init__(
        self,
        message: str,
        query: str | None = None,
        original_exception: Exception | None = None,
    ) -> None:
        """Initialize research error.

        Args:
            message: Error message
            query: Search query (optional)
            original_exception: Original exception (optional)
        """
        self.message = message
        self.query = query
        self.original_exception = original_exception
        super().__init__(message)

    def __str__(self) -> str:
        """Return string representation of the error."""
        details = []
        if self.query:
            details.append(f"query={self.query[:50]}...")
        if self.original_exception:
            details.append(f"caused by: {self.original_exception}")
        if details:
            return f"{self.message} ({', '.join(details)})"
        return self.message


class WebResearcher:
    """Web researcher using BigModel API for market context gathering.

    Uses BigModel (智谱AI) web_search API to gather relevant information
    about prediction markets for LLM analysis.

    Simple and reliable - no browser automation required.

    Attributes:
        _search_engine: Multi-source search engine instance

    Example:
        >>> researcher = WebResearcher()
        >>> summary = await researcher.research_market(
        ...     market_title="Will Bitcoin reach $100k?"
        ... )
        >>> print(summary)
    """

    def __init__(self) -> None:
        """Initialize the web researcher with settings from config."""
        self._logger = get_logger(__name__)

        # Import here to avoid circular imports
        from src.analysis.search_sources import (
            BigModelSearchSource,
            MultiSourceSearchEngine,
        )

        # Initialize multi-source search engine with only BigModel
        timeout = settings.web_research.timeout_seconds
        max_results = settings.web_research.max_results
        api_key = settings.web_research.bigmodel_api_key

        # Create search sources - using only BigModel for simplicity
        sources = [
            BigModelSearchSource(timeout=timeout, max_results=max_results, api_key=api_key),
        ]

        self._search_engine = MultiSourceSearchEngine(
            sources=sources,
            timeout=timeout,
            max_total_results=max_results,
        )

        self._logger.info(
            f"{OPERATION_EMOJIS['analysis']} WebResearcher initialized with BigModel search engine"
        )

    async def research_market(
        self, market_title: str, description: str | None = None
    ) -> str:
        """Perform web research on a market.

        Args:
            market_title: Market title/question
            description: Optional market description for better search

        Returns:
            Formatted text summary of search results

        Raises:
            ResearchError: If research fails

        Example:
            >>> researcher = WebResearcher()
            >>> summary = await researcher.research_market(
            ...     "Will Bitcoin reach $100k by 2026?"
            ... )
            >>> "Bitcoin" in summary
            True
        """
        self._logger.info(
            f"{OPERATION_EMOJIS['analysis']} Starting web research: "
            f"{market_title[:50]}..."
        )

        try:
            # Build search query
            search_query = self._build_search_query(market_title, description)
            self._logger.debug(f"{OPERATION_EMOJIS['analysis']} Search query: {search_query}")

            # Perform multi-source search
            search_results = await self._search_engine.search(search_query)

            # Format results
            research_summary = self._format_research_results(search_results)

            self._logger.info(
                f"{OPERATION_EMOJIS['analysis']} Web research complete: "
                f"{len(search_results)} results found"
            )

            return research_summary

        except ImportError as e:
            self._logger.error(f"BigModel SDK not installed: {e}")
            raise ResearchError(
                message="BigModel SDK not installed. Run: pip install zai-sdk",
                query=search_query,
                original_exception=e,
            )
        except Exception as e:
            self._logger.error(f"Web research failed: {e}")
            raise ResearchError(
                message=f"Web research failed: {e}",
                query=search_query,
                original_exception=e,
            )

    def _build_search_query(self, title: str, description: str | None) -> str:
        """Build search query from market title and description.

        Args:
            title: Market title
            description: Optional market description

        Returns:
            Optimized search query string
        """
        # Use market title as primary query
        query = title

        # If description is short and has useful info, add to query
        if description and len(description) < 200:
            # Extract keywords
            keywords = self._extract_keywords(description)
            if keywords:
                query += f" {keywords}"

        return query

    def _extract_keywords(self, text: str) -> str:
        """Extract relevant keywords from text.

        Args:
            text: Text to extract keywords from

        Returns:
            Space-separated keywords
        """
        # Simple keyword extraction logic
        # Can be improved with NLP or more sophisticated logic
        words = text.split()
        # Remove common stopwords
        stopwords = {
            "will",
            "the",
            "a",
            "an",
            "by",
            "in",
            "on",
            "at",
            "for",
            "of",
            "to",
            "be",
            "this",
            "that",
            "with",
            "from",
        }
        keywords = [
            w for w in words if w.lower() not in stopwords and len(w) > 3
        ]
        return " ".join(keywords[:5])  # Take first 5 keywords

    def _format_research_results(self, results: list["SearchResult"]) -> str:
        """Format search results into readable text.

        Args:
            results: List of SearchResult objects

        Returns:
            Formatted text summary
        """
        if not results:
            return "No search results found."

        formatted_lines = ["**Web Research Results:**\n"]

        for i, result in enumerate(results, 1):
            formatted_lines.append(
                f"{i}. **{result.title}**\n"
                f"   {result.snippet}\n"
                f"   Source: {result.source} - {result.url}\n"
            )

        return "\n".join(formatted_lines)
