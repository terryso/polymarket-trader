"""Tests for PositionRepository.

Story 4.5: 持仓管理
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.position import Position, PositionOutcome, PositionStatus
from src.storage.repositories.position_repo import PositionRepository


class TestPositionRepository:
    """测试 PositionRepository CRUD 操作."""

    @pytest.fixture
    def repo(self) -> PositionRepository:
        """创建测试用持仓仓库."""
        return PositionRepository()

    @pytest.fixture
    def sample_position(self) -> Position:
        """创建示例持仓."""
        return Position(
            id=0,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=45.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
            closed_at=None,
        )

    # ==================== save tests ====================

    @pytest.mark.asyncio
    async def test_save_position(
        self, repo: PositionRepository, sample_position: Position
    ) -> None:
        """测试保存持仓."""
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            saved = await repo.save(sample_position)

            assert saved.id == 1
            assert saved.market_id == sample_position.market_id
            assert saved.outcome == sample_position.outcome
            assert saved.shares == sample_position.shares
            assert saved.avg_price == sample_position.avg_price
            mock_conn.execute.assert_called_once()
            mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_position_with_closed_status(
        self, repo: PositionRepository
    ) -> None:
        """测试保存已关闭的持仓."""
        position = Position(
            id=0,
            market_id="closed-market",
            outcome=PositionOutcome.NO,
            shares=50.0,
            avg_price=0.35,
            initial_value=17.5,
            current_value=25.0,
            pnl=7.5,
            status=PositionStatus.CLOSED,
            opened_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc),
        )

        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 2

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            saved = await repo.save(position)

            assert saved.id == 2
            assert saved.status == PositionStatus.CLOSED
            assert saved.closed_at is not None

    # ==================== get_by_id tests ====================

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repo: PositionRepository) -> None:
        """测试通过 ID 获取持仓."""
        mock_row = self._create_mock_row(
            position_id=1,
            market_id="test-market-1",
            outcome="YES",
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=45.0,
            pnl=0.0,
            status="OPEN",
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            retrieved = await repo.get_by_id(1)

            assert retrieved is not None
            assert retrieved.id == 1
            assert retrieved.market_id == "test-market-1"
            assert retrieved.outcome == PositionOutcome.YES
            assert retrieved.status == PositionStatus.OPEN

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo: PositionRepository) -> None:
        """测试获取不存在的持仓."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            retrieved = await repo.get_by_id(99999)

            assert retrieved is None

    # ==================== get_by_market tests ====================

    @pytest.mark.asyncio
    async def test_get_by_market_found(self, repo: PositionRepository) -> None:
        """测试通过市场 ID 获取持仓."""
        mock_row = self._create_mock_row(
            position_id=1,
            market_id="test-market-1",
            outcome="YES",
            shares=100.0,
            avg_price=0.45,
            status="OPEN",
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            retrieved = await repo.get_by_market("test-market-1")

            assert retrieved is not None
            assert retrieved.market_id == "test-market-1"

    @pytest.mark.asyncio
    async def test_get_by_market_with_status_filter(
        self, repo: PositionRepository
    ) -> None:
        """测试通过市场 ID 和状态获取持仓."""
        mock_row = self._create_mock_row(
            position_id=1,
            market_id="test-market-1",
            outcome="YES",
            shares=100.0,
            avg_price=0.45,
            status="OPEN",
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            retrieved = await repo.get_by_market("test-market-1", PositionStatus.OPEN)

            assert retrieved is not None
            assert retrieved.status == PositionStatus.OPEN
            # Verify status filter was used
            call_args = mock_conn.execute.call_args
            assert "status = ?" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_by_market_with_closed_status_filter(
        self, repo: PositionRepository
    ) -> None:
        """测试通过市场 ID 和 CLOSED 状态获取持仓."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            retrieved = await repo.get_by_market("test-market-1", PositionStatus.CLOSED)

            assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_by_market_not_found(self, repo: PositionRepository) -> None:
        """测试获取不存在市场的持仓."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            retrieved = await repo.get_by_market("non-existent-market")

            assert retrieved is None

    # ==================== get_open_positions tests ====================

    @pytest.mark.asyncio
    async def test_get_open_positions(self, repo: PositionRepository) -> None:
        """测试获取所有未平仓位."""
        mock_rows = [
            self._create_mock_row(
                position_id=1,
                market_id="market-1",
                outcome="YES",
                shares=100.0,
                avg_price=0.50,
                status="OPEN",
            ),
            self._create_mock_row(
                position_id=2,
                market_id="market-2",
                outcome="NO",
                shares=50.0,
                avg_price=0.40,
                status="OPEN",
            ),
        ]

        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=mock_rows)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            open_positions = await repo.get_open_positions()

            assert len(open_positions) == 2
            for pos in open_positions:
                assert pos.status == PositionStatus.OPEN
            # Verify ORDER BY clause
            call_args = mock_conn.execute.call_args
            assert "ORDER BY opened_at DESC" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_open_positions_empty(self, repo: PositionRepository) -> None:
        """测试获取空列表."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            open_positions = await repo.get_open_positions()

            assert open_positions == []

    # ==================== update tests ====================

    @pytest.mark.asyncio
    async def test_update_position(
        self, repo: PositionRepository, sample_position: Position
    ) -> None:
        """测试更新持仓."""
        sample_position.id = 1
        sample_position.current_value = 55.0
        sample_position.pnl = 10.0

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            updated = await repo.update(sample_position)

            assert updated.current_value == 55.0
            assert updated.pnl == 10.0
            mock_conn.execute.assert_called_once()
            mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_close_position(
        self, repo: PositionRepository, sample_position: Position
    ) -> None:
        """测试关闭持仓 (更新状态)."""
        sample_position.id = 1
        sample_position.status = PositionStatus.CLOSED
        sample_position.current_value = 60.0
        sample_position.pnl = 15.0
        sample_position.closed_at = datetime.now(timezone.utc)

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            updated = await repo.update(sample_position)

            assert updated.status == PositionStatus.CLOSED
            assert updated.closed_at is not None

    # ==================== delete tests ====================

    @pytest.mark.asyncio
    async def test_delete_position(self, repo: PositionRepository) -> None:
        """测试删除持仓."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            deleted = await repo.delete(1)

            assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repo: PositionRepository) -> None:
        """测试删除不存在的持仓."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            deleted = await repo.delete(99999)

            assert deleted is False

    # ==================== _row_to_position tests ====================

    @pytest.mark.asyncio
    async def test_position_with_no_outcome(self, repo: PositionRepository) -> None:
        """测试 NO 方向的持仓."""
        mock_row = self._create_mock_row(
            position_id=1,
            market_id="test-market-no",
            outcome="NO",
            shares=50.0,
            avg_price=0.35,
            initial_value=17.5,
            current_value=17.5,
            pnl=0.0,
            status="OPEN",
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            retrieved = await repo.get_by_id(1)

            assert retrieved is not None
            assert retrieved.outcome == PositionOutcome.NO
            assert retrieved.shares == 50.0
            assert retrieved.avg_price == 0.35

    @pytest.mark.asyncio
    async def test_row_to_position_with_datetime(
        self, repo: PositionRepository
    ) -> None:
        """测试 datetime 字段解析."""
        test_opened = "2026-02-15T10:30:00+00:00"
        test_closed = "2026-02-16T14:00:00+00:00"

        mock_row = self._create_mock_row(
            position_id=1,
            market_id="test-market",
            outcome="YES",
            shares=100.0,
            avg_price=0.50,
            status="CLOSED",
            opened_at=test_opened,
            closed_at=test_closed,
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            position = await repo.get_by_id(1)

            assert position is not None
            assert position.opened_at == datetime.fromisoformat(test_opened)
            assert position.closed_at == datetime.fromisoformat(test_closed)

    @pytest.mark.asyncio
    async def test_row_to_position_with_null_datetime(
        self, repo: PositionRepository
    ) -> None:
        """测试 NULL datetime 字段."""
        mock_row = self._create_mock_row(
            position_id=1,
            market_id="test-market",
            outcome="YES",
            shares=100.0,
            avg_price=0.50,
            status="OPEN",
            opened_at=None,
            closed_at=None,
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            position = await repo.get_by_id(1)

            assert position is not None
            assert position.opened_at is None
            assert position.closed_at is None

    @pytest.mark.asyncio
    async def test_row_to_position_with_invalid_datetime(
        self, repo: PositionRepository
    ) -> None:
        """测试无效 datetime 字段处理."""
        mock_row = self._create_mock_row(
            position_id=1,
            market_id="test-market",
            outcome="YES",
            shares=100.0,
            avg_price=0.50,
            status="OPEN",
            opened_at="not-a-valid-datetime",
            closed_at="also-invalid",
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.position_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            position = await repo.get_by_id(1)

            assert position is not None
            assert position.opened_at is None
            assert position.closed_at is None

    # ==================== Helper methods ====================

    def _create_mock_row(
        self,
        position_id: int,
        market_id: str,
        outcome: str,
        shares: float,
        avg_price: float,
        initial_value: float | None = None,
        current_value: float | None = None,
        pnl: float | None = None,
        status: str = "OPEN",
        opened_at: str | None = None,
        closed_at: str | None = None,
    ) -> MagicMock:
        """Create a mock database row for testing."""
        mock_row = MagicMock()
        data: dict[str, Any] = {
            "id": position_id,
            "market_id": market_id,
            "outcome": outcome,
            "shares": shares,
            "avg_price": avg_price,
            "initial_value": initial_value,
            "current_value": current_value,
            "pnl": pnl,
            "status": status,
            "opened_at": opened_at,
            "closed_at": closed_at,
        }

        # Use side_effect to properly implement __getitem__
        def getitem(key: str) -> Any:
            return data[key]

        mock_row.__getitem__.side_effect = getitem

        return mock_row
