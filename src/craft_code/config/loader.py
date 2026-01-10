import os
import copy
import tomllib
import tomli_w
from pathlib import Path
from typing import Literal, Dict
from pydantic import BaseModel, Field, HttpUrl, field_validator

# ============================================================================
# Pydantic Models
# ============================================================================


class ModelConfig(BaseModel):
    """Configuration for a specific LLM provider."""

    base_url: str  # Using str instead of HttpUrl for flexibility with local URLs
    model: str = Field(min_length=1)
    api_key: str = Field(default="")

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate base_url format."""
        if not v:
            raise ValueError("base_url cannot be empty")
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v


class Config(BaseModel):
    """Main configuration for Craft Code."""

    provider: Literal["lm_studio", "ollama", "openai", "mistral"]
    models: Dict[str, ModelConfig]

    @field_validator("models")
    @classmethod
    def validate_provider_exists(cls, v: Dict[str, ModelConfig], info) -> Dict[str, ModelConfig]:
        """Ensure selected provider exists in models."""
        # Note: info.data contains already-validated fields
        # We'll check this in a model_validator instead
        return v

    def get_active_model_config(self) -> ModelConfig:
        """Get configuration for the active provider."""
        if self.provider not in self.models:
            raise ValueError(f"Provider '{self.provider}' not found in models configuration")
        return self.models[self.provider]


# ============================================================================
# Default Configuration
# ============================================================================

DEFAULT_CONFIG_DICT = {
    "provider": "lm_studio",
    "models": {
        "lm_studio": {
            "base_url": "http://localhost:1234/v1",
            "model": "qwen/qwen3-4b-2507",
            "api_key": "lm-studio",
        },
        "ollama": {
            "base_url": "http://localhost:11434/v1",
            "model": "qwen3:4b",
            "api_key": "ollama",
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-5",
            "api_key": "",
        },
        "mistral": {
            "base_url": "https://api.mistral.ai/v1",
            "model": "mistral-small-latest",
            "api_key": "",
        },
    },
}

CONFIG_PATH = Path(os.path.expanduser("~/.config/craft-code/config.toml"))


def ensure_config_dir():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_config() -> Config:
    """Load Craft Code configuration, fallback to defaults if missing.

    Returns:
        Validated Config object

    Raises:
        ValueError: If configuration is invalid
    """
    ensure_config_dir()

    if not CONFIG_PATH.exists():
        print(
            "No config file found, using default LM Studio settings. Please run 'craft-code --configure' to set up."
        )
        return Config(**DEFAULT_CONFIG_DICT)

    try:
        with open(CONFIG_PATH, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        print(f"Failed to load config file: {e}. Using defaults.")
        return Config(**DEFAULT_CONFIG_DICT)

    # Deep merge user config with defaults (fill missing parts)
    merged = copy.deepcopy(DEFAULT_CONFIG_DICT)

    # Merge models from user config into defaults
    if "models" in data:
        merged["models"].update(data["models"])

    # Update provider selection
    if "provider" in data:
        merged["provider"] = data["provider"]

    # Validate and return as Pydantic model
    try:
        return Config(**merged)
    except Exception as e:
        print(f"Configuration validation error: {e}")
        print("Falling back to default configuration.")
        return Config(**DEFAULT_CONFIG_DICT)


def get_active_model_config() -> Dict[str, str]:
    """Return provider configuration for the active model.

    Returns:
        Dict with provider, base_url, api_key, and model
    """
    cfg = load_config()
    model_cfg = cfg.get_active_model_config()

    return {
        "provider": cfg.provider,
        "base_url": model_cfg.base_url,
        "api_key": model_cfg.api_key,
        "model": model_cfg.model,
    }


def save_config(config):
    """Save config to CONFIG_PATH.

    Args:
        config: Either a Config Pydantic model or a dict
    """
    ensure_config_dir()

    # Convert Pydantic model to dict if necessary
    if isinstance(config, Config):
        config_dict = config.model_dump()
    else:
        config_dict = config

    with open(CONFIG_PATH, "wb") as f:
        tomli_w.dump(config_dict, f)
    print(f"Configuration saved to {CONFIG_PATH}")
