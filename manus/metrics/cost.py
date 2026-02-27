"""Cost calculation for different LLM providers."""

import os
import json
from typing import TypedDict


class ModelPricing(TypedDict):
    input: float
    output: float


CURRENT_MODELS: dict[str, ModelPricing] = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o-2025-01-27": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini-2024-07-18": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo-2024-04-09": {"input": 0.01, "output": 0.03},
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    "claude-sonnet-3-5-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-5-sonnet-20240620": {"input": 0.003, "output": 0.015},
    "claude-opus-3-20240229": {"input": 0.015, "output": 0.075},
    "claude-haiku-3-20240307": {"input": 0.00025, "output": 0.00125},
    "deepseek-chat": {"input": 0.00014, "output": 0.00028},
    "deepseek-coder": {"input": 0.00014, "output": 0.00028},
    "deepseek-reasoner": {"input": 0.00014, "output": 0.00028},
    "qwen-turbo": {"input": 0.0002, "output": 0.0006},
    "qwen-plus": {"input": 0.0004, "output": 0.0012},
    "qwen-max": {"input": 0.002, "output": 0.006},
    "qwen-long": {"input": 0.0004, "output": 0.0012},
    "kimi-chat": {"input": 0.0003, "output": 0.0006},
    "moonshot-v1-8k": {"input": 0.0003, "output": 0.0006},
    "moonshot-v1-32k": {"input": 0.0006, "output": 0.0012},
    "moonshot-v1-128k": {"input": 0.001, "output": 0.003},
    "glm-4": {"input": 0.0001, "output": 0.0003},
    "glm-4-flash": {"input": 0.0001, "output": 0.0003},
    "glm-4-flashx": {"input": 0.0001, "output": 0.0003},
    "glm-3-turbo": {"input": 0.0001, "output": 0.0003},
    "doubao-pro-32k": {"input": 0.0003, "output": 0.0006},
    "doubao-lite-32k": {"input": 0.00005, "output": 0.0001},
    "hunyuan-pro": {"input": 0.0002, "output": 0.0005},
    "hunyuan-standard": {"input": 0.0001, "output": 0.00025},
    "gemini-2.0-flash": {"input": 0.0, "output": 0.0},
    "gemini-2.0-flash-lite": {"input": 0.0, "output": 0.0},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-1.5-flash-8b": {"input": 0.0000375, "output": 0.00015},
}

DEFAULT_PRICING: ModelPricing = {"input": 0.001, "output": 0.001}


class CostCalculator:
    _pricing_cache: dict[str, ModelPricing] | None = None

    @classmethod
    def _load_pricing(cls) -> dict[str, ModelPricing]:
        if cls._pricing_cache is not None:
            return cls._pricing_cache

        pricing = CURRENT_MODELS.copy()

        config_path = os.getenv("MODEL_PRICING_CONFIG")
        if config_path and os.path.exists(config_path):
            with open(config_path, "r") as f:
                custom = json.load(f)
                pricing.update(custom)

        cls._pricing_cache = pricing
        return pricing

    @classmethod
    def get_price(cls, provider: str, model: str) -> ModelPricing | None:
        key = model.lower()
        pricing = cls._load_pricing()
        return pricing.get(key)

    @classmethod
    def calculate_cost(
        cls,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        pricing = cls.get_price(provider, model)
        if not pricing:
            return 0.0
        prompt_cost = (prompt_tokens / 1000) * pricing["input"]
        completion_cost = (completion_tokens / 1000) * pricing["output"]
        return prompt_cost + completion_cost

    @classmethod
    def calculate_cost_with_default(
        cls,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        pricing = cls.get_price(provider, model) or DEFAULT_PRICING
        prompt_cost = (prompt_tokens / 1000) * pricing["input"]
        completion_cost = (completion_tokens / 1000) * pricing["output"]
        return prompt_cost + completion_cost

    @classmethod
    def reload_pricing(cls):
        cls._pricing_cache = None
