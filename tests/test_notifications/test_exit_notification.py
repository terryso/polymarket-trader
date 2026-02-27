"""Tests for exit notification functionality.

Story 10.5: 退出通知集成
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.market import Market
from src.models.position import Position, PositionOutcome, PositionStatus
from src.notifications.telegram_notifier import EXIT_REASON_MAP, TelegramNotifier


class TestExitReasonMapping:
    """Tests for exit reason Chinese mapping."""

    def test_take_profit_mapping(self) -> None:
        """Test take_profit maps to 止盈."""
        assert EXIT_REASON_MAP["take_profit"] == "止盈"

    def test_stop_loss_mapping(self) -> None:
        """Test stop_loss maps to 止损."""
        assert EXIT_REASON_MAP["stop_loss"] == "止损"

    def test_time_exit_mapping(self) -> None:
        """Test time_exit maps to 时间退出."""
        assert EXIT_REASON_MAP["time_exit"] == "时间退出"

    def test_signal_exit_mapping(self) -> None:
        """Test signal_exit maps to 信号反转."""
        assert EXIT_REASON_MAP["signal_exit"] == "信号反转"

    def test_manual_mapping(self) -> None:
        """Test manual maps to 手动退出."""
        assert EXIT_REASON_MAP["manual"] == "手动退出"

    def test_unknown_reason_falls_back_to_original(self) -> None:
        """Test unknown reason returns original value."""
        assert (
            EXIT_REASON_MAP.get("unknown_reason", "unknown_reason") == "unknown_reason"
        )


class TestExitNotification:
    """Tests for exit notification functionality."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock TelegramClient."""
        client = MagicMock()
        client.is_enabled = True
        client.authorized_chat_id = "123456789"
        client._bot = AsyncMock()
        return client

    @pytest.fixture
    def notifier(self, mock_client: MagicMock) -> TelegramNotifier:
        """Create a TelegramNotifier with mock client (queue disabled for tests)."""
        with patch("src.notifications.telegram_notifier.settings") as mock_settings:
            mock_settings.telegram.enabled = True
            return TelegramNotifier(mock_client, use_queue=False)

    @pytest.fixture
    def sample_position(self) -> Position:
        """Create a sample position for testing."""
        return Position(
            id=1,
            market_id="market-1",
            outcome=PositionOutcome.YES,
            shares=15.38,
            avg_price=0.65,
            initial_value=10.0,
            current_value=12.5,
            pnl=2.5,
            status=PositionStatus.CLOSED,
            opened_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def sample_market(self) -> Market:
        """Create a sample market for testing."""
        return Market(
            id="market-1",
            title="Will Trump win 2028?",
            yes_price=0.65,
        )

    @pytest.mark.asyncio
    async def test_send_exit_notification_profit(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
        sample_position: Position,
        sample_market: Market,
    ) -> None:
        """Test exit notification with profit."""
        result = await notifier.send_exit_notification(
            position=sample_position,
            market=sample_market,
            pnl=2.5,
            pnl_pct=0.25,
            exit_reason="take_profit",
        )
        assert result is True

        # Verify message format
        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        assert "*持仓退出*" in message
        assert "Will Trump win 2028?" in message
        assert "YES" in message
        assert "止盈" in message
        assert "15.38" in message  # shares
        assert "$10.00" in message  # cost
        assert "$12.50" in message  # revenue
        assert "+$2.50" in message  # profit
        assert "+25.0%" in message  # profit percentage
        assert "时间:" in message

    @pytest.mark.asyncio
    async def test_send_exit_notification_loss(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
        sample_market: Market,
    ) -> None:
        """Test exit notification with loss."""
        position = Position(
            id=1,
            market_id="market-1",
            outcome=PositionOutcome.NO,
            shares=50.0,
            avg_price=0.70,
            initial_value=35.0,
            current_value=25.0,
            pnl=-10.0,
            status=PositionStatus.CLOSED,
            opened_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc),
        )

        result = await notifier.send_exit_notification(
            position=position,
            market=sample_market,
            pnl=-10.0,
            pnl_pct=-0.2857,
            exit_reason="stop_loss",
        )
        assert result is True

        # Verify message format
        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        assert "*持仓退出*" in message
        assert "NO" in message
        assert "止损" in message
        assert "$-10.00" in message  # loss
        assert "-28.6%" in message  # loss percentage

    @pytest.mark.asyncio
    async def test_send_exit_notification_time_exit(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
        sample_position: Position,
        sample_market: Market,
    ) -> None:
        """Test exit notification with time exit reason."""
        result = await notifier.send_exit_notification(
            position=sample_position,
            market=sample_market,
            pnl=1.0,
            pnl_pct=0.10,
            exit_reason="time_exit",
        )
        assert result is True

        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        assert "时间退出" in message

    @pytest.mark.asyncio
    async def test_send_exit_notification_signal_exit(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
        sample_position: Position,
        sample_market: Market,
    ) -> None:
        """Test exit notification with signal exit reason."""
        result = await notifier.send_exit_notification(
            position=sample_position,
            market=sample_market,
            pnl=-0.5,
            pnl_pct=-0.05,
            exit_reason="signal_exit",
        )
        assert result is True

        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        assert "信号反转" in message

    @pytest.mark.asyncio
    async def test_send_exit_notification_manual(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
        sample_position: Position,
        sample_market: Market,
    ) -> None:
        """Test exit notification with manual reason."""
        result = await notifier.send_exit_notification(
            position=sample_position,
            market=sample_market,
            pnl=0.0,
            pnl_pct=0.0,
            exit_reason="manual",
        )
        assert result is True

        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        assert "手动退出" in message

    @pytest.mark.asyncio
    async def test_send_exit_notification_zero_pnl(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
        sample_market: Market,
    ) -> None:
        """Test exit notification with zero PnL."""
        position = Position(
            id=1,
            market_id="market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.50,
            initial_value=50.0,
            current_value=50.0,
            pnl=0.0,
            status=PositionStatus.CLOSED,
            opened_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc),
        )

        result = await notifier.send_exit_notification(
            position=position,
            market=sample_market,
            pnl=0.0,
            pnl_pct=0.0,
            exit_reason="time_exit",
        )
        assert result is True

        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        # Zero should show as positive (no minus sign)
        assert "+$0.00" in message
        assert "+0.0%" in message


class TestFormatExitMessage:
    """Tests for exit message formatting."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock TelegramClient."""
        client = MagicMock()
        client.is_enabled = True
        client.authorized_chat_id = "123456789"
        client._bot = AsyncMock()
        return client

    @pytest.fixture
    def notifier(self, mock_client: MagicMock) -> TelegramNotifier:
        """Create a TelegramNotifier with mock client."""
        with patch("src.notifications.telegram_notifier.settings") as mock_settings:
            mock_settings.telegram.enabled = True
            return TelegramNotifier(mock_client, use_queue=False)

    @pytest.fixture
    def sample_position(self) -> Position:
        """Create a sample position for testing."""
        return Position(
            id=1,
            market_id="market-1",
            outcome=PositionOutcome.YES,
            shares=15.38,
            avg_price=0.65,
            initial_value=10.0,
            current_value=12.5,
            pnl=2.5,
            status=PositionStatus.CLOSED,
            opened_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def sample_market(self) -> Market:
        """Create a sample market for testing."""
        return Market(
            id="market-1",
            title="Will Trump win 2028?",
            yes_price=0.65,
        )

    def test_format_exit_message_profit(
        self,
        notifier: TelegramNotifier,
        sample_position: Position,
        sample_market: Market,
    ) -> None:
        """Test exit message formatting with profit."""
        message = notifier._format_exit_message(
            position=sample_position,
            market=sample_market,
            pnl=2.5,
            pnl_pct=0.25,
            exit_reason="take_profit",
        )

        assert "*持仓退出*" in message
        assert "市场: Will Trump win 2028?" in message
        assert "方向: YES" in message
        assert "退出原因: 止盈" in message
        assert "份额: 15.38" in message
        assert "成本: $10.00" in message
        assert "收益: $12.50" in message
        assert "+$2.50" in message
        assert "+25.0%" in message
        assert "时间:" in message

    def test_format_exit_message_loss(
        self,
        notifier: TelegramNotifier,
        sample_market: Market,
    ) -> None:
        """Test exit message formatting with loss."""
        position = Position(
            id=1,
            market_id="market-1",
            outcome=PositionOutcome.NO,
            shares=50.0,
            avg_price=0.70,
            initial_value=35.0,
            current_value=25.0,
            pnl=-10.0,
            status=PositionStatus.CLOSED,
            opened_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc),
        )

        message = notifier._format_exit_message(
            position=position,
            market=sample_market,
            pnl=-10.0,
            pnl_pct=-0.2857,
            exit_reason="stop_loss",
        )

        assert "*持仓退出*" in message
        assert "方向: NO" in message
        assert "退出原因: 止损" in message
        assert "$-10.00" in message  # loss (negative sign is part of the number)
        assert "-28.6%" in message

    def test_format_exit_message_without_initial_value(
        self,
        notifier: TelegramNotifier,
        sample_market: Market,
    ) -> None:
        """Test exit message formatting without initial value."""
        position = Position(
            id=1,
            market_id="market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.50,
            initial_value=None,
            current_value=50.0,
            pnl=0.0,
            status=PositionStatus.CLOSED,
            opened_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc),
        )

        message = notifier._format_exit_message(
            position=position,
            market=sample_market,
            pnl=0.0,
            pnl_pct=0.0,
            exit_reason="manual",
        )

        assert "*持仓退出*" in message
        assert "成本: N/A" in message  # Should handle None initial_value

    def test_format_exit_message_without_current_value(
        self,
        notifier: TelegramNotifier,
        sample_market: Market,
    ) -> None:
        """Test exit message formatting without current value."""
        position = Position(
            id=1,
            market_id="market-1",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.50,
            initial_value=50.0,
            current_value=None,
            pnl=0.0,
            status=PositionStatus.CLOSED,
            opened_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc),
        )

        message = notifier._format_exit_message(
            position=position,
            market=sample_market,
            pnl=0.0,
            pnl_pct=0.0,
            exit_reason="time_exit",
        )

        assert "*持仓退出*" in message
        assert "收益: N/A" in message  # Should handle None current_value

    def test_format_exit_message_unknown_reason(
        self,
        notifier: TelegramNotifier,
        sample_position: Position,
        sample_market: Market,
    ) -> None:
        """Test exit message formatting with unknown reason."""
        message = notifier._format_exit_message(
            position=sample_position,
            market=sample_market,
            pnl=2.5,
            pnl_pct=0.25,
            exit_reason="unknown_reason",
        )

        # Should fallback to original value
        assert "退出原因: unknown_reason" in message


class TestExitNotificationWithQueue:
    """Tests for exit notification with message queue."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock TelegramClient."""
        client = MagicMock()
        client.is_enabled = True
        client.authorized_chat_id = "123456789"
        client._bot = AsyncMock()
        return client

    @pytest.fixture
    def notifier_with_queue(self, mock_client: MagicMock) -> TelegramNotifier:
        """Create a TelegramNotifier with queue enabled."""
        with patch("src.notifications.telegram_notifier.settings") as mock_settings:
            mock_settings.telegram.enabled = True
            return TelegramNotifier(mock_client, use_queue=True)

    @pytest.fixture
    def sample_position(self) -> Position:
        """Create a sample position for testing."""
        return Position(
            id=1,
            market_id="market-1",
            outcome=PositionOutcome.YES,
            shares=15.38,
            avg_price=0.65,
            initial_value=10.0,
            current_value=12.5,
            pnl=2.5,
            status=PositionStatus.CLOSED,
            opened_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def sample_market(self) -> Market:
        """Create a sample market for testing."""
        return Market(
            id="market-1",
            title="Will Trump win 2028?",
            yes_price=0.65,
        )

    @pytest.mark.asyncio
    async def test_send_exit_notification_uses_queue(
        self,
        notifier_with_queue: TelegramNotifier,
        sample_position: Position,
        sample_market: Market,
    ) -> None:
        """Test exit notification uses message queue."""
        # Start the queue
        await notifier_with_queue.start()

        result = await notifier_with_queue.send_exit_notification(
            position=sample_position,
            market=sample_market,
            pnl=2.5,
            pnl_pct=0.25,
            exit_reason="take_profit",
        )
        assert result is True

        # Verify message was queued (queue.enqueue returns True)
        # The queue handles message sending asynchronously

        # Stop the queue to clean up
        await notifier_with_queue.stop()

    @pytest.mark.asyncio
    async def test_send_exit_notification_queue_stats(
        self,
        notifier_with_queue: TelegramNotifier,
        sample_position: Position,
        sample_market: Market,
    ) -> None:
        """Test queue stats are available for exit notifications."""
        await notifier_with_queue.start()

        # Get initial stats
        stats = notifier_with_queue.get_queue_stats()
        assert stats is not None

        await notifier_with_queue.stop()


class TestExitNotificationDisabled:
    """Tests for exit notification when Telegram is disabled."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock TelegramClient that is disabled."""
        client = MagicMock()
        client.is_enabled = False
        client.authorized_chat_id = None
        client._bot = None
        return client

    @pytest.fixture
    def disabled_notifier(self, mock_client: MagicMock) -> TelegramNotifier:
        """Create a disabled TelegramNotifier."""
        with patch("src.notifications.telegram_notifier.settings") as mock_settings:
            mock_settings.telegram.enabled = False
            return TelegramNotifier(mock_client, use_queue=False)

    @pytest.fixture
    def sample_position(self) -> Position:
        """Create a sample position for testing."""
        return Position(
            id=1,
            market_id="market-1",
            outcome=PositionOutcome.YES,
            shares=15.38,
            avg_price=0.65,
            initial_value=10.0,
            current_value=12.5,
            pnl=2.5,
            status=PositionStatus.CLOSED,
            opened_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def sample_market(self) -> Market:
        """Create a sample market for testing."""
        return Market(
            id="market-1",
            title="Will Trump win 2028?",
            yes_price=0.65,
        )

    @pytest.mark.asyncio
    async def test_send_exit_notification_disabled(
        self,
        disabled_notifier: TelegramNotifier,
        sample_position: Position,
        sample_market: Market,
    ) -> None:
        """Test exit notification returns False when disabled."""
        result = await disabled_notifier.send_exit_notification(
            position=sample_position,
            market=sample_market,
            pnl=2.5,
            pnl_pct=0.25,
            exit_reason="take_profit",
        )
        assert result is False
        # Notifier is disabled, so message should not be sent
        # (disabled_notifier._enabled is False)
