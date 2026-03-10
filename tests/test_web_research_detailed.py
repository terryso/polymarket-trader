"""Detailed debug script for web research functionality."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_web_research_detailed():
    """Test web research with detailed debugging."""

    print("=" * 60)
    print("Detailed Web Research Debug")
    print("=" * 60)

    # Import Playwright
    from playwright.async_api import async_playwright

    # Test query
    search_query = "Will Chelsea win the 2025-26 English Premier League?"

    # Settings
    proxy_url = "http://127.0.0.1:1087"
    search_engine = "google"
    timeout = 30

    print(f"\n🔍 Search Query: {search_query}")
    print(f"🌐 Proxy: {proxy_url}")
    print(f"⏱️ Timeout: {timeout}s")

    try:
        async with async_playwright() as p:
            print(f"\n🚀 Launching browser...")
            browser = await p.chromium.launch(
                proxy={"server": proxy_url} if proxy_url else None,
                headless=True,
            )

            try:
                page = await browser.new_page()
                page.set_default_timeout(timeout * 1000)

                # Build search URL
                from urllib.parse import quote_plus
                encoded_query = quote_plus(search_query)
                search_url = f"https://www.google.com/search?q={encoded_query}"

                print(f"\n📋 Search URL: {search_url}")

                # Navigate to search page
                print(f"\n🌐 Navigating to Google...")
                await page.goto(search_url)

                # Wait for page to load
                await page.wait_for_load_state("networkidle")
                print(f"✅ Page loaded")

                # Check page title
                title = await page.title()
                print(f"📄 Page Title: {title}")

                # Check if we're on a captcha/block page
                content = await page.content()
                if "unusual traffic" in content.lower() or "captcha" in content.lower():
                    print("⚠️ WARNING: Google detected unusual traffic or showed CAPTCHA!")
                    print("This might be why we're not getting results.")

                # Try to get search results with different selectors
                print(f"\n🔍 Attempting to extract search results...")

                selectors_to_try = [
                    ("div.g", "Standard Google results"),
                    ("div[data-hveid]", "Google results with data-hveid"),
                    (".g", "Class g results"),
                    ("div[class*='g']", "Partial class match"),
                ]

                results_found = False
                for selector, description in selectors_to_try:
                    try:
                        print(f"\nTrying selector: {selector} ({description})")
                        search_results = await page.query_selector_all(selector)
                        print(f"  Found {len(search_results)} elements")

                        if len(search_results) > 0:
                            # Try to extract data from first few results
                            for i, result in enumerate(search_results[:3]):
                                try:
                                    text_content = await result.inner_text()
                                    print(f"  Result {i+1} text (first 100 chars): {text_content[:100]}...")

                                    if len(text_content) > 50:  # Real result has content
                                        results_found = True
                                except Exception as e:
                                    print(f"  Error extracting result {i}: {e}")

                            if results_found:
                                print(f"✅ SUCCESS: Found valid results with {description}")
                                break
                    except Exception as e:
                        print(f"  ❌ Error with selector {selector}: {e}")

                # Try to get page HTML for debugging
                print(f"\n📄 Getting page content for analysis...")
                body_text = await page.evaluate("() => document.body.innerText")
                print(f"Page text length: {len(body_text)} characters")
                print(f"First 200 chars of page: {body_text[:200]}...")

                # Check for specific indicators
                if "did not match any documents" in body_text:
                    print("❌ Google says: 'did not match any documents'")
                elif "your search" in body_text.lower() and "did not match" in body_text.lower():
                    print("❌ No search results found according to Google")
                elif "solve this puzzle" in body_text.lower():
                    print("⚠️ Google is showing a CAPTCHA")
                else:
                    print("✅ Page seems to have loaded, but extraction might be failing")

                if not results_found:
                    print(f"\n❌ FAILED: Could not extract search results with any selector")
                    print("This indicates either:")
                    print("  1. Google has changed their HTML structure")
                    print("  2. The proxy/VPN is being blocked")
                    print("  3. CAPTCHA or anti-bot protection")

            finally:
                await browser.close()

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_web_research_detailed())
