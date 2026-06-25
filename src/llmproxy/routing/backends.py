"""Backend routing configuration."""

from enum import Enum
from typing import Optional


class Backend(Enum):
    """Backend types with their path mappings."""
    
    LLM = "llm"
    EMBED = "embed"
    RERANK = "rerank"
    
    @property
    def paths(self) -> list[str]:
        """Return paths that map to this backend."""
        mapping = {
            Backend.LLM: ["/v1/chat/completions", "/v1/completions"],
            Backend.EMBED: ["/v1/embeddings"],
            Backend.RERANK: ["/v1/rerank"],
        }
        return mapping[self]
    
    @classmethod
    def for_path(cls, path: str) -> Optional["Backend"]:
        """Get backend for a given path."""
        for backend in cls:
            if path in backend.paths:
                return backend
        return None


def get_backend_for_path(path: str) -> Optional[Backend]:
    """Get backend for a given path."""
    return Backend.for_path(path)
