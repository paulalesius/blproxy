"""Configuration loader - YAML + environment overrides (YAML is authoritative)."""

import os
import yaml
from typing import Optional, Dict, Any
from .models import AppConfig, ServerConfig, BackendConfig, LockConfig


def load_yaml_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load raw config from YAML file or return empty dict."""
    if path and os.path.exists(path):
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    # Try default locations
    for candidate in ["config.yaml", "src/llmproxy/config.yaml", "/etc/llmproxy/config.yaml"]:
        if os.path.exists(candidate):
            with open(candidate, "r") as f:
                return yaml.safe_load(f) or {}
    return {}


def apply_env_overrides(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a few common environment overrides (kept minimal)."""
    if os.environ.get("LLMPROXY_HOST"):
        raw.setdefault("server", {})["host"] = os.environ["LLMPROXY_HOST"]
    if os.environ.get("LLMPROXY_PORT"):
        raw.setdefault("server", {})["port"] = int(os.environ["LLMPROXY_PORT"])
    if os.environ.get("LLMPROXY_LOG_LEVEL"):
        raw.setdefault("server", {})["log_level"] = os.environ["LLMPROXY_LOG_LEVEL"]
    if os.environ.get("LLMPROXY_API_KEY"):
        raw["api_key"] = os.environ["LLMPROXY_API_KEY"]
    return raw


def build_app_config(raw: Dict[str, Any]) -> AppConfig:
    """Build typed AppConfig from raw dict. Very tolerant."""
    server_raw = raw.get("server", {}) or {}

    server = ServerConfig(
        host=server_raw.get("host", "0.0.0.0"),
        port=int(server_raw.get("port", 8000)),
        log_level=server_raw.get("log_level", "INFO"),
    )

    # --- Backends ---
    backends: Dict[str, BackendConfig] = {}
    backends_raw = raw.get("backends", {}) or {}

    # Support both styles:
    # backends:
    #   rerank:
    #     base_url: ...
    #   llm:
    #     ...
    for name in ["llm", "embed", "rerank", "embeddings"]:
        entry = backends_raw.get(name) or backends_raw.get(name.replace("embeddings", "embed"))
        if isinstance(entry, dict):
            url = entry.get("base_url") or entry.get("url") or entry.get("baseURL") or ""
            if not url and name == "rerank":
                url = "http://127.0.0.1:8082"
            elif not url and name == "llm":
                url = "http://127.0.0.1:8080"
            elif not url and name in ("embed", "embeddings"):
                url = "http://127.0.0.1:8081"

            backends[name if name != "embeddings" else "embed"] = BackendConfig(
                name=name if name != "embeddings" else "embed",
                url=url,
                timeout=int(entry.get("timeout", 30)),
                read_timeout=int(entry.get("read_timeout", entry.get("readTimeout", 60))),
                locks=entry.get("locks", []) or [],
                enabled=entry.get("enabled", True),
            )

    # Ensure we always have the three main backends
    for name, default_url in [("llm", "http://127.0.0.1:8080"),
                              ("embed", "http://127.0.0.1:8081"),
                              ("rerank", "http://127.0.0.1:8082")]:
        if name not in backends:
            backends[name] = BackendConfig(name=name, url=default_url)

    # --- Lock config ---
    lock_raw = raw.get("global_lock") or raw.get("lock") or backends_raw.get("global_lock", {})
    if isinstance(lock_raw, bool):
        lock_raw = {"enabled": lock_raw}

    lock = LockConfig(
        enabled=bool(lock_raw.get("enabled", True)),
        locked_error=bool(lock_raw.get("locked_error", False)),
        backends=lock_raw.get("backends", {}) or {},
    )

    api_key = raw.get("api_key") or server_raw.get("api_key") or ""

    return AppConfig(
        backends=backends,
        server=server,
        lock=lock,
        api_key=api_key,
        log_requests=raw.get("log_requests", True),
        log_responses=raw.get("log_responses", True),
    )


def load_config(path: Optional[str] = None) -> AppConfig:
    raw = load_yaml_config(path)
    raw = apply_env_overrides(raw)
    return build_app_config(raw)


def reload_config(path: Optional[str] = None) -> AppConfig:
    from .state import set_config
    cfg = load_config(path)
    set_config(cfg)
    return cfg
