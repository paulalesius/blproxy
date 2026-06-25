"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import get_config
from .endpoints import (
    chat_router,
    embeddings_router,
    models_router,
    rerank_router,
)
from .middleware import (
    APIKeyMiddleware,
    GlobalLockMiddleware,
    LoggingMiddleware,
)
from .components.tei import TEIComponent
from .components.openai import OpenAIComponent
from .components.embeddings import EmbeddingsComponent

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()
    logger.info("Starting LLM Proxy components...")

    app.state.tei = TEIComponent()
    app.state.openai = OpenAIComponent()
    app.state.embeddings = EmbeddingsComponent()

    logger.info("All components initialized successfully")
    yield

    logger.info("Shutting down components...")
    await app.state.tei.close()
    await app.state.openai.close()
    await app.state.embeddings.close()


def create_app(config_path: str | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if config_path:
        from .config import reload_config
        reload_config(config_path)

    config = get_config()

    app = FastAPI(
        title="LLM Proxy",
        description="Unified proxy for LLM, embeddings and rerank backends",
        version="0.3.0",
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(LoggingMiddleware)
    if config.api_key:
        app.add_middleware(APIKeyMiddleware)
    if config.lock.enabled:
        app.add_middleware(GlobalLockMiddleware)

    app.include_router(chat_router)
    app.include_router(embeddings_router)
    app.include_router(models_router)
    app.include_router(rerank_router)

    @app.get("/")
    async def root():
        return {"service": "llmproxy", "status": "running"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


# Do NOT create the app at import time.
# The app should only be created in main.py after the config is loaded.
# app = create_app()
