"""Market data fetching and storage service.

This module orchestrates fetching market data from Polymarket
and storing it in the local database.

Usage:
    from src.storage import MarketFetcher

    fetcher = MarketFetcher()
    count = await fetcher.fetch_and_store_markets()
    print(f"Stored {count} markets")
"""

from __future__ import annotations

__all__ = ["MarketFetcher"]

from src.api import PolymarketClient
from src.exceptions import (
    BotError,
    DatabaseError,
    NetworkError,
    RateLimitError,
    RequestTimeoutError,
)
from src.storage.repositories.market_repo import MarketRepository
from src.utils.logger import OPERATION_EMOJIS, get_logger
from src.utils.retry import retry

logger = get_logger(__name__)


class MarketFetcher:
    """Service for fetching and storing market data.

    Orchestrates the flow of data from Polymarket API to local storage.

    Attributes:
        _client: Polymarket API client
        _repo: Market data repository

    Example:
        >>> fetcher = MarketFetcher()
        >>> count = await fetcher.fetch_and_store_markets()
        >>> print(f"Stored {count} markets")
    """

    def __init__(
        self,
        client: PolymarketClient | None = None,
        repo: MarketRepository | None = None,
    ) -> None:
        """Initialize the market fetcher.

        Args:
            client: PolymarketClient instance (optional, creates new if None)
            repo: MarketRepository instance (optional, creates new if None)
        """
        self._client = client or PolymarketClient()
        self._repo = repo or MarketRepository()

    @retry(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        exceptions=(NetworkError, RateLimitError, RequestTimeoutError),
    )
    async def fetch_and_store_markets(
        self,
        limit: int = 100,
        min_liquidity: float | None = None,
    ) -> int:
        """Fetch markets from Polymarket and store in database.

        Uses Gamma API for filtered, active markets.

        Args:
            limit: Maximum number of markets to fetch (default: 100)
            min_liquidity: Minimum liquidity filter (default: None)

        Returns:
            Number of markets stored

        Raises:
            NetworkError: If API request fails after retries
            RateLimitError: If rate limit is exceeded
            RequestTimeoutError: If request times out
            DatabaseError: If database operation fails
        """
        logger.info(
            f"{OPERATION_EMOJIS['network']} Fetching markets from Polymarket..."
        )

        try:
            # Fetch markets from Gamma API (synchronous call)
            gamma_markets = self._client.get_active_markets(
                limit=limit,
                min_liquidity=min_liquidity,
            )

            # Handle empty results
            if not gamma_markets:
                logger.info(f"{OPERATION_EMOJIS['data']} No active markets found")
                await self._repo.update_last_fetch_time()
                return 0

            # Convert GammaMarket to Market models
            markets = [gm.to_market() for gm in gamma_markets]
            logger.info(
                f"{OPERATION_EMOJIS['network']} Fetched {len(markets)} markets from API"
            )

            # Save to database
            saved_count = await self._repo.save_markets(markets)

            # Update last fetch time
            await self._repo.update_last_fetch_time()

            logger.info(f"{OPERATION_EMOJIS['data']} ✅ Stored {saved_count} markets")

            return saved_count

        except (NetworkError, RateLimitError, RequestTimeoutError):
            # Re-raise network errors after logging
            logger.error(f"{OPERATION_EMOJIS['network']} API error during fetch")
            raise
        except DatabaseError:
            # Re-raise database errors after logging
            logger.error(f"{OPERATION_EMOJIS['data']} Database error during store")
            raise
        except Exception as e:
            # Catch unexpected errors - wrap in BotError (base class)
            # Not NetworkError since this could be a data parsing error, etc.
            logger.error(f"{OPERATION_EMOJIS['data']} Unexpected error: {e}")
            raise BotError(
                message=f"Unexpected error fetching markets: {e}",
                original_exception=e,
                operation="fetch_and_store_markets",
            ) from e
