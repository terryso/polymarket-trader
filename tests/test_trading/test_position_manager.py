"""Tests for PositionManager.

Story 4.5: 持仓管理
Story 5.4: 模拟持仓 PnL 计算
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.state import StateSnapshot, ThreadSafeState
from src.exceptions import TradingError, ValidationError
from src.models.position import Position, PositionOutcome, PositionStatus
from src.storage.repositories.position_repo import PositionRepository
from src.trading.position_manager import PnLResult, PositionManager, TotalPnLResult


class TestPositionManager:
    """测试 PositionManager."""

    @pytest.fixture
    def state(self) -> ThreadSafeState:
        """创建测试用状态管理器."""
        return ThreadSafeState(initial_capital=200.0)

    @pytest.fixture
    def repo(self) -> PositionRepository:
        """创建测试用持仓仓库."""
        return PositionRepository()

    @pytest.fixture
    def manager(
        self, repo: PositionRepository, state: ThreadSafeState
    ) -> PositionManager:
        """创建测试用持仓管理器."""
        return PositionManager(repo, state)

    @pytest.fixture
    def sample_position(self) -> Position:
        """创建示例持仓."""
        return Position(
            id=1,
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

    # ==================== open_position tests ====================

    @pytest.mark.asyncio
    async def test_open_position(
        self, manager: PositionManager, sample_position: Position
    ) -> None:
        """测试开仓."""
        with patch.object(manager._repo, "get_by_market", return_value=None):
            with patch.object(manager._repo, "save", return_value=sample_position):
                position = await manager.open_position(
                    market_id="test-market-1",
                    outcome=PositionOutcome.YES,
                    shares=100.0,
                    price=0.45,
                )

                assert position.id == 1
                assert position.market_id == "test-market-1"
                assert position.outcome == PositionOutcome.YES
                assert position.shares == 100.0
                assert position.avg_price == 0.45
                assert position.initial_value == 45.0
                assert position.current_value == 45.0
                assert position.pnl == 0.0
                assert position.status == PositionStatus.OPEN
                assert position.opened_at is not None
                assert position.closed_at is None

    @pytest.mark.asyncio
    async def test_open_position_no_outcome(self, manager: PositionManager) -> None:
        """测试开仓 NO 方向."""
        no_position = Position(
            id=2,
            market_id="test-market-no",
            outcome=PositionOutcome.NO,
            shares=50.0,
            avg_price=0.35,
            initial_value=17.5,
            current_value=17.5,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
            closed_at=None,
        )

        with patch.object(manager._repo, "get_by_market", return_value=None):
            with patch.object(manager._repo, "save", return_value=no_position):
                position = await manager.open_position(
                    market_id="test-market-no",
                    outcome=PositionOutcome.NO,
                    shares=50.0,
                    price=0.35,
                )

                assert position.outcome == PositionOutcome.NO
                assert position.shares == 50.0
                assert position.avg_price == 0.35
                assert position.initial_value == 17.5

    @pytest.mark.asyncio
    async def test_open_position_invalid_shares(self, manager: PositionManager) -> None:
        """测试开仓 - 无效份额."""
        with pytest.raises(ValidationError, match="Shares must be positive"):
            await manager.open_position(
                market_id="test-market",
                outcome=PositionOutcome.YES,
                shares=-10.0,
                price=0.50,
            )

        with pytest.raises(ValidationError, match="Shares must be positive"):
            await manager.open_position(
                market_id="test-market",
                outcome=PositionOutcome.YES,
                shares=0.0,
                price=0.50,
            )

    @pytest.mark.asyncio
    async def test_open_position_invalid_price(self, manager: PositionManager) -> None:
        """测试开仓 - 无效价格."""
        with pytest.raises(ValidationError, match="Price must be between 0 and 1"):
            await manager.open_position(
                market_id="test-market",
                outcome=PositionOutcome.YES,
                shares=100.0,
                price=0.0,
            )

        with pytest.raises(ValidationError, match="Price must be between 0 and 1"):
            await manager.open_position(
                market_id="test-market",
                outcome=PositionOutcome.YES,
                shares=100.0,
                price=1.0,
            )

        with pytest.raises(ValidationError, match="Price must be between 0 and 1"):
            await manager.open_position(
                market_id="test-market",
                outcome=PositionOutcome.YES,
                shares=100.0,
                price=1.5,
            )

    @pytest.mark.asyncio
    async def test_open_position_duplicate(
        self, manager: PositionManager, sample_position: Position
    ) -> None:
        """测试开仓 - 重复开仓同一市场."""
        with patch.object(manager._repo, "get_by_market", return_value=sample_position):
            with pytest.raises(TradingError, match="Open position already exists"):
                await manager.open_position(
                    market_id="test-market-1",
                    outcome=PositionOutcome.YES,
                    shares=50.0,
                    price=0.60,
                )

    @pytest.mark.asyncio
    async def test_open_position_updates_state(
        self, manager: PositionManager, sample_position: Position
    ) -> None:
        """测试开仓更新状态."""
        with patch.object(manager._repo, "get_by_market", return_value=None):
            with patch.object(manager._repo, "save", return_value=sample_position):
                initial_state = await manager._state.get_state()
                initial_count = initial_state.open_positions_count

                await manager.open_position(
                    market_id="test-market-1",
                    outcome=PositionOutcome.YES,
                    shares=100.0,
                    price=0.45,
                )

                new_state = await manager._state.get_state()
                assert new_state.open_positions_count == initial_count + 1

    # ==================== update_position_value tests ====================

    @pytest.mark.asyncio
    async def test_update_position_value(
        self, manager: PositionManager, sample_position: Position
    ) -> None:
        """测试更新持仓价值."""
        with patch.object(manager._repo, "get_by_id", return_value=sample_position):
            updated_position = sample_position.model_copy(
                update={"current_value": 55.0, "pnl": 10.0}
            )
            with patch.object(manager._repo, "update", return_value=updated_position):
                updated = await manager.update_position_value(1, 0.55)

                assert updated.current_value == 55.0  # 100 * 0.55
                assert updated.pnl == 10.0  # 55 - 45

    @pytest.mark.asyncio
    async def test_update_position_value_loss(self, manager: PositionManager) -> None:
        """测试更新持仓价值 - 亏损."""
        position = Position(
            id=1,
            market_id="loss-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.50,
            initial_value=50.0,
            current_value=50.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
            closed_at=None,
        )

        with patch.object(manager._repo, "get_by_id", return_value=position):
            updated_position = position.model_copy(
                update={"current_value": 40.0, "pnl": -10.0}
            )
            with patch.object(manager._repo, "update", return_value=updated_position):
                updated = await manager.update_position_value(1, 0.40)

                assert updated.current_value == 40.0  # 100 * 0.40
                assert updated.pnl == -10.0  # 40 - 50

    @pytest.mark.asyncio
    async def test_update_position_value_invalid_price(
        self, manager: PositionManager, sample_position: Position
    ) -> None:
        """测试更新持仓价值 - 无效价格."""
        with patch.object(manager._repo, "get_by_id", return_value=sample_position):
            with pytest.raises(
                ValidationError, match="Current price must be between 0 and 1"
            ):
                await manager.update_position_value(1, 1.5)

    @pytest.mark.asyncio
    async def test_update_position_value_not_found(
        self, manager: PositionManager
    ) -> None:
        """测试更新持仓价值 - 持仓不存在."""
        with patch.object(manager._repo, "get_by_id", return_value=None):
            with pytest.raises(ValidationError, match="Position 99999 not found"):
                await manager.update_position_value(99999, 0.50)

    @pytest.mark.asyncio
    async def test_update_position_value_closed_position(
        self, manager: PositionManager
    ) -> None:
        """测试更新持仓价值 - 已关闭的持仓."""
        closed_position = Position(
            id=1,
            market_id="closed-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.50,
            initial_value=50.0,
            current_value=60.0,
            pnl=10.0,
            status=PositionStatus.CLOSED,
            opened_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc),
        )

        with patch.object(manager._repo, "get_by_id", return_value=closed_position):
            with pytest.raises(TradingError, match="Cannot update closed position"):
                await manager.update_position_value(1, 0.70)

    # ==================== close_position tests ====================

    @pytest.mark.asyncio
    async def test_close_position(
        self, manager: PositionManager, sample_position: Position
    ) -> None:
        """测试平仓."""
        with patch.object(manager._repo, "get_by_id", return_value=sample_position):
            closed_position = sample_position.model_copy(
                update={
                    "status": PositionStatus.CLOSED,
                    "current_value": 60.0,
                    "pnl": 15.0,
                    "closed_at": datetime.now(timezone.utc),
                }
            )
            with patch.object(manager._repo, "update", return_value=closed_position):
                closed = await manager.close_position(1, 0.60)

                assert closed.status == PositionStatus.CLOSED
                assert closed.current_value == 60.0
                assert closed.pnl == 15.0  # 60 - 45
                assert closed.closed_at is not None

    @pytest.mark.asyncio
    async def test_close_position_loss(self, manager: PositionManager) -> None:
        """测试平仓 - 亏损."""
        position = Position(
            id=1,
            market_id="loss-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.50,
            initial_value=50.0,
            current_value=50.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
            closed_at=None,
        )

        with patch.object(manager._repo, "get_by_id", return_value=position):
            closed_position = position.model_copy(
                update={
                    "status": PositionStatus.CLOSED,
                    "current_value": 40.0,
                    "pnl": -10.0,
                    "closed_at": datetime.now(timezone.utc),
                }
            )
            with patch.object(manager._repo, "update", return_value=closed_position):
                closed = await manager.close_position(1, 0.40)

                assert closed.status == PositionStatus.CLOSED
                assert closed.pnl == -10.0  # 40 - 50

    @pytest.mark.asyncio
    async def test_close_position_updates_state(
        self, manager: PositionManager, sample_position: Position
    ) -> None:
        """测试平仓更新状态."""
        initial_state = await manager._state.get_state()
        initial_capital = initial_state.current_capital
        initial_count = initial_state.open_positions_count

        # First open a position to increment count
        with patch.object(manager._repo, "get_by_market", return_value=None):
            with patch.object(manager._repo, "save", return_value=sample_position):
                await manager.open_position(
                    market_id="test-market-1",
                    outcome=PositionOutcome.YES,
                    shares=100.0,
                    price=0.45,
                )

        state_after_open = await manager._state.get_state()
        assert state_after_open.open_positions_count == initial_count + 1

        # Now close it
        with patch.object(manager._repo, "get_by_id", return_value=sample_position):
            closed_position = sample_position.model_copy(
                update={
                    "status": PositionStatus.CLOSED,
                    "current_value": 60.0,
                    "pnl": 15.0,
                    "closed_at": datetime.now(timezone.utc),
                }
            )
            with patch.object(manager._repo, "update", return_value=closed_position):
                await manager.close_position(1, 0.60)

        final_state = await manager._state.get_state()
        assert final_state.open_positions_count == initial_count
        assert final_state.current_capital == initial_capital + 15.0

    @pytest.mark.asyncio
    async def test_close_position_invalid_price(
        self, manager: PositionManager, sample_position: Position
    ) -> None:
        """测试平仓 - 无效价格."""
        with patch.object(manager._repo, "get_by_id", return_value=sample_position):
            with pytest.raises(
                ValidationError, match="Final price must be between 0 and 1"
            ):
                await manager.close_position(1, 1.5)

    @pytest.mark.asyncio
    async def test_close_position_not_found(self, manager: PositionManager) -> None:
        """测试平仓 - 持仓不存在."""
        with patch.object(manager._repo, "get_by_id", return_value=None):
            with pytest.raises(ValidationError, match="Position 99999 not found"):
                await manager.close_position(99999, 0.50)

    @pytest.mark.asyncio
    async def test_close_position_already_closed(
        self, manager: PositionManager
    ) -> None:
        """测试平仓 - 已关闭的持仓."""
        closed_position = Position(
            id=1,
            market_id="closed-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.50,
            initial_value=50.0,
            current_value=60.0,
            pnl=10.0,
            status=PositionStatus.CLOSED,
            opened_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc),
        )

        with patch.object(manager._repo, "get_by_id", return_value=closed_position):
            with pytest.raises(TradingError, match="already closed"):
                await manager.close_position(1, 0.70)

    # ==================== get_open_positions tests ====================

    @pytest.mark.asyncio
    async def test_get_open_positions(self, manager: PositionManager) -> None:
        """测试获取开放持仓列表."""
        mock_positions = [
            Position(
                id=1,
                market_id="m1",
                outcome=PositionOutcome.YES,
                shares=100.0,
                avg_price=0.50,
                initial_value=50.0,
                current_value=50.0,
                pnl=0.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
            ),
            Position(
                id=2,
                market_id="m2",
                outcome=PositionOutcome.NO,
                shares=50.0,
                avg_price=0.40,
                initial_value=20.0,
                current_value=20.0,
                pnl=0.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
            ),
        ]

        with patch.object(
            manager._repo, "get_open_positions", return_value=mock_positions
        ):
            positions = await manager.get_open_positions()

            assert len(positions) == 2
            for pos in positions:
                assert pos.status == PositionStatus.OPEN

    @pytest.mark.asyncio
    async def test_get_open_positions_empty(self, manager: PositionManager) -> None:
        """测试获取空列表."""
        with patch.object(manager._repo, "get_open_positions", return_value=[]):
            positions = await manager.get_open_positions()
            assert positions == []

    # ==================== get_total_exposure tests ====================

    @pytest.mark.asyncio
    async def test_get_total_exposure(self, manager: PositionManager) -> None:
        """测试计算总风险敞口."""
        mock_positions = [
            Position(
                id=1,
                market_id="m1",
                outcome=PositionOutcome.YES,
                shares=100.0,
                avg_price=0.50,
                initial_value=50.0,
                current_value=55.0,
                pnl=5.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
            ),
            Position(
                id=2,
                market_id="m2",
                outcome=PositionOutcome.NO,
                shares=50.0,
                avg_price=0.40,
                initial_value=20.0,
                current_value=20.0,
                pnl=0.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
            ),
        ]

        with patch.object(
            manager._repo, "get_open_positions", return_value=mock_positions
        ):
            exposure = await manager.get_total_exposure()
            # 55 + 20 = 75
            assert exposure == 75.0

    @pytest.mark.asyncio
    async def test_get_total_exposure_empty(self, manager: PositionManager) -> None:
        """测试空持仓的总风险敞口."""
        with patch.object(manager._repo, "get_open_positions", return_value=[]):
            exposure = await manager.get_total_exposure()
            assert exposure == 0.0

    # ==================== get_position_by_market tests ====================

    @pytest.mark.asyncio
    async def test_get_position_by_market(
        self, manager: PositionManager, sample_position: Position
    ) -> None:
        """测试通过市场 ID 获取持仓."""
        with patch.object(manager._repo, "get_by_market", return_value=sample_position):
            position = await manager.get_position_by_market("test-market-1")

            assert position is not None
            assert position.market_id == "test-market-1"
            assert position.status == PositionStatus.OPEN

    @pytest.mark.asyncio
    async def test_get_position_by_market_not_found(
        self, manager: PositionManager
    ) -> None:
        """测试通过市场 ID 获取持仓 - 不存在."""
        with patch.object(manager._repo, "get_by_market", return_value=None):
            position = await manager.get_position_by_market("non-existent-market")
            assert position is None

    # ==================== state integration tests ====================

    @pytest.mark.asyncio
    async def test_state_integration_on_multiple_operations(
        self, manager: PositionManager
    ) -> None:
        """测试多次操作后状态集成."""
        initial_state = await manager._state.get_state()
        initial_capital = initial_state.current_capital
        initial_count = initial_state.open_positions_count

        pos1 = Position(
            id=1,
            market_id="multi-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.30,
            initial_value=30.0,
            current_value=30.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
            closed_at=None,
        )
        pos2 = Position(
            id=2,
            market_id="multi-2",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.40,
            initial_value=40.0,
            current_value=40.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
            closed_at=None,
        )
        pos3 = Position(
            id=3,
            market_id="multi-3",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.50,
            initial_value=50.0,
            current_value=50.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
            closed_at=None,
        )

        # Open 3 positions
        with patch.object(manager._repo, "get_by_market", return_value=None):
            with patch.object(manager._repo, "save", side_effect=[pos1, pos2, pos3]):
                await manager.open_position("multi-1", PositionOutcome.YES, 100.0, 0.30)
                await manager.open_position("multi-2", PositionOutcome.YES, 100.0, 0.40)
                await manager.open_position("multi-3", PositionOutcome.YES, 100.0, 0.50)

        state1 = await manager._state.get_state()
        assert state1.open_positions_count == initial_count + 3

        # Close one position with profit
        closed_pos3 = pos3.model_copy(
            update={
                "status": PositionStatus.CLOSED,
                "current_value": 70.0,
                "pnl": 20.0,
                "closed_at": datetime.now(timezone.utc),
            }
        )
        with patch.object(manager._repo, "get_by_id", return_value=pos3):
            with patch.object(manager._repo, "update", return_value=closed_pos3):
                await manager.close_position(3, 0.70)  # Profit: 70 - 50 = 20

        state2 = await manager._state.get_state()
        assert state2.open_positions_count == initial_count + 2
        assert state2.current_capital == initial_capital + 20.0

    # ==================== PnL calculation tests (Story 5.4) ====================

    @pytest.mark.asyncio
    async def test_calculate_pnl_buy_yes_profit(self, manager: PositionManager) -> None:
        """测试 BUY_YES 持仓盈利场景."""
        position = Position(
            id=1,
            market_id="test-market",
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

        result = manager.calculate_pnl(position, current_price=0.55)

        assert isinstance(result, PnLResult)
        assert result.pnl == pytest.approx(10.0)  # 100 * (0.55 - 0.45)
        assert result.pnl_pct == pytest.approx(10.0 / 45.0)
        assert result.current_value == pytest.approx(55.0)

    @pytest.mark.asyncio
    async def test_calculate_pnl_buy_yes_loss(self, manager: PositionManager) -> None:
        """测试 BUY_YES 持仓亏损场景."""
        position = Position(
            id=1,
            market_id="test-market",
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

        result = manager.calculate_pnl(position, current_price=0.35)

        assert isinstance(result, PnLResult)
        assert result.pnl == pytest.approx(-10.0)  # 100 * (0.35 - 0.45)
        assert result.pnl_pct == pytest.approx(-10.0 / 45.0)
        assert result.current_value == pytest.approx(35.0)

    @pytest.mark.asyncio
    async def test_calculate_pnl_buy_no_profit(self, manager: PositionManager) -> None:
        """测试 BUY_NO 持仓盈利场景 (NO 价格上涨)."""
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.NO,
            shares=100.0,
            avg_price=0.55,
            initial_value=55.0,
            current_value=55.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
            closed_at=None,
        )

        # NO 价格从 0.55 上涨到 0.65 = 盈利
        result = manager.calculate_pnl(position, current_price=0.65)

        assert isinstance(result, PnLResult)
        assert result.pnl == pytest.approx(10.0)  # 100 * (0.65 - 0.55)
        assert result.pnl_pct == pytest.approx(10.0 / 55.0, rel=0.01)
        assert result.current_value == pytest.approx(65.0)

    @pytest.mark.asyncio
    async def test_calculate_pnl_buy_no_loss(self, manager: PositionManager) -> None:
        """测试 BUY_NO 持仓亏损场景 (NO 价格下跌)."""
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.NO,
            shares=100.0,
            avg_price=0.55,
            initial_value=55.0,
            current_value=55.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
            closed_at=None,
        )

        # NO 价格从 0.55 下跌到 0.45 = 亏损
        result = manager.calculate_pnl(position, current_price=0.45)

        assert isinstance(result, PnLResult)
        assert result.pnl == pytest.approx(-10.0)  # 100 * (0.45 - 0.55)
        assert result.pnl_pct == pytest.approx(-10.0 / 55.0, rel=0.01)
        assert result.current_value == pytest.approx(45.0)

    @pytest.mark.asyncio
    async def test_calculate_pnl_zero_initial_value(
        self, manager: PositionManager
    ) -> None:
        """测试 initial_value 为 None 的边界情况."""
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=None,  # None case
            current_value=None,
            pnl=None,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
            closed_at=None,
        )

        result = manager.calculate_pnl(position, current_price=0.55)

        assert isinstance(result, PnLResult)
        assert result.pnl == pytest.approx(10.0)
        assert result.pnl_pct == 0.0  # Safe default when initial_value is None

    @pytest.mark.asyncio
    async def test_calculate_pnl_invalid_price(self, manager: PositionManager) -> None:
        """测试 calculate_pnl - 无效价格."""
        position = Position(
            id=1,
            market_id="test-market",
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

        # Price <= 0
        with pytest.raises(
            ValidationError, match="Current price must be between 0 and 1"
        ):
            manager.calculate_pnl(position, current_price=0.0)

        # Price >= 1
        with pytest.raises(
            ValidationError, match="Current price must be between 0 and 1"
        ):
            manager.calculate_pnl(position, current_price=1.0)

        # Negative price
        with pytest.raises(
            ValidationError, match="Current price must be between 0 and 1"
        ):
            manager.calculate_pnl(position, current_price=-0.5)

        # Price > 1
        with pytest.raises(
            ValidationError, match="Current price must be between 0 and 1"
        ):
            manager.calculate_pnl(position, current_price=1.5)

    @pytest.mark.asyncio
    async def test_calculate_pnl_zero_initial_value_zero(
        self, manager: PositionManager
    ) -> None:
        """测试 initial_value 为 0 的边界情况."""
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=0.0,  # Zero case
            current_value=0.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
            closed_at=None,
        )

        result = manager.calculate_pnl(position, current_price=0.55)

        assert isinstance(result, PnLResult)
        assert result.pnl == pytest.approx(10.0)
        assert result.pnl_pct == 0.0  # Safe default when initial_value is 0

    @pytest.mark.asyncio
    async def test_calculate_total_pnl(self, manager: PositionManager) -> None:
        """测试总 PnL 计算."""
        mock_positions = [
            Position(
                id=1,
                market_id="m1",
                outcome=PositionOutcome.YES,
                shares=100.0,
                avg_price=0.45,
                initial_value=45.0,
                current_value=55.0,
                pnl=10.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
            ),
            Position(
                id=2,
                market_id="m2",
                outcome=PositionOutcome.NO,
                shares=50.0,
                avg_price=0.60,
                initial_value=30.0,
                current_value=25.0,
                pnl=-5.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
            ),
        ]

        with patch.object(
            manager._repo, "get_open_positions", return_value=mock_positions
        ):
            result = await manager.calculate_total_pnl()

            assert isinstance(result, TotalPnLResult)
            assert result.total_pnl == pytest.approx(5.0)  # 10 - 5
            assert result.positions_count == 2
            assert result.winning_count == 1
            assert result.losing_count == 1

    @pytest.mark.asyncio
    async def test_calculate_total_pnl_empty(self, manager: PositionManager) -> None:
        """测试空持仓的总 PnL 计算."""
        with patch.object(manager._repo, "get_open_positions", return_value=[]):
            result = await manager.calculate_total_pnl()

            assert isinstance(result, TotalPnLResult)
            assert result.total_pnl == 0.0
            assert result.positions_count == 0
            assert result.winning_count == 0
            assert result.losing_count == 0

    @pytest.mark.asyncio
    async def test_calculate_total_pnl_all_winning(
        self, manager: PositionManager
    ) -> None:
        """测试全部盈利的总 PnL 计算."""
        mock_positions = [
            Position(
                id=1,
                market_id="m1",
                outcome=PositionOutcome.YES,
                shares=100.0,
                avg_price=0.40,
                initial_value=40.0,
                current_value=50.0,
                pnl=10.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
            ),
            Position(
                id=2,
                market_id="m2",
                outcome=PositionOutcome.NO,
                shares=50.0,
                avg_price=0.50,
                initial_value=25.0,
                current_value=35.0,
                pnl=10.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
            ),
        ]

        with patch.object(
            manager._repo, "get_open_positions", return_value=mock_positions
        ):
            result = await manager.calculate_total_pnl()

            assert isinstance(result, TotalPnLResult)
            assert result.total_pnl == pytest.approx(20.0)
            assert result.positions_count == 2
            assert result.winning_count == 2
            assert result.losing_count == 0

    @pytest.mark.asyncio
    async def test_calculate_total_pnl_all_losing(
        self, manager: PositionManager
    ) -> None:
        """测试全部亏损的总 PnL 计算."""
        mock_positions = [
            Position(
                id=1,
                market_id="m1",
                outcome=PositionOutcome.YES,
                shares=100.0,
                avg_price=0.60,
                initial_value=60.0,
                current_value=50.0,
                pnl=-10.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
            ),
            Position(
                id=2,
                market_id="m2",
                outcome=PositionOutcome.NO,
                shares=50.0,
                avg_price=0.40,
                initial_value=20.0,
                current_value=15.0,
                pnl=-5.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
            ),
        ]

        with patch.object(
            manager._repo, "get_open_positions", return_value=mock_positions
        ):
            result = await manager.calculate_total_pnl()

            assert isinstance(result, TotalPnLResult)
            assert result.total_pnl == pytest.approx(-15.0)
            assert result.positions_count == 2
            assert result.winning_count == 0
            assert result.losing_count == 2

    @pytest.mark.asyncio
    async def test_calculate_total_pnl_with_none_pnl(
        self, manager: PositionManager
    ) -> None:
        """测试持仓 pnl 为 None 的总 PnL 计算."""
        mock_positions = [
            Position(
                id=1,
                market_id="m1",
                outcome=PositionOutcome.YES,
                shares=100.0,
                avg_price=0.45,
                initial_value=45.0,
                current_value=45.0,
                pnl=None,  # None pnl
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
            ),
        ]

        with patch.object(
            manager._repo, "get_open_positions", return_value=mock_positions
        ):
            result = await manager.calculate_total_pnl()

            assert isinstance(result, TotalPnLResult)
            assert result.total_pnl == 0.0  # None is treated as 0
            assert result.positions_count == 1
            assert result.winning_count == 0
            assert result.losing_count == 0  # pnl == 0 is not losing

    @pytest.mark.asyncio
    async def test_update_all_positions_value(self, manager: PositionManager) -> None:
        """测试批量更新持仓价值."""
        positions = [
            Position(
                id=1,
                market_id="m1",
                outcome=PositionOutcome.YES,
                shares=100.0,
                avg_price=0.45,
                initial_value=45.0,
                current_value=45.0,
                pnl=0.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
            ),
            Position(
                id=2,
                market_id="m2",
                outcome=PositionOutcome.NO,
                shares=50.0,
                avg_price=0.60,
                initial_value=30.0,
                current_value=30.0,
                pnl=0.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
            ),
        ]

        with patch.object(manager._repo, "get_open_positions", return_value=positions):
            # Mock get_by_id to return the position
            async def mock_get_by_id(pos_id: int) -> Position | None:
                for p in positions:
                    if p.id == pos_id:
                        return p
                return None

            with patch.object(manager._repo, "get_by_id", side_effect=mock_get_by_id):
                # Mock update to return the updated position
                def mock_update(pos: Position) -> Position:
                    return pos

                with patch.object(manager._repo, "update", side_effect=mock_update):
                    market_prices = {"m1": 0.55, "m2": 0.50}

                    updated = await manager.update_all_positions_value(market_prices)

                    assert len(updated) == 2
                    # Position 1: 100 shares @ new price 0.55 = 55 current_value, pnl = 10
                    assert updated[0].current_value == pytest.approx(55.0)
                    assert updated[0].pnl == pytest.approx(10.0)
                    # Position 2: 50 shares @ new price 0.50 = 25 current_value, pnl = -5
                    assert updated[1].current_value == pytest.approx(25.0)
                    assert updated[1].pnl == pytest.approx(-5.0)

    @pytest.mark.asyncio
    async def test_update_all_positions_value_missing_price(
        self, manager: PositionManager
    ) -> None:
        """测试批量更新持仓价值 - 缺少市场价格."""
        positions = [
            Position(
                id=1,
                market_id="m1",
                outcome=PositionOutcome.YES,
                shares=100.0,
                avg_price=0.45,
                initial_value=45.0,
                current_value=45.0,
                pnl=0.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
            ),
            Position(
                id=2,
                market_id="m2",
                outcome=PositionOutcome.NO,
                shares=50.0,
                avg_price=0.60,
                initial_value=30.0,
                current_value=30.0,
                pnl=0.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
            ),
        ]

        with patch.object(manager._repo, "get_open_positions", return_value=positions):

            async def mock_get_by_id(pos_id: int) -> Position | None:
                for p in positions:
                    if p.id == pos_id:
                        return p
                return None

            with patch.object(manager._repo, "get_by_id", side_effect=mock_get_by_id):

                def mock_update(pos: Position) -> Position:
                    return pos

                with patch.object(manager._repo, "update", side_effect=mock_update):
                    # Only provide price for m1, not m2
                    market_prices = {"m1": 0.55}

                    updated = await manager.update_all_positions_value(market_prices)

                    # Only 1 position should be updated (m1)
                    assert len(updated) == 1
                    assert updated[0].market_id == "m1"

    @pytest.mark.asyncio
    async def test_update_all_positions_value_empty(
        self, manager: PositionManager
    ) -> None:
        """测试批量更新持仓价值 - 空持仓."""
        with patch.object(manager._repo, "get_open_positions", return_value=[]):
            market_prices = {"m1": 0.55}

            updated = await manager.update_all_positions_value(market_prices)

            assert len(updated) == 0

    @pytest.mark.asyncio
    async def test_update_all_positions_value_with_error(
        self, manager: PositionManager
    ) -> None:
        """测试批量更新持仓价值 - 一个持仓更新失败."""
        positions = [
            Position(
                id=1,
                market_id="m1",
                outcome=PositionOutcome.YES,
                shares=100.0,
                avg_price=0.45,
                initial_value=45.0,
                current_value=45.0,
                pnl=0.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
            ),
            Position(
                id=2,
                market_id="m2",
                outcome=PositionOutcome.NO,
                shares=50.0,
                avg_price=0.60,
                initial_value=30.0,
                current_value=30.0,
                pnl=0.0,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                closed_at=None,
            ),
        ]

        with patch.object(manager._repo, "get_open_positions", return_value=positions):
            call_count = [0]

            async def mock_get_by_id(pos_id: int) -> Position | None:
                for p in positions:
                    if p.id == pos_id:
                        return p
                return None

            with patch.object(manager._repo, "get_by_id", side_effect=mock_get_by_id):

                def mock_update(pos: Position) -> Position:
                    call_count[0] += 1
                    if pos.id == 2:
                        raise TradingError("Database error")
                    return pos

                with patch.object(manager._repo, "update", side_effect=mock_update):
                    market_prices = {"m1": 0.55, "m2": 0.50}

                    updated = await manager.update_all_positions_value(market_prices)

                    # Only m1 should succeed
                    assert len(updated) == 1
                    assert updated[0].market_id == "m1"

    # ==================== PnLResult and TotalPnLResult dataclass tests ====================

    def test_pnl_result_dataclass(self) -> None:
        """测试 PnLResult 数据类."""
        result = PnLResult(
            pnl=10.0,
            pnl_pct=0.2222,
            current_value=55.0,
        )

        assert result.pnl == 10.0
        assert result.pnl_pct == pytest.approx(0.2222)
        assert result.current_value == 55.0

    def test_total_pnl_result_dataclass(self) -> None:
        """测试 TotalPnLResult 数据类."""
        result = TotalPnLResult(
            total_pnl=5.0,
            positions_count=2,
            winning_count=1,
            losing_count=1,
        )

        assert result.total_pnl == 5.0
        assert result.positions_count == 2
        assert result.winning_count == 1
        assert result.losing_count == 1

    # ==================== Notification Tests (Story 9.3) ====================

    @pytest.mark.asyncio
    async def test_init_with_notifier(self, repo: PositionRepository) -> None:
        """测试初始化时带有 notifier."""
        state = ThreadSafeState(initial_capital=200.0)
        mock_notifier = AsyncMock()
        mock_notifier.send_position_closed_notification = AsyncMock(return_value=True)

        manager = PositionManager(repo, state, notifier=mock_notifier)

        assert manager._notifier is mock_notifier

    @pytest.mark.asyncio
    async def test_init_without_notifier(self, repo: PositionRepository) -> None:
        """测试初始化时不带 notifier."""
        state = ThreadSafeState(initial_capital=200.0)

        manager = PositionManager(repo, state, notifier=None)

        assert manager._notifier is None

    @pytest.mark.asyncio
    async def test_close_position_sends_notification(
        self, repo: PositionRepository, sample_position: Position
    ) -> None:
        """测试平仓时发送通知."""
        state = ThreadSafeState(initial_capital=200.0)
        mock_notifier = AsyncMock()
        mock_notifier.send_position_closed_notification = AsyncMock(return_value=True)

        manager = PositionManager(repo, state, notifier=mock_notifier)

        # Create sample market
        from src.models.market import Market

        sample_market = Market(
            id="test-market-1",
            title="Test Market",
            yes_price=0.50,
        )

        with patch.object(manager._repo, "get_by_id", return_value=sample_position):
            closed_position = sample_position.model_copy(
                update={
                    "status": PositionStatus.CLOSED,
                    "current_value": 60.0,
                    "pnl": 15.0,
                    "closed_at": datetime.now(timezone.utc),
                }
            )
            with patch.object(manager._repo, "update", return_value=closed_position):
                await manager.close_position(1, 0.60, market=sample_market)

                # Verify notification was sent
                mock_notifier.send_position_closed_notification.assert_called_once()
                call_kwargs = mock_notifier.send_position_closed_notification.call_args
                assert call_kwargs[1]["position"] == closed_position
                assert call_kwargs[1]["market"] == sample_market
                assert call_kwargs[1]["pnl"] == pytest.approx(15.0)
                assert call_kwargs[1]["pnl_pct"] == pytest.approx(15.0 / 45.0)

    @pytest.mark.asyncio
    async def test_close_position_no_notification_without_market(
        self, repo: PositionRepository, sample_position: Position
    ) -> None:
        """测试平仓时不发送通知（没有 market 参数）."""
        state = ThreadSafeState(initial_capital=200.0)
        mock_notifier = AsyncMock()
        mock_notifier.send_position_closed_notification = AsyncMock(return_value=True)

        manager = PositionManager(repo, state, notifier=mock_notifier)

        with patch.object(manager._repo, "get_by_id", return_value=sample_position):
            closed_position = sample_position.model_copy(
                update={
                    "status": PositionStatus.CLOSED,
                    "current_value": 60.0,
                    "pnl": 15.0,
                    "closed_at": datetime.now(timezone.utc),
                }
            )
            with patch.object(manager._repo, "update", return_value=closed_position):
                await manager.close_position(1, 0.60, market=None)

                # No notification should be sent without market
                mock_notifier.send_position_closed_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_position_no_notification_when_notifier_is_none(
        self, repo: PositionRepository, sample_position: Position
    ) -> None:
        """测试平仓时不发送通知（notifier 为 None）."""
        state = ThreadSafeState(initial_capital=200.0)

        manager = PositionManager(repo, state, notifier=None)

        from src.models.market import Market

        sample_market = Market(
            id="test-market-1",
            title="Test Market",
            yes_price=0.50,
        )

        with patch.object(manager._repo, "get_by_id", return_value=sample_position):
            closed_position = sample_position.model_copy(
                update={
                    "status": PositionStatus.CLOSED,
                    "current_value": 60.0,
                    "pnl": 15.0,
                    "closed_at": datetime.now(timezone.utc),
                }
            )
            with patch.object(manager._repo, "update", return_value=closed_position):
                # Should not raise exception
                await manager.close_position(1, 0.60, market=sample_market)

    @pytest.mark.asyncio
    async def test_close_position_notification_failure_does_not_affect_close(
        self, repo: PositionRepository, sample_position: Position
    ) -> None:
        """测试通知失败不影响平仓."""
        state = ThreadSafeState(initial_capital=200.0)
        mock_notifier = AsyncMock()
        mock_notifier.send_position_closed_notification = AsyncMock(
            side_effect=Exception("Network error")
        )

        manager = PositionManager(repo, state, notifier=mock_notifier)

        from src.models.market import Market

        sample_market = Market(
            id="test-market-1",
            title="Test Market",
            yes_price=0.50,
        )

        with patch.object(manager._repo, "get_by_id", return_value=sample_position):
            closed_position = sample_position.model_copy(
                update={
                    "status": PositionStatus.CLOSED,
                    "current_value": 60.0,
                    "pnl": 15.0,
                    "closed_at": datetime.now(timezone.utc),
                }
            )
            with patch.object(manager._repo, "update", return_value=closed_position):
                # Should not raise exception
                result = await manager.close_position(1, 0.60, market=sample_market)

                # Position should still be closed
                assert result.status == PositionStatus.CLOSED
                assert result.pnl == 15.0

    @pytest.mark.asyncio
    async def test_close_position_notification_with_loss(
        self, repo: PositionRepository
    ) -> None:
        """测试平仓亏损时发送通知."""
        state = ThreadSafeState(initial_capital=200.0)
        mock_notifier = AsyncMock()
        mock_notifier.send_position_closed_notification = AsyncMock(return_value=True)

        manager = PositionManager(repo, state, notifier=mock_notifier)

        position = Position(
            id=1,
            market_id="loss-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.50,
            initial_value=50.0,
            current_value=50.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
            closed_at=None,
        )

        from src.models.market import Market

        sample_market = Market(
            id="loss-market",
            title="Loss Market",
            yes_price=0.40,
        )

        with patch.object(manager._repo, "get_by_id", return_value=position):
            closed_position = position.model_copy(
                update={
                    "status": PositionStatus.CLOSED,
                    "current_value": 40.0,
                    "pnl": -10.0,
                    "closed_at": datetime.now(timezone.utc),
                }
            )
            with patch.object(manager._repo, "update", return_value=closed_position):
                await manager.close_position(1, 0.40, market=sample_market)

                # Verify notification with loss
                call_kwargs = mock_notifier.send_position_closed_notification.call_args
                assert call_kwargs[1]["pnl"] == pytest.approx(-10.0)
                assert call_kwargs[1]["pnl_pct"] == pytest.approx(-10.0 / 50.0)
