"""Cost calculation for different LLM providers."""

from typing import TypedDict


class ModelPricing(TypedDict):
    input: float
    output: float


COST_PER_1K_TOKENS: dict[str, ModelPricing] = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "claude-2.1": {"input": 0.008, "output": 0.024},
    "claude-2": {"input": 0.008, "output": 0.024},
    "claude-instant": {"input": 0.00163, "output": 0.00551},
    "deepseek-chat": {"input": 0.00014, "output": 0.00028},
    "deepseek-coder": {"input": 0.00014, "output": 0.00028},
    "qwen-turbo": {"input": 0.0002, "output": 0.0006},
    "qwen-plus": {"input": 0.0004, "output": 0.0012},
    "qwen-max": {"input": 0.002, "output": 0.006},
    "kimi-chat": {"input": 0.0003, "output": 0.0006},
    "moonshot-v1-8k": {"input": 0.0003, "output": 0.0006},
    "moonshot-v1-32k": {"input": 0.0006, "output": 0.0012},
    "moonshot-v1-128k": {"input": 0.001, "output": 0.003},
    "glm-4": {"input": 0.0001, "output": 0.0003},
    "glm-4-flash": {"input": 0.0001, "output": 0.0003},
    "glm-3-turbo": {"input": 0.0001, "output": 0.0003},
    "doubao-pro-32k": {"input": 0.0003, "output": 0.0006},
    "doubao-lite-32k": {"input": 0.00005, "output": 0.0001},
    "hunyuan-pro": {"input": 0.0002, "output": 0.0005},
    "hunyuan-standard": {"input": 0.0001, "output": 0.00025},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-1.5-flash-8b": {"input": 0.0000375, "output": 0.00015},
    "gemini-pro": {"input": 0.00125, "output": 0.005},
}


class CostCalculator:
    """Calculate API usage costs."""

    @staticmethod
    def get_price(provider: str, model: str) -> ModelPricing | None:
        key = model.lower()
        if key in COST_PER_1K_TOKENS:
            return COST_PER_1K_TOKENS[key]
        return None

    @staticmethod
    def calculate_cost(
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        pricing = CostCalculator.get_price(provider, model)
        if not pricing:
            return 0.0
        prompt_cost = (prompt_tokens / 1000) * pricing["input"]
        completion_cost = (completion_tokens / 1000) * pricing["output"]
        return prompt_cost + completion_cost
