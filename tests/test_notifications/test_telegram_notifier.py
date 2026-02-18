"""Tests for TelegramNotifier.

Story 9.2: 通知消息发送
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.market import Market
from src.models.prediction import PredictionResult, Recommendation
from src.models.trade import Trade, TradeMode, TradeStatus, TradeType
from src.notifications.telegram_notifier import TelegramNotifier


class TestTelegramNotifier:
    """Tests for TelegramNotifier class."""

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
            return TelegramNotifier(mock_client)

    @pytest.fixture
    def sample_trade(self) -> Trade:
        """Create a sample trade for testing."""
        return Trade(
            id=1,
            market_id="market-1",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=10.0,
            price=0.65,
            shares=15.38,
            status=TradeStatus.FILLED,
        )

    @pytest.fixture
    def sample_market(self) -> Market:
        """Create a sample market for testing."""
        return Market(
            id="market-1",
            title="Will Trump win 2028?",
            yes_price=0.65,
        )

    @pytest.fixture
    def sample_prediction(self) -> PredictionResult:
        """Create a sample prediction for testing."""
        return PredictionResult(
            predicted_probability=0.75,
            confidence=0.85,
            reasoning="Strong indicators",
            key_assumptions=["Economy stable", "No major news"],
            recommendation=Recommendation.BUY_YES,
            edge=0.20,
        )

    def test_init_enabled(self, mock_client: MagicMock) -> None:
        """Test initialization when enabled."""
        with patch("src.notifications.telegram_notifier.settings") as mock_settings:
            mock_settings.telegram.enabled = True
            mock_client.is_enabled = True

            notifier = TelegramNotifier(mock_client)
            assert notifier._enabled is True

    def test_init_disabled_by_settings(self, mock_client: MagicMock) -> None:
        """Test initialization when disabled by settings."""
        with patch("src.notifications.telegram_notifier.settings") as mock_settings:
            mock_settings.telegram.enabled = False
            mock_client.is_enabled = True

            notifier = TelegramNotifier(mock_client)
            assert notifier._enabled is False

    def test_init_disabled_by_client(self, mock_client: MagicMock) -> None:
        """Test initialization when client is not enabled."""
        with patch("src.notifications.telegram_notifier.settings") as mock_settings:
            mock_settings.telegram.enabled = True
            mock_client.is_enabled = False

            notifier = TelegramNotifier(mock_client)
            assert notifier._enabled is False

    @pytest.mark.asyncio
    async def test_send_message_success(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
    ) -> None:
        """Test successful message sending."""
        result = await notifier.send_message("Test message")
        assert result is True
        mock_client._bot.send_message.assert_called_once_with(
            chat_id="123456789",
            text="Test message",
            parse_mode="Markdown",
        )

    @pytest.mark.asyncio
    async def test_send_message_with_custom_parse_mode(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
    ) -> None:
        """Test message sending with custom parse mode."""
        result = await notifier.send_message("Test message", parse_mode="HTML")
        assert result is True
        mock_client._bot.send_message.assert_called_once_with(
            chat_id="123456789",
            text="Test message",
            parse_mode="HTML",
        )

    @pytest.mark.asyncio
    async def test_send_message_disabled(self, mock_client: MagicMock) -> None:
        """Test message sending when disabled."""
        with patch("src.notifications.telegram_notifier.settings") as mock_settings:
            mock_settings.telegram.enabled = False
            mock_client.is_enabled = False

            notifier = TelegramNotifier(mock_client)
            result = await notifier.send_message("Test message")
            assert result is False
            mock_client._bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_message_no_chat_id(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Test message sending when no chat_id configured."""
        with patch("src.notifications.telegram_notifier.settings") as mock_settings:
            mock_settings.telegram.enabled = True
            mock_client.is_enabled = True
            mock_client.authorized_chat_id = None

            notifier = TelegramNotifier(mock_client)
            result = await notifier.send_message("Test message")
            assert result is False
            mock_client._bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_message_error(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
    ) -> None:
        """Test message sending with error."""
        mock_client._bot.send_message.side_effect = Exception("Network error")
        result = await notifier.send_message("Test message")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_bot_not_initialized(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Test message sending when bot is not initialized."""
        with patch("src.notifications.telegram_notifier.settings") as mock_settings:
            mock_settings.telegram.enabled = True
            mock_client.is_enabled = True
            mock_client._bot = None  # Bot not initialized

            notifier = TelegramNotifier(mock_client)
            result = await notifier.send_message("Test message")
            assert result is False

    @pytest.mark.asyncio
    async def test_send_trade_notification(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
        sample_trade: Trade,
        sample_market: Market,
    ) -> None:
        """Test trade notification."""
        result = await notifier.send_trade_notification(sample_trade, sample_market)
        assert result is True

        # Verify message format
        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        assert "*交易执行*" in message
        assert "Will Trump win 2028?" in message
        assert "BUY_YES" in message
        assert "$10.00" in message
        assert "0.6500" in message
        assert "15.38" in message

    @pytest.mark.asyncio
    async def test_send_trade_notification_without_shares(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
        sample_market: Market,
    ) -> None:
        """Test trade notification without shares."""
        trade = Trade(
            id=1,
            market_id="market-1",
            trade_type=TradeType.BUY_NO,
            mode=TradeMode.PAPER,
            amount=20.0,
            price=0.35,
            shares=None,
            status=TradeStatus.FILLED,
        )
        result = await notifier.send_trade_notification(trade, sample_market)
        assert result is True

        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        assert "*交易执行*" in message
        assert "BUY_NO" in message
        assert "份额" not in message  # Shares should not appear

    @pytest.mark.asyncio
    async def test_send_analysis_notification(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
        sample_prediction: PredictionResult,
        sample_market: Market,
    ) -> None:
        """Test analysis notification."""
        result = await notifier.send_analysis_notification(
            sample_prediction, sample_market
        )
        assert result is True

        # Verify message format
        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        assert "*市场分析*" in message
        assert "Will Trump win 2028?" in message
        assert "YES 0.65" in message
        assert "YES 0.75" in message
        assert "85%" in message
        assert "20%" in message  # Edge
        assert "BUY_YES" in message
        assert "*关键假设:*" in message
        assert "Economy stable" in message

    @pytest.mark.asyncio
    async def test_send_analysis_notification_buy_no(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
        sample_market: Market,
    ) -> None:
        """Test analysis notification for BUY_NO recommendation."""
        prediction = PredictionResult(
            predicted_probability=0.75,
            confidence=0.85,
            reasoning="Strong indicators",
            key_assumptions=[],
            recommendation=Recommendation.BUY_NO,
            edge=0.20,
        )
        result = await notifier.send_analysis_notification(prediction, sample_market)
        assert result is True

        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        assert "NO 0.75" in message
        assert "BUY_NO" in message

    @pytest.mark.asyncio
    async def test_send_analysis_notification_without_edge(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
        sample_market: Market,
    ) -> None:
        """Test analysis notification without edge."""
        prediction = PredictionResult(
            predicted_probability=0.55,
            confidence=0.65,
            reasoning="Weak indicators",
            key_assumptions=[],
            recommendation=Recommendation.NO_TRADE,
            edge=None,
        )
        result = await notifier.send_analysis_notification(prediction, sample_market)
        assert result is True

        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        assert "Edge:" not in message

    @pytest.mark.asyncio
    async def test_send_error_notification_exception(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
    ) -> None:
        """Test error notification with exception."""
        error = ValueError("Test error message")
        result = await notifier.send_error_notification(error)
        assert result is True

        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        assert "*错误告警*" in message
        assert "ValueError" in message
        assert "Test error message" in message

    @pytest.mark.asyncio
    async def test_send_error_notification_string(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
    ) -> None:
        """Test error notification with string."""
        result = await notifier.send_error_notification("Simple error message")
        assert result is True

        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        assert "*错误告警*" in message
        assert "Error" in message
        assert "Simple error message" in message

    @pytest.mark.asyncio
    async def test_send_error_notification_truncates_long_message(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
    ) -> None:
        """Test error notification truncates long messages."""
        long_message = "A" * 300
        result = await notifier.send_error_notification(long_message)
        assert result is True

        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        # Should be truncated to 200 chars
        assert "A" * 200 in message
        assert (
            len([line for line in message.split("\n") if line.startswith("信息:")][0])
            <= 210
        )

    @pytest.mark.asyncio
    async def test_send_system_notification(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
    ) -> None:
        """Test system notification."""
        details = {"mode": "Paper Trading", "capital": "$200.00"}
        result = await notifier.send_system_notification("startup", details)
        assert result is True

        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        assert "*系统事件*" in message
        assert "事件: startup" in message
        assert "*详情:*" in message
        assert "mode: Paper Trading" in message
        assert "capital: $200.00" in message

    @pytest.mark.asyncio
    async def test_send_system_notification_without_details(
        self,
        notifier: TelegramNotifier,
        mock_client: MagicMock,
    ) -> None:
        """Test system notification without details."""
        result = await notifier.send_system_notification("shutdown")
        assert result is True

        call_args = mock_client._bot.send_message.call_args
        message = call_args.kwargs["text"]
        assert "*系统事件*" in message
        assert "事件: shutdown" in message
        assert "*详情:*" not in message

    def test_format_trade_message_filled(
        self,
        notifier: TelegramNotifier,
        sample_trade: Trade,
        sample_market: Market,
    ) -> None:
        """Test trade message formatting for filled trade."""
        message = notifier._format_trade_message(sample_trade, sample_market)
        assert "*交易执行*" in message
        assert "Will Trump win 2028?" in message
        assert "BUY_YES" in message
        assert "$10.00" in message
        assert "0.6500" in message
        assert "15.38" in message
        assert "\u2705" in message  # Check mark emoji for FILLED
        assert "FILLED" in message

    def test_format_trade_message_pending(
        self,
        notifier: TelegramNotifier,
        sample_market: Market,
    ) -> None:
        """Test trade message formatting for pending trade."""
        trade = Trade(
            id=1,
            market_id="market-1",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=10.0,
            price=0.65,
            shares=15.38,
            status=TradeStatus.PENDING,
        )
        message = notifier._format_trade_message(trade, sample_market)
        assert "\u274c" in message  # X mark emoji for non-FILLED
        assert "PENDING" in message

    def test_format_analysis_message(
        self,
        notifier: TelegramNotifier,
        sample_prediction: PredictionResult,
        sample_market: Market,
    ) -> None:
        """Test analysis message formatting."""
        message = notifier._format_analysis_message(sample_prediction, sample_market)
        assert "*市场分析*" in message
        assert "Will Trump win 2028?" in message
        assert "YES 0.65" in message  # Market price
        assert "YES 0.75" in message  # Predicted probability
        assert "85%" in message  # Confidence
        assert "20%" in message  # Edge
        assert "BUY_YES" in message
        assert "*关键假设:*" in message
        assert "- Economy stable" in message
        assert "- No major news" in message

    def test_format_analysis_message_limits_assumptions(
        self,
        notifier: TelegramNotifier,
        sample_market: Market,
    ) -> None:
        """Test analysis message limits assumptions to 3."""
        prediction = PredictionResult(
            predicted_probability=0.75,
            confidence=0.85,
            reasoning="Strong indicators",
            key_assumptions=["A", "B", "C", "D", "E"],
            recommendation=Recommendation.BUY_YES,
            edge=0.20,
        )
        message = notifier._format_analysis_message(prediction, sample_market)
        assert "- A" in message
        assert "- B" in message
        assert "- C" in message
        assert "- D" not in message  # Should be limited to 3
        assert "- E" not in message

    def test_format_error_message_exception(
        self,
        notifier: TelegramNotifier,
    ) -> None:
        """Test error message formatting with exception."""
        error = ValueError("Test error")
        message = notifier._format_error_message(error)

        assert "*错误告警*" in message
        assert "类型: ValueError" in message
        assert "信息: Test error" in message
        assert "时间:" in message

    def test_format_error_message_string(
        self,
        notifier: TelegramNotifier,
    ) -> None:
        """Test error message formatting with string."""
        message = notifier._format_error_message("Simple error")

        assert "*错误告警*" in message
        assert "类型: Error" in message
        assert "信息: Simple error" in message
        assert "时间:" in message

    def test_format_system_message_with_details(
        self,
        notifier: TelegramNotifier,
    ) -> None:
        """Test system message formatting with details."""
        details = {"key1": "value1", "key2": "value2"}
        message = notifier._format_system_message("startup", details)

        assert "*系统事件*" in message
        assert "事件: startup" in message
        assert "时间:" in message
        assert "*详情:*" in message
        assert "- key1: value1" in message
        assert "- key2: value2" in message

    def test_format_system_message_without_details(
        self,
        notifier: TelegramNotifier,
    ) -> None:
        """Test system message formatting without details."""
        message = notifier._format_system_message("shutdown", None)

        assert "*系统事件*" in message
        assert "事件: shutdown" in message
        assert "时间:" in message
        assert "*详情:*" not in message

    def test_format_system_message_empty_details(
        self,
        notifier: TelegramNotifier,
    ) -> None:
        """Test system message formatting with empty details."""
        message = notifier._format_system_message("test", {})

        assert "*系统事件*" in message
        assert "事件: test" in message
        assert "*详情:*" not in message  # Empty dict should not show details section
