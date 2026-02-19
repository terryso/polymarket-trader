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

__all__ = ["PolymarketClient", "GammaMarket", "WalletBalance", "OrderHistoryItem", "OrderHistoryResult", "BalanceItem", "BalanceResult"]

from dataclasses import dataclass, field
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
class WalletBalance:
    """Wallet balance information from Polymarket.

    Contains USDC balance and metadata for the connected wallet.

    Attributes:
        usdc_balance: USDC balance in USD
        last_updated: Timestamp when balance was fetched
        error: Error message if balance fetch failed
    """

    usdc_balance: float | None = None
    last_updated: datetime | None = None
    error: str | None = None

    @property
    def is_success(self) -> bool:
        """Check if balance fetch was successful."""
        return self.error is None and self.usdc_balance is not None


@dataclass
class BalanceItem:
    """Position balance item from Polymarket.

    Represents a single position balance from the user's wallet.

    Attributes:
        condition_id: Market condition ID
        outcome: Outcome type (YES/NO)
        shares: Number of shares held
        asset_id: Token/asset ID
        market_title: Optional market title for display
    """

    condition_id: str
    outcome: str  # YES/NO
    shares: float
    asset_id: str | None = None
    market_title: str | None = None


@dataclass
class BalanceResult:
    """Result of fetching wallet balances.

    Attributes:
        balances: List of balance items
        error: Error message if fetch failed
    """

    balances: list[BalanceItem] = field(default_factory=list)
    error: str | None = None

    @property
    def is_success(self) -> bool:
        """Check if balance fetch was successful."""
        return self.error is None


@dataclass
class OrderHistoryItem:
    """Order history item from Polymarket.

    Represents a single order from the user's trading history.

    Attributes:
        order_id: Unique order identifier
        market_id: Market condition ID
        asset_id: Token ID for the outcome
        side: Order side (BUY/SELL)
        outcome: Outcome type (YES/NO)
        price: Order price (0-1)
        size: Order size in shares
        original_size: Original order size before fills
        status: Order status (LIVE/MATCHED/CANCELED)
        created_at: Order creation timestamp
        updated_at: Last update timestamp
    """

    order_id: str
    market_id: str | None = None
    asset_id: str | None = None
    side: str = "BUY"
    outcome: str = "YES"
    price: float = 0.0
    size: float = 0.0
    original_size: float = 0.0
    status: str = "LIVE"
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class OrderHistoryResult:
    """Result of fetching order history.

    Attributes:
        orders: List of order history items
        next_cursor: Cursor for pagination (None if no more pages)
        has_more: Whether there are more orders to fetch
        error: Error message if fetch failed
    """

    orders: list[OrderHistoryItem] = field(default_factory=list)
    next_cursor: str | None = None
    has_more: bool = False
    error: str | None = None

    @property
    def is_success(self) -> bool:
        """Check if order history fetch was successful."""
        return self.error is None


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
    event_slug: str | None = None  # Event slug for URL (from events[0].slug)

    def to_market(self) -> Market:
        """Convert to base Market model."""
        return Market(
            id=self.condition_id,
            title=self.question,
            slug=self.event_slug or self.slug,  # Use event_slug for URL, fallback to slug
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
        self._auth_level = 0  # Track authentication level (0, 1, or 2)

        # Get credentials from settings
        pk = settings.polymarket.pk
        proxy_wallet = settings.polymarket.proxy_wallet
        api_key = settings.polymarket.api_key
        api_secret = settings.polymarket.api_secret
        api_passphrase = settings.polymarket.api_passphrase

        # Initialize the underlying ClobClient with appropriate auth level
        # Level 2: Full auth with API credentials (can access order history)
        # Level 1: Private key only (can sign orders)
        # Level 0: Read-only mode
        if pk and proxy_wallet:
            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Initializing Polymarket client "
                f"with Level 2 auth (proxy wallet: {proxy_wallet[:6]}...{proxy_wallet[-4:]})"
            )
            # For proxy wallet trading, need signature_type=1 and funder
            self._client = ClobClient(
                host,
                key=pk,
                chain_id=chain_id,
                signature_type=1,  # Email/Magic wallet signatures
                funder=proxy_wallet,  # Address that holds funds
            )
            self._auth_level = 2
            self._api_creds_set = False  # Will be set lazily when needed
            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Running with full authentication "
                "(Level 2 - can access order history)"
            )
        elif pk:
            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Initializing Polymarket client "
                f"with Level 1 auth (proxy wallet: {proxy_wallet[:6]}...{proxy_wallet[-4:]})"
            )
            self._client = ClobClient(host, key=pk, chain_id=chain_id)
            self._auth_level = 1
            self._api_creds_set = False
            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Running with basic authentication "
                "(Level 1 - order history requires API credentials)"
            )
        else:
            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Initializing Polymarket client "
                "(read-only mode)"
            )
            self._client = ClobClient(host, key=None, chain_id=chain_id)
            self._auth_level = 0
            self._api_creds_set = False

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

        # Parse event slug from events array (for correct Polymarket URL)
        event_slug: str | None = None
        events = data.get("events", [])
        if events and len(events) > 0:
            event_slug = events[0].get("slug") or events[0].get("ticker")

        return GammaMarket(
            condition_id=data.get("conditionId", ""),
            question=data.get("question", ""),
            slug=data.get("slug", ""),
            event_slug=event_slug,
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

    def get_wallet_balance(
        self, wallet_address: str | None = None
    ) -> WalletBalance:
        """Get USDC balance for a wallet from Polygon network.

        Queries the USDC contract on Polygon directly via RPC to get
        the real wallet balance.

        Args:
            wallet_address: Wallet address to check (default: proxy_wallet from settings)

        Returns:
            WalletBalance with USDC balance or error information

        Example:
            >>> client = PolymarketClient()
            >>> balance = client.get_wallet_balance()
            >>> if balance.is_success:
            ...     print(f"USDC Balance: ${balance.usdc_balance:.2f}")
            >>> else:
            ...     print(f"Error: {balance.error}")
        """
        # Use proxy_wallet from settings if not specified
        wallet = wallet_address or settings.polymarket.proxy_wallet

        if not wallet:
            return WalletBalance(
                usdc_balance=None,
                error="No wallet address configured",
            )

        self._logger.info(
            f"{OPERATION_EMOJIS['network']} Fetching wallet balance for: "
            f"{wallet[:6]}...{wallet[-4:]}"
        )

        try:
            # USDC contract address on Polygon (Polymarket uses this)
            USDC_CONTRACT = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
            # List of reliable Polygon RPC endpoints (ordered by preference)
            POLYGON_RPCS = [
                "https://rpc.ankr.com/polygon",  # Ankr public RPC
                "https://polygon-mainnet.g.alchemy.com/v2/demo",  # Alchemy demo
                "https://polygon-bor-rpc.publicnode.com",  # PublicNode
                "https://polygon-rpc.com",  # Official (may require auth)
            ]

            # balanceOf(address) function selector
            # keccak256("balanceOf(address)") first 4 bytes = 0x70a08231
            data = "0x70a08231" + wallet[2:].lower().zfill(64)

            client = self._get_http_client()

            # Try each RPC endpoint until one works
            last_error = None
            for rpc_url in POLYGON_RPCS:
                try:
                    response = client.post(
                        rpc_url,
                        json={
                            "jsonrpc": "2.0",
                            "method": "eth_call",
                            "params": [{"to": USDC_CONTRACT, "data": data}, "latest"],
                            "id": 1,
                        },
                        timeout=10.0,
                    )
                    response.raise_for_status()

                    result = response.json()
                    if "result" not in result:
                        last_error = f"RPC error from {rpc_url}: {result.get('error', 'Unknown error')}"
                        continue

                    # Parse balance from hex
                    balance_hex = result["result"]
                    balance_wei = int(balance_hex, 16)
                    usdc_balance = balance_wei / 1_000_000  # USDC has 6 decimals

                    self._logger.info(
                        f"{OPERATION_EMOJIS['network']} Wallet balance: ${usdc_balance:.2f} USDC (via {rpc_url})"
                    )

                    return WalletBalance(
                        usdc_balance=usdc_balance,
                        last_updated=datetime.now(),
                        error=None,
                    )
                except Exception as rpc_error:
                    last_error = str(rpc_error)
                    self._logger.debug(
                        f"{OPERATION_EMOJIS['network']} RPC {rpc_url} failed: {rpc_error}"
                    )
                    continue

            # All RPCs failed
            return WalletBalance(
                usdc_balance=None,
                last_updated=datetime.now(),
                error=f"All Polygon RPCs failed. Last error: {last_error}",
            )

        except Exception as e:
            error_msg = str(e)
            self._logger.warning(
                f"{OPERATION_EMOJIS['network']} Failed to fetch wallet balance: {error_msg}"
            )
            return WalletBalance(
                usdc_balance=None,
                last_updated=datetime.now(),
                error=error_msg,
            )

    def get_order_history(
        self,
        market_id: str | None = None,
        asset_id: str | None = None,
        cursor: str | None = None,
    ) -> OrderHistoryResult:
        """Get order history from Polymarket.

        Fetches the user's order history. Requires Level 2 authentication
        (API credentials must be configured).

        Args:
            market_id: Filter by market condition ID (optional)
            asset_id: Filter by asset/token ID (optional)
            cursor: Pagination cursor for fetching next page (optional)

        Returns:
            OrderHistoryResult with list of orders and pagination info

        Example:
            >>> client = PolymarketClient()
            >>> result = client.get_order_history()
            >>> if result.is_success:
            ...     for order in result.orders:
            ...         print(f"{order.side} {order.size} @ {order.price}")
            >>> else:
            ...     print(f"Error: {result.error}")
        """
        # Check if we have Level 2 authentication (requires pk + proxy_wallet)
        if self._auth_level < 2:
            return OrderHistoryResult(
                orders=[],
                error="Order history requires private key and proxy wallet. "
                "Please configure PK and YOUR_PROXY_WALLET in your .env file.",
            )

        # Lazily set API credentials (derived from private key)
        if not self._api_creds_set:
            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Deriving API credentials from private key"
            )
            derived_creds = self._client.create_or_derive_api_creds()
            self._client.set_api_creds(derived_creds)
            self._api_creds_set = True
            self._logger.info(
                f"{OPERATION_EMOJIS['network']} API credentials set "
                f"(derived key: {derived_creds.api_key[:8]}...)"
            )

        self._logger.info(
            f"{OPERATION_EMOJIS['network']} Fetching trade history"
            + (f" for market: {market_id[:10]}..." if market_id else "")
        )

        try:
            # Use get_trades() to fetch actual trade history (not orders)
            # get_orders() returns unfilled/open orders, get_trades() returns executed trades
            self._logger.debug(
                f"{OPERATION_EMOJIS['network']} Calling get_trades()"
            )
            response = self._client.get_trades()
            self._logger.debug(
                f"{OPERATION_EMOJIS['network']} get_trades response type: {type(response)}, count: {len(response) if isinstance(response, list) else 0}"
            )

            # Parse response
            orders: list[OrderHistoryItem] = []

            # Response is a list of trade objects
            if isinstance(response, list):
                trades_data = response
            else:
                trades_data = []

            for trade_data in trades_data:
                try:
                    # Skip if market filter doesn't match
                    if market_id and trade_data.get("market") != market_id:
                        continue
                    if asset_id and trade_data.get("asset_id") != asset_id:
                        continue

                    # Parse trade data - note the different field names from orders
                    # Trade has: id, market, asset_id, side, size, price, status, match_time, outcome
                    trade = OrderHistoryItem(
                        order_id=trade_data.get("id", ""),
                        market_id=trade_data.get("market", ""),
                        asset_id=trade_data.get("asset_id", ""),
                        side=trade_data.get("side", "BUY").upper(),
                        outcome=trade_data.get("outcome", "YES").upper(),
                        price=float(trade_data.get("price", 0)),
                        size=float(trade_data.get("size", 0)),
                        original_size=float(trade_data.get("size", 0)),  # Trades don't have original_size
                        status=trade_data.get("status", "CONFIRMED"),
                        created_at=self._parse_datetime(
                            trade_data.get("match_time")  # Trades use match_time
                        ),
                        updated_at=self._parse_datetime(
                            trade_data.get("last_update")
                        ),
                    )
                    orders.append(trade)
                except Exception as e:
                    self._logger.warning(
                        f"{OPERATION_EMOJIS['network']} Failed to parse trade: {e}"
                    )
                    continue

            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Fetched {len(orders)} trades"
            )

            # get_trades() doesn't support pagination, so no has_more
            return OrderHistoryResult(
                orders=orders,
                next_cursor=None,
                has_more=False,
                error=None,
            )

        except Exception as e:
            import traceback
            error_msg = str(e)
            self._logger.warning(
                f"{OPERATION_EMOJIS['network']} Failed to fetch order history: {error_msg}"
            )
            self._logger.debug(
                f"{OPERATION_EMOJIS['network']} Exception traceback:\n{traceback.format_exc()}"
            )
            return OrderHistoryResult(
                orders=[],
                error=error_msg,
            )

    def get_balances(self) -> BalanceResult:
        """Get wallet position balances from Polymarket.

        Fetches the user's current position balances by:
        1. Getting asset IDs from trade history via get_trades()
        2. Querying on-chain ERC-1155 balances using web3.py
        3. Returning only non-zero positions

        Requires Level 2 authentication (API credentials must be configured).

        Story 5.7: 同步实际持仓

        Returns:
            BalanceResult with list of balance items

        Example:
            >>> client = PolymarketClient()
            >>> result = client.get_balances()
            >>> if result.is_success:
            ...     for balance in result.balances:
            ...         print(f"{balance.outcome}: {balance.shares} shares")
            >>> else:
            ...     print(f"Error: {result.error}")
        """
        # Check if we have Level 2 authentication (requires pk + proxy_wallet)
        if self._auth_level < 2:
            return BalanceResult(
                balances=[],
                error="Position balances require private key and proxy wallet. "
                "Please configure PK and YOUR_PROXY_WALLET in your .env file.",
            )

        # Lazily set API credentials (derived from private key)
        if not self._api_creds_set:
            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Deriving API credentials from private key"
            )
            derived_creds = self._client.create_or_derive_api_creds()
            self._client.set_api_creds(derived_creds)
            self._api_creds_set = True
            self._logger.info(
                f"{OPERATION_EMOJIS['network']} API credentials set "
                f"(derived key: {derived_creds.api_key[:8]}...)"
            )

        self._logger.info(
            f"{OPERATION_EMOJIS['network']} Fetching wallet position balances"
        )

        try:
            # Step 1: Get asset IDs from trade history
            # Note: get_trades() may return incomplete data, but we only need
            # the asset IDs to query on-chain balances (the source of truth)
            trades_response = self._client.get_trades()

            if not trades_response:
                self._logger.info(
                    f"{OPERATION_EMOJIS['network']} No trades found, returning empty balances"
                )
                return BalanceResult(balances=[], error=None)

            # Build asset info map from trades
            asset_info_map: dict[str, dict] = {}
            for trade in trades_response:
                asset_id = str(trade.get("asset_id", ""))
                if asset_id and asset_id not in asset_info_map:
                    asset_info_map[asset_id] = {
                        "outcome": str(trade.get("outcome", "YES")).upper(),
                        "market_id": trade.get("market", ""),
                    }

            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Found {len(asset_info_map)} unique assets from trade history"
            )

            # Step 2: Query on-chain ERC-1155 balances for each asset
            wallet = settings.polymarket.proxy_wallet
            balances: list[BalanceItem] = []

            for asset_id, info in asset_info_map.items():
                try:
                    # Query on-chain balance (this is the source of truth)
                    on_chain_balance = self._get_erc1155_balance(wallet, asset_id)

                    # Only include non-zero positions
                    if on_chain_balance > 0.0001:
                        balance = BalanceItem(
                            condition_id=info["market_id"],
                            outcome=info["outcome"],
                            shares=on_chain_balance,
                            asset_id=asset_id,
                            market_title=None,
                        )
                        balances.append(balance)
                        self._logger.debug(
                            f"{OPERATION_EMOJIS['network']} Position: {info['outcome']} "
                            f"{on_chain_balance:.6f} shares (asset: {asset_id[:10]}...)"
                        )
                    else:
                        self._logger.debug(
                            f"{OPERATION_EMOJIS['network']} Zero balance for asset: {asset_id[:10]}..."
                        )

                except Exception as e:
                    self._logger.warning(
                        f"{OPERATION_EMOJIS['network']} Failed to get balance for asset "
                        f"{asset_id[:10]}...: {e}"
                    )
                    continue

            self._logger.info(
                f"{OPERATION_EMOJIS['network']} Found {len(balances)} non-zero positions"
            )

            return BalanceResult(balances=balances, error=None)

        except Exception as e:
            error_msg = str(e)
            self._logger.warning(
                f"{OPERATION_EMOJIS['network']} Failed to fetch position balances: {error_msg}"
            )
            return BalanceResult(
                balances=[],
                error=error_msg,
            )

    def _get_erc1155_balance(self, wallet: str, asset_id: str) -> float:
        """Query ERC-1155 token balance from Polygon chain.

        Uses the Polymarket CTF (Conditional Token Framework) contract
        to get the actual on-chain balance for a given asset/token.

        Args:
            wallet: Wallet address to query
            asset_id: Token/asset ID (as string, will be converted to int)

        Returns:
            Balance as float (shares with 6 decimal precision)

        Raises:
            Exception: If RPC call fails after all retries
        """
        from web3 import Web3

        # Polymarket CTF contract on Polygon
        CTF_CONTRACT = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"

        # List of reliable Polygon RPC endpoints (ordered by preference)
        POLYGON_RPCS = [
            "https://rpc.ankr.com/polygon",  # Ankr public RPC
            "https://polygon-mainnet.g.alchemy.com/v2/demo",  # Alchemy demo
            "https://polygon-bor-rpc.publicnode.com",  # PublicNode
            "https://polygon-rpc.com",  # Official (may require auth)
        ]

        # ERC-1155 balanceOf(address, uint256) ABI
        ctf_abi = """[{
            "inputs": [
                {"internalType": "address", "name": "owner", "type": "address"},
                {"internalType": "uint256", "name": "id", "type": "uint256"}
            ],
            "name": "balanceOf",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        }]"""

        # Try each RPC endpoint until one works
        last_error = None
        for rpc_url in POLYGON_RPCS:
            try:
                w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
                contract = w3.eth.contract(
                    address=Web3.to_checksum_address(CTF_CONTRACT),
                    abi=ctf_abi,
                )

                # Query balance
                balance_wei = contract.functions.balanceOf(
                    Web3.to_checksum_address(wallet),
                    int(asset_id),
                ).call()

                # Convert from wei to shares (6 decimals)
                return balance_wei / 1_000_000

            except Exception as e:
                last_error = e
                self._logger.debug(
                    f"{OPERATION_EMOJIS['network']} RPC {rpc_url} failed: {e}"
                )
                continue

        # All RPCs failed
        raise Exception(
            f"All Polygon RPCs failed for ERC-1155 balance query. Last error: {last_error}"
        )

    def _parse_outcome_from_asset_id(self, asset_id: str) -> str:
        """Parse outcome type from asset ID.

        The asset ID encodes whether it's YES or NO outcome.
        This is a simplified implementation - actual parsing may vary.
        """
        # Polymarket token IDs: last character often indicates outcome
        # This is a heuristic and may need adjustment
        if not asset_id:
            return "UNKNOWN"
        return "YES"  # Default, actual implementation would need token metadata

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

    def _parse_datetime(self, date_str: str | int | None) -> datetime | None:
        """Parse datetime string from API response.

        Args:
            date_str: Date string in various formats (ISO, Unix timestamp, etc.)

        Returns:
            Parsed datetime with UTC timezone or None
        """
        from datetime import timezone

        if not date_str:
            return None

        # Handle Unix timestamp (integer or string of digits)
        if isinstance(date_str, int) or (isinstance(date_str, str) and date_str.isdigit()):
            try:
                timestamp = int(date_str)
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            except (ValueError, OSError):
                pass

        # Try ISO format first
        try:
            # Handle 'Z' suffix for UTC timezone
            if isinstance(date_str, str):
                if date_str.endswith("Z"):
                    date_str = date_str[:-1] + "+00:00"
                dt = datetime.fromisoformat(date_str)
                # Ensure timezone-aware
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
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
                dt = datetime.strptime(date_str, fmt)
                # Assume UTC for naive datetimes
                return dt.replace(tzinfo=timezone.utc)
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
