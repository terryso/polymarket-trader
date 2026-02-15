"""Integration tests for PolymarketClient with real API calls.

These tests make actual HTTP requests to Polymarket APIs.
Run with: pytest tests/integration/ -v -m integration

To skip these tests during normal development:
    pytest tests/ -v -m "not integration"
"""

from __future__ import annotations

import pytest

from src.api import GammaMarket, PolymarketClient

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestPolymarketClientIntegration:
    """Integration tests for PolymarketClient with real APIs."""

    def test_client_initialization(self) -> None:
        """Test client initialization with default settings."""
        client = PolymarketClient()

        assert client._host == "https://clob.polymarket.com"
        assert client._chain_id == 137
        assert client._gamma_host == "https://gamma-api.polymarket.com"

        client.close()

    def test_get_markets_returns_markets(self) -> None:
        """Test get_markets returns a list of markets from CLOB API."""
        with PolymarketClient() as client:
            markets = client.get_markets()

            assert isinstance(markets, list)
            assert len(markets) > 0

            # Verify market structure
            market = markets[0]
            assert market.id is not None
            assert market.title is not None

    def test_get_market_by_id(self) -> None:
        """Test get_market returns a single market by condition ID."""
        with PolymarketClient() as client:
            # First get a market ID
            markets = client.get_markets()
            if not markets:
                pytest.skip("No markets available")

            condition_id = markets[0].id

            # Then fetch it individually
            market = client.get_market(condition_id)

            assert market is not None
            assert market.id == condition_id

    def test_get_market_not_found_raises_error(self) -> None:
        """Test get_market raises NetworkError for invalid ID."""
        from src.exceptions import NetworkError

        with PolymarketClient() as client:
            with pytest.raises(NetworkError):
                client.get_market("invalid_condition_id_12345")


class TestGammaApiIntegration:
    """Integration tests for Gamma API methods."""

    def test_get_active_markets_returns_markets(self) -> None:
        """Test get_active_markets returns active markets from Gamma API."""
        with PolymarketClient() as client:
            markets = client.get_active_markets(limit=5)

            assert isinstance(markets, list)
            assert len(markets) <= 5
            assert len(markets) > 0

            # Verify all are active and not closed
            for market in markets:
                assert market.active is True
                assert market.closed is False
                assert market.accepting_orders is True

    def test_get_active_markets_with_volume_filter(self) -> None:
        """Test get_active_markets with minimum volume filter."""
        with PolymarketClient() as client:
            markets = client.get_active_markets(
                limit=10,
                min_volume_24h=100000,  # $100k minimum
            )

            # All returned markets should have volume >= 100k
            for market in markets:
                if market.volume_24h is not None:
                    assert market.volume_24h >= 100000

    def test_get_active_markets_with_liquidity_filter(self) -> None:
        """Test get_active_markets with minimum liquidity filter."""
        with PolymarketClient() as client:
            markets = client.get_active_markets(
                limit=10,
                min_liquidity=50000,  # $50k minimum
            )

            # All returned markets should have liquidity >= 50k
            for market in markets:
                if market.liquidity is not None:
                    assert market.liquidity >= 50000

    def test_get_active_markets_returns_token_ids(self) -> None:
        """Test that active markets include token IDs for order book queries."""
        with PolymarketClient() as client:
            markets = client.get_active_markets(limit=5)

            # At least one market should have token IDs
            has_token_ids = any(len(m.clob_token_ids) > 0 for m in markets)
            assert has_token_ids, "No markets with token IDs found"


class TestOrderBookIntegration:
    """Integration tests for order book functionality."""

    def test_get_order_book_for_active_market(self) -> None:
        """Test get_order_book returns data for active market."""
        with PolymarketClient() as client:
            # Get an active market with order book enabled
            markets = client.get_active_markets(limit=10)

            token_id = None
            for market in markets:
                if market.enable_order_book and market.clob_token_ids:
                    token_id = market.clob_token_ids[0]
                    break

            if not token_id:
                pytest.skip("No markets with active order books found")

            # Get order book
            order_book = client.get_order_book(token_id)

            assert "market" in order_book
            assert "bids" in order_book
            assert "asks" in order_book

    def test_get_order_book_invalid_token_raises_error(self) -> None:
        """Test get_order_book raises NetworkError for invalid token."""
        from src.exceptions import NetworkError

        with PolymarketClient() as client:
            with pytest.raises(NetworkError):
                client.get_order_book("invalid_token_id_12345")


class TestGammaMarketDataclass:
    """Tests for GammaMarket dataclass."""

    def test_gamma_market_to_market_conversion(self) -> None:
        """Test converting GammaMarket to base Market."""
        from datetime import datetime

        gamma = GammaMarket(
            condition_id="test_id",
            question="Test question?",
            slug="test-slug",
            active=True,
            closed=False,
            accepting_orders=True,
            enable_order_book=True,
            clob_token_ids=["token1", "token2"],
            volume_24h=100000.0,
            liquidity=50000.0,
            category="Politics",
            end_date=datetime(2025, 12, 31),
        )

        market = gamma.to_market()

        assert market.id == "test_id"
        assert market.title == "Test question?"
        assert market.liquidity == 50000.0
