"""Multi-source web search engine for market research.

This module provides a robust, fault-tolerant web search system that aggregates
results from multiple search engines in parallel. It implements fallback mechanisms
to ensure stability even when individual sources fail.

Architecture:
    - SearchSource: Abstract base class for search engines
    - GoogleSearchSource, BingSearchSource, DuckDuckGoSearchSource: Concrete implementations
    - MultiSourceSearchEngine: Aggregates and deduplicates results from multiple sources

Usage:
    from src.analysis import MultiSourceSearchEngine

    engine = MultiSourceSearchEngine()
    results = await engine.search("Bitcoin price prediction 2026")

    for result in results:
        print(f"{result.title} - {result.source}")
"""

from __future__ import annotations

__all__ = [
    "SearchResult",
    "SearchSource",
    "GoogleSearchSource",
    "BingSearchSource",
    "DuckDuckGoSearchSource",
    "BigModelSearchSource",
    "MultiSourceSearchEngine",
    "SearchAggregationError",
]

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from fake_useragent import UserAgent
from playwright_stealth import Stealth
from src.utils.logger import OPERATION_EMOJIS, get_logger


@dataclass(frozen=True)
class SearchResult:
    """Represents a single search result.

    Attributes:
        title: Result title
        url: Result URL
        snippet: Result snippet/description
        source: Search engine source name
        timestamp: When the result was found
        relevance_score: Optional relevance score (0-1)

    Example:
        >>> result = SearchResult(
        ...     title="Bitcoin reaches $100k",
        ...     url="https://example.com/article",
        ...     snippet="Bitcoin has reached...",
        ...     source="Google"
        ... )
    """

    title: str
    url: str
    snippet: str
    source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    relevance_score: float | None = None

    def __post_init__(self) -> None:
        """Validate search result data."""
        if not self.title:
            raise ValueError("Search result title cannot be empty")
        if not self.url:
            raise ValueError("Search result URL cannot be empty")

        # Validate URL format
        try:
            parsed = urlparse(self.url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"Invalid URL: {self.url}")
        except Exception as e:
            raise ValueError(f"Invalid URL format: {e}")

    def normalize_for_deduplication(self) -> str:
        """Normalize result for deduplication.

        Returns:
            Normalized string for comparison
        """
        # Use domain + first 100 chars of title for deduplication
        parsed = urlparse(self.url)
        domain = parsed.netloc.lower()
        title_prefix = self.title.lower()[:100]
        return f"{domain}:{title_prefix}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation of the result
        """
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "relevance_score": self.relevance_score,
        }


class SearchSource(ABC):
    """Abstract base class for search engines.

    All search engine implementations must inherit from this class
    and implement the search method.

    Attributes:
        name: Human-readable name of the search source
        timeout: Request timeout in seconds
        max_results: Maximum number of results to return

    Example:
        >>> class MySearchSource(SearchSource):
        ...     async def search(self, query: str) -> list[SearchResult]:
        ...         # Implementation here
        ...         return results
    """

    def __init__(
        self,
        name: str,
        timeout: int = 30,
        max_results: int = 10,
    ) -> None:
        """Initialize search source.

        Args:
            name: Human-readable name
            timeout: Request timeout in seconds
            max_results: Maximum results to return
        """
        self.name = name
        self.timeout = timeout
        self.max_results = max_results
        self._logger = get_logger(__name__)
        self._ua_generator = UserAgent()

    @abstractmethod
    async def search(self, query: str) -> list[SearchResult]:
        """Perform search and return results.

        Args:
            query: Search query string

        Returns:
            List of search results

        Raises:
            Exception: If search fails (will be caught by aggregator)
        """
        pass

    def _is_available(self) -> bool:
        """Check if the search source is available.

        Can be overridden by subclasses to implement custom availability checks.

        Returns:
            True if available, False otherwise
        """
        return True

    def __repr__(self) -> str:
        """Return string representation."""
        return f"{self.__class__.__name__}(name='{self.name}', timeout={self.timeout})"


class GoogleSearchSource(SearchSource):
    """Google search engine implementation.

    Uses Playwright to scrape Google search results.

    Example:
        >>> source = GoogleSearchSource(timeout=30)
        >>> results = await source.search("Bitcoin price")
    """

    def __init__(
        self,
        timeout: int = 30,
        max_results: int = 10,
        proxy_url: str | None = None,
    ) -> None:
        """Initialize Google search source.

        Args:
            timeout: Request timeout in seconds
            max_results: Maximum results to return
            proxy_url: Optional proxy server URL
        """
        super().__init__(name="Google", timeout=timeout, max_results=max_results)
        self._proxy_url = proxy_url

    async def search(self, query: str) -> list[SearchResult]:
        """Perform Google search.

        Args:
            query: Search query

        Returns:
            List of search results from Google

        Raises:
            ImportError: If Playwright is not installed
            Exception: If search fails
        """
        self._logger.debug(
            f"{OPERATION_EMOJIS['analysis']} Google search: {query[:50]}..."
        )
        self._logger.info(
            f"🔍 Google: proxy={self._proxy_url}, timeout={self.timeout}s"
        )

        try:
            from playwright.async_api import async_playwright

            self._logger.debug("🌐 Launching Chromium browser...")
            async with async_playwright() as p:
                browser_args = {
                    "headless": True,
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-web-security",
                        "--disable-features=IsolateOrigins,site-per-process",
                    ]
                }

                if self._proxy_url:
                    browser_args["proxy"] = {"server": self._proxy_url}
                    self._logger.debug(f"🔐 Using proxy: {self._proxy_url}")
                else:
                    self._logger.warning("⚠️ No proxy configured - may fail for international search engines")

                browser = await p.chromium.launch(**browser_args)
                self._logger.debug("✅ Browser launched successfully")

                try:
                    # Create context with random realistic user agent
                    random_ua = self._ua_generator.random
                    self._logger.debug(f"🎭 Using User-Agent: {random_ua[:50]}...")

                    context = await browser.new_context(
                        user_agent=random_ua,
                        viewport={"width": 1920, "height": 1080},
                        locale="en-US",
                    )

                    # Apply stealth to the entire context
                    stealth = Stealth()
                    await stealth.apply_stealth_async(context)
                    self._logger.debug("✅ Stealth applied to context")

                    page = await context.new_page()
                    page.set_default_timeout(self.timeout * 1000)
                    self._logger.debug("✅ New page created with realistic headers")

                    # Build Google search URL
                    from urllib.parse import quote_plus

                    search_url = f"https://www.google.com/search?q={quote_plus(query)}&hl=en"
                    self._logger.debug(f"🔗 Navigating to: {search_url}")

                    await page.goto(search_url)
                    self._logger.debug("✅ Page loaded, waiting for network idle...")

                    await page.wait_for_load_state("networkidle")
                    self._logger.debug("✅ Network idle achieved")

                    # Extract results
                    results = await self._extract_results(page)

                    self._logger.info(
                        f"✅ Google found {len(results)} results"
                    )
                    return results

                finally:
                    await browser.close()
                    self._logger.debug("🔚 Browser closed")

        except ImportError as e:
            self._logger.error(f"❌ Playwright not installed: {e}")
            raise
        except Exception as e:
            self._logger.warning(f"❌ Google search failed: {e}")
            raise

    async def _extract_results(self, page: Any) -> list[SearchResult]:
        """Extract results from Google search page.

        Args:
            page: Playwright page object

        Returns:
            List of search results
        """
        results = []

        try:
            self._logger.warning("=========google body==========")

            content = await page.content()


            self._logger.warning(f"content: {content}")
            # snapshot = await page.accessibility.snapshot()
            # self._logger.warning(f"snapshot: {snapshot}")

            self._logger.warning("=========google body end==========")

            self._logger.debug("🔍 Looking for search results...")

            # Try multiple selectors for Google results
            selectors = [
                "div.g",              # Standard Google results
                "div[data-hveid]",    # Alternative Google results
                "div.tF2Cxc",         # Another Google result format
                "div.yuRUbf",         # Another Google result format
            ]

            search_results = []
            for selector in selectors:
                found = await page.query_selector_all(selector)
                if found:
                    self._logger.debug(f"📊 Found {len(found)} elements with selector: {selector}")
                    search_results = found
                    break
                else:
                    self._logger.debug(f"⚠️ No elements found with selector: {selector}")

            if not search_results:
                self._logger.warning("⚠️ No search result elements found - Google may have changed their page structure")
                # Get page content for debugging
                page_content = await page.content()
                self._logger.debug(f"Page content length: {len(page_content)} chars")

                # Check for common Google detection pages
                if "unusual traffic" in page_content.lower() or "please verify you are a human" in page_content.lower():
                    self._logger.warning("⚠️ Google detected automated access - may need to adjust approach")
                elif "captcha" in page_content.lower():
                    self._logger.warning("⚠️ Google is showing a CAPTCHA")

                return []

            self._logger.debug(f"📊 Processing {len(search_results)} result elements")

            for i, result in enumerate(search_results[: self.max_results]):
                try:
                    # Try multiple selectors for title
                    title_elem = await result.query_selector("h3")
                    if not title_elem:
                        title_elem = await result.query_selector("h2")
                    if not title_elem:
                        title_elem = await result.query_selector("[role='heading']")

                    title = await title_elem.inner_text() if title_elem else "N/A"

                    # Try multiple selectors for URL
                    link_elem = await result.query_selector("a")
                    if not link_elem:
                        link_elem = await result.query_selector("[href]")

                    url = await link_elem.get_attribute("href") if link_elem else "N/A"

                    # Try multiple selectors for snippet
                    snippet_selectors = [
                        ".VwiC3b",
                        ".st",
                        ".s3v9kd",
                        ".ITZqW",
                        "[data-hveid] span",
                    ]

                    snippet = "N/A"
                    for snippet_selector in snippet_selectors:
                        snippet_elem = await result.query_selector(snippet_selector)
                        if snippet_elem:
                            snippet = await snippet_elem.inner_text()
                            break

                    self._logger.debug(f"  Result {i+1}: title={title[:30]}..., url={url[:50] if url != 'N/A' else 'N/A'}...")

                    # Filter out invalid results
                    if title != "N/A" and url != "N/A" and url.startswith("http"):
                        results.append(
                            SearchResult(
                                title=title.strip(),
                                url=url,
                                snippet=snippet.strip() if snippet != "N/A" else "",
                                source=self.name,
                            )
                        )
                    else:
                        self._logger.debug(f"  ⚠️ Skipped invalid result: title={title}, url={url}")

                except Exception as e:
                    self._logger.debug(f"  ❌ Failed to extract result {i+1}: {e}")
                    continue

        except Exception as e:
            self._logger.warning(f"❌ Failed to extract Google results: {e}")

        return results


class BingSearchSource(SearchSource):
    """Bing search engine implementation.

    Uses Playwright to scrape Bing search results.

    Example:
        >>> source = BingSearchSource(timeout=30)
        >>> results = await source.search("Bitcoin price")
    """

    def __init__(
        self,
        timeout: int = 30,
        max_results: int = 10,
        proxy_url: str | None = None,
    ) -> None:
        """Initialize Bing search source.

        Args:
            timeout: Request timeout in seconds
            max_results: Maximum results to return
            proxy_url: Optional proxy server URL
        """
        super().__init__(name="Bing", timeout=timeout, max_results=max_results)
        self._proxy_url = proxy_url

    async def search(self, query: str) -> list[SearchResult]:
        """Perform Bing search.

        Args:
            query: Search query

        Returns:
            List of search results from Bing

        Raises:
            ImportError: If Playwright is not installed
            Exception: If search fails
        """
        self._logger.debug(
            f"{OPERATION_EMOJIS['analysis']} Bing search: {query[:50]}..."
        )
        self._logger.info(
            f"🔍 Bing: proxy={self._proxy_url}, timeout={self.timeout}s"
        )

        try:
            from playwright.async_api import async_playwright

            self._logger.debug("🌐 Launching Chromium browser...")
            async with async_playwright() as p:
                browser_args = {
                    "headless": True,
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                    ]
                }

                if self._proxy_url:
                    browser_args["proxy"] = {"server": self._proxy_url}
                    self._logger.debug(f"🔐 Using proxy: {self._proxy_url}")
                else:
                    self._logger.warning("⚠️ No proxy configured - may fail for international search engines")

                browser = await p.chromium.launch(**browser_args)
                self._logger.debug("✅ Browser launched successfully")

                try:
                    # Create context with random realistic user agent
                    random_ua = self._ua_generator.random
                    self._logger.debug(f"🎭 Using User-Agent: {random_ua[:50]}...")

                    context = await browser.new_context(
                        user_agent=random_ua,
                        viewport={"width": 1920, "height": 1080},
                    )

                    # Apply stealth to the entire context
                    stealth = Stealth()
                    await stealth.apply_stealth_async(context)
                    self._logger.debug("✅ Stealth applied to context")

                    page = await context.new_page()
                    page.set_default_timeout(self.timeout * 1000)
                    self._logger.debug("✅ New page created with realistic headers")

                    # Build Bing search URL
                    from urllib.parse import quote_plus

                    search_url = f"https://www.bing.com/search?q={quote_plus(query)}"
                    self._logger.debug(f"🔗 Navigating to: {search_url}")

                    await page.goto(search_url)
                    self._logger.debug("✅ Page loaded, waiting for network idle...")

                    await page.wait_for_load_state("networkidle")
                    self._logger.debug("✅ Network idle achieved")

                    # Extract results
                    results = await self._extract_results(page)

                    self._logger.info(
                        f"✅ Bing found {len(results)} results"
                    )
                    return results

                finally:
                    await browser.close()
                    self._logger.debug("🔚 Browser closed")

        except ImportError as e:
            self._logger.error(f"❌ Playwright not installed: {e}")
            raise
        except Exception as e:
            self._logger.warning(f"❌ Bing search failed: {e}")
            raise

    async def _extract_results(self, page: Any) -> list[SearchResult]:
        """Extract results from Bing search page.

        Args:
            page: Playwright page object

        Returns:
            List of search results
        """
        results = []

        try:
            self._logger.warning("=========bing body==========")

            content = await page.content()


            self._logger.warning(f"content: {content}")
            # snapshot = await page.accessibility.snapshot()
            # self._logger.warning(f"snapshot: {snapshot}")

            self._logger.warning("=========bing body end==========")

            search_results = await page.query_selector_all("li.b_algo")

            for result in search_results[: self.max_results]:
                try:
                    # Extract title
                    title_elem = await result.query_selector("h2 a")
                    title = await title_elem.inner_text() if title_elem else "N/A"

                    # Extract URL
                    link_elem = await result.query_selector("h2 a")
                    url = await link_elem.get_attribute("href") if link_elem else "N/A"

                    # Extract snippet
                    snippet_elem = await result.query_selector("p, .b_caption p")
                    snippet = await snippet_elem.inner_text() if snippet_elem else "N/A"

                    # Filter out invalid results
                    if title != "N/A" and url != "N/A" and url.startswith("http"):
                        results.append(
                            SearchResult(
                                title=title.strip(),
                                url=url,
                                snippet=snippet.strip(),
                                source=self.name,
                            )
                        )

                except Exception as e:
                    self._logger.debug(f"Failed to extract result: {e}")
                    continue

        except Exception as e:
            self._logger.warning(f"Failed to extract Bing results: {e}")

        return results


class DuckDuckGoSearchSource(SearchSource):
    """DuckDuckGo search engine implementation.

    Uses Playwright to scrape DuckDuckGo search results.

    Example:
        >>> source = DuckDuckGoSearchSource(timeout=30)
        >>> results = await source.search("Bitcoin price")
    """

    def __init__(
        self,
        timeout: int = 30,
        max_results: int = 10,
        proxy_url: str | None = None,
    ) -> None:
        """Initialize DuckDuckGo search source.

        Args:
            timeout: Request timeout in seconds
            max_results: Maximum results to return
            proxy_url: Optional proxy server URL
        """
        super().__init__(name="DuckDuckGo", timeout=timeout, max_results=max_results)
        self._proxy_url = proxy_url

    async def search(self, query: str) -> list[SearchResult]:
        """Perform DuckDuckGo search.

        Args:
            query: Search query

        Returns:
            List of search results from DuckDuckGo

        Raises:
            ImportError: If Playwright is not installed
            Exception: If search fails
        """
        self._logger.debug(
            f"{OPERATION_EMOJIS['analysis']} DuckDuckGo search: {query[:50]}..."
        )
        self._logger.info(
            f"🔍 DuckDuckGo: proxy={self._proxy_url}, timeout={self.timeout}s"
        )

        try:
            from playwright.async_api import async_playwright

            self._logger.debug("🌐 Launching Chromium browser...")
            async with async_playwright() as p:
                browser_args = {
                    "headless": True,
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                    ]
                }

                if self._proxy_url:
                    browser_args["proxy"] = {"server": self._proxy_url}
                    self._logger.debug(f"🔐 Using proxy: {self._proxy_url}")
                else:
                    self._logger.warning("⚠️ No proxy configured - may fail for international search engines")

                browser = await p.chromium.launch(**browser_args)
                self._logger.debug("✅ Browser launched successfully")

                try:
                    # Create context with random realistic user agent
                    random_ua = self._ua_generator.random
                    self._logger.debug(f"🎭 Using User-Agent: {random_ua[:50]}...")

                    context = await browser.new_context(
                        user_agent=random_ua,
                        viewport={"width": 1920, "height": 1080},
                    )

                    # Apply stealth to the entire context
                    stealth = Stealth()
                    await stealth.apply_stealth_async(context)
                    self._logger.debug("✅ Stealth applied to context")

                    page = await context.new_page()
                    page.set_default_timeout(self.timeout * 1000)
                    self._logger.debug("✅ New page created with realistic headers")

                    # Build DuckDuckGo search URL
                    from urllib.parse import quote_plus

                    search_url = f"https://duckduckgo.com/?q={quote_plus(query)}"
                    self._logger.debug(f"🔗 Navigating to: {search_url}")

                    await page.goto(search_url)
                    self._logger.debug("✅ Page loaded, waiting for network idle...")

                    await page.wait_for_load_state("networkidle")
                    self._logger.debug("✅ Network idle achieved")

                    # Extract results
                    results = await self._extract_results(page)

                    self._logger.info(
                        f"✅ DuckDuckGo found {len(results)} results"
                    )
                    return results

                finally:
                    await browser.close()
                    self._logger.debug("🔚 Browser closed")

        except ImportError as e:
            self._logger.error(f"❌ Playwright not installed: {e}")
            raise
        except Exception as e:
            self._logger.warning(f"❌ DuckDuckGo search failed: {e}")
            raise

    async def _extract_results(self, page: Any) -> list[SearchResult]:
        """Extract results from DuckDuckGo search page.

        Args:
            page: Playwright page object

        Returns:
            List of search results
        """
        results = []

        try:
            self._logger.warning("=========duckduckgo body==========")

            content = await page.content()

            
            self._logger.warning(f"content: {content}")
            #snapshot = await page.accessibility.snapshot()
            # self._logger.warning(f"snapshot: {snapshot}")
            
            self._logger.warning("=========duckduckgo body end==========")

            search_results = await page.query_selector_all("div.web-result")

            for result in search_results[: self.max_results]:
                try:
                    # Extract title
                    title_elem = await result.query_selector("a.result__a")
                    title = await title_elem.inner_text() if title_elem else "N/A"

                    # Extract URL
                    link_elem = await result.query_selector("a.result__a")
                    url = await link_elem.get_attribute("href") if link_elem else "N/A"

                    # Extract snippet
                    snippet_elem = await result.query_selector(".result__snippet")
                    snippet = await snippet_elem.inner_text() if snippet_elem else "N/A"

                    # Filter out invalid results
                    if title != "N/A" and url != "N/A" and url.startswith("http"):
                        results.append(
                            SearchResult(
                                title=title.strip(),
                                url=url,
                                snippet=snippet.strip(),
                                source=self.name,
                            )
                        )

                except Exception as e:
                    self._logger.debug(f"Failed to extract result: {e}")
                    continue

        except Exception as e:
            self._logger.warning(f"Failed to extract DuckDuckGo results: {e}")

        return results


class BigModelSearchSource(SearchSource):
    """BigModel (智谱AI) search engine implementation.

    Uses ZhipuAI's web_search API for intelligent search.

    Example:
        >>> source = BigModelSearchSource(api_key="your_api_key")
        >>> results = await source.search("Bitcoin price")
    """

    def __init__(
        self,
        timeout: int = 30,
        max_results: int = 10,
        api_key: str | None = None,
    ) -> None:
        """Initialize BigModel search source.

        Args:
            timeout: Request timeout in seconds
            max_results: Maximum results to return
            api_key: ZhipuAI API key (optional, will use env if not provided)
        """
        super().__init__(name="BigModel", timeout=timeout, max_results=max_results)
        self._api_key = api_key

    async def search(self, query: str) -> list[SearchResult]:
        """Perform BigModel web search.

        Tries direct web_search API first, falls back to chat completions with web_search tool.

        Args:
            query: Search query

        Returns:
            List of search results from BigModel

        Raises:
            ImportError: If zai-sdk is not installed
            Exception: If search fails
        """
        self._logger.debug(
            f"{OPERATION_EMOJIS['analysis']} BigModel search: {query[:50]}..."
        )
        self._logger.info(
            f"🔍 BigModel: timeout={self.timeout}s"
        )

        try:
            # Try direct API first (more reliable)
            # try:
            #     results = await self._search_with_direct_api(query)
            #     if results:
            #         return results
            # except Exception as e:
            #     self._logger.debug(f"Direct API failed, trying chat method: {e}")

            # Fallback to chat completions with web_search tool
            return await self._search_with_chat_tool(query)

        except ImportError as e:
            self._logger.error(f"❌ zai-sdk not installed: {e}")
            self._logger.error("💡 Install with: pip install zai-sdk")
            raise
        except Exception as e:
            self._logger.warning(f"❌ BigModel search failed: {e}")
            raise

    async def _search_with_direct_api(self, query: str) -> list[SearchResult]:
        """Search using direct web_search API.

        Args:
            query: Search query

        Returns:
            List of search results
        """
        from zai import ZhipuAiClient

        # Use provided API key or get from settings
        if not self._api_key:
            from src.config import settings
            self._api_key = settings.web_research.bigmodel_api_key

        if not self._api_key:
            self._logger.error("❌ BigModel API key not configured")
            raise ValueError("BigModel API key not configured. Please set WEB_RESEARCH_BIGMODEL_API_KEY in .env")

        self._logger.debug("🔑 Using BigModel direct API")

        # Initialize client
        client = ZhipuAiClient(api_key=self._api_key)
        self._logger.debug("✅ BigModel client initialized")

        # Call direct web_search API
        self._logger.debug(f"🔍 Searching for: {query[:100]}...")

        response = client.web_search.web_search(
            search_engine="search_pro",
            search_query=query,
            count=min(self.max_results, 50),
            search_recency_filter="noLimit",
            content_size="high"
        )

        self._logger.debug(f"✅ Got response from BigModel direct API")

        # Parse results from response.search_result
        results = []

        # Check if response has search_result attribute
        if hasattr(response, 'search_result'):
            search_results = response.search_result
            self._logger.debug(f"📦 Found search_result with {len(search_results)} items")

            for item in search_results[:self.max_results]:
                try:
                    # Extract from SearchResultResp object
                    title = getattr(item, 'title', 'N/A')
                    url = getattr(item, 'link', 'N/A')
                    snippet = getattr(item, 'content', '')

                    # Filter out invalid results
                    if title != 'N/A' and url != 'N/A' and url.startswith('http'):
                        results.append(
                            SearchResult(
                                title=title.strip(),
                                url=url,
                                snippet=snippet.strip() if snippet else '',
                                source=self.name,
                            )
                        )
                        self._logger.debug(f"  ✓ Result: {title[:50]}...")

                except Exception as e:
                    self._logger.debug(f"  ❌ Failed to parse result: {e}")
                    continue
        else:
            self._logger.warning(f"⚠️ Response has no 'search_result' attribute")
            self._logger.warning(f"📦 Available attributes: {[attr for attr in dir(response) if not attr.startswith('_')][:20]}")
            return []

        self._logger.info(f"✅ BigModel direct API found {len(results)} results")
        return results

    async def _search_with_chat_tool(self, query: str) -> list[SearchResult]:
        """Search using chat completions with web_search tool.

        Args:
            query: Search query

        Returns:
            List of search results
        """
        from zai import ZhipuAiClient

        # Use provided API key or get from settings
        if not self._api_key:
            from src.config import settings
            self._api_key = settings.web_research.bigmodel_api_key

        if not self._api_key:
            self._logger.error("❌ BigModel API key not configured")
            raise ValueError("BigModel API key not configured. Please set WEB_RESEARCH_BIGMODEL_API_KEY in .env")

        self._logger.debug("🔑 Using BigModel chat completions with web_search tool")

        # Initialize client
        client = ZhipuAiClient(api_key=self._api_key)
        self._logger.debug("✅ BigModel client initialized")

        # Call chat.completions.create with web_search tool
        self._logger.debug(f"🔍 Searching for: {query[:100]}...")

        response = client.chat.completions.create(
            model="glm-4-air",
            messages=[
                {
                    "role": "user",
                    "content": f"我想预测研究'{query}', 分别用中文和英文的方式，搜索你认为与主题强相关的信息" 
                }
            ],
            tools=[
                {
                    "type": "web_search",
                    "web_search": {
                        "search_query": query,
                        "search_result": "True",
                        "search_prompt": f"你是一个舆情新闻分析师, 请用简洁的语言总监网络搜索{{search_result}}的信息，按日期和重要性倒叙排序，今天日期是, {datetime.now().strftime('%Y-%m-%d')}",
                        "count": "5"
                    }
                }
            ],
            temperature=0.7,
        )

        self._logger.debug(f"✅ Got response from BigModel chat completions, response: {response}")

        # Parse results from response
        results = []

        # BigModel returns web_search results directly in the response object
        if hasattr(response, 'web_search') and response.web_search:
            search_results = response.web_search
            self._logger.debug(f"📦 Found web_search with {len(search_results)} items")

            if isinstance(search_results, list):
                for item in search_results[:self.max_results]:
                    try:
                        # Extract result fields from dict
                        if isinstance(item, dict):
                            title = item.get('title', 'N/A')
                            url = item.get('link', item.get('url', 'N/A'))
                            snippet = item.get('content', item.get('description', ''))

                            # Filter out invalid results
                            if title != 'N/A' and url != 'N/A' and url.startswith('http'):
                                results.append(
                                    SearchResult(
                                        title=title.strip(),
                                        url=url,
                                        snippet=snippet.strip() if snippet else '',
                                        source=self.name,
                                    )
                                )
                                self._logger.debug(f"  ✓ Result: {title[:50]}...")

                    except Exception as e:
                        self._logger.debug(f"  ❌ Failed to parse result: {e}")
                        continue

        self._logger.info(f"✅ BigModel chat completions found {len(results)} results")

        # If no results from tool calls, try to extract from content
        if not results and response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            self._logger.debug(f"📝 Response content: {content[:200]}...")

        return results


class SearchAggregationError(Exception):
    """Raised when all search sources fail.

    Attributes:
        message: Error message
        source_errors: Dictionary of source names to their errors
    """

    def __init__(self, message: str, source_errors: dict[str, Exception]) -> None:
        """Initialize aggregation error.

        Args:
            message: Error message
            source_errors: Dictionary of source errors
        """
        self.message = message
        self.source_errors = source_errors
        super().__init__(message)

    def __str__(self) -> str:
        """Return string representation."""
        error_summary = ", ".join(self.source_errors.keys())
        return f"{self.message} (failed sources: {error_summary})"


class MultiSourceSearchEngine:
    """Multi-source search engine with fault tolerance.

    Aggregates results from multiple search sources in parallel.
    Implements fallback mechanisms to ensure stability.

    Features:
        - Parallel search across multiple sources
        - Automatic deduplication of results
        - Fault tolerance (continues if some sources fail)
        - Configurable timeout and result limits

    Attributes:
        _sources: List of search sources
        _timeout: Per-source timeout in seconds
        _max_total_results: Maximum total results to return

    Example:
        >>> engine = MultiSourceSearchEngine()
        >>> results = await engine.search("Bitcoin price prediction 2026")
        >>> print(f"Found {len(results)} unique results")
    """

    def __init__(
        self,
        sources: list[SearchSource] | None = None,
        timeout: int = 30,
        max_total_results: int = 20,
    ) -> None:
        """Initialize multi-source search engine.

        Args:
            sources: List of search sources (None = use all defaults)
            timeout: Per-source timeout in seconds
            max_total_results: Maximum total results to return
        """
        self._logger = get_logger(__name__)
        self._timeout = timeout
        self._max_total_results = max_total_results

        # Default to all available sources if none specified
        # Note: BigModel is prioritized as it uses official API (most reliable)
        if sources is None:
            from src.config import settings

            proxy_url = settings.web_research.proxy_url
            sources = [
                # Start with BigModel API (most reliable, no anti-scraping issues)
                BigModelSearchSource(timeout=timeout, max_results=10),
                # Fallback to Playwright-based engines (if BigModel fails)
                # BingSearchSource(timeout=timeout, max_results=10, proxy_url=proxy_url),
                # DuckDuckGoSearchSource(
                    # timeout=timeout, max_results=10, proxy_url=proxy_url
                # ),
                # Google last, as it's more likely to detect automation
                # GoogleSearchSource(timeout=timeout, max_results=10, proxy_url=proxy_url),
            ]

        self._sources = sources
        self._logger.info(
            f"{OPERATION_EMOJIS['analysis']} MultiSourceSearchEngine initialized with "
            f"{len(sources)} sources: {[s.name for s in sources]}"
        )

    async def search(self, query: str) -> list[SearchResult]:
        """Search across all sources and return aggregated results.

        Args:
            query: Search query string

        Returns:
            Deduplicated list of search results from all sources

        Raises:
            SearchAggregationError: If all search sources fail
        """
        self._logger.info(
            f"{OPERATION_EMOJIS['analysis']} Starting multi-source search: {query[:50]}..."
        )

        # Execute searches in parallel
        search_tasks = {
            source.name: asyncio.create_task(source.search(query))
            for source in self._sources
        }

        # Wait for all searches to complete (with timeout)
        results_by_source: dict[str, list[SearchResult]] = {}
        errors_by_source: dict[str, Exception] = {}

        done, pending = await asyncio.wait(
            search_tasks.values(),
            timeout=self._timeout * len(self._sources),
            return_when=asyncio.ALL_COMPLETED,
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()

        # Collect results and errors
        for source_name, task in search_tasks.items():
            try:
                if task.done():
                    results_by_source[source_name] = task.result()
                else:
                    errors_by_source[source_name] = TimeoutError(
                        f"Search timed out after {self._timeout}s"
                    )
            except Exception as e:
                errors_by_source[source_name] = e
                self._logger.warning(f"{source_name} search failed: {e}")

        # Check if all sources failed
        if not results_by_source:
            raise SearchAggregationError(
                message="All search sources failed",
                source_errors=errors_by_source,
            )

        # Aggregate and deduplicate results
        aggregated_results = self._aggregate_and_deduplicate(results_by_source)

        self._logger.info(
            f"{OPERATION_EMOJIS['analysis']} Search complete: "
            f"{len(aggregated_results)} unique results from "
            f"{len(results_by_source)}/{len(self._sources)} sources"
        )

        # Log any failures
        if errors_by_source:
            self._logger.warning(
                f"{OPERATION_EMOJIS['analysis']} Failed sources: {list(errors_by_source.keys())}"
            )

        return aggregated_results[: self._max_total_results]

    def _aggregate_and_deduplicate(
        self, results_by_source: dict[str, list[SearchResult]]
    ) -> list[SearchResult]:
        """Aggregate and deduplicate results from multiple sources.

        Args:
            results_by_source: Dictionary of source names to their results

        Returns:
            Deduplicated list of search results
        """
        all_results: list[SearchResult] = []
        seen_normalizations: set[str] = set()

        # Collect results from all sources
        for source_name, results in results_by_source.items():
            for result in results:
                # Check for duplicates
                normalized = result.normalize_for_deduplication()
                if normalized not in seen_normalizations:
                    seen_normalizations.add(normalized)
                    all_results.append(result)
                else:
                    self._logger.debug(
                        f"Filtered duplicate result from {source_name}: {result.title[:50]}..."
                    )

        return all_results

    def get_statistics(self) -> dict[str, Any]:
        """Get engine statistics.

        Returns:
            Dictionary with engine information
        """
        return {
            "num_sources": len(self._sources),
            "sources": [source.name for source in self._sources],
            "timeout_per_source": self._timeout,
            "max_total_results": self._max_total_results,
        }
