import os
import copy
import tomllib
import tomli_w
from pathlib import Path

DEFAULT_CONFIG = {
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


def load_config():
    """Load Craft Code configuration, fallback to defaults if missing."""
    ensure_config_dir()

    if not CONFIG_PATH.exists():
        print(
            "No config file found, using default LM Studio settings. Please run 'craft-code --configure' to set up."
        )
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_PATH, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        print(f"Failed to load config file: {e}. Using defaults.")
        return DEFAULT_CONFIG

    # Deep merge user config with defaults (fill missing parts)
    merged = copy.deepcopy(DEFAULT_CONFIG)

    # Merge models from user config into defaults
    if "models" in data:
        merged["models"].update(data["models"])

    # Update provider selection
    if "provider" in data:
        merged["provider"] = data["provider"]

    return merged


def get_active_model_config():
    """Return provider configuration for the active model."""
    cfg = load_config()
    provider = cfg.get("provider", "lm_studio")
    model_cfg = cfg.get("models", {}).get(provider, {})
    return {
        "provider": provider,
        "base_url": model_cfg.get("base_url"),
        "api_key": model_cfg.get("api_key"),
        "model": model_cfg.get("model"),
    }


def save_config(config):
    """Save config to CONFIG_PATH."""
    ensure_config_dir()
    with open(CONFIG_PATH, "wb") as f:
        tomli_w.dump(config, f)
    print(f"Configuration saved to {CONFIG_PATH}")
