"""Debug script to test web research functionality."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.web_researcher import WebResearcher
from src.config import settings


async def test_web_research():
    """Test web research with actual market titles."""

    print("=" * 60)
    print("Testing Web Research Functionality")
    print("=" * 60)

    # Check settings
    print(f"\n📋 Web Research Settings:")
    print(f"  Enabled: {settings.web_research.enabled}")
    print(f"  Proxy URL: {settings.web_research.proxy_url}")
    print(f"  Search Engine: {settings.web_research.search_engine}")
    print(f"  Max Results: {settings.web_research.max_results}")
    print(f"  Timeout: {settings.web_research.timeout_seconds}s")

    if not settings.web_research.enabled:
        print("\n❌ Web research is DISABLED in settings!")
        return

    # Test cases from failed predictions
    test_cases = [
        "Will the Fed increase interest rates by 25+ bps after the March 2026 meeting?",
        "Will Chelsea win the 2025–26 English Premier League?"
    ]

    researcher = WebResearcher()

    for i, query in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"Test {i}: {query[:60]}...")
        print(f"{'=' * 60}")

        try:
            result = await researcher.research_market(
                market_title=query,
                description=None
            )

            print(f"\n✅ Research completed successfully!")
            print(f"Result length: {len(result)} characters")
            print(f"\n📄 Research Result:")
            print("-" * 60)
            print(result)
            print("-" * 60)

            # Check if result indicates failure
            if "No search results found" in result or not result.strip():
                print("\n⚠️ WARNING: Research returned empty or failed result!")

        except Exception as e:
            print(f"\n❌ Research failed with error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_web_research())
