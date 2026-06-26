"""Configuration data models."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BackendConfig:
    """Configuration for a single backend."""
    name: str
    url: str
    timeout: int = 30
    read_timeout: int = 60
    api_key: str = ""
    locks: list[str] = field(default_factory=list)
    enabled: bool = True
    lock_script: Optional[str] = None

    # --- Custom forwarder specific fields (only used when type == "forward") ---
    type: str = "core"                    # "core" or "forward"
    path_prefix: Optional[str] = None
    paths: list[str] = field(default_factory=list)
    strip_prefix: bool = False


@dataclass
class ServerConfig:
    """Server configuration."""
    host: str = "0.0.0.0"
    port: int = 4002
    log_level: str = "INFO"


@dataclass
class LockConfig:
    """Lock configuration."""
    enabled: bool = True
    locked_error: bool = False
    timeout: int = 300
    backends: dict[str, list[str]] = field(default_factory=dict)
    lock_script: Optional[str] = None


@dataclass
class AppConfig:
    """Main application configuration."""
    backends: dict[str, BackendConfig] = field(default_factory=dict)
    server: ServerConfig = field(default_factory=ServerConfig)
    lock: LockConfig = field(default_factory=LockConfig)
    api_key: Optional[str] = None
    log_requests: bool = True
    log_responses: bool = True
