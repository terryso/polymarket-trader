"""Tests for Market model.

This module tests the Market and MarketCategory models including:
- Enum values
- Model creation (minimal and full)
- Field validation (price range)
- DateTime serialization
- JSON export
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.models import Market, MarketCategory


class TestMarketCategory:
    """Tests for MarketCategory enum."""

    def test_all_categories_exist(self) -> None:
        """Test all category values exist."""
        assert MarketCategory.POLITICS.value == "politics"
        assert MarketCategory.BUSINESS.value == "business"
        assert MarketCategory.TECHNOLOGY.value == "technology"
        assert MarketCategory.ECONOMICS.value == "economics"
        assert MarketCategory.CRYPTO.value == "crypto"

    def test_category_count(self) -> None:
        """Test total number of categories."""
        assert len(MarketCategory) == 5

    def test_category_is_str_enum(self) -> None:
        """Test MarketCategory is string enum."""
        assert isinstance(MarketCategory.POLITICS, str)
        assert MarketCategory.POLITICS == "politics"


class TestMarket:
    """Tests for Market model."""

    def test_create_market_minimal(self) -> None:
        """Test creating market with minimal required fields."""
        market = Market(id="test-123", title="Test Market")

        assert market.id == "test-123"
        assert market.title == "Test Market"
        assert market.description is None
        assert market.category is None
        assert market.yes_price is None
        assert market.no_price is None
        assert market.liquidity is None
        assert market.deadline is None
        assert market.resolution_status is None
        assert market.resolution_outcome is None
        assert market.created_at is None
        assert market.updated_at is None

    def test_create_market_full(self) -> None:
        """Test creating market with all fields."""
        market = Market(
            id="btc-100k-2026",
            title="Will Bitcoin reach $100k by end of 2026?",
            description="Bitcoin price prediction market",
            category=MarketCategory.CRYPTO,
            yes_price=0.45,
            no_price=0.55,
            liquidity=50000.0,
            deadline=datetime(2026, 12, 31, 23, 59, 59),
            resolution_status="open",
            resolution_outcome=None,
            created_at=datetime(2026, 2, 15, 10, 30, 0),
            updated_at=datetime(2026, 2, 15, 10, 30, 0),
        )

        assert market.id == "btc-100k-2026"
        assert market.title == "Will Bitcoin reach $100k by end of 2026?"
        assert market.description == "Bitcoin price prediction market"
        assert market.category == MarketCategory.CRYPTO
        assert market.yes_price == 0.45
        assert market.no_price == 0.55
        assert market.liquidity == 50000.0
        assert market.deadline == datetime(2026, 12, 31, 23, 59, 59)
        assert market.resolution_status == "open"
        assert market.resolution_outcome is None
        assert market.created_at == datetime(2026, 2, 15, 10, 30, 0)
        assert market.updated_at == datetime(2026, 2, 15, 10, 30, 0)

    def test_price_validation_valid(self) -> None:
        """Test valid price range (0-1)."""
        market = Market(id="test", title="Test", yes_price=0.0)
        assert market.yes_price == 0.0

        market = Market(id="test", title="Test", yes_price=0.5)
        assert market.yes_price == 0.5

        market = Market(id="test", title="Test", yes_price=1.0)
        assert market.yes_price == 1.0

    def test_price_validation_invalid_high(self) -> None:
        """Test price validation rejects values > 1."""
        with pytest.raises(ValueError):
            Market(id="test", title="Test", yes_price=1.5)

    def test_price_validation_invalid_negative(self) -> None:
        """Test price validation rejects negative values."""
        with pytest.raises(ValueError):
            Market(id="test", title="Test", yes_price=-0.1)

    def test_no_price_validation_invalid(self) -> None:
        """Test no_price validation rejects invalid values."""
        with pytest.raises(ValueError):
            Market(id="test", title="Test", no_price=1.5)

    def test_liquidity_validation_negative(self) -> None:
        """Test liquidity validation rejects negative values."""
        with pytest.raises(ValueError):
            Market(id="test", title="Test", liquidity=-100.0)

    def test_title_validation_empty(self) -> None:
        """Test title validation rejects empty strings."""
        with pytest.raises(ValueError):
            Market(id="test", title="")

    def test_title_validation_whitespace(self) -> None:
        """Test title is stripped of whitespace."""
        market = Market(id="test", title="  Test Market  ")
        assert market.title == "Test Market"

    def test_datetime_serialization(self) -> None:
        """Test datetime serialization to ISO 8601."""
        market = Market(
            id="test",
            title="Test",
            created_at=datetime(2026, 2, 15, 10, 30, 0),
        )

        # model_dump with mode='json' returns ISO 8601 string
        data = market.model_dump(mode="json")
        assert data["created_at"] == "2026-02-15T10:30:00"

        # model_dump_json returns ISO 8601 string
        json_str = market.model_dump_json()
        assert "2026-02-15T10:30:00" in json_str

    def test_datetime_serializer_method(self) -> None:
        """Test custom datetime serializer returns ISO format."""
        market = Market(
            id="test",
            title="Test",
            created_at=datetime(2026, 2, 15, 10, 30, 0),
        )

        # Test serialization via model_dump with mode='json'
        data = market.model_dump(mode="json")
        assert data["created_at"] == "2026-02-15T10:30:00"

    def test_model_json_export(self) -> None:
        """Test JSON export."""
        market = Market(id="test-123", title="Test Market")
        json_str = market.model_dump_json()

        assert '"id":"test-123"' in json_str
        assert '"title":"Test Market"' in json_str

    def test_model_config_validate_assignment(self) -> None:
        """Test that validate_assignment is enabled."""
        market = Market(id="test", title="Test")

        # Should validate on assignment
        with pytest.raises(ValueError):
            market.yes_price = 1.5

        # Valid assignment should work
        market.yes_price = 0.5
        assert market.yes_price == 0.5

    def test_model_config_str_strip_whitespace(self) -> None:
        """Test that str_strip_whitespace is enabled."""
        market = Market(id="  test  ", title="  Test  ")
        assert market.id == "test"
        assert market.title == "Test"

    def test_market_with_category_string(self) -> None:
        """Test market creation with category as string."""
        market = Market(id="test", title="Test", category="crypto")
        assert market.category == MarketCategory.CRYPTO

    def test_market_with_invalid_category(self) -> None:
        """Test market creation with invalid category."""
        with pytest.raises(ValueError):
            Market(id="test", title="Test", category="invalid")
