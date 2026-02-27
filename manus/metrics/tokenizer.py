"""Token counter using tiktoken for estimation."""

ENCODING_MAP = {
    "gpt-4o": "o200k_base",
    "gpt-4o-mini": "o200k_base",
    "o1": "o200k_base",
    "o3": "o200k_base",
    "o4": "o200k_base",
    "claude-sonnet": "cl100k_base",
    "claude-opus": "cl100k_base",
    "claude-haiku": "cl100k_base",
    "deepseek": "cl100k_base",
    "deepseek-v3": "cl100k_base",
    "deepseek-r1": "cl100k_base",
    "qwen": "cl100k_base",
    "qwen2": "cl100k_base",
    "gemini": "cl100k_base",
    "gemini-2": "cl100k_base",
    "gemini-2.5": "cl100k_base",
    "glm": "cl100k_base",
    "doubao": "cl100k_base",
    "hunyuan": "cl100k_base",
    "kimi": "cl100k_base",
    "moonshot": "cl100k_base",
    "grok": "cl100k_base",
    "grok-3": "cl100k_base",
    "mistral": "cl100k_base",
    "command-r": "cl100k_base",
}


class TokenCounter:
    _encodings: dict = {}

    @classmethod
    def _get_encoding(cls, model: str) -> str:
        model_lower = model.lower()
        for key, encoding in ENCODING_MAP.items():
            if key in model_lower:
                return encoding
        return "cl100k_base"

    @classmethod
    def count(cls, text: str, model: str = "gpt-4o") -> int:
        encoding_name = cls._get_encoding(model)

        try:
            import tiktoken
        except ImportError:
            return len(text) // 4

        if encoding_name not in cls._encodings:
            cls._encodings[encoding_name] = tiktoken.get_encoding(encoding_name)

        encoding = cls._encodings[encoding_name]
        return len(encoding.encode(text))

    @classmethod
    def count_messages(cls, messages: list[dict], model: str = "gpt-4o") -> int:
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += cls.count(content, model)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            total += cls.count(item.get("text", ""), model)
                        elif item.get("type") == "image_url":
                            total += 85
        total += len(messages) * 4
        return total

    @classmethod
    def estimate_cost(
        cls,
        text: str,
        model: str,
        prompt_or_completion: str = "prompt",
    ) -> float:
        from manus.metrics.cost import CostCalculator

        tokens = cls.count(text, model)
        if prompt_or_completion == "prompt":
            return CostCalculator.calculate_cost("", model, tokens, 0)
        else:
            return CostCalculator.calculate_cost("", model, 0, tokens)
