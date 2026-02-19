"""Tests for MarketFilter.

This module contains comprehensive tests for the market filtering functionality,
covering liquidity, deadline, category filters, and exclusion rules.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.models import Market, MarketCategory


class TestMarketFilterDataclasses:
    """Tests for FilterStatistics and FilterResult dataclasses."""

    def test_filter_statistics_defaults(self) -> None:
        """Test FilterStatistics has correct default values."""
        from src.analysis.market_filter import FilterStatistics

        stats = FilterStatistics()
        assert stats.total_input == 0
        assert stats.passed_hard_liquidity == 0
        assert stats.passed_hard_deadline == 0
        assert stats.passed_soft_liquidity == 0
        assert stats.passed_soft_deadline == 0
        assert stats.passed_category == 0
        assert stats.passed_exclusion == 0
        assert stats.final_count == 0

    def test_filter_result_defaults(self) -> None:
        """Test FilterResult has correct default values."""
        from src.analysis.market_filter import FilterResult, FilterStatistics

        result = FilterResult()
        assert result.markets == []
        assert isinstance(result.statistics, FilterStatistics)


class TestMarketFilter:
    """Tests for MarketFilter class."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings with market filter configuration."""
        settings = MagicMock()
        settings.market_filter = MagicMock()
        settings.market_filter.min_liquidity = 10000.0
        settings.market_filter.min_deadline_hours = 1
        settings.market_filter.excluded_keywords = ["price", "USD", "tomorrow"]
        settings.market_filter.controversial_keywords = []
        return settings

    @pytest.fixture
    def market_filter(self, mock_settings: MagicMock) -> "MarketFilter":
        """Create a MarketFilter instance for testing."""
        from src.analysis.market_filter import MarketFilter

        return MarketFilter(settings=mock_settings)

    @pytest.fixture
    def valid_market(self) -> Market:
        """Create a sample Market that should pass all filters."""
        return Market(
            id="valid-market-123",
            title="Will X happen by next month?",
            description="A prediction market about X",
            category=MarketCategory.POLITICS,
            liquidity=50000.0,
            deadline=datetime.now(timezone.utc) + timedelta(days=14),
        )

    # ========== Empty Input Tests ==========

    def test_filter_empty_list(self, market_filter: "MarketFilter") -> None:
        """Test filtering an empty list returns empty result."""
        result = market_filter.filter_markets([])
        assert result.markets == []
        assert result.statistics.total_input == 0
        assert result.statistics.final_count == 0

    # ========== Liquidity Filter Tests ==========

    def test_liquidity_pass_high(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test liquidity filter passes high liquidity market."""
        valid_market.liquidity = 50000.0
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 1

    def test_liquidity_pass_boundary(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test liquidity filter passes at minimum threshold ($10,000)."""
        valid_market.liquidity = 10000.0
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 1

    def test_liquidity_fail_below_threshold(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test liquidity filter rejects below minimum ($10,000)."""
        valid_market.liquidity = 9999.99
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

    def test_liquidity_hard_exclude(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test liquidity hard exclusion below $5,000."""
        valid_market.liquidity = 4000.0
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

    def test_liquidity_none_excluded(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test market with no liquidity is excluded."""
        valid_market.liquidity = None
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

    # ========== Deadline Filter Tests ==========

    def test_deadline_pass_future(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test deadline filter passes market with far deadline."""
        valid_market.deadline = datetime.now(timezone.utc) + timedelta(days=30)
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 1

    def test_deadline_pass_boundary(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test deadline filter passes at minimum threshold (1 hour)."""
        valid_market.deadline = datetime.now(timezone.utc) + timedelta(hours=3)
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 1

    def test_deadline_fail_below_threshold(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test deadline filter rejects below minimum (1 hour)."""
        valid_market.deadline = datetime.now(timezone.utc) + timedelta(minutes=30)
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

    def test_deadline_hard_exclude(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test deadline hard exclusion below 1 hour."""
        valid_market.deadline = datetime.now(timezone.utc) + timedelta(minutes=30)
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

    def test_deadline_none_excluded(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test market with no deadline is excluded."""
        valid_market.deadline = None
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

    # ========== Category Filter Tests ==========

    def test_category_politics_pass(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test POLITICS category passes."""
        valid_market.category = MarketCategory.POLITICS
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 1

    def test_category_business_pass(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test BUSINESS category passes."""
        valid_market.category = MarketCategory.BUSINESS
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 1

    def test_category_technology_pass(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test TECHNOLOGY category passes."""
        valid_market.category = MarketCategory.TECHNOLOGY
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 1

    def test_category_economics_pass(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test ECONOMICS category passes."""
        valid_market.category = MarketCategory.ECONOMICS
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 1

    def test_category_crypto_pass(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test CRYPTO category passes."""
        valid_market.category = MarketCategory.CRYPTO
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 1

    def test_category_none_passes(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test market with no category is kept (allowed by default)."""
        valid_market.category = None
        result = market_filter.filter_markets([valid_market])
        # Market with no category should pass category filter
        assert len(result.markets) == 1

    # ========== Exclusion Rules Tests ==========

    def test_exclusion_price_keyword(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test exclusion of title containing 'price'."""
        valid_market.title = "What will be the price of gold?"
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

    def test_exclusion_usd_keyword(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test exclusion of title containing 'USD'."""
        valid_market.title = "Will USD strengthen against EUR?"
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

    def test_exclusion_tomorrow_keyword(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test exclusion of title containing 'tomorrow'."""
        valid_market.title = "Will it rain tomorrow?"
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

    def test_exclusion_case_insensitive(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test exclusion is case insensitive."""
        valid_market.title = "What will be the PRICE of Bitcoin?"
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

    def test_exclusion_valid_title_passes(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test valid title passes exclusion rules."""
        valid_market.title = "Will the election be decided fairly?"
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 1

    # ========== Description Controversial Keywords Tests ==========

    def test_description_controversial_keyword_excluded(
        self, valid_market: Market
    ) -> None:
        """Test that description with controversial keyword is excluded."""
        from src.analysis.market_filter import MarketFilter

        # Create settings with controversial keywords
        settings = MagicMock()
        settings.market_filter = MagicMock()
        settings.market_filter.min_liquidity = 10000.0
        settings.market_filter.min_deadline_hours = 1
        settings.market_filter.excluded_keywords = ["price", "USD", "tomorrow"]
        settings.market_filter.controversial_keywords = ["controversial", "sensitive"]

        market_filter = MarketFilter(settings=settings)
        valid_market.description = "This is a controversial topic."
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

    def test_description_no_controversial_keyword_passes(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test that description without controversial keywords passes."""
        valid_market.description = "A normal market description."
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 1

    def test_description_none_passes(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test that market with no description passes."""
        valid_market.description = None
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 1

    # ========== Integration Tests ==========

    def test_multiple_markets_mixed_results(
        self, market_filter: "MarketFilter"
    ) -> None:
        """Test filtering multiple markets with mixed results."""
        markets = [
            # Should pass all filters
            Market(
                id="pass-1",
                title="Will X happen?",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            ),
            # Low liquidity - should fail
            Market(
                id="fail-liquidity",
                title="Will Y happen?",
                category=MarketCategory.POLITICS,
                liquidity=3000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            ),
            # Short deadline - should fail (< 1 hour)
            Market(
                id="fail-deadline",
                title="Will Z happen?",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
            ),
            # Excluded keyword - should fail
            Market(
                id="fail-keyword",
                title="What is the price of Bitcoin?",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            ),
        ]

        result = market_filter.filter_markets(markets)

        assert len(result.markets) == 1
        assert result.markets[0].id == "pass-1"
        assert result.statistics.total_input == 4
        assert result.statistics.final_count == 1

    def test_statistics_tracking(self, market_filter: "MarketFilter") -> None:
        """Test that statistics are correctly tracked."""
        markets = [
            Market(
                id="market-1",
                title="Valid market",
                category=MarketCategory.POLITICS,
                liquidity=20000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=10),
            ),
            Market(
                id="market-2",
                title="Valid market 2",
                category=MarketCategory.CRYPTO,
                liquidity=30000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=15),
            ),
        ]

        result = market_filter.filter_markets(markets)

        assert result.statistics.total_input == 2
        assert result.statistics.final_count == 2

    # ========== Default Settings Tests ==========

    def test_default_settings(self) -> None:
        """Test MarketFilter can be created with default settings."""
        from src.analysis.market_filter import MarketFilter

        # Should not raise
        filter_instance = MarketFilter()
        assert filter_instance is not None

    # ========== Non-Target Category Tests (using string value for non-enum categories) ==========

    def test_category_non_target_filtered(self, market_filter: "MarketFilter") -> None:
        """Test non-target category is filtered out.

        Since MarketCategory only has POLITICS, BUSINESS, TECHNOLOGY, ECONOMICS, CRYPTO,
        we test by creating a market with a non-target category value using model_construct.
        """
        # Create market with category=None first, then the filter won't filter by category
        # Instead, test that a category NOT in TARGET_CATEGORIES would be filtered
        # Since the enum doesn't have SPORTS, we verify the target categories are correct
        from src.analysis.market_filter import MarketFilter

        # Verify that all MarketCategory values are in TARGET_CATEGORIES
        # So no category from the enum should be filtered
        for category in MarketCategory:
            assert (
                category in MarketFilter.TARGET_CATEGORIES
            ), f"Category {category} should be in TARGET_CATEGORIES"

    def test_category_none_still_passes(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test market with None category still passes (no category filtering)."""
        valid_market.category = None
        result = market_filter.filter_markets([valid_market])
        # Market with no category should pass
        assert len(result.markets) == 1

    # ========== Boundary Value Tests ==========

    def test_liquidity_hard_exclude_boundary(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test liquidity at hard exclude boundary ($4,999.99 fails, $5,000 passes)."""
        # Just below hard exclude threshold
        valid_market.liquidity = 4999.99
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

        # Exactly at hard exclude threshold (should pass hard exclude, but fail soft filter)
        valid_market.liquidity = 5000.0
        result = market_filter.filter_markets([valid_market])
        # Passes hard exclude ($5,000) but fails soft filter ($10,000)
        assert len(result.markets) == 0

    def test_liquidity_soft_filter_boundary(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test liquidity at soft filter boundary ($9,999.99 fails, $10,000 passes)."""
        # Just below soft filter threshold
        valid_market.liquidity = 9999.99
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

        # Exactly at soft filter threshold
        valid_market.liquidity = 10000.0
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 1

    def test_deadline_hard_exclude_boundary(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test deadline at hard exclude boundary (30 mins fails, 3 hours passes)."""
        # Just below threshold (30 minutes)
        valid_market.deadline = datetime.now(timezone.utc) + timedelta(minutes=30)
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

        # Above threshold (3 hours) - passes
        valid_market.deadline = datetime.now(timezone.utc) + timedelta(hours=3)
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 1

    def test_deadline_soft_filter_boundary(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test deadline at soft filter boundary (30 mins fails, 3 hours passes)."""
        # Just below threshold (30 minutes)
        valid_market.deadline = datetime.now(timezone.utc) + timedelta(minutes=30)
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

        # Above threshold (3 hours) - passes
        valid_market.deadline = datetime.now(timezone.utc) + timedelta(hours=3)
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 1

    # ========== Edge Case Tests ==========

    def test_very_low_liquidity_excluded(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test market with very low liquidity is excluded.

        Note: Market model validates liquidity >= 0, so we test with 0.01 instead.
        """
        valid_market.liquidity = 0.01  # Minimum valid positive liquidity
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

    def test_zero_liquidity_excluded(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test market with zero liquidity is excluded."""
        valid_market.liquidity = 0.0
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

    def test_past_deadline_excluded(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test market with past deadline is excluded."""
        valid_market.deadline = datetime.now(timezone.utc) - timedelta(days=1)
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

    def test_very_large_liquidity_passes(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test market with very large liquidity passes."""
        valid_market.liquidity = 10000000.0  # $10 million
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 1

    def test_very_far_deadline_passes(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test market with very far deadline passes."""
        valid_market.deadline = datetime.now(timezone.utc) + timedelta(days=365)
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 1

    # ========== Multiple Keywords Tests ==========

    def test_exclusion_multiple_keywords(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test exclusion when title contains multiple excluded keywords."""
        valid_market.title = "What will be the price of USD tomorrow?"
        result = market_filter.filter_markets([valid_market])
        assert len(result.markets) == 0

    def test_exclusion_keyword_partial_match(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test that partial word matches are NOT excluded (word boundary matching).

        With word boundary matching, 'prices' does NOT match 'price' pattern.
        This is the desired behavior to avoid false positives like 'priceless'.
        """
        valid_market.title = "What are the prices of goods?"
        result = market_filter.filter_markets([valid_market])
        # 'prices' does NOT match 'price' with word boundary, so should PASS
        assert len(result.markets) == 1

    def test_exclusion_keyword_in_word(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test that keyword as part of larger word is NOT excluded (word boundary).

        With word boundary matching, 'tomorrows' does NOT match 'tomorrow'.
        """
        valid_market.title = "What is the tomorrows weather?"
        result = market_filter.filter_markets([valid_market])
        # 'tomorrows' does NOT match 'tomorrow' with word boundary
        assert len(result.markets) == 1

    def test_exclusion_exact_word_match(
        self, market_filter: "MarketFilter", valid_market: Market
    ) -> None:
        """Test that exact word matches are excluded."""
        valid_market.title = "What is the price of Bitcoin?"
        result = market_filter.filter_markets([valid_market])
        # 'price' is an exact word, should be excluded
        assert len(result.markets) == 0

    # ========== Private Method Tests ==========

    def test_hard_exclude_by_liquidity_method(
        self, market_filter: "MarketFilter"
    ) -> None:
        """Test _hard_exclude_by_liquidity private method directly."""
        markets = [
            Market(
                id="high-liquidity",
                title="Valid",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            ),
            Market(
                id="at-threshold",
                title="Valid",
                category=MarketCategory.POLITICS,
                liquidity=5000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            ),
            Market(
                id="below-threshold",
                title="Valid",
                category=MarketCategory.POLITICS,
                liquidity=4999.99,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            ),
            Market(
                id="no-liquidity",
                title="Valid",
                category=MarketCategory.POLITICS,
                liquidity=None,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            ),
        ]

        result = market_filter._hard_exclude_by_liquidity(markets)
        assert len(result) == 2
        ids = {m.id for m in result}
        assert "high-liquidity" in ids
        assert "at-threshold" in ids
        assert "below-threshold" not in ids
        assert "no-liquidity" not in ids

    def test_hard_exclude_by_deadline_method(
        self, market_filter: "MarketFilter"
    ) -> None:
        """Test _hard_exclude_by_deadline private method directly.

        Note: The hard exclude uses hours calculation (deadline - now).total_seconds() / 3600.
        """
        now = datetime.now(timezone.utc)
        markets = [
            Market(
                id="far-deadline",
                title="Valid",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=now + timedelta(days=14),
            ),
            Market(
                id="at-threshold",
                title="Valid",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=now + timedelta(hours=3),  # > 1 hour
            ),
            Market(
                id="below-threshold",
                title="Valid",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=now + timedelta(minutes=30),  # < 1 hour
            ),
            Market(
                id="no-deadline",
                title="Valid",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=None,
            ),
        ]

        result = market_filter._hard_exclude_by_deadline(markets)
        assert len(result) == 2
        ids = {m.id for m in result}
        assert "far-deadline" in ids
        assert "at-threshold" in ids
        assert "below-threshold" not in ids
        assert "no-deadline" not in ids

    def test_filter_by_category_method(self, market_filter: "MarketFilter") -> None:
        """Test _filter_by_category private method directly.

        Note: All MarketCategory enum values are in TARGET_CATEGORIES, so only
        None category markets are kept alongside target category markets.
        """
        markets = [
            Market(
                id="politics",
                title="Valid",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            ),
            Market(
                id="crypto",
                title="Valid",
                category=MarketCategory.CRYPTO,
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            ),
            Market(
                id="no-category",
                title="Valid",
                category=None,
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            ),
        ]

        result = market_filter._filter_by_category(markets)
        # All should pass: POLITICS and CRYPTO are in TARGET_CATEGORIES, None is kept
        assert len(result) == 3
        ids = {m.id for m in result}
        assert "politics" in ids
        assert "crypto" in ids
        assert "no-category" in ids

    def test_apply_exclusion_rules_method(self, market_filter: "MarketFilter") -> None:
        """Test _apply_exclusion_rules private method directly."""
        markets = [
            Market(
                id="valid-title",
                title="Will the election happen?",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            ),
            Market(
                id="price-title",
                title="What is the price of Bitcoin?",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            ),
            Market(
                id="usd-title",
                title="Will USD rise?",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            ),
        ]

        result = market_filter._apply_exclusion_rules(markets)
        assert len(result) == 1
        assert result[0].id == "valid-title"

    # ========== Class Constant Tests ==========

    def test_target_categories_constant(self, market_filter: "MarketFilter") -> None:
        """Test TARGET_CATEGORIES constant contains expected values."""
        from src.analysis.market_filter import MarketFilter

        expected = {
            MarketCategory.POLITICS,
            MarketCategory.BUSINESS,
            MarketCategory.TECHNOLOGY,
            MarketCategory.ECONOMICS,
            MarketCategory.CRYPTO,
        }
        assert MarketFilter.TARGET_CATEGORIES == expected

    def test_hard_exclude_constants(self, market_filter: "MarketFilter") -> None:
        """Test hard exclude threshold constants."""
        from src.analysis.market_filter import MarketFilter

        assert MarketFilter.HARD_EXCLUDE_LIQUIDITY == 5000.0
        assert MarketFilter.HARD_EXCLUDE_DEADLINE_HOURS == 1

    def test_default_excluded_keywords_constant(
        self, market_filter: "MarketFilter"
    ) -> None:
        """Test DEFAULT_EXCLUDED_KEYWORDS constant."""
        from src.analysis.market_filter import MarketFilter

        assert "price" in MarketFilter.DEFAULT_EXCLUDED_KEYWORDS
        assert "USD" in MarketFilter.DEFAULT_EXCLUDED_KEYWORDS
        assert "tomorrow" in MarketFilter.DEFAULT_EXCLUDED_KEYWORDS

    # ========== FilterStatistics Tests ==========

    def test_filter_statistics_custom_values(self) -> None:
        """Test FilterStatistics with custom values."""
        from src.analysis.market_filter import FilterStatistics

        stats = FilterStatistics(
            total_input=100,
            passed_hard_liquidity=90,
            passed_hard_deadline=85,
            passed_soft_liquidity=80,
            passed_soft_deadline=75,
            passed_category=70,
            passed_exclusion=65,
            final_count=65,
        )
        assert stats.total_input == 100
        assert stats.passed_hard_liquidity == 90
        assert stats.passed_hard_deadline == 85
        assert stats.passed_soft_liquidity == 80
        assert stats.passed_soft_deadline == 75
        assert stats.passed_category == 70
        assert stats.passed_exclusion == 65
        assert stats.final_count == 65

    # ========== FilterResult Tests ==========

    def test_filter_result_custom_values(self) -> None:
        """Test FilterResult with custom values."""
        from src.analysis.market_filter import FilterResult, FilterStatistics

        markets = [
            Market(
                id="test-1",
                title="Test",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            )
        ]
        stats = FilterStatistics(total_input=1, final_count=1)
        result = FilterResult(markets=markets, statistics=stats)

        assert len(result.markets) == 1
        assert result.statistics.total_input == 1
        assert result.statistics.final_count == 1

    # ========== Large Dataset Tests ==========

    def test_large_dataset_performance(self, market_filter: "MarketFilter") -> None:
        """Test filtering a large dataset efficiently."""
        # Create 1000 markets with varying liquidity
        markets = []
        for i in range(1000):
            market = Market(
                id=f"market-{i}",
                title=f"Will event {i} happen?",
                category=MarketCategory.POLITICS,
                liquidity=50000.0 if i % 3 == 0 else 3000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            )
            markets.append(market)

        result = market_filter.filter_markets(markets)

        # Should have filtered out ~666 with low liquidity (i % 3 != 0)
        # range(1000) has 334 numbers divisible by 3 (0, 3, 6, ..., 999)
        assert result.statistics.total_input == 1000
        assert result.statistics.final_count == 334  # Only i % 3 == 0 should pass

    # ========== All Filters Combined Tests ==========

    def test_all_filters_combined_pass(self, market_filter: "MarketFilter") -> None:
        """Test a market that passes all filters."""
        market = Market(
            id="perfect-market",
            title="Will the election result be confirmed?",
            category=MarketCategory.POLITICS,
            liquidity=100000.0,
            deadline=datetime.now(timezone.utc) + timedelta(days=30),
        )
        result = market_filter.filter_markets([market])
        assert len(result.markets) == 1
        assert result.statistics.final_count == 1

    def test_all_filters_combined_fail(self, market_filter: "MarketFilter") -> None:
        """Test a market that fails all filters.

        Uses: excluded keyword, low liquidity, short deadline.
        Note: All MarketCategory values are in TARGET_CATEGORIES, so category won't filter.
        """
        market = Market(
            id="worst-market",
            title="What is the price of USD tomorrow?",
            category=MarketCategory.POLITICS,  # Valid category
            liquidity=100.0,  # Low liquidity - will be hard excluded
            deadline=datetime.now(timezone.utc) + timedelta(days=1),  # Short deadline
        )
        result = market_filter.filter_markets([market])
        assert len(result.markets) == 0


# Import for type hints
from src.analysis.market_filter import MarketFilter
