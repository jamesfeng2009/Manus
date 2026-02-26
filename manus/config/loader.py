"""Configuration loader for Manus."""

import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from manus.core.constants import CONFIG_DIR, DEFAULT_MODEL_YAML
from manus.core.exceptions import ConfigurationError
from manus.core.types import (
    AppConfig,
    ConfigDefaults,
    ModelInfo,
    ProviderInfo,
)


class ConfigLoader:
    """Load and manage configuration for Manus."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or DEFAULT_MODEL_YAML
        self._config: AppConfig | None = None

    def load(self) -> AppConfig:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise ConfigurationError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        providers = []
        for provider_data in data.get("models", []):
            models = []
            for model_data in provider_data.get("models", []):
                models.append(ModelInfo(**model_data))
            providers.append(
                ProviderInfo(
                    provider=provider_data["provider"],
                    name=provider_data["name"],
                    api_key_env=provider_data["api_key_env"],
                    base_url=provider_data["base_url"],
                    models=models,
                )
            )

        defaults = ConfigDefaults(**data.get("defaults", {}))

        self._config = AppConfig(models=providers, defaults=defaults)
        return self._config

    def get_config(self) -> AppConfig:
        """Get loaded configuration."""
        if self._config is None:
            self._config = self.load()
        return self._config

    def get_provider(self, provider_name: str) -> ProviderInfo | None:
        """Get provider by name."""
        config = self.get_config()
        for provider in config.models:
            if provider.provider == provider_name:
                return provider
        return None

    def get_model(self, model_id: str) -> tuple[ProviderInfo, ModelInfo] | None:
        """Get model and its provider by model ID."""
        config = self.get_config()
        for provider in config.models:
            for model in provider.models:
                if model.id == model_id:
                    return provider, model
        return None

    def get_default_model_id(self) -> str:
        """Get default model ID."""
        return self.get_config().defaults.default_model

    def get_model_for_agent(self, agent_type: str) -> str:
        """Get model ID for specific agent type."""
        defaults = self.get_config().defaults
        model_map = {
            "planner": defaults.planner_model,
            "executor": defaults.executor_model,
            "verifier": defaults.verifier_model,
        }
        return model_map.get(agent_type, defaults.default_model)


def resolve_env_vars(value: str) -> str:
    """Resolve environment variables in a string.

    Supports ${VAR} and $VAR formats.
    """
    if not isinstance(value, str):
        return value

    pattern = r"\$\{(\w+)\}|\$(\w+)"

    def replacer(match):
        var_name = match.group(1) or match.group(2)
        return os.environ.get(var_name, match.group(0))

    return re.sub(pattern, replacer, value)


def load_env_file(env_file: str | Path | None = None) -> None:
    """Load environment variables from .env file."""
    if env_file is None:
        env_file = Path.cwd() / ".env"
    elif isinstance(env_file, str):
        env_file = Path(env_file)

    if env_file.exists():
        load_dotenv(env_file)


_config_loader: ConfigLoader | None = None


def get_config_loader() -> ConfigLoader:
    """Get global config loader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def load_config() -> AppConfig:
    """Load configuration (convenience function)."""
    load_env_file()
    return get_config_loader().load()


def get_config() -> AppConfig:
    """Get configuration (convenience function)."""
    return get_config_loader().get_config()
