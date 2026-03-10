#!/usr/bin/env python3
"""BigModel (ZhipuAI) search testing script.

This script tests two different methods for using BigModel's web search:
1. Chat completions with web_search tool (current implementation)
2. Direct web_search API call (new method to test)

Usage:
    uv run python examples/bigmodel_search_test.py [--query QUERY]

Examples:
    # Test with default query
    uv run python examples/bigmodel_search_test.py

    # Test with custom query
    uv run python examples/bigmodel_search_test.py --query "Bitcoin price 2026"

    # Enable debug logging
    uv run python examples/bigmodel_search_test.py --debug
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_direct_web_search_api(api_key: str, query: str) -> None:
    """Test the direct web_search API call.

    This method uses client.web_search.web_search() which is a dedicated
    search API endpoint.

    Args:
        api_key: BigModel API key
        query: Search query
    """
    print(f"\n{'='*80}")
    print(f"🔍 Test 1: Direct web_search API")
    print(f"{'='*80}\n")

    try:
        from zai import ZhipuAiClient

        print(f"✅ zai-sdk imported successfully")
        print(f"🔑 Using API key: {api_key[:10]}...{api_key[-10:]}")
        print(f"🔍 Search query: {query}\n")

        # Initialize client
        client = ZhipuAiClient(api_key=api_key)
        print(f"✅ Client initialized\n")

        # Call direct web_search API
        print("⏳ Calling client.web_search.web_search()...")
        response = client.web_search.web_search(
            search_engine="search_pro",  # 使用高级搜索
            search_query=query,
            count=10,  # 返回10条结果
            search_recency_filter="noLimit",  # 不限制时间
            content_size="high"  # 返回更详细的内容
        )

        print(f"✅ Got response type: {type(response)}")
        print(f"📦 Response: {response}\n")

        # Parse and display results
        results = parse_direct_web_search_response(response)

        if results:
            print(f"✅ Found {len(results)} results:\n")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result.get('title', 'N/A')}")
                print(f"     URL: {result.get('link', 'N/A')}")
                print(f"     📝 {result.get('content', 'N/A')[:200]}...\n")
        else:
            print("⚠️ No results found or unable to parse response\n")

        return True

    except ImportError as e:
        print(f"❌ Failed to import zai-sdk: {e}")
        print(f"💡 Install with: pip install zai-sdk")
        return False
    except AttributeError as e:
        print(f"❌ API method not found: {e}")
        print(f"💡 The web_search API might not be available in this version of zai-sdk")
        return False
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def parse_direct_web_search_response(response: Any) -> list[dict[str, Any]]:
    """Parse response from direct web_search API.

    Args:
        response: Response from client.web_search.web_search()

    Returns:
        List of search result dictionaries
    """
    results = []

    # Handle different response formats
    if hasattr(response, 'data'):
        # Response has a 'data' attribute
        items = response.data
    elif isinstance(response, dict):
        # Response is a dictionary
        items = response.get('data', response.get('results', []))
    elif isinstance(response, list):
        # Response is already a list
        items = response
    else:
        print(f"⚠️ Unknown response format: {type(response)}")
        print(f"   Response attributes: {dir(response)[:20]}")
        return []

    # Extract results
    for item in items:
        if isinstance(item, dict):
            results.append({
                'title': item.get('title', 'N/A'),
                'link': item.get('link', item.get('url', 'N/A')),
                'content': item.get('content', item.get('description', 'N/A')),
            })
        else:
            # Try to extract from object
            result_dict = {}
            if hasattr(item, 'title'):
                result_dict['title'] = item.title
            if hasattr(item, 'link'):
                result_dict['link'] = item.link
            if hasattr(item, 'content'):
                result_dict['content'] = item.content
            if result_dict:
                results.append(result_dict)

    return results


async def test_chat_web_search_tool(api_key: str, query: str) -> None:
    """Test the chat completions with web_search tool.

    This method uses client.chat.completions.create() with web_search tool,
    which is the current implementation in BigModelSearchSource.

    Args:
        api_key: BigModel API key
        query: Search query
    """
    print(f"\n{'='*80}")
    print(f"🔍 Test 2: Chat completions with web_search tool")
    print(f"{'='*80}\n")

    try:
        from zai import ZhipuAiClient

        print(f"✅ zai-sdk imported successfully")
        print(f"🔑 Using API key: {api_key[:10]}...{api_key[-10:]}")
        print(f"🔍 Search query: {query}\n")

        # Initialize client
        client = ZhipuAiClient(api_key=api_key)
        print(f"✅ Client initialized\n")

        # Call chat.completions.create with web_search tool
        print("⏳ Calling client.chat.completions.create() with web_search tool...")

        response = client.chat.completions.create(
            model="glm-4-air",  # 使用支持联网搜索的模型
            messages=[
                {
                    "role": "user",
                    "content": f"请搜索关于 '{query}' 的最新信息，并返回搜索结果列表"
                }
            ],
            tools=[
                {
                    "type": "web_search",
                    "web_search": {
                        "search_query": query,
                        "search_result": True,
                    }
                }
            ],
            temperature=0.7,
        )

        print(f"✅ Got response type: {type(response)}")

        # Parse and display results
        results = parse_chat_web_search_response(response)

        if results:
            print(f"✅ Found {len(results)} results:\n")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result.get('title', 'N/A')}")
                print(f"     URL: {result.get('url', 'N/A')}")
                print(f"     📝 {result.get('snippet', 'N/A')[:200]}...\n")
        else:
            print("⚠️ No results found in tool_calls")
            print(f"📝 Response content: {response.choices[0].message.content if response.choices else 'No content'}\n")

        return True

    except ImportError as e:
        print(f"❌ Failed to import zai-sdk: {e}")
        print(f"💡 Install with: pip install zai-sdk")
        return False
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def parse_chat_web_search_response(response: Any) -> list[dict[str, Any]]:
    """Parse response from chat.completions with web_search tool.

    Args:
        response: Response from client.chat.completions.create()

    Returns:
        List of search result dictionaries
    """
    results = []

    try:
        # Extract tool calls from response
        if response.choices and len(response.choices) > 0:
            choice = response.choices[0]
            message = choice.message

            print(f"📦 Message type: {type(message)}")
            print(f"📦 Message attributes: {[attr for attr in dir(message) if not attr.startswith('_')][:20]}")

            # Check if there are tool calls
            if hasattr(message, 'tool_calls') and message.tool_calls:
                print(f"✅ Found {len(message.tool_calls)} tool calls")

                for idx, tool_call in enumerate(message.tool_calls):
                    print(f"\n  Tool call {idx + 1}:")
                    print(f"    Type: {tool_call.type if hasattr(tool_call, 'type') else 'N/A'}")

                    if tool_call.type == "web_search":
                        # Parse web search results
                        print(f"    ✅ This is a web_search tool call")

                        if hasattr(tool_call, 'web_search') and tool_call.web_search:
                            search_results = tool_call.web_search
                            print(f"    📦 web_search data type: {type(search_results)}")
                            print(f"    📦 web_search data: {search_results}")

                            if isinstance(search_results, list):
                                for item in search_results:
                                    try:
                                        if isinstance(item, dict):
                                            results.append({
                                                'title': item.get('title', 'N/A'),
                                                'url': item.get('link', item.get('url', 'N/A')),
                                                'snippet': item.get('content', item.get('description', 'N/A')),
                                            })
                                        else:
                                            # Try to extract from object
                                            result_dict = {}
                                            if hasattr(item, 'title'):
                                                result_dict['title'] = item.title
                                            if hasattr(item, 'link') or hasattr(item, 'url'):
                                                result_dict['url'] = getattr(item, 'link', getattr(item, 'url', 'N/A'))
                                            if hasattr(item, 'content') or hasattr(item, 'description'):
                                                result_dict['snippet'] = getattr(item, 'content', getattr(item, 'description', 'N/A'))
                                            if result_dict:
                                                results.append(result_dict)
                                    except Exception as e:
                                        print(f"    ❌ Failed to parse result item: {e}")
                                        continue
                        else:
                            print(f"    ⚠️ No web_search data found")
                            print(f"    Tool call attributes: {[attr for attr in dir(tool_call) if not attr.startswith('_')]}")
            else:
                print("⚠️ No tool_calls found in message")
                print(f"📝 Message content: {message.content if hasattr(message, 'content') else 'N/A'}")
        else:
            print("⚠️ No choices in response")

    except Exception as e:
        print(f"❌ Error parsing response: {e}")
        import traceback
        traceback.print_exc()

    return results


async def test_bigmodel_search_source(query: str) -> None:
    """Test the BigModelSearchSource class implementation.

    Args:
        query: Search query
    """
    print(f"\n{'='*80}")
    print(f"🔍 Test 3: BigModelSearchSource class")
    print(f"{'='*80}\n")

    try:
        from src.analysis import BigModelSearchSource

        print(f"✅ BigModelSearchSource imported successfully")
        print(f"🔍 Search query: {query}\n")

        # Initialize source
        source = BigModelSearchSource(timeout=30, max_results=10)
        print(f"✅ BigModelSearchSource initialized\n")

        # Perform search
        print("⏳ Calling source.search()...")
        results = await source.search(query)

        print(f"✅ Got {len(results)} results:\n")
        for i, result in enumerate(results, 1):
            print(f"  {i}. [{result.source}] {result.title}")
            print(f"     URL: {result.url}")
            print(f"     📝 {result.snippet[:200]}...\n")

        return True

    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main() -> None:
    """Main entry point for the test script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="BigModel (ZhipuAI) search testing"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="Bitcoin price prediction 2026",
        help="Search query (default: 'Bitcoin price prediction 2026')"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="BigModel API key (default: read from WEB_RESEARCH_BIGMODEL_API_KEY env var)"
    )
    parser.add_argument(
        "--test",
        type=str,
        choices=["direct", "chat", "source", "all"],
        default="all",
        help="Which test(s) to run (default: all)"
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

    # Get API key
    if args.api_key:
        api_key = args.api_key
    else:
        from src.config import settings
        api_key = settings.web_research.bigmodel_api_key

    if not api_key:
        print("❌ BigModel API key not configured!")
        print("💡 Either pass --api-key argument or set WEB_RESEARCH_BIGMODEL_API_KEY in .env")
        sys.exit(1)

    print(f"\n{'='*80}")
    print(f"🧪 BigModel Search Testing")
    print(f"{'='*80}")
    print(f"Query: {args.query}")
    print(f"Test: {args.test}")
    print(f"{'='*80}\n")

    # Run tests
    results = {}

    if args.test in ["direct", "all"]:
        results["direct"] = test_direct_web_search_api(api_key, args.query)

    if args.test in ["chat", "all"]:
        results["chat"] = await test_chat_web_search_tool(api_key, args.query)

    if args.test in ["source", "all"]:
        results["source"] = await test_bigmodel_search_source(args.query)

    # Summary
    print(f"\n{'='*80}")
    print(f"📊 Test Summary")
    print(f"{'='*80}\n")

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")

    total_passed = sum(1 for v in results.values() if v)
    total_tests = len(results)

    print(f"\n  Total: {total_passed}/{total_tests} tests passed")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
