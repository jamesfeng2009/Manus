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
    "o1": {"input": 0.015, "output": 0.06},
    "o3": {"input": 0.01, "output": 0.04},
    "o4-mini": {"input": 0.0004, "output": 0.0016},
    "claude-sonnet-4": {"input": 0.003, "output": 0.015},
    "claude-opus-4": {"input": 0.015, "output": 0.075},
    "claude-haiku-4": {"input": 0.00025, "output": 0.00125},
    "deepseek-chat": {"input": 0.00014, "output": 0.00028},
    "deepseek-v3": {"input": 0.00027, "output": 0.0011},
    "deepseek-r1": {"input": 0.00055, "output": 0.0022},
    "qwen-turbo": {"input": 0.0002, "output": 0.0006},
    "qwen-plus": {"input": 0.0004, "output": 0.0012},
    "qwen-max": {"input": 0.002, "output": 0.006},
    "qwen2.5": {"input": 0.0002, "output": 0.0006},
    "kimi-chat": {"input": 0.0003, "output": 0.0006},
    "glm-4": {"input": 0.0001, "output": 0.0003},
    "glm-4-plus": {"input": 0.0005, "output": 0.0015},
    "doubao-pro": {"input": 0.0003, "output": 0.0006},
    "doubao-lite": {"input": 0.00005, "output": 0.0001},
    "hunyuan-pro": {"input": 0.0002, "output": 0.0005},
    "gemini-2.0-flash": {"input": 0.0, "output": 0.0},
    "gemini-2.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-2.5-flash": {"input": 0.000075, "output": 0.0003},
    "grok-3": {"input": 0.003, "output": 0.015},
    "mistral-large": {"input": 0.002, "output": 0.006},
    "command-r-plus": {"input": 0.003, "output": 0.015},
}

FALLBACK_PRICING: ModelPricing = {"input": 0.001, "output": 0.001}


def _load_pricing() -> dict[str, ModelPricing]:
    pricing = CURRENT_MODELS.copy()
    
    config_path = os.getenv("MODEL_PRICING_CONFIG")
    if config_path and os.path.exists(config_path):
        with open(config_path, "r") as f:
            custom = json.load(f)
            pricing.update(custom)
    
    env_overrides = os.getenv("MODEL_PRICING_OVERRIDE")
    if env_overrides:
        overrides = json.loads(env_overrides)
        pricing.update(overrides)
    
    return pricing


class CostCalculator:
    _pricing_cache: dict[str, ModelPricing] | None = None
    _unknown_models: set = set()

    @classmethod
    def get_price(cls, provider: str, model: str) -> ModelPricing | None:
        if cls._pricing_cache is None:
            cls._pricing_cache = _load_pricing()
        
        key = model.lower()
        
        if key not in cls._pricing_cache and key not in cls._unknown_models:
            cls._unknown_models.add(key)
            print(f"[Warning] Unknown model pricing: {model}")
        
        return cls._pricing_cache.get(key)

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
        pricing = cls.get_price(provider, model) or FALLBACK_PRICING
        prompt_cost = (prompt_tokens / 1000) * pricing["input"]
        completion_cost = (completion_tokens / 1000) * pricing["output"]
        return prompt_cost + completion_cost

    @classmethod
    def reload_pricing(cls):
        cls._pricing_cache = None
        cls._unknown_models.clear()
