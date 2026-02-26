"""ByteDance (Doubao) model adapter."""

from typing import Any, AsyncGenerator

from manus.core.types import Message
from manus.models.adapters.openai import OpenAIAdapter


class DoubaoAdapter(OpenAIAdapter):
    """ByteDance Doubao API adapter.

    Doubao uses OpenAI-compatible API.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model.id,
            "messages": [self._format_message(m) for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            payload["tools"] = tools

        if kwargs.get("response_format") == "json":
            payload["response_format"] = {"type": "json_object"}

        response = await self._make_request("POST", url, json=payload)
        return self.parse_response(response)

    def _format_message(self, message: Message) -> dict[str, Any]:
        result = {
            "role": message.role.value,
            "content": message.content,
        }
        if message.tool_calls:
            result["tool_calls"] = message.tool_calls
        if message.tool_call_id:
            result["tool_call_id"] = message.tool_call_id
        return result
