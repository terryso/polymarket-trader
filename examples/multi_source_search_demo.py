#!/usr/bin/env python3
"""Multi-source search engine demo.

This script demonstrates how to use the multi-source web search engine
to gather market research information.

Usage:
    uv run python examples/multi_source_search_demo.py [--topic TOPIC]

Examples:
    # Search for a specific topic
    uv run python examples/multi_source_search_demo.py --topic "Bitcoin price prediction 2026"

    # Search with default topic
    uv run python examples/multi_source_search_demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def search_topic(topic: str) -> None:
    """Search for a topic using multi-source search engine.

    Args:
        topic: Search topic/query
    """
    from src.analysis import MultiSourceSearchEngine, SearchAggregationError

    print(f"\n{'='*80}")
    print(f"🔍 Multi-Source Search Demo")
    print(f"{'='*80}\n")
    print(f"Topic: {topic}\n")

    # Initialize search engine
    print("⏳ Initializing search engine...")
    engine = MultiSourceSearchEngine(
        timeout=30,
        max_total_results=15,
    )

    stats = engine.get_statistics()
    print(f"✅ Search engine ready:")
    print(f"   - Sources: {', '.join(stats['sources'])}")
    print(f"   - Timeout: {stats['timeout_per_source']}s per source")
    print(f"   - Max results: {stats['max_total_results']}\n")

    # Perform search
    print("⏳ Searching across all sources...")
    try:
        results = await engine.search(topic)

        print(f"\n✅ Found {len(results)} unique results:\n")

        # Display results grouped by source
        results_by_source = {}
        for result in results:
            if result.source not in results_by_source:
                results_by_source[result.source] = []
            results_by_source[result.source].append(result)

        # Display results by source
        for source, source_results in results_by_source.items():
            print(f"📊 {source} ({len(source_results)} results):")
            print("-" * 80)

            for i, result in enumerate(source_results, 1):
                print(f"\n  {i}. {result.title}")
                print(f"     URL: {result.url}")
                print(f"     📝 {result.snippet[:200]}...")

            print("\n")

        # Summary
        print(f"{'='*80}")
        print(f"📊 Summary:")
        print(f"   - Total unique results: {len(results)}")
        print(f"   - Sources with results: {len(results_by_source)}")
        for source, source_results in results_by_source.items():
            print(f"   - {source}: {len(source_results)} results")
        print(f"{'='*80}\n")

    except SearchAggregationError as e:
        print(f"\n❌ All search sources failed!")
        print(f"Error: {e.message}")
        print(f"\nFailed sources:")
        for source, error in e.source_errors.items():
            print(f"   - {source}: {error}")
        print("\n")

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")


async def search_from_database(limit: int = 5) -> None:
    """Search for topics from the database predictions.

    Args:
        limit: Maximum number of predictions to search
    """
    from src.storage.database import get_db_manager
    import aiosqlite

    print(f"\n{'='*80}")
    print(f"🔍 Database-Powered Multi-Source Search Demo")
    print(f"{'='*80}\n")

    try:
        # Initialize database
        db_manager = get_db_manager()
        await db_manager.initialize()

        # Get recent predictions from database
        print("⏳ Fetching predictions from database...")
        async with aiosqlite.connect(db_manager._db_path) as conn:
            cursor = await conn.execute("""
                SELECT
                    p.id,
                    p.market_id,
                    m.title,
                    p.reasoning
                FROM predictions p
                LEFT JOIN markets m ON p.market_id = m.id
                ORDER BY p.created_at DESC
                LIMIT ?
            """, (limit,))

            predictions = await cursor.fetchall()

        if not predictions:
            print("❌ No predictions found in database.")
            print("💡 Run the main application first to generate some predictions.\n")
            return

        print(f"✅ Found {len(predictions)} recent predictions\n")

        # Search for each prediction topic
        from src.analysis import MultiSourceSearchEngine

        engine = MultiSourceSearchEngine(max_total_results=10)

        for pred_id, market_id, title, reasoning in predictions:
            if not title:
                continue

            print(f"\n{'='*80}")
            print(f"🔍 Prediction #{pred_id}: {title[:70]}...")
            print(f"{'='*80}\n")

            print("⏳ Searching for latest information...")
            try:
                results = await engine.search(title)

                if results:
                    print(f"\n✅ Found {len(results)} results:\n")

                    # Show top 3 results
                    for i, result in enumerate(results[:3], 1):
                        print(f"  {i}. [{result.source}] {result.title}")
                        print(f"     {result.snippet[:150]}...")
                        print(f"     🔗 {result.url}\n")

                    if len(results) > 3:
                        print(f"  ... and {len(results) - 3} more results\n")

                else:
                    print("❌ No results found\n")

            except Exception as e:
                print(f"❌ Search failed: {e}\n")

            # Small delay between searches to be respectful
            await asyncio.sleep(2)

        print(f"\n{'='*80}")
        print(f"✅ Demo complete")
        print(f"{'='*80}\n")

    except Exception as e:
        print(f"\n❌ Error: {e}\n")

    finally:
        # Clean up database
        if 'db_manager' in locals():
            await db_manager.close()


async def main() -> None:
    """Main entry point for the demo."""
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="Multi-source search engine demo"
    )
    parser.add_argument(
        "--topic",
        type=str,
        default="Bitcoin price prediction 2026",
        help="Search topic (default: 'Bitcoin price prediction 2026')"
    )
    parser.add_argument(
        "--from-database",
        action="store_true",
        help="Search for topics from database predictions"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Maximum predictions to search from database (default: 3)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable DEBUG level logging"
    )

    args = parser.parse_args()

    # Set log level if --debug is provided
    if args.debug:
        os.environ["LOG_LEVEL"] = "DEBUG"
        print("🔍 Debug logging enabled\n")

    # Import after setting log level to ensure it takes effect
    from src.utils.logger import get_logger
    logger = get_logger(__name__)

    if args.from_database:
        await search_from_database(limit=args.limit)
    else:
        await search_topic(args.topic)


if __name__ == "__main__":
    asyncio.run(main())
