"""Chat completion endpoints."""

import httpx
import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..config import get_config
from ..routing.backends import Backend

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["chat"])


def _get_llm_backend() -> str:
    """Get LLM backend URL from config."""
    config = get_config()
    llm_config = config.backends.get("llm")
    if not llm_config or not llm_config.enabled:
        raise HTTPException(
            status_code=503,
            detail="LLM backend not configured or disabled",
        )
    return llm_config.url


async def _proxy_request(
    method: str,
    path: str,
    json: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Proxy request to backend."""
    backend_url = _get_llm_backend()
    url = f"{backend_url}{path}"
    
    config = get_config()
    timeout = config.backends.get("llm", type("obj", (object,), {"timeout": 30})()).timeout
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method == "POST":
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


@router.post("/chat/completions")
async def chat_completions(body: Dict[str, Any]) -> Dict[str, Any]:
    """Proxy chat completion request to LLM backend."""
    logger.info("Chat completion request")
    return await _proxy_request("POST", "/chat/completions", json=body)


@router.post("/completions")
async def completions(body: Dict[str, Any]) -> Dict[str, Any]:
    """Proxy legacy completion request to LLM backend."""
    logger.info("Completion request")
    return await _proxy_request("POST", "/completions", json=body)
