"""Google (Gemini) model adapter."""

import json
from typing import Any, AsyncGenerator

from manus.core.types import Message
from manus.models.base import ModelAdapter


class GoogleAdapter(ModelAdapter):
    """Google Gemini API adapter."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_headers(self) -> dict[str, str]:
        return {
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
        url = f"{self.base_url}/models/{self.model.id}:generateContent"

        contents = self._convert_messages(messages)

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        if tools:
            payload["tools"] = tools

        if kwargs.get("response_format") == "json":
            payload["generationConfig"]["responseMimeType"] = "application/json"

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
        url = f"{self.base_url}/models/{self.model.id}:streamGenerateContent"

        contents = self._convert_messages(messages)

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "stream": True,
            },
        }

        headers = self._get_headers()
        import httpx
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST", url, json=payload, headers=headers
            ) as response:
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            content = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            if content:
                                yield content
                        except Exception:
                            continue

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        contents = []
        for msg in messages:
            if msg.role.value == "system":
                continue
            role = "user" if msg.role.value in ("user", "system") else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg.content}],
            })
        return contents

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Parse Gemini response to standard format."""
        candidate = response.get("candidates", [{}])[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])

        content_text = ""
        for part in parts:
            if "text" in part:
                content_text += part["text"]

        finish_reason = candidate.get("finishReason")

        result = {
            "content": content_text,
            "role": "assistant",
            "finish_reason": finish_reason,
        }

        return result
