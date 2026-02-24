"""Tests for TradeRepository.

Story 5.1: 交易记录数据模型

This module tests the TradeRepository class for managing
trade records in the database using mocked database connections.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.storage.repositories.trade_repo import TradeRepository


class TestTradeRepository:
    """Tests for TradeRepository CRUD operations."""

    @pytest.fixture
    def repo(self) -> TradeRepository:
        """Create test repository instance."""
        return TradeRepository()

    @pytest.fixture
    def sample_trade(self) -> Trade:
        """Create sample trade for testing."""
        return Trade(
            id=0,
            market_id="test-market-1",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=100.0,
            price=0.45,
            shares=222.22,
            status=TradeStatus.FILLED,
            llm_prediction_id=None,
            position_id=None,
        )

    # ==================== save tests ====================

    @pytest.mark.asyncio
    async def test_save_trade(self, repo: TradeRepository, sample_trade: Trade) -> None:
        """Test saving a trade."""
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            saved = await repo.save(sample_trade)

            assert saved.id == 1
            assert saved.market_id == sample_trade.market_id
            assert saved.trade_type == sample_trade.trade_type
            assert saved.mode == sample_trade.mode
            assert saved.amount == sample_trade.amount
            assert saved.price == sample_trade.price
            assert saved.shares == sample_trade.shares
            assert saved.status == sample_trade.status
            mock_conn.execute.assert_called_once()
            mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_trade_with_prediction_id(self, repo: TradeRepository) -> None:
        """Test saving trade with prediction reference."""
        trade = Trade(
            id=0,
            market_id="test-market-pred",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=100.0,
            price=0.5,
            status=TradeStatus.FILLED,
            llm_prediction_id=1,
        )

        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 2

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            saved = await repo.save(trade)

            assert saved.id == 2
            assert saved.llm_prediction_id == 1

    @pytest.mark.asyncio
    async def test_save_trade_with_position_id(self, repo: TradeRepository) -> None:
        """Test saving trade with position reference."""
        trade = Trade(
            id=0,
            market_id="test-market-pos",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=100.0,
            price=0.5,
            status=TradeStatus.FILLED,
            position_id=1,
        )

        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 3

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            saved = await repo.save(trade)

            assert saved.id == 3
            assert saved.position_id == 1

    @pytest.mark.asyncio
    async def test_save_trade_without_shares(self, repo: TradeRepository) -> None:
        """Test saving trade without shares."""
        trade = Trade(
            id=0,
            market_id="test-market-no-shares",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=100.0,
            price=0.5,
            shares=None,
            status=TradeStatus.PENDING,
        )

        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 4

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            saved = await repo.save(trade)

            assert saved.id == 4
            assert saved.shares is None

    # ==================== get_by_id tests ====================

    def _create_mock_row(self, **kwargs: Any) -> MagicMock:
        """Create a mock database row."""
        mock_row = MagicMock()

        data: dict[str, Any] = {
            "id": 1,
            "market_id": "test-market",
            "trade_type": "BUY_YES",
            "mode": "PAPER",
            "amount": 100.0,
            "price": 0.5,
            "shares": 200.0,
            "status": "FILLED",
            "llm_prediction_id": None,
            "position_id": None,
            "created_at": "2026-02-16T10:30:00",
        }
        data.update(kwargs)

        # Use side_effect to properly implement __getitem__
        def getitem(key: str) -> Any:
            return data[key]

        mock_row.__getitem__.side_effect = getitem

        return mock_row

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repo: TradeRepository) -> None:
        """Test getting a trade by ID."""
        mock_row = self._create_mock_row(
            id=1,
            market_id="test-market-1",
            trade_type="BUY_YES",
            mode="PAPER",
            amount=100.0,
            price=0.45,
            shares=222.22,
            status="FILLED",
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            found = await repo.get_by_id(1)

            assert found is not None
            assert found.id == 1
            assert found.market_id == "test-market-1"
            assert found.trade_type == TradeType.BUY_YES
            assert found.status == TradeStatus.FILLED

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo: TradeRepository) -> None:
        """Test getting a non-existent trade."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            found = await repo.get_by_id(99999)

            assert found is None

    # ==================== get_by_market tests ====================

    @pytest.mark.asyncio
    async def test_get_by_market(self, repo: TradeRepository) -> None:
        """Test getting trades by market ID."""
        mock_rows = [
            self._create_mock_row(
                id=1, market_id="market-a", trade_type="BUY_YES", amount=50.0
            ),
            self._create_mock_row(
                id=2, market_id="market-a", trade_type="SELL_YES", amount=20.0
            ),
        ]

        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=mock_rows)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            trades = await repo.get_by_market("market-a")

            assert len(trades) == 2
            assert all(t.market_id == "market-a" for t in trades)

    @pytest.mark.asyncio
    async def test_get_by_market_empty(self, repo: TradeRepository) -> None:
        """Test getting trades for non-existent market."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            trades = await repo.get_by_market("non-existent-market")

            assert trades == []

    # ==================== get_by_mode tests ====================

    @pytest.mark.asyncio
    async def test_get_by_mode_paper(self, repo: TradeRepository) -> None:
        """Test getting PAPER trades."""
        mock_rows = [
            self._create_mock_row(id=1, market_id="market-1", mode="PAPER"),
            self._create_mock_row(id=2, market_id="market-2", mode="PAPER"),
        ]

        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=mock_rows)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            paper_trades = await repo.get_by_mode(TradeMode.PAPER)

            assert len(paper_trades) == 2
            assert all(t.mode == TradeMode.PAPER for t in paper_trades)

    @pytest.mark.asyncio
    async def test_get_by_mode_live(self, repo: TradeRepository) -> None:
        """Test getting LIVE trades."""
        mock_rows = [
            self._create_mock_row(id=1, market_id="market-live", mode="LIVE"),
        ]

        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=mock_rows)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            live_trades = await repo.get_by_mode(TradeMode.LIVE)

            assert len(live_trades) == 1
            assert all(t.mode == TradeMode.LIVE for t in live_trades)

    @pytest.mark.asyncio
    async def test_get_by_mode_empty(self, repo: TradeRepository) -> None:
        """Test getting trades when none exist for mode."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            live_trades = await repo.get_by_mode(TradeMode.LIVE)

            assert live_trades == []

    # ==================== get_recent tests ====================

    @pytest.mark.asyncio
    async def test_get_recent(self, repo: TradeRepository) -> None:
        """Test getting recent trades."""
        mock_rows = [
            self._create_mock_row(id=i, market_id=f"market-{i}", amount=float(i * 10))
            for i in range(3, 0, -1)
        ]

        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=mock_rows)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            recent = await repo.get_recent(3)

            assert len(recent) == 3

    @pytest.mark.asyncio
    async def test_get_recent_default_limit(self, repo: TradeRepository) -> None:
        """Test getting recent trades with default limit."""
        mock_rows = [
            self._create_mock_row(id=1, market_id="market-1"),
        ]

        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=mock_rows)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            recent = await repo.get_recent()

            assert len(recent) == 1

    @pytest.mark.asyncio
    async def test_get_recent_empty(self, repo: TradeRepository) -> None:
        """Test getting recent trades when database is empty."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            recent = await repo.get_recent()

            assert recent == []

    # ==================== _row_to_trade tests ====================

    def test_row_to_trade_with_all_fields(self, repo: TradeRepository) -> None:
        """Test converting row with all fields."""
        mock_row = self._create_mock_row(
            id=1,
            market_id="test-market",
            trade_type="BUY_YES",
            mode="PAPER",
            amount=100.0,
            price=0.5,
            shares=200.0,
            status="FILLED",
            llm_prediction_id=2,
            position_id=3,
            created_at="2026-02-16T10:30:00",
        )

        trade = repo._row_to_trade(mock_row)

        assert trade.id == 1
        assert trade.market_id == "test-market"
        assert trade.trade_type == TradeType.BUY_YES
        assert trade.mode == TradeMode.PAPER
        assert trade.amount == 100.0
        assert trade.price == 0.5
        assert trade.shares == 200.0
        assert trade.status == TradeStatus.FILLED
        assert trade.llm_prediction_id == 2
        assert trade.position_id == 3
        assert trade.created_at == datetime(2026, 2, 16, 10, 30, 0)

    def test_row_to_trade_with_null_fields(self, repo: TradeRepository) -> None:
        """Test converting row with null fields."""
        mock_row = self._create_mock_row(
            id=1,
            market_id="test-market",
            trade_type="BUY_YES",
            mode="PAPER",
            amount=100.0,
            price=0.5,
            shares=None,
            status="PENDING",
            llm_prediction_id=None,
            position_id=None,
            created_at=None,
        )

        trade = repo._row_to_trade(mock_row)

        assert trade.shares is None
        assert trade.llm_prediction_id is None
        assert trade.position_id is None
        assert trade.created_at is None

    def test_row_to_trade_all_trade_types(self, repo: TradeRepository) -> None:
        """Test converting rows with different trade types."""
        trade_types = [
            ("BUY_YES", TradeType.BUY_YES),
            ("BUY_NO", TradeType.BUY_NO),
            ("SELL_YES", TradeType.SELL_YES),
            ("SELL_NO", TradeType.SELL_NO),
        ]

        for trade_type_str, expected_type in trade_types:
            mock_row = self._create_mock_row(trade_type=trade_type_str)
            trade = repo._row_to_trade(mock_row)
            assert trade.trade_type == expected_type

    def test_row_to_trade_all_trade_statuses(self, repo: TradeRepository) -> None:
        """Test converting rows with different trade statuses."""
        statuses = [
            ("PENDING", TradeStatus.PENDING),
            ("FILLED", TradeStatus.FILLED),
            ("CANCELLED", TradeStatus.CANCELLED),
        ]

        for status_str, expected_status in statuses:
            mock_row = self._create_mock_row(status=status_str)
            trade = repo._row_to_trade(mock_row)
            assert trade.status == expected_status

    def test_row_to_trade_all_trade_modes(self, repo: TradeRepository) -> None:
        """Test converting rows with different trade modes."""
        modes = [
            ("PAPER", TradeMode.PAPER),
            ("LIVE", TradeMode.LIVE),
        ]

        for mode_str, expected_mode in modes:
            mock_row = self._create_mock_row(mode=mode_str)
            trade = repo._row_to_trade(mock_row)
            assert trade.mode == expected_mode

    # ==================== error handling tests ====================

    @pytest.mark.asyncio
    async def test_save_trade_database_error(
        self, repo: TradeRepository, sample_trade: Trade
    ) -> None:
        """Test that database errors are properly wrapped."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=aiosqlite.Error("database error"))

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            from src.exceptions import DatabaseError

            with pytest.raises(DatabaseError) as exc_info:
                await repo.save(sample_trade)

            assert "Failed to save trade" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_by_id_database_error(self, repo: TradeRepository) -> None:
        """Test that database errors are properly wrapped for get_by_id."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(side_effect=aiosqlite.Error("database error"))

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            from src.exceptions import DatabaseError

            with pytest.raises(DatabaseError) as exc_info:
                await repo.get_by_id(1)

            assert "Failed to get trade" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_by_market_database_error(self, repo: TradeRepository) -> None:
        """Test that database errors are properly wrapped for get_by_market."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(side_effect=aiosqlite.Error("database error"))

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            from src.exceptions import DatabaseError

            with pytest.raises(DatabaseError) as exc_info:
                await repo.get_by_market("market-1")

            assert "Failed to get trades for market" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_by_mode_database_error(self, repo: TradeRepository) -> None:
        """Test that database errors are properly wrapped for get_by_mode."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(side_effect=aiosqlite.Error("database error"))

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            from src.exceptions import DatabaseError

            with pytest.raises(DatabaseError) as exc_info:
                await repo.get_by_mode(TradeMode.PAPER)

            assert "Failed to get trades for mode" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_recent_database_error(self, repo: TradeRepository) -> None:
        """Test that database errors are properly wrapped for get_recent."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(side_effect=aiosqlite.Error("database error"))

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            from src.exceptions import DatabaseError

            with pytest.raises(DatabaseError) as exc_info:
                await repo.get_recent()

            assert "Failed to get recent trades" in str(exc_info.value)

    # ==================== Story 6.3: get_trades_by_date tests ====================

    @pytest.mark.asyncio
    async def test_get_trades_by_date(self, repo: TradeRepository) -> None:
        """Test getting trades for a specific date (Story 6.3)."""
        mock_rows = [
            self._create_mock_row(
                id=1,
                market_id="market-1",
                created_at="2026-02-16T10:30:00",
            ),
            self._create_mock_row(
                id=2,
                market_id="market-2",
                created_at="2026-02-16T14:00:00",
            ),
        ]

        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=mock_rows)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            trades = await repo.get_trades_by_date(date(2026, 2, 16))

            assert len(trades) == 2
            # Verify the query used the correct date
            call_args = mock_conn.execute.call_args
            assert "date(created_at) = ?" in call_args[0][0]
            assert call_args[0][1] == ("2026-02-16",)

    @pytest.mark.asyncio
    async def test_get_trades_by_date_empty(self, repo: TradeRepository) -> None:
        """Test getting trades for a date with no trades (Story 6.3)."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            trades = await repo.get_trades_by_date(date(2026, 2, 16))

            assert trades == []

    @pytest.mark.asyncio
    async def test_get_trades_by_date_database_error(self, repo: TradeRepository) -> None:
        """Test that database errors are properly wrapped for get_trades_by_date (Story 6.3)."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(side_effect=aiosqlite.Error("database error"))

        with patch(
            "src.storage.repositories.trade_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            from src.exceptions import DatabaseError

            with pytest.raises(DatabaseError) as exc_info:
                await repo.get_trades_by_date(date(2026, 2, 16))

            assert "Failed to get trades for date" in str(exc_info.value)
