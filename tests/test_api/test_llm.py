"""Tests for LLMClient.

This module tests the LLM API client including:
- Client initialization
- Chat requests
- Error handling
- API key masking
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)

from src.api.llm import LLMClient
from src.exceptions import (
    NetworkError,
    RateLimitError as BotRateLimitError,
    RequestTimeoutError,
)


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings for LLM client."""
    mock = MagicMock()
    mock.llm.api_base = "https://api.example.com/v1"
    mock.llm.api_key = "test-api-key-12345678"
    mock.llm.model = "test-model"
    mock.llm.timeout = 30
    mock.llm.thinking_enabled = True
    return mock


@pytest.fixture
def mock_openai_response() -> MagicMock:
    """Create mock OpenAI response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Test response content"
    response.usage = MagicMock()
    response.usage.total_tokens = 100
    return response


class TestLLMClientInit:
    """Tests for LLMClient initialization."""

    def test_init_success(self, mock_settings: MagicMock) -> None:
        """Test successful LLM client initialization."""
        with patch("src.api.llm.settings", mock_settings):
            with patch("src.api.llm.OpenAI") as mock_openai:
                client = LLMClient()
                assert client._model == "test-model"
                assert client._timeout == 30
                assert client._api_base == "https://api.example.com/v1"
                mock_openai.assert_called_once_with(
                    api_key="test-api-key-12345678",
                    base_url="https://api.example.com/v1",
                    timeout=30.0,
                )

    def test_init_logs_masked_api_key(self, mock_settings: MagicMock) -> None:
        """Test that API key is masked in logs."""
        with patch("src.api.llm.settings", mock_settings):
            with patch("src.api.llm.OpenAI"):
                with patch("src.api.llm.get_logger") as mock_logger:
                    mock_log = MagicMock()
                    mock_logger.return_value = mock_log
                    LLMClient()

                    # Check that the log message contains masked API key
                    log_call = mock_log.info.call_args[0][0]
                    assert "test****5678" in log_call
                    assert "test-api-key-12345678" not in log_call


class TestMaskApiKey:
    """Tests for API key masking."""

    def test_mask_long_key(self) -> None:
        """Test masking a long API key."""
        with patch("src.api.llm.settings") as mock_settings:
            mock_settings.llm.api_base = "https://api.example.com"
            mock_settings.llm.api_key = "test-key"
            mock_settings.llm.model = "test-model"
            mock_settings.llm.timeout = 30
            mock_settings.llm.thinking_enabled = True

            with patch("src.api.llm.OpenAI"):
                client = LLMClient()
                masked = client._mask_api_key("abcdefghijklmnop")
                assert masked == "abcd****mnop"

    def test_mask_short_key(self) -> None:
        """Test masking a short API key."""
        with patch("src.api.llm.settings") as mock_settings:
            mock_settings.llm.api_base = "https://api.example.com"
            mock_settings.llm.api_key = "test-key"
            mock_settings.llm.model = "test-model"
            mock_settings.llm.timeout = 30
            mock_settings.llm.thinking_enabled = True

            with patch("src.api.llm.OpenAI"):
                client = LLMClient()
                masked = client._mask_api_key("short")
                assert masked == "****"

    def test_mask_empty_key(self) -> None:
        """Test masking an empty API key."""
        with patch("src.api.llm.settings") as mock_settings:
            mock_settings.llm.api_base = "https://api.example.com"
            mock_settings.llm.api_key = "test-key"
            mock_settings.llm.model = "test-model"
            mock_settings.llm.timeout = 30
            mock_settings.llm.thinking_enabled = True

            with patch("src.api.llm.OpenAI"):
                client = LLMClient()
                masked = client._mask_api_key("")
                assert masked == "[NOT_SET]"


class TestChat:
    """Tests for chat method."""

    def test_chat_success(
        self,
        mock_settings: MagicMock,
        mock_openai_response: MagicMock,
    ) -> None:
        """Test successful chat request."""
        with patch("src.api.llm.settings", mock_settings):
            with patch("src.api.llm.OpenAI") as mock_openai:
                mock_openai.return_value.chat.completions.create.return_value = (
                    mock_openai_response
                )

                with LLMClient() as client:
                    response = client.chat(
                        [{"role": "user", "content": "Hello!"}]
                    )

                assert response == "Test response content"
                mock_openai.return_value.chat.completions.create.assert_called_once_with(
                    model="test-model",
                    messages=[{"role": "user", "content": "Hello!"}],
                    extra_body={"thinking": {"type": "enabled"}},
                )

    def test_chat_multiple_messages(
        self,
        mock_settings: MagicMock,
        mock_openai_response: MagicMock,
    ) -> None:
        """Test chat with multiple messages."""
        with patch("src.api.llm.settings", mock_settings):
            with patch("src.api.llm.OpenAI") as mock_openai:
                mock_openai.return_value.chat.completions.create.return_value = (
                    mock_openai_response
                )

                messages = [
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "Hello!"},
                    {"role": "assistant", "content": "Hi!"},
                    {"role": "user", "content": "How are you?"},
                ]

                with LLMClient() as client:
                    response = client.chat(messages)

                assert response == "Test response content"

    def test_chat_empty_response(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test chat with empty response content."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 10

        with patch("src.api.llm.settings", mock_settings):
            with patch("src.api.llm.OpenAI") as mock_openai:
                mock_openai.return_value.chat.completions.create.return_value = (
                    mock_response
                )

                with LLMClient() as client:
                    response = client.chat([{"role": "user", "content": "Hello"}])

                assert response == ""

    def test_chat_timeout_error(self, mock_settings: MagicMock) -> None:
        """Test chat timeout error handling."""
        with patch("src.api.llm.settings", mock_settings):
            with patch("src.api.llm.OpenAI") as mock_openai:
                mock_request = MagicMock()
                mock_openai.return_value.chat.completions.create.side_effect = (
                    APITimeoutError(request=mock_request)
                )

                with LLMClient() as client:
                    with pytest.raises(RequestTimeoutError) as exc_info:
                        client.chat([{"role": "user", "content": "Hello"}])

                assert exc_info.value.endpoint == "chat"
                assert exc_info.value.timeout_seconds == 30.0

    def test_chat_rate_limit_error(self, mock_settings: MagicMock) -> None:
        """Test chat rate limit error handling."""
        with patch("src.api.llm.settings", mock_settings):
            with patch("src.api.llm.OpenAI") as mock_openai:
                mock_response = MagicMock()
                mock_response.headers = {"Retry-After": "60"}

                mock_openai.return_value.chat.completions.create.side_effect = (
                    RateLimitError(
                        message="Rate limit exceeded",
                        response=mock_response,
                        body=MagicMock(),
                    )
                )

                with LLMClient() as client:
                    with pytest.raises(BotRateLimitError) as exc_info:
                        client.chat([{"role": "user", "content": "Hello"}])

                assert exc_info.value.endpoint == "chat"
                assert exc_info.value.retry_after == 60

    def test_chat_rate_limit_error_no_retry_after(
        self, mock_settings: MagicMock
    ) -> None:
        """Test chat rate limit error without Retry-After header."""
        with patch("src.api.llm.settings", mock_settings):
            with patch("src.api.llm.OpenAI") as mock_openai:
                mock_response = MagicMock()
                mock_response.headers = {}

                mock_openai.return_value.chat.completions.create.side_effect = (
                    RateLimitError(
                        message="Rate limit exceeded",
                        response=mock_response,
                        body=MagicMock(),
                    )
                )

                with LLMClient() as client:
                    with pytest.raises(BotRateLimitError) as exc_info:
                        client.chat([{"role": "user", "content": "Hello"}])

                assert exc_info.value.retry_after is None

    def test_chat_connection_error(self, mock_settings: MagicMock) -> None:
        """Test chat connection error handling."""
        with patch("src.api.llm.settings", mock_settings):
            with patch("src.api.llm.OpenAI") as mock_openai:
                mock_openai.return_value.chat.completions.create.side_effect = (
                    APIConnectionError(message="Connection failed", request=MagicMock())
                )

                with LLMClient() as client:
                    with pytest.raises(NetworkError) as exc_info:
                        client.chat([{"role": "user", "content": "Hello"}])

                assert exc_info.value.endpoint == "chat"

    def test_chat_api_status_error(self, mock_settings: MagicMock) -> None:
        """Test chat API status error handling."""
        with patch("src.api.llm.settings", mock_settings):
            with patch("src.api.llm.OpenAI") as mock_openai:
                mock_response = MagicMock()
                mock_response.status_code = 500

                mock_openai.return_value.chat.completions.create.side_effect = (
                    APIStatusError(
                        message="Internal server error",
                        response=mock_response,
                        body=MagicMock(),
                    )
                )

                with LLMClient() as client:
                    with pytest.raises(NetworkError) as exc_info:
                        client.chat([{"role": "user", "content": "Hello"}])

                assert exc_info.value.status_code == 500


class TestChatWithSystem:
    """Tests for chat_with_system method."""

    def test_chat_with_system_success(
        self,
        mock_settings: MagicMock,
        mock_openai_response: MagicMock,
    ) -> None:
        """Test successful chat with system prompt."""
        with patch("src.api.llm.settings", mock_settings):
            with patch("src.api.llm.OpenAI") as mock_openai:
                mock_openai.return_value.chat.completions.create.return_value = (
                    mock_openai_response
                )

                with LLMClient() as client:
                    response = client.chat_with_system(
                        system_prompt="You are a helpful assistant.",
                        user_prompt="What is the capital of France?",
                    )

                assert response == "Test response content"

                # Verify messages format
                call_args = mock_openai.return_value.chat.completions.create.call_args
                messages = call_args.kwargs["messages"]
                assert len(messages) == 2
                assert messages[0]["role"] == "system"
                assert messages[0]["content"] == "You are a helpful assistant."
                assert messages[1]["role"] == "user"
                assert messages[1]["content"] == "What is the capital of France?"

    def test_chat_with_system_empty_prompts(
        self,
        mock_settings: MagicMock,
        mock_openai_response: MagicMock,
    ) -> None:
        """Test chat with empty prompts."""
        with patch("src.api.llm.settings", mock_settings):
            with patch("src.api.llm.OpenAI") as mock_openai:
                mock_openai.return_value.chat.completions.create.return_value = (
                    mock_openai_response
                )

                with LLMClient() as client:
                    response = client.chat_with_system(
                        system_prompt="",
                        user_prompt="",
                    )

                assert response == "Test response content"


class TestContextManager:
    """Tests for context manager protocol."""

    def test_context_manager_enter(self, mock_settings: MagicMock) -> None:
        """Test context manager __enter__ method."""
        with patch("src.api.llm.settings", mock_settings):
            with patch("src.api.llm.OpenAI"):
                with LLMClient() as client:
                    assert isinstance(client, LLMClient)

    def test_context_manager_exit(self, mock_settings: MagicMock) -> None:
        """Test context manager __exit__ method."""
        with patch("src.api.llm.settings", mock_settings):
            with patch("src.api.llm.OpenAI"):
                client = LLMClient()
                # __exit__ should not raise
                client.__exit__(None, None, None)


class TestRetry:
    """Tests for retry behavior."""

    def test_retry_on_network_error(
        self,
        mock_settings: MagicMock,
        mock_openai_response: MagicMock,
    ) -> None:
        """Test that retry happens on network errors."""
        with patch("src.api.llm.settings", mock_settings):
            with patch("src.api.llm.OpenAI") as mock_openai:
                # First call fails, second succeeds
                mock_request = MagicMock()
                mock_openai.return_value.chat.completions.create.side_effect = [
                    APIConnectionError(message="Connection failed", request=mock_request),
                    mock_openai_response,
                ]

                # Disable retry delays for testing
                with patch("src.utils.retry.time.sleep"):
                    with LLMClient() as client:
                        response = client.chat([{"role": "user", "content": "Hello"}])

                assert response == "Test response content"
                assert mock_openai.return_value.chat.completions.create.call_count == 2
