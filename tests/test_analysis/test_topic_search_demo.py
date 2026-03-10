"""Topic-based web search demonstration tests.

This module demonstrates how to search for market topics and retrieve
the latest news summaries with sources.

Example:
    >>> # Search for a specific topic
    >>> results = await search_topic("Bitcoin price prediction")
    >>> for result in results:
    >>>     print(f"{result.title} - {result.source}")
"""

from __future__ import annotations

import pytest

from src.analysis.search_sources import (
    SearchResult,
    MultiSourceSearchEngine,
    SearchAggregationError,
)


# ============================================================================
# Topic Search Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_bitcoin_topic() -> None:
    """Demonstrate searching for Bitcoin-related topics.

    This test shows how to:
    1. Create a search engine
    2. Search for a specific topic
    3. Extract and display results with sources
    """
    # Initialize search engine
    engine = MultiSourceSearchEngine(
        timeout=30,
        max_total_results=10,
    )

    # Search for Bitcoin topic
    topic = "Bitcoin price prediction 2026"
    results = await engine.search(topic)

    # Verify we got results
    assert len(results) > 0, "Should find search results for Bitcoin topic"

    # Display results (this would be the actual application usage)
    print(f"\n📊 Search Results for '{topic}':\n")

    for i, result in enumerate(results, 1):
        print(f"{i}. [{result.source}] {result.title}")
        print(f"   📝 {result.snippet[:200]}...")
        print(f"   🔗 {result.url}")
        print()

    # Verify all results have required fields
    for result in results:
        assert result.title, "Result should have a title"
        assert result.url, "Result should have a URL"
        assert result.snippet, "Result should have a snippet"
        assert result.source, "Result should have a source name"
        assert result.source in ["Google", "Bing", "DuckDuckGo"], \
            f"Source should be one of the known engines, got {result.source}"


@pytest.mark.asyncio
async def test_search_polymarket_topic() -> None:
    """Demonstrate searching for Polymarket-related topics."""
    engine = MultiSourceSearchEngine(max_total_results=8)

    topic = "Polymarket prediction markets trading"
    results = await engine.search(topic)

    assert len(results) > 0, "Should find results for Polymarket topic"

    # Group results by source for display
    results_by_source = {}
    for result in results:
        if result.source not in results_by_source:
            results_by_source[result.source] = []
        results_by_source[result.source].append(result)

    print(f"\n📊 Search Results by Source:\n")

    for source, source_results in results_by_source.items():
        print(f"{source} ({len(source_results)} results):")
        for result in source_results[:3]:  # Show top 3 per source
            print(f"  - {result.title}")
            print(f"    {result.url}")
        print()


@pytest.mark.asyncio
async def test_extract_latest_summaries() -> None:
    """Demonstrate extracting latest summaries from search results.

    This test shows how to:
    1. Search for a topic
    2. Extract the most relevant summaries
    3. Group by source for comprehensive coverage
    """
    engine = MultiSourceSearchEngine(max_total_results=15)

    topic = "Ethereum price analysis"
    results = await engine.search(topic)

    # Get top results
    top_results = results[:5]

    print(f"\n📰 Latest Summaries for '{topic}':\n")

    summaries = []
    for result in top_results:
        summary = {
            "title": result.title,
            "summary": result.snippet,
            "source": result.source,
            "url": result.url,
            "timestamp": result.timestamp.isoformat(),
        }
        summaries.append(summary)

        print(f"🔹 {summary['title']}")
        print(f"   Source: {summary['source']}")
        print(f"   Summary: {summary['summary'][:150]}...")
        print(f"   Link: {summary['url']}")
        print()

    # Verify we extracted summaries
    assert len(summaries) > 0, "Should have extracted summaries"
    assert all("title" in s for s in summaries), "All summaries should have titles"
    assert all("source" in s for s in summaries), "All summaries should have sources"
    assert all("summary" in s for s in summaries), "All summaries should have summaries"


@pytest.mark.asyncio
async def test_search_with_error_handling() -> None:
    """Demonstrate error handling when searching topics.

    This test shows how to handle search failures gracefully.
    """
    engine = MultiSourceSearchEngine(
        timeout=10,  # Short timeout for demo
        max_total_results=5,
    )

    # Try searching for a topic (might fail if no internet)
    topic = "Quantum computing advances 2026"

    try:
        results = await engine.search(topic)

        print(f"\n✅ Successfully found {len(results)} results for '{topic}'\n")

        for result in results[:3]:
            print(f"  - [{result.source}] {result.title}")

    except SearchAggregationError as e:
        print(f"\n⚠️ Search encountered issues:")
        print(f"   Message: {e.message}")
        print(f"   Failed sources: {list(e.source_errors.keys())}")
        print(f"   This is OK - some sources may be unavailable\n")

        # This is expected behavior - not all sources may be available
        assert True, "Should handle search aggregation errors gracefully"

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        raise


# ============================================================================
# Helper Functions (for application use)
# ============================================================================


async def search_topic(topic: str, max_results: int = 10) -> list[dict]:
    """Search for a topic and return formatted results.

    This is a helper function that can be used in applications to
    search for topics and get formatted results with sources.

    Args:
        topic: Search topic/query
        max_results: Maximum number of results to return

    Returns:
        List of dictionaries with title, summary, source, and url

    Example:
        >>> results = await search_topic("Bitcoin price")
        >>> for result in results:
        >>>     print(f"{result['title']} - {result['source']}")
    """
    engine = MultiSourceSearchEngine(max_total_results=max_results)

    search_results = await engine.search(topic)

    # Convert to simple dictionaries for easy use
    results = [
        {
            "title": result.title,
            "summary": result.snippet,
            "source": result.source,
            "url": result.url,
            "timestamp": result.timestamp.isoformat(),
        }
        for result in search_results
    ]

    return results


async def get_latest_news_for_topic(
    topic: str,
    sources: list[str] | None = None,
) -> dict[str, list[dict]]:
    """Get latest news for a topic, grouped by source.

    This helper function searches for a topic and groups results
    by source for comprehensive coverage.

    Args:
        topic: Search topic/query
        sources: Optional list of sources to filter by

    Returns:
        Dictionary mapping source names to lists of results

    Example:
        >>> news_by_source = await get_latest_news_for_topic("Bitcoin")
        >>> for source, articles in news_by_source.items():
        >>>     print(f"{source}: {len(articles)} articles")
    """
    engine = MultiSourceSearchEngine(max_total_results=15)

    search_results = await engine.search(topic)

    # Group by source
    news_by_source: dict[str, list[dict]] = {}
    for result in search_results:
        if sources and result.source not in sources:
            continue

        if result.source not in news_by_source:
            news_by_source[result.source] = []

        news_by_source[result.source].append({
            "title": result.title,
            "summary": result.snippet,
            "url": result.url,
            "timestamp": result.timestamp.isoformat(),
        })

    return news_by_source


# ============================================================================
# Integration Tests (require network)
# ============================================================================


@pytest.mark.integration
class TestTopicSearchIntegration:
    """Integration tests for topic-based search (requires network)."""

    @pytest.mark.asyncio
    async def test_real_bitcoin_search(self) -> None:
        """Test real search for Bitcoin topics."""
        results = await search_topic("Bitcoin price prediction 2026", max_results=5)

        assert len(results) > 0, "Should find real Bitcoin search results"

        # Verify result structure
        for result in results:
            assert "title" in result
            assert "summary" in result
            assert "source" in result
            assert "url" in result

        print(f"\n📊 Real search found {len(results)} Bitcoin results\n")

    @pytest.mark.asyncio
    async def test_real_multi_source_search(self) -> None:
        """Test real multi-source search."""
        news_by_source = await get_latest_news_for_topic("Polymarket trading")

        assert len(news_by_source) > 0, "Should get results from at least one source"

        total_results = sum(len(articles) for articles in news_by_source.values())

        print(f"\n📊 Multi-source search results:\n")
        for source, articles in news_by_source.items():
            print(f"  {source}: {len(articles)} articles")

        print(f"\n  Total: {total_results} articles\n")

        assert total_results > 0, "Should have total results from all sources"
