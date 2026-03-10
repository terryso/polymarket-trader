#!/usr/bin/env python3
"""Proxy connection test script.

This script tests if the proxy configuration is working correctly.

Usage:
    uv run python examples/test_proxy_connection.py
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_proxy_with_requests() -> None:
    """Test proxy connection using requests library."""
    import requests

    from src.config import settings

    proxy_url = settings.web_research.proxy_url

    print(f"\n{'='*80}")
    print(f"🔍 Proxy Connection Test (requests)")
    print(f"{'='*80}\n")

    print(f"Configuration:")
    print(f"  Proxy URL: {proxy_url if proxy_url else 'Not configured'}")
    print(f"  Timeout: {settings.web_research.timeout_seconds}s\n")

    if not proxy_url:
        print("⚠️  No proxy configured in .env file")
        print("💡 Add WEB_RESEARCH_PROXY_URL to your .env file\n")
        return

    # Test with Google
    test_urls = [
        ("Google", "https://www.google.com"),
        ("Bing", "https://www.bing.com"),
        ("DuckDuckGo", "https://duckduckgo.com"),
    ]

    for name, url in test_urls:
        print(f"⏳ Testing {name} ({url})...")

        try:
            response = requests.get(
                url,
                proxies={"http": proxy_url, "https": proxy_url},
                timeout=settings.web_research.timeout_seconds,
            )

            if response.status_code == 200:
                print(f"✅ {name}: SUCCESS (status {response.status_code})")
            else:
                print(f"⚠️  {name}: Unexpected status {response.status_code}")

        except requests.exceptions.Timeout:
            print(f"❌ {name}: TIMEOUT (proxy may be slow or unavailable)")
        except requests.exceptions.ProxyError as e:
            print(f"❌ {name}: PROXY ERROR - {e}")
        except requests.exceptions.ConnectionError as e:
            print(f"❌ {name}: CONNECTION ERROR - {e}")
        except Exception as e:
            print(f"❌ {name}: ERROR - {e}")

    print()


async def test_proxy_with_playwright() -> None:
    """Test proxy connection using Playwright (as used by search engines)."""
    from src.config import settings

    proxy_url = settings.web_research.proxy_url

    print(f"{'='*80}")
    print(f"🔍 Proxy Connection Test (Playwright)")
    print(f"{'='*80}\n")

    if not proxy_url:
        print("⚠️  No proxy configured - skipping Playwright test")
        print("💡 Add WEB_RESEARCH_PROXY_URL to your .env file\n")
        return

    print(f"Testing with Chromium browser...")
    print(f"  Proxy: {proxy_url}")
    print(f"  Timeout: {settings.web_research.timeout_seconds}s\n")

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            print("⏳ Launching Chromium with proxy...")

            browser = await p.chromium.launch(
                proxy={"server": proxy_url},
                headless=True,
            )

            print("✅ Browser launched successfully\n")

            # Test Google
            print("⏳ Testing Google access...")
            try:
                page = await browser.new_page()
                await page.goto("https://www.google.com", timeout=15000)

                title = await page.title()
                print(f"✅ Google: SUCCESS (title: {title[:50]}...)")

                await page.close()
            except Exception as e:
                print(f"❌ Google: FAILED - {e}")

            await browser.close()

    except ImportError:
        print("❌ Playwright not installed")
        print("💡 Run: playwright install chromium\n")
    except Exception as e:
        print(f"❌ Browser launch failed: {e}\n")


async def test_search_engine() -> None:
    """Test actual search engine functionality."""
    from src.analysis import GoogleSearchSource

    from src.config import settings

    print(f"{'='*80}")
    print(f"🔍 Search Engine Test")
    print(f"{'='*80}\n")

    if not settings.web_research.proxy_url:
        print("⚠️  No proxy configured - skipping search test")
        print("💡 Add WEB_RESEARCH_PROXY_URL to your .env file\n")
        return

    print("Testing Google search with a simple query...\n")

    try:
        source = GoogleSearchSource(
            timeout=30,
            max_results=3,
            proxy_url=settings.web_research.proxy_url,
        )

        results = await source.search("test")

        print(f"✅ Search completed successfully!")
        print(f"   Found {len(results)} results:\n")

        for i, result in enumerate(results, 1):
            print(f"   {i}. {result.title}")
            print(f"      URL: {result.url[:60]}...")
            print(f"      Source: {result.source}\n")

    except Exception as e:
        print(f"❌ Search failed: {e}\n")


def check_env_configuration() -> None:
    """Check .env configuration."""
    from src.config import settings

    print(f"{'='*80}")
    print(f"🔍 .env Configuration Check")
    print(f"{'='*80}\n")

    print("Web Research Settings:")
    print(f"  Enabled: {settings.web_research.enabled}")
    print(f"  Proxy URL: {settings.web_research.proxy_url if settings.web_research.proxy_url else 'Not configured'}")
    print(f"  Search Engine: {settings.web_research.search_engine}")
    print(f"  Max Results: {settings.web_research.max_results}")
    print(f"  Timeout: {settings.web_research.timeout_seconds}s\n")

    if not settings.web_research.proxy_url:
        print("⚠️  WARNING: WEB_RESEARCH_PROXY_URL not set!")
        print("\n💡 Add this line to your .env file:")
        print("   WEB_RESEARCH_PROXY_URL=http://127.0.0.1:1087")
        print("   (replace with your actual proxy address)\n")
    else:
        print("✅ Proxy URL is configured\n")


async def main() -> None:
    """Run all tests."""
    print("\n" + "="*80)
    print("🧪 Polymarket Trader - Proxy Configuration Test")
    print("="*80 + "\n")

    # Check configuration
    check_env_configuration()

    # Test with requests
    test_proxy_with_requests()

    # Test with Playwright
    await test_proxy_with_playwright()

    # Test search engine
    await test_search_engine()

    print("="*80)
    print("🏁 Test Complete")
    print("="*80 + "\n")

    print("📋 Summary:")
    print("  1. Check if all tests passed successfully")
    print("  2. If tests failed, verify your proxy is running")
    print("  3. Check the proxy URL in your .env file")
    print("  4. Try accessing the proxy URL manually\n")

    print("📚 For detailed configuration guide, see:")
    print("   docs/proxy-configuration-guide.md\n")


if __name__ == "__main__":
    asyncio.run(main())
