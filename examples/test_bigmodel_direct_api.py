#!/usr/bin/env python3
"""独立测试 BigModel 直接 web_search API.

Usage:
    uv run python examples/test_bigmodel_direct_api.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """测试 BigModel 直接 web_search API."""
    from src.config import settings

    api_key = settings.web_research.bigmodel_api_key

    if not api_key:
        print("❌ BigModel API key not configured!")
        print("💡 Set WEB_RESEARCH_BIGMODEL_API_KEY in .env")
        sys.exit(1)

    print(f"🔑 Using API key: {api_key[:10]}...{api_key[-10:]}")
    print(f"🔍 Search query: Bitcoin price 2026\n")

    try:
        from zai import ZhipuAiClient

        print("✅ zai-sdk imported successfully\n")

        # Initialize client
        client = ZhipuAiClient(api_key=api_key)
        print("✅ Client initialized\n")

        # Call direct web_search API
        print("⏳ Calling client.web_search.web_search()...\n")

        response = client.web_search.web_search(
            search_engine="search_pro",
            search_query="Bitcoin price 2026",
            count=10,
            search_recency_filter="noLimit",
            content_size="high"
        )

        print(f"✅ Got response type: {type(response)}\n")
        print("="*80)
        print("📦 RESPONSE STRUCTURE")
        print("="*80)

        # Print all attributes
        print(f"\n📋 All attributes:")
        attrs = [attr for attr in dir(response) if not attr.startswith('_')]
        for i, attr in enumerate(attrs, 1):
            print(f"  {i:2d}. {attr}")

        print(f"\n📦 Response dict representation:")
        print(f"  {response.__dict__}\n")

        # Try to access common attributes
        print("="*80)
        print("🔍 TRYING DIFFERENT ATTRIBUTES")
        print("="*80)

        for attr_name in ['data', 'results', 'items', 'web_results', 'search_results', 'records', 'entries']:
            if hasattr(response, attr_name):
                attr_value = getattr(response, attr_name)
                print(f"\n✅ Found '{attr_name}':")
                print(f"   Type: {type(attr_value)}")
                print(f"   Value: {attr_value}")

                if isinstance(attr_value, list) and len(attr_value) > 0:
                    print(f"\n   First item type: {type(attr_value[0])}")
                    print(f"   First item: {attr_value[0]}")

                    if isinstance(attr_value[0], dict):
                        print(f"\n   First item keys: {list(attr_value[0].keys())}")
            else:
                print(f"\n❌ No attribute '{attr_name}'")

        # Check if response is iterable
        print("\n" + "="*80)
        print("🔍 CHECKING IF ITERABLE")
        print("="*80)

        try:
            print(f"\n✅ Response is iterable")
            for i, item in enumerate(response):
                print(f"\n  Item {i+1}:")
                print(f"    Type: {type(item)}")
                print(f"    Value: {item}")

                if isinstance(item, dict):
                    print(f"    Keys: {list(item.keys())}")

                if i >= 2:  # Only show first 3 items
                    print(f"\n  ... (total {len(response)} items)")
                    break
        except Exception as e:
            print(f"\n❌ Response is not iterable: {e}")

        print("\n" + "="*80)
        print("✅ Test complete")
        print("="*80 + "\n")

    except ImportError as e:
        print(f"❌ Failed to import zai-sdk: {e}")
        print(f"💡 Install with: pip install zai-sdk")
        sys.exit(1)
    except AttributeError as e:
        print(f"❌ API method not found: {e}")
        print(f"💡 The web_search API might not be available in this version of zai-sdk")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
