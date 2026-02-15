"""Polymarket API client wrapper.

This module provides a typed interface to the Polymarket CLOB API and Gamma API,
with retry logic and error handling.

Usage:
    from src.api import PolymarketClient

    client = PolymarketClient()

    # Get all markets (CLOB API, no filtering)
    markets = client.get_markets()

    # Get active markets (Gamma API, with filtering)
    active_markets = client.get_active_markets(limit=10)

    # Get single market
    market = client.get_market("condition-id")

    # Get order book
    order_book = client.get_order_book("token-id")
"""

from __future__ import annotations

__all__ = ["PolymarketClient", "GammaMarket"]

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
from py_clob_client.client import ClobClient  # type: ignore[import-untyped]
from py_clob_client.clob_types import (  # type: ignore[import-untyped]  # noqa: F401 - Reserved for future proxy wallet auth
    ApiCreds,
)

from src.config import settings
from src.exceptions import NetworkError, RateLimitError, RequestTimeoutError
from src.models import Market, MarketCategory
from src.utils.logger import OPERATION_EMOJIS, get_logger
from src.utils.retry import retry


@dataclass
class GammaMarket:
    """Market data from Gamma API with additional fields.

    Gamma API provides more detailed market information including
    24h volume, order book status, and token IDs for trading.
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
        """Convert to base Market model."""
        return Market(
            id=self.condition_id,
            title=self.question,
            category=self._map_category(),
            liquidity=self.liquidity,
            deadline=self.end_date,
        )

    def _map_category(self) -> MarketCategory | None:
        """Map category string to MarketCategory enum."""
        if not self.category:
            return None

        from src.api.polymarket import PolymarketClient

        # Use the client's category mapping
        client = PolymarketClient.__new__(PolymarketClient)
        client._logger = get_logger(__name__)
        return client._map_category(self.category)


class PolymarketClient:
    """Polymarket API client with retry and error handling.

    Provides methods to interact with the Polymarket CLOB API and Gamma API,
    converting responses to typed Market models.

    The client uses two APIs:
    - CLOB API: For trading operations and basic market data
    - Gamma API: For filtered market queries and detailed market info

    Attributes:
        _client: The underlying py-clob-client ClobClient instance
        _host: CLOB API host URL
        _gamma_host: Gamma API host URL
        _chain_id: Blockchain chain ID

    Example:
        >>> client = PolymarketClient()
        >>> markets = client.get_markets()
        >>> print(f"Found {len(markets)} markets")
    """

    # Polymarket CLOB API host
    DEFAULT_HOST = "https://clob.polymarket.com"
    # Gamma API host for market filtering
    GAMMA_HOST = "https://gamma-api.polymarket.com"
    # Polygon mainnet chain ID
    DEFAULT_CHAIN_ID = 137
    # Default HTTP timeout
    DEFAULT_TIMEOUT = 30.0

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        chain_id: int = DEFAULT_CHAIN_ID,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the Polymarket client.

        Args:
            host: CLOB API host URL (default: mainnet)
            chain_id: Chain ID (default: 137 for Polygon)
            timeout: HTTP request timeout in seconds (default: 30)
        """
        self._logger = get_logger(__name__)
        self._host = host
        self._gamma_host = self.GAMMA_HOST
        self._chain_id = chain_id
        self._timeout = timeout
        self._http_client: httpx.Client | None = None

        # Get credentials from settings
        pk = settings.polymarket.pk
        proxy_wallet = settings.polymarket.proxy_wallet

        # Initialize the underlying ClobClient
        # Note: In read-only mode (no credentials), we can still fetch public data
        if pk and proxy_wallet:
            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Initializing Polymarket client "
                f"with proxy wallet: {proxy_wallet[:6]}...{proxy_wallet[-4:]}"
            )
            # TODO: Full proxy wallet authentication requires API credentials
            # (api_key, api_secret, api_passphrase) which need to be generated
            # via Polymarket's credential creation process.
            # For now, use read-only mode with the private key for signing.
            # See: https://docs.polymarket.com/#creating-api-credentials
            self._client = ClobClient(host, key=pk, chain_id=chain_id)
            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Running in authenticated mode "
                "(proxy wallet configured)"
            )
        else:
            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Initializing Polymarket client "
                "(read-only mode)"
            )
            self._client = ClobClient(host, key=None, chain_id=chain_id)

    def _get_http_client(self) -> httpx.Client:
        """Get or create HTTP client for Gamma API."""
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=self._timeout)
        return self._http_client

    def close(self) -> None:
        """Close HTTP client connections."""
        if self._http_client:
            self._http_client.close()
            self._http_client = None

    def __enter__(self) -> "PolymarketClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    # ==================== Gamma API Methods ====================

    def get_active_markets(
        self,
        limit: int = 100,
        min_liquidity: float | None = None,
        min_volume_24h: float | None = None,
        order_by: str = "volume24hr",
        ascending: bool = False,
    ) -> list[GammaMarket]:
        """Get active markets using Gamma API with filtering.

        Gamma API provides filtering capabilities not available in CLOB API.
        Use this method to find markets that are actively trading.

        Args:
            limit: Maximum number of markets to return (default: 100)
            min_liquidity: Minimum liquidity filter (default: None)
            min_volume_24h: Minimum 24h volume filter (default: None)
            order_by: Field to order by (default: "volume24hr")
            ascending: Sort ascending if True (default: False, highest first)

        Returns:
            List of GammaMarket instances with active order books

        Raises:
            NetworkError: If API request fails
            RequestTimeoutError: If request times out

        Example:
            >>> client = PolymarketClient()
            >>> markets = client.get_active_markets(limit=10, min_volume_24h=100000)
            >>> for m in markets:
            ...     print(f"{m.question}: ${m.volume_24h:,.0f}")
        """
        self._logger.info(
            f"{OPERATION_EMOJIS['network']} Fetching active markets from Gamma API"
        )

        params: dict[str, Any] = {
            "limit": limit,
            "active": "true",
            "closed": "false",
            "order": order_by,
            "ascending": str(ascending).lower(),
        }

        if min_liquidity is not None:
            params["liquidity_num_min"] = min_liquidity
        if min_volume_24h is not None:
            params["volume_num_min"] = min_volume_24h

        try:
            client = self._get_http_client()
            response = client.get(
                f"{self._gamma_host}/markets",
                params=params,
            )
            response.raise_for_status()

            markets = [self._parse_gamma_market(m) for m in response.json()]
            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Fetched {len(markets)} active markets"
            )
            return markets

        except httpx.TimeoutException as e:
            raise RequestTimeoutError(
                message="Gamma API request timed out",
                endpoint="get_active_markets",
                timeout_seconds=self._timeout,
                original_exception=e,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                raise RateLimitError(
                    message="Gamma API rate limit exceeded",
                    endpoint="get_active_markets",
                    retry_after=int(retry_after) if retry_after else None,
                    original_exception=e,
                )
            raise NetworkError(
                message=f"Gamma API error: {e.response.status_code}",
                endpoint="get_active_markets",
                status_code=e.response.status_code,
                original_exception=e,
            )
        except httpx.RequestError as e:
            raise NetworkError(
                message="Gamma API request failed",
                endpoint="get_active_markets",
                original_exception=e,
            )

    def _parse_gamma_market(self, data: dict[str, Any]) -> GammaMarket:
        """Parse Gamma API response into GammaMarket.

        Args:
            data: Raw API response data

        Returns:
            GammaMarket instance
        """
        import json

        # Parse token IDs from JSON string
        clob_token_ids: list[str] = []
        token_ids_str = data.get("clobTokenIds", "[]")
        if token_ids_str:
            try:
                clob_token_ids = json.loads(token_ids_str)
            except (json.JSONDecodeError, TypeError):
                clob_token_ids = []

        # Parse end date
        end_date: datetime | None = None
        end_date_str = data.get("endDateIso") or data.get("endDate")
        if end_date_str:
            end_date = self._parse_datetime(end_date_str)

        return GammaMarket(
            condition_id=data.get("conditionId", ""),
            question=data.get("question", ""),
            slug=data.get("slug", ""),
            active=data.get("active", False),
            closed=data.get("closed", False),
            accepting_orders=data.get("acceptingOrders", False),
            enable_order_book=data.get("enableOrderBook", False),
            clob_token_ids=clob_token_ids,
            volume_24h=data.get("volume24hr"),
            liquidity=data.get("liquidityNum"),
            category=data.get("category"),
            end_date=end_date,
        )

    # ==================== CLOB API Methods ====================

    @retry(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        exceptions=(NetworkError, RateLimitError, RequestTimeoutError),
    )
    def get_markets(self, next_cursor: str = "MA==") -> list[Market]:
        """Get list of available markets from CLOB API.

        Note: This method returns all markets without filtering.
        Use get_active_markets() for filtered results.

        Args:
            next_cursor: Pagination cursor (default: "MA==" for first page)

        Returns:
            List of Market models

        Raises:
            NetworkError: If API request fails
            RateLimitError: If rate limit is exceeded
            RequestTimeoutError: If request times out
        """
        self._logger.info(
            f"{OPERATION_EMOJIS['network']} Fetching markets from Polymarket"
        )

        try:
            response = self._client.get_markets(next_cursor=next_cursor)
            markets = self._parse_markets_response(response)
            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Fetched {len(markets)} markets"
            )
            return markets
        except Exception as e:
            raise self._map_exception(e, endpoint="get_markets")

    @retry(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        exceptions=(NetworkError, RateLimitError, RequestTimeoutError),
    )
    def get_market(self, condition_id: str) -> Market | None:
        """Get a single market by condition ID.

        Args:
            condition_id: The market's condition ID

        Returns:
            Market model if found, None otherwise

        Raises:
            NetworkError: If API request fails
            RateLimitError: If rate limit is exceeded
            RequestTimeoutError: If request times out
        """
        self._logger.info(
            f"{OPERATION_EMOJIS['network']} Fetching market: {condition_id[:10]}..."
        )

        try:
            response = self._client.get_market(condition_id)
            if not response:
                self._logger.warning(
                    f"{OPERATION_EMOJIS['network']} Market not found: {condition_id[:10]}..."
                )
                return None

            market = self._parse_market_response(response)
            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Fetched market: {market.title[:50]}..."
            )
            return market
        except Exception as e:
            raise self._map_exception(e, endpoint=f"get_market/{condition_id}")

    @retry(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        exceptions=(NetworkError, RateLimitError, RequestTimeoutError),
    )
    def get_order_book(self, token_id: str) -> dict[str, Any]:
        """Get order book for a specific token.

        Args:
            token_id: The token ID to get order book for

        Returns:
            Order book dictionary with bids and asks

        Raises:
            NetworkError: If API request fails
            RateLimitError: If rate limit is exceeded
            RequestTimeoutError: If request times out
        """
        self._logger.info(
            f"{OPERATION_EMOJIS['network']} Fetching order book for token: {token_id[:10]}..."
        )

        try:
            response = self._client.get_order_book(token_id)
            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Fetched order book with "
                f"{len(response.bids)} bids, {len(response.asks)} asks"
            )
            return self._parse_order_book_response(response)
        except Exception as e:
            raise self._map_exception(e, endpoint=f"get_order_book/{token_id}")

    def _parse_markets_response(
        self, response: dict[str, Any] | list[dict[str, Any]]
    ) -> list[Market]:
        """Parse markets list response into Market models.

        The API returns a paginated response with format:
        {"data": [...], "next_cursor": "...", "limit": N, "count": N}

        Args:
            response: Raw API response (paginated dict or list)

        Returns:
            List of Market models
        """
        # Handle paginated response format
        if isinstance(response, dict) and "data" in response:
            markets_data = response["data"]
        elif isinstance(response, list):
            markets_data = response
        else:
            self._logger.warning(
                f"{OPERATION_EMOJIS['network']} Unexpected response format: {type(response)}"
            )
            return []

        markets: list[Market] = []
        for item in markets_data:
            try:
                market = self._parse_market_response(item)
                if market:
                    markets.append(market)
            except Exception as e:
                self._logger.warning(
                    f"{OPERATION_EMOJIS['network']} Failed to parse market: {e}"
                )
                continue
        return markets

    def _parse_market_response(self, data: dict[str, Any]) -> Market:
        """Parse API response into Market model.

        Args:
            data: Raw API response data

        Returns:
            Market model instance
        """
        # Extract basic fields
        market_id = data.get("condition_id") or data.get("hash", "")
        title = data.get("question", "")

        # Parse category
        category_str = data.get("category")
        category = self._map_category(category_str)

        # Parse prices (Polymarket uses 0-1 range)
        tokens = data.get("tokens", [])
        yes_price: float | None = None
        no_price: float | None = None

        # Try to get prices from tokens
        for token in tokens:
            outcome = token.get("outcome", "").lower()
            price = token.get("price")
            if price is not None:
                price_val = float(price)
                if outcome == "yes":
                    yes_price = price_val
                elif outcome == "no":
                    no_price = price_val

        # Fallback to top-level price fields
        if yes_price is None:
            yes_price = self._safe_float(data.get("yes_price"))
        if no_price is None:
            no_price = self._safe_float(data.get("no_price"))

        # Parse liquidity
        liquidity = self._safe_float(data.get("liquidity"))

        # Parse deadline
        deadline: datetime | None = None
        end_date_str = data.get("end_date_iso") or data.get("end_date")
        if end_date_str:
            deadline = self._parse_datetime(end_date_str)

        return Market(
            id=market_id,
            title=title,
            description=data.get("description"),
            category=category,
            yes_price=yes_price,
            no_price=no_price,
            liquidity=liquidity,
            deadline=deadline,
        )

    def _parse_order_book_response(self, response: Any) -> dict[str, Any]:
        """Parse order book response into dictionary.

        Args:
            response: OrderBookSummary from py-clob-client

        Returns:
            Dictionary with market, asset_id, bids, and asks
        """
        return {
            "market": getattr(response, "market", ""),
            "asset_id": getattr(response, "asset_id", ""),
            "bids": [
                {"price": bid.price, "size": bid.size}
                for bid in getattr(response, "bids", [])
            ],
            "asks": [
                {"price": ask.price, "size": ask.size}
                for ask in getattr(response, "asks", [])
            ],
        }

    def _map_category(self, category: str | None) -> MarketCategory | None:
        """Map API category string to MarketCategory enum.

        Args:
            category: Category string from API

        Returns:
            MarketCategory enum value or None
        """
        if not category:
            return None

        category_lower = category.lower()

        # Map common category names to enum values
        category_mapping: dict[str, MarketCategory] = {
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
            "sports": MarketCategory.BUSINESS,  # Default sports to business
            "entertainment": MarketCategory.BUSINESS,  # Default entertainment to business
        }

        for key, value in category_mapping.items():
            if key in category_lower:
                return value

        return None

    def _parse_datetime(self, date_str: str) -> datetime | None:
        """Parse datetime string from API response.

        Args:
            date_str: Date string in various formats

        Returns:
            Parsed datetime or None
        """
        if not date_str:
            return None

        # Try ISO format first
        try:
            # Handle 'Z' suffix for UTC timezone
            if date_str.endswith("Z"):
                date_str = date_str[:-1] + "+00:00"
            return datetime.fromisoformat(date_str)
        except ValueError:
            pass

        # Try other common formats
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        self._logger.warning(
            f"{OPERATION_EMOJIS['network']} Failed to parse datetime: {date_str}"
        )
        return None

    def _safe_float(self, value: Any) -> float | None:
        """Safely convert value to float.

        Args:
            value: Value to convert

        Returns:
            Float value or None
        """
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _map_exception(
        self, e: Exception, endpoint: str = ""
    ) -> NetworkError | RateLimitError | RequestTimeoutError:
        """Map exception to appropriate custom exception type.

        Args:
            e: Original exception
            endpoint: API endpoint that caused the error

        Returns:
            Appropriate custom exception
        """
        error_message = str(e).lower()

        # Check for timeout
        if "timeout" in error_message or isinstance(e, TimeoutError):
            return RequestTimeoutError(
                message="API request timed out",
                endpoint=endpoint,
                original_exception=e,
            )

        # Check for rate limit (429)
        if "429" in error_message or "rate limit" in error_message:
            # Try to extract retry_after from the exception
            retry_after = None
            if hasattr(e, "response") and hasattr(e.response, "headers"):
                retry_after_str = e.response.headers.get("Retry-After")
                if retry_after_str:
                    try:
                        retry_after = int(retry_after_str)
                    except ValueError:
                        pass
            return RateLimitError(
                message="Rate limit exceeded",
                endpoint=endpoint,
                retry_after=retry_after,
                original_exception=e,
            )

        # Default to network error
        return NetworkError(
            message="API request failed",
            endpoint=endpoint,
            original_exception=e,
        )
