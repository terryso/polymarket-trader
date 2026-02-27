"""Tests for ExitChecker.

Story 10.3: 退出条件检查器
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.config import ExitStrategySettings
from src.models.market import Market
from src.models.position import Position, PositionOutcome, PositionStatus
from src.models.prediction import Prediction, Recommendation
from src.trading.exit_checker import ExitCheckResult, ExitChecker, ExitReason


def create_exit_config(
    take_profit_enabled: bool = True,
    take_profit_pct: float = 0.50,
    stop_loss_enabled: bool = True,
    stop_loss_pct: float = -0.30,
    time_exit_enabled: bool = False,
    time_exit_hours: int = 72,
    signal_exit_enabled: bool = True,
    exit_check_interval_minutes: int = 5,
) -> ExitStrategySettings:
    """Create ExitStrategySettings with explicit values, bypassing env var issues.

    Uses model_construct to avoid pydantic-settings env var override issues.
    """
    return ExitStrategySettings.model_construct(
        take_profit_enabled=take_profit_enabled,
        take_profit_pct=take_profit_pct,
        stop_loss_enabled=stop_loss_enabled,
        stop_loss_pct=stop_loss_pct,
        time_exit_enabled=time_exit_enabled,
        time_exit_hours=time_exit_hours,
        signal_exit_enabled=signal_exit_enabled,
        exit_check_interval_minutes=exit_check_interval_minutes,
    )


class TestExitCheckResult:
    """测试 ExitCheckResult 数据类."""

    def test_exit_check_result_creation(self) -> None:
        """测试创建 ExitCheckResult."""
        result = ExitCheckResult(
            should_exit=True,
            reason="take_profit",
            priority=2,
            position_id=1,
            pnl_pct=0.55,
        )

        assert result.should_exit is True
        assert result.reason == "take_profit"
        assert result.priority == 2
        assert result.position_id == 1
        assert result.pnl_pct == 0.55

    def test_exit_check_result_no_exit(self) -> None:
        """测试不退出的结果."""
        result = ExitCheckResult(
            should_exit=False,
            reason="",
            priority=0,
            position_id=1,
            pnl_pct=0.10,
        )

        assert result.should_exit is False
        assert result.reason == ""
        assert result.priority == 0

    def test_priority_constants(self) -> None:
        """测试优先级常量."""
        assert ExitCheckResult.PRIORITY_STOP_LOSS == 1
        assert ExitCheckResult.PRIORITY_TAKE_PROFIT == 2
        assert ExitCheckResult.PRIORITY_TIME_EXIT == 3
        assert ExitCheckResult.PRIORITY_SIGNAL_EXIT == 4


class TestExitReason:
    """测试 ExitReason 枚举."""

    def test_exit_reason_values(self) -> None:
        """测试退出原因枚举值."""
        assert ExitReason.TAKE_PROFIT.value == "take_profit"
        assert ExitReason.STOP_LOSS.value == "stop_loss"
        assert ExitReason.TIME_EXIT.value == "time_exit"
        assert ExitReason.SIGNAL_EXIT.value == "signal_exit"


class TestExitChecker:
    """测试 ExitChecker 类."""

    @pytest.fixture
    def sample_market(self) -> Market:
        """创建示例市场."""
        return Market(
            id="test-market-1",
            title="Test Market",
            yes_price=0.60,
            no_price=0.40,
            liquidity=10000.0,
        )

    @pytest.fixture
    def sample_prediction_buy_yes(self) -> Prediction:
        """创建买入 YES 的预测."""
        return Prediction(
            id=1,
            market_id="test-market-1",
            predicted_probability=0.75,
            confidence=0.85,
            reasoning="Strong indicators for YES",
            recommendation=Recommendation.BUY_YES,
        )

    @pytest.fixture
    def sample_prediction_buy_no(self) -> Prediction:
        """创建买入 NO 的预测."""
        return Prediction(
            id=2,
            market_id="test-market-1",
            predicted_probability=0.25,
            confidence=0.80,
            reasoning="Strong indicators for NO",
            recommendation=Recommendation.BUY_NO,
        )

    # ==================== PnL Calculation Tests ====================

    def test_calculate_pnl_pct_profit(self) -> None:
        """测试盈利 PnL 百分比计算."""
        config = create_exit_config()
        checker = ExitChecker(config=config)
        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=67.5,  # 50% profit
            pnl=22.5,
            status=PositionStatus.OPEN,
        )
        pnl_pct = checker._calculate_pnl_pct(position)
        assert pnl_pct == 0.50  # 50% profit

    def test_calculate_pnl_pct_loss(self) -> None:
        """测试亏损 PnL 百分比计算."""
        config = create_exit_config()
        checker = ExitChecker(config=config)
        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=31.5,  # -30% loss
            pnl=-13.5,
            status=PositionStatus.OPEN,
        )
        pnl_pct = checker._calculate_pnl_pct(position)
        assert pnl_pct == -0.30  # 30% loss

    def test_calculate_pnl_pct_no_initial_value(self) -> None:
        """测试没有初始值时 PnL 计算."""
        config = create_exit_config()
        checker = ExitChecker(config=config)
        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=None,  # No initial value
            current_value=50.0,
            pnl=5.0,
            status=PositionStatus.OPEN,
        )
        pnl_pct = checker._calculate_pnl_pct(position)
        assert pnl_pct is None

    def test_calculate_pnl_pct_no_current_value(self) -> None:
        """测试没有当前值时 PnL 计算."""
        config = create_exit_config()
        checker = ExitChecker(config=config)
        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=None,  # No current value
            pnl=None,
            status=PositionStatus.OPEN,
        )
        pnl_pct = checker._calculate_pnl_pct(position)
        assert pnl_pct is None

    def test_calculate_pnl_pct_zero_initial_value(self) -> None:
        """测试初始值为零时 PnL 计算."""
        config = create_exit_config()
        checker = ExitChecker(config=config)
        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=0.0,  # Zero initial value
            current_value=50.0,
            pnl=50.0,
            status=PositionStatus.OPEN,
        )
        pnl_pct = checker._calculate_pnl_pct(position)
        assert pnl_pct is None

    # ==================== Take Profit Tests ====================

    @pytest.mark.asyncio
    async def test_take_profit_triggered(self, sample_market: Market) -> None:
        """测试止盈触发."""
        config = create_exit_config(
            take_profit_enabled=True,
            take_profit_pct=0.50,
            stop_loss_enabled=False,
            time_exit_enabled=False,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=67.5,  # 50% profit
            pnl=22.5,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = await checker.check_exit_conditions(position, sample_market)

        assert result.should_exit is True
        assert result.reason == ExitReason.TAKE_PROFIT.value
        assert result.priority == ExitCheckResult.PRIORITY_TAKE_PROFIT
        assert result.position_id == 1
        assert result.pnl_pct == 0.50

    @pytest.mark.asyncio
    async def test_take_profit_not_triggered(self, sample_market: Market) -> None:
        """测试止盈未触发."""
        config = create_exit_config(
            take_profit_enabled=True,
            take_profit_pct=0.50,
            stop_loss_enabled=False,
            time_exit_enabled=False,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=55.0,  # ~22% profit, below 50% threshold
            pnl=10.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = await checker.check_exit_conditions(position, sample_market)

        assert result.should_exit is False
        assert result.reason == ""

    @pytest.mark.asyncio
    async def test_take_profit_disabled(self, sample_market: Market) -> None:
        """测试禁用止盈时跳过检查."""
        config = create_exit_config(
            take_profit_enabled=False,  # Disabled
            take_profit_pct=0.50,
            stop_loss_enabled=False,
            time_exit_enabled=False,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=67.5,  # 50% profit - would trigger if enabled
            pnl=22.5,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = await checker.check_exit_conditions(position, sample_market)

        assert result.should_exit is False

    @pytest.mark.asyncio
    async def test_take_profit_at_exact_threshold(self, sample_market: Market) -> None:
        """测试 PnL 刚好等于止盈阈值."""
        config = create_exit_config(
            take_profit_enabled=True,
            take_profit_pct=0.50,
            stop_loss_enabled=False,
            time_exit_enabled=False,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.40,
            initial_value=40.0,
            current_value=60.0,  # Exactly 50% profit
            pnl=20.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = await checker.check_exit_conditions(position, sample_market)

        assert result.should_exit is True
        assert result.reason == ExitReason.TAKE_PROFIT.value

    # ==================== Stop Loss Tests ====================

    @pytest.mark.asyncio
    async def test_stop_loss_triggered(self, sample_market: Market) -> None:
        """测试止损触发."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=True,
            stop_loss_pct=-0.30,
            time_exit_enabled=False,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=2,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=31.5,  # -30% loss
            pnl=-13.5,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = await checker.check_exit_conditions(position, sample_market)

        assert result.should_exit is True
        assert result.reason == ExitReason.STOP_LOSS.value
        assert result.priority == ExitCheckResult.PRIORITY_STOP_LOSS
        assert result.position_id == 2
        assert result.pnl_pct == -0.30

    @pytest.mark.asyncio
    async def test_stop_loss_not_triggered(self, sample_market: Market) -> None:
        """测试止损未触发."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=True,
            stop_loss_pct=-0.30,
            time_exit_enabled=False,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=40.0,  # ~-11% loss, above -30% threshold
            pnl=-5.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = await checker.check_exit_conditions(position, sample_market)

        assert result.should_exit is False

    @pytest.mark.asyncio
    async def test_stop_loss_disabled(self, sample_market: Market) -> None:
        """测试禁用止损时跳过检查."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=False,  # Disabled
            stop_loss_pct=-0.30,
            time_exit_enabled=False,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=2,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=31.5,  # -30% loss - would trigger if enabled
            pnl=-13.5,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = await checker.check_exit_conditions(position, sample_market)

        assert result.should_exit is False

    @pytest.mark.asyncio
    async def test_stop_loss_at_exact_threshold(self, sample_market: Market) -> None:
        """测试 PnL 刚好等于止损阈值."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=True,
            stop_loss_pct=-0.30,
            time_exit_enabled=False,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.50,
            initial_value=50.0,
            current_value=35.0,  # Exactly -30% loss
            pnl=-15.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = await checker.check_exit_conditions(position, sample_market)

        assert result.should_exit is True
        assert result.reason == ExitReason.STOP_LOSS.value

    # ==================== Time Exit Tests ====================

    @pytest.mark.asyncio
    async def test_time_exit_triggered(self, sample_market: Market) -> None:
        """测试时间退出触发."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=False,
            time_exit_enabled=True,
            time_exit_hours=72,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=3,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=50.0,  # Small profit
            pnl=5.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc) - timedelta(hours=73),
        )

        result = await checker.check_exit_conditions(position, sample_market)

        assert result.should_exit is True
        assert result.reason == ExitReason.TIME_EXIT.value
        assert result.priority == ExitCheckResult.PRIORITY_TIME_EXIT
        assert result.position_id == 3

    @pytest.mark.asyncio
    async def test_time_exit_not_triggered(self, sample_market: Market) -> None:
        """测试时间退出未触发."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=False,
            time_exit_enabled=True,
            time_exit_hours=72,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=50.0,
            pnl=5.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc) - timedelta(hours=24),  # 24 hours
        )

        result = await checker.check_exit_conditions(position, sample_market)

        assert result.should_exit is False

    @pytest.mark.asyncio
    async def test_time_exit_disabled(self, sample_market: Market) -> None:
        """测试禁用时间退出时跳过检查."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=False,
            time_exit_enabled=False,  # Disabled
            time_exit_hours=72,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=3,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=50.0,
            pnl=5.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc)
            - timedelta(hours=73),  # Would trigger if enabled
        )

        result = await checker.check_exit_conditions(position, sample_market)

        assert result.should_exit is False

    @pytest.mark.asyncio
    async def test_time_exit_no_opened_at(self, sample_market: Market) -> None:
        """测试没有开仓时间时跳过时间退出检查."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=False,
            time_exit_enabled=True,
            time_exit_hours=72,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=50.0,
            pnl=5.0,
            status=PositionStatus.OPEN,
            opened_at=None,  # No opened_at
        )

        result = await checker.check_exit_conditions(position, sample_market)

        # Should not trigger time exit
        assert result.should_exit is False

    @pytest.mark.asyncio
    async def test_time_exit_at_exact_threshold(self, sample_market: Market) -> None:
        """测试持仓时间刚好等于配置阈值."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=False,
            time_exit_enabled=True,
            time_exit_hours=24,  # 24 hours
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=50.0,
            pnl=5.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc)
            - timedelta(hours=24),  # Exactly 24 hours
        )

        result = await checker.check_exit_conditions(position, sample_market)

        assert result.should_exit is True
        assert result.reason == ExitReason.TIME_EXIT.value

    # ==================== Signal Exit Tests ====================

    @pytest.mark.asyncio
    async def test_signal_exit_triggered(
        self,
        sample_market: Market,
        sample_prediction_buy_no: Prediction,
    ) -> None:
        """测试信号反转退出触发 (持仓 YES，预测建议 NO)."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=False,
            time_exit_enabled=False,
            signal_exit_enabled=True,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,  # YES position
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=50.0,  # Small profit
            pnl=5.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = await checker.check_exit_conditions(
            position, sample_market, sample_prediction_buy_no  # BUY_NO
        )

        assert result.should_exit is True
        assert result.reason == ExitReason.SIGNAL_EXIT.value
        assert result.priority == ExitCheckResult.PRIORITY_SIGNAL_EXIT
        assert result.position_id == 1

    @pytest.mark.asyncio
    async def test_signal_exit_not_triggered_same_direction(
        self,
        sample_market: Market,
        sample_prediction_buy_yes: Prediction,
    ) -> None:
        """测试信号方向一致时不触发退出."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=False,
            time_exit_enabled=False,
            signal_exit_enabled=True,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,  # YES position
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=50.0,
            pnl=5.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = await checker.check_exit_conditions(
            position, sample_market, sample_prediction_buy_yes  # BUY_YES
        )

        # Position is YES, prediction is BUY_YES - same direction
        assert result.should_exit is False

    @pytest.mark.asyncio
    async def test_signal_exit_disabled(
        self,
        sample_market: Market,
        sample_prediction_buy_no: Prediction,
    ) -> None:
        """测试禁用信号退出时跳过检查."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=False,
            time_exit_enabled=False,
            signal_exit_enabled=False,  # Disabled
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=50.0,
            pnl=5.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = await checker.check_exit_conditions(
            position, sample_market, sample_prediction_buy_no
        )

        assert result.should_exit is False

    @pytest.mark.asyncio
    async def test_signal_exit_no_prediction(self, sample_market: Market) -> None:
        """测试没有预测时跳过信号退出检查."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=False,
            time_exit_enabled=False,
            signal_exit_enabled=True,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=50.0,
            pnl=5.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = await checker.check_exit_conditions(position, sample_market, None)

        assert result.should_exit is False

    @pytest.mark.asyncio
    async def test_signal_exit_no_trade_recommendation(
        self, sample_market: Market
    ) -> None:
        """测试 NO_TRADE 建议时不触发信号退出."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=False,
            time_exit_enabled=False,
            signal_exit_enabled=True,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=50.0,
            pnl=5.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        prediction = Prediction(
            id=1,
            market_id="test-market-1",
            predicted_probability=0.50,
            confidence=0.60,
            reasoning="No clear edge",
            recommendation=Recommendation.NO_TRADE,
        )

        result = await checker.check_exit_conditions(
            position, sample_market, prediction
        )

        assert result.should_exit is False

    @pytest.mark.asyncio
    async def test_signal_exit_no_recommendation(self, sample_market: Market) -> None:
        """测试预测没有建议时不触发信号退出."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=False,
            time_exit_enabled=False,
            signal_exit_enabled=True,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=50.0,
            pnl=5.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        prediction = Prediction(
            id=1,
            market_id="test-market-1",
            predicted_probability=0.75,
            confidence=0.85,
            reasoning="Analysis",
            recommendation=None,  # No recommendation
        )

        result = await checker.check_exit_conditions(
            position, sample_market, prediction
        )

        assert result.should_exit is False

    @pytest.mark.asyncio
    async def test_signal_exit_no_position_outcome(
        self,
        sample_market: Market,
        sample_prediction_buy_no: Prediction,
    ) -> None:
        """测试 NO 持仓方向与预测方向比较."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=False,
            time_exit_enabled=False,
            signal_exit_enabled=True,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.NO,  # NO position
            shares=100.0,
            avg_price=0.35,
            initial_value=35.0,
            current_value=40.0,
            pnl=5.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        # Position is NO, prediction is BUY_NO - same direction
        result = await checker.check_exit_conditions(
            position, sample_market, sample_prediction_buy_no
        )

        assert result.should_exit is False

    # ==================== Priority Tests ====================

    @pytest.mark.asyncio
    async def test_stop_loss_has_higher_priority_than_take_profit(
        self,
        sample_market: Market,
    ) -> None:
        """测试止损优先级高于止盈."""
        config = create_exit_config(
            take_profit_enabled=True,
            take_profit_pct=0.10,  # Low threshold
            stop_loss_enabled=True,
            stop_loss_pct=-0.10,  # Low threshold
            time_exit_enabled=False,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        # Position with small loss (triggers stop loss first)
        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.50,
            initial_value=50.0,
            current_value=40.0,  # -20% loss, triggers stop loss
            pnl=-10.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = await checker.check_exit_conditions(position, sample_market)

        # Stop loss should trigger first (priority 1)
        assert result.should_exit is True
        assert result.reason == ExitReason.STOP_LOSS.value
        assert result.priority == ExitCheckResult.PRIORITY_STOP_LOSS

    # ==================== Batch Check Tests ====================

    @pytest.mark.asyncio
    async def test_check_all_positions(self, sample_market: Market) -> None:
        """测试批量检查所有持仓."""
        config = create_exit_config(
            take_profit_enabled=True,
            take_profit_pct=0.50,
            stop_loss_enabled=True,
            stop_loss_pct=-0.30,
            time_exit_enabled=True,
            time_exit_hours=72,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        # Position 1: triggers take profit
        position1 = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=67.5,  # 50% profit
            pnl=22.5,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc) - timedelta(hours=10),
        )

        # Position 2: triggers stop loss
        position2 = Position(
            id=2,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=31.5,  # -30% loss
            pnl=-13.5,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc) - timedelta(hours=10),
        )

        # Position 3: triggers time exit
        position3 = Position(
            id=3,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=50.0,  # Small profit
            pnl=5.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc) - timedelta(hours=73),
        )

        positions = [position1, position2, position3]
        markets = {"test-market-1": sample_market}

        results = await checker.check_all_positions(positions, markets)

        # All positions should trigger exit
        assert len(results) == 3
        exit_results = [r for r in results if r.should_exit]
        assert len(exit_results) == 3

    @pytest.mark.asyncio
    async def test_check_all_positions_skip_closed(self, sample_market: Market) -> None:
        """测试批量检查跳过已关闭持仓."""
        config = create_exit_config(
            take_profit_enabled=True,
            take_profit_pct=0.50,
            stop_loss_enabled=False,
            time_exit_enabled=False,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        open_position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=67.5,  # Would trigger take profit
            pnl=22.5,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        closed_position = Position(
            id=99,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=67.5,  # Would trigger take profit
            pnl=22.5,
            status=PositionStatus.CLOSED,  # Closed
            opened_at=datetime.now(timezone.utc),
        )

        positions = [open_position, closed_position]
        markets = {"test-market-1": sample_market}

        results = await checker.check_all_positions(positions, markets)

        # Only open position should be checked
        assert len(results) == 1
        assert results[0].position_id == open_position.id

    @pytest.mark.asyncio
    async def test_check_all_positions_missing_market(self) -> None:
        """测试批量检查时市场不存在的情况."""
        config = create_exit_config(
            take_profit_enabled=True,
            take_profit_pct=0.50,
            stop_loss_enabled=False,
            time_exit_enabled=False,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=67.5,
            pnl=22.5,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        positions = [position]
        markets = {}  # No markets

        results = await checker.check_all_positions(positions, markets)

        # Should skip position with missing market
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_check_all_positions_with_predictions(
        self,
        sample_market: Market,
        sample_prediction_buy_no: Prediction,
    ) -> None:
        """测试批量检查包含预测时触发信号退出."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=False,
            time_exit_enabled=False,
            signal_exit_enabled=True,
        )
        checker = ExitChecker(config=config)

        # Position with small profit (no take profit trigger)
        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=50.0,  # ~11% profit
            pnl=5.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        positions = [position]
        markets = {"test-market-1": sample_market}
        predictions = {"test-market-1": sample_prediction_buy_no}

        results = await checker.check_all_positions(positions, markets, predictions)

        assert len(results) == 1
        assert results[0].should_exit is True
        assert results[0].reason == ExitReason.SIGNAL_EXIT.value

    # ==================== Configuration Tests ====================

    @pytest.mark.asyncio
    async def test_all_strategies_disabled(self, sample_market: Market) -> None:
        """测试所有策略禁用时不触发退出."""
        config = create_exit_config(
            take_profit_enabled=False,
            stop_loss_enabled=False,
            time_exit_enabled=False,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=67.5,  # 50% profit
            pnl=22.5,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = await checker.check_exit_conditions(position, sample_market)

        assert result.should_exit is False

    @pytest.mark.asyncio
    async def test_custom_thresholds(self, sample_market: Market) -> None:
        """测试自定义阈值."""
        config = create_exit_config(
            take_profit_enabled=True,
            take_profit_pct=0.20,  # 20% profit (lower threshold)
            stop_loss_enabled=False,
            time_exit_enabled=False,
            signal_exit_enabled=False,
        )
        checker = ExitChecker(config=config)

        # Position with 22% profit
        position = Position(
            id=1,
            market_id="test-market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=55.0,  # ~22% profit
            pnl=10.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )

        result = await checker.check_exit_conditions(position, sample_market)

        assert result.should_exit is True
        assert result.reason == ExitReason.TAKE_PROFIT.value

    def test_default_config_from_settings(self) -> None:
        """测试默认配置从全局设置加载."""
        checker = ExitChecker()  # No config provided
        assert checker.config is not None
        # Should have loaded from settings
        assert hasattr(checker.config, "take_profit_enabled")
        assert hasattr(checker.config, "stop_loss_enabled")
