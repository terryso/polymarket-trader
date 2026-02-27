"""Tests for PolymarketClient.

This module tests the Polymarket API client wrapper including:
- Client initialization
- Market data fetching (get_markets, get_market, get_order_book)
- Gamma API integration (get_active_markets)
- Error handling and exception mapping
- Retry mechanism integration

All tests are unit tests using mocks - no real API calls.
"""

from __future__ import annotations

import json
from datetime import datetime
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


@pytest.fixture
def client_with_creds(mock_settings: MagicMock) -> PolymarketClient:
    """Create a PolymarketClient with credentials for testing."""
    mock_settings.polymarket.pk = "test_private_key_12345"
    mock_settings.polymarket.proxy_wallet = "0x1234567890abcdef1234567890abcdef12345678"
    with patch("src.api.polymarket.settings", mock_settings):
        return PolymarketClient()


class TestPolymarketClientInit:
    """Tests for PolymarketClient initialization."""

    def test_init_read_only_mode(
        self, mock_settings: MagicMock, mock_clob_client: MagicMock
    ) -> None:
        """Test client initialization in read-only mode."""
        mock_settings.polymarket.pk = ""
        mock_settings.polymarket.proxy_wallet = ""

        with patch("src.api.polymarket.settings", mock_settings):
            with patch("src.api.polymarket.ClobClient", return_value=mock_clob_client):
                client = PolymarketClient()

        assert client._host == PolymarketClient.DEFAULT_HOST
        assert client._chain_id == PolymarketClient.DEFAULT_CHAIN_ID

    def test_init_with_custom_host_and_chain(
        self, mock_settings: MagicMock, mock_clob_client: MagicMock
    ) -> None:
        """Test client initialization with custom host and chain ID."""
        with patch("src.api.polymarket.settings", mock_settings):
            with patch("src.api.polymarket.ClobClient", return_value=mock_clob_client):
                client = PolymarketClient(host="https://test.example.com", chain_id=1)

        assert client._host == "https://test.example.com"
        assert client._chain_id == 1

    def test_init_with_credentials(
        self, mock_settings: MagicMock, mock_clob_client: MagicMock
    ) -> None:
        """Test client initialization with credentials."""
        mock_settings.polymarket.pk = "test_key"
        mock_settings.polymarket.proxy_wallet = (
            "0x1234567890abcdef1234567890abcdef12345678"
        )

        with patch("src.api.polymarket.settings", mock_settings):
            with patch("src.api.polymarket.ClobClient", return_value=mock_clob_client):
                client = PolymarketClient()

        assert client._host == PolymarketClient.DEFAULT_HOST


class TestGetMarkets:
    """Tests for get_markets method."""

    def test_get_markets_success(
        self, client: PolymarketClient, mock_clob_client: MagicMock
    ) -> None:
        """Test successful market fetching."""
        mock_response = [
            {
                "condition_id": "market-1",
                "question": "Will Bitcoin reach $100k?",
                "category": "Crypto",
                "tokens": [
                    {"outcome": "Yes", "price": "0.65"},
                    {"outcome": "No", "price": "0.35"},
                ],
                "liquidity": "50000.0",
                "end_date_iso": "2026-12-31T00:00:00Z",
            },
            {
                "condition_id": "market-2",
                "question": "Will ETH flip BTC?",
                "category": "Crypto",
                "tokens": [
                    {"outcome": "Yes", "price": "0.10"},
                    {"outcome": "No", "price": "0.90"},
                ],
                "liquidity": "10000.0",
            },
        ]
        mock_clob_client.get_markets.return_value = mock_response
        client._client = mock_clob_client

        markets = client.get_markets()

        assert len(markets) == 2
        assert markets[0].id == "market-1"
        assert markets[0].title == "Will Bitcoin reach $100k?"
        assert markets[0].category == MarketCategory.CRYPTO
        assert markets[0].yes_price == 0.65
        assert markets[0].no_price == 0.35
        assert markets[0].liquidity == 50000.0

    def test_get_markets_empty_response(
        self, client: PolymarketClient, mock_clob_client: MagicMock
    ) -> None:
        """Test empty market list response."""
        mock_clob_client.get_markets.return_value = []
        client._client = mock_clob_client

        markets = client.get_markets()

        assert len(markets) == 0

    def test_get_markets_with_pagination(
        self, client: PolymarketClient, mock_clob_client: MagicMock
    ) -> None:
        """Test market fetching with pagination cursor."""
        mock_clob_client.get_markets.return_value = []
        client._client = mock_clob_client

        client.get_markets(next_cursor="NEXT_PAGE_TOKEN")

        mock_clob_client.get_markets.assert_called_once_with(
            next_cursor="NEXT_PAGE_TOKEN"
        )

    def test_get_markets_network_error(
        self, client: PolymarketClient, mock_clob_client: MagicMock
    ) -> None:
        """Test network error handling in get_markets."""
        mock_clob_client.get_markets.side_effect = Exception("Connection failed")
        client._client = mock_clob_client

        with pytest.raises(NetworkError):
            client.get_markets()

    def test_get_markets_timeout_error(
        self, client: PolymarketClient, mock_clob_client: MagicMock
    ) -> None:
        """Test timeout error handling in get_markets."""
        mock_clob_client.get_markets.side_effect = TimeoutError("Request timed out")
        client._client = mock_clob_client

        with pytest.raises(RequestTimeoutError):
            client.get_markets()

    def test_get_markets_rate_limit_error(
        self, client: PolymarketClient, mock_clob_client: MagicMock
    ) -> None:
        """Test rate limit error handling in get_markets."""
        mock_clob_client.get_markets.side_effect = Exception("429 Too Many Requests")
        client._client = mock_clob_client

        with pytest.raises(RateLimitError):
            client.get_markets()


class TestGetMarket:
    """Tests for get_market method."""

    def test_get_market_success(
        self, client: PolymarketClient, mock_clob_client: MagicMock
    ) -> None:
        """Test successful single market fetching."""
        mock_response = {
            "condition_id": "market-123",
            "question": "Will X happen?",
            "description": "A test market",
            "category": "Politics",
            "tokens": [
                {"outcome": "Yes", "price": "0.75"},
                {"outcome": "No", "price": "0.25"},
            ],
            "liquidity": "100000.0",
            "end_date_iso": "2026-06-30T00:00:00Z",
        }
        mock_clob_client.get_market.return_value = mock_response
        client._client = mock_clob_client

        market = client.get_market("market-123")

        assert market is not None
        assert market.id == "market-123"
        assert market.title == "Will X happen?"
        assert market.description == "A test market"
        assert market.category == MarketCategory.POLITICS
        assert market.yes_price == 0.75
        assert market.no_price == 0.25
        assert market.liquidity == 100000.0

    def test_get_market_not_found(
        self, client: PolymarketClient, mock_clob_client: MagicMock
    ) -> None:
        """Test market not found response."""
        mock_clob_client.get_market.return_value = None
        client._client = mock_clob_client

        market = client.get_market("nonexistent-market")

        assert market is None

    def test_get_market_empty_response(
        self, client: PolymarketClient, mock_clob_client: MagicMock
    ) -> None:
        """Test empty market response - should still parse but with empty id."""
        mock_response = {
            "question": "Empty market test",
        }
        mock_clob_client.get_market.return_value = mock_response
        client._client = mock_clob_client

        market = client.get_market("market-123")

        # Should return a Market with title but no condition_id
        assert market is not None
        assert market.title == "Empty market test"
        assert market.id == ""  # No condition_id in response

    def test_get_market_network_error(
        self, client: PolymarketClient, mock_clob_client: MagicMock
    ) -> None:
        """Test network error handling in get_market."""
        mock_clob_client.get_market.side_effect = Exception("Connection failed")
        client._client = mock_clob_client

        with pytest.raises(NetworkError):
            client.get_market("market-123")


class TestGetOrderBook:
    """Tests for get_order_book method."""

    def test_get_order_book_success(
        self, client: PolymarketClient, mock_clob_client: MagicMock
    ) -> None:
        """Test successful order book fetching."""
        mock_response = MagicMock()
        mock_response.market = "market-123"
        mock_response.asset_id = "token-456"
        mock_response.bids = [
            MagicMock(price="0.65", size="100"),
            MagicMock(price="0.64", size="200"),
        ]
        mock_response.asks = [
            MagicMock(price="0.66", size="150"),
            MagicMock(price="0.67", size="100"),
        ]
        mock_clob_client.get_order_book.return_value = mock_response
        client._client = mock_clob_client

        order_book = client.get_order_book("token-456")

        assert order_book["market"] == "market-123"
        assert order_book["asset_id"] == "token-456"
        assert len(order_book["bids"]) == 2
        assert len(order_book["asks"]) == 2
        assert order_book["bids"][0]["price"] == "0.65"
        assert order_book["bids"][0]["size"] == "100"

    def test_get_order_book_empty(
        self, client: PolymarketClient, mock_clob_client: MagicMock
    ) -> None:
        """Test empty order book response."""
        mock_response = MagicMock()
        mock_response.market = ""
        mock_response.asset_id = ""
        mock_response.bids = []
        mock_response.asks = []
        mock_clob_client.get_order_book.return_value = mock_response
        client._client = mock_clob_client

        order_book = client.get_order_book("token-456")

        assert order_book["bids"] == []
        assert order_book["asks"] == []

    def test_get_order_book_network_error(
        self, client: PolymarketClient, mock_clob_client: MagicMock
    ) -> None:
        """Test network error handling in get_order_book."""
        mock_clob_client.get_order_book.side_effect = Exception("Connection failed")
        client._client = mock_clob_client

        with pytest.raises(NetworkError):
            client.get_order_book("token-456")


class TestCategoryMapping:
    """Tests for category mapping functionality."""

    def test_map_category_politics(self, client: PolymarketClient) -> None:
        """Test politics category mapping."""
        assert client._map_category("Politics") == MarketCategory.POLITICS
        assert client._map_category("POLITICAL EVENTS") == MarketCategory.POLITICS

    def test_map_category_crypto(self, client: PolymarketClient) -> None:
        """Test crypto category mapping."""
        assert client._map_category("Crypto") == MarketCategory.CRYPTO
        assert client._map_category("Cryptocurrency") == MarketCategory.CRYPTO

    def test_map_category_technology(self, client: PolymarketClient) -> None:
        """Test technology category mapping."""
        assert client._map_category("Technology") == MarketCategory.TECHNOLOGY
        assert client._map_category("Tech") == MarketCategory.TECHNOLOGY

    def test_map_category_business(self, client: PolymarketClient) -> None:
        """Test business category mapping."""
        assert client._map_category("Business") == MarketCategory.BUSINESS
        assert client._map_category("Finance") == MarketCategory.BUSINESS

    def test_map_category_economics(self, client: PolymarketClient) -> None:
        """Test economics category mapping."""
        assert client._map_category("Economics") == MarketCategory.ECONOMICS
        assert client._map_category("Economic Indicators") == MarketCategory.ECONOMICS

    def test_map_category_none(self, client: PolymarketClient) -> None:
        """Test None category mapping."""
        assert client._map_category(None) is None
        assert client._map_category("") is None
        assert client._map_category("Unknown Category") is None


class TestDatetimeParsing:
    """Tests for datetime parsing functionality."""

    def test_parse_datetime_iso_format(self, client: PolymarketClient) -> None:
        """Test ISO format datetime parsing."""
        result = client._parse_datetime("2026-12-31T00:00:00Z")
        assert result is not None
        assert result.year == 2026
        assert result.month == 12
        assert result.day == 31

    def test_parse_datetime_with_timezone(self, client: PolymarketClient) -> None:
        """Test datetime parsing with timezone."""
        result = client._parse_datetime("2026-06-15T10:30:00+00:00")
        assert result is not None
        assert result.year == 2026
        assert result.month == 6
        assert result.day == 15

    def test_parse_datetime_simple_format(self, client: PolymarketClient) -> None:
        """Test simple datetime format parsing."""
        result = client._parse_datetime("2026-12-31 00:00:00")
        assert result is not None
        assert result.year == 2026

    def test_parse_datetime_date_only(self, client: PolymarketClient) -> None:
        """Test date-only format parsing."""
        result = client._parse_datetime("2026-12-31")
        assert result is not None
        assert result.year == 2026
        assert result.month == 12
        assert result.day == 31

    def test_parse_datetime_invalid(self, client: PolymarketClient) -> None:
        """Test invalid datetime parsing."""
        result = client._parse_datetime("invalid-date")
        assert result is None

    def test_parse_datetime_none(self, client: PolymarketClient) -> None:
        """Test None datetime parsing."""
        result = client._parse_datetime(None)
        assert result is None


class TestExceptionMapping:
    """Tests for exception mapping functionality."""

    def test_map_exception_timeout(self, client: PolymarketClient) -> None:
        """Test timeout exception mapping."""
        e = TimeoutError("Request timed out")
        result = client._map_exception(e, "test_endpoint")
        assert isinstance(result, RequestTimeoutError)

    def test_map_exception_timeout_in_message(self, client: PolymarketClient) -> None:
        """Test timeout detection from message."""
        e = Exception("Connection timeout occurred")
        result = client._map_exception(e, "test_endpoint")
        assert isinstance(result, RequestTimeoutError)

    def test_map_exception_rate_limit_429(self, client: PolymarketClient) -> None:
        """Test rate limit detection from 429 status."""
        e = Exception("HTTP 429 Too Many Requests")
        result = client._map_exception(e, "test_endpoint")
        assert isinstance(result, RateLimitError)

    def test_map_exception_rate_limit_message(self, client: PolymarketClient) -> None:
        """Test rate limit detection from message."""
        e = Exception("Rate limit exceeded, please retry later")
        result = client._map_exception(e, "test_endpoint")
        assert isinstance(result, RateLimitError)

    def test_map_exception_network(self, client: PolymarketClient) -> None:
        """Test generic network exception mapping."""
        e = Exception("Connection refused")
        result = client._map_exception(e, "test_endpoint")
        assert isinstance(result, NetworkError)


class TestSafeFloat:
    """Tests for safe float conversion."""

    def test_safe_float_valid(self, client: PolymarketClient) -> None:
        """Test valid float conversion."""
        assert client._safe_float(3.14) == 3.14
        assert client._safe_float("3.14") == 3.14
        assert client._safe_float(100) == 100.0

    def test_safe_float_invalid(self, client: PolymarketClient) -> None:
        """Test invalid float conversion."""
        assert client._safe_float("invalid") is None
        assert client._safe_float(None) is None

    def test_safe_float_edge_cases(self, client: PolymarketClient) -> None:
        """Test edge cases for float conversion."""
        assert client._safe_float(0) == 0.0
        assert client._safe_float("") is None


class TestGammaMarket:
    """Tests for GammaMarket dataclass."""

    def test_gamma_market_creation(self) -> None:
        """Test creating a GammaMarket instance."""
        market = GammaMarket(
            condition_id="test_id",
            question="Test question?",
            slug="test-slug",
            active=True,
            closed=False,
            accepting_orders=True,
            enable_order_book=True,
            clob_token_ids=["token1", "token2"],
        )

        assert market.condition_id == "test_id"
        assert market.question == "Test question?"
        assert market.active is True
        assert market.closed is False

    def test_gamma_market_to_market(self) -> None:
        """Test converting GammaMarket to Market."""
        gamma = GammaMarket(
            condition_id="test_id",
            question="Test question?",
            slug="test-slug",
            active=True,
            closed=False,
            accepting_orders=True,
            enable_order_book=True,
            clob_token_ids=["token1"],
            volume_24h=100000.0,
            liquidity=50000.0,
            category="Politics",
        )

        market = gamma.to_market()

        assert isinstance(market, Market)
        assert market.id == "test_id"
        assert market.title == "Test question?"
        assert market.liquidity == 50000.0

    def test_gamma_market_category_mapping(self) -> None:
        """Test category mapping in GammaMarket."""
        gamma = GammaMarket(
            condition_id="test_id",
            question="Test?",
            slug="test",
            active=True,
            closed=False,
            accepting_orders=True,
            enable_order_book=True,
            clob_token_ids=[],
            category="Crypto",
        )

        market = gamma.to_market()
        assert market.category == MarketCategory.CRYPTO


class TestGetActiveMarkets:
    """Tests for get_active_markets method (Gamma API)."""

    @pytest.fixture
    def mock_gamma_response(self) -> list[dict]:
        """Create mock Gamma API response."""
        return [
            {
                "conditionId": "0x123abc",
                "question": "Will Bitcoin reach $100k?",
                "slug": "bitcoin-100k",
                "active": True,
                "closed": False,
                "acceptingOrders": True,
                "enableOrderBook": True,
                "clobTokenIds": json.dumps(["token_abc", "token_xyz"]),
                "volume24hr": 1500000.0,
                "liquidityNum": 500000.0,
                "category": "Crypto",
                "endDateIso": "2025-12-31T23:59:59Z",
            },
            {
                "conditionId": "0x456def",
                "question": "Will Trump win 2024?",
                "slug": "trump-2024",
                "active": True,
                "closed": False,
                "acceptingOrders": True,
                "enableOrderBook": True,
                "clobTokenIds": json.dumps(["token_def"]),
                "volume24hr": 2000000.0,
                "liquidityNum": 800000.0,
                "category": "Politics",
            },
        ]

    def test_get_active_markets_success(
        self,
        mock_settings: MagicMock,
        mock_gamma_response: list[dict],
    ) -> None:
        """Test successful get_active_markets call."""
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = mock_gamma_response
        mock_http_response.raise_for_status = MagicMock()

        with patch("src.api.polymarket.settings", mock_settings):
            with patch("src.api.polymarket.ClobClient"):
                with patch("httpx.Client") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.get.return_value = mock_http_response
                    mock_client_class.return_value = mock_client

                    client = PolymarketClient()
                    markets = client.get_active_markets(limit=10)

        assert len(markets) == 2
        assert markets[0].question == "Will Bitcoin reach $100k?"
        assert markets[0].volume_24h == 1500000.0
        assert markets[1].category == "Politics"

    def test_get_active_markets_with_filters(
        self,
        mock_settings: MagicMock,
        mock_gamma_response: list[dict],
    ) -> None:
        """Test get_active_markets with volume and liquidity filters."""
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = mock_gamma_response
        mock_http_response.raise_for_status = MagicMock()

        with patch("src.api.polymarket.settings", mock_settings):
            with patch("src.api.polymarket.ClobClient"):
                with patch("httpx.Client") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.get.return_value = mock_http_response
                    mock_client_class.return_value = mock_client

                    client = PolymarketClient()
                    client.get_active_markets(
                        limit=10,
                        min_volume_24h=100000,
                        min_liquidity=50000,
                    )

        # Verify params were passed
        call_args = mock_client.get.call_args
        params = call_args.kwargs.get("params", call_args[1].get("params", {}))
        assert params.get("volume_num_min") == 100000
        assert params.get("liquidity_num_min") == 50000

    def test_get_active_markets_timeout_error(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test get_active_markets handles timeout."""
        with patch("src.api.polymarket.settings", mock_settings):
            with patch("src.api.polymarket.ClobClient"):
                with patch("httpx.Client") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.get.side_effect = httpx.TimeoutException("Timeout")
                    mock_client_class.return_value = mock_client

                    client = PolymarketClient()
                    with pytest.raises(RequestTimeoutError):
                        client.get_active_markets()

    def test_get_active_markets_rate_limit_error(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test get_active_markets handles rate limit."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate limited", request=MagicMock(), response=mock_response
        )

        with patch("src.api.polymarket.settings", mock_settings):
            with patch("src.api.polymarket.ClobClient"):
                with patch("httpx.Client") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.get.return_value = mock_response
                    mock_client_class.return_value = mock_client

                    client = PolymarketClient()
                    with pytest.raises(RateLimitError):
                        client.get_active_markets()

    def test_get_active_markets_network_error(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test get_active_markets handles network errors."""
        with patch("src.api.polymarket.settings", mock_settings):
            with patch("src.api.polymarket.ClobClient"):
                with patch("httpx.Client") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.get.side_effect = httpx.RequestError("Network error")
                    mock_client_class.return_value = mock_client

                    client = PolymarketClient()
                    with pytest.raises(NetworkError):
                        client.get_active_markets()


class TestParseGammaMarket:
    """Tests for _parse_gamma_market method."""

    def test_parse_gamma_market_basic(self, client: PolymarketClient) -> None:
        """Test parsing basic Gamma market data."""
        data = {
            "conditionId": "0xabc123",
            "question": "Test question?",
            "slug": "test-slug",
            "active": True,
            "closed": False,
            "acceptingOrders": True,
            "enableOrderBook": True,
            "clobTokenIds": '["token1", "token2"]',
        }

        market = client._parse_gamma_market(data)

        assert market.condition_id == "0xabc123"
        assert market.question == "Test question?"
        assert market.active is True
        assert market.clob_token_ids == ["token1", "token2"]

    def test_parse_gamma_market_with_numeric_fields(
        self, client: PolymarketClient
    ) -> None:
        """Test parsing Gamma market with volume and liquidity."""
        data = {
            "conditionId": "0xabc",
            "question": "Test?",
            "slug": "test",
            "active": True,
            "closed": False,
            "acceptingOrders": True,
            "enableOrderBook": True,
            "clobTokenIds": "[]",
            "volume24hr": 1000000.5,
            "liquidityNum": 500000.25,
        }

        market = client._parse_gamma_market(data)

        assert market.volume_24h == 1000000.5
        assert market.liquidity == 500000.25

    def test_parse_gamma_market_invalid_token_ids(
        self, client: PolymarketClient
    ) -> None:
        """Test parsing Gamma market with invalid token IDs JSON."""
        data = {
            "conditionId": "0xabc",
            "question": "Test?",
            "slug": "test",
            "active": True,
            "closed": False,
            "acceptingOrders": True,
            "enableOrderBook": True,
            "clobTokenIds": "invalid json",
        }

        market = client._parse_gamma_market(data)

        assert market.clob_token_ids == []


class TestClientLifecycle:
    """Tests for client lifecycle management."""

    def test_client_context_manager(
        self, mock_settings: MagicMock, mock_clob_client: MagicMock
    ) -> None:
        """Test client as context manager."""
        with patch("src.api.polymarket.settings", mock_settings):
            with patch("src.api.polymarket.ClobClient", return_value=mock_clob_client):
                with PolymarketClient() as client:
                    assert client._http_client is None

                # After exit, client should be closed
                # (http_client would be None if never used)

    def test_client_close_method(
        self, mock_settings: MagicMock, mock_clob_client: MagicMock
    ) -> None:
        """Test explicit client close."""
        with patch("src.api.polymarket.settings", mock_settings):
            with patch("src.api.polymarket.ClobClient", return_value=mock_clob_client):
                client = PolymarketClient()
                # Create HTTP client
                _ = client._get_http_client()
                assert client._http_client is not None

                client.close()
                assert client._http_client is None
