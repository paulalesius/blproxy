"""Global configuration state management."""

from typing import Optional

from .loader import load_config
from .models import AppConfig

_CONFIG: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = load_config()
    return _CONFIG


def set_config(config: AppConfig) -> None:
    """Set the global configuration instance."""
    global _CONFIG
    _CONFIG = config


def reload_config(path: Optional[str] = None) -> AppConfig:
    """Reload configuration from file."""
    global _CONFIG
    _CONFIG = load_config(path)
    return _CONFIG
