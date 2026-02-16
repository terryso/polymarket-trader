"""Tests for MarketRepository."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import DatabaseError
from src.models import Market, MarketCategory
from src.storage.repositories.market_repo import MarketRepository


class TestMarketRepository:
    """Tests for MarketRepository class."""

    @pytest.fixture
    def repo(self) -> MarketRepository:
        """Create a MarketRepository instance for testing."""
        return MarketRepository()

    @pytest.fixture
    def sample_market(self) -> Market:
        """Create a sample Market for testing."""
        return Market(
            id="test-market-123",
            title="Will X happen?",
            category=MarketCategory.POLITICS,
            yes_price=0.65,
            no_price=0.35,
            liquidity=50000.0,
        )

    @pytest.fixture
    def sample_market_with_all_fields(self) -> Market:
        """Create a sample Market with all fields populated."""
        return Market(
            id="full-market-456",
            title="Will Y happen by Z date?",
            description="A detailed description of the market",
            category=MarketCategory.CRYPTO,
            yes_price=0.42,
            no_price=0.58,
            liquidity=100000.0,
            deadline=datetime(2026, 12, 31, 23, 59, 59),
            resolution_status="resolved",
            resolution_outcome="Yes",
            created_at=datetime(2026, 1, 1, 0, 0, 0),
        )

    # ==================== save_market tests ====================

    @pytest.mark.asyncio
    async def test_save_market_success(
        self, repo: MarketRepository, sample_market: Market
    ) -> None:
        """Test successful market save."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            await repo.save_market(sample_market)

            # Verify execute was called
            mock_conn.execute.assert_called_once()
            mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_market_with_all_fields(
        self, repo: MarketRepository, sample_market_with_all_fields: Market
    ) -> None:
        """Test saving a market with all fields populated."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            await repo.save_market(sample_market_with_all_fields)

            mock_conn.execute.assert_called_once()
            mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_market_database_error(
        self, repo: MarketRepository, sample_market: Market
    ) -> None:
        """Test that database errors are properly wrapped."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(
            side_effect=aiosqlite.Error("Database error")
        )

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(DatabaseError) as exc_info:
                await repo.save_market(sample_market)

            assert exc_info.value.operation == "save_market"

    # ==================== save_markets tests ====================

    @pytest.mark.asyncio
    async def test_save_markets_batch(
        self, repo: MarketRepository, sample_market: Market
    ) -> None:
        """Test batch save of multiple markets."""
        markets = [
            sample_market,
            sample_market.model_copy(update={"id": "test-market-456"}),
            sample_market.model_copy(update={"id": "test-market-789"}),
        ]

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            count = await repo.save_markets(markets)

            assert count == 3
            assert mock_conn.execute.call_count == 3
            mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_markets_empty_list(self, repo: MarketRepository) -> None:
        """Test saving an empty list of markets."""
        count = await repo.save_markets([])
        assert count == 0

    @pytest.mark.asyncio
    async def test_save_markets_handles_individual_failures(
        self, repo: MarketRepository, sample_market: Market
    ) -> None:
        """Test that individual market failures don't stop the batch."""
        import aiosqlite

        markets = [
            sample_market,
            sample_market.model_copy(update={"id": "test-market-456"}),
            sample_market.model_copy(update={"id": "test-market-789"}),
        ]

        call_count = 0

        async def mock_execute(*args: object, **kwargs: object) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                # Second market fails
                raise aiosqlite.Error("Individual error")

        mock_conn = AsyncMock()
        mock_conn.execute = mock_execute
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            count = await repo.save_markets(markets)

            # Two markets should succeed (first and third)
            assert count == 2

    @pytest.mark.asyncio
    async def test_save_markets_upsert_behavior(
        self, repo: MarketRepository, sample_market: Market
    ) -> None:
        """Test UPSERT behavior - saving same ID twice should not error."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            # Save same market twice
            await repo.save_market(sample_market)
            await repo.save_market(sample_market)

            # Should not raise an error
            assert mock_conn.execute.call_count == 2

    # ==================== update_last_fetch_time tests ====================

    @pytest.mark.asyncio
    async def test_update_last_fetch_time_success(
        self, repo: MarketRepository
    ) -> None:
        """Test successful update of last fetch time."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            await repo.update_last_fetch_time()

            mock_conn.execute.assert_called_once()
            mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_last_fetch_time_database_error(
        self, repo: MarketRepository
    ) -> None:
        """Test that database errors are properly wrapped."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(
            side_effect=aiosqlite.Error("Database error")
        )

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(DatabaseError) as exc_info:
                await repo.update_last_fetch_time()

            assert exc_info.value.operation == "update_last_fetch_time"

    # ==================== get_market tests ====================

    @pytest.mark.asyncio
    async def test_get_market_found(
        self, repo: MarketRepository, sample_market: Market
    ) -> None:
        """Test retrieving a market that exists."""
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {
            "id": sample_market.id,
            "title": sample_market.title,
            "description": sample_market.description,
            "category": sample_market.category.value
            if sample_market.category
            else None,
            "yes_price": sample_market.yes_price,
            "no_price": sample_market.no_price,
            "liquidity": sample_market.liquidity,
            "deadline": None,
            "resolution_status": None,
            "resolution_outcome": None,
            "created_at": None,
            "updated_at": None,
        }[key]

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_market(sample_market.id)

            assert result is not None
            assert result.id == sample_market.id
            assert result.title == sample_market.title

    @pytest.mark.asyncio
    async def test_get_market_not_found(self, repo: MarketRepository) -> None:
        """Test retrieving a market that doesn't exist."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_market("non-existent-id")

            assert result is None

    # ==================== get_all_markets tests ====================

    @pytest.mark.asyncio
    async def test_get_all_markets_success(self, repo: MarketRepository) -> None:
        """Test retrieving all markets."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_all_markets()

            assert result == []

    @pytest.mark.asyncio
    async def test_get_all_markets_with_limit(
        self, repo: MarketRepository
    ) -> None:
        """Test retrieving markets with limit using parameterized query."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            await repo.get_all_markets(limit=10)

            # Verify LIMIT was added to query (parameterized)
            call_args = mock_conn.execute.call_args
            assert "LIMIT ?" in call_args[0][0]
            assert call_args[0][1] == (10,)  # limit passed as parameter

    # ==================== get_last_fetch_time tests ====================

    @pytest.mark.asyncio
    async def test_get_last_fetch_time_found(self, repo: MarketRepository) -> None:
        """Test retrieving last fetch time when set."""
        test_time = "2026-02-15T10:30:00"
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: test_time

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_last_fetch_time()

            assert result is not None
            assert isinstance(result, datetime)

    @pytest.mark.asyncio
    async def test_get_last_fetch_time_not_found(
        self, repo: MarketRepository
    ) -> None:
        """Test retrieving last fetch time when not set."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_last_fetch_time()

            assert result is None

    # ==================== additional error handling tests ====================

    @pytest.mark.asyncio
    async def test_get_market_database_error(self, repo: MarketRepository) -> None:
        """Test that database errors in get_market are properly wrapped."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(
            side_effect=aiosqlite.Error("Database error")
        )

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(DatabaseError) as exc_info:
                await repo.get_market("test-id")

            assert exc_info.value.operation == "get_market"

    @pytest.mark.asyncio
    async def test_get_all_markets_database_error(
        self, repo: MarketRepository
    ) -> None:
        """Test that database errors in get_all_markets are properly wrapped."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(
            side_effect=aiosqlite.Error("Database error")
        )

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(DatabaseError) as exc_info:
                await repo.get_all_markets()

            assert exc_info.value.operation == "get_all_markets"

    @pytest.mark.asyncio
    async def test_get_last_fetch_time_database_error(
        self, repo: MarketRepository
    ) -> None:
        """Test that database errors in get_last_fetch_time are properly wrapped."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(
            side_effect=aiosqlite.Error("Database error")
        )

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(DatabaseError) as exc_info:
                await repo.get_last_fetch_time()

            assert exc_info.value.operation == "get_last_fetch_time"

    @pytest.mark.asyncio
    async def test_save_markets_connection_error_on_commit(
        self, repo: MarketRepository, sample_market: Market
    ) -> None:
        """Test that connection errors during commit are properly wrapped."""
        import aiosqlite

        markets = [sample_market]

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock(
            side_effect=aiosqlite.Error("Commit failed")
        )

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(DatabaseError) as exc_info:
                await repo.save_markets(markets)

            assert exc_info.value.operation == "save_markets"

    # ==================== get_active_markets tests ====================

    @pytest.mark.asyncio
    async def test_get_active_markets_success(
        self, repo: MarketRepository, sample_market: Market
    ) -> None:
        """Test retrieving active markets."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_active_markets()

            assert result == []
            # Verify query filters for NULL resolution_status
            call_args = mock_conn.execute.call_args
            assert "resolution_status IS NULL" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_active_markets_database_error(
        self, repo: MarketRepository
    ) -> None:
        """Test that database errors in get_active_markets are properly wrapped."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(
            side_effect=aiosqlite.Error("Database error")
        )

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(DatabaseError) as exc_info:
                await repo.get_active_markets()

            assert exc_info.value.operation == "get_active_markets"

    # ==================== get_markets_by_category tests ====================

    @pytest.mark.asyncio
    async def test_get_markets_by_category_with_enum(
        self, repo: MarketRepository
    ) -> None:
        """Test retrieving markets by category using enum."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_markets_by_category(MarketCategory.POLITICS)

            assert result == []
            # Verify category was passed as parameter
            call_args = mock_conn.execute.call_args
            assert call_args[0][1] == ("politics",)

    @pytest.mark.asyncio
    async def test_get_markets_by_category_with_string(
        self, repo: MarketRepository
    ) -> None:
        """Test retrieving markets by category using string."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_markets_by_category("crypto")

            assert result == []
            call_args = mock_conn.execute.call_args
            assert call_args[0][1] == ("crypto",)

    @pytest.mark.asyncio
    async def test_get_markets_by_category_database_error(
        self, repo: MarketRepository
    ) -> None:
        """Test that database errors in get_markets_by_category are properly wrapped."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(
            side_effect=aiosqlite.Error("Database error")
        )

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(DatabaseError) as exc_info:
                await repo.get_markets_by_category("politics")

            assert exc_info.value.operation == "get_markets_by_category"

    # ==================== update_market_resolution tests ====================

    @pytest.mark.asyncio
    async def test_update_market_resolution_success(
        self, repo: MarketRepository, sample_market: Market
    ) -> None:
        """Test successful market resolution update."""
        mock_cursor = AsyncMock()
        mock_cursor.rowcount = 1

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.update_market_resolution(sample_market.id, "YES")

            assert result is True
            mock_conn.execute.assert_called_once()
            mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_market_resolution_not_found(
        self, repo: MarketRepository
    ) -> None:
        """Test updating resolution for non-existent market."""
        mock_cursor = AsyncMock()
        mock_cursor.rowcount = 0

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.update_market_resolution("nonexistent", "YES")

            assert result is False

    @pytest.mark.asyncio
    async def test_update_market_resolution_database_error(
        self, repo: MarketRepository
    ) -> None:
        """Test that database errors in update_market_resolution are properly wrapped."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(
            side_effect=aiosqlite.Error("Database error")
        )

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(DatabaseError) as exc_info:
                await repo.update_market_resolution("test-id", "YES")

            assert exc_info.value.operation == "update_market_resolution"

    # ==================== save_market return value tests ====================

    @pytest.mark.asyncio
    async def test_save_market_returns_market(
        self, repo: MarketRepository, sample_market: Market
    ) -> None:
        """Test that save_market returns the saved Market."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.save_market(sample_market)

            assert result is not None
            assert result.id == sample_market.id
            assert result.title == sample_market.title

    # ==================== _row_to_market edge cases ====================

    @pytest.mark.asyncio
    async def test_row_to_market_with_invalid_category(
        self, repo: MarketRepository
    ) -> None:
        """Test that invalid category values are handled gracefully."""
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {
            "id": "test-id",
            "title": "Test Market",
            "description": None,
            "category": "invalid_category",  # Invalid category value
            "yes_price": 0.5,
            "no_price": 0.5,
            "liquidity": 1000.0,
            "deadline": None,
            "resolution_status": None,
            "resolution_outcome": None,
            "created_at": None,
            "updated_at": None,
        }[key]

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_market("test-id")

            assert result is not None
            assert result.category is None  # Invalid category falls back to None

    @pytest.mark.asyncio
    async def test_row_to_market_with_invalid_datetime(
        self, repo: MarketRepository
    ) -> None:
        """Test that invalid datetime values are handled gracefully."""
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {
            "id": "test-id",
            "title": "Test Market",
            "description": None,
            "category": None,
            "yes_price": 0.5,
            "no_price": 0.5,
            "liquidity": 1000.0,
            "deadline": "not-a-valid-datetime",  # Invalid datetime
            "resolution_status": None,
            "resolution_outcome": None,
            "created_at": "also-invalid",
            "updated_at": None,
        }[key]

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_market("test-id")

            assert result is not None
            assert result.deadline is None  # Invalid datetime falls back to None
            assert result.created_at is None

    @pytest.mark.asyncio
    async def test_row_to_market_with_valid_datetime(
        self, repo: MarketRepository
    ) -> None:
        """Test that valid datetime values are parsed correctly."""
        test_deadline = "2026-12-31T23:59:59"
        test_created = "2026-01-01T00:00:00"
        test_updated = "2026-02-15T10:30:00"

        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {
            "id": "test-id",
            "title": "Test Market",
            "description": None,
            "category": None,
            "yes_price": 0.5,
            "no_price": 0.5,
            "liquidity": 1000.0,
            "deadline": test_deadline,
            "resolution_status": None,
            "resolution_outcome": None,
            "created_at": test_created,
            "updated_at": test_updated,
        }[key]

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_market("test-id")

            assert result is not None
            assert result.deadline == datetime.fromisoformat(test_deadline)
            assert result.created_at == datetime.fromisoformat(test_created)
            assert result.updated_at == datetime.fromisoformat(test_updated)

    # ==================== get_all_markets with actual data ====================

    @pytest.mark.asyncio
    async def test_get_all_markets_returns_multiple_markets(
        self, repo: MarketRepository
    ) -> None:
        """Test that get_all_markets correctly parses multiple markets."""
        mock_rows = []
        for i in range(3):
            mock_row = MagicMock()
            # Use closure to capture the value of i
            def make_getitem(idx: int) -> callable:
                def getitem(self, key: str) -> any:
                    return {
                        "id": f"market-{idx}",
                        "title": f"Market {idx}",
                        "description": None,
                        "category": None,
                        "yes_price": 0.5,
                        "no_price": 0.5,
                        "liquidity": 1000.0,
                        "deadline": None,
                        "resolution_status": None,
                        "resolution_outcome": None,
                        "created_at": None,
                        "updated_at": None,
                    }[key]
                return getitem
            mock_row.__getitem__ = make_getitem(i)
            mock_rows.append(mock_row)

        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=mock_rows)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_all_markets()

            assert len(result) == 3
            assert result[0].id == "market-0"
            assert result[1].id == "market-1"
            assert result[2].id == "market-2"

    # ==================== get_active_markets with actual data ====================

    @pytest.mark.asyncio
    async def test_get_active_markets_returns_unresolved_only(
        self, repo: MarketRepository
    ) -> None:
        """Test that get_active_markets only returns unresolved markets."""
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {
            "id": "active-market",
            "title": "Active Market",
            "description": None,
            "category": None,
            "yes_price": 0.5,
            "no_price": 0.5,
            "liquidity": 1000.0,
            "deadline": None,
            "resolution_status": None,  # NULL = active
            "resolution_outcome": None,
            "created_at": None,
            "updated_at": None,
        }[key]

        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[mock_row])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_active_markets()

            assert len(result) == 1
            assert result[0].id == "active-market"
            assert result[0].resolution_status is None

    # ==================== get_markets_by_category with actual data ====================

    @pytest.mark.asyncio
    async def test_get_markets_by_category_returns_filtered_results(
        self, repo: MarketRepository
    ) -> None:
        """Test that get_markets_by_category returns correctly filtered markets."""
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {
            "id": "politics-market",
            "title": "Politics Market",
            "description": None,
            "category": "politics",
            "yes_price": 0.5,
            "no_price": 0.5,
            "liquidity": 1000.0,
            "deadline": None,
            "resolution_status": None,
            "resolution_outcome": None,
            "created_at": None,
            "updated_at": None,
        }[key]

        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[mock_row])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_markets_by_category(MarketCategory.POLITICS)

            assert len(result) == 1
            assert result[0].category == MarketCategory.POLITICS

    # ==================== additional edge cases ====================

    @pytest.mark.asyncio
    async def test_save_markets_all_fail(
        self, repo: MarketRepository, sample_market: Market
    ) -> None:
        """Test that save_markets returns 0 when all markets fail to save."""
        import aiosqlite

        markets = [
            sample_market.model_copy(update={"id": f"market-{i}"}) for i in range(3)
        ]

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=aiosqlite.Error("Insert failed"))
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            count = await repo.save_markets(markets)

            assert count == 0

    @pytest.mark.asyncio
    async def test_get_last_fetch_time_with_none_value(
        self, repo: MarketRepository
    ) -> None:
        """Test get_last_fetch_time when value column is NULL."""
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: None

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_last_fetch_time()

            assert result is None

    # ==================== get_resolved_markets tests ====================

    @pytest.mark.asyncio
    async def test_get_resolved_markets_success(
        self, repo: MarketRepository
    ) -> None:
        """Test retrieving resolved markets."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_resolved_markets()

            assert result == []
            # Verify query filters for RESOLVED status
            call_args = mock_conn.execute.call_args
            assert "resolution_status = 'RESOLVED'" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_resolved_markets_returns_resolved_only(
        self, repo: MarketRepository
    ) -> None:
        """Test that get_resolved_markets only returns resolved markets."""
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {
            "id": "resolved-market",
            "title": "Resolved Market",
            "description": None,
            "category": None,
            "yes_price": 0.5,
            "no_price": 0.5,
            "liquidity": 1000.0,
            "deadline": None,
            "resolution_status": "RESOLVED",
            "resolution_outcome": "YES",
            "created_at": None,
            "updated_at": None,
        }[key]

        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[mock_row])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.get_resolved_markets()

            assert len(result) == 1
            assert result[0].resolution_status == "RESOLVED"
            assert result[0].resolution_outcome == "YES"

    @pytest.mark.asyncio
    async def test_get_resolved_markets_database_error(
        self, repo: MarketRepository
    ) -> None:
        """Test that database errors in get_resolved_markets are properly wrapped."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(
            side_effect=aiosqlite.Error("Database error")
        )

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(DatabaseError) as exc_info:
                await repo.get_resolved_markets()

            assert exc_info.value.operation == "get_resolved_markets"

    @pytest.mark.asyncio
    async def test_get_resolved_markets_ordered_by_updated_at(
        self, repo: MarketRepository
    ) -> None:
        """Test that resolved markets are ordered by updated_at DESC."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.market_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            await repo.get_resolved_markets()

            call_args = mock_conn.execute.call_args
            assert "ORDER BY updated_at DESC" in call_args[0][0]
