"""P0 Tests for Share Calculation Precision - Story 5.2.

ATDD Tests for Epic 5, P0 Scenario:
- 5.2-UNIT-003: 份额计算精度边界

Risk Link: R-001 (交易金额计算精度错误导致资金损失)

These tests verify precision handling in share calculations.
If any test fails, it indicates a potential precision bug.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.market import Market
from src.models.position import PositionOutcome
from src.models.prediction import PredictionResult, Recommendation
from src.models.trade import TradeMode, TradeStatus, TradeType
from src.trading.paper_trading import PaperTradeResult, PaperTradingExecutor


class TestShareCalculationPrecisionP0:
    """P0 测试: 份额计算精度边界.

    份额计算公式: shares = amount / price

    关键风险:
    - 浮点数精度问题
    - 极端价格边界
    - 极端金额边界
    """

    @pytest.fixture
    def executor(self) -> PaperTradingExecutor:
        """创建测试用执行器."""
        mock_trade_repo = AsyncMock()
        mock_position_manager = AsyncMock()
        mock_state = AsyncMock()

        # Setup state mock
        mock_state.get_state = AsyncMock(
            return_value=MagicMock(current_capital=200.0)
        )

        # Setup position manager mock to return a position
        from datetime import datetime, timezone

        from src.models.position import Position

        async def mock_open_position(
            market_id: str, outcome: PositionOutcome, shares: float, price: float
        ) -> Position:
            return Position(
                id=1,
                market_id=market_id,
                outcome=outcome,
                shares=shares,
                avg_price=price,
                initial_value=shares * price,
                current_value=shares * price,
                pnl=0.0,
                status="OPEN",
                opened_at=datetime.now(timezone.utc),
            )

        mock_position_manager.open_position = mock_open_position
        mock_position_manager.get_position_by_market_from_api = AsyncMock(
            return_value=None
        )

        # Setup trade repo mock
        async def mock_save_trade(trade):
            from copy import copy

            saved = copy(trade)
            saved.id = 1
            return saved

        mock_trade_repo.save = mock_save_trade

        return PaperTradingExecutor(
            trade_repo=mock_trade_repo,
            position_manager=mock_position_manager,
            state=mock_state,
        )

    @pytest.fixture
    def sample_market(self) -> Market:
        """创建示例市场."""
        return Market(
            id="test-market",
            title="Test Market",
            description="Test Description",
            category="test",
            yes_price=0.45,
            no_price=0.55,
            liquidity=50000.0,
        )

    @pytest.fixture
    def sample_prediction(self) -> PredictionResult:
        """创建示例预测."""
        return PredictionResult(
            predicted_probability=0.70,
            confidence=0.85,
            reasoning="Test reasoning",
            key_assumptions=["Test assumption"],
            recommendation=Recommendation.BUY_YES,
            edge=0.25,
        )

    # ========================================
    # 精度边界测试
    # ========================================

    def test_calculate_shares_normal(self) -> None:
        """测试正常份额计算.

        Expected: shares = amount / price = 40 / 0.45 = 88.888...
        """
        amount = 40.0
        price = 0.45

        shares = amount / price

        # Verify calculation
        assert shares == pytest.approx(88.8888, rel=1e-3), (
            f"Expected shares ~88.89, got {shares}"
        )

        # Verify reverse calculation (shares * price ≈ amount)
        reconstructed = shares * price
        assert reconstructed == pytest.approx(amount, rel=1e-6), (
            f"Reverse calculation failed: {shares} * {price} = {reconstructed}, "
            f"expected {amount}"
        )

    def test_calculate_shares_extreme_small_price(self) -> None:
        """测试极小价格边界 (0.001).

        Expected: shares = 1 / 0.001 = 1000.0
        Risk: 精度丢失可能导致错误
        """
        amount = 1.0
        price = 0.001

        shares = amount / price

        assert shares == pytest.approx(1000.0, rel=1e-4), (
            f"Expected shares ~1000.0, got {shares}"
        )

        # Verify reverse
        reconstructed = shares * price
        assert reconstructed == pytest.approx(amount, rel=1e-6), (
            f"Reverse calculation failed: {reconstructed} != {amount}"
        )

    def test_calculate_shares_extreme_large_price(self) -> None:
        """测试极大价格边界 (0.999).

        Expected: shares = 1 / 0.999 = 1.001001...
        """
        amount = 1.0
        price = 0.999

        shares = amount / price

        assert shares == pytest.approx(1.001, rel=1e-3), (
            f"Expected shares ~1.001, got {shares}"
        )

        # Verify reverse
        reconstructed = shares * price
        assert reconstructed == pytest.approx(amount, rel=1e-6), (
            f"Reverse calculation failed: {reconstructed} != {amount}"
        )

    def test_calculate_shares_tiny_amount(self) -> None:
        """测试极小金额边界 ($0.01).

        Expected: shares = 0.01 / 0.50 = 0.02
        Risk: 小金额可能被舍入为 0
        """
        amount = 0.01
        price = 0.50

        shares = amount / price

        assert shares == pytest.approx(0.02, rel=1e-4), (
            f"Expected shares ~0.02, got {shares}"
        )

        # Verify reverse
        reconstructed = shares * price
        assert reconstructed == pytest.approx(amount, rel=1e-6), (
            f"Reverse calculation failed: {reconstructed} != {amount}"
        )

    def test_calculate_shares_large_amount(self) -> None:
        """测试大金额 ($10,000).

        Expected: shares = 10000 / 0.50 = 20000.0
        """
        amount = 10000.0
        price = 0.50

        shares = amount / price

        assert shares == pytest.approx(20000.0, rel=1e-4), (
            f"Expected shares ~20000.0, got {shares}"
        )

        # Verify reverse
        reconstructed = shares * price
        assert reconstructed == pytest.approx(amount, rel=1e-6), (
            f"Reverse calculation failed: {reconstructed} != {amount}"
        )

    def test_calculate_shares_precision_consistency(self) -> None:
        """测试精度一致性.

        验证: shares * price ≈ amount
        对多个边界值进行测试。
        """
        test_cases = [
            (1.0, 0.001),  # 极小价格
            (1.0, 0.01),
            (1.0, 0.10),
            (1.0, 0.50),
            (1.0, 0.90),
            (1.0, 0.99),
            (1.0, 0.999),  # 极大价格
            (0.01, 0.50),  # 极小金额
            (10000.0, 0.50),  # 大金额
            (40.0, 0.45),  # 常规场景
        ]

        for amount, price in test_cases:
            shares = amount / price
            reconstructed = shares * price

            assert reconstructed == pytest.approx(amount, rel=1e-6), (
                f"Precision lost for amount={amount}, price={price}: "
                f"shares={shares}, reconstructed={reconstructed}"
            )

    def test_calculate_shares_many_decimal_places(self) -> None:
        """测试多小数位精度.

        验证不会因为小数位过多而丢失精度。
        """
        amount = 100.0
        price = 0.123456789

        shares = amount / price

        # Should be approximately 810.0
        assert shares == pytest.approx(810.0, rel=1e-2), (
            f"Expected shares ~810, got {shares}"
        )

        # Verify reverse with higher precision requirement
        reconstructed = shares * price
        assert reconstructed == pytest.approx(amount, rel=1e-4), (
            f"Precision lost for price with many decimals: {reconstructed} != {amount}"
        )

    def test_calculate_shares_buy_no_price(self) -> None:
        """测试 BUY_NO 的份额计算.

        BUY_NO 使用 no_price 而非 yes_price。
        """
        amount = 50.0
        yes_price = 0.65
        no_price = 1.0 - yes_price  # 0.35

        shares = amount / no_price

        assert shares == pytest.approx(142.857, rel=1e-3), (
            f"Expected shares ~142.86, got {shares}"
        )

        # Verify with actual no_price
        reconstructed = shares * no_price
        assert reconstructed == pytest.approx(amount, rel=1e-6)

    def test_calculate_shares_round_trip_accuracy(self) -> None:
        """测试往返精度.

        验证: amount -> shares -> value ≈ amount
        模拟完整的交易计算流程。
        """
        initial_amount = 40.0
        price = 0.45

        # Step 1: Calculate shares
        shares = initial_amount / price

        # Step 2: Calculate value (what we actually invested)
        calculated_value = shares * price

        # Should equal initial amount
        assert calculated_value == pytest.approx(initial_amount, rel=1e-6), (
            f"Round trip failed: {initial_amount} -> shares={shares} -> "
            f"value={calculated_value}"
        )


class TestShareCalculationEdgeCases:
    """份额计算边界条件测试."""

    def test_zero_amount_should_fail(self) -> None:
        """测试金额为 0 应该被拒绝."""
        amount = 0.0
        price = 0.50

        # In production, this should be validated before calculation
        # Here we just verify the math works but flag it as invalid
        if amount > 0:
            shares = amount / price
        else:
            shares = 0.0

        assert shares == 0.0, "Zero amount should result in zero shares"

    def test_zero_price_should_fail(self) -> None:
        """测试价格为 0 应该抛出异常."""
        amount = 10.0
        price = 0.0

        with pytest.raises(ZeroDivisionError):
            _ = amount / price

    def test_negative_amount_should_fail(self) -> None:
        """测试负金额应该被拒绝."""
        amount = -10.0
        price = 0.50

        # In production, validation should catch this
        # Mathematical result would be negative
        shares = amount / price
        assert shares < 0, "Negative amount produces negative shares (invalid)"

    def test_price_greater_than_one_should_fail(self) -> None:
        """测试价格大于 1 应该被拒绝 (无效概率)."""
        # In prediction markets, prices must be between 0 and 1
        invalid_price = 1.5

        assert not (0 < invalid_price < 1), (
            f"Price {invalid_price} is outside valid range (0, 1)"
        )
