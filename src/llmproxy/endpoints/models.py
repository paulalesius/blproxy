"""Model listing endpoints."""

import httpx
import logging

from fastapi import APIRouter, HTTPException, Path

from ..config import get_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["models"])


@router.get("/models")
async def list_models() -> dict:
    """List all available models from configured backends."""
    config = get_config()
    models = []
    
    for backend_name, backend_config in config.backends.items():
        if not backend_config.enabled:
            continue
        
        try:
            async with httpx.AsyncClient(timeout=backend_config.timeout) as client:
                response = await client.get(f"{backend_config.url}/v1/models")
                response.raise_for_status()
                backend_models = response.json()
                
                # Prefix models with backend name for disambiguation
                if isinstance(backend_models, dict) and "data" in backend_models:
                    for model in backend_models["data"]:
                        model["id"] = f"{backend_name}:{model['id']}"
                    models.extend(backend_models["data"])
                elif isinstance(backend_models, list):
                    for model in backend_models:
                        model["id"] = f"{backend_name}:{model['id']}"
                    models.extend(backend_models)
        
        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch models from {backend_name}: {e}")
    
    return {"data": models}


@router.get("/models/{model_id}")
async def get_model(model_id: str = Path(...)) -> dict:
    """Get details for a specific model."""
    # Parse model_id as backend:model
    if ":" not in model_id:
        raise HTTPException(
            status_code=400,
            detail="Model ID must be in format backend:model",
        )
    
    backend_name, actual_model_id = model_id.split(":", 1)
    
    config = get_config()
    backend_config = config.backends.get(backend_name)
    
    if not backend_config or not backend_config.enabled:
        raise HTTPException(
            status_code=404,
            detail=f"Backend {backend_name} not found or disabled",
        )
    
    try:
        async with httpx.AsyncClient(timeout=backend_config.timeout) as client:
            response = await client.get(
                f"{backend_config.url}/v1/models/{actual_model_id}"
            )
            response.raise_for_status()
            model_data = response.json()
            model_data["id"] = model_id  # Restore prefixed ID
            return model_data
    
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch model {model_id}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Backend error: {str(e)}",
        )
