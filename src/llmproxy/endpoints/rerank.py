"""Rerank endpoints (TEI-compatible)."""

import httpx
import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..config import get_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["rerank"])


def _get_rerank_backend() -> str:
    """Get rerank backend URL from config."""
    config = get_config()
    rerank_config = config.backends.get("rerank")
    if not rerank_config or not rerank_config.enabled:
        raise HTTPException(
            status_code=503,
            detail="Rerank backend not configured or disabled",
        )
    return rerank_config.url


async def _proxy_request(
    path: str,
    json: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Proxy request to rerank backend."""
    backend_url = _get_rerank_backend()
    url = f"{backend_url}{path}"
    
    config = get_config()
    timeout = config.backends.get("rerank", type("obj", (object,), {"timeout": 30})()).timeout
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if json:
                response = await client.post(url, json=json)
            else:
                response = await client.get(url)
            
            response.raise_for_status()
            return response.json()
    
    except httpx.HTTPError as e:
        logger.error(f"Backend error: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Backend error: {str(e)}",
        )


@router.post("/rerank")
async def rerank(body: Dict[str, Any]) -> Dict[str, Any]:
    """Proxy rerank request to rerank backend."""
    logger.info("Rerank request")
    return await _proxy_request("/rerank", json=body)


@router.get("/info")
async def info() -> Dict[str, Any]:
    """Get rerank backend info."""
    logger.info("Rerank info request")
    return await _proxy_request("/info")
