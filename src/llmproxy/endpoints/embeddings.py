"""Embedding endpoints."""

import httpx
import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..config import get_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["embeddings"])


def _get_embed_backend() -> str:
    """Get embeddings backend URL from config."""
    config = get_config()
    embed_config = config.backends.get("embed")
    if not embed_config or not embed_config.enabled:
        raise HTTPException(
            status_code=503,
            detail="Embeddings backend not configured or disabled",
        )
    return embed_config.url


async def _proxy_request(
    path: str,
    json: Dict[str, Any],
) -> Dict[str, Any]:
    """Proxy request to embeddings backend."""
    backend_url = _get_embed_backend()
    url = f"{backend_url}{path}"
    
    config = get_config()
    timeout = config.backends.get("embed", type("obj", (object,), {"timeout": 30})()).timeout
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=json)
            response.raise_for_status()
            return response.json()
    
    except httpx.HTTPError as e:
        logger.error(f"Backend error: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Backend error: {str(e)}",
        )


@router.post("/embeddings")
async def embeddings(body: Dict[str, Any]) -> Dict[str, Any]:
    """Proxy embeddings request to embeddings backend."""
    logger.info("Embeddings request")
    return await _proxy_request("/embeddings", json=body)
