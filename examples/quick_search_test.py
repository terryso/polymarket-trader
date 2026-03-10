#!/usr/bin/env python3
"""Quick search test with detailed logging.

Usage:
    uv run python examples/quick_search_test.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)


async def test_google_search() -> None:
    """Test Google search with detailed logging."""
    from src.analysis import GoogleSearchSource
    from src.config import settings

    print("\n" + "="*80)
    print("🔍 Google Search Test with Detailed Logging")
    print("="*80 + "\n")

    print("Configuration:")
    print(f"  Proxy: {settings.web_research.proxy_url}")
    print(f"  Timeout: {settings.web_research.timeout_seconds}s")
    print(f"  Max Results: {settings.web_research.max_results}\n")

    print("⏳ Starting Google search...\n")

    try:
        source = GoogleSearchSource(
            timeout=30,
            max_results=5,
            proxy_url=settings.web_research.proxy_url,
        )

        results = await source.search("Bitcoin price")

        print(f"\n{'='*80}")
        print(f"📊 Search Results")
        print(f"{'='*80}\n")

        if results:
            print(f"✅ Found {len(results)} results:\n")

            for i, result in enumerate(results, 1):
                print(f"{i}. {result.title}")
                print(f"   URL: {result.url}")
                print(f"   Snippet: {result.snippet[:100]}...")
                print(f"   Source: {result.source}\n")
        else:
            print("❌ No results found")
            print("\nPossible issues:")
            print("  1. Google page structure changed (try alternative selectors)")
            print("  2. Google detected automated access (try different approach)")
            print("  3. Network/connectivity issues\n")

    except Exception as e:
        print(f"\n❌ Search failed: {e}\n")


if __name__ == "__main__":
    asyncio.run(test_google_search())
