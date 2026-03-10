"""Test that analysis fails properly when web research fails."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_analysis_with_failed_web_research():
    """Test that LLMAnalyzer properly handles failed web research."""

    print("=" * 60)
    print("Testing LLMAnalyzer with Failed Web Research")
    print("=" * 60)

    from src.analysis.llm_analyzer import LLMAnalyzer
    from src.models.market import Market
    from src.exceptions import BotError

    # Create a test market
    test_market = Market(
        id="test-market-001",
        title="Will Bitcoin reach $100k by end of 2026?",
        slug="test-btc-100k",
        description="This market resolves to YES if Bitcoin reaches $100k USD by end of 2026.",
        category="crypto",
        yes_price=0.35,
        no_price=0.65,
        liquidity=100000.0,
    )

    print(f"\n📋 Test Market:")
    print(f"  ID: {test_market.id}")
    print(f"  Title: {test_market.title}")
    print(f"  Yes Price: {test_market.yes_price}")

    # Create analyzer (with web research enabled)
    print(f"\n🔧 Creating LLMAnalyzer with web research...")
    analyzer = LLMAnalyzer()

    if not analyzer._web_researcher:
        print("⚠️ WARNING: Web research is not enabled in settings!")
        print("Cannot test this scenario properly.")
        return

    print(f"✅ WebResearcher is initialized")

    # Try to analyze the market
    print(f"\n🔍 Attempting to analyze market...")
    print(f"Expected: Analysis should FAIL due to web research issues")

    try:
        result = await analyzer.analyze_market(test_market)
        print(f"\n❌ UNEXPECTED: Analysis succeeded!")
        print(f"  This means web research failure was not properly handled.")
        print(f"  Result: {result.recommendation}, Confidence: {result.confidence}")
        return False

    except Exception as e:
        print(f"\n✅ EXPECTED: Analysis failed with exception")
        print(f"  Exception type: {type(e).__name__}")
        print(f"  Message: {e}")

        # Check if it's the right kind of error
        if "web research" in str(e).lower() or "no search results" in str(e).lower():
            print(f"✅ CORRECT: Error is related to web research failure")
            return True
        else:
            print(f"⚠️ WARNING: Error might not be specifically about web research")
            return False


async def test_analysis_with_web_research_disabled():
    """Test that LLMAnalyzer works when web research is disabled."""

    print("\n" + "=" * 60)
    print("Testing LLMAnalyzer with Web Research DISABLED")
    print("=" * 60)

    from src.analysis.llm_analyzer import LLMAnalyzer
    from src.models.market import Market
    from src.config import settings

    # Temporarily disable web research
    original_enabled = settings.web_research.enabled
    settings.web_research.enabled = False

    try:
        # Create a test market
        test_market = Market(
            id="test-market-002",
            title="Test market for analysis",
            slug="test-analysis",
            description="Test description",
            category="business",  # Changed from "other" to valid category
            yes_price=0.5,
            no_price=0.5,
            liquidity=1000.0,
        )

        print(f"\n📋 Test Market:")
        print(f"  Title: {test_market.title}")
        print(f"  Web Research: DISABLED")

        # Create analyzer (web research disabled)
        print(f"\n🔧 Creating LLMAnalyzer (web research disabled)...")
        analyzer = LLMAnalyzer()

        print(f"✅ Analyzer created")
        print(f"  WebResearcher present: {analyzer._web_researcher is not None}")

        # This should work but with a warning
        print(f"\n🔍 Attempting to analyze market...")
        print(f"Expected: Analysis should succeed with warning about missing web research")

        try:
            result = await analyzer.analyze_market(test_market)
            print(f"\n✅ Analysis succeeded (as expected)")
            print(f"  Recommendation: {result.recommendation}")
            print(f"  Confidence: {result.confidence}")
            print(f"  Note: This prediction was made WITHOUT web research context")
            return True

        except Exception as e:
            print(f"\n❌ UNEXPECTED: Analysis failed")
            print(f"  Error: {e}")
            return False

    finally:
        # Restore original setting
        settings.web_research.enabled = original_enabled


async def main():
    """Run all tests."""
    print("\n" + "🧪 " + "=" * 58)
    print("ANALYSIS VALIDATION TESTS")
    print("=" * 60)

    # Test 1: Failed web research
    test1_passed = await test_analysis_with_failed_web_research()

    # Test 2: Disabled web research
    test2_passed = await test_analysis_with_web_research_disabled()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Test 1 (Failed web research): {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"Test 2 (Disabled web research): {'✅ PASS' if test2_passed else '❌ FAIL'}")

    if test1_passed and test2_passed:
        print(f"\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
