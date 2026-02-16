"""LLM API client for GLM (OpenAI-compatible protocol).

This module provides a typed interface to the GLM API,
which is compatible with OpenAI's chat completion API.

Usage:
    from src.api import LLMClient

    with LLMClient() as client:
        # Simple chat
        response = client.chat([
            {"role": "user", "content": "Hello!"}
        ])

        # Chat with system prompt
        response = client.chat_with_system(
            system_prompt="You are a helpful assistant.",
            user_prompt="What is the capital of France?"
        )
"""

from __future__ import annotations

__all__ = ["LLMClient"]

from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)
from openai.types.chat import ChatCompletionMessageParam

from src.config import settings
from src.exceptions import (
    NetworkError,
)
from src.exceptions import RateLimitError as BotRateLimitError
from src.exceptions import (
    RequestTimeoutError,
)
from src.utils.logger import OPERATION_EMOJIS, get_logger
from src.utils.retry import retry


class LLMClient:
    """LLM API client with retry and error handling.

    Provides methods to interact with GLM API using OpenAI-compatible protocol.
    All API calls are wrapped with retry logic and proper error handling.

    Attributes:
        _client: The underlying OpenAI client instance
        _model: The model name to use
        _timeout: Request timeout in seconds

    Example:
        >>> with LLMClient() as client:
        ...     response = client.chat([{"role": "user", "content": "Hello!"}])
        ...     print(response)
    """

    def __init__(self) -> None:
        """Initialize the LLM client with settings from config."""
        self._logger = get_logger(__name__)

        # Load configuration
        self._api_base = settings.llm.api_base
        self._api_key = settings.llm.api_key
        self._model = settings.llm.model
        self._timeout = settings.llm.timeout

        # Log initialization (with masked API key)
        self._logger.info(
            f"{OPERATION_EMOJIS['network']} Initializing LLM client "
            f"(model={self._model}, api_base={self._api_base}, "
            f"api_key={self._mask_api_key(self._api_key)})"
        )

        # Initialize OpenAI client
        self._client = OpenAI(
            api_key=self._api_key,
            base_url=self._api_base,
            timeout=float(self._timeout),
        )

    def _mask_api_key(self, api_key: str) -> str:
        """Mask API key for logging (show only first and last 4 chars).

        Args:
            api_key: The API key to mask

        Returns:
            Masked API key (e.g., "sk-a****xxxx")
        """
        if not api_key:
            return "[NOT_SET]"
        if len(api_key) <= 8:
            return "****"
        return f"{api_key[:4]}****{api_key[-4:]}"

    def __enter__(self) -> "LLMClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        # OpenAI client doesn't need explicit cleanup
        pass

    @retry(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        exceptions=(NetworkError, BotRateLimitError, RequestTimeoutError),
    )
    def chat(self, messages: list[ChatCompletionMessageParam]) -> str:
        """Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
                Example: [{"role": "user", "content": "Hello!"}]

        Returns:
            The assistant's response text

        Raises:
            NetworkError: If API request fails
            BotRateLimitError: If rate limit is exceeded
            RequestTimeoutError: If request times out
        """
        self._logger.info(
            f"{OPERATION_EMOJIS['analysis']} Sending LLM request "
            f"(model={self._model}, messages={len(messages)})"
        )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
            )

            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else "N/A"
            self._logger.info(
                f"{OPERATION_EMOJIS['analysis']} LLM response received "
                f"(tokens={tokens})"
            )
            return content

        except APITimeoutError as e:
            self._logger.error(f"❌ LLM API timeout: {e}")
            raise RequestTimeoutError(
                message="LLM API request timed out",
                endpoint="chat",
                timeout_seconds=float(self._timeout),
                original_exception=e,
            )
        except RateLimitError as e:
            retry_after = None
            if hasattr(e, "response") and e.response is not None:
                retry_after_str = e.response.headers.get("Retry-After")
                if retry_after_str:
                    try:
                        retry_after = int(retry_after_str)
                    except ValueError:
                        pass
            self._logger.warning(f"⚠️ LLM API rate limit exceeded")
            raise BotRateLimitError(
                message="LLM API rate limit exceeded",
                endpoint="chat",
                retry_after=retry_after,
                original_exception=e,
            )
        except APIConnectionError as e:
            self._logger.error(f"❌ LLM API connection error: {e}")
            raise NetworkError(
                message=f"LLM API connection error: {e}",
                endpoint="chat",
                original_exception=e,
            )
        except APIStatusError as e:
            self._logger.error(f"❌ LLM API error: {e.status_code}")
            raise NetworkError(
                message=f"LLM API error: {e.status_code}",
                endpoint="chat",
                status_code=e.status_code,
                original_exception=e,
            )

    def chat_with_system(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat request with system and user prompts.

        Args:
            system_prompt: System prompt to set the assistant's behavior
            user_prompt: User's question or request

        Returns:
            The assistant's response text

        Example:
            >>> with LLMClient() as client:
            ...     response = client.chat_with_system(
            ...         system_prompt="You are a prediction market analyst.",
            ...         user_prompt="Analyze this market: ..."
            ...     )
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.chat(messages)
