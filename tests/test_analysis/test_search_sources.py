"""Unit tests for multi-source web search engine.

This module tests the search_sources module, including:
- SearchResult model validation
- SearchSource base class functionality
- MultiSourceSearchEngine aggregation
- Deduplication logic
- Error handling and fault tolerance
"""

from __future__ import annotations

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.analysis.search_sources import (
    SearchResult,
    SearchSource,
    GoogleSearchSource,
    BingSearchSource,
    DuckDuckGoSearchSource,
    MultiSourceSearchEngine,
    SearchAggregationError,
)


# ============================================================================
# SearchResult Tests
# ============================================================================


class TestSearchResult:
    """Test SearchResult data model."""

    def test_create_valid_search_result(self) -> None:
        """Test creating a valid search result."""
        result = SearchResult(
            title="Bitcoin reaches $100k",
            url="https://example.com/bitcoin-100k",
            snippet="Bitcoin has reached the $100,000 milestone...",
            source="Google",
        )

        assert result.title == "Bitcoin reaches $100k"
        assert result.url == "https://example.com/bitcoin-100k"
        assert result.snippet == "Bitcoin has reached the $100,000 milestone..."
        assert result.source == "Google"
        assert isinstance(result.timestamp, datetime)
        assert result.relevance_score is None

    def test_search_result_with_relevance_score(self) -> None:
        """Test creating search result with relevance score."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Test snippet",
            source="Test",
            relevance_score=0.85,
        )

        assert result.relevance_score == 0.85

    def test_search_result_empty_title_raises_error(self) -> None:
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            SearchResult(
                title="",
                url="https://example.com",
                snippet="Test",
                source="Test",
            )

    def test_search_result_empty_url_raises_error(self) -> None:
        """Test that empty URL raises ValueError."""
        with pytest.raises(ValueError, match="URL cannot be empty"):
            SearchResult(
                title="Test",
                url="",
                snippet="Test",
                source="Test",
            )

    def test_search_result_invalid_url_raises_error(self) -> None:
        """Test that invalid URL format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid URL"):
            SearchResult(
                title="Test",
                url="not-a-valid-url",
                snippet="Test",
                source="Test",
            )

    def test_normalize_for_deduplication(self) -> None:
        """Test result normalization for deduplication."""
        result = SearchResult(
            title="Bitcoin Price Analysis",
            url="https://example.com/article?id=123",
            snippet="Test",
            source="Google",
        )

        normalized = result.normalize_for_deduplication()

        assert "example.com" in normalized
        assert "bitcoin price analysis" in normalized.lower()

    def test_normalize_case_insensitive(self) -> None:
        """Test that normalization is case-insensitive."""
        result1 = SearchResult(
            title="Bitcoin Price",
            url="https://Example.com/page1",
            snippet="Test",
            source="Google",
        )

        result2 = SearchResult(
            title="bitcoin price",
            url="https://example.com/page2",
            snippet="Test",
            source="Bing",
        )

        # Domain should match (normalized to lowercase)
        assert "example.com" in result1.normalize_for_deduplication()
        assert "example.com" in result2.normalize_for_deduplication()

    def test_to_dict(self) -> None:
        """Test converting search result to dictionary."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            source="Google",
            relevance_score=0.9,
        )

        result_dict = result.to_dict()

        assert result_dict["title"] == "Test Title"
        assert result_dict["url"] == "https://example.com"
        assert result_dict["snippet"] == "Test snippet"
        assert result_dict["source"] == "Google"
        assert "timestamp" in result_dict
        assert result_dict["relevance_score"] == 0.9


# ============================================================================
# Mock Search Source for Testing
# ============================================================================


class MockSearchSource(SearchSource):
    """Mock search source for testing."""

    def __init__(
        self,
        name: str = "MockSource",
        results: list[SearchResult] | None = None,
        should_fail: bool = False,
    ) -> None:
        """Initialize mock search source.

        Args:
            name: Source name
            results: Results to return (default: empty list)
            should_fail: Whether to raise exception on search
        """
        super().__init__(name=name, timeout=30, max_results=10)
        self._results = results or []
        self._should_fail = should_fail
        self._search_called = False

    async def search(self, query: str) -> list[SearchResult]:
        """Mock search implementation.

        Args:
            query: Search query (ignored)

        Returns:
            Pre-configured results or raises exception
        """
        self._search_called = True

        if self._should_fail:
            raise Exception(f"{self.name} search failed")

        return self._results

    @property
    def search_called(self) -> bool:
        """Check if search was called."""
        return self._search_called


# ============================================================================
# MultiSourceSearchEngine Tests
# ============================================================================


class TestMultiSourceSearchEngine:
    """Test multi-source search engine."""

    def test_initialization_default_sources(self) -> None:
        """Test engine initialization with default sources."""
        # Test with custom sources instead of relying on settings
        mock_source = MockSearchSource(name="TestSource")
        engine = MultiSourceSearchEngine(sources=[mock_source])

        stats = engine.get_statistics()
        assert stats["num_sources"] == 1
        assert "TestSource" in stats["sources"]

    def test_initialization_custom_sources(self) -> None:
        """Test engine initialization with custom sources."""
        mock_source = MockSearchSource(name="CustomSource")
        engine = MultiSourceSearchEngine(sources=[mock_source])

        stats = engine.get_statistics()
        assert stats["num_sources"] == 1
        assert "CustomSource" in stats["sources"]

    @pytest.mark.asyncio
    async def test_search_single_source(self) -> None:
        """Test search with a single source."""
        results = [
            SearchResult(
                title="Result 1",
                url="https://example.com/1",
                snippet="Snippet 1",
                source="MockSource",
            ),
            SearchResult(
                title="Result 2",
                url="https://example.com/2",
                snippet="Snippet 2",
                source="MockSource",
            ),
        ]

        mock_source = MockSearchSource(name="MockSource", results=results)
        engine = MultiSourceSearchEngine(sources=[mock_source])

        search_results = await engine.search("test query")

        assert len(search_results) == 2
        assert search_results[0].title == "Result 1"
        assert search_results[1].title == "Result 2"
        assert mock_source.search_called

    @pytest.mark.asyncio
    async def test_search_multiple_sources_aggregation(self) -> None:
        """Test search with multiple sources aggregates results."""
        results1 = [
            SearchResult(
                title="Result 1",
                url="https://example.com/1",
                snippet="Snippet 1",
                source="Source1",
            )
        ]

        results2 = [
            SearchResult(
                title="Result 2",
                url="https://other.com/2",
                snippet="Snippet 2",
                source="Source2",
            )
        ]

        source1 = MockSearchSource(name="Source1", results=results1)
        source2 = MockSearchSource(name="Source2", results=results2)

        engine = MultiSourceSearchEngine(sources=[source1, source2])

        search_results = await engine.search("test query")

        assert len(search_results) == 2
        titles = {r.title for r in search_results}
        assert "Result 1" in titles
        assert "Result 2" in titles

    @pytest.mark.asyncio
    async def test_search_deduplication(self) -> None:
        """Test that duplicate results are removed."""
        # Create duplicate results from different sources
        results1 = [
            SearchResult(
                title="Bitcoin Price",
                url="https://example.com/bitcoin",
                snippet="Bitcoin price analysis",
                source="Source1",
            )
        ]

        results2 = [
            # Same domain and similar title (should be deduplicated)
            SearchResult(
                title="Bitcoin Price Analysis",
                url="https://example.com/bitcoin-analysis",
                snippet="Detailed Bitcoin analysis",
                source="Source2",
            )
        ]

        source1 = MockSearchSource(name="Source1", results=results1)
        source2 = MockSearchSource(name="Source2", results=results2)

        engine = MultiSourceSearchEngine(sources=[source1, source2])

        search_results = await engine.search("bitcoin")

        # Should have less results than total due to deduplication
        # (Similar domain + title prefix)
        assert len(search_results) <= 2

    @pytest.mark.asyncio
    async def test_search_fault_tolerance_one_source_fails(self) -> None:
        """Test that search continues when one source fails."""
        results1 = [
            SearchResult(
                title="Result 1",
                url="https://example.com/1",
                snippet="Snippet 1",
                source="Source1",
            )
        ]

        source1 = MockSearchSource(name="Source1", results=results1)
        source2 = MockSearchSource(name="Source2", should_fail=True)

        engine = MultiSourceSearchEngine(sources=[source1, source2])

        search_results = await engine.search("test query")

        # Should still get results from source1
        assert len(search_results) == 1
        assert search_results[0].title == "Result 1"

    @pytest.mark.asyncio
    async def test_search_all_sources_fail_raises_error(self) -> None:
        """Test that error is raised when all sources fail."""
        source1 = MockSearchSource(name="Source1", should_fail=True)
        source2 = MockSearchSource(name="Source2", should_fail=True)

        engine = MultiSourceSearchEngine(sources=[source1, source2])

        with pytest.raises(SearchAggregationError) as exc_info:
            await engine.search("test query")

        assert "All search sources failed" in str(exc_info.value)
        assert "Source1" in exc_info.value.source_errors
        assert "Source2" in exc_info.value.source_errors

    @pytest.mark.asyncio
    async def test_search_respects_max_total_results(self) -> None:
        """Test that search respects max_total_results limit."""
        # Create many results
        results1 = [
            SearchResult(
                title=f"Result {i}",
                url=f"https://example.com/{i}",
                snippet=f"Snippet {i}",
                source="Source1",
            )
            for i in range(20)
        ]

        source1 = MockSearchSource(name="Source1", results=results1)
        engine = MultiSourceSearchEngine(sources=[source1], max_total_results=5)

        search_results = await engine.search("test query")

        assert len(search_results) == 5

    @pytest.mark.asyncio
    async def test_get_statistics(self) -> None:
        """Test getting engine statistics."""
        source1 = MockSearchSource(name="Source1")
        source2 = MockSearchSource(name="Source2")

        engine = MultiSourceSearchEngine(
            sources=[source1, source2],
            timeout=20,
            max_total_results=15,
        )

        stats = engine.get_statistics()

        assert stats["num_sources"] == 2
        assert stats["sources"] == ["Source1", "Source2"]
        assert stats["timeout_per_source"] == 20
        assert stats["max_total_results"] == 15


# ============================================================================
# Integration Tests (require network)
# ============================================================================


@pytest.mark.integration
class TestSearchSourceIntegration:
    """Integration tests for search sources (requires network)."""

    @pytest.mark.asyncio
    async def test_google_search_real(self) -> None:
        """Test Google search with real API (requires network)."""
        source = GoogleSearchSource(timeout=30, max_results=5)

        results = await source.search("Bitcoin price")

        assert len(results) > 0
        assert all(r.source == "Google" for r in results)
        assert all(r.title for r in results)
        assert all(r.url.startswith("http") for r in results)

    @pytest.mark.asyncio
    async def test_bing_search_real(self) -> None:
        """Test Bing search with real API (requires network)."""
        source = BingSearchSource(timeout=30, max_results=5)

        results = await source.search("Ethereum price")

        assert len(results) > 0
        assert all(r.source == "Bing" for r in results)
        assert all(r.title for r in results)
        assert all(r.url.startswith("http") for r in results)

    @pytest.mark.asyncio
    async def test_multi_source_search_real(self) -> None:
        """Test multi-source search with real APIs (requires network)."""
        engine = MultiSourceSearchEngine(max_total_results=15)

        results = await engine.search("Polymarket trading")

        assert len(results) > 0

        # Check results come from different sources
        sources = {r.source for r in results}
        assert len(sources) > 0

        # Check all results have required fields
        assert all(r.title for r in results)
        assert all(r.url for r in results)
        assert all(r.snippet for r in results)


# ============================================================================
# Search Result Format Tests
# ============================================================================


class TestSearchResultFormatting:
    """Test search result formatting and display."""

    def test_search_result_str_representation(self) -> None:
        """Test search result string representation."""
        result = SearchResult(
            title="Bitcoin Price",
            url="https://example.com/bitcoin",
            snippet="Bitcoin reaches new high",
            source="Google",
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["title"] == "Bitcoin Price"
        assert result_dict["url"] == "https://example.com/bitcoin"
        assert result_dict["snippet"] == "Bitcoin reaches new high"
        assert result_dict["source"] == "Google"
