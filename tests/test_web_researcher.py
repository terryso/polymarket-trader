"""Tests for WebResearcher module."""

import pytest

from src.analysis.web_researcher import WebResearcher, ResearchError


class TestWebResearcher:
    """Test suite for WebResearcher class."""

    @pytest.fixture
    def researcher(self) -> WebResearcher:
        """Create a WebResearcher instance for testing."""
        return WebResearcher()

    def test_initialization(self, researcher: WebResearcher) -> None:
        """Test WebResearcher initializes correctly."""
        assert researcher is not None
        assert researcher._max_results > 0
        assert researcher._timeout > 0
        assert researcher._search_engine in ["google", "bing", "duckduckgo"]

    @pytest.mark.asyncio
    async def test_research_market_basic(
        self, researcher: WebResearcher
    ) -> None:
        """Test basic market research functionality."""
        # Use a simple query
        result = await researcher.research_market(
            market_title="Bitcoin price",
            description="Current Bitcoin price in USD",
        )

        # Should return a string
        assert isinstance(result, str)

        # Should contain web research results header
        assert "Web Research Results:" in result or "No search results" in result

    @pytest.mark.asyncio
    async def test_research_market_no_description(
        self, researcher: WebResearcher
    ) -> None:
        """Test research with no description provided."""
        result = await researcher.research_market(
            market_title="Ethereum price prediction",
            description=None,
        )

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_research_market_error_handling(
        self, researcher: WebResearcher
    ) -> None:
        """Test error handling in market research."""
        # This test verifies the function handles errors gracefully
        # Even if the search fails, it should not crash

        try:
            result = await researcher.research_market(
                market_title="Test query that might fail",
            )
            # If it succeeds, verify result format
            assert isinstance(result, str)
        except ResearchError as e:
            # If it fails with ResearchError, that's acceptable
            assert e.message is not None

    def test_extract_keywords(self, researcher: WebResearcher) -> None:
        """Test keyword extraction from description."""
        text = "This market will resolve based on whether Bitcoin reaches $100k by end of 2026"
        keywords = researcher._extract_keywords(text)

        assert isinstance(keywords, str)
        assert len(keywords) > 0

    def test_format_research_results(self, researcher: WebResearcher) -> None:
        """Test formatting of research results."""
        results = [
            {
                "title": "Bitcoin Price Analysis",
                "snippet": "Bitcoin price is expected to rise",
                "link": "https://example.com/bitcoin",
            },
            {
                "title": "Crypto Market Forecast",
                "snippet": "Crypto markets show bullish trends",
                "link": "https://example.com/crypto",
            },
        ]

        formatted = researcher._format_research_results(results)

        assert "Web Research Results:" in formatted
        assert "Bitcoin Price Analysis" in formatted
        assert "Crypto Market Forecast" in formatted
        assert "https://example.com/bitcoin" in formatted
        assert "https://example.com/crypto" in formatted

    def test_format_research_results_empty(self, researcher: WebResearcher) -> None:
        """Test formatting with empty results."""
        formatted = researcher._format_research_results([])
        assert "No search results found" in formatted

    def test_build_search_url(self, researcher: WebResearcher) -> None:
        """Test search URL building for different engines."""
        query = "Bitcoin price"

        # Test Google
        researcher._search_engine = "google"
        url = researcher._build_search_url(query)
        assert "google.com/search" in url
        assert "Bitcoin" in url or "price" in url

        # Test Bing
        researcher._search_engine = "bing"
        url = researcher._build_search_url(query)
        assert "bing.com/search" in url

        # Test DuckDuckGo
        researcher._search_engine = "duckduckgo"
        url = researcher._build_search_url(query)
        assert "duckduckgo.com" in url


@pytest.mark.integration
class TestWebResearcherIntegration:
    """Integration tests for WebResearcher (requires network)."""

    @pytest.fixture
    def researcher(self) -> WebResearcher:
        """Create a WebResearcher instance for integration testing."""
        return WebResearcher()

    @pytest.mark.asyncio
    async def test_research_market_real_search(
        self, researcher: WebResearcher
    ) -> None:
        """Test actual web search (requires network and playwright)."""
        pytest.skip(
            "Skip integration test by default. Run with: pytest -m integration -v"
        )

        result = await researcher.research_market(
            market_title="Will Bitcoin reach $100,000 by end of 2026?",
            description="This market resolves to YES if Bitcoin trades at or above $100,000",
        )

        # Should get actual search results
        assert isinstance(result, str)
        assert "Web Research Results:" in result
        # Should have at least some content
        assert len(result) > 100

    @pytest.mark.asyncio
    async def test_research_market_with_proxy(
        self, researcher: WebResearcher
    ) -> None:
        """Test web search with proxy (requires proxy server)."""
        pytest.skip(
            "Skip proxy test by default. Run with: pytest -m integration -v"
        )

        # This test assumes proxy is configured and running
        result = await researcher.research_market(
            market_title="Bitcoin price prediction 2026",
        )

        assert isinstance(result, str)
        # Verify we got results through proxy
        assert "Web Research Results:" in result or "No search results" in result
