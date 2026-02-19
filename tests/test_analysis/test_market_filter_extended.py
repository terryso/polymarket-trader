# tests/test_analysis/test_market_filter_extended.py
"""Extended tests for MarketFilter to cover uncovered lines.

This module tests edge cases that hit:
- Lines 341-342: logger.debug when deadline is None
- Lines 388-389: logger.debug for non-target category
- Lines 395-397: logger.info when markets filtered by category
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.models import Market, MarketCategory


class TestMarketFilterLogging:
    """Tests for MarketFilter logging behavior."""

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
    def market_filter(self, mock_settings: MagicMock):
        """Create a MarketFilter instance for testing."""
        from src.analysis.market_filter import MarketFilter

        return MarketFilter(settings=mock_settings)

    def test_filter_by_deadline_logs_debug_when_none(
        self, market_filter, mock_settings
    ) -> None:
        """Test _filter_by_deadline logs debug message when deadline is None."""
        from src.analysis.market_filter import MarketFilter

        # Create a market with no deadline
        market = Market(
            id="no-deadline-market",
            title="Will X happen?",
            category=MarketCategory.POLITICS,
            liquidity=50000.0,
            deadline=None,
        )

        with patch("src.analysis.market_filter.logger") as mock_logger:
            result = market_filter._filter_by_deadline([market])

            # Market should be filtered out
            assert len(result) == 0

            # Debug log should have been called
            assert mock_logger.debug.called
            debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
            assert any("no deadline" in str(call).lower() for call in debug_calls)

    def test_filter_by_deadline_logs_info_when_markets_filtered(
        self, market_filter
    ) -> None:
        """Test _filter_by_deadline logs info when markets are filtered."""
        # Create markets with no deadline
        markets = [
            Market(
                id=f"market-{i}",
                title=f"Market {i}",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=None,
            )
            for i in range(3)
        ]

        with patch("src.analysis.market_filter.logger") as mock_logger:
            result = market_filter._filter_by_deadline(markets)

            assert len(result) == 0

            # Info log should have been called with count
            assert mock_logger.info.called
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("3" in str(call) for call in info_calls)


class TestNonTargetCategoryFiltering:
    """Tests for filtering markets with non-target categories."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings."""
        settings = MagicMock()
        settings.market_filter = MagicMock()
        settings.market_filter.min_liquidity = 10000.0
        settings.market_filter.min_deadline_hours = 1
        settings.market_filter.excluded_keywords = ["price", "USD", "tomorrow"]
        settings.market_filter.controversial_keywords = []
        return settings

    def test_filter_by_category_with_non_enum_category(self, mock_settings) -> None:
        """Test _filter_by_category filters non-TARGET_CATEGORIES.

        Since MarketCategory enum only has POLITICS, BUSINESS, TECHNOLOGY,
        ECONOMICS, CRYPTO, and all are in TARGET_CATEGORIES, we need to use
        model_construct to bypass validation and create a market with a
        non-standard category.
        """
        from src.analysis.market_filter import MarketFilter

        market_filter = MarketFilter(settings=mock_settings)

        # Create a market using model_construct to bypass enum validation
        # This simulates a category not in TARGET_CATEGORIES
        market = Market.model_construct(
            id="sports-market",
            title="Will team X win?",
            category="sports",  # Not a MarketCategory enum value
            liquidity=50000.0,
            deadline=datetime.now(timezone.utc) + timedelta(days=14),
        )

        with patch("src.analysis.market_filter.logger") as mock_logger:
            result = market_filter._filter_by_category([market])

            # Market should be filtered out
            assert len(result) == 0

            # Debug log should have been called
            assert mock_logger.debug.called
            debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
            assert any(
                "category not in targets" in str(call).lower() for call in debug_calls
            )

    def test_filter_by_category_logs_info_when_markets_filtered(
        self, mock_settings
    ) -> None:
        """Test _filter_by_category logs info when markets are filtered out."""
        from src.analysis.market_filter import MarketFilter

        market_filter = MarketFilter(settings=mock_settings)

        # Create multiple markets with non-target categories
        markets = []
        for i in range(3):
            market = Market.model_construct(
                id=f"sports-market-{i}",
                title=f"Will team {i} win?",
                category="sports",
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            )
            markets.append(market)

        with patch("src.analysis.market_filter.logger") as mock_logger:
            result = market_filter._filter_by_category(markets)

            assert len(result) == 0

            # Info log should have been called
            assert mock_logger.info.called
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("category" in str(call).lower() for call in info_calls)

    def test_filter_by_category_mixed_results(self, mock_settings) -> None:
        """Test _filter_by_category with mixed target and non-target categories."""
        from src.analysis.market_filter import MarketFilter

        market_filter = MarketFilter(settings=mock_settings)

        markets = [
            # Target category - should pass
            Market(
                id="politics-market",
                title="Politics question",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            ),
            # Non-target category - should be filtered
            Market.model_construct(
                id="sports-market",
                title="Sports question",
                category="sports",
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            ),
            # None category - should pass
            Market(
                id="no-category-market",
                title="No category question",
                category=None,
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=14),
            ),
        ]

        with patch("src.analysis.market_filter.logger") as mock_logger:
            result = market_filter._filter_by_category(markets)

            # Only politics and no-category should pass
            assert len(result) == 2
            ids = {m.id for m in result}
            assert "politics-market" in ids
            assert "no-category-market" in ids
            assert "sports-market" not in ids

            # Should have logged debug for filtered market
            assert mock_logger.debug.called


class TestDeadlineFilterEdgeCases:
    """Additional edge case tests for deadline filtering."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings."""
        settings = MagicMock()
        settings.market_filter = MagicMock()
        settings.market_filter.min_liquidity = 10000.0
        settings.market_filter.min_deadline_hours = 1
        settings.market_filter.excluded_keywords = ["price", "USD", "tomorrow"]
        settings.market_filter.controversial_keywords = []
        return settings

    @pytest.fixture
    def market_filter(self, mock_settings):
        """Create a MarketFilter instance."""
        from src.analysis.market_filter import MarketFilter

        return MarketFilter(settings=mock_settings)

    def test_filter_by_deadline_all_none(self, market_filter) -> None:
        """Test _filter_by_deadline with all markets having None deadline."""
        markets = [
            Market(
                id=f"market-{i}",
                title=f"Market {i}",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=None,
            )
            for i in range(5)
        ]

        result = market_filter._filter_by_deadline(markets)
        assert len(result) == 0

    def test_filter_by_deadline_all_pass(self, market_filter) -> None:
        """Test _filter_by_deadline with all markets passing."""
        markets = [
            Market(
                id=f"market-{i}",
                title=f"Market {i}",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=30),
            )
            for i in range(5)
        ]

        result = market_filter._filter_by_deadline(markets)
        assert len(result) == 5

    def test_filter_by_deadline_mixed_none_and_valid(self, market_filter) -> None:
        """Test _filter_by_deadline with mix of None and valid deadlines."""
        markets = [
            Market(
                id="market-none",
                title="No deadline",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=None,
            ),
            Market(
                id="market-valid",
                title="Valid deadline",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=30),
            ),
            Market(
                id="market-short",
                title="Short deadline",
                category=MarketCategory.POLITICS,
                liquidity=50000.0,
                deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
            ),
        ]

        result = market_filter._filter_by_deadline(markets)
        assert len(result) == 1
        assert result[0].id == "market-valid"
