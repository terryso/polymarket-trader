"""Tests for TelegramClient.

This module tests the Telegram API client including:
- Client initialization
- Connection verification (get_me)
- Error handling
- Token masking
- Chat ID authorization

Story 9.1: Telegram Bot 配置与初始化
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import User
from telegram.error import (
    InvalidToken,
    NetworkError as TelegramNetworkError,
    TelegramError,
)

from src.api.telegram import TelegramClient
from src.exceptions import ConfigurationError, NetworkError


@pytest.fixture
def mock_settings_disabled() -> MagicMock:
    """Create mock settings with Telegram disabled."""
    mock = MagicMock()
    mock.telegram.bot_token = None
    mock.telegram.chat_id = None
    mock.telegram.enabled = False
    return mock


@pytest.fixture
def mock_settings_enabled() -> MagicMock:
    """Create mock settings with Telegram enabled."""
    mock = MagicMock()
    mock.telegram.bot_token = "test-token-1234567890:ABC-DEF"
    mock.telegram.chat_id = "123456789"
    mock.telegram.enabled = True
    return mock


@pytest.fixture
def mock_user() -> MagicMock:
    """Create mock Telegram User."""
    user = MagicMock(spec=User)
    user.username = "test_bot"
    user.first_name = "Test Bot"
    user.id = 123456789
    return user


class TestTelegramClientInit:
    """Tests for TelegramClient initialization."""

    def test_init_disabled(self, mock_settings_disabled: MagicMock) -> None:
        """Test initialization when Telegram is disabled."""
        with patch("src.api.telegram.settings", mock_settings_disabled):
            client = TelegramClient()
            assert client._enabled is False
            assert client._token is None
            assert client._chat_id is None

    def test_init_enabled(self, mock_settings_enabled: MagicMock) -> None:
        """Test initialization when Telegram is enabled."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            client = TelegramClient()
            assert client._enabled is True
            assert client._token == "test-token-1234567890:ABC-DEF"
            assert client._chat_id == "123456789"

    def test_init_logs_masked_token(self, mock_settings_enabled: MagicMock) -> None:
        """Test that token is masked in logs."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            with patch("src.api.telegram.get_logger") as mock_logger:
                mock_log = MagicMock()
                mock_logger.return_value = mock_log
                TelegramClient()

                # Check that info was called with masked token
                info_call = mock_log.info.call_args[0][0]
                # Token "test-token-1234567890:ABC-DEF" masked as "test****-DEF"
                assert "test****-DEF" in info_call
                # Full token should not appear
                assert "test-token-1234567890:ABC-DEF" not in info_call


class TestTelegramClientMaskToken:
    """Tests for _mask_token method."""

    def test_mask_token_normal(self, mock_settings_disabled: MagicMock) -> None:
        """Test masking normal length token."""
        with patch("src.api.telegram.settings", mock_settings_disabled):
            client = TelegramClient()
            # Standard bot token format: "1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
            # First 4 = "1234", Last 4 = "w11" (wait, last 4 is "ew11")
            result = client._mask_token("1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
            assert result == "1234****ew11"
            assert "567890" not in result
            assert "ABC-DEF" not in result

    def test_mask_token_short(self, mock_settings_disabled: MagicMock) -> None:
        """Test masking short token."""
        with patch("src.api.telegram.settings", mock_settings_disabled):
            client = TelegramClient()
            result = client._mask_token("short")
            assert result == "****"

    def test_mask_token_empty(self, mock_settings_disabled: MagicMock) -> None:
        """Test masking empty token."""
        with patch("src.api.telegram.settings", mock_settings_disabled):
            client = TelegramClient()
            result = client._mask_token("")
            assert result == "[NOT_SET]"

    def test_mask_token_none(self, mock_settings_disabled: MagicMock) -> None:
        """Test masking None token."""
        with patch("src.api.telegram.settings", mock_settings_disabled):
            client = TelegramClient()
            result = client._mask_token(None)  # type: ignore
            assert result == "[NOT_SET]"

    def test_mask_token_8_chars(self, mock_settings_disabled: MagicMock) -> None:
        """Test masking token with exactly 8 characters."""
        with patch("src.api.telegram.settings", mock_settings_disabled):
            client = TelegramClient()
            # Token of exactly 8 chars is considered too short to meaningfully mask
            result = client._mask_token("12345678")
            assert result == "****"

    def test_mask_token_9_chars(self, mock_settings_disabled: MagicMock) -> None:
        """Test masking token with exactly 9 characters (boundary case)."""
        with patch("src.api.telegram.settings", mock_settings_disabled):
            client = TelegramClient()
            # Token of 9 chars shows first 4 and last 4
            result = client._mask_token("123456789")
            assert result == "1234****6789"


class TestTelegramClientInitialize:
    """Tests for initialize method."""

    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_settings_enabled: MagicMock) -> None:
        """Test successful initialization."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            with patch("src.api.telegram.Application") as mock_app:
                mock_instance = AsyncMock()
                mock_app.builder.return_value.token.return_value.build.return_value = (
                    mock_instance
                )
                mock_bot = MagicMock()
                mock_instance.bot = mock_bot

                client = TelegramClient()
                await client.initialize()

                mock_instance.initialize.assert_called_once()
                assert client._application == mock_instance
                assert client._bot == mock_bot

    @pytest.mark.asyncio
    async def test_initialize_disabled_skip(
        self, mock_settings_disabled: MagicMock
    ) -> None:
        """Test initialization is skipped when disabled."""
        with patch("src.api.telegram.settings", mock_settings_disabled):
            client = TelegramClient()
            await client.initialize()

            # Should not create application
            assert client._application is None
            assert client._bot is None

    @pytest.mark.asyncio
    async def test_initialize_invalid_token(
        self, mock_settings_enabled: MagicMock
    ) -> None:
        """Test initialization with invalid token raises ConfigurationError."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            with patch("src.api.telegram.Application") as mock_app:
                mock_instance = AsyncMock()
                mock_instance.initialize.side_effect = InvalidToken()
                mock_app.builder.return_value.token.return_value.build.return_value = (
                    mock_instance
                )

                client = TelegramClient()
                with pytest.raises(ConfigurationError) as exc_info:
                    await client.initialize()

                assert "Invalid Telegram bot token" in str(exc_info.value)
                assert exc_info.value.config_key == "TELEGRAM_BOT_TOKEN"

    @pytest.mark.asyncio
    async def test_initialize_network_error(
        self, mock_settings_enabled: MagicMock
    ) -> None:
        """Test initialization with network error raises NetworkError."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            with patch("src.api.telegram.Application") as mock_app:
                mock_instance = AsyncMock()
                mock_instance.initialize.side_effect = TelegramNetworkError(
                    "Network failed"
                )
                mock_app.builder.return_value.token.return_value.build.return_value = (
                    mock_instance
                )

                client = TelegramClient()
                with pytest.raises(NetworkError) as exc_info:
                    await client.initialize()

                assert "Telegram network error" in str(exc_info.value)
                assert exc_info.value.endpoint == "initialize"

    @pytest.mark.asyncio
    async def test_initialize_telegram_error(
        self, mock_settings_enabled: MagicMock
    ) -> None:
        """Test initialization with generic Telegram error raises NetworkError."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            with patch("src.api.telegram.Application") as mock_app:
                mock_instance = AsyncMock()
                mock_instance.initialize.side_effect = TelegramError("API error")
                mock_app.builder.return_value.token.return_value.build.return_value = (
                    mock_instance
                )

                client = TelegramClient()
                with pytest.raises(NetworkError) as exc_info:
                    await client.initialize()

                assert "Telegram API error" in str(exc_info.value)


class TestTelegramClientShutdown:
    """Tests for shutdown method."""

    @pytest.mark.asyncio
    async def test_shutdown_success(self, mock_settings_enabled: MagicMock) -> None:
        """Test successful shutdown."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            with patch("src.api.telegram.Application") as mock_app:
                mock_instance = AsyncMock()
                mock_app.builder.return_value.token.return_value.build.return_value = (
                    mock_instance
                )

                client = TelegramClient()
                await client.initialize()
                await client.shutdown()

                mock_instance.shutdown.assert_called_once()
                assert client._application is None
                assert client._bot is None

    @pytest.mark.asyncio
    async def test_shutdown_no_application(
        self, mock_settings_disabled: MagicMock
    ) -> None:
        """Test shutdown when no application exists."""
        with patch("src.api.telegram.settings", mock_settings_disabled):
            client = TelegramClient()
            # Should not raise error
            await client.shutdown()
            assert client._application is None

    @pytest.mark.asyncio
    async def test_shutdown_handles_exception(
        self, mock_settings_enabled: MagicMock
    ) -> None:
        """Test shutdown handles exceptions gracefully."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            with patch("src.api.telegram.Application") as mock_app:
                mock_instance = AsyncMock()
                mock_instance.shutdown.side_effect = Exception("Shutdown error")
                mock_app.builder.return_value.token.return_value.build.return_value = (
                    mock_instance
                )

                client = TelegramClient()
                await client.initialize()
                # Should not raise error
                await client.shutdown()

                assert client._application is None


class TestTelegramClientContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_success(
        self, mock_settings_enabled: MagicMock
    ) -> None:
        """Test async context manager initializes and shuts down."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            with patch("src.api.telegram.Application") as mock_app:
                mock_instance = AsyncMock()
                mock_app.builder.return_value.token.return_value.build.return_value = (
                    mock_instance
                )

                async with TelegramClient() as client:
                    mock_instance.initialize.assert_called_once()
                    assert client._bot is not None

                mock_instance.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_disabled(
        self, mock_settings_disabled: MagicMock
    ) -> None:
        """Test async context manager when disabled."""
        with patch("src.api.telegram.settings", mock_settings_disabled):
            async with TelegramClient() as client:
                assert client._application is None
                assert client._bot is None


class TestTelegramClientGetMe:
    """Tests for get_me method."""

    @pytest.mark.asyncio
    async def test_get_me_success(
        self, mock_settings_enabled: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test successful get_me call."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            client = TelegramClient()
            # Manually set up bot mock
            mock_bot = AsyncMock()
            mock_bot.get_me.return_value = mock_user
            client._bot = mock_bot
            client._enabled = True

            result = await client.get_me()

            assert result == mock_user
            assert result.username == "test_bot"
            mock_bot.get_me.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_me_not_enabled(self, mock_settings_disabled: MagicMock) -> None:
        """Test get_me when client not enabled."""
        with patch("src.api.telegram.settings", mock_settings_disabled):
            client = TelegramClient()
            result = await client.get_me()

            assert result is None

    @pytest.mark.asyncio
    async def test_get_me_not_initialized(
        self, mock_settings_enabled: MagicMock
    ) -> None:
        """Test get_me when client not initialized."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            client = TelegramClient()
            client._enabled = True
            client._bot = None

            result = await client.get_me()

            assert result is None

    @pytest.mark.asyncio
    async def test_get_me_network_error(self, mock_settings_enabled: MagicMock) -> None:
        """Test get_me with network error raises NetworkError."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            client = TelegramClient()
            mock_bot = AsyncMock()
            mock_bot.get_me.side_effect = TelegramNetworkError("Network failed")
            client._bot = mock_bot
            client._enabled = True

            with pytest.raises(NetworkError) as exc_info:
                await client.get_me()

            assert "Telegram network error" in str(exc_info.value)
            assert exc_info.value.endpoint == "get_me"

    @pytest.mark.asyncio
    async def test_get_me_telegram_error(
        self, mock_settings_enabled: MagicMock
    ) -> None:
        """Test get_me with Telegram error raises NetworkError."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            client = TelegramClient()
            mock_bot = AsyncMock()
            mock_bot.get_me.side_effect = TelegramError("API error")
            client._bot = mock_bot
            client._enabled = True

            with pytest.raises(NetworkError) as exc_info:
                await client.get_me()

            assert "Telegram API error" in str(exc_info.value)


class TestTelegramClientIsAuthorizedChat:
    """Tests for is_authorized_chat method."""

    def test_is_authorized_chat_match(self, mock_settings_enabled: MagicMock) -> None:
        """Test authorized chat ID matches."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            client = TelegramClient()
            assert client.is_authorized_chat("123456789") is True
            assert client.is_authorized_chat(123456789) is True

    def test_is_authorized_chat_no_match(
        self, mock_settings_enabled: MagicMock
    ) -> None:
        """Test unauthorized chat ID does not match."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            client = TelegramClient()
            assert client.is_authorized_chat("987654321") is False
            assert client.is_authorized_chat(987654321) is False

    def test_is_authorized_chat_no_restriction(
        self, mock_settings_disabled: MagicMock
    ) -> None:
        """Test all chats authorized when no restriction."""
        with patch("src.api.telegram.settings", mock_settings_disabled):
            client = TelegramClient()
            # No chat_id restriction means all chats are authorized
            assert client.is_authorized_chat("123456789") is True
            assert client.is_authorized_chat("any_chat_id") is True
            assert client.is_authorized_chat(999999999) is True


class TestTelegramClientProperties:
    """Tests for property methods."""

    def test_is_enabled_true(self, mock_settings_enabled: MagicMock) -> None:
        """Test is_enabled property returns True when enabled and initialized."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            client = TelegramClient()
            client._bot = AsyncMock()  # Simulate initialized

            assert client.is_enabled is True

    def test_is_enabled_false_not_enabled(
        self, mock_settings_disabled: MagicMock
    ) -> None:
        """Test is_enabled property returns False when not enabled."""
        with patch("src.api.telegram.settings", mock_settings_disabled):
            client = TelegramClient()

            assert client.is_enabled is False

    def test_is_enabled_false_not_initialized(
        self, mock_settings_enabled: MagicMock
    ) -> None:
        """Test is_enabled property returns False when not initialized."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            client = TelegramClient()
            # bot is None by default

            assert client.is_enabled is False

    def test_authorized_chat_id(self, mock_settings_enabled: MagicMock) -> None:
        """Test authorized_chat_id property."""
        with patch("src.api.telegram.settings", mock_settings_enabled):
            client = TelegramClient()

            assert client.authorized_chat_id == "123456789"

    def test_authorized_chat_id_none(self, mock_settings_disabled: MagicMock) -> None:
        """Test authorized_chat_id property when None."""
        with patch("src.api.telegram.settings", mock_settings_disabled):
            client = TelegramClient()

            assert client.authorized_chat_id is None
