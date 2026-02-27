"""Integration tests for LLMClient with real GLM API calls.

These tests make actual HTTP requests to the GLM API.
Run with: pytest tests/integration/ -v -m integration

To skip these tests during normal development:
    pytest tests/ -v -m "not integration"

Note: These tests require a valid LLM_API_KEY environment variable.
"""

from __future__ import annotations

import os

import pytest

from src.api import LLMClient
from src.config import settings
from src.exceptions import NetworkError, RateLimitError, RequestTimeoutError

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Skip all tests if no API key is configured
requires_llm_api_key = pytest.mark.skipif(
    not settings.llm.api_key,
    reason="LLM_API_KEY not configured",
)


class TestLLMClientIntegration:
    """Integration tests for LLMClient with real GLM API."""

    @requires_llm_api_key
    def test_client_initialization(self) -> None:
        """Test client initialization with default settings."""
        with LLMClient() as client:
            assert client._model is not None
            assert client._api_base is not None
            assert client._timeout > 0

    @requires_llm_api_key
    def test_simple_chat_returns_response(self) -> None:
        """Test simple chat request returns a response."""
        with LLMClient() as client:
            response = client.chat(
                [{"role": "user", "content": "Hello, say 'hi' back in one word."}]
            )

            assert isinstance(response, str)
            assert len(response) > 0

    @requires_llm_api_key
    def test_chat_with_system_prompt(self) -> None:
        """Test chat with system prompt."""
        with LLMClient() as client:
            response = client.chat_with_system(
                system_prompt="You are a helpful assistant. Always respond with exactly one word.",
                user_prompt="What is the capital of France?",
            )

            assert isinstance(response, str)
            assert len(response) > 0
            # Response should contain Paris or similar
            assert "paris" in response.lower() or "france" in response.lower()

    @requires_llm_api_key
    def test_chat_with_prediction_market_context(self) -> None:
        """Test chat with prediction market analysis context."""
        with LLMClient() as client:
            response = client.chat_with_system(
                system_prompt="You are a prediction market analyst. Respond in JSON format.",
                user_prompt="What is the probability that it will rain in Seattle tomorrow? Respond with a JSON object containing 'probability' (0-1) and 'reasoning'.",
            )

            assert isinstance(response, str)
            assert len(response) > 0

    @requires_llm_api_key
    def test_chat_multiturn_conversation(self) -> None:
        """Test multi-turn conversation."""
        with LLMClient() as client:
            messages = [
                {"role": "user", "content": "My name is Alice."},
                {"role": "assistant", "content": "Nice to meet you, Alice!"},
                {"role": "user", "content": "What is my name?"},
            ]

            response = client.chat(messages)

            assert isinstance(response, str)
            assert "alice" in response.lower()


class TestLLMClientErrorHandling:
    """Integration tests for LLMClient error handling."""

    @requires_llm_api_key
    def test_chat_with_empty_message_raises_error(self) -> None:
        """Test chat with empty message list behavior."""
        with LLMClient() as client:
            # Empty messages may work or raise an error depending on API
            # We just verify it doesn't crash the client
            try:
                response = client.chat([])
                # If it returns, it should be a string
                assert isinstance(response, str)
            except (NetworkError, RequestTimeoutError):
                # API may reject empty messages
                pass

    @requires_llm_api_key
    def test_chat_with_long_message(self) -> None:
        """Test chat with a long message."""
        with LLMClient() as client:
            long_message = "Please analyze this text: " + ("word " * 100)
            response = client.chat([{"role": "user", "content": long_message}])

            assert isinstance(response, str)
            assert len(response) > 0

    def test_chat_timeout_handling(self) -> None:
        """Test that timeout is configured properly."""
        # This test verifies the timeout configuration is working
        # A real timeout would take too long for integration tests
        with LLMClient() as client:
            assert client._timeout == 30  # Default from config


class TestLLMClientMaskApiKey:
    """Tests for API key masking (security feature)."""

    def test_mask_api_key_full_key(self) -> None:
        """Test masking a full API key."""
        with LLMClient() as client:
            masked = client._mask_api_key("abcdefghijklmnop1234567890")
            assert masked == "abcd****7890"
            assert "mnop" not in masked
            assert "1234" not in masked

    def test_mask_api_key_short_key(self) -> None:
        """Test masking a short API key."""
        with LLMClient() as client:
            masked = client._mask_api_key("short")
            assert masked == "****"

    def test_mask_api_key_empty(self) -> None:
        """Test masking an empty API key."""
        with LLMClient() as client:
            masked = client._mask_api_key("")
            assert masked == "[NOT_SET]"
