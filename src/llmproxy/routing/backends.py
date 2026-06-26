"""Backend routing configuration."""

from enum import Enum
from typing import Optional, Union

from ..config import get_config
from ..config.models import BackendConfig


class Backend(Enum):
    """Backend types with their path mappings."""
    
    LLM = "llm"
    EMBED = "embed"
    RERANK = "rerank"
    STT = "stt"
    TTS = "tts"
    
    @property
    def paths(self) -> list[str]:
        """Return paths that map to this backend."""
        mapping = {
            Backend.LLM: [
                "/v1/chat/completions",
                "/v1/completions",
                "/v1/models",
                "/v1/models/*",
                "/models",
                "/models/*",
            ],
            Backend.EMBED: ["/v1/embeddings"],
            Backend.RERANK: [
                "/v1/rerank",
                "/rerank",
                "/info",
                "/v1/info",
            ],
            Backend.STT: [
                "/v1/audio/transcriptions",
                "/v1/audio/translations",
            ],
            Backend.TTS: ["/v1/audio/speech"],
        }
        return mapping[self]
    
    @classmethod
    def for_path(cls, path: str) -> Optional["Backend"]:
        """Get backend for a given path (core backends only)."""
        for backend in cls:
            paths = backend.paths
            for p in paths:
                if p.endswith("*"):
                    prefix = p[:-1]
                    if path.startswith(prefix):
                        return backend
                elif path == p:
                    return backend
        return None


def _matches_custom_path(incoming_path: str, cfg: BackendConfig) -> bool:
    """Check if incoming_path matches this custom backend's path_prefix or paths."""
    if not cfg or cfg.type != "forward":
        return False

    candidates = []
    if cfg.path_prefix:
        candidates.append(cfg.path_prefix)
    if cfg.paths:
        candidates.extend(cfg.paths)

    for candidate in candidates:
        if not candidate:
            continue
        if candidate.endswith("/*") or candidate.endswith("*"):
            prefix = candidate.rstrip("/*")
            if incoming_path.startswith(prefix):
                return True
        elif incoming_path == candidate or incoming_path.startswith(candidate + "/"):
            return True
    return False


def get_backend_for_path(path: str) -> Optional[Union[Backend, str]]:
    """Get backend for a given path.

    Returns:
        - Backend enum member for core backends (llm, embed, etc.)
        - str (backend name) for custom forward backends
        - None if no match
    """
    # First check core backends (they take precedence for exact known paths)
    core = Backend.for_path(path)
    if core is not None:
        return core

    # Then check custom forward backends from current config
    try:
        config = get_config()
        for backend_name, backend_cfg in config.backends.items():
            if backend_cfg.type == "forward" and _matches_custom_path(path, backend_cfg):
                return backend_name
    except Exception:
        # If config not loaded yet or error, fall back to core only
        pass

    return None
