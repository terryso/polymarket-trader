#!/usr/bin/env python3
"""测试 BigModelSearchSource 的 _search_with_chat_tool 方法.

Usage:
    uv run python examples/test_bigmodel_chat_tools.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def main():
    """测试 BigModelSearchSource._search_with_chat_tool 方法."""
    from src.config import settings

    api_key = settings.web_research.bigmodel_api_key

    if not api_key:
        print("❌ BigModel API key not configured!")
        print("💡 Set WEB_RESEARCH_BIGMODEL_API_KEY in .env")
        sys.exit(1)

    print(f"🔑 Using API key: {api_key[:10]}...{api_key[-10:]}")
    print(f"🔍 Search query: Bitcoin price prediction 2026\n")

    try:
        from src.analysis.search_sources import BigModelSearchSource

        print("✅ BigModelSearchSource imported successfully\n")

        # Initialize search source
        search_source = BigModelSearchSource(
            timeout=30,
            max_results=5,
            api_key=api_key
        )
        print("✅ BigModelSearchSource initialized\n")

        print("=" * 80)
        print("🔍 CALLING _search_with_chat_tool")
        print("=" * 80)

        # Call the _search_with_chat_tool method directly
        results = await search_source.search(
            query="Bitcoin price prediction 2026"
        )

        print(f"\n✅ Got {len(results)} results\n")

        # Display results
        print("=" * 80)
        print("📦 SEARCH RESULTS")
        print("=" * 80)

        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.title}")
            print(f"   URL: {result.url}")
            print(f"   Source: {result.source}")
            if result.snippet:
                print(f"   Snippet: {result.snippet[:200]}...")

        # Test with different query
        print("\n" + "=" * 80)
        print("🔍 TESTING WITH CHINESE QUERY")
        print("=" * 80)

        results_zh = await search_source._search_with_chat_tool(
            query="原油价格走势 2026"
        )

        print(f"\n✅ Got {len(results_zh)} results for Chinese query\n")

        for i, result in enumerate(results_zh[:3], 1):  # Show first 3
            print(f"\n{i}. {result.title}")
            print(f"   URL: {result.url}")

        print("\n" + "=" * 80)
        print("✅ Test complete")
        print("=" * 80 + "\n")

    except ImportError as e:
        print(f"❌ Failed to import: {e}")
        print(f"💡 Install dependencies with: pip install zai-sdk")
        sys.exit(1)
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
