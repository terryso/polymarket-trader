"""P0 Tests for PnL Calculation - Story 5.4.

ATDD Tests for Epic 5, P0 Scenarios:
- 5.4-UNIT-001: BUY_YES PnL 计算
- 5.4-UNIT-002: BUY_NO PnL 计算

Risk Link: R-003 (PnL 计算公式错误导致收益统计失真)

These tests verify the expected behavior of PnL calculation.
If any test fails, it indicates a bug in the implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.models.position import Position, PositionOutcome, PositionStatus
from src.trading.position_manager import PositionManager


class TestPnLCalculationP0:
    """P0 测试: PnL 计算核心逻辑.

    PnL 计算公式:
    - current_value = shares * current_price
    - pnl = current_value - initial_value
    - pnl_pct = pnl / initial_value
    """

    @pytest.fixture
    def manager(self) -> PositionManager:
        """创建测试用持仓管理器 (不需要 repo 和 state)."""
        from unittest.mock import MagicMock

        return PositionManager(
            repository=MagicMock(),
            state=MagicMock(),
        )

    # ========================================
    # 5.4-UNIT-001: BUY_YES PnL 计算
    # ========================================

    def test_calculate_pnl_buy_yes_profit(
        self, manager: PositionManager
    ) -> None:
        """测试 BUY_YES 盈利场景.

        场景: 买入 YES 份额，价格上涨
        - 初始价格: 0.45
        - 当前价格: 0.55 (上涨)
        - 预期: pnl > 0, 盈利

        Expected behavior:
        - pnl = shares * (current_price - avg_price)
        - pnl = 100 * (0.55 - 0.45) = 10.0
        - pnl_pct = 10.0 / 45.0 = 0.2222 (22.22%)
        """
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,  # 100 * 0.45
            current_value=45.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = manager.calculate_pnl(position, current_price=0.55)

        # Expected PnL: 100 * (0.55 - 0.45) = 10.0
        assert result.pnl == pytest.approx(10.0, rel=1e-4), (
            f"Expected PnL ~10.0 for price increase 0.45->0.55, got {result.pnl}"
        )
        assert result.pnl > 0, "PnL should be positive when price increases"
        assert result.pnl_pct == pytest.approx(10.0 / 45.0, rel=1e-4), (
            f"Expected PnL% ~22.22%, got {result.pnl_pct:.4f}"
        )
        assert result.current_value == pytest.approx(55.0, rel=1e-4), (
            f"Expected current_value ~55.0, got {result.current_value}"
        )

    def test_calculate_pnl_buy_yes_loss(
        self, manager: PositionManager
    ) -> None:
        """测试 BUY_YES 亏损场景.

        场景: 买入 YES 份额，价格下跌
        - 初始价格: 0.55
        - 当前价格: 0.35 (下跌)
        - 预期: pnl < 0, 亏损
        """
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.55,
            initial_value=55.0,  # 100 * 0.55
            current_value=55.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = manager.calculate_pnl(position, current_price=0.35)

        # Expected PnL: 100 * (0.35 - 0.55) = -20.0
        assert result.pnl == pytest.approx(-20.0, rel=1e-4), (
            f"Expected PnL ~-20.0 for price decrease 0.55->0.35, got {result.pnl}"
        )
        assert result.pnl < 0, "PnL should be negative when price decreases"
        assert result.pnl_pct == pytest.approx(-20.0 / 55.0, rel=1e-4), (
            f"Expected PnL% ~-36.36%, got {result.pnl_pct:.4f}"
        )

    # ========================================
    # 5.4-UNIT-002: BUY_NO PnL 计算
    # ========================================

    def test_calculate_pnl_buy_no_profit(
        self, manager: PositionManager
    ) -> None:
        """测试 BUY_NO 盈利场景.

        场景: 买入 NO 份额，NO 价格上涨 (YES 价格下跌)
        - 初始 NO 价格: 0.35 (YES=0.65)
        - 当前 NO 价格: 0.55 (YES=0.45)
        - 预期: pnl > 0, 盈利

        Note: In prediction markets, buying NO is like betting against YES.
        When YES price drops, NO price rises.
        """
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.NO,
            shares=100.0,
            avg_price=0.35,
            initial_value=35.0,  # 100 * 0.35
            current_value=35.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = manager.calculate_pnl(position, current_price=0.55)

        # Expected PnL: 100 * (0.55 - 0.35) = 20.0
        assert result.pnl == pytest.approx(20.0, rel=1e-4), (
            f"Expected PnL ~20.0 for NO price increase 0.35->0.55, got {result.pnl}"
        )
        assert result.pnl > 0, "PnL should be positive when NO price increases"
        assert result.pnl_pct == pytest.approx(20.0 / 35.0, rel=1e-4), (
            f"Expected PnL% ~57.14%, got {result.pnl_pct:.4f}"
        )

    def test_calculate_pnl_buy_no_loss(
        self, manager: PositionManager
    ) -> None:
        """测试 BUY_NO 亏损场景.

        场景: 买入 NO 份额，NO 价格下跌 (YES 价格上涨)
        - 初始 NO 价格: 0.55 (YES=0.45)
        - 当前 NO 价格: 0.35 (YES=0.65)
        - 预期: pnl < 0, 亏损
        """
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.NO,
            shares=100.0,
            avg_price=0.55,
            initial_value=55.0,  # 100 * 0.55
            current_value=55.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = manager.calculate_pnl(position, current_price=0.35)

        # Expected PnL: 100 * (0.35 - 0.55) = -20.0
        assert result.pnl == pytest.approx(-20.0, rel=1e-4), (
            f"Expected PnL ~-20.0 for NO price decrease 0.55->0.35, got {result.pnl}"
        )
        assert result.pnl < 0, "PnL should be negative when NO price decreases"
        assert result.pnl_pct == pytest.approx(-20.0 / 55.0, rel=1e-4), (
            f"Expected PnL% ~-36.36%, got {result.pnl_pct:.4f}"
        )

    # ========================================
    # 边界条件测试
    # ========================================

    def test_calculate_pnl_zero_price_change(
        self, manager: PositionManager
    ) -> None:
        """测试价格不变场景.

        场景: 价格保持不变
        - 预期: pnl = 0
        """
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.50,
            initial_value=50.0,
            current_value=50.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = manager.calculate_pnl(position, current_price=0.50)

        assert result.pnl == pytest.approx(0.0, abs=1e-6), (
            f"Expected PnL = 0 when price unchanged, got {result.pnl}"
        )
        assert result.pnl_pct == pytest.approx(0.0, abs=1e-6), (
            f"Expected PnL% = 0 when price unchanged, got {result.pnl_pct}"
        )

    def test_calculate_pnl_percentage_accuracy(
        self, manager: PositionManager
    ) -> None:
        """测试 PnL 百分比精度.

        验证公式: pnl_pct = pnl / initial_value
        """
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=200.0,
            avg_price=0.40,
            initial_value=80.0,  # 200 * 0.40
            current_value=80.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        # Price goes to 0.60
        result = manager.calculate_pnl(position, current_price=0.60)

        # pnl = 200 * (0.60 - 0.40) = 40.0
        # pnl_pct = 40.0 / 80.0 = 0.5 (50%)
        expected_pnl = 40.0
        expected_pnl_pct = expected_pnl / 80.0  # 0.5

        assert result.pnl == pytest.approx(expected_pnl, rel=1e-4)
        assert result.pnl_pct == pytest.approx(expected_pnl_pct, rel=1e-4), (
            f"pnl_pct should equal pnl/initial_value: "
            f"{result.pnl_pct} != {result.pnl}/{position.initial_value}"
        )

    def test_calculate_pnl_extreme_price_high(
        self, manager: PositionManager
    ) -> None:
        """测试极端高价场景 (接近 1.0)."""
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.90,
            initial_value=90.0,
            current_value=90.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        # Price goes to 0.99
        result = manager.calculate_pnl(position, current_price=0.99)

        # pnl = 100 * (0.99 - 0.90) = 9.0
        assert result.pnl == pytest.approx(9.0, rel=1e-4)
        assert result.current_value == pytest.approx(99.0, rel=1e-4)

    def test_calculate_pnl_extreme_price_low(
        self, manager: PositionManager
    ) -> None:
        """测试极端低价场景 (接近 0.0)."""
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.10,
            initial_value=10.0,
            current_value=10.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        # Price goes to 0.01
        result = manager.calculate_pnl(position, current_price=0.01)

        # pnl = 100 * (0.01 - 0.10) = -9.0
        assert result.pnl == pytest.approx(-9.0, rel=1e-4)
        assert result.current_value == pytest.approx(1.0, rel=1e-4)

    def test_calculate_pnl_invalid_price_zero(
        self, manager: PositionManager
    ) -> None:
        """测试无效价格 (0) 应抛出异常."""
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.50,
            initial_value=50.0,
            current_value=50.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        from src.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            manager.calculate_pnl(position, current_price=0.0)

        assert "between 0 and 1" in str(exc_info.value)

    def test_calculate_pnl_invalid_price_one(
        self, manager: PositionManager
    ) -> None:
        """测试无效价格 (1.0) 应抛出异常."""
        position = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.50,
            initial_value=50.0,
            current_value=50.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        from src.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            manager.calculate_pnl(position, current_price=1.0)

        assert "between 0 and 1" in str(exc_info.value)


class TestPnLCalculationConsistency:
    """PnL 计算一致性测试.

    验证 YES 和 NO 的计算逻辑一致性。
    """

    @pytest.fixture
    def manager(self) -> PositionManager:
        """创建测试用持仓管理器."""
        from unittest.mock import MagicMock

        return PositionManager(
            repository=MagicMock(),
            state=MagicMock(),
        )

    def test_yes_and_no_symmetric_profit(
        self, manager: PositionManager
    ) -> None:
        """测试 YES 和 NO 盈亏对称性.

        正确理解:
        - YES 价格上涨 = 买 YES 赚钱
        - NO 价格上涨 = 买 NO 赚钱

        对称场景:
        - YES at 0.45 -> 0.55: profit (YES price rises)
        - NO at 0.35 -> 0.55: profit (NO price rises, which means YES drops)

        两者都是因为它们持有的 outcome 价格上涨而盈利。
        """
        # YES position: buy at 0.45, price goes to 0.55 (YES rises)
        yes_position = Position(
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
        )

        # NO position: buy at 0.35, price goes to 0.55 (NO rises)
        # This happens when market sentiment shifts toward NO
        no_position = Position(
            id=2,
            market_id="test-market",
            outcome=PositionOutcome.NO,
            shares=100.0,
            avg_price=0.35,
            initial_value=35.0,
            current_value=35.0,
            pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        yes_result = manager.calculate_pnl(yes_position, current_price=0.55)
        no_result = manager.calculate_pnl(no_position, current_price=0.55)

        # Both should be profitable (both outcomes' prices rose)
        assert yes_result.pnl > 0, "YES should be profitable when YES price rises"
        assert no_result.pnl > 0, "NO should be profitable when NO price rises"

        # PnL should be equal (both had 0.10 price increase)
        # YES: 100 * (0.55 - 0.45) = 10.0
        # NO: 100 * (0.55 - 0.35) = 20.0
        # Not equal because different initial prices, but both profitable
        assert yes_result.pnl == pytest.approx(10.0, rel=1e-4)
        assert no_result.pnl == pytest.approx(20.0, rel=1e-4)
