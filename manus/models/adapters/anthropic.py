"""Anthropic (Claude) model adapter."""

from typing import Any, AsyncGenerator

from manus.core.types import Message, ModelInfo, ProviderInfo
from manus.models.base import ModelAdapter


class AnthropicAdapter(ModelAdapter):
    """Anthropic Claude API adapter."""

    def _get_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
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
        url = f"{self.base_url}/messages"

        system_message = ""
        filtered_messages = []
        for msg in messages:
            if msg.role.value == "system":
                system_message = msg.content
            else:
                filtered_messages.append(msg)

        payload = {
            "model": self.model.id,
            "messages": [self._format_message(m) for m in filtered_messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if system_message:
            payload["system"] = system_message

        if tools:
            payload["tools"] = tools

        response = await self._make_request("POST", url, json=payload)
        return self.parse_response(response)

    async def chat_stream(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/messages"

        system_message = ""
        filtered_messages = []
        for msg in messages:
            if msg.role.value == "system":
                system_message = msg.content
            else:
                filtered_messages.append(msg)

        payload = {
            "model": self.model.id,
            "messages": [self._format_message(m) for m in filtered_messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if system_message:
            payload["system"] = system_message

        if tools:
            payload["tools"] = tools

        headers = self._get_headers()
        import httpx
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST", url, json=payload, headers=headers
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            import json
                            chunk = json.loads(data)
                            if chunk.get("type") == "content_block_delta":
                                delta = chunk.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")
                        except Exception:
                            continue

    def _format_message(self, message: Message) -> dict[str, Any]:
        return {
            "role": message.role.value,
            "content": message.content,
        }

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Parse Anthropic response to standard format."""
        content_blocks = response.get("content", [])
        content = ""
        tool_calls = []

        for block in content_blocks:
            if block.get("type") == "text":
                content += block.get("text", "")
            elif block.get("type") == "tool_use":
                tool_calls.append({
                    "id": block.get("id"),
                    "type": "function",
                    "function": {
                        "name": block.get("name"),
                        "arguments": block.get("input"),
                    }
                })

        result = {
            "content": content,
            "role": "assistant",
            "finish_reason": response.get("stop_reason"),
        }

        if tool_calls:
            result["tool_calls"] = tool_calls

        return result
