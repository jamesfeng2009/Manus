"""Tencent (HunYuan) model adapter."""

import hashlib
import hmac
import time
from typing import Any, AsyncGenerator

from manus.core.types import Message
from manus.models.base import ModelAdapter


class HunYuanAdapter(ModelAdapter):
    """Tencent HunYuan API adapter.

    HunYuan uses Tencent Cloud API with signature authentication.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
        }

    def _generate_signature(self) -> str:
        timestamp = str(int(time.time()))
        return timestamp

    async def chat(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        url = self.base_url

        payload = {
            "Model": self.model.id,
            "Messages": [self._format_message(m) for m in messages],
            "Temperature": temperature,
            "MaxTokens": max_tokens,
        }

        if tools:
            payload["Tools"] = tools

        headers = self._get_headers()
        headers["X-Action"] = "ChatCompletions"
        headers["X-Version"] = "2023-09-01"
        headers["X-Timestamp"] = str(int(time.time()))

        response = await self._make_request(
            "POST", url, json=payload, headers=headers
        )
        return self.parse_response(response)

    async def chat_stream(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError("HunYuan streaming not implemented")

    def _format_message(self, message: Message) -> dict[str, Any]:
        role_map = {
            "system": "system",
            "user": "user",
            "assistant": "assistant",
            "tool": "tool",
        }
        return {
            "Role": role_map.get(message.role.value, "user"),
            "Content": message.content,
        }

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Parse HunYuan response to standard format."""
        choice = response.get("Choices", [{}])[0]
        message = choice.get("Message", {})

        result = {
            "content": message.get("Content", ""),
            "role": message.get("Role", "assistant"),
            "finish_reason": choice.get("FinishReason"),
        }

        return result
