"""Base model adapter for LLM providers."""

import os
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

import httpx

from manus.core.exceptions import (
    ModelAuthenticationError,
    ModelError,
    ModelRateLimitError,
    ModelTimeoutError,
)
from manus.core.types import Message, ModelInfo, ProviderInfo


class ModelAdapter(ABC):
    """Base class for LLM model adapters."""

    def __init__(
        self,
        provider: ProviderInfo,
        model: ModelInfo,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 120,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.environ.get(provider.api_key_env, "")
        self.base_url = base_url or provider.base_url
        self.timeout = timeout

        if not self.api_key:
            raise ModelAuthenticationError(
                f"API key not found. Set {provider.api_key_env} environment variable."
            )

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Send chat completion request."""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Send chat completion request with streaming."""
        pass

    @abstractmethod
    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Parse provider response to standard format."""
        pass

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        return {}

    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Make HTTP request with error handling."""
        headers = self._get_headers()
        headers.update(kwargs.pop("headers", {}))

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs,
                )
                return self._handle_response(response)
        except httpx.TimeoutException as e:
            raise ModelTimeoutError(f"Request timeout: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ModelAuthenticationError(f"Authentication failed: {e}")
            elif e.response.status_code == 429:
                raise ModelRateLimitError(f"Rate limit exceeded: {e}")
            raise ModelError(f"HTTP error: {e}")
        except Exception as e:
            raise ModelError(f"Request failed: {e}")

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle HTTP response."""
        if response.status_code != 200:
            if response.status_code == 401:
                raise ModelAuthenticationError("Authentication failed")
            elif response.status_code == 429:
                raise ModelRateLimitError("Rate limit exceeded")
            raise ModelError(f"HTTP {response.status_code}: {response.text}")

        try:
            return response.json()
        except Exception as e:
            raise ModelError(f"Failed to parse response: {e}")

    def supports_vision(self) -> bool:
        """Check if model supports vision."""
        return "vision" in self.model.capabilities

    def supports_json(self) -> bool:
        """Check if model supports JSON mode."""
        return self.model.supports_json
