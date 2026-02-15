"""Tests for MarketFetcher."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import BotError, DatabaseError, NetworkError, RateLimitError, RequestTimeoutError
from src.models import Market, MarketCategory
from src.storage.market_fetcher import MarketFetcher


# Category mapping matching src.api.polymarket.PolymarketClient._map_category()
_CATEGORY_MAP: dict[str, MarketCategory] = {
    "politics": MarketCategory.POLITICS,
    "political": MarketCategory.POLITICS,
    "business": MarketCategory.BUSINESS,
    "finance": MarketCategory.BUSINESS,
    "technology": MarketCategory.TECHNOLOGY,
    "tech": MarketCategory.TECHNOLOGY,
    "economics": MarketCategory.ECONOMICS,
    "economic": MarketCategory.ECONOMICS,
    "crypto": MarketCategory.CRYPTO,
    "cryptocurrency": MarketCategory.CRYPTO,
}


@dataclass
class MockGammaMarket:
    """Mock GammaMarket for testing.

    This mock replicates the behavior of src.api.polymarket.GammaMarket.to_market()
    for consistent testing.
    """

    condition_id: str
    question: str
    slug: str
    active: bool
    closed: bool
    accepting_orders: bool
    enable_order_book: bool
    clob_token_ids: list[str]
    volume_24h: float | None = None
    liquidity: float | None = None
    category: str | None = None
    end_date: datetime | None = None

    def to_market(self) -> Market:
        """Convert to Market model matching real GammaMarket behavior."""
        category: MarketCategory | None = None
        if self.category:
            category = _CATEGORY_MAP.get(self.category.lower())
        return Market(
            id=self.condition_id,
            title=self.question,
            category=category,
            liquidity=self.liquidity,
            deadline=self.end_date,
        )


class TestMarketFetcher:
    """Tests for MarketFetcher class."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock PolymarketClient."""
        return MagicMock()

    @pytest.fixture
    def mock_repo(self) -> AsyncMock:
        """Create a mock MarketRepository."""
        repo = AsyncMock()
        repo.save_markets = AsyncMock(return_value=0)
        repo.update_last_fetch_time = AsyncMock()
        return repo

    @pytest.fixture
    def fetcher(
        self, mock_client: MagicMock, mock_repo: AsyncMock
    ) -> MarketFetcher:
        """Create a MarketFetcher with mocked dependencies."""
        return MarketFetcher(client=mock_client, repo=mock_repo)

    @pytest.fixture
    def sample_gamma_markets(self) -> list[MockGammaMarket]:
        """Create sample GammaMarket list for testing."""
        return [
            MockGammaMarket(
                condition_id="market-1",
                question="Will X happen?",
                slug="will-x-happen",
                active=True,
                closed=False,
                accepting_orders=True,
                enable_order_book=True,
                clob_token_ids=["token-1", "token-2"],
                liquidity=50000.0,
                category="politics",
            ),
            MockGammaMarket(
                condition_id="market-2",
                question="Will Y happen?",
                slug="will-y-happen",
                active=True,
                closed=False,
                accepting_orders=True,
                enable_order_book=True,
                clob_token_ids=["token-3", "token-4"],
                liquidity=75000.0,
                category="crypto",
            ),
        ]

    # ==================== fetch_and_store_markets tests ====================

    @pytest.mark.asyncio
    async def test_fetch_and_store_markets_success(
        self,
        fetcher: MarketFetcher,
        mock_client: MagicMock,
        mock_repo: AsyncMock,
        sample_gamma_markets: list[MockGammaMarket],
    ) -> None:
        """Test successful fetch and store of markets."""
        mock_client.get_active_markets.return_value = sample_gamma_markets
        mock_repo.save_markets.return_value = 2

        count = await fetcher.fetch_and_store_markets()

        assert count == 2
        mock_client.get_active_markets.assert_called_once_with(
            limit=100, min_liquidity=None
        )
        mock_repo.save_markets.assert_called_once()
        mock_repo.update_last_fetch_time.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_and_store_markets_with_filters(
        self,
        fetcher: MarketFetcher,
        mock_client: MagicMock,
        mock_repo: AsyncMock,
        sample_gamma_markets: list[MockGammaMarket],
    ) -> None:
        """Test fetch with custom limit and liquidity filter."""
        mock_client.get_active_markets.return_value = sample_gamma_markets
        mock_repo.save_markets.return_value = 2

        count = await fetcher.fetch_and_store_markets(
            limit=50, min_liquidity=10000.0
        )

        assert count == 2
        mock_client.get_active_markets.assert_called_once_with(
            limit=50, min_liquidity=10000.0
        )

    @pytest.mark.asyncio
    async def test_fetch_and_store_markets_empty_result(
        self,
        fetcher: MarketFetcher,
        mock_client: MagicMock,
        mock_repo: AsyncMock,
    ) -> None:
        """Test handling of empty API response."""
        mock_client.get_active_markets.return_value = []

        count = await fetcher.fetch_and_store_markets()

        assert count == 0
        mock_repo.update_last_fetch_time.assert_called_once()
        mock_repo.save_markets.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_and_store_markets_partial_save(
        self,
        fetcher: MarketFetcher,
        mock_client: MagicMock,
        mock_repo: AsyncMock,
        sample_gamma_markets: list[MockGammaMarket],
    ) -> None:
        """Test when some markets fail to save."""
        mock_client.get_active_markets.return_value = sample_gamma_markets
        mock_repo.save_markets.return_value = 1  # Only 1 saved

        count = await fetcher.fetch_and_store_markets()

        assert count == 1

    @pytest.mark.asyncio
    async def test_fetch_and_store_markets_network_error(
        self,
        fetcher: MarketFetcher,
        mock_client: MagicMock,
        mock_repo: AsyncMock,
    ) -> None:
        """Test handling of network errors."""
        mock_client.get_active_markets.side_effect = NetworkError(
            message="API error",
            endpoint="get_active_markets",
        )

        with pytest.raises(NetworkError):
            await fetcher.fetch_and_store_markets()

    @pytest.mark.asyncio
    async def test_fetch_and_store_markets_rate_limit_error(
        self,
        fetcher: MarketFetcher,
        mock_client: MagicMock,
        mock_repo: AsyncMock,
    ) -> None:
        """Test handling of rate limit errors."""
        mock_client.get_active_markets.side_effect = RateLimitError(
            message="Rate limited",
            endpoint="get_active_markets",
            retry_after=60,
        )

        with pytest.raises(RateLimitError):
            await fetcher.fetch_and_store_markets()

    @pytest.mark.asyncio
    async def test_fetch_and_store_markets_timeout_error(
        self,
        fetcher: MarketFetcher,
        mock_client: MagicMock,
        mock_repo: AsyncMock,
    ) -> None:
        """Test handling of request timeout errors."""
        mock_client.get_active_markets.side_effect = RequestTimeoutError(
            message="Request timed out",
            endpoint="get_active_markets",
            timeout_seconds=30.0,
        )

        with pytest.raises(RequestTimeoutError):
            await fetcher.fetch_and_store_markets()

    @pytest.mark.asyncio
    async def test_fetch_and_store_markets_database_error(
        self,
        fetcher: MarketFetcher,
        mock_client: MagicMock,
        mock_repo: AsyncMock,
        sample_gamma_markets: list[MockGammaMarket],
    ) -> None:
        """Test handling of database errors."""
        mock_client.get_active_markets.return_value = sample_gamma_markets
        mock_repo.save_markets.side_effect = DatabaseError(
            message="Database error",
            operation="save_markets",
        )

        with pytest.raises(DatabaseError):
            await fetcher.fetch_and_store_markets()

    @pytest.mark.asyncio
    async def test_fetch_and_store_markets_unexpected_error(
        self,
        fetcher: MarketFetcher,
        mock_client: MagicMock,
        mock_repo: AsyncMock,
    ) -> None:
        """Test handling of unexpected errors."""
        mock_client.get_active_markets.side_effect = RuntimeError(
            "Unexpected error"
        )

        with pytest.raises(BotError) as exc_info:
            await fetcher.fetch_and_store_markets()

        assert "Unexpected error" in str(exc_info.value)

    # ==================== initialization tests ====================

    def test_init_with_defaults(self) -> None:
        """Test initialization with default dependencies."""
        with patch(
            "src.storage.market_fetcher.PolymarketClient"
        ) as mock_client_class:
            with patch(
                "src.storage.market_fetcher.MarketRepository"
            ) as mock_repo_class:
                fetcher = MarketFetcher()

                mock_client_class.assert_called_once()
                mock_repo_class.assert_called_once()
                assert fetcher._client is not None
                assert fetcher._repo is not None

    def test_init_with_custom_dependencies(
        self, mock_client: MagicMock, mock_repo: AsyncMock
    ) -> None:
        """Test initialization with custom dependencies."""
        fetcher = MarketFetcher(client=mock_client, repo=mock_repo)

        assert fetcher._client is mock_client
        assert fetcher._repo is mock_repo
