"""Tests for market API routes.

This module contains tests for the market data API endpoints,
including list and detail endpoints with pagination and filtering.
"""

from datetime import datetime
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.models.market import Market, MarketCategory


@pytest.fixture
def sample_markets() -> list[Market]:
    """Create sample markets for testing."""
    return [
        Market(
            id="market-001",
            title="Will Bitcoin reach $100k by 2026?",
            description="Bitcoin price prediction market",
            category=MarketCategory.CRYPTO,
            yes_price=0.45,
            no_price=0.55,
            liquidity=50000.0,
            deadline=datetime(2026, 12, 31, 23, 59, 59),
            resolution_status=None,
            resolution_outcome=None,
            created_at=datetime(2026, 1, 1, 10, 0, 0),
            updated_at=datetime(2026, 2, 1, 8, 0, 0),
        ),
        Market(
            id="market-002",
            title="Will candidate X win the election?",
            description="Political election prediction market",
            category=MarketCategory.POLITICS,
            yes_price=0.65,
            no_price=0.35,
            liquidity=100000.0,
            deadline=datetime(2026, 11, 3, 0, 0, 0),
            resolution_status=None,
            resolution_outcome=None,
            created_at=datetime(2026, 1, 2, 10, 0, 0),
            updated_at=datetime(2026, 2, 2, 8, 0, 0),
        ),
        Market(
            id="market-003",
            title="Will company Y acquire company Z?",
            description="Business merger prediction market",
            category=MarketCategory.BUSINESS,
            yes_price=0.30,
            no_price=0.70,
            liquidity=25000.0,
            deadline=datetime(2026, 6, 30, 0, 0, 0),
            resolution_status="RESOLVED",
            resolution_outcome="NO",
            created_at=datetime(2026, 1, 3, 10, 0, 0),
            updated_at=datetime(2026, 7, 1, 8, 0, 0),
        ),
    ]


@pytest.fixture
def mock_market_repo() -> MagicMock:
    """Create a mock MarketRepository for testing."""
    repo = MagicMock()
    repo.get_all_markets = AsyncMock(return_value=[])
    repo.get_active_markets = AsyncMock(return_value=[])
    repo.get_resolved_markets = AsyncMock(return_value=[])
    repo.get_market = AsyncMock(return_value=None)
    repo.get_markets_by_category = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def client(mock_market_repo: MagicMock) -> Generator[TestClient, None, None]:
    """Create test client with mocked dependencies."""
    # Patch init_db and close_db to avoid database operations
    with patch("src.dashboard.app.init_db", new_callable=AsyncMock):
        with patch("src.dashboard.app.close_db", new_callable=AsyncMock):
            # Create a mock repository factory function
            def mock_get_market_repository() -> MagicMock:
                return mock_market_repo

            # Import app after patches
            from src.dashboard.app import app
            from src.dashboard.routes.markets import get_market_repository

            # Override the dependency
            app.dependency_overrides[get_market_repository] = mock_get_market_repository

            with TestClient(app, raise_server_exceptions=False) as c:
                yield c

            # Clean up
            app.dependency_overrides.clear()


class TestListMarkets:
    """Tests for the market list endpoint."""

    def test_list_markets_returns_200(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
    ) -> None:
        """Test list markets returns 200."""
        mock_market_repo.get_all_markets.return_value = []

        response = client.get("/api/markets")

        assert response.status_code == 200

    def test_list_markets_returns_success(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
    ) -> None:
        """Test list markets returns success status."""
        mock_market_repo.get_all_markets.return_value = []

        response = client.get("/api/markets")
        data = response.json()

        assert data["success"] is True

    def test_list_markets_returns_data_list(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
    ) -> None:
        """Test list markets returns data as list."""
        mock_market_repo.get_all_markets.return_value = []

        response = client.get("/api/markets")
        data = response.json()

        assert "data" in data
        assert isinstance(data["data"], list)

    def test_list_markets_returns_meta(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
    ) -> None:
        """Test list markets returns pagination metadata."""
        mock_market_repo.get_all_markets.return_value = []

        response = client.get("/api/markets")
        data = response.json()

        assert "meta" in data
        assert "total" in data["meta"]
        assert "page" in data["meta"]
        assert "per_page" in data["meta"]

    def test_list_markets_pagination(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test list markets pagination."""
        mock_market_repo.get_all_markets.return_value = sample_markets

        response = client.get("/api/markets?page=1&per_page=2")
        data = response.json()

        assert data["meta"]["page"] == 1
        assert data["meta"]["per_page"] == 2
        assert data["meta"]["total"] == 3
        assert len(data["data"]) == 2

    def test_list_markets_second_page(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test list markets second page."""
        mock_market_repo.get_all_markets.return_value = sample_markets

        response = client.get("/api/markets?page=2&per_page=2")
        data = response.json()

        assert data["meta"]["page"] == 2
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == "market-003"

    def test_list_markets_status_filter_active(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test list markets with status=active filter."""
        active_markets = [m for m in sample_markets if m.resolution_status is None]
        mock_market_repo.get_active_markets.return_value = active_markets

        response = client.get("/api/markets?status=active")
        data = response.json()

        mock_market_repo.get_active_markets.assert_called_once()
        assert data["meta"]["total"] == 2

    def test_list_markets_status_filter_resolved(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test list markets with status=resolved filter."""
        resolved_markets = [
            m for m in sample_markets if m.resolution_status == "RESOLVED"
        ]
        mock_market_repo.get_resolved_markets.return_value = resolved_markets

        response = client.get("/api/markets?status=resolved")
        data = response.json()

        mock_market_repo.get_resolved_markets.assert_called_once()
        assert data["meta"]["total"] == 1

    def test_list_markets_status_filter_all(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test list markets with status=all filter."""
        mock_market_repo.get_all_markets.return_value = sample_markets

        response = client.get("/api/markets?status=all")
        data = response.json()

        mock_market_repo.get_all_markets.assert_called_once()
        assert data["meta"]["total"] == 3

    def test_list_markets_category_filter(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test list markets with category filter."""
        # When status=all and category is specified, get_markets_by_category is called
        politics_markets = [
            m for m in sample_markets if m.category == MarketCategory.POLITICS
        ]
        mock_market_repo.get_markets_by_category.return_value = politics_markets

        response = client.get("/api/markets?category=politics")
        data = response.json()

        mock_market_repo.get_markets_by_category.assert_called_once()
        assert data["meta"]["total"] == 1
        assert data["data"][0]["category"] == "politics"

    def test_list_markets_category_filter_crypto(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test list markets with crypto category filter."""
        # When status=all and category is specified, get_markets_by_category is called
        crypto_markets = [
            m for m in sample_markets if m.category == MarketCategory.CRYPTO
        ]
        mock_market_repo.get_markets_by_category.return_value = crypto_markets

        response = client.get("/api/markets?category=crypto")
        data = response.json()

        mock_market_repo.get_markets_by_category.assert_called_once()
        assert data["meta"]["total"] == 1
        assert data["data"][0]["id"] == "market-001"

    def test_list_markets_invalid_category(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test list markets with invalid category returns 422 validation error."""
        response = client.get("/api/markets?category=invalid_category")

        # FastAPI validates the enum, so invalid category returns 422
        assert response.status_code == 422

    def test_list_markets_combined_filters(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test list markets with combined filters."""
        active_markets = [m for m in sample_markets if m.resolution_status is None]
        mock_market_repo.get_active_markets.return_value = active_markets

        response = client.get("/api/markets?status=active&category=politics")
        data = response.json()

        assert data["meta"]["total"] == 1
        assert data["data"][0]["category"] == "politics"

    def test_list_markets_default_pagination(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
    ) -> None:
        """Test list markets uses default pagination values."""
        mock_market_repo.get_all_markets.return_value = []

        response = client.get("/api/markets")
        data = response.json()

        assert data["meta"]["page"] == 1
        assert data["meta"]["per_page"] == 20

    def test_list_markets_market_item_fields(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test list markets returns correct fields."""
        mock_market_repo.get_all_markets.return_value = [sample_markets[0]]

        response = client.get("/api/markets")
        data = response.json()

        item = data["data"][0]
        assert "id" in item
        assert "title" in item
        assert "category" in item
        assert "yes_price" in item
        assert "no_price" in item
        assert "liquidity" in item
        assert "deadline" in item
        assert "resolution_status" in item


class TestGetMarket:
    """Tests for the market detail endpoint."""

    def test_get_market_returns_200(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test get market returns 200."""
        mock_market_repo.get_market.return_value = sample_markets[0]

        response = client.get("/api/markets/market-001")

        assert response.status_code == 200

    def test_get_market_returns_success(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test get market returns success status."""
        mock_market_repo.get_market.return_value = sample_markets[0]

        response = client.get("/api/markets/market-001")
        data = response.json()

        assert data["success"] is True

    def test_get_market_returns_data(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test get market returns market data."""
        mock_market_repo.get_market.return_value = sample_markets[0]

        response = client.get("/api/markets/market-001")
        data = response.json()

        assert "data" in data
        assert data["data"]["id"] == "market-001"
        assert data["data"]["title"] == "Will Bitcoin reach $100k by 2026?"

    def test_get_market_all_fields(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test get market returns all market fields."""
        mock_market_repo.get_market.return_value = sample_markets[0]

        response = client.get("/api/markets/market-001")
        data = response.json()

        item = data["data"]
        assert item["id"] == "market-001"
        assert item["title"] == "Will Bitcoin reach $100k by 2026?"
        assert item["description"] == "Bitcoin price prediction market"
        assert item["category"] == "crypto"
        assert item["yes_price"] == 0.45
        assert item["no_price"] == 0.55
        assert item["liquidity"] == 50000.0
        assert "deadline" in item
        assert item["resolution_status"] is None
        assert item["resolution_outcome"] is None
        assert "created_at" in item
        assert "updated_at" in item

    def test_get_market_404(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
    ) -> None:
        """Test get market returns 404 for non-existent market."""
        mock_market_repo.get_market.return_value = None

        response = client.get("/api/markets/nonexistent-id")

        assert response.status_code == 404

    def test_get_market_404_error_format(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
    ) -> None:
        """Test get market 404 has proper error format."""
        mock_market_repo.get_market.return_value = None

        response = client.get("/api/markets/nonexistent-id")
        data = response.json()

        # The error is in the detail field due to HTTPException
        assert "detail" in data
        assert data["detail"]["success"] is False
        assert data["detail"]["error"]["code"] == "NOT_FOUND"
        assert "Market not found" in data["detail"]["error"]["message"]

    def test_get_market_resolved(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test get market returns resolved market correctly."""
        mock_market_repo.get_market.return_value = sample_markets[2]  # Resolved market

        response = client.get("/api/markets/market-003")
        data = response.json()

        assert data["data"]["resolution_status"] == "RESOLVED"
        assert data["data"]["resolution_outcome"] == "NO"

    def test_get_market_calls_repository(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test get market calls repository with correct ID."""
        mock_market_repo.get_market.return_value = sample_markets[0]

        client.get("/api/markets/market-001")

        mock_market_repo.get_market.assert_called_once_with("market-001")


class TestMarketResponseFormat:
    """Tests for market response format compliance."""

    def test_list_response_format(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test list response follows API specification."""
        mock_market_repo.get_all_markets.return_value = sample_markets

        response = client.get("/api/markets")
        data = response.json()

        # Top-level fields
        assert data["success"] is True
        assert isinstance(data["data"], list)
        assert isinstance(data["meta"], dict)

        # Meta fields
        assert isinstance(data["meta"]["total"], int)
        assert isinstance(data["meta"]["page"], int)
        assert isinstance(data["meta"]["per_page"], int)

    def test_detail_response_format(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test detail response follows API specification."""
        mock_market_repo.get_market.return_value = sample_markets[0]

        response = client.get("/api/markets/market-001")
        data = response.json()

        # Top-level fields
        assert data["success"] is True
        assert isinstance(data["data"], dict)
        assert data["error"] is None

    def test_datetime_serialization(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test datetime fields are serialized to ISO 8601."""
        mock_market_repo.get_market.return_value = sample_markets[0]

        response = client.get("/api/markets/market-001")
        data = response.json()

        # Check deadline is ISO format string
        deadline = data["data"]["deadline"]
        if deadline:
            # Should be parseable as ISO format
            datetime.fromisoformat(deadline.replace("Z", "+00:00"))

    def test_category_enum_values(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
        sample_markets: list[Market],
    ) -> None:
        """Test category values are lowercase strings."""
        mock_market_repo.get_all_markets.return_value = sample_markets

        response = client.get("/api/markets")
        data = response.json()

        for item in data["data"]:
            if item["category"]:
                assert item["category"] == item["category"].lower()
                assert item["category"] in [
                    "politics",
                    "business",
                    "technology",
                    "economics",
                    "crypto",
                ]


class TestValidationErrors:
    """Tests for input validation."""

    def test_list_markets_invalid_page(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
    ) -> None:
        """Test list markets rejects invalid page number."""
        response = client.get("/api/markets?page=0")

        assert response.status_code == 422

    def test_list_markets_invalid_per_page(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
    ) -> None:
        """Test list markets rejects per_page > 100."""
        response = client.get("/api/markets?per_page=101")

        assert response.status_code == 422

    def test_list_markets_negative_page(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
    ) -> None:
        """Test list markets rejects negative page."""
        response = client.get("/api/markets?page=-1")

        assert response.status_code == 422

    def test_list_markets_per_page_minimum(
        self,
        client: TestClient,
        mock_market_repo: MagicMock,
    ) -> None:
        """Test list markets rejects per_page < 1."""
        response = client.get("/api/markets?per_page=0")

        assert response.status_code == 422


class TestMarketResponseModels:
    """Tests for Market response model classes."""

    def test_market_list_item_model(self) -> None:
        """Test MarketListItem model creation."""
        from src.models.market_response import MarketListItem

        item = MarketListItem(
            id="test-id",
            title="Test Market",
            category=MarketCategory.POLITICS,
            yes_price=0.6,
            no_price=0.4,
            liquidity=10000.0,
        )

        assert item.id == "test-id"
        assert item.title == "Test Market"
        assert item.category == MarketCategory.POLITICS
        assert item.yes_price == 0.6

    def test_market_response_model(self) -> None:
        """Test MarketResponse model creation."""
        from src.models.market_response import MarketResponse

        response = MarketResponse(
            id="test-id",
            title="Test Market",
            description="Test description",
            category=MarketCategory.CRYPTO,
            yes_price=0.5,
            no_price=0.5,
            liquidity=5000.0,
            resolution_status=None,
            resolution_outcome=None,
        )

        assert response.id == "test-id"
        assert response.description == "Test description"

    def test_market_list_query_params_defaults(self) -> None:
        """Test MarketListQueryParams default values."""
        from src.models.market_response import MarketListQueryParams

        params = MarketListQueryParams()

        assert params.page == 1
        assert params.per_page == 20
        assert params.status == "all"
        assert params.category is None

    def test_market_list_query_params_validation(self) -> None:
        """Test MarketListQueryParams validation."""
        from pydantic import ValidationError

        from src.models.market_response import MarketListQueryParams

        # Valid params
        params = MarketListQueryParams(page=2, per_page=50)
        assert params.page == 2
        assert params.per_page == 50

        # Invalid per_page > 100
        with pytest.raises(ValidationError):
            MarketListQueryParams(per_page=101)

        # Invalid page < 1
        with pytest.raises(ValidationError):
            MarketListQueryParams(page=0)

    def test_market_list_item_datetime_serialization(self) -> None:
        """Test MarketListItem datetime serialization."""
        from src.models.market_response import MarketListItem

        item = MarketListItem(
            id="test-id",
            title="Test Market",
            deadline=datetime(2026, 12, 31, 23, 59, 59),
        )

        data = item.model_dump()
        assert isinstance(data["deadline"], str)
        assert "2026-12-31" in data["deadline"]

    def test_market_response_datetime_serialization(self) -> None:
        """Test MarketResponse datetime serialization."""
        from src.models.market_response import MarketResponse

        response = MarketResponse(
            id="test-id",
            title="Test Market",
            created_at=datetime(2026, 1, 1, 10, 0, 0),
            updated_at=datetime(2026, 2, 1, 8, 0, 0),
        )

        data = response.model_dump()
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)
