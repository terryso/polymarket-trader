#!/usr/bin/env python3
"""Demo script for WebResearcher functionality.

This script demonstrates how to use the WebResearcher module
to perform web searches before LLM market analysis.

Usage:
    python examples/web_research_demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.analysis import WebResearcher, ResearchError
from src.config import settings


async def demo_web_research() -> None:
    """Demonstrate web research functionality."""
    print("=" * 80)
    print("WebResearcher Demo")
    print("=" * 80)
    print()

    # Check if web research is enabled
    if not settings.web_research.enabled:
        print("⚠️  Web research is disabled in settings.")
        print("   Enable it by setting WEB_RESEARCH_ENABLED=true in .env file")
        return

    # Display configuration
    print("📋 Configuration:")
    print(f"   Enabled: {settings.web_research.enabled}")
    print(f"   Proxy: {settings.web_research.proxy_url}")
    print(f"   Search Engine: {settings.web_research.search_engine}")
    print(f"   Max Results: {settings.web_research.max_results}")
    print(f"   Timeout: {settings.web_research.timeout_seconds}s")
    print()

    # Create researcher
    print("🔧 Initializing WebResearcher...")
    researcher = WebResearcher()
    print("✅ WebResearcher initialized")
    print()

    # Example markets to research
    markets = [
        {
            "title": "Will Bitcoin reach $100,000 by end of 2026?",
            "description": "This market resolves to YES if Bitcoin trades at or above $100,000 on Coinbase",
        },
        {
            "title": "Will there be a US recession in 2026?",
            "description": "This market resolves YES if the NBER declares a US recession in 2026",
        },
        {
            "title": "Will Tesla release a new model in 2026?",
            "description": "Resolves YES if Tesla announces a new vehicle model in 2026",
        },
    ]

    # Research each market
    for i, market in enumerate(markets, 1):
        print("=" * 80)
        print(f"Market {i}/{len(markets)}")
        print("=" * 80)
        print(f"Title: {market['title']}")
        print(f"Description: {market['description']}")
        print()
        print("🔍 Performing web research...")

        try:
            # Perform research
            result = await researcher.research_market(
                market_title=market["title"],
                description=market["description"],
            )

            # Display results
            print()
            print("📊 Research Results:")
            print("-" * 80)
            print(result)
            print("-" * 80)
            print()

        except ResearchError as e:
            print(f"❌ Research failed: {e}")
            print()

        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            print()

        # Wait between searches to avoid rate limiting
        if i < len(markets):
            print("⏳ Waiting 2 seconds before next search...")
            await asyncio.sleep(2)
            print()

    print("=" * 80)
    print("Demo completed!")
    print("=" * 80)


async def demo_simple_search() -> None:
    """Demonstrate simple web search."""
    print("=" * 80)
    print("Simple Web Search Demo")
    print("=" * 80)
    print()

    researcher = WebResearcher()

    query = "Bitcoin price prediction 2026"
    print(f"🔍 Searching for: {query}")
    print()

    try:
        result = await researcher.research_market(market_title=query)

        print("📊 Search Results:")
        print("-" * 80)
        print(result)
        print("-" * 80)

    except Exception as e:
        print(f"❌ Search failed: {e}")


async def main() -> None:
    """Main entry point."""
    try:
        # Run full demo
        await demo_web_research()

        print()
        print()

        # Run simple search demo
        await demo_simple_search()

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Check if playwright is installed
    try:
        import playwright

        print("✅ Playwright is installed")
    except ImportError:
        print("❌ Playwright is not installed")
        print()
        print("Please install it first:")
        print("  pip install playwright")
        print("  playwright install chromium")
        print()
        sys.exit(1)

    # Run the demo
    asyncio.run(main())
