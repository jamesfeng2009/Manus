"""DeepSeek model adapter."""

from typing import Any, AsyncGenerator

from manus.core.types import Message, ModelInfo, ProviderInfo
from manus.models.base import ModelAdapter


class DeepSeekAdapter(ModelAdapter):
    """DeepSeek API adapter."""

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

    async def chat_stream(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model.id,
            "messages": [self._format_message(m) for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if tools:
            payload["tools"] = tools

        import httpx
        headers = self._get_headers()
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
                            content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                yield content
                        except Exception:
                            continue

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

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Parse DeepSeek response to standard format."""
        choice = response["choices"][0]
        message = choice["message"]

        result = {
            "content": message.get("content", ""),
            "role": message.get("role", "assistant"),
            "finish_reason": choice.get("finish_reason"),
        }

        if message.get("tool_calls"):
            result["tool_calls"] = message["tool_calls"]

        return result
