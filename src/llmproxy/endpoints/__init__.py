"""Endpoints module."""

from .chat import router as chat_router
from .embeddings import router as embeddings_router
from .models import router as models_router
from .rerank import router as rerank_router

__all__ = [
    "chat_router",
    "embeddings_router",
    "models_router",
    "rerank_router",
]
