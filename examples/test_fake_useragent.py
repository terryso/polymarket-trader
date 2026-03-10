#!/usr/bin/env python3
"""Test fake-useragent functionality."""

from fake_useragent import UserAgent
import asyncio
from playwright.async_api import async_playwright

async def test_fake_useragent():
    """Test fake-useragent with Playwright."""
    print("🎭 Testing fake-useragent functionality\n")

    # Initialize UserAgent generator
    ua = UserAgent()

    # Show some example User-Agents
    print("📋 Example User-Agents:")
    for i in range(5):
        random_ua = ua.random
        print(f"  {i+1}. {random_ua[:80]}...")

    print("\n🌐 Testing with Playwright:")

    try:
        async with async_playwright() as p:
            # Test with different User-Agents
            for i in range(3):
                random_ua = ua.random
                print(f"\n{i+1}. Testing with: {random_ua[:60]}...")

                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                    ]
                )

                try:
                    context = await browser.new_context(
                        user_agent=random_ua,
                        viewport={"width": 1920, "height": 1080},
                        locale="en-US",
                    )

                    page = await context.new_page()

                    # Test with a simple site that shows User-Agent
                    print(f"   🌍 Navigating to httpbin.org/user_agent...")
                    await page.goto("http://httpbin.org/user_agent", timeout=10000)

                    # Get the page content
                    content = await page.content()
                    print(f"   ✅ Page loaded successfully")

                    # Check if our User-Agent was used
                    if '"user-agent"' in content:
                        # Extract the User-Agent from response
                        start = content.find('"user-agent": "') + len('"user-agent": "')
                        end = content.find('"', start)
                        detected_ua = content[start:end]
                        print(f"   ✅ Detected UA: {detected_ua[:60]}...")

                        if random_ua in detected_ua:
                            print(f"   ✅ User-Agent matched!")
                        else:
                            print(f"   ⚠️  User-Agent mismatch")

                finally:
                    await browser.close()

        print("\n✅ All tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fake_useragent())
