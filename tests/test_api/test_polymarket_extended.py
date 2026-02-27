# tests/test_api/test_polymarket_extended.py
"""Extended tests for PolymarketClient to cover uncovered lines.

This module tests edge cases that hit:
- Lines 79: GammaMarket._map_category fallback
- Lines 270: _parse_markets_response empty result edge case
- Lines 453, 457-460: _parse_markets_response unexpected format handling
- Lines 468-472: _parse_market_response exception handling
- Lines 673-678: Rate limit error with Retry-After header extraction
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.api.polymarket import GammaMarket, PolymarketClient
from src.exceptions import NetworkError, RateLimitError, RequestTimeoutError
from src.models import Market, MarketCategory


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings for testing."""
    mock = MagicMock()
    mock.polymarket.pk = ""
    mock.polymarket.proxy_wallet = ""
    mock.polymarket.trader_address = ""
    return mock


@pytest.fixture
def mock_clob_client() -> MagicMock:
    """Create mock ClobClient for testing."""
    return MagicMock()


@pytest.fixture
def client(mock_settings: MagicMock) -> PolymarketClient:
    """Create a PolymarketClient instance for testing."""
    with patch("src.api.polymarket.settings", mock_settings):
        return PolymarketClient()


class TestGammaMarketMapCategoryFallback:
    """Tests for GammaMarket._map_category fallback behavior."""

    def test_map_category_with_none_category(self) -> None:
        """Test _map_category returns None when category is None."""
        gamma = GammaMarket(
            condition_id="test_id",
            question="Test?",
            slug="test",
            active=True,
            closed=False,
            accepting_orders=True,
            enable_order_book=True,
            clob_token_ids=[],
            category=None,
        )

        market = gamma.to_market()
        assert market.category is None

    def test_map_category_creates_client_instance(self) -> None:
        """Test _map_category creates PolymarketClient instance for mapping."""
        # This tests the fallback path where _map_category creates a client
        gamma = GammaMarket(
            condition_id="test_id",
            question="Test?",
            slug="test",
            active=True,
            closed=False,
            accepting_orders=True,
            enable_order_book=True,
            clob_token_ids=[],
            category="Politics",
        )

        # The _map_category method creates a PolymarketClient instance
        # to use its _map_category method
        market = gamma.to_market()
        assert market.category == MarketCategory.POLITICS


class TestParseMarketsResponseEdgeCases:
    """Tests for _parse_markets_response edge cases."""

    def test_parse_markets_response_unexpected_format(
        self, client: PolymarketClient
    ) -> None:
        """Test _parse_markets_response with unexpected format."""
        # Pass a string instead of dict or list
        result = client._parse_markets_response("unexpected format")  # type: ignore
        assert result == []

    def test_parse_markets_response_dict_without_data(
        self, client: PolymarketClient
    ) -> None:
        """Test _parse_markets_response with dict but no 'data' key."""
        result = client._parse_markets_response({"other_key": "value"})
        assert result == []

    def test_parse_markets_response_with_exception_in_parsing(
        self, client: PolymarketClient
    ) -> None:
        """Test _parse_markets_response handles exception during parsing."""
        # Create data that will cause exception in _parse_market_response
        invalid_market_data = [
            {
                "condition_id": "valid-market",
                "question": "Valid question",
                "tokens": [],
            },
            # This will cause an exception because tokens access might fail
            {"condition_id": None, "question": None},
        ]

        # Should not raise, just skip invalid markets
        with patch.object(
            client,
            "_parse_market_response",
            side_effect=[
                Market(id="valid-market", title="Valid question"),
                Exception("Parse error"),
            ],
        ):
            result = client._parse_markets_response(invalid_market_data)
            # Should have caught the exception and continued
            assert len(result) >= 1  # At least the valid one


class TestExceptionMappingExtended:
    """Extended tests for exception mapping with retry-after header."""

    def test_map_exception_rate_limit_with_retry_after_header(
        self, client: PolymarketClient
    ) -> None:
        """Test rate limit error extracts Retry-After header."""
        # Create exception with response.headers
        mock_response = MagicMock()
        mock_response.headers = {"Retry-After": "60"}

        e = Exception("429 Too Many Requests")
        e.response = mock_response  # type: ignore

        result = client._map_exception(e, "test_endpoint")
        assert isinstance(result, RateLimitError)
        assert result.retry_after == 60

    def test_map_exception_rate_limit_with_invalid_retry_after(
        self, client: PolymarketClient
    ) -> None:
        """Test rate limit error handles invalid Retry-After header."""
        mock_response = MagicMock()
        mock_response.headers = {"Retry-After": "invalid"}

        e = Exception("429 Too Many Requests")
        e.response = mock_response  # type: ignore

        result = client._map_exception(e, "test_endpoint")
        assert isinstance(result, RateLimitError)
        assert result.retry_after is None

    def test_map_exception_rate_limit_without_response_attr(
        self, client: PolymarketClient
    ) -> None:
        """Test rate limit error when exception has no response attribute."""
        e = Exception("429 Too Many Requests")
        # No response attribute

        result = client._map_exception(e, "test_endpoint")
        assert isinstance(result, RateLimitError)
        assert result.retry_after is None

    def test_map_exception_rate_limit_with_no_headers(
        self, client: PolymarketClient
    ) -> None:
        """Test rate limit error when response has no headers."""
        mock_response = MagicMock()
        mock_response.headers = {}  # Empty headers

        e = Exception("429 Too Many Requests")
        e.response = mock_response  # type: ignore

        result = client._map_exception(e, "test_endpoint")
        assert isinstance(result, RateLimitError)
        assert result.retry_after is None


class TestGetMarketsExtended:
    """Extended tests for get_markets method."""

    def test_get_markets_with_dict_response(
        self, client: PolymarketClient, mock_clob_client: MagicMock
    ) -> None:
        """Test get_markets with paginated dict response format."""
        mock_response = {
            "data": [
                {
                    "condition_id": "market-1",
                    "question": "Test question?",
                    "category": "Crypto",
                    "tokens": [
                        {"outcome": "Yes", "price": "0.5"},
                        {"outcome": "No", "price": "0.5"},
                    ],
                }
            ],
            "next_cursor": "NEXT_PAGE",
        }
        mock_clob_client.get_markets.return_value = mock_response
        client._client = mock_clob_client

        markets = client.get_markets()

        assert len(markets) == 1
        assert markets[0].id == "market-1"

    def test_get_markets_with_list_response(
        self, client: PolymarketClient, mock_clob_client: MagicMock
    ) -> None:
        """Test get_markets with list response format."""
        mock_response = [
            {
                "condition_id": "market-1",
                "question": "Test question?",
                "category": "Crypto",
                "tokens": [],
            }
        ]
        mock_clob_client.get_markets.return_value = mock_response
        client._client = mock_clob_client

        markets = client.get_markets()

        assert len(markets) == 1


class TestParseMarketResponseExtended:
    """Extended tests for _parse_market_response method."""

    def test_parse_market_response_with_hash_fallback(
        self, client: PolymarketClient
    ) -> None:
        """Test _parse_market_response uses hash when condition_id missing."""
        data = {
            "hash": "hash-based-id",
            "question": "Test question?",
            "category": "Crypto",
            "tokens": [],
        }

        market = client._parse_market_response(data)

        assert market.id == "hash-based-id"
        assert market.title == "Test question?"

    def test_parse_market_response_with_no_tokens(
        self, client: PolymarketClient
    ) -> None:
        """Test _parse_market_response handles missing tokens."""
        data = {
            "condition_id": "market-1",
            "question": "Test?",
            "category": "Crypto",
            # No tokens key
        }

        market = client._parse_market_response(data)

        assert market.id == "market-1"
        assert market.yes_price is None
        assert market.no_price is None

    def test_parse_market_response_with_empty_tokens(
        self, client: PolymarketClient
    ) -> None:
        """Test _parse_market_response handles empty tokens list."""
        data = {
            "condition_id": "market-1",
            "question": "Test?",
            "category": "Crypto",
            "tokens": [],
        }

        market = client._parse_market_response(data)

        assert market.id == "market-1"
        assert market.yes_price is None
        assert market.no_price is None

    def test_parse_market_response_with_yes_no_tokens(
        self, client: PolymarketClient
    ) -> None:
        """Test _parse_market_response parses YES/NO tokens correctly."""
        data = {
            "condition_id": "market-1",
            "question": "Test?",
            "category": "Politics",
            "tokens": [
                {"outcome": "Yes", "price": "0.75"},
                {"outcome": "No", "price": "0.25"},
            ],
            "liquidity": "50000.0",
        }

        market = client._parse_market_response(data)

        assert market.yes_price == 0.75
        assert market.no_price == 0.25
        assert market.liquidity == 50000.0


class TestGetActiveMarketsExtended:
    """Extended tests for get_active_markets method."""

    def test_get_active_markets_empty_response(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test get_active_markets with empty response."""
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = []
        mock_http_response.raise_for_status = MagicMock()

        with patch("src.api.polymarket.settings", mock_settings):
            with patch("src.api.polymarket.ClobClient"):
                with patch("httpx.Client") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.get.return_value = mock_http_response
                    mock_client_class.return_value = mock_client

                    client = PolymarketClient()
                    markets = client.get_active_markets()

        assert markets == []

    def test_get_active_markets_with_end_date(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test get_active_markets parses end_date correctly."""
        mock_response = [
            {
                "conditionId": "0x123",
                "question": "Test?",
                "slug": "test",
                "active": True,
                "closed": False,
                "acceptingOrders": True,
                "enableOrderBook": True,
                "clobTokenIds": "[]",
                "endDateIso": "2026-12-31T23:59:59Z",
            }
        ]

        mock_http_response = MagicMock()
        mock_http_response.json.return_value = mock_response
        mock_http_response.raise_for_status = MagicMock()

        with patch("src.api.polymarket.settings", mock_settings):
            with patch("src.api.polymarket.ClobClient"):
                with patch("httpx.Client") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.get.return_value = mock_http_response
                    mock_client_class.return_value = mock_client

                    client = PolymarketClient()
                    markets = client.get_active_markets()

        assert len(markets) == 1
        assert markets[0].end_date is not None
        assert markets[0].end_date.year == 2026
