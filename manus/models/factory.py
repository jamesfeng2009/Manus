"""Model factory for creating model adapters."""

from typing import Any

from manus.config import get_config
from manus.core.exceptions import ModelError
from manus.core.types import ModelInfo, ProviderInfo
from manus.models.adapters.anthropic import AnthropicAdapter
from manus.models.adapters.deepseek import DeepSeekAdapter
from manus.models.adapters.doubao import DoubaoAdapter
from manus.models.adapters.glm import GLMAdapter
from manus.models.adapters.google import GoogleAdapter
from manus.models.adapters.hunyuan import HunYuanAdapter
from manus.models.adapters.kimi import KimiAdapter
from manus.models.adapters.minimax import MiniMaxAdapter
from manus.models.adapters.openai import OpenAIAdapter
from manus.models.adapters.qwen import QwenAdapter
from manus.models.base import ModelAdapter

ADAPTER_REGISTRY: dict[str, type[ModelAdapter]] = {
    "openai": OpenAIAdapter,
    "anthropic": AnthropicAdapter,
    "deepseek": DeepSeekAdapter,
    "qwen": QwenAdapter,
    "kimi": KimiAdapter,
    "minimax": MiniMaxAdapter,
    "glm": GLMAdapter,
    "doubao": DoubaoAdapter,
    "hunyuan": HunYuanAdapter,
    "google": GoogleAdapter,
}


def register_adapter(provider: str, adapter_class: type[ModelAdapter]) -> None:
    """Register a new adapter."""
    ADAPTER_REGISTRY[provider.lower()] = adapter_class


class ModelFactory:
    """Factory for creating model adapters."""

    def __init__(self):
        self._adapters: dict[str, ModelAdapter] = {}
        self._config = get_config()

    def get_adapter(self, model_id: str) -> ModelAdapter:
        """Get or create adapter for a model."""
        if model_id in self._adapters:
            return self._adapters[model_id]

        result = self._config.get_model(model_id)
        if not result:
            raise ModelError(f"Model not found: {model_id}")

        provider, model = result
        adapter_class = ADAPTER_REGISTRY.get(provider.provider)

        if not adapter_class:
            raise ModelError(f"No adapter for provider: {provider.provider}")

        adapter = adapter_class(provider=provider, model=model)
        self._adapters[model_id] = adapter
        return adapter

    def create_adapter(
        self,
        provider: str,
        model_id: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> ModelAdapter:
        """Create a new adapter with custom configuration."""
        provider_info = self._config.get_provider(provider)
        if not provider_info:
            raise ModelError(f"Provider not found: {provider}")

        model_info = None
        for m in provider_info.models:
            if m.id == model_id:
                model_info = m
                break

        if not model_info:
            raise ModelError(f"Model not found: {model_id}")

        adapter_class = ADAPTER_REGISTRY.get(provider)
        if not adapter_class:
            raise ModelError(f"No adapter for provider: {provider}")

        return adapter_class(
            provider=provider_info,
            model=model_info,
            api_key=api_key,
            base_url=base_url,
        )

    def list_available_models(self) -> list[str]:
        """List all available model IDs."""
        models = []
        for provider in self._config.models:
            for model in provider.models:
                models.append(model.id)
        return models

    def clear_cache(self) -> None:
        """Clear adapter cache."""
        self._adapters.clear()


_model_factory: ModelFactory | None = None


def get_model_factory() -> ModelFactory:
    """Get global model factory instance."""
    global _model_factory
    if _model_factory is None:
        _model_factory = ModelFactory()
    return _model_factory


def get_adapter(model_id: str) -> ModelAdapter:
    """Get adapter for a model (convenience function)."""
    return get_model_factory().get_adapter(model_id)
